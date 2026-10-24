#include "original_compare.h"
#include "../modules/mx-delay-original/vendor/mxdelay_dsp.h"
#include "reference_mx.h"
int main(int argc,char** argv){try{require(argc==2,"module path");double maximum=0,energy=0;uint64_t samples=0;auto started=std::chrono::steady_clock::now();
 constexpr unsigned ids[]{
#include "mx_vst_ids.inc"
 };
 for(double sr:{44100.,48000.}){Loaded m(argv[1],"mx-delay-original",sr);require(m.parameters.size()==std::size(ids),"missing MX controls");auto defaults=m.parameters;JerzyAudio::MXDelayDSP<float> reference;reference.prepare(sr,2);
 std::array<std::array<float,1024>,2> input{},out{},expected{};uint64_t cursor=0;
 for(int parameter=-1;parameter<int(m.parameters.size());++parameter){
 std::vector<float> values{0.f,.37f,1.f};if(parameter>=0){std::string key=m.api->parameters[parameter].id;int choices=key.find("_algorithm")!=std::string::npos?9:(key.find("_type")!=std::string::npos?6:0);if(choices){values.clear();for(int n=0;n<choices;++n)values.push_back(float(n)/float(choices-1));}}
 for(float value:values){
  m.parameters=defaults;if(parameter>=0)m.parameters[size_t(parameter)]=value;
  if(parameter>=0){std::string key=m.api->parameters[parameter].id;auto a=key.find("_algo");if(a!=std::string::npos){int slot=key[4]-'0',alg=key[a+5]-'0';m.parameters[m.index("slot"+std::to_string(slot)+"_algorithm")]=alg/8.f;}}
  OriginalMXMapping original;for(unsigned i=0;i<std::size(ids);++i)original.setNormalized(ids[i],m.parameters[i]);
  unsigned n=std::array<unsigned,5>{64,128,256,512,1024}[unsigned(parameter+1)%5];
  for(unsigned i=0;i<n;++i){input[0][i]=.09f*std::sin(float((cursor+i)*.031));input[1][i]=.08f*std::sin(float((cursor+i)*.052));}
  JAProcess b{sizeof(JAProcess),n,sr,117,cursor*117/(60*sr),1,{input[0].data(),input[1].data()},{out[0].data(),out[1].data()},nullptr,nullptr,0};m.process(b);
  float* in[]{input[0].data(),input[1].data()};float* dest[]{expected[0].data(),expected[1].data()};double peak=0;reference.process(in,dest,2,int(n),original.p,117,peak);
  for(int c=0;c<2;++c)for(unsigned i=0;i<n;++i){require(std::isfinite(out[c][i]),"nonfinite MX");maximum=std::max(maximum,double(std::abs(out[c][i]-expected[c][i])));energy+=std::abs(out[c][i]);++samples;}cursor+=n;
 }}
 }
 require(energy>.01,"silent MX test");require(maximum<1e-7,"MX parameter mapping or DSP mismatch");std::cout<<"{\"module\":\"mx-delay-original\",\"samples\":"<<samples<<",\"max_error\":"<<maximum<<",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()<<"}\n";return 0;
 }catch(const std::exception& e){rt=false;std::cerr<<e.what()<<'\n';return 1;}}
