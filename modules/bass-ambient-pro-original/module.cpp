#include "jerzy_module.h"
#include "OptimizedCore.h"
#include <thread>
#include <chrono>
struct State {
 jerzy_opt::Instrument synth;jerzy_opt::Parameters current;double sr,localBeat=0;int previousClock=-1,previousSource=-1;std::atomic<bool> stop{false};std::thread worker;
 State(double rate):sr(rate){current.bass=false;synth.prepare(sr);worker=std::thread([this]{while(!stop.load()){synth.serviceResources();std::this_thread::sleep_for(std::chrono::milliseconds(5));}});}
 ~State(){stop.store(true);if(worker.joinable())worker.join();}
};
static jerzy_opt::Parameters parameters(const float* v){jerzy_opt::Parameters p;constexpr int den[]{2,4,8,16};
#include "assign.inc"
 // The core implements MIDI and JAM; composer/file-export stays in VST.
 if(p.performanceSource==1){p.modularMidi=true;p.autoPlay=false;p.direct=p.bassMidiMode==0;}
 if(p.performanceSource==2){p.modularMidi=false;p.direct=false;}
 return p;
}
static void* create(double sr,uint32_t,const char*){try{return new State(sr);}catch(...){return nullptr;}}
static void destroy(void* p){delete static_cast<State*>(p);}
static void process(void* ptr,const JAProcess* b){auto& s=*static_cast<State*>(ptr);const auto p=parameters(b->parameters);if(s.previousSource!=p.performanceSource){if(s.previousSource>=0)s.synth.reset();s.previousSource=p.performanceSource;}if(s.previousClock!=p.clockSource){s.synth.allOff();s.localBeat=0;s.previousClock=p.clockSource;}const auto previous=s.current;s.current=p;
#include "continuous.inc"
 const double tempo=p.clockSource==1?b->bpm:p.internalTempo;double beat=p.clockSource==1?b->beat:s.localBeat;const double smoothing=1-std::exp(-1/(s.sr*.02));
 s.synth.configureResources(p);s.synth.beginBlock(beat,tempo,p.clockSource==1&&b->playing!=0);unsigned event=0;
 struct Ramp{double* current;const double* target;};std::array<Ramp,725> ramps{};unsigned rampCount=0;
 auto addRamp=[&](double& current,const double& target){if(std::abs(current-target)<=1e-14*std::max(1.,std::abs(target)))current=target;else ramps[rampCount++]={&current,&target};};
#include "ramps.inc"

 for(unsigned i=0;i<b->frames;++i){
  for(unsigned r=0;r<rampCount;++r){auto& c=*ramps[r].current;c+=(*ramps[r].target-c)*smoothing;}
  while(event<b->midi_count&&b->midi[event].frame<=i){const auto& e=b->midi[event++];if(e.size<3)continue;int status=e.bytes[0]&240,ch=(e.bytes[0]&15)+1;
   if(status==144&&e.bytes[2])s.synth.noteOn(e.bytes[1],ch,e.bytes[2]/127.,s.current,beat);
   else if(status==128||status==144)s.synth.noteOff(e.bytes[1],ch,s.current,beat);
   else if(status==176)s.synth.controller(ch,e.bytes[1],e.bytes[2],s.current,beat);
   else if(status==224)s.synth.pitchBend(ch,e.bytes[1]+128*e.bytes[2]);
  }
  auto y=s.synth.next(s.current,beat,s.current.numerator,s.current.denominator,false,0);b->output[0][i]=float(y.l);b->output[1][i]=float(y.r);beat+=tempo/(60*s.sr);
 }
 s.localBeat=beat;
}
static uint32_t latency(void*){return 0;}
extern "C" const JAModule* ja_module(){static const jerzy_opt::Parameters p;static const JAParameter metadata[]={
#include "metadata.inc"
};static const JAModule m{sizeof(JAModule),JA_ABI,"bass-ambient-pro-original","Jerzy Bass Ambient PRO — modalny DSP","0.3.1",1,uint32_t(sizeof(metadata)/sizeof(metadata[0])),metadata,create,destroy,process,latency};return &m;}
