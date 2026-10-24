#include "jerzy_module.h"
#include <cmath>
struct State { float gain=1; };
static void* create(double,uint32_t,const char*) { return new State; }
static void destroy(void* s) { delete static_cast<State*>(s); }
static void process(void* s,const JAProcess* b) {
 auto& x=*static_cast<State*>(s);
 float target=std::pow(10.f,b->parameters[0]/20.f);
 for(uint32_t i=0;i<b->frames;++i){ x.gain+=(target-x.gain)*float(1-std::exp(-1/(.01*b->sample_rate)));
  for(int c=0;c<2;++c)b->output[c][i]=b->input[c][i]*x.gain;
 }
}
static uint32_t latency(void*){return 0;}
static const JAParameter params[]={{"gain","Poziom","dB","",-60,12,0,0}};
extern "C" const JAModule* ja_module(){static const JAModule m{sizeof(JAModule),JA_ABI,"utility-gain-meter","Poziom sygnału","0.1.0",0,1,params,create,destroy,process,latency};return &m;}
