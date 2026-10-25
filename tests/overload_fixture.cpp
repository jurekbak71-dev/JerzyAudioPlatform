#include "jerzy_module.h"
#include <thread>
#include <chrono>
#include <cstdlib>
#include <algorithm>
#include <time.h>
#include <string>
struct State{int milliseconds;bool sleep;bool memory=false,latched=false;};
static void* create(double,uint32_t,const char* asset){return new State{asset&&*asset?std::clamp(std::abs(std::atoi(asset)),1,30):30,asset&&*asset=='-',asset&&std::string(asset)=="latched",false};}
static void destroy(void* p){delete static_cast<State*>(p);}
static uint64_t now(){timespec t{};clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return uint64_t(t.tv_sec)*1000000000+uint64_t(t.tv_nsec);}
static void process(void* p,const JAProcess* b){auto& s=*static_cast<State*>(p);if(s.memory&&b->parameters[0]>.5f)s.latched=true;if(s.memory&&!s.latched){}else if(s.sleep)std::this_thread::sleep_for(std::chrono::milliseconds(s.milliseconds));else{const auto end=now()+uint64_t((s.memory?30:s.milliseconds))*1000000;while(now()<end){} }for(unsigned i=0;i<b->frames;++i)for(int c=0;c<2;++c)b->output[c][i]=b->input[c][i];}
static uint32_t latency(void*){return 0;}
extern "C" const JAModule* ja_module(){static const JAParameter metadata[]={{"engage","Engage","","",0,1,1,1}};static const JAModule m{sizeof(JAModule),JA_ABI,"test-overload","Overload fixture","0.0.0",0,1,metadata,create,destroy,process,latency};return &m;}
