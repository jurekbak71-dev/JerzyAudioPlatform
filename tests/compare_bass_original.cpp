#include "original_compare.h"
#include "../modules/bass-ambient-original/vendor/Core.h"
static jerzy::Parameters read(Loaded& m){jerzy::Parameters p;auto get=[&](const char* id){return m.parameters[m.index(id)];};
#define BOOL(f,l,g) p.f=get(#f)>.5f;
#define FLOAT(f,a,b,s,l,g) p.f=get(#f);
#define INT(f,a,b,l,g) p.f=int(std::lround(get(#f)));
#define CHOICE(f,l,g,c) p.f=int(std::lround(get(#f)));
#define CHOICE_DEN(f,l,g) {constexpr int d[]{2,4,8,16};p.f=d[std::clamp(int(get(#f)),0,3)];}
#include "../modules/bass-ambient-original/vendor/Parameters.def"
#undef BOOL
#undef FLOAT
#undef INT
#undef CHOICE
#undef CHOICE_DEN
 for(int i=0;i<6;++i)p.order[i]=int(get(("order"+std::to_string(i)).c_str()));
 for(int index=0;index<2;++index){auto& rack=index==0?p.padRack:p.masterRack;const std::string prefix=index==0?"pad_":"master_";
#define BOOL(f,l,g) rack.f=get((prefix+#f).c_str())>.5f;
#define FLOAT(f,a,b,s,l,g) rack.f=get((prefix+#f).c_str());
#define CHOICE(f,l,g,c) rack.f=int(std::lround(get((prefix+#f).c_str())));
#include "../modules/bass-ambient-original/vendor/FXParameters.def"
#undef BOOL
#undef FLOAT
#undef CHOICE
 for(int i=0;i<6;++i)rack.order[i]=int(get((prefix+"order"+std::to_string(i)).c_str()));}
 p.masterFX=get("masterFX");return p;}
static void adopt(jerzy::Parameters& current,const jerzy::Parameters& target){auto previous=current;current=target;
#define BOOL(f,l,g)
#define FLOAT(f,a,b,s,l,g) current.f=previous.f;
#define INT(f,a,b,l,g)
#define CHOICE(f,l,g,c)
#define CHOICE_DEN(f,l,g)
#include "../modules/bass-ambient-original/vendor/Parameters.def"
#undef BOOL
#undef FLOAT
#undef INT
#undef CHOICE
#undef CHOICE_DEN
 for(int i=0;i<2;++i){auto& c=i==0?current.padRack:current.masterRack;const auto& old=i==0?previous.padRack:previous.masterRack;
#define BOOL(f,l,g)
#define FLOAT(f,a,b,s,l,g) c.f=old.f;
#define CHOICE(f,l,g,c)
#include "../modules/bass-ambient-original/vendor/FXParameters.def"
#undef BOOL
#undef FLOAT
#undef CHOICE
 }current.masterFX=previous.masterFX;
}
static void smooth(jerzy::Parameters& current,const jerzy::Parameters& target,double factor){
#define BOOL(f,l,g)
#define FLOAT(f,a,b,s,l,g) current.f+=(target.f-current.f)*factor;
#define INT(f,a,b,l,g)
#define CHOICE(f,l,g,c)
#define CHOICE_DEN(f,l,g)
#include "../modules/bass-ambient-original/vendor/Parameters.def"
#undef BOOL
#undef FLOAT
#undef INT
#undef CHOICE
#undef CHOICE_DEN
 for(int i=0;i<2;++i){auto& c=i==0?current.padRack:current.masterRack;const auto& t=i==0?target.padRack:target.masterRack;
#define BOOL(f,l,g)
#define FLOAT(f,a,b,s,l,g) c.f+=(t.f-c.f)*factor;
#define CHOICE(f,l,g,c)
#include "../modules/bass-ambient-original/vendor/FXParameters.def"
#undef BOOL
#undef FLOAT
#undef CHOICE
 }current.masterFX+=(target.masterFX-current.masterFX)*factor;
}
int main(int argc,char** argv){try{require(argc==2,"module path");double maximum=0,energy=0;uint64_t samples=0;auto started=std::chrono::steady_clock::now();
 for(double sr:{44100.,48000.}){Loaded m(argv[1],"bass-ambient-original",sr);require(m.parameters.size()==180,"missing BassAmbient controls");m.parameters[m.index("auto_root")]=0;m.parameters[m.index("bass")]=1;m.parameters[m.index("pad")]=1;m.parameters[m.index("padAttack")]=.05f;m.parameters[m.index("evolution")]=.5f;
  jerzy::Instrument reference;reference.prepare(sr);jerzy::Parameters current;current.bass=false;current.pad=false;double beat=0;std::array<std::array<float,1024>,2> out{},input{};
  for(unsigned block=0;block<240;++block){unsigned n=std::array<unsigned,5>{64,128,256,512,1024}[block%5];double bpm=block<120?123:87;
   if(block%20==0){m.parameters[m.index("model")]=float((block/20)%3);m.parameters[m.index("style")]=float((block/20)%5);m.parameters[m.index("scale")]=float((block/20)%5);m.parameters[m.index("padMode")]=float((block/20)%3);m.parameters[m.index("engine1")]=float((block/20)%5);m.parameters[m.index("engine2")]=float(((block/20)+1)%5);m.parameters[m.index("seed")]=float(71+block);}
   if(block==80)m.parameters[m.index("direct")]=1;if(block==160)m.parameters[m.index("direct")]=0;
   if(block==180){m.parameters[m.index("pad_fxGrain")]=1;m.parameters[m.index("masterFX")]=.4f;}
   auto target=read(m);adopt(current,target);reference.beginBlock(beat,bpm,true);
   std::array<JAMidi,3> midi{};unsigned count=0;
   if(block%20==0){midi[0]={0,3,{0x90,uint8_t(36+(block/20)%12),100}};count=1;}
   if(block%20==15){midi[0]={unsigned(n/2),3,{0xb0,64,127}};midi[1]={unsigned(n/2+1),3,{0x80,uint8_t(36+((block-15)/20)%12),0}};midi[2]={n-1,3,{0xb0,64,0}};count=3;}
   JAProcess b{sizeof(JAProcess),n,sr,bpm,beat,1,{input[0].data(),input[1].data()},{out[0].data(),out[1].data()},nullptr,midi.data(),count};m.process(b);
   unsigned event=0;double position=beat;const double factor=1-std::exp(-1/(sr*.02));
   for(unsigned i=0;i<n;++i){smooth(current,target,factor);while(event<count&&midi[event].frame<=i){auto e=midi[event++];int status=e.bytes[0]&240,ch=(e.bytes[0]&15)+1;if(status==144)reference.noteOn(e.bytes[1],ch,e.bytes[2]/127.,current,position);else if(status==128)reference.noteOff(e.bytes[1],ch,current,position);else if(status==176)reference.controller(ch,e.bytes[1],e.bytes[2],current,position);}
    auto y=reference.next(current,position);const float expected[]{float(y.l),float(y.r)};for(int c=0;c<2;++c){require(std::isfinite(out[c][i]),"nonfinite BassAmbient");maximum=std::max(maximum,double(std::abs(out[c][i]-expected[c])));energy+=std::abs(out[c][i]);++samples;}position+=bpm/(60*sr);
   }beat=position;
  }
 }
 require(energy>.1,"silent BassAmbient");require(maximum<1e-7,"BassAmbient original processor mismatch");std::cout<<"{\"module\":\"bass-ambient-original\",\"samples\":"<<samples<<",\"max_error\":"<<maximum<<",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()<<"}\n";return 0;
 }catch(const std::exception& e){rt=false;std::cerr<<e.what()<<'\n';return 1;}}
