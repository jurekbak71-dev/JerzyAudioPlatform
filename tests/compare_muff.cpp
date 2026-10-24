#include "original_compare.h"
#include "../modules/big-muff-original/OriginalProcessor.h"
int main(int argc,char** argv){try{require(argc==2,"module path");double maximum=0,energy=0;uint64_t samples=0;auto started=std::chrono::steady_clock::now();
 for(double sr:{44100.,48000.}){Loaded m(argv[1],"big-muff-original",sr);OriginalMuffDSP reference;reference.prepareToPlay(sr,8192);require(reference.isReady(),"reference initialization");require(m.api->latency(m.instance)==unsigned(reference.latencyFrames),"oversampling latency");
  std::array<std::array<float,1024>,2> in{},out{},expected{};uint64_t cursor=0;
  for(int model=0;model<20;++model){m.parameters[3]=float(std::min(model,5));m.parameters[5]=float(model<6?0:model-5);
   for(unsigned n:{64u,128u,256u,512u,1024u}){
    m.parameters[0]=.4f;m.parameters[1]=float(.1+.8*(model%3)/2);m.parameters[2]=float(.2+.6*(model%4)/3);m.parameters[4]=0.f;
    for(unsigned i=0;i<n;++i){in[0][i]=.06f*std::sin(float((cursor+i)*.047));in[1][i]=model%2?in[0][i]:.07f*std::sin(float((cursor+i)*.059));}
    JAProcess b{sizeof(JAProcess),n,sr,120,0,1,{in[0].data(),in[1].data()},{out[0].data(),out[1].data()},nullptr,nullptr,0};m.process(b);
    for(int p=0;p<6;++p)reference.controls[p].store(m.parameters[p]);expected=in;float* pointers[]{expected[0].data(),expected[1].data()};juce::AudioBuffer<float> buffer(pointers,2,int(n));juce::MidiBuffer midi;reference.processBlock(buffer,midi);
    for(int c=0;c<2;++c)for(unsigned i=0;i<n;++i){require(std::isfinite(out[c][i]),"nonfinite");maximum=std::max(maximum,double(std::abs(out[c][i]-expected[c][i])));energy+=std::abs(out[c][i]);++samples;}cursor+=n;
   }
  }
 }
 require(energy>.01,"silent test");require(maximum<1e-7,"Muff processor differs");std::cout<<"{\"module\":\"big-muff-original\",\"samples\":"<<samples<<",\"max_error\":"<<maximum<<",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()<<"}\n";return 0;
 }catch(const std::exception& e){rt=false;std::cerr<<e.what()<<'\n';return 1;}}
