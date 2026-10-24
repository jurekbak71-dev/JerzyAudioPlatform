#include "original_compare.h"
#include "../modules/bass-ambient-pro-original/vendor/Core.h"
#include "reference_pro_parameters.h"
#include "../modules/bass-ambient-pro-original/module.cpp"
static std::vector<float> snapshot(const jerzy::Parameters& p){const JAParameter fields[]={
#include "../modules/bass-ambient-pro-original/metadata.inc"
};std::vector<float> out;for(const auto& f:fields)out.push_back(f.initial);out.push_back(float(p.bass));out.push_back(float(p.denominator));return out;}
int main(int argc,char** argv){try{require(argc==2,"module path");double maximum=0,energy=0;uint64_t samples=0;auto started=std::chrono::steady_clock::now();
 for(double sr:{44100.,48000.}){
  Loaded m(argv[1],"bass-ambient-pro-original",sr);require(m.parameters.size()==725,"complete PRO parameter count");// Every parameter ID is wired independently against the original VST reader.
  for(unsigned index=0;index<m.parameters.size();++index){
   if(std::string(m.api->parameters[index].id)=="performanceSource")continue;
   const auto before=m.parameters[index];const auto& spec=m.api->parameters[index];
   for(float value:{spec.minimum,spec.maximum}){m.parameters[index]=value;require(snapshot(parameters(m.parameters.data()))==snapshot(referenceParameters(m.parameters.data())),"PRO parameter wiring differs from VST reader");}m.parameters[index]=before;
  }
  jerzy::Instrument reference;reference.prepare(sr);jerzy::Parameters current;current.bass=false;
  m.parameters[m.index("fxEnabled")]=0;m.parameters[m.index("autoPlay")]=1;m.parameters[m.index("direct")]=1;
  m.parameters[m.index("bass")]=1;m.parameters[m.index("bassBody")]=.6;m.parameters[m.index("bassAttackTransient")]=.5;
  std::array<std::array<float,1024>,2> in{},out{};uint64_t cursor=0;
  for(int part=0;part<5;++part){
   for(auto key:{"bass","pad","arp","drums","krell"})m.parameters[m.index(key)]=0;
   const char* keys[]{"bass","pad","arp","drums","krell"};m.parameters[m.index(keys[part])]=1;
   m.parameters[m.index("padBody")]=.4;m.parameters[m.index("padAttackTransient")]=.3;
   for(unsigned n:{64u,128u,256u,512u,1024u})for(int iteration=0;iteration<5;++iteration){
    m.parameters[m.index("autoPlay")]=iteration<2?1.f:0.f;m.parameters[m.index("modularMidi")]=iteration<2?0.f:1.f;
    m.parameters[m.index("bassMidiMode")]=0;m.parameters[m.index("padMidiMode")]=0;m.parameters[m.index("arpMidiMode")]=0;m.parameters[m.index("krellMidiMode")]=0;
    auto target=referenceParameters(m.parameters.data());auto previous=current;current=target;
#define FLOAT(f,a,b,s,l,g) current.f=previous.f;
#define BOOL(f,l,g)
#define INT(f,a,b,l,g)
#define CHOICE(f,l,g,c)
#define CHOICE_DEN(f,l,g)
#include "../modules/bass-ambient-pro-original/vendor/Parameters.def"
#undef FLOAT
#undef BOOL
#undef INT
#undef CHOICE
#undef CHOICE_DEN
    current.bassBody=previous.bassBody;current.bassAttackTransient=previous.bassAttackTransient;current.padBody=previous.padBody;current.padAttackTransient=previous.padAttackTransient;
    const double tempo=target.internalTempo;double beat=double(cursor)*tempo/(60*sr);reference.configureResources(target);reference.beginBlock(beat,tempo,true);
    const unsigned ch=std::array<unsigned,5>{1,2,3,10,4}[part];
    const JAMidi midi[]={{0,3,{uint8_t(0x90+ch-1),60,90}},{8,3,{uint8_t(0xe0+ch-1),0,65}},{16,3,{uint8_t(0xb0+ch-1),64,0}},{32,3,{uint8_t(0x80+ch-1),60,0}}};
    unsigned event=0;
    JAProcess b{sizeof(JAProcess),n,sr,120,beat,1,{in[0].data(),in[1].data()},{out[0].data(),out[1].data()},nullptr,midi,iteration<2?0u:4u};m.process(b);
    const double smoothing=1-std::exp(-1/(sr*.02));
    for(unsigned i=0;i<n;++i){
#define FLOAT(f,a,b,s,l,g) current.f+=(target.f-current.f)*smoothing;
#define BOOL(f,l,g)
#define INT(f,a,b,l,g)
#define CHOICE(f,l,g,c)
#define CHOICE_DEN(f,l,g)
#include "../modules/bass-ambient-pro-original/vendor/Parameters.def"
#undef FLOAT
#undef BOOL
#undef INT
#undef CHOICE
#undef CHOICE_DEN
     current.bassBody+=(target.bassBody-current.bassBody)*smoothing;current.bassAttackTransient+=(target.bassAttackTransient-current.bassAttackTransient)*smoothing;current.padBody+=(target.padBody-current.padBody)*smoothing;current.padAttackTransient+=(target.padAttackTransient-current.padAttackTransient)*smoothing;
     while(event<b.midi_count&&midi[event].frame<=i){const auto& e=midi[event++];int status=e.bytes[0]&240,channel=(e.bytes[0]&15)+1;
      if(status==144)reference.noteOn(e.bytes[1],channel,e.bytes[2]/127.,current,beat);
      else if(status==128)reference.noteOff(e.bytes[1],channel,current,beat);
      else if(status==176)reference.controller(channel,e.bytes[1],e.bytes[2],current,beat);
      else if(status==224)reference.pitchBend(channel,e.bytes[1]+128*e.bytes[2]);
     }
     auto y=reference.next(current,beat,current.numerator,current.denominator,false,0);float expected[]{float(y.l),float(y.r)};
     for(int c=0;c<2;++c){require(std::isfinite(out[c][i]),"nonfinite PRO");maximum=std::max(maximum,double(std::abs(out[c][i]-expected[c])));energy+=std::abs(out[c][i]);++samples;}beat+=tempo/(60*sr);
    }cursor+=n;
   }
  }
 }
 // Resource-managed PRO FX must remain allocation-free on the callback
 // while the original resource worker allocates and retires rack buffers.
 {
  Loaded fx(argv[1],"bass-ambient-pro-original",44100);for(auto key:{"bass","pad","arp","drums","krell","autoPlay"})fx.parameters[fx.index(key)]=1;
  for(auto key:{"bassFX","padFX","arpFX","drumsFX","krellFX","masterFX"})fx.parameters[fx.index(key)]=.2f;
  std::array<std::array<float,128>,2> in{},out{};
  for(unsigned cycle=0;cycle<8;++cycle){fx.parameters[fx.index("fxEnabled")]=float(cycle%2);
   for(unsigned block=0;block<3;++block){JAProcess p{sizeof(JAProcess),128,44100,120,double(cycle*384+block*128)*120/(60*44100),1,{in[0].data(),in[1].data()},{out[0].data(),out[1].data()},nullptr,nullptr,0};fx.process(p);for(const auto& c:out)for(float value:c)require(std::isfinite(value)&&std::abs(value)<4,"PRO resource switching invalid audio");std::this_thread::sleep_for(std::chrono::milliseconds(10));}
  }
 }
 require(energy>.01,"silent PRO test");require(maximum<1e-7,"PRO DSP differs");std::cout<<"{\"module\":\"bass-ambient-pro-original\",\"samples\":"<<samples<<",\"max_error\":"<<maximum<<",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()<<"}\n";return 0;
 }catch(const std::exception& e){rt=false;std::cerr<<e.what()<<'\n';return 1;}}
