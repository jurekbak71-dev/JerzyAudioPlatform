#include "jerzy_module.h"
#include "../modules/bass-ambient/OriginalCore.h"
#include <dlfcn.h>
#include <array>
#include <atomic>
#include <cassert>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <new>
#include <stdexcept>
#include <vector>
static bool realtime=false;static unsigned allocations=0,checks=0;
void* operator new(std::size_t n){if(realtime)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}void operator delete(void* p,std::size_t) noexcept{std::free(p);}
void check(bool ok,const char* msg){++checks;if(!ok)throw std::runtime_error(msg);}
struct Plugin {void* lib;const JAModule* api;void* instance;std::vector<float> values;
 Plugin(const std::filesystem::path& root,const std::string& id,double sr,const char* asset):lib(dlopen((root/id/(id+".so")).c_str(),RTLD_NOW)),api(nullptr),instance(nullptr){
  check(lib!=nullptr,"dlopen");api=reinterpret_cast<JAEntry>(dlsym(lib,"ja_module"))();check(api->abi==JA_ABI,"ABI");
  instance=api->create(sr,8192,asset);check(instance!=nullptr,"create");for(unsigned i=0;i<api->parameter_count;++i)values.push_back(api->parameters[i].initial);
 }
 ~Plugin(){api->destroy(instance);dlclose(lib);}
 unsigned index(const std::string& id){for(unsigned i=0;i<api->parameter_count;++i)if(id==api->parameters[i].id)return i;throw std::runtime_error("param not found");}
 void run(JAProcess& b){b.parameters=values.data();allocations=0;realtime=true;api->process(instance,&b);realtime=false;check(allocations==0,"allocation in DSP process");}
};
int main(int argc,char** argv){try{check(argc==2,"module directory required");const std::filesystem::path root=argv[1];
 auto asset=std::filesystem::temp_directory_path()/("jerzy-test-"+std::to_string(reinterpret_cast<uintptr_t>(&root))+".wav");
 {std::ofstream o(asset,std::ios::binary);auto u16=[&](uint16_t v){o.put(char(v));o.put(char(v>>8));};auto u32=[&](uint32_t v){u16(uint16_t(v));u16(uint16_t(v>>16));};o.write("RIFF",4);u32(164);o.write("WAVEfmt ",8);u32(16);u16(1);u16(1);u32(44100);u32(88200);u16(2);u16(16);o.write("data",4);u32(128);u16(16384);for(int i=1;i<64;++i)u16(0);}
 std::array<std::array<float,1024>,2> in{},out{};
 for(double sr:{44100.,48000.})for(const std::string id:{"utility-gain-meter","big-muff","tape-drive","bass-ambient","cab-ir"}){
  Plugin p(root,id,sr,asset.c_str());if(id=="bass-ambient"){p.values[p.index("bass")]=1;p.values[p.index("pad")]=1;}
  double energy=0;
  for(unsigned size:{64u,128u,256u,512u,1024u})for(unsigned block=0;block<20;++block){
   for(unsigned i=0;i<size;++i)in[0][i]=in[1][i]=.1f*std::sin(float((block*size+i)*6.28318530718*220/sr));
   JAProcess b{sizeof(JAProcess),size,sr,120,block*size*120/(60*sr),1,{in[0].data(),in[1].data()},{out[0].data(),out[1].data()},nullptr,nullptr,0};p.run(b);
   for(int c=0;c<2;++c)for(unsigned i=0;i<size;++i){check(std::isfinite(out[c][i]),"NaN/Inf audio");check(std::abs(out[c][i])<4,"runaway level");energy+=out[c][i]*out[c][i];}
  }
  check(energy>.0001,"module is silent");
  std::cout<<"PASS "<<id<<" @ "<<sr<<" Hz, 64..1024 frames\n";
 }
 // Sample comparison against the original DSP with identical settings and seed.
 for(double sr:{44100.,48000.}){
  Plugin plugin(root,"bass-ambient",sr,"");plugin.values[plugin.index("bass")]=1;plugin.values[plugin.index("pad")]=1;
  jerzy::Instrument original;original.prepare(sr);jerzy::Parameters params;params.pad=true;
  struct {jerzy::Parameters current;} s;
  const double smoothing=-std::expm1(-1/(sr*.02));
  // Match the original VST processor's continuous-parameter smoothing and float host values.
  {jerzy::Parameters p0; (void)p0;}
  const JAProcess targetBlock{sizeof(JAProcess),128,sr,120,0,1,{nullptr,nullptr},{nullptr,nullptr},plugin.values.data(),nullptr,0};
  jerzy::Parameters target;constexpr int den[]{2,4,8,16};
  {const JAProcess* b=&targetBlock;jerzy::Parameters p;
#include "../modules/bass-ambient/assign.inc"
   target=p;}
  params=target;
  double beat=0,error=0;float fade=0;original.noteOn(40,1,.76,params,0);
  for(unsigned block=0;block<200;++block){
   jerzy::Parameters p=target;auto previous=s.current;s.current=p;
#include "../modules/bass-ambient/continuous.inc"
   original.beginBlock(beat,120,true);JAProcess b{sizeof(JAProcess),128,sr,120,beat,1,{in[0].data(),in[1].data()},{out[0].data(),out[1].data()},nullptr,nullptr,0};plugin.run(b);
   for(unsigned i=0;i<128;++i){
#include "../modules/bass-ambient/smooth.inc"
    auto expected=original.next(s.current,beat);fade=std::min(1.f,fade+1.f/float(sr*.02));error=std::max(error,double(std::abs(float(expected.l)*fade-out[0][i])));error=std::max(error,double(std::abs(float(expected.r)*fade-out[1][i])));beat+=120/(60*sr);}
  }std::cout<<"comparison error="<<error<<std::endl;check(error<2e-6,"BassAmbient differs from original DSP");std::cout<<"PASS BassAmbient original comparison @ "<<sr<<", max error="<<error<<'\n';
  plugin.values[plugin.index("bass")]=plugin.values[plugin.index("pad")]=0;JAProcess b{sizeof(JAProcess),128,sr,120,beat,1,{in[0].data(),in[1].data()},{out[0].data(),out[1].data()},nullptr,nullptr,0};for(int tail=0;tail<12;++tail)plugin.run(b);for(int i=0;i<128;++i)check(out[0][i]==0&&out[1][i]==0,"stopped instrument synthesizes audio");
 }
 // Actual IR impulse response has gain .5 and latency 64 frames.
 {Plugin p(root,"cab-ir",44100,asset.c_str());in={};in[0][0]=in[1][0]=1;JAProcess b{sizeof(JAProcess),256,44100,120,0,1,{in[0].data(),in[1].data()},{out[0].data(),out[1].data()},nullptr,nullptr,0};p.run(b);for(int i=0;i<256;++i)check(std::abs(out[0][i]-(i==64?.5f:0.f))<1e-5,"IR impulse mismatch");check(p.api->latency(p.instance)==64,"latency report");}
 // Added CAB controls: latency-aligned dry mix and inverted IR polarity.
 {Plugin dry(root,"cab-ir",44100,asset.c_str()),wet(root,"cab-ir",44100,asset.c_str());dry.values[1]=0;wet.values[2]=1;in={};
  JAProcess b{sizeof(JAProcess),256,44100,120,0,1,{in[0].data(),in[1].data()},{out[0].data(),out[1].data()},nullptr,nullptr,0};for(int block=0;block<60;++block){dry.run(b);wet.run(b);}
  in[0][0]=in[1][0]=1;dry.run(b);for(int i=0;i<256;++i)check(std::abs(out[0][i]-(i==64?1.f:0.f))<1e-5,"CAB dry mix latency mismatch");wet.run(b);for(int i=0;i<256;++i)check(std::abs(out[0][i]-(i==64?-.5f:0.f))<2e-5,"CAB polarity mismatch");
 }
 // Every fuzz/tape parameter must change the rendered signal, not just metadata.
 for(std::string id:{"big-muff","tape-drive"})for(unsigned parameter=0;parameter<3;++parameter){double difference=0;
  Plugin a(root,id,48000,""),b(root,id,48000,"");a.values[parameter]=.1;b.values[parameter]=.9;
  std::array<std::array<float,1024>,2> other{};
  for(int block=0;block<30;++block){for(unsigned i=0;i<1024;++i)in[0][i]=in[1][i]=.08f*(std::sin(float((block*1024+i)*.03))+.3f*std::sin(float((block*1024+i)*.17)));
   JAProcess x{sizeof(JAProcess),1024,48000,120,0,1,{in[0].data(),in[1].data()},{out[0].data(),out[1].data()},nullptr,nullptr,0};a.run(x);x.output[0]=other[0].data();x.output[1]=other[1].data();b.run(x);if(block>10)for(unsigned i=0;i<1024;++i)difference+=std::abs(out[0][i]-other[0][i]);
  }check(difference>1,"effect parameter has no audible signal effect");
 }
 std::filesystem::remove(asset);std::cout<<"PASS "<<checks<<" checks\n";return 0;
 }catch(const std::exception& ex){realtime=false;std::cerr<<"FAIL "<<ex.what()<<'\n';return 1;}}
