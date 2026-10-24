#include "original_compare.h"
#if defined(REFERENCE_CLONE)
#include "../modules/small-clone-original/vendor/Dsp.h"
namespace original=jerzy;
constexpr const char* identifier="small-clone-original";
#elif defined(REFERENCE_ATOMIC)
#include "../modules/atomic-cluster-original/vendor/Dsp.h"
namespace original=atomiccluster;
constexpr const char* identifier="atomic-cluster-original";
#else
#include "../modules/memory-delay-original/vendor/dsp.h"
constexpr const char* identifier="memory-delay-original";
#endif
int main(int argc,char** argv){try{require(argc==2,"module path");double maximum=0,energy=0;uint64_t samples=0;auto started=std::chrono::steady_clock::now();
 for(double sr:{44100.,48000.}){Loaded m(argv[1],identifier,sr);auto defaults=m.parameters;
#if defined(REFERENCE_CLONE) || defined(REFERENCE_ATOMIC)
 original::Engine reference;reference.reset(sr,original::defaults());
#else
 Jerzy::Engine reference;reference.prepare(sr);
#endif
 std::array<std::array<float,1024>,2> in{},out{};uint64_t cursor=0;
 for(int parameter=-1;parameter<int(m.parameters.size());++parameter){
 std::vector<float> values{0.f,.37f,1.f};
 if(parameter>=0){std::string key=m.api->parameters[parameter].id;int choices=0;
#if defined(REFERENCE_CLONE)
 if(key=="model")choices=14;if(key=="division")choices=18;
#elif defined(REFERENCE_ATOMIC)
 if(key=="division")choices=5;if(key=="motion")choices=3;
 if(key=="atoms"){values.clear();for(int n=1;n<=64;++n)values.push_back(float(std::log(double(n))/std::log(64.)));}
#else
 if(key=="model")choices=6;if(key=="division")choices=21;
#endif
 if(choices){values.clear();for(int n=0;n<choices;++n)values.push_back(float(n)/float(choices-1));}}
 for(float value:values)for(unsigned n:{64u,128u,256u,512u,1024u}){
  m.parameters=defaults;if(parameter>=0)m.parameters[size_t(parameter)]=value;
#if defined(REFERENCE_CLONE) || defined(REFERENCE_ATOMIC)
  original::Values p{};for(size_t i=0;i<p.size();++i)p[i]=m.parameters[i];
#else
  Jerzy::Parameters p;for(size_t i=0;i<p.value.size();++i)p.value[i]=m.parameters[i];
#endif
  for(unsigned i=0;i<n;++i){in[0][i]=.09f*std::sin(float((cursor+i)*.037))+.015f*std::sin(float((cursor+i)*.3));in[1][i]=.07f*std::sin(float((cursor+i)*.049));}
  const double bpm=parameter%2?123:87,beat=cursor*bpm/(60*sr);
  JAProcess b{sizeof(JAProcess),n,sr,bpm,beat,1,{in[0].data(),in[1].data()},{out[0].data(),out[1].data()},nullptr,nullptr,0};m.process(b);
  for(unsigned i=0;i<n;++i){
#if defined(REFERENCE_CLONE)
   auto y=reference.process(in[0][i],in[1][i],p,bpm,beat+i*bpm/(60*sr));
#elif defined(REFERENCE_ATOMIC)
   auto y=reference.process(in[0][i],in[1][i],p,bpm,beat+(double(i)-original::fftSize)*bpm/(60*sr));
#else
   double x[]{in[0][i],in[1][i]},y[2];reference.tick(x,y,2,p,bpm);
#endif
   for(int c=0;c<2;++c){require(std::isfinite(out[c][i]),"nonfinite output");maximum=std::max(maximum,double(std::abs(out[c][i]-float(y[c]))));energy+=std::abs(out[c][i]);++samples;}
  }cursor+=n;
 }}
 require(energy>.001,"silent test");
#if defined(REFERENCE_ATOMIC)
 require(m.api->latency(m.instance)==2048,"Atomic latency mismatch");
#endif
 }
 require(maximum<1e-7,"module differs from original DSP");std::cout<<"{\"module\":\""<<identifier<<"\",\"samples\":"<<samples<<",\"max_error\":"<<maximum<<",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()<<"}\n";return 0;
 }catch(const std::exception& e){rt=false;std::cerr<<e.what()<<'\n';return 1;}}
