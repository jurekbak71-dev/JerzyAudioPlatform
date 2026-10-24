#include "jerzy_module.h"
#include "convolution.h"
struct State {std::unique_ptr<mfx4::CabinetIR> ir;float gain=1,mix=1,polarity=1;std::array<std::array<float,64>,2> dry{};unsigned cursor=0;};
static void* create(double sr,uint32_t,const char* asset){if(!asset||!*asset)return nullptr;std::string error;auto ir=mfx4::CabinetIR::load(asset,sr,error);if(!ir)return nullptr;return new State{std::move(ir)};}
static void destroy(void* s){delete static_cast<State*>(s);}
static void process(void* ptr,const JAProcess* b){auto& s=*static_cast<State*>(ptr);
 for(uint32_t i=0;i<b->frames;++i){float x[]{b->input[0][i],b->input[1][i]},y[2]{};s.ir->tick(x,y);s.gain+=(b->parameters[0]-s.gain)*.002;s.mix+=(b->parameters[1]-s.mix)*.002;s.polarity+=((b->parameters[2]>.5f?-1.f:1.f)-s.polarity)*.002;
  for(int c=0;c<2;++c){float dry=s.dry[c][s.cursor];s.dry[c][s.cursor]=x[c];const float wet=y[c]*s.polarity;b->output[c][i]=(dry+(wet-dry)*s.mix)*s.gain;}s.cursor=(s.cursor+1)%64;
 }
}
static uint32_t latency(void*){return 64;}
static const JAParameter params[]={{"level","Głośność IR","","",0,2,1,0},{"mix","Udział IR","","",0,1,1,0},{"polarity","Odwrócenie polaryzacji","","",0,1,0,1}};
extern "C" const JAModule* ja_module(){static const JAModule m{sizeof(JAModule),JA_ABI,"cab-ir","Jerzy CAB / IR","0.2.1",0,3,params,create,destroy,process,latency};return &m;}
