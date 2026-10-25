#include "jerzy_module.h"
#include <thread>
#include <chrono>
#include <cstdlib>
#include <algorithm>
#include <time.h>
struct State{int milliseconds;bool sleep;};
static void* create(double,uint32_t,const char* asset){return new State{asset&&*asset?std::clamp(std::abs(std::atoi(asset)),1,30):30,asset&&*asset=='-'};}
static void destroy(void* p){delete static_cast<State*>(p);}
static uint64_t now(){timespec t{};clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return uint64_t(t.tv_sec)*1000000000+uint64_t(t.tv_nsec);}
static void process(void* p,const JAProcess* b){auto& s=*static_cast<State*>(p);if(s.sleep)std::this_thread::sleep_for(std::chrono::milliseconds(s.milliseconds));else{const auto end=now()+uint64_t(s.milliseconds)*1000000;while(now()<end){} }for(unsigned i=0;i<b->frames;++i)for(int c=0;c<2;++c)b->output[c][i]=b->input[c][i];}
static uint32_t latency(void*){return 0;}
extern "C" const JAModule* ja_module(){static const JAModule m{sizeof(JAModule),JA_ABI,"test-overload","Overload fixture","0.0.0",0,0,nullptr,create,destroy,process,latency};return &m;}
