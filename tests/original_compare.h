#pragma once
#include "../module-sdk/jerzy_module.h"
#include <dlfcn.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>
#include <vector>
static thread_local bool rt=false;static thread_local unsigned allocations=0;
extern "C" void* __libc_malloc(std::size_t);
extern "C" void* __libc_calloc(std::size_t,std::size_t);
extern "C" void* __libc_realloc(void*,std::size_t);
extern "C" void __libc_free(void*);
extern "C" void* malloc(std::size_t n) noexcept {if(rt)++allocations;return __libc_malloc(n);}
extern "C" void* calloc(std::size_t n,std::size_t s) noexcept {if(rt)++allocations;return __libc_calloc(n,s);}
extern "C" void* realloc(void* p,std::size_t n) noexcept {if(rt)++allocations;return __libc_realloc(p,n);}
extern "C" void free(void* p) noexcept {if(rt&&p)++allocations;__libc_free(p);}
void* operator new(std::size_t n){if(rt)++allocations;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}void operator delete(void* p,std::size_t) noexcept{std::free(p);}
static void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
struct Loaded {
 void* library;const JAModule* api;void* instance;std::vector<float> parameters;
 Loaded(const std::string& root,const char* id,double rate):library(dlopen((root+"/"+id+"/"+id+".so").c_str(),RTLD_NOW|RTLD_LOCAL)){
  if(!library)throw std::runtime_error(dlerror());api=reinterpret_cast<JAEntry>(dlsym(library,"ja_module"))();require(api&&api->abi==1,"ABI");
  instance=api->create(rate,8192,"");require(instance,"create");for(unsigned p=0;p<api->parameter_count;++p)parameters.push_back(api->parameters[p].initial);
 }
 ~Loaded(){api->destroy(instance);dlclose(library);}
 unsigned index(const std::string& key){for(unsigned i=0;i<parameters.size();++i)if(key==api->parameters[i].id)return i;throw std::runtime_error("missing parameter: "+key);}
 void process(JAProcess& b){b.parameters=parameters.data();allocations=0;rt=true;api->process(instance,&b);rt=false;require(allocations==0,"allocation in module process");}
};
