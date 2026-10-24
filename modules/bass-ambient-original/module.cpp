#include "jerzy_module.h"
#include <memory>
#include "vendor/Core.h"
struct State {jerzy::Instrument synth;jerzy::Parameters current;double sr=44100,localBeat=0;int root=-1;bool autoActive=false;};
static void* create(double sr,uint32_t,const char*){try{auto s=std::make_unique<State>();s->sr=sr;s->synth.prepare(sr);s->current.bass=false;s->current.pad=false;return s.release();}catch(...){return nullptr;}}
static void destroy(void* s){delete static_cast<State*>(s);}
static void process(void* ptr,const JAProcess* b){auto& s=*static_cast<State*>(ptr);jerzy::Parameters p;constexpr int den[]{2,4,8,16};
#include "assign.inc"
 auto previous=s.current;s.current=p;
#include "continuous.inc"
 const bool sync=b->parameters[178]>.5,automatic=b->parameters[179]>.5;
 const double tempo=sync?b->bpm:b->parameters[177];double beat=sync&&b->playing?b->beat:s.localBeat;
 s.synth.beginBlock(beat,tempo,b->playing!=0);
 const int root=int(b->parameters[176]);
 if(automatic&&b->playing&&(p.bass||p.pad)){if(!s.autoActive||s.root!=root){s.synth.allOff();s.synth.noteOn(root,1,.76,p,beat);s.root=root;s.autoActive=true;}}
 else if(s.autoActive){s.synth.allOff();s.autoActive=false;}
 const double smoothing=1-std::exp(-1/(s.sr*.02));uint32_t event=0;
 for(uint32_t i=0;i<b->frames;++i){
#include "smooth.inc"
  while(event<b->midi_count&&b->midi[event].frame<=i){const auto& e=b->midi[event++];if(e.size<3)continue;int status=e.bytes[0]&240,ch=(e.bytes[0]&15)+1;
   if(status==144&&e.bytes[2])s.synth.noteOn(e.bytes[1],ch,e.bytes[2]/127.,s.current,beat);
   else if(status==128||status==144)s.synth.noteOff(e.bytes[1],ch,s.current,beat);
   else if(status==176)s.synth.controller(ch,e.bytes[1],e.bytes[2],s.current,beat);
   else if(status==224)s.synth.pitchBend(ch,e.bytes[1]+128*e.bytes[2]);
  }
  auto y=s.synth.next(s.current,beat);b->output[0][i]=float(y.l);b->output[1][i]=float(y.r);beat+=tempo/(60*s.sr);
 }
 s.localBeat=beat;
}
static uint32_t latency(void*){return 0;}
extern "C" const JAModule* ja_module(){static const jerzy::Parameters p;static const JAParameter params[]={
#include "metadata.inc"
};static const JAModule m{sizeof(JAModule),JA_ABI,"bass-ambient-original","Jerzy BassAmbient — oryginalny DSP","0.2.0",1,uint32_t(sizeof(params)/sizeof(params[0])),params,create,destroy,process,latency};return &m;}
