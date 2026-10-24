#include "original_compare.h"
int main(int argc,char** argv){try{require(argc==2,"module path");const double sr=44100;std::array<std::array<float,256>,2> in{},out{},other{};double difference=0;
 for(int parameter=0;parameter<3;++parameter){Loaded a(argv[1],"big-muff-original",sr),b(argv[1],"big-muff-original",sr);a.parameters[parameter]=.15;b.parameters[parameter]=.85;
  double d=0;for(unsigned block=0;block<40;++block){for(unsigned i=0;i<256;++i)in[0][i]=in[1][i]=.07f*(std::sin(float((block*256+i)*.041))+.3f*std::sin(float((block*256+i)*.13)));
   JAProcess p{sizeof(JAProcess),256,sr,120,0,1,{in[0].data(),in[1].data()},{out[0].data(),out[1].data()},nullptr,nullptr,0};a.process(p);p.output[0]=other[0].data();p.output[1]=other[1].data();b.process(p);
   for(int c=0;c<2;++c)for(unsigned i=0;i<256;++i){require(std::isfinite(out[c][i])&&std::isfinite(other[c][i]),"Muff nonfinite");if(block>10)d+=std::abs(out[c][i]-other[c][i]);}
  }require(d>.001,"Muff control does not affect sound");difference+=d;
 }
 Loaded atomic(argv[1],"atomic-cluster-original",sr);double maxPeak=0,totalEnergy=0;uint64_t samples=0;
 // Twelve seconds with changing count/pattern/dynamics, not isolated short frames.
 for(unsigned block=0;block<2068;++block){
  if(block%256==0){atomic.parameters[atomic.index("atoms")]=(block/256)%2?1.f:.66f;atomic.parameters[atomic.index("flat")]=(block/256)%2;atomic.parameters[atomic.index("motion")]=float((block/256)%3)/2;}
  for(unsigned i=0;i<256;++i){in[0][i]=.12f*std::sin(float((block*256+i)*.031));in[1][i]=.09f*std::sin(float((block*256+i)*.043));}
  JAProcess p{sizeof(JAProcess),256,sr,120,double(block*256)*120/(60*sr),1,{in[0].data(),in[1].data()},{out[0].data(),out[1].data()},nullptr,nullptr,0};atomic.process(p);
  for(int c=0;c<2;++c)for(unsigned i=0;i<256;++i){require(std::isfinite(out[c][i])&&std::abs(out[c][i])<=1.01,"Atomic output grew or became nonfinite");maxPeak=std::max(maxPeak,double(std::abs(out[c][i])));totalEnergy+=std::abs(out[c][i]);++samples;}
 }
 require(totalEnergy>.01,"Atomic silent");std::cout<<"PASS: Big Muff volume/tone/sustain alter audio; Atomic 12s changing 16/64 voices bounded, no callback allocations. samples="<<samples<<", peak="<<maxPeak<<", Muff difference="<<difference<<"\n";return 0;
}catch(const std::exception& e){rt=false;std::cerr<<e.what()<<'\n';return 1;}}
