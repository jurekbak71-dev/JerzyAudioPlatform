#include "original_compare.h"
#include "../modules/tape-drive-original/vendor/tapedrive_dsp.h"
int main(int argc,char** argv){try{require(argc==2,"module path");double maximum=0;uint64_t samples=0;auto start=std::chrono::steady_clock::now();
 for(double sr:{44100.,48000.}){Loaded m(argv[1],"tape-drive-original",sr);JerzyAudio::TapeDriveDSP<float> reference;reference.prepare(sr,2);auto defaults=m.parameters;
  const char* keys[]{"sat","level","dry","gainMode","shift","bypass","hpfCutoff","hpfRes","lpfCutoff","lpfRes","wowFlutter","preampMode","preampDrive","flutter","tapeAge","optoAmount","optoMakeup","optoBypass"};
  double JerzyAudio::TapeDriveParams::* field[]{&JerzyAudio::TapeDriveParams::sat,&JerzyAudio::TapeDriveParams::level,&JerzyAudio::TapeDriveParams::dry,&JerzyAudio::TapeDriveParams::gainMode,&JerzyAudio::TapeDriveParams::shift,&JerzyAudio::TapeDriveParams::bypass,&JerzyAudio::TapeDriveParams::hpfCutoff,&JerzyAudio::TapeDriveParams::hpfRes,&JerzyAudio::TapeDriveParams::lpfCutoff,&JerzyAudio::TapeDriveParams::lpfRes,&JerzyAudio::TapeDriveParams::wowFlutter,&JerzyAudio::TapeDriveParams::preampMode,&JerzyAudio::TapeDriveParams::preampDrive,&JerzyAudio::TapeDriveParams::flutter,&JerzyAudio::TapeDriveParams::tapeAge,&JerzyAudio::TapeDriveParams::optoAmount,&JerzyAudio::TapeDriveParams::optoMakeup,&JerzyAudio::TapeDriveParams::optoBypass};
  std::array<std::array<float,1024>,2> input{},out{},expected{};uint64_t cursor=0;
  for(int parameter=-1;parameter<18;++parameter)for(float value:{0.f,.37f,1.f})for(unsigned n:{64u,128u,256u,512u,1024u}){
   m.parameters=defaults;if(parameter>=0)m.parameters[m.index(keys[parameter])]=value;
   JerzyAudio::TapeDriveParams p;for(unsigned k=0;k<18;++k)p.*field[k]=m.parameters[m.index(keys[k])];
   for(unsigned i=0;i<n;++i){input[0][i]=.13f*std::sin(float((cursor+i)*.031))+.03f*std::sin(float((cursor+i)*.19));input[1][i]=input[0][i]*.7f;}
   JAProcess b{sizeof(JAProcess),n,sr,123,double(cursor)*123/(60*sr),1,{input[0].data(),input[1].data()},{out[0].data(),out[1].data()},nullptr,nullptr,0};m.process(b);
   const float* in[]{input[0].data(),input[1].data()};float* dest[]{expected[0].data(),expected[1].data()};double a=0,c=0,d=0,e=0;
   if(p.bypass>=.5)expected=input;else reference.process(in,dest,2,int(n),p,a,c,d,e);
   for(int ch=0;ch<2;++ch)for(unsigned i=0;i<n;++i){require(std::isfinite(out[ch][i]),"nonfinite");maximum=std::max(maximum,double(std::abs(out[ch][i]-expected[ch][i])));++samples;}cursor+=n;
  }
 }
 require(maximum<1e-7,"Tape Drive differs from original");std::cout<<"{\"module\":\"tape-drive-original\",\"samples\":"<<samples<<",\"max_error\":"<<maximum<<",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";return 0;
 }catch(const std::exception& e){rt=false;std::cerr<<e.what()<<'\n';return 1;}}
