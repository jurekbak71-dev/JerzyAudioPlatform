#include "jerzy_module.h"
#include <cmath>
struct State { double sr,low[2]{},memory[2]{},dc[2]{};float drive=.35,tone=.5,level=.5; };
static void* create(double sr,uint32_t,const char*) { return new State{sr}; }
static void destroy(void* s){delete static_cast<State*>(s);}
static void process(void* ptr,const JAProcess* b){auto& s=*static_cast<State*>(ptr);
 for(uint32_t i=0;i<b->frames;++i){s.drive+=(b->parameters[0]-s.drive)*.002;s.tone+=(b->parameters[1]-s.tone)*.002;s.level+=(b->parameters[2]-s.level)*.002;
  double drive=1+15*s.drive,alpha=-std::expm1(-6.28318530718*(2500+9000*s.tone)/s.sr);
  for(int c=0;c<2;++c){double x=b->input[c][i];s.low[c]+=(x-s.low[c])*alpha;
   double y=std::tanh((s.low[c]+.04*s.memory[c])*drive)/std::sqrt(drive);
   s.memory[c]+=(y-s.memory[c])*.08;s.dc[c]+=(y-s.dc[c])*(-std::expm1(-6.28318530718*8/s.sr));
   b->output[c][i]=float((y-s.dc[c])*(s.level*2));
  }
 }
}
static uint32_t latency(void*){return 0;}
static const JAParameter params[]={{"drive","Nasycenie","","",0,1,.35,0},{"tone","Barwa","","",0,1,.5,0},{"level","Poziom","","",0,1,.5,0}};
extern "C" const JAModule* ja_module(){static const JAModule m{sizeof(JAModule),JA_ABI,"tape-drive","Jerzy Tape Drive","0.1.0",0,3,params,create,destroy,process,latency};return &m;}
