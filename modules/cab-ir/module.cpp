#include "jerzy_module.h"
#include "convolution.h"
struct State { std::unique_ptr<mfx4::CabinetIR> ir; float gain=1; };
static void* create(double sr,uint32_t,const char* asset){
 if(!asset||!*asset)return nullptr;
 std::string error;auto ir=mfx4::CabinetIR::load(asset,sr,error);if(!ir)return nullptr;
 return new State{std::move(ir)};
}
static void destroy(void* s){delete static_cast<State*>(s);}
static void process(void* ptr,const JAProcess* b){auto& s=*static_cast<State*>(ptr);
 for(uint32_t i=0;i<b->frames;++i){float x[]{b->input[0][i],b->input[1][i]},y[2]{};s.ir->tick(x,y);
  s.gain+=(b->parameters[0]-s.gain)*.002;for(int c=0;c<2;++c)b->output[c][i]=y[c]*s.gain;
 }
}
static uint32_t latency(void*){return 64;}
static const JAParameter params[]={{"level","Poziom","","",0,2,1,0}};
extern "C" const JAModule* ja_module(){static const JAModule m{sizeof(JAModule),JA_ABI,"cab-ir","Jerzy CAB / IR","0.1.0",0,1,params,create,destroy,process,latency};return &m;}
