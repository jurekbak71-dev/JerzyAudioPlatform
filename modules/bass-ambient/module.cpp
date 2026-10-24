#include "jerzy_module.h"
#include "OriginalCore.h"
struct State {jerzy::Instrument synth;jerzy::Parameters current,lastPlaying;float fade=0;double sr;int root=-1;bool active=false;double beat=0;};
static void* create(double sr,uint32_t,const char*){auto* s=new State;s->sr=sr;s->synth.prepare(sr);s->current.bass=false;s->current.pad=false;return s;}
static void destroy(void* s){delete static_cast<State*>(s);}
static void process(void* ptr,const JAProcess* b){auto& s=*static_cast<State*>(ptr);jerzy::Parameters p;constexpr int den[]{2,4,8,16};
#include "assign.inc"
 const auto previous=s.current;s.current=p;
#include "continuous.inc"
 const int root=int(b->parameters[176]);
 const double tempo=b->parameters[178]>.5?b->bpm:b->parameters[177];
 if(!p.bass&&!p.pad){
  for(uint32_t i=0;i<b->frames;++i){
   if(s.fade>0){auto y=s.synth.next(s.lastPlaying,s.beat);s.fade=std::max(0.f,s.fade-1.f/float(s.sr*.02));b->output[0][i]=float(y.l)*s.fade;b->output[1][i]=float(y.r)*s.fade;s.beat+=tempo/(60*s.sr);}
   else {if(s.active){s.synth.allOff();s.active=false;}b->output[0][i]=b->output[1][i]=0;}
  }
  return;
 }
 s.synth.beginBlock(s.beat,tempo,b->playing!=0);
 if(!s.active||root!=s.root){s.synth.allOff();s.synth.noteOn(root,1,.76,p,s.beat);s.root=root;s.active=true;}
 const double smoothing=-std::expm1(-1/(s.sr*.02));uint32_t event=0;
 for(uint32_t i=0;i<b->frames;++i){
#include "smooth.inc"
  while(event<b->midi_count&&b->midi[event].frame<=i){const auto& e=b->midi[event++];int status=e.bytes[0]&240,ch=(e.bytes[0]&15)+1;
   if(e.size>=3){if(status==144&&e.bytes[2])s.synth.noteOn(e.bytes[1],ch,e.bytes[2]/127.,s.current,s.beat);
    if(status==128||(status==144&&!e.bytes[2]))s.synth.noteOff(e.bytes[1],ch,s.current,s.beat);
    if(status==176)s.synth.controller(ch,e.bytes[1],e.bytes[2],s.current,s.beat);
    if(status==224)s.synth.pitchBend(ch,e.bytes[1]+128*e.bytes[2]);}
  }
  s.fade=std::min(1.f,s.fade+1.f/float(s.sr*.02));const auto y=s.synth.next(s.current,s.beat);b->output[0][i]=float(y.l)*s.fade;b->output[1][i]=float(y.r)*s.fade;s.beat+=tempo/(60*s.sr);
 }
 s.lastPlaying=s.current;
}
static uint32_t latency(void*){return 0;}
extern "C" const JAModule* ja_module(){
 static const jerzy::Parameters p;
 static const JAParameter params[]={
#include "metadata.inc"
 };
 static const JAModule m{sizeof(JAModule),JA_ABI,"bass-ambient","Jerzy BassAmbient","0.1.0",1,uint32_t(sizeof(params)/sizeof(params[0])),params,create,destroy,process,latency};return &m;
}
