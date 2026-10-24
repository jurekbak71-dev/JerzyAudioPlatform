#include "jerzy_module.h"
#include <thread>
#include <chrono>
#include <cstdlib>
#include <algorithm>
static void* create(double,uint32_t,const char* asset){return new int(asset&&*asset?std::clamp(std::atoi(asset),1,30):30);}
static void destroy(void* p){delete static_cast<int*>(p);}
static void process(void* p,const JAProcess* b){std::this_thread::sleep_for(std::chrono::milliseconds(*static_cast<int*>(p)));for(unsigned i=0;i<b->frames;++i)for(int c=0;c<2;++c)b->output[c][i]=b->input[c][i];}
static uint32_t latency(void*){return 0;}
extern "C" const JAModule* ja_module(){static const JAModule m{sizeof(JAModule),JA_ABI,"test-overload","Overload fixture","0.0.0",0,0,nullptr,create,destroy,process,latency};return &m;}
