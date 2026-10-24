#pragma once
#include <juce_dsp/juce_dsp.h>
#include "vendor/MuffDSP.h"
#include "vendor/Circuit/AnalogCircuit.h"
// Mechanical extraction of the original DSP processor. No GUI/VST host code.
class OriginalMuffDSP {
    static constexpr size_t legacyCount=6;
    static constexpr size_t circuitCount=muff::circuit::revisions.size();
    static constexpr size_t totalModels=legacyCount+circuitCount;
    std::array<muff::Engine,legacyCount> legacy;
    std::array<std::array<muff::circuit::AnalogCircuit,2>,circuitCount> circuits;
    std::array<juce::SmoothedValue<float>,totalModels> modelWeights;
    std::unique_ptr<juce::dsp::Oversampling<float>> oversampling;
    juce::SmoothedValue<float> volumeSmooth,toneSmooth,sustainSmooth,wet;
    std::vector<float> volumes,tones,sustains,mixes,inputScratch,outputScratch;
    std::array<std::vector<float>,totalModels> weights;
    std::atomic<float> *volumeParam,*toneParam,*sustainParam,*modelParam,*bypassParam,*circuitParam;
    size_t factor=4;
    bool ready=false, channelsAligned=true;

public:
 int latencyFrames=0;
 std::array<std::atomic<float>,6> controls;
 OriginalMuffDSP(){const float d[]{.5,.5,.5,0,0,float(circuitCount)};for(int i=0;i<6;++i)controls[i].store(d[i]);volumeParam=&controls[0];toneParam=&controls[1];sustainParam=&controls[2];modelParam=&controls[3];bypassParam=&controls[4];circuitParam=&controls[5];}
 int selectedModel() const {int c=juce::jlimit(0,int(circuitCount),int(circuitParam->load()));return c==0?juce::jlimit(0,5,int(modelParam->load())):5+c;}
 bool isReady() const{return ready;}
    void prepareToPlay(double rate,int size) {
        // Keep the internal rate near 176.4/192 kHz at the usual host rates.
        const size_t stages=rate>=176400?0u:(rate>=88200?1u:2u);
        factor=size_t(1)<<stages;
        oversampling=std::make_unique<juce::dsp::Oversampling<float>>(2,stages,juce::dsp::Oversampling<float>::filterHalfBandPolyphaseIIR,true,true);
        oversampling->initProcessing(static_cast<size_t>(std::max(1,size)));oversampling->reset();
        const double internalRate=rate*double(factor);
        ready=true;channelsAligned=true;
        for(auto& e:legacy)e.prepare(internalRate);
        for(size_t m=0;m<circuitCount;++m)for(auto& c:circuits[m])ready=c.prepare(internalRate,m,sustainParam->load(),toneParam->load(),volumeParam->load())&&ready;
        latencyFrames=int(oversampling->getLatencyInSamples());
        const size_t capacity=static_cast<size_t>(std::max(1,size))*factor;
        for(size_t m=0;m<totalModels;++m){modelWeights[m].reset(internalRate,.02);modelWeights[m].setCurrentAndTargetValue(int(m)==selectedModel()?1.f:0.f);weights[m].resize(capacity);}
        volumeSmooth.reset(internalRate,.02);toneSmooth.reset(internalRate,.02);sustainSmooth.reset(internalRate,.02);wet.reset(internalRate,.01);
        volumeSmooth.setCurrentAndTargetValue(volumeParam->load());toneSmooth.setCurrentAndTargetValue(toneParam->load());sustainSmooth.setCurrentAndTargetValue(sustainParam->load());wet.setCurrentAndTargetValue(bypassParam->load()>.5f?0.f:1.f);
        volumes.resize(capacity);tones.resize(capacity);sustains.resize(capacity);mixes.resize(capacity);inputScratch.resize(capacity);outputScratch.resize(capacity);
    }
    void processBlock(juce::AudioBuffer<float>& buffer,juce::MidiBuffer&) {
        juce::ScopedNoDenormals noDenormals;
        const int count=buffer.getNumSamples();if(count==0)return;
        if(volumes.empty()||!oversampling){buffer.clear();return;}
        for(int c=0;c<buffer.getNumChannels();++c)for(int i=0;i<count;++i)if(!std::isfinite(buffer.getSample(c,i)))buffer.setSample(c,i,0);
        bool mirror=channelsAligned&&buffer.getNumChannels()==2&&std::memcmp(buffer.getReadPointer(0),buffer.getReadPointer(1),size_t(count)*sizeof(float))==0;
        if(buffer.getNumChannels()==2&&!mirror)channelsAligned=false;
        juce::dsp::AudioBlock<float> full(buffer);
        volumeSmooth.setTargetValue(volumeParam->load());toneSmooth.setTargetValue(toneParam->load());sustainSmooth.setTargetValue(sustainParam->load());wet.setTargetValue(bypassParam->load()>.5f?0.f:1.f);
        const int selected=selectedModel();
        std::array<size_t,totalModels> active{};size_t activeCount=0;
        for(size_t m=0;m<totalModels;++m){modelWeights[m].setTargetValue(int(m)==selected?1.f:0.f);if(modelWeights[m].isSmoothing()||modelWeights[m].getCurrentValue()!=0)active[activeCount++]=m;}
        for(size_t offset=0;offset<static_cast<size_t>(count);){
            size_t length=std::min(volumes.size()/factor,static_cast<size_t>(count)-offset);
            auto block=full.getSubBlock(offset,length);auto up=oversampling->processSamplesUp(block);size_t n=up.getNumSamples();
            for(size_t i=0;i<n;++i){volumes[i]=volumeSmooth.getNextValue();tones[i]=toneSmooth.getNextValue();sustains[i]=sustainSmooth.getNextValue();mixes[i]=wet.getNextValue();}
            for(size_t a=0;a<activeCount;++a){size_t m=active[a];for(size_t i=0;i<n;++i)weights[m][i]=modelWeights[m].getNextValue();}
            for(int channel=0;channel<(mirror?1:buffer.getNumChannels());++channel){
                auto* data=up.getChannelPointer(static_cast<size_t>(channel));std::copy(data,data+n,inputScratch.begin());std::fill(outputScratch.begin(),outputScratch.begin()+static_cast<ptrdiff_t>(n),0.f);
                for(size_t a=0;a<activeCount;++a){size_t m=active[a];
                    for(size_t i=0;i<n;++i){float y=m<legacyCount?legacy[m].process(inputScratch[i],channel,int(m),sustains[i],tones[i])*2*volumes[i]:circuits[m-legacyCount][static_cast<size_t>(channel)].process(inputScratch[i]*float(muff::circuit::voltsPerFullScale),sustains[i],tones[i],volumes[i])/float(muff::circuit::voltsPerFullScale);outputScratch[i]+=y*weights[m][i];}
                }
                for(size_t i=0;i<n;++i)data[i]=inputScratch[i]+(outputScratch[i]-inputScratch[i])*mixes[i];
            }
            if(mirror){
                std::copy(up.getChannelPointer(0),up.getChannelPointer(0)+n,up.getChannelPointer(1));
                for(size_t a=0;a<activeCount;++a){size_t m=active[a];if(m<legacyCount)legacy[m].mirrorChannel();else circuits[m-legacyCount][1]=circuits[m-legacyCount][0];}
            }
            oversampling->processSamplesDown(block);offset+=length;
        }
    }
};
