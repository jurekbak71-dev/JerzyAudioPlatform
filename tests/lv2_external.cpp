#include "../core/lv2_host.h"
#include <iostream>
int main(){try{
 for(auto uri:{"http://lv2plug.in/plugins/eg-amp","http://drobilla.net/plugins/mda/DX10","http://drobilla.net/plugins/mda/JX10","http://drobilla.net/plugins/mda/EPiano","http://drobilla.net/plugins/mda/Piano"}){
  auto p=std::make_unique<jerzy_lv2::Plugin>(uri,44100,8192);std::vector<float> values;for(unsigned i=0;i<p->api.parameter_count;++i)values.push_back(p->api.parameters[i].initial);
  std::array<float,512> input{},left{},right{};input.fill(.1f);double energy=0;float peak=0;JAMidi note{0,3,{144,60,100}};
  for(unsigned block=0;block<80;++block){JAProcess b{sizeof(JAProcess),512,44100,120,double(block)*512*120/(60*44100),1,{input.data(),input.data()},{left.data(),right.data()},values.data(),&note,block==0?1u:0u};p->run(b);for(unsigned i=0;i<512;++i){if(!std::isfinite(left[i])||!std::isfinite(right[i]))throw std::runtime_error("nonfinite external plugin");energy+=std::abs(left[i])+std::abs(right[i]);peak=std::max(peak,std::max(std::abs(left[i]),std::abs(right[i])));}}
  if(energy<.001||peak>32)throw std::runtime_error(std::string("No valid output: ")+uri);
  std::cout<<"PASS external LV2 "<<p->api.name<<" energy="<<energy<<" peak="<<peak<<'\n';
 }
 return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
