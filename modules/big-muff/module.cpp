#include "jerzy_module.h"
#include <algorithm>
#include <cmath>
// Four gain stages, two diode feedback clipping stages, DC coupling,
// parallel lowpass/highpass tone network. Not a component-accurate emulation.
struct Channel { double coupling[4]{},clipLP[2]{},low=0,high=0,dc=0; };
struct State { Channel channel[2]; double sr; float sustain=.5,tone=.5,level=.25; };
static void* create(double sr,uint32_t,const char*) { return new State{{},sr}; }
static void destroy(void* s){delete static_cast<State*>(s);}
static double lowpass(double x,double& z,double hz,double sr){z+=(x-z)*(-std::expm1(-6.28318530718*hz/sr));return z;}
static void process(void* ptr,const JAProcess* b){
 auto& s=*static_cast<State*>(ptr);
 for(uint32_t i=0;i<b->frames;++i){
  s.sustain+=(b->parameters[0]-s.sustain)*.002; s.tone+=(b->parameters[1]-s.tone)*.002;
  s.level+=(b->parameters[2]-s.level)*.002;
  for(int c=0;c<2;++c){auto& z=s.channel[c];double x=b->input[c][i];
   x=(x-lowpass(x,z.coupling[0],30,s.sr))*(2+12*s.sustain);
   for(int k=0;k<2;++k){
    x-=lowpass(x,z.coupling[k+1],35,s.sr);
    x=lowpass(x,z.clipLP[k],std::min(9000.,s.sr*.2),s.sr);
    // Diode feedback approximation solved by bounded Newton iterations.
    double a=x*(3+9*s.sustain),y=std::clamp(a,-1.,1.);
    for(int n=0;n<6;++n){double v=std::clamp(3*y,-12.,12.);y-=(y+.15*std::sinh(v)-a)/(1+.45*std::cosh(v));}
    x=y;
   }
   double lo=lowpass(x,z.low,650,s.sr),hi=x-lowpass(x,z.high,1700,s.sr);
   x=2*((1-s.tone)*lo+s.tone*hi);
   x-=lowpass(x,z.dc,12,s.sr);
   b->output[c][i]=float(x*s.level*.55);
  }
 }
}
static uint32_t latency(void*){return 0;}
static const JAParameter params[]={{"sustain","Sustain","","",0,1,.5,0},{"tone","Barwa","","",0,1,.5,0},{"level","Poziom","","",0,1,.25,0}};
extern "C" const JAModule* ja_module(){static const JAModule m{sizeof(JAModule),JA_ABI,"big-muff","Jerzy Fuzz typu Big Muff","0.1.0",0,3,params,create,destroy,process,latency};return &m;}
