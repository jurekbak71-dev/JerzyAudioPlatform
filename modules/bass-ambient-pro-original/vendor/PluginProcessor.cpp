#include "PluginProcessor.h"
#include "PluginEditor.h"

std::vector<ParameterSpec> parameterSpecs() {
    const jerzy::Parameters p;
    std::vector<ParameterSpec> out;
    auto choices=[](const char* text) { return juce::StringArray::fromTokens(text,"|",""); };
#define BOOL(f,l,g) out.push_back({#f,l,g,1,0,1,double(p.f),1,{}});
#define FLOAT(f,a,b,s,l,g) out.push_back({#f,l,g,0,a,b,p.f,s,{}});
#define INT(f,a,b,l,g) out.push_back({#f,l,g,2,a,b,double(p.f),1,{}});
#define CHOICE(f,l,g,c) out.push_back({#f,l,g,3,0,0,double(p.f),1,choices(c)});
#define CHOICE_DEN(f,l,g) out.push_back({#f,l,g,3,0,0,1,1,choices("2|4|8|16")});
#include "Parameters.def"
#undef BOOL
#undef FLOAT
#undef INT
#undef CHOICE
#undef CHOICE_DEN
    for(int i=0;i<6;++i) out.push_back({"order"+juce::String(i),"FX slot "+juce::String(i+1),3,3,0,0,double(i),1,choices("Drive / Comp|Chorus|Delay|Granular|Reverb|Width")});
    // Keep original FX IDs for BASS; append independent AMBIENT and MASTER IDs.
    const auto original=out;
    for(const auto& prefix:juce::StringArray{"pad_","master_"}) for(auto spec:original) if(spec.group==3) {
        spec.id=prefix+spec.id;
        spec.label=(prefix=="pad_"?"Ambient ":"Master ")+spec.label;
        out.push_back(std::move(spec));
    }
    out.push_back({"masterFX","Master FX amount",4,0,0,1,0,1,{}});
    for(int lane=0;lane<4;++lane) {
        const auto prefix="drum"+juce::String(lane)+"_";
        const char* names[]{"Kick","Snare","Hi-hat","Aux"};
        const juce::String name=names[lane];
        out.push_back({prefix+"enabled",name+" power",8+lane,1,0,1,1,1,{}});
        out.push_back({prefix+"level",name+" level",8+lane,0,0,1,.7,1,{}});
        out.push_back({prefix+"drive",name+" drive",8+lane,0,0,1,.1,1,{}});
        out.push_back({prefix+"tone",name+" tone",8+lane,0,0,1,.5,1,{}});
        out.push_back({prefix+"cutoff",name+" filter Hz",8+lane,0,40,18000,12000,.3,{}});
        out.push_back({prefix+"decay",name+" decay s",8+lane,0,.015,2,lane==2?.06:.2,.4,{}});
        out.push_back({prefix+"pan",name+" pan",8+lane,0,-1,1,0,1,{}});
        for(int step=0;step<64;++step) out.push_back({prefix+"step"+juce::String(step),name+" step "+juce::String(step+1),12,2,0,127,double(p.drumGrid[size_t(lane)][size_t(step)]),1,{}});
    }
    // Append new rack IDs after existing parameters to preserve older ordering.
    for(const auto& prefix:juce::StringArray{"arp_","drums_","krell_"})for(auto spec:original)if(spec.group==3){spec.id=prefix+spec.id;spec.label=(prefix=="arp_"?"Arpeggio ":prefix=="drums_"?"Drums ":"Krell ")+spec.label;out.push_back(std::move(spec));}
    // New performance parameters follow every legacy static and generated ID.
#define BOOL(f,l,g) out.push_back({#f,l,g,1,0,1,double(p.f),1,{}});
#define CHOICE(f,l,g,c) out.push_back({#f,l,g,3,0,0,double(p.f),1,choices(c)});
#include "PerformanceParameters.def"
#undef BOOL
#undef CHOICE
    // New IDs MUST be appended after all frozen legacy IDs.
    out.push_back({"bassBody","BASS Body resonance",0,0,0,1,0,1,{}});
    out.push_back({"bassAttackTransient","BASS Pick / beater attack",0,0,0,1,0,1,{}});
    out.push_back({"padBody","AMBIENT Modal body resonance",2,0,0,1,0,1,{}});
    out.push_back({"padAttackTransient","AMBIENT Strike excitation",2,0,0,1,0,1,{}});
    return out;
}

juce::AudioProcessorValueTreeState::ParameterLayout BassAmbientProcessor::layout() {
    juce::AudioProcessorValueTreeState::ParameterLayout result;
    for(const auto& s:parameterSpecs()) {
        juce::ParameterID id{s.id,1};
        if(s.kind==1) result.add(std::make_unique<juce::AudioParameterBool>(id,s.label,s.initial>.5));
        else if(s.kind==2) result.add(std::make_unique<juce::AudioParameterInt>(id,s.label,int(s.minimum),int(s.maximum),int(s.initial)));
        else if(s.kind==3) result.add(std::make_unique<juce::AudioParameterChoice>(id,s.label,s.choices,int(s.initial)));
        else result.add(std::make_unique<juce::AudioParameterFloat>(id,s.label,juce::NormalisableRange<float>(float(s.minimum),float(s.maximum),0,float(s.skew)),float(s.initial)));
    }
    return result;
}

BassAmbientProcessor::BassAmbientProcessor()
    : AudioProcessor(buses()),
      state(*this,nullptr,"JerzyBassAmbientPRO",layout()) {
    for(auto& mapping:ccMap)mapping.store(-1);
    const auto specs=parameterSpecs();
    for(const auto& s:specs) {values.push_back(state.getRawParameterValue(s.id));hostParameters.push_back(state.getParameter(s.id));parameterGroups.push_back(s.group);}
    generateParameter=state.getParameter("autoPlay");
    const char* switches[]{"bass","pad","arp","drums","fxEnabled","autoPlay","composerEnabled","composerPlaying","composerSongMode","composerLoop","composerScene","composerIntensity","separateOutputs","midiPlayback"};
    for(int k=0;k<14;++k) for(size_t i=0;i<specs.size();++i) if(specs[i].id==switches[k])ccMap[size_t(20+k)].store(int(i));
    for(size_t i=0;i<specs.size();++i)if(specs[i].id=="krell")ccMap[34].store(int(i));
}

jerzy::Parameters BassAmbientProcessor::readParameters() const {
    jerzy::Parameters p;size_t i=0;
#define BOOL(f,l,g) p.f=values[i++]->load()>.5f;
#define FLOAT(f,a,b,s,l,g) p.f=values[i++]->load();
#define INT(f,a,b,l,g) p.f=int(std::lround(values[i++]->load()));
#define CHOICE(f,l,g,c) p.f=int(std::lround(values[i++]->load()));
#define CHOICE_DEN(f,l,g) { constexpr int d[]{2,4,8,16};p.f=d[juce::jlimit(0,3,int(std::lround(values[i++]->load())))]; }
#include "Parameters.def"
#undef BOOL
#undef FLOAT
#undef INT
#undef CHOICE
#undef CHOICE_DEN
    for(int k=0;k<6;++k) p.order[size_t(k)]=int(std::lround(values[i++]->load()));
    for(auto* rack:{&p.padRack,&p.masterRack}) {
#define BOOL(f,l,g) rack->f=values[i++]->load()>.5f;
#define FLOAT(f,a,b,s,l,g) rack->f=values[i++]->load();
#define CHOICE(f,l,g,c) rack->f=int(std::lround(values[i++]->load()));
#include "FXParameters.def"
#undef BOOL
#undef FLOAT
#undef CHOICE
        for(int k=0;k<6;++k) rack->order[size_t(k)]=int(std::lround(values[i++]->load()));
    }
    p.masterFX=values[i++]->load();
    for(auto& sound:p.drumSounds) {
        sound.enabled=values[i++]->load()>.5f;sound.level=values[i++]->load();sound.drive=values[i++]->load();
        sound.tone=values[i++]->load();sound.cutoff=values[i++]->load();sound.decay=values[i++]->load();sound.pan=values[i++]->load();
        for(auto& step:p.drumGrid[size_t(&sound-p.drumSounds.data())])step=int(std::lround(values[i++]->load()));
    }
    for(auto* rack:{&p.arpRack,&p.drumsRack,&p.krellRack}) {
#define BOOL(f,l,g) rack->f=values[i++]->load()>.5f;
#define FLOAT(f,a,b,s,l,g) rack->f=values[i++]->load();
#define CHOICE(f,l,g,c) rack->f=int(std::lround(values[i++]->load()));
#include "FXParameters.def"
#undef BOOL
#undef FLOAT
#undef CHOICE
        for(int k=0;k<6;++k)rack->order[size_t(k)]=int(std::lround(values[i++]->load()));
    }
#define BOOL(f,l,g) p.f=values[i++]->load()>.5f;
#define CHOICE(f,l,g,c) p.f=int(std::lround(values[i++]->load()));
#include "PerformanceParameters.def"
#undef BOOL
#undef CHOICE
    p.bassBody=values[i++]->load();
    p.bassAttackTransient=values[i++]->load();
    p.padBody=values[i++]->load();
    p.padAttackTransient=values[i++]->load();
    return p;
}

void BassAmbientProcessor::prepareToPlay(double sampleRate,int) {
    stopResourceWorker();stopLiveRecording();liveAudioReady=false;liveAudioRate=sampleRate;
    delete activeComposer;activeComposer=nullptr;delete pendingComposer.exchange(nullptr);delete retiredComposer.exchange(nullptr);
    activeComposer=new jerzy::composer::Compiled(jerzy::composer::compile(composerDocument()));compiledRevision=composerRevision.load();
    playback=nullptr;wasComposerPlaying=false;previousComposerBeat=-1;lastComposerPPQ=-1;sectionIndex=-1;lastResourceSection=-2;tailUntil.fill(0);previousTracks.fill(false);
    sr=sampleRate;midiClock.reset(sr);clockSamples=0;previousClock=-1;instrument.prepare(sr);current=readParameters();localPPQ=0;resetRequested=false;
    instrument.configureResources(current);instrument.serviceResources();instrument.configureResources(current);
    lastControlSnapshot=readParameters();
    liveAudioReady=true;stopWorker=false;resourceWorker=std::thread([this] {while(!stopWorker.load()) {instrument.serviceResources();serviceComposer();serviceLive();std::this_thread::sleep_for(std::chrono::milliseconds(5));}instrument.serviceResources();});
}
bool BassAmbientProcessor::isBusesLayoutSupported(const BusesLayout& buses) const {
    if(!buses.inputBuses.isEmpty()||buses.outputBuses.isEmpty()||buses.outputBuses.size()>11||buses.getMainOutputChannelSet()!=juce::AudioChannelSet::stereo())return false;
    for(const auto& layout:buses.outputBuses)if(!layout.isDisabled()&&layout!=juce::AudioChannelSet::stereo())return false;
    return true;
}

void BassAmbientProcessor::processBlock(juce::AudioBuffer<float>& audio,juce::MidiBuffer& midi) {
    juce::ScopedNoDenormals noDenormals;
    const bool reset=resetRequested.exchange(false),panic=panicRequested.exchange(false);
    if(reset||panic) {instrument.reset();wasComposerPlaying=false;playback=nullptr;previousComposerBeat=-1;tailUntil.fill(0);previousTracks.fill(false);}
    audio.clear();auto target=readParameters();
    // Source is a host parameter as well as a GUI choice: automation must select
    // the same routing, without automatically starting JAM or the arrangement.
    if(target.performanceSource!=lastPerformanceSource){
        const bool changed=lastPerformanceSource>=0;lastPerformanceSource=target.performanceSource;
        if(lastPerformanceSource>0){setParameterValue("modularMidi",lastPerformanceSource==1?1:0);setParameterValue("composerEnabled",lastPerformanceSource==3?1:0);setParameterValue("midiPlayback",0);if(lastPerformanceSource!=2)setParameterValue("autoPlay",0);if(lastPerformanceSource==2)setParameterValue("direct",0);target=readParameters();}
        if(changed){instrument.reset();wasComposerPlaying=false;playback=nullptr;previousComposerBeat=-1;tailUntil.fill(0);previousTracks.fill(false);}
    }
    auto controls=target;
    adoptComposer(controls.composerEnabled);
    if(auto mask=resetParts.exchange(0))for(int t=0;t<8;++t)if(mask&(1U<<t))instrument.resetMidiPart(t);
    if(controls.modularMidi&&!controls.composerEnabled){target.direct=current.direct=controls.bassMidiMode==0;controls.direct=target.direct;}
    if(!controls.composerEnabled&&wasComposerPlaying){instrument.allOff();wasComposerPlaying=false;playback=nullptr;}
    std::array<int,10> stemChannels{};stemChannels.fill(-1);unsigned splitMask=0;
    for(int t=0;t<10;++t)if(auto* bus=getBus(false,t==7?10:t>=8?t:t+1);bus&&bus->isEnabled()) {
        const int offset=getChannelIndexInProcessBlockBuffer(false,t==7?10:t>=8?t:t+1,0);
        if(offset>=0&&offset+1<audio.getNumChannels()){stemChannels[size_t(t)]=offset;if(controls.separateOutputs)splitMask|=1U<<t;}
    }
    if(!controls.composerEnabled)instrument.configureResources(target);
    // Structural changes are immediate; continuous controls ramp at audio rate.
    auto previous=current;current=target;
#define BOOL(f,l,g)
#define FLOAT(f,a,b,s,l,g) current.f=previous.f;
#define INT(f,a,b,l,g)
#define CHOICE(f,l,g,c)
#define CHOICE_DEN(f,l,g)
#include "Parameters.def"
#undef BOOL
#undef FLOAT
#undef INT
#undef CHOICE
#undef CHOICE_DEN
    current.bassBody=previous.bassBody;current.bassAttackTransient=previous.bassAttackTransient;
    current.padBody=previous.padBody;current.padAttackTransient=previous.padAttackTransient;
    current.padRack=previous.padRack;current.masterRack=previous.masterRack;current.arpRack=previous.arpRack;current.drumsRack=previous.drumsRack;current.krellRack=previous.krellRack;
    // Adopt discrete fields immediately, retaining only continuous values for the ramp.
    for(int rack=0;rack<5;++rack) {
        auto& c=rack==0?current.padRack:rack==1?current.masterRack:rack==2?current.arpRack:rack==3?current.drumsRack:current.krellRack;
        const auto& t=rack==0?target.padRack:rack==1?target.masterRack:rack==2?target.arpRack:rack==3?target.drumsRack:target.krellRack;
#define BOOL(f,l,g) c.f=t.f;
#define FLOAT(f,a,b,s,l,g)
#define CHOICE(f,l,g,c_) c.f=t.f;
#include "FXParameters.def"
#undef BOOL
#undef FLOAT
#undef CHOICE
        c.order=t.order;
    }
    current.masterFX=previous.masterFX;
    double tempo=target.internalTempo,ppq=localPPQ;bool playing=false,hostAvailable=false;int num=4,den=4;
    if(controls.clockSource!=previousClock){previousClock=controls.clockSource;instrument.allOff();wasComposerPlaying=false;localPPQ=ppq=0;}
    if(controls.clockSource==1)if(auto* head=getPlayHead())if(auto position=head->getPosition()){
        if(auto t=position->getBpm()){tempo=*t;hostAvailable=true;}
        if(auto t=position->getPpqPosition())ppq=*t;
        if(auto t=position->getTimeSignature()){num=t->numerator;den=t->denominator;}
        playing=position->getIsPlaying();
    }
    if(controls.clockSource==2){tempo=midiClock.bpm;ppq=midiClock.beat;playing=midiClock.running&&midiClock.valid(clockSamples);}
    const bool clockReady=controls.clockSource==0||(controls.clockSource==1&&hostAvailable&&playing)||(controls.clockSource==2&&playing);
    clockStatus=controls.clockSource==0?0:clockReady?1:(controls.clockSource==2&&midiClock.locked?3:2);
    tempo=juce::jlimit(20.0,400.0,tempo);tempoDisplay=tempo;clockBarBeats=double(num)*4/std::max(1,den);
    instrument.beginBlock(ppq,tempo,playing);
    double increment=tempo/(60*sr);const double smoothing=1-std::exp(-1/(sr*.02));
    std::array<float,10> peaks{};std::array<bool,8> inputs{},active{};
    auto event=midi.cbegin();const auto end=midi.cend();float maximum=0;
    for(int sample=0;sample<audio.getNumSamples();++sample) {
#define BOOL(f,l,g)
#define FLOAT(f,a,b,s,l,g) current.f+=(target.f-current.f)*smoothing;
#define INT(f,a,b,l,g)
#define CHOICE(f,l,g,c)
#define CHOICE_DEN(f,l,g)
#include "Parameters.def"
#undef BOOL
#undef FLOAT
#undef INT
#undef CHOICE
#undef CHOICE_DEN
        current.bassBody+=(target.bassBody-current.bassBody)*smoothing;
        current.bassAttackTransient+=(target.bassAttackTransient-current.bassAttackTransient)*smoothing;
        current.padBody+=(target.padBody-current.padBody)*smoothing;
        current.padAttackTransient+=(target.padAttackTransient-current.padAttackTransient)*smoothing;
        for(int rack=0;rack<5;++rack) {
            auto& c=rack==0?current.padRack:rack==1?current.masterRack:rack==2?current.arpRack:rack==3?current.drumsRack:current.krellRack;
            const auto& t=rack==0?target.padRack:rack==1?target.masterRack:rack==2?target.arpRack:rack==3?target.drumsRack:target.krellRack;
#define BOOL(f,l,g)
#define FLOAT(f,a,b,s,l,g) c.f+=(t.f-c.f)*smoothing;
#define CHOICE(f,l,g,c_)
#include "FXParameters.def"
#undef BOOL
#undef FLOAT
#undef CHOICE
        }
        current.masterFX+=(target.masterFX-current.masterFX)*smoothing;
        double position=controls.clockSource==2?midiClock.beat:ppq+sample*increment;
        while(event!=end&&(*event).samplePosition<=sample) {
            auto m=(*event).getMessage();int ch=m.getChannel();
            if(m.isMidiClock()){midiClock.tick(clockSamples+sample);if(controls.clockSource==2){tempo=midiClock.bpm;increment=tempo/(60*sr);position=midiClock.beat;}}
            else if(m.isMidiStart()||m.isMidiContinue()||m.isMidiStop()||m.isSongPositionPointer()){
                if(m.isMidiStart())midiClock.start();else if(m.isMidiContinue())midiClock.resume();else if(m.isMidiStop())midiClock.stop();else midiClock.songPosition(m.getSongPositionPointerMidiBeat());
                if(controls.clockSource==2&&!m.isSongPositionPointer()){
                    const bool run=!m.isMidiStop();controls.composerPlaying=run;controls.autoPlay=run&&!controls.composerEnabled;target.autoPlay=current.autoPlay=controls.autoPlay;
                    setParameterValue("composerPlaying",run?1:0);setParameterValue("autoPlay",controls.autoPlay?1:0);wasComposerPlaying=false;
                }
            }
            else if(controls.modularMidi&&!controls.composerEnabled&&(m.isNoteOn()||m.isNoteOff())) {
                const int track=ch==1?0:ch==2?1:ch==3?2:ch==4?7:ch==10?3:-1;
                const bool generated=track==0?true:track==1?controls.padMidiMode==1:track==2?controls.arpMidiMode==1:track==7?controls.krellMidiMode==1:false;
                if(generated){if(m.isNoteOn())instrument.noteOn(m.getNoteNumber(),ch,m.getFloatVelocity(),current,position);else instrument.noteOff(m.getNoteNumber(),ch,current,position);}
                else routePartMidi(m,current);
                if(track==0&&m.isNoteOn()&&controls.harmonyLink)setParameterValue("harmonyRoot",float(m.getNoteNumber()));
            }
            else if((controls.midiPlayback||controls.composerEnabled)&&!m.isController()&&!m.isPitchWheel()) {if(controls.midiPlayback)routePartMidi(m,current);}
            else if(m.isNoteOn()){instrument.noteOn(m.getNoteNumber(),ch,m.getFloatVelocity(),current,position);if(controls.harmonyLink&&ch!=10)setParameterValue("harmonyRoot",float(m.getNoteNumber()));}
            else if(m.isNoteOff()) instrument.noteOff(m.getNoteNumber(),ch,current,position);
            else if(m.isPitchWheel()) instrument.pitchBend(ch,m.getPitchWheelValue());
            else if(m.isController()) {
                const int cc=m.getControllerNumber(),value=m.getControllerValue();
                const int mapped=ccMap[size_t(cc)].load();if(mapped>=0&&mapped<int(parameterGroups.size())){const int group=parameterGroups[size_t(mapped)];if(group<=1)inputs[0]=true;else if(group==2)inputs[1]=true;else if(group==6)inputs[2]=true;else if(group>=8&&group<=11)inputs[size_t(group-5)]=true;else if(group==23||group==24)inputs[7]=true;else if(group>=14&&group<=20)inputs[size_t(group-14)]=true;}

                if(cc==120) {generateParameter->setValueNotifyingHost(0);target.autoPlay=current.autoPlay=controls.autoPlay=false;if(auto* parameter=state.getParameter("composerPlaying"))parameter->setValueNotifyingHost(0);controls.composerPlaying=false;instrument.reset();wasComposerPlaying=false;}
                else if(cc==123)instrument.allOff();
                else {handleMappedController(cc,value,controls);target=controls;instrument.controller(ch,cc,value,current,position);}
                // Discrete module changes apply at the exact event sample.
                current.bass=target.bass;current.pad=target.pad;current.arp=target.arp;current.drums=target.drums;current.krell=target.krell;
                current.fxEnabled=target.fxEnabled;current.autoPlay=target.autoPlay;
            }
            else if(m.isAllNotesOff()||m.isAllSoundOff()) instrument.allOff();
            if(m.isNoteOn()){
                lastMidiChannel=ch;lastMidiNote=m.getNoteNumber();
                if(controls.midiPlayback||controls.modularMidi){const int track=ch==1?0:ch==2?1:ch==3?2:ch==4?7:ch==10?(m.getNoteNumber()==36?3:m.getNoteNumber()==38||m.getNoteNumber()==40?4:m.getNoteNumber()==42||m.getNoteNumber()==44?5:6):-1;if(track>=0)inputs[size_t(track)]=true;}
                else if(!controls.composerEnabled){inputs[0]|=controls.bass;inputs[1]|=controls.pad;inputs[2]|=controls.arp;inputs[7]|=controls.krell;if(ch==10)for(int t=3;t<7;++t)inputs[size_t(t)]=true;}
            }
            ++event;
        }
        auto playbackControls=controls;
        const bool advancing=controls.clockSource==0||(controls.clockSource==1&&hostAvailable&&playing)||(controls.clockSource==2&&midiClock.running&&midiClock.valid(clockSamples+sample));
        if(!advancing){playbackControls.composerPlaying=false;playbackControls.autoPlay=false;current.autoPlay=false;}
        if(controls.composerEnabled) {target=composerSample(playbackControls,position,tempo,playing,num,den);current=target;if(sample==0)instrument.configureResources(target);}
        auto output=instrument.next(current,position,num,den,controls.composerEnabled||(controls.midiPlayback&&!controls.modularMidi),splitMask);
        const double sceneGain=controls.composerEnabled?sceneTransitionGain:1.;output=output*sceneGain;
        const auto& stems=instrument.stemOutputs();
        const auto& returns=instrument.returnOutputs();
        const auto voices=instrument.activeTracks();
        for(int t=0;t<10;++t){const auto value=t<8?stems[size_t(t)]:returns[size_t(t-8)];peaks[size_t(t)]=std::max(peaks[size_t(t)],float(std::max(std::abs(value.l),std::abs(value.r))));
            if(t<8)active[size_t(t)]|=voices[size_t(t)];
            if(stemChannels[size_t(t)]>=0){audio.setSample(stemChannels[size_t(t)],sample,float(value.l*sceneGain));audio.setSample(stemChannels[size_t(t)]+1,sample,float(value.r*sceneGain));}}
        if(controls.clockSource==2&&midiClock.running&&midiClock.valid(clockSamples+sample))midiClock.beat+=increment;
        audio.setSample(0,sample,float(output.l));audio.setSample(1,sample,float(output.r));
        maximum=std::max(maximum,float(std::max(std::abs(output.l),std::abs(output.r))));
    }
    liveRecorder.push(audio);
    localPPQ=ppq+audio.getNumSamples()*increment;clockSamples+=audio.getNumSamples();midi.clear();
    tempoDisplay=tempo;beatDisplay=controls.clockSource==2?midiClock.beat:localPPQ;
    if(controls.clockSource==2)clockStatus=midiClock.valid(clockSamples)?1:midiClock.locked?3:2;
    for(int t=0;t<10;++t)channelPeak[size_t(t)]=std::max(peaks[size_t(t)],channelPeak[size_t(t)].load()*float(std::exp(-audio.getNumSamples()/(sr*.15))));
    for(int t=0;t<8;++t){if(inputs[size_t(t)])inputPulse[size_t(t)]=int(sr*.15);else inputPulse[size_t(t)]=std::max(0,inputPulse[size_t(t)].load()-audio.getNumSamples());activePulse[size_t(t)]=active[size_t(t)]?int(sr*.12):std::max(0,activePulse[size_t(t)].load()-audio.getNumSamples());}
    rootDisplay=instrument.currentRoot();peak=maximum;drumStep=instrument.drumPosition();arpNote=instrument.arpNoteDisplay();fxBytes=instrument.fxMemoryBytes();
}

void BassAmbientProcessor::getStateInformation(juce::MemoryBlock& output) {
    auto tree=state.copyState();tree.setProperty("editorScale",double(editorScale.load()),nullptr);tree.setProperty("schemaVersion",4,nullptr);
    tree.removeChild(tree.getChildWithName("Composer"),nullptr);tree.appendChild(jerzy::composer::toTree(composerDocument()),nullptr);
    juce::ValueTree mappings("MidiMappings");
    for(int cc=0;cc<128;++cc) {const int index=ccMap[size_t(cc)].load();if(index>=0&&index<int(hostParameters.size())) {juce::ValueTree item("CC");item.setProperty("number",cc,nullptr);item.setProperty("id",hostParameters[size_t(index)]->paramID,nullptr);mappings.appendChild(item,nullptr);}}
    tree.removeChild(tree.getChildWithName("MidiMappings"),nullptr);tree.appendChild(mappings,nullptr);
    if(auto xml=tree.createXml()) copyXmlToBinary(*xml,output);
}
void BassAmbientProcessor::setStateInformation(const void* data,int size) {
    restoredSession=true;
    if(auto xml=getXmlFromBinary(data,size)) if(xml->hasTagName(state.state.getType())) {
        auto tree=juce::ValueTree::fromXml(*xml);editorScale=float(tree.getProperty("editorScale",0.f));
        if(!tree.getChildWithProperty("id","modularMidi").isValid()){
            const bool parts=bool(tree.getChildWithProperty("id","midiPlayback").getProperty("value",false));
            const bool direct=bool(tree.getChildWithProperty("id","direct").getProperty("value",false));
            const char* ids[]{"modularMidi","performanceSource","bassMidiMode","padMidiMode","arpMidiMode","krellMidiMode","drumsMidiMode"};const int defaults[]{0,0,parts||direct?0:1,parts?0:1,parts?0:1,parts?0:1,0};
            for(int i=0;i<7;++i){juce::ValueTree child("PARAM");child.setProperty("id",ids[i],nullptr);child.setProperty("value",defaults[i],nullptr);tree.appendChild(child,nullptr);}
        }
        // Old sessions used a shared FX configuration: duplicate it to AMBIENT.
        if(int(tree.getProperty("schemaVersion",1))<2) {
            for(const auto& spec:parameterSpecs()) if(spec.id.startsWith("pad_")) {
                const auto source=tree.getChildWithProperty("id",spec.id.substring(4));
                auto copy=source.isValid()?source.createCopy():juce::ValueTree("PARAM");
                copy.setProperty("id",spec.id,nullptr);
                if(!source.isValid()) copy.setProperty("value",spec.initial,nullptr);
                tree.appendChild(copy,nullptr);
            }
            for(const auto& spec:parameterSpecs()) if(spec.id.startsWith("master_")||spec.id=="masterFX") {
                juce::ValueTree child("PARAM");child.setProperty("id",spec.id,nullptr);
                child.setProperty("value",spec.initial,nullptr);tree.appendChild(child,nullptr);
            }
        }
        if(auto mappings=tree.getChildWithName("MidiMappings");mappings.isValid()) {
            for(auto& mapping:ccMap)mapping.store(-1);
            for(const auto& item:mappings) {const int cc=int(item.getProperty("number",-1));const auto id=item.getProperty("id").toString();
                if(cc>=0&&cc<128&&cc!=64&&cc!=120&&cc!=123) for(size_t i=0;i<hostParameters.size();++i)if(hostParameters[i]->paramID==id)ccMap[size_t(cc)].store(int(i));
            }
        }
        if(auto song=tree.getChildWithName("Composer");song.isValid()) {try{auto data=jerzy::composer::fromTree(song);editComposer([&](auto& d){d=std::move(data);});}catch(const std::exception& e){const juce::ScopedLock lock(composerLock);composerFailure=e.what();}}
        state.replaceState(tree);controlSnapshotReset=true;resetRequested=true;
    }
}
void BassAmbientProcessor::applyPreset(int preset) {
    auto set=[&](const char* id,float v) {
        if(auto* parameter=state.getParameter(id)) { parameter->beginChangeGesture();parameter->setValueNotifyingHost(parameter->convertTo0to1(v));parameter->endChangeGesture(); }
    };
    // Explicit factory snapshots; all remaining controls return to defaults.
    const bool modern=readParameters().performanceSource>0;
    const juce::StringArray preferences{"autoPlay","composerEnabled","composerPlaying","composerSongMode","composerLoop","composerScene","midiPlayback","separateOutputs","clockSource","internalTempo","transportRun","harmonyLink","harmonyRoot","scale","autoHarmony","harmonyBars","meter","numerator","denominator"};
    for(const auto& s:parameterSpecs())if(!modern||(s.group!=26&&!preferences.contains(s.id)))set(s.id.toRawUTF8(),float(s.initial));
    if(preset==0) { set("style",0);set("model",2);set("cutoff",1800);set("density",.85f); }
    if(preset==1) { set("style",2);set("model",0);set("slide",.5f);set("resonance",.7f);set("cutoff",700);set("bassFX",.25f); }
    if(preset==2) { set("style",4);set("model",1);set("bassDecay",.8f);set("bassSustain",.65f);set("bassRelease",.3f);set("drive",.4f); }
    if(preset==3) { set("bass",0);set("pad",1);set("padMode",1);set("engine1",0);set("engine2",2);set("pad_reverbMix",.5f);set("padAttack",3);set("padRelease",9); }
    if(preset==4) { set("krellMin",.7f);set("krellMax",12);set("krellSpace",.4f);set("padAttack",1.4f);set("padRelease",4);set("padDetune",14); set("bass",0);set("pad",1);set("padMode",2);set("engine1",3);set("engine2",4);set("pad_fxGrain",1);set("pad_grainPitch",7);set("pad_damage",.35f);set("motion",.7f); }
    if(preset==5) { set("bass",1);set("pad",1);set("model",2);set("padLevel",.25f);set("padAttack",4);set("padRelease",8); }
    if(preset==6) {set("style",5);set("model",2);set("density",.8f);set("swing",.22f);set("fill",.35f);set("drums",1);set("arp",1);set("arpPulses",5);set("arpLevel",.22f);}
    if(preset==7) {set("bass",0);set("arp",1);set("arpModel",1);set("arpPattern",4);set("arpGateRandom",.7f);set("arpPitchRandom",.35f);set("arpPanMode",1);set("pad",1);set("padLevel",.2f);}
    if(preset==8) {set("bass",0);set("pad",1);set("padMode",2);set("engine1",2);set("engine2",3);set("padDetune",18);set("padShimmer",.5f);set("krellMax",18);set("padAttack",2);set("padRelease",8);set("masterFX",.4f);}
    if(preset==9){set("model",3);set("style",3);set("cutoff",3500);set("drive",.08f);set("sub",0);set("bassSustain",.75f);set("bassDecay",.6f);set("gate",.7f);set("swing",.12f);set("bassFX",.08f);}
    if(preset>=10&&preset<=13){set("model",3);set("style",float(preset));set("cutoff",preset==11?6000:3500);set("drive",preset==11?.3f:.08f);set("sub",0);set("bassSustain",.7f);set("gate",preset==11?.5f:.8f);set("guitarArticulation",preset==13?0:1);set("swing",preset==13?.6f:0);set("division",2);set("movement",.8f);set("density",1);}
    if(preset==14){set("bass",0);set("pad",0);set("arp",0);set("drums",0);set("krell",1);set("krellEngine",0);set("krellAttack",.4f);set("krellRelease",2);if(!modern)set("harmonyLink",1);}
    resetRequested=true;
}
BassAmbientProcessor::~BassAmbientProcessor() {stopResourceWorker();stopLiveRecording();delete activeComposer;delete pendingComposer.load();delete retiredComposer.load();}
void BassAmbientProcessor::stopResourceWorker() {stopWorker=true;if(resourceWorker.joinable())resourceWorker.join();}
void BassAmbientProcessor::releaseResources() {liveAudioReady=false;stopResourceWorker();stopLiveRecording();}
void BassAmbientProcessor::setParameterValue(const juce::String& id,float value) {
    if(auto* p=state.getParameter(id)) {p->beginChangeGesture();p->setValueNotifyingHost(p->convertTo0to1(value));p->endChangeGesture();}
}
void BassAmbientProcessor::learnMidi(const juce::String& id) {for(size_t i=0;i<hostParameters.size();++i)if(hostParameters[i]->paramID==id){learnParameter=int(i);learnCC=-1;return;}}
void BassAmbientProcessor::clearMidiMapping(const juce::String& id) {for(auto& mapping:ccMap){const int i=mapping.load();if(i>=0&&hostParameters[size_t(i)]->paramID==id)mapping=-1;}}
juce::String BassAmbientProcessor::midiAssignment(const juce::String& id) const {for(size_t cc=0;cc<ccMap.size();++cc){int i=ccMap[cc].load();if(i>=0&&hostParameters[size_t(i)]->paramID==id)return "CC "+juce::String(int(cc));}return "Unassigned";}
void BassAmbientProcessor::handleMappedController(int cc,int value,jerzy::Parameters& target) {
    if(cc==64||cc==120||cc==123)return;
    const int learned=learnParameter.exchange(-1);
    if(learned>=0) {for(auto& mapping:ccMap)if(mapping.load()==learned)mapping=-1;ccMap[size_t(cc)]=learned;learnCC=cc;}
    const int index=ccMap[size_t(cc)].load();
    if(index<0)queueLiveController(cc,value);
    if(index>=0&&index<int(hostParameters.size())) {auto* parameter=hostParameters[size_t(index)];parameter->setValueNotifyingHost(float(value)/127);
        if(target.performanceSource>0){if(parameter->paramID=="autoPlay"&&value>=64){setParameterValue("performanceSource",2);setParameterValue("modularMidi",0);setParameterValue("composerEnabled",0);}else if(parameter->paramID=="composerEnabled"){setParameterValue("performanceSource",value>=64?3:1);setParameterValue("modularMidi",value>=64?0:1);if(value>=64)setParameterValue("autoPlay",0);}}
        target=readParameters();}
}
juce::AudioProcessorEditor* BassAmbientProcessor::createEditor() { return new BassAmbientEditor(*this); }
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new BassAmbientProcessor(); }

void BassAmbientProcessor::transport(bool run){
    setParameterValue("transportRun",run?1:0);
    if(!run){liveQueuedScene=-1;liveRetrigger=false;setParameterValue("composerPlaying",0);setParameterValue("autoPlay",0);requestPanic();}
    else if(readParameters().composerEnabled)launchComposer(readParameters().composerScene-1,readParameters().composerSongMode);
    else if(readParameters().performanceSource!=1&&!readParameters().modularMidi)setParameterValue("autoPlay",1);
}
