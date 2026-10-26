#include "../core/lv2_host.h"
#include <iostream>
#include <unistd.h>
static thread_local bool realtime=false;
void* operator new(std::size_t size){if(realtime)throw std::runtime_error("allocation on audio callback");if(auto p=std::malloc(size))return p;throw std::bad_alloc();}
void operator delete(void* p)noexcept{std::free(p);}void operator delete(void* p,std::size_t)noexcept{std::free(p);}
void require(bool ok,const char* what){if(!ok)throw std::runtime_error(what);}
int main(){try{auto list=jerzy_lv2::catalog();require(list.find("urn:jerzy:test:gain")!=std::string::npos,"discovery");require(list.find("urn:jerzy:not-supported")!=std::string::npos,"required feature diagnosis");
 for(double sr:{44100.,48000.}){for(auto uri:{"urn:jerzy:test:gain","urn:jerzy:test:synth","urn:jerzy:test:worker"}){auto p=std::make_unique<jerzy_lv2::Plugin>(uri,sr,8192);if(std::strstr(uri,"worker")){require(p->enumeration(0),"enumeration metadata");require(p->normalize(0,.7f)==.5f,"CC snaps to noncontiguous scale points");}
 std::array<float,1024> left{},right{},outL{},outR{};left.fill(.1f);right.fill(.3f);float value=.5f;JAMidi on{8,3,{144,69,100}},off{16,3,{128,69,0}};
 for(unsigned frames:{64u,128u,256u,512u,1024u}){JAProcess b{sizeof(JAProcess),frames,sr,120,0,1,{left.data(),right.data()},{outL.data(),outR.data()},&value,&on,1};realtime=true;p->run(b);realtime=false;
  if(p->api.instrument){for(unsigned i=0;i<8;++i)require(outL[i]==0||frames!=64,"MIDI timestamp");double energy=0;for(unsigned i=8;i<frames;++i)energy+=std::abs(outL[i]);require(energy>0,"synth MIDI note-on");b.midi=&off;p->run(b);for(unsigned i=16;i<frames;++i)require(outL[i]==0,"synth note-off timestamp");}
  else if(std::strstr(uri,"worker")){std::this_thread::sleep_for(std::chrono::milliseconds(10));p->run(b);require(std::abs(outL[frames-1]-.1f)<1e-6,"worker response");}
  else for(unsigned i=0;i<frames;++i)require(std::abs(outL[i]-.1f)<1e-6&&outL[i]==outR[i],"mono FX gain and stereo duplication");
 }
 }}
 {auto p=std::make_unique<jerzy_lv2::Plugin>("urn:jerzy:test:synth",44100,8192);std::array<float,512> input{},output{},right{};float value=1;JAMidi on{0,3,{144,69,100}},program{0,2,{192,127,0}};JAProcess b{sizeof(JAProcess),512,44100,120,0,1,{input.data(),input.data()},{output.data(),right.data()},&value,&on,1};p->run(b);auto folder=std::filesystem::temp_directory_path()/("jerzy-lv2-state-"+std::to_string(getpid()));p->saveState(folder.string());b.midi=&program;p->run(b);auto peak=[](auto& samples){float result=0;for(auto x:samples)result=std::max(result,std::abs(x));return result;};float loud=peak(output);p->restoreState((folder/"state.ttl").string());b.midi_count=0;p->run(b);require(peak(output)<loud*.3f,"LV2 internal state roundtrip");std::filesystem::remove_all(folder);}
 bool rejected=false;try{jerzy_lv2::Plugin p("urn:jerzy:test:unsupported",44100,8192);}catch(const std::runtime_error&){rejected=true;}require(rejected,"unsupported plugin rejected");std::cout<<"PASS LV2 discovery, FX, MIDI synth frame timing, worker, block sizes, sample rates, RT allocation guard\n";return 0;
 }catch(const std::exception& e){realtime=false;std::cerr<<e.what()<<'\n';return 1;}}
