#pragma once
#include "../module-sdk/jerzy_module.h"
#include <lilv/lilv.h>
#include <lv2/atom/forge.h>
#include <lv2/buf-size/buf-size.h>
#include <lv2/midi/midi.h>
#include <lv2/options/options.h>
#include <lv2/state/state.h>
#include <lv2/time/time.h>
#include <lv2/urid/urid.h>
#include <lv2/worker/worker.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstring>
#include <deque>
#include <filesystem>
#include <iomanip>
#include <memory>
#include <limits>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
namespace jerzy_lv2 {
inline std::string quote(const std::string& s){std::ostringstream o;o<<'"';for(unsigned char c:s){if(c=='"'||c=='\\')o<<'\\'<<c;else if(c<32)o<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<int(c)<<std::dec;else o<<c;}return o.str()+'"';}
struct World {
 LilvWorld* value=lilv_world_new();
 World(){if(!value)throw std::runtime_error("Brak biblioteki LV2");
  const char* home=std::getenv("HOME");const char* custom=std::getenv("JERZY_LV2_PATH");std::string own=custom?custom:std::string(home?home:"/tmp")+"/.local/share/jerzy-audio-platform/lv2";
  if(std::filesystem::is_directory(own)){const char* configured=std::getenv("LV2_PATH");std::string path=own+":"+(configured?configured:std::string(home?home:"/tmp")+"/.lv2:/usr/local/lib/lv2:/usr/lib/lv2");auto option=lilv_new_string(value,path.c_str());lilv_world_set_option(value,LILV_OPTION_LV2_PATH,option);lilv_node_free(option);}
  lilv_world_load_all(value);}
 ~World(){lilv_world_free(value);}
 bool is(const LilvPlugin* p,const LilvPort* port,const char* uri) const{auto n=lilv_new_uri(value,uri);bool result=lilv_port_is_a(p,port,n);lilv_node_free(n);return result;}
 bool property(const LilvPlugin* p,const LilvPort* port,const char* uri)const{auto n=lilv_new_uri(value,uri);bool result=lilv_port_has_property(p,port,n);lilv_node_free(n);return result;}
 bool event(const LilvPlugin* p,const LilvPort* port,const char* uri)const{auto n=lilv_new_uri(value,uri);bool result=lilv_port_supports_event(p,port,n);lilv_node_free(n);return result;}
};
inline bool supported_feature(const char* uri){for(auto s:{LV2_URID__map,LV2_URID__unmap,LV2_OPTIONS__options,LV2_BUF_SIZE__boundedBlockLength,LV2_CORE__isLive,LV2_WORKER__schedule})if(std::strcmp(s,uri)==0)return true;return false;}
inline std::string unsupported(World& w,const LilvPlugin* p){
 if(lilv_plugin_get_num_ports(p)>4096)return "Zbyt wiele portów LV2";
 auto features=lilv_plugin_get_required_features(p);std::string error;
 LILV_FOREACH(nodes,i,features){auto uri=lilv_node_as_uri(lilv_nodes_get(features,i));if(!uri){error="Niepoprawny identyfikator wymaganej funkcji LV2";break;}if(!supported_feature(uri)){error="Wymagana funkcja LV2: "+std::string(uri);break;}}lilv_nodes_free(features);
 unsigned inputs=0,outputs=0,controls=0;
 for(unsigned i=0;i<lilv_plugin_get_num_ports(p);++i){auto port=lilv_plugin_get_port_by_index(p,i);bool optional=w.property(p,port,LV2_CORE__connectionOptional);
  if(w.is(p,port,LV2_CORE__AudioPort)){if(w.is(p,port,LV2_CORE__InputPort))++inputs;else ++outputs;}
  else if(w.is(p,port,LV2_CORE__ControlPort)){if(w.is(p,port,LV2_CORE__InputPort))++controls;}
  else if(w.is(p,port,LV2_ATOM__AtomPort)){auto key=lilv_new_uri(w.value,LV2_ATOM__bufferType);auto type=lilv_port_get(p,port,key);lilv_node_free(key);if(!type||std::strcmp(lilv_node_as_string(type),LV2_ATOM__Sequence)!=0){if(!optional)error="Nieobsługiwany bufor Atom (wymagana Sequence)";}lilv_node_free(type);}
  else if(!optional)error="Nieobsługiwany obowiązkowy port LV2";
 }
 if(inputs>2||outputs<1||outputs>2)error="Obsługiwane wtyczki audio mono/stereo";
 if(controls>JA_MAX_PARAMETERS)error="Zbyt wiele parametrów LV2";
 return error;
}
inline std::string catalog(){World w;std::ostringstream out;out<<"{\"ok\":true,\"plugins\":[";bool first=true;auto plugins=lilv_world_get_all_plugins(w.value);
 LILV_FOREACH(plugins,i,plugins){auto p=lilv_plugins_get(plugins,i);auto name=lilv_plugin_get_name(p);auto uri=lilv_node_as_uri(lilv_plugin_get_uri(p));unsigned inputs=0;bool midi=false;
  for(unsigned j=0;j<lilv_plugin_get_num_ports(p);++j){auto port=lilv_plugin_get_port_by_index(p,j);inputs+=w.is(p,port,LV2_CORE__AudioPort)&&w.is(p,port,LV2_CORE__InputPort);midi|=w.event(p,port,LV2_MIDI__MidiEvent);}
  auto error=unsupported(w,p);if(!first)out<<',';first=false;
  out<<"{\"id\":"<<quote(std::string("lv2:")+uri)<<",\"path\":"<<quote(std::string("lv2:")+uri)<<",\"uri\":"<<quote(uri)<<",\"name\":"<<quote(name?lilv_node_as_string(name):uri)<<",\"bundle\":"<<quote(lilv_node_as_uri(lilv_plugin_get_bundle_uri(p)))<<",\"format\":\"lv2\",\"version\":\"LV2\",\"instrument\":"<<(!inputs?"true":"false")<<",\"supported\":"<<(error.empty()?"true":"false")<<",\"error\":"<<quote(error)<<'}';lilv_node_free(name);
 }return out.str()+"]}";}
class Plugin {
 static constexpr uint32_t atomBytes=65536,queueSize=8;
 struct Mapper {
  std::array<std::array<char,512>,2048> strings{};std::atomic<uint32_t> count{0};std::mutex mutex;
  static LV2_URID map(void* handle,const char* uri){auto& m=*static_cast<Mapper*>(handle);auto n=m.count.load(std::memory_order_acquire);for(unsigned i=0;i<n;++i)if(std::strcmp(m.strings[i].data(),uri)==0)return i+1;
   std::lock_guard lock(m.mutex);n=m.count.load();for(unsigned i=0;i<n;++i)if(std::strcmp(m.strings[i].data(),uri)==0)return i+1;if(n==m.strings.size()||std::strlen(uri)>=512)return 0;std::strcpy(m.strings[n].data(),uri);m.count.store(n+1,std::memory_order_release);return n+1;
  }
  static const char* unmap(void* handle,LV2_URID id){auto& m=*static_cast<Mapper*>(handle);return id&&id<=m.count.load(std::memory_order_acquire)?m.strings[id-1].data():nullptr;}
 } mapper;
 struct Packet{uint32_t size=0;std::array<uint8_t,atomBytes> data{};};
 struct Queue{std::array<Packet,queueSize> items;std::atomic<unsigned> read{0},write{0};
  bool push(uint32_t size,const void* data){auto w=write.load(std::memory_order_relaxed);if(size>atomBytes||w-read.load(std::memory_order_acquire)==queueSize)return false;auto& p=items[w%queueSize];p.size=size;if(size)std::memcpy(p.data.data(),data,size);write.store(w+1,std::memory_order_release);return true;}
  Packet* front(){auto r=read.load(std::memory_order_relaxed);return r==write.load(std::memory_order_acquire)?nullptr:&items[r%queueSize];}
  void pop(){read.fetch_add(1,std::memory_order_release);}
 } jobs,responses;
 struct Port{enum Kind{Audio,Control,Atom,Unknown} kind=Unknown;bool input=false,midi=false,time=false;float value=0;std::vector<float> audio;std::vector<uint64_t> atom;int parameter=-1;};
 World world;const LilvPlugin* plugin=nullptr;LilvInstance* instance=nullptr;std::unique_ptr<LilvInstance,decltype(&lilv_instance_free)> owned{nullptr,lilv_instance_free};std::vector<Port> ports;std::deque<std::string> strings;std::vector<JAParameter> parameters;
 std::vector<unsigned> audioInputs,audioOutputs;std::vector<std::string> scalePoints;std::vector<std::vector<float>> scaleValues;std::vector<bool> enumerations;
 LV2_URID_Map mapFeature{&mapper,Mapper::map};LV2_URID_Unmap unmapFeature{&mapper,Mapper::unmap};
 LV2_Worker_Schedule scheduleFeature{this,schedule};const LV2_Worker_Interface* workerInterface=nullptr;std::atomic<bool> stop{false};std::thread worker;
 std::mutex workMutex;
 std::atomic<uint32_t> latencyValue{0};uint32_t latencyPort=UINT32_MAX,maxFrames;float sampleRate;int32_t minimumBlock=1,maximumBlock;uint64_t frame=0;
 std::array<LV2_Options_Option,4> options{};std::array<LV2_Feature,6> features{};std::array<const LV2_Feature*,7> featurePointers{};
 LV2_URID midiType=0;
 const char* keep(std::string s){strings.push_back(std::move(s));return strings.back().c_str();}
 static LV2_Worker_Status schedule(void* self,uint32_t size,const void* data){return static_cast<Plugin*>(self)->jobs.push(size,data)?LV2_WORKER_SUCCESS:LV2_WORKER_ERR_NO_SPACE;}
 static LV2_Worker_Status respond(void* self,uint32_t size,const void* data){return static_cast<Plugin*>(self)->responses.push(size,data)?LV2_WORKER_SUCCESS:LV2_WORKER_ERR_NO_SPACE;}
 static void render(void* instance,const JAProcess* b){static_cast<Plugin*>(instance)->run(*b);}
public:
 JAModule api{};
 Plugin(const std::string& uri,double sr,uint32_t frames):maxFrames(frames),sampleRate(float(sr)),maximumBlock(int32_t(frames)){
  auto node=lilv_new_uri(world.value,uri.c_str());plugin=lilv_plugins_get_by_uri(lilv_world_get_all_plugins(world.value),node);lilv_node_free(node);if(!plugin)throw std::runtime_error("Nie znaleziono wtyczki LV2: "+uri);
  auto error=unsupported(world,plugin);if(!error.empty())throw std::runtime_error(error);
  auto map=[&](const char* u){return Mapper::map(&mapper,u);};midiType=map(LV2_MIDI__MidiEvent);
  LV2_Atom_Forge initialForge;lv2_atom_forge_init(&initialForge,&mapFeature);for(auto uri:{LV2_TIME__Position,LV2_TIME__frame,LV2_TIME__speed,LV2_TIME__beatsPerMinute,LV2_TIME__barBeat,LV2_TIME__beatsPerBar,LV2_TIME__beatUnit})map(uri);
  options={LV2_Options_Option{LV2_OPTIONS_INSTANCE,0,map(LV2_BUF_SIZE__minBlockLength),sizeof(minimumBlock),map(LV2_ATOM__Int),&minimumBlock},LV2_Options_Option{LV2_OPTIONS_INSTANCE,0,map(LV2_BUF_SIZE__maxBlockLength),sizeof(maximumBlock),map(LV2_ATOM__Int),&maximumBlock},LV2_Options_Option{LV2_OPTIONS_INSTANCE,0,map("http://lv2plug.in/ns/parameters#sampleRate"),sizeof(sampleRate),map(LV2_ATOM__Float),&sampleRate},LV2_Options_Option{}};
  features={LV2_Feature{LV2_URID__map,&mapFeature},LV2_Feature{LV2_URID__unmap,&unmapFeature},LV2_Feature{LV2_OPTIONS__options,options.data()},LV2_Feature{LV2_BUF_SIZE__boundedBlockLength,nullptr},LV2_Feature{LV2_CORE__isLive,nullptr},LV2_Feature{LV2_WORKER__schedule,&scheduleFeature}};for(unsigned i=0;i<features.size();++i)featurePointers[i]=&features[i];
  const unsigned count=lilv_plugin_get_num_ports(plugin);ports.resize(count);std::vector<float> minimum(count),maximum(count),defaults(count);lilv_plugin_get_port_ranges_float(plugin,minimum.data(),maximum.data(),defaults.data());
  for(unsigned i=0;i<count;++i){auto spec=lilv_plugin_get_port_by_index(plugin,i);auto& p=ports[i];p.input=world.is(plugin,spec,LV2_CORE__InputPort);
   if(world.is(plugin,spec,LV2_CORE__AudioPort)){p.kind=Port::Audio;p.audio.resize(frames);(p.input?audioInputs:audioOutputs).push_back(i);}
   else if(world.is(plugin,spec,LV2_CORE__ControlPort)){p.kind=Port::Control;float scale=world.property(plugin,spec,LV2_CORE__sampleRate)?float(sr):1;float fallback=std::isfinite(defaults[i])?defaults[i]*scale:0;float lo=std::isfinite(minimum[i])?minimum[i]*scale:std::min(0.f,fallback),hi=std::isfinite(maximum[i])?maximum[i]*scale:std::max(1.f,fallback);if(hi<lo)std::swap(lo,hi);float initial=std::clamp(std::isfinite(defaults[i])?defaults[i]*scale:lo,lo,hi);p.value=initial;
    if(p.input){p.parameter=int(parameters.size());auto name=lilv_port_get_name(plugin,spec);bool integer=world.property(plugin,spec,LV2_CORE__integer)||world.property(plugin,spec,LV2_CORE__toggled);if(integer){lo=std::ceil(lo);hi=std::max(lo,std::floor(hi));initial=std::clamp(std::round(initial),lo,hi);p.value=initial;}
     parameters.push_back({keep(lilv_node_as_string(lilv_port_get_symbol(plugin,spec))),keep(name?lilv_node_as_string(name):"Parametr"),keep(""),keep(""),lo,hi,initial,uint32_t(integer)});lilv_node_free(name);
     enumerations.push_back(world.property(plugin,spec,LV2_CORE__enumeration));scaleValues.emplace_back();std::ostringstream points;points<<std::setprecision(std::numeric_limits<float>::max_digits10)<<'[';auto scales=lilv_port_get_scale_points(plugin,spec);bool first=true;LILV_FOREACH(scale_points,j,scales){auto point=lilv_scale_points_get(scales,j);auto value=lilv_scale_point_get_value(point);if((!lilv_node_is_float(value)&&!lilv_node_is_int(value))||!std::isfinite(lilv_node_as_float(value)))continue;scaleValues.back().push_back(lilv_node_as_float(value)*scale);if(!first)points<<',';first=false;points<<"{\"value\":"<<lilv_node_as_float(value)*scale<<",\"label\":"<<quote(lilv_node_as_string(lilv_scale_point_get_label(point)))<<'}';}lilv_scale_points_free(scales);scalePoints.push_back(points.str()+']');
    }
   }else if(world.is(plugin,spec,LV2_ATOM__AtomPort)){p.kind=Port::Atom;p.atom.resize(atomBytes/8);p.midi=world.event(plugin,spec,LV2_MIDI__MidiEvent);p.time=world.event(plugin,spec,LV2_TIME__Position);}
  }
  auto name=lilv_plugin_get_name(plugin);api={sizeof(JAModule),JA_ABI,keep("lv2:"+uri),keep(name?lilv_node_as_string(name):uri),keep("LV2"),uint32_t(audioInputs.empty()),uint32_t(parameters.size()),parameters.data(),nullptr,[](void*){},render,[](void* self){return static_cast<Plugin*>(self)->latencyValue.load();}};lilv_node_free(name);
  instance=lilv_plugin_instantiate(plugin,sr,featurePointers.data());if(!instance)throw std::runtime_error("Nie można uruchomić wtyczki LV2");owned.reset(instance);
  for(unsigned i=0;i<ports.size();++i){auto& p=ports[i];void* address=p.kind==Port::Audio?static_cast<void*>(p.audio.data()):p.kind==Port::Control?static_cast<void*>(&p.value):p.kind==Port::Atom?static_cast<void*>(p.atom.data()):nullptr;lilv_instance_connect_port(instance,i,address);}
  if(lilv_plugin_has_latency(plugin))latencyPort=lilv_plugin_get_latency_port_index(plugin);
  workerInterface=static_cast<const LV2_Worker_Interface*>(lilv_instance_get_extension_data(instance,LV2_WORKER__interface));lilv_instance_activate(instance);
  if(workerInterface&&workerInterface->work)worker=std::thread([this]{while(!stop.load()){if(auto packet=jobs.front()){std::lock_guard lock(workMutex);workerInterface->work(lilv_instance_get_handle(instance),respond,this,packet->size,packet->data.data());jobs.pop();}else std::this_thread::sleep_for(std::chrono::milliseconds(1));}});
 }
 ~Plugin(){stop.store(true);if(worker.joinable())worker.join();if(instance)lilv_instance_deactivate(instance);owned.reset();}
 const std::string& points(unsigned index)const{return scalePoints.at(index);}
 void setTransportFrame(uint64_t value){frame=value;}
 bool enumeration(unsigned index)const{return enumerations.at(index);}
 float normalize(unsigned index,float value)const{if(!enumerations[index]||scaleValues[index].empty())return value;const auto& choices=scaleValues[index];return *std::min_element(choices.begin(),choices.end(),[value](float a,float b){return std::abs(a-value)<std::abs(b-value);});}
 void saveState(const std::string& directory){
  std::lock_guard lock(workMutex);std::filesystem::create_directories(directory);
  auto state=lilv_state_new_from_instance(plugin,instance,&mapFeature,nullptr,directory.c_str(),directory.c_str(),directory.c_str(),nullptr,nullptr,0,featurePointers.data());
  if(!state)throw std::runtime_error("Nie zapisano stanu LV2");
  int result=lilv_state_save(world.value,&mapFeature,&unmapFeature,state,nullptr,directory.c_str(),"state.ttl");lilv_state_free(state);if(result)throw std::runtime_error("Błąd zapisu pliku stanu LV2");
 }
 void restoreState(const std::string& file){
  std::lock_guard lock(workMutex);auto state=lilv_state_new_from_file(world.value,&mapFeature,nullptr,file.c_str());if(!state)throw std::runtime_error("Niepoprawny stan LV2");
  if(!lilv_node_equals(lilv_state_get_plugin_uri(state),lilv_plugin_get_uri(plugin))){lilv_state_free(state);throw std::runtime_error("Stan należy do innej wtyczki LV2");}
  lilv_state_restore(state,instance,nullptr,nullptr,0,featurePointers.data());lilv_state_free(state);
 }
 void run(const JAProcess& b){
  if(b.frames>maxFrames){for(auto* p:b.output)std::fill_n(p,b.frames,0);return;}
  for(unsigned j=0;j<audioInputs.size();++j){auto& target=ports[audioInputs[j]].audio;if(audioInputs.size()==1)for(unsigned i=0;i<b.frames;++i)target[i]=(b.input[0][i]+b.input[1][i])*.5f;else std::copy_n(b.input[j],b.frames,target.data());}
  for(auto i:audioOutputs)std::fill_n(ports[i].audio.data(),b.frames,0);
  for(auto& p:ports){if(p.kind==Port::Control&&p.input)p.value=b.parameters[p.parameter];if(p.kind!=Port::Atom)continue;auto seq=reinterpret_cast<LV2_Atom_Sequence*>(p.atom.data());
   if(!p.input){seq->atom.size=atomBytes-sizeof(LV2_Atom);seq->atom.type=Mapper::map(&mapper,LV2_ATOM__Sequence);continue;}
   LV2_Atom_Forge forge;lv2_atom_forge_init(&forge,&mapFeature);lv2_atom_forge_set_buffer(&forge,reinterpret_cast<uint8_t*>(p.atom.data()),atomBytes);LV2_Atom_Forge_Frame sequence;lv2_atom_forge_sequence_head(&forge,&sequence,0);
   if(p.time){LV2_Atom_Forge_Frame object;lv2_atom_forge_frame_time(&forge,0);lv2_atom_forge_object(&forge,&object,0,Mapper::map(&mapper,LV2_TIME__Position));lv2_atom_forge_key(&forge,Mapper::map(&mapper,LV2_TIME__frame));lv2_atom_forge_long(&forge,int64_t(frame));lv2_atom_forge_key(&forge,Mapper::map(&mapper,LV2_TIME__speed));lv2_atom_forge_float(&forge,float(b.playing));lv2_atom_forge_key(&forge,Mapper::map(&mapper,LV2_TIME__beatsPerMinute));lv2_atom_forge_float(&forge,float(b.bpm));lv2_atom_forge_key(&forge,Mapper::map(&mapper,LV2_TIME__barBeat));lv2_atom_forge_float(&forge,float(std::fmod(b.beat,4.)));lv2_atom_forge_key(&forge,Mapper::map(&mapper,LV2_TIME__beatsPerBar));lv2_atom_forge_float(&forge,4);lv2_atom_forge_key(&forge,Mapper::map(&mapper,LV2_TIME__beatUnit));lv2_atom_forge_int(&forge,4);lv2_atom_forge_pop(&forge,&object);}
   if(p.midi)for(unsigned i=0;i<b.midi_count;++i){auto& event=b.midi[i];if(event.frame>=b.frames||event.size>3)continue;lv2_atom_forge_frame_time(&forge,event.frame);lv2_atom_forge_atom(&forge,event.size,midiType);lv2_atom_forge_write(&forge,event.bytes,event.size);}
   lv2_atom_forge_pop(&forge,&sequence);
  }
  if(workerInterface&&workerInterface->work_response)for(unsigned response=0;response<queueSize;++response){auto packet=responses.front();if(!packet)break;workerInterface->work_response(lilv_instance_get_handle(instance),packet->size,packet->data.data());responses.pop();}
  lilv_instance_run(instance,b.frames);if(workerInterface&&workerInterface->end_run)workerInterface->end_run(lilv_instance_get_handle(instance));
  for(unsigned c=0;c<2;++c)std::copy_n(ports[audioOutputs[std::min<size_t>(c,audioOutputs.size()-1)]].audio.data(),b.frames,b.output[c]);
  if(latencyPort<ports.size()){float value=ports[latencyPort].value;latencyValue.store(std::isfinite(value)?uint32_t(std::clamp(value,0.f,float(UINT32_MAX/2))):0);}frame+=b.frames;
 }
};
}
