#include "../module-sdk/jerzy_module.h"
#include <jack/jack.h>
#include <jack/midiport.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <poll.h>
#include <unistd.h>
#include <dlfcn.h>
#include <atomic>
#include <array>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstring>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#ifdef __SSE__
#include <xmmintrin.h>
#endif
namespace {
constexpr uint32_t MAX_FRAMES=8192;
static_assert(std::atomic<float>::is_always_lock_free && std::atomic<uint64_t>::is_always_lock_free && std::atomic<void*>::is_always_lock_free);
std::atomic<bool> running{true};
void signalHandler(int){running.store(false);}
std::string json(const std::string& s){std::ostringstream o;o<<'"';for(unsigned char c:s){if(c=='"'||c=='\\')o<<'\\'<<c;else if(c<32)o<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<int(c)<<std::dec;else o<<c;}o<<'"';return o.str();}
struct Node {
 void* lib=nullptr;const JAModule* api=nullptr;void* instance=nullptr;unsigned id;int route;std::string path,asset;
 std::array<std::atomic<float>,JA_MAX_PARAMETERS> params{};std::array<std::atomic<int>,JA_MAX_PARAMETERS> mapping{};std::atomic<bool> bypass{false};float mix=0;
 Node(unsigned i,int r,std::string p,std::string a,double sr):id(i),route(r),path(std::move(p)),asset(std::move(a)){
  for(auto& value:mapping)value.store(-1);
  lib=dlopen(path.c_str(),RTLD_NOW|RTLD_LOCAL);if(!lib)throw std::runtime_error("Nie można otworzyć biblioteki modułu");
  try {auto entry=reinterpret_cast<JAEntry>(dlsym(lib,"ja_module"));if(!entry)throw std::runtime_error("Brak symbolu ja_module");api=entry();
   if(!api||api->size!=sizeof(JAModule)||api->abi!=JA_ABI||api->parameter_count>JA_MAX_PARAMETERS||!api->id||!api->name||!api->version||!api->create||!api->destroy||!api->process||!api->latency||(api->parameter_count&&!api->parameters))throw std::runtime_error("Niezgodne ABI modułu");
   for(unsigned j=0;j<api->parameter_count;++j){const auto& p0=api->parameters[j];if(!p0.id||!p0.label||!p0.unit||!p0.choices||!std::isfinite(p0.minimum)||!std::isfinite(p0.maximum)||!std::isfinite(p0.initial)||p0.minimum>p0.maximum||p0.initial<p0.minimum||p0.initial>p0.maximum)throw std::runtime_error("Niepoprawne parametry modułu");params[j].store(p0.initial);}
   instance=api->create(sr,MAX_FRAMES,asset.c_str());if(!instance)throw std::runtime_error("Inicjalizacja modułu nie powiodła się; sprawdź zasób IR");
  }catch(...){dlclose(lib);lib=nullptr;throw;}
 }
 ~Node(){if(instance)api->destroy(instance);if(lib)dlclose(lib);}
};
struct Graph {std::vector<std::shared_ptr<Node>> nodes;};
struct Bus {std::atomic<float> gain{.7},pan{0},peak{0},rms{0};std::atomic<bool> mute{false},solo{false};float currentGain=.7,currentPan=0;};
struct Engine {
 jack_client_t* client=nullptr;jack_port_t *input[2]{},*output[2]{},*midi=nullptr;
 std::atomic<Graph*> graph{new Graph};std::atomic<bool> busy{false},quiet{false},silent{true},invalidRate{false};
 std::atomic<float> bpm{120},master{.7},peak{0},rms{0},ceiling{.98};std::atomic<bool> limiter{true};
 std::atomic<uint64_t> xruns{0},clips{0},badSamples{0},midiOverflow{0},blocks{0};
 std::atomic<unsigned> learnNode{0},learnParameter{0};std::atomic<int> lastCC{-1};
 std::unique_ptr<Graph> pending;
 Bus bus[2];float fade=0,masterSmooth=.7;double beat=0,sr=44100;unsigned nextId=1;
 std::array<std::array<std::array<float,MAX_FRAMES>,2>,2> audio{};
 std::array<std::array<float,MAX_FRAMES>,2> wet{};
 ~Engine(){if(client){jack_deactivate(client);jack_client_close(client);}delete graph.exchange(nullptr);}
 static int xrun(void* p){static_cast<Engine*>(p)->xruns.fetch_add(1,std::memory_order_relaxed);return 0;}
 static int rate(jack_nframes_t n,void* p){auto& e=*static_cast<Engine*>(p);if(e.sr!=n)e.invalidRate.store(true);return 0;}
 static void shutdown(void*){running.store(false);}
 static int callback(jack_nframes_t frames,void* ptr) noexcept {
#ifdef __SSE__
  _mm_setcsr(_mm_getcsr()|0x8040);
#endif
#ifdef __aarch64__
  uint64_t fpcr;asm volatile("mrs %0, fpcr":"=r"(fpcr));fpcr|=(1u<<24);asm volatile("msr fpcr, %0"::"r"(fpcr));
#endif
  auto& e=*static_cast<Engine*>(ptr);e.busy.store(true);
  Graph* g=e.graph.load();
  float* out[]{static_cast<float*>(jack_port_get_buffer(e.output[0],frames)),static_cast<float*>(jack_port_get_buffer(e.output[1],frames))};
  if(frames>MAX_FRAMES||e.invalidRate.load()||!g){for(int c=0;c<2;++c)std::fill_n(out[c],frames,0);e.busy.store(false);return 0;}
  for(int c=0;c<2;++c){const auto* in=static_cast<const float*>(jack_port_get_buffer(e.input[c],frames));
   for(unsigned i=0;i<frames;++i)e.audio[0][c][i]=std::isfinite(in[i])?in[i]:0;
   std::fill_n(e.audio[1][c].data(),frames,0);
  }
  std::array<JAMidi,256> events{};uint32_t count=0;void* midiBuffer=jack_port_get_buffer(e.midi,frames);
  const uint32_t total=jack_midi_get_event_count(midiBuffer);
  for(uint32_t i=0;i<total;++i){jack_midi_event_t m{};if(jack_midi_event_get(&m,midiBuffer,i)||m.size>3)continue;
   if(count==events.size()){e.midiOverflow.fetch_add(1,std::memory_order_relaxed);break;}
   auto& v=events[count++];v.frame=m.time;v.size=uint32_t(m.size);std::copy_n(m.buffer,m.size,v.bytes);
  }
  for(unsigned i=0;i<count;++i)if(events[i].size==3&&(events[i].bytes[0]&240)==176)e.lastCC.store((events[i].bytes[0]&15)*128+events[i].bytes[1]);
  const double tempo=e.bpm.load(std::memory_order_relaxed);
  for(const auto& owner:g->nodes){Node& node=*owner;auto& a=e.audio[node.route];
   const bool bypass=node.bypass.load(std::memory_order_relaxed);if(bypass&&node.mix==0)continue;
   std::array<float,JA_MAX_PARAMETERS> values{};for(unsigned p=0;p<node.api->parameter_count;++p){
    if(e.learnNode.load()==node.id&&e.learnParameter.load()==p){for(unsigned m=0;m<count;++m)if(events[m].size==3&&(events[m].bytes[0]&240)==176){node.mapping[p].store((events[m].bytes[0]&15)*128+events[m].bytes[1]);e.learnNode.store(0);break;}}
    const int mapping=node.mapping[p].load();
    if(mapping>=0)for(unsigned m=0;m<count;++m)if(events[m].size==3&&(events[m].bytes[0]&240)==176&&mapping==(events[m].bytes[0]&15)*128+events[m].bytes[1]){
     const auto& metadata=node.api->parameters[p];float v=metadata.minimum+(metadata.maximum-metadata.minimum)*events[m].bytes[2]/127.f;if(metadata.integer)v=std::round(v);node.params[p].store(v);
    }
    values[p]=node.params[p].load(std::memory_order_relaxed);
   }
   JAProcess b{sizeof(JAProcess),frames,e.sr,tempo,e.beat,1,{a[0].data(),a[1].data()},{e.wet[0].data(),e.wet[1].data()},values.data(),events.data(),count};
   node.api->process(node.instance,&b);
   for(unsigned i=0;i<frames;++i){node.mix=std::clamp(node.mix+(bypass?-1.f:1.f)/float(e.sr*.01),0.f,1.f);
    for(int c=0;c<2;++c){float v=e.wet[c][i];if(!std::isfinite(v)){v=0;e.badSamples.fetch_add(1,std::memory_order_relaxed);}
     if(node.api->instrument)a[c][i]+=v*node.mix;else a[c][i]+=(v-a[c][i])*node.mix;
    }
   }
  }
  const bool anySolo=e.bus[0].solo.load()||e.bus[1].solo.load();
  float maxPeak=0;double squares=0;float busPeak[2]{};double busSquares[2]{};
  const float master=e.master.load(),ceiling=e.ceiling.load();const bool limit=e.limiter.load(),quiet=e.quiet.load();
  for(unsigned i=0;i<frames;++i){float mix[2]{};
   for(int r=0;r<2;++r){auto& b=e.bus[r];const float gain=(b.mute.load()||(anySolo&&!b.solo.load()))?0:b.gain.load();
    b.currentGain+=(gain-b.currentGain)*.002;b.currentPan+=(b.pan.load()-b.currentPan)*.002;
    const double theta=(b.currentPan+1)*.7853981633974483;const float pan[]{float(std::cos(theta)*1.41421356237),float(std::sin(theta)*1.41421356237)};
    for(int c=0;c<2;++c){float v=e.audio[r][c][i]*b.currentGain*pan[c];mix[c]+=v;busPeak[r]=std::max(busPeak[r],std::abs(v));busSquares[r]+=double(v)*v;}
   }
   e.fade=std::clamp(e.fade+(quiet?-1.f:1.f)/float(e.sr*.02),0.f,1.f);e.masterSmooth+=(master-e.masterSmooth)*.002;
   for(int c=0;c<2;++c){float v=mix[c]*e.masterSmooth*e.fade;if(!std::isfinite(v)){v=0;e.badSamples.fetch_add(1,std::memory_order_relaxed);}
    if(std::abs(v)>ceiling){e.clips.fetch_add(1,std::memory_order_relaxed);if(limit)v=std::clamp(v,-ceiling,ceiling);}
    out[c][i]=v;maxPeak=std::max(maxPeak,std::abs(v));squares+=double(v)*v;
   }
  }
  for(int r=0;r<2;++r){e.bus[r].peak.store(busPeak[r]);e.bus[r].rms.store(float(std::sqrt(busSquares[r]/(2*frames))));}
  e.peak.store(maxPeak);e.rms.store(float(std::sqrt(squares/(2*frames))));e.beat+=frames*tempo/(60*e.sr);e.silent.store(e.fade==0);e.blocks.fetch_add(1);e.busy.store(false);return 0;
 }
 void start(){jack_status_t status{};client=jack_client_open("JerzyAudioPlatform",JackNoStartServer,&status);if(!client)throw std::runtime_error("JACK nie działa");sr=jack_get_sample_rate(client);
  for(int c=0;c<2;++c){std::string in="wejscie_"+std::to_string(c+1),out="wyjscie_"+std::to_string(c+1);input[c]=jack_port_register(client,in.c_str(),JACK_DEFAULT_AUDIO_TYPE,JackPortIsInput,0);output[c]=jack_port_register(client,out.c_str(),JACK_DEFAULT_AUDIO_TYPE,JackPortIsOutput,0);if(!input[c]||!output[c])throw std::runtime_error("Nie można utworzyć portów JACK");}
  midi=jack_port_register(client,"midi",JACK_DEFAULT_MIDI_TYPE,JackPortIsInput,0);if(!midi)throw std::runtime_error("Nie można utworzyć portu MIDI");
  jack_set_process_callback(client,callback,this);jack_set_xrun_callback(client,xrun,this);jack_set_sample_rate_callback(client,rate,this);jack_on_shutdown(client,shutdown,this);
  if(jack_activate(client))throw std::runtime_error("Nie można aktywować klienta JACK");
 }
 void swap(std::unique_ptr<Graph> next){quiet.store(true);auto end=std::chrono::steady_clock::now()+std::chrono::seconds(3);
  while(!silent.load()){if(std::chrono::steady_clock::now()>end){quiet.store(false);throw std::runtime_error("Audio nie potwierdziło wyciszenia grafu");}std::this_thread::sleep_for(std::chrono::milliseconds(1));}
  Graph* old=graph.exchange(next.release());while(busy.load())std::this_thread::yield();delete old;quiet.store(false);
 }
 std::shared_ptr<Node> find(unsigned id){if(pending)for(auto& n:pending->nodes)if(n->id==id)return n;for(auto& n:graph.load()->nodes)if(n->id==id)return n;throw std::runtime_error("Nie ma takiej instancji");}
 std::string status(){std::ostringstream o;o<<"{\"ok\":true,\"client\":"<<json(jack_get_client_name(client))<<",\"sample_rate\":"<<sr<<",\"buffer\":"<<jack_get_buffer_size(client)<<",\"buffer_ms\":"<<1000.*jack_get_buffer_size(client)/sr<<",\"cpu\":"<<jack_cpu_load(client)<<",\"xruns\":"<<xruns<<",\"clips\":"<<clips<<",\"invalid_samples\":"<<badSamples<<",\"blocks\":"<<blocks<<",\"midi_overflow\":"<<midiOverflow<<",\"restart_required\":"<<(invalidRate?"true":"false")<<",\"peak\":"<<peak<<",\"rms\":"<<rms<<",\"master\":"<<master<<",\"last_cc\":"<<lastCC<<",\"learn_node\":"<<learnNode<<",\"bpm\":"<<bpm<<",\"limiter\":"<<(limiter?"true":"false")<<",\"ceiling\":"<<ceiling<<",\"buses\":[";
  for(int r=0;r<2;++r){if(r)o<<',';auto& b=bus[r];o<<"{\"gain\":"<<b.gain<<",\"pan\":"<<b.pan<<",\"mute\":"<<(b.mute?"true":"false")<<",\"solo\":"<<(b.solo?"true":"false")<<",\"peak\":"<<b.peak<<",\"rms\":"<<b.rms<<'}';}o<<"]}";return o.str();
 }
 std::string list(bool staging=false){std::ostringstream o;o<<"{\"ok\":true,\"nodes\":[";bool first=true;for(auto& n:(staging&&pending?pending.get():graph.load())->nodes){if(!first)o<<',';first=false;
  o<<"{\"id\":"<<n->id<<",\"module\":"<<json(n->api->id)<<",\"name\":"<<json(n->api->name)<<",\"path\":"<<json(n->path)<<",\"asset\":"<<json(n->asset)<<",\"route\":"<<n->route<<",\"instrument\":"<<(n->api->instrument?"true":"false")<<",\"bypass\":"<<(n->bypass?"true":"false")<<",\"latency\":"<<n->api->latency(n->instance)<<",\"parameters\":[";
  for(unsigned p=0;p<n->api->parameter_count;++p){if(p)o<<',';const auto& v=n->api->parameters[p];o<<"{\"id\":"<<json(v.id)<<",\"label\":"<<json(v.label)<<",\"unit\":"<<json(v.unit)<<",\"choices\":"<<json(v.choices)<<",\"min\":"<<v.minimum<<",\"max\":"<<v.maximum<<",\"default\":"<<v.initial<<",\"integer\":"<<v.integer<<",\"mapping\":"<<n->mapping[p]<<",\"value\":"<<n->params[p]<<'}';}o<<"]}";
  }o<<"]}";return o.str();}
 std::string command(const std::string& line){std::istringstream in(line);std::string cmd;in>>cmd;
  if(cmd=="STATUS")return status();
  if(cmd=="LIST")return list();
  if(cmd=="PENDING")return list(true);
  if(cmd=="BEGIN"){if(pending)throw std::runtime_error("Transakcja już trwa");pending=std::make_unique<Graph>();return "{\"ok\":true}";}
  if(cmd=="ABORT"){pending.reset();return "{\"ok\":true}";}
  if(cmd=="COMMIT"){if(!pending)throw std::runtime_error("Brak transakcji");swap(std::move(pending));return "{\"ok\":true}";}
  if(cmd=="ADD"){int route;std::string path,asset;if(!(in>>route>>std::quoted(path)>>std::quoted(asset))||route<0||route>1)throw std::runtime_error("Niepoprawny tor lub ścieżka");
   auto node=std::make_shared<Node>(nextId++,route,path,asset,sr);if(pending)pending->nodes.push_back(node);else {auto next=std::make_unique<Graph>(*graph.load());next->nodes.push_back(node);swap(std::move(next));}return "{\"ok\":true,\"id\":"+std::to_string(node->id)+"}";}
  if(cmd=="REMOVE"||cmd=="MOVE"){unsigned id,index=0;if(!(in>>id))throw std::runtime_error("Brak numeru instancji");auto node=find(id);auto next=std::make_unique<Graph>(*graph.load());std::erase(next->nodes,node);
   if(cmd=="MOVE"){if(!(in>>index)||index>next->nodes.size())throw std::runtime_error("Niepoprawna pozycja");next->nodes.insert(next->nodes.begin()+index,node);}swap(std::move(next));}
  else if(cmd=="PARAM"){unsigned id,index;float v;if(!(in>>id>>index>>v)||!std::isfinite(v))throw std::runtime_error("Niepoprawny parametr");auto n=find(id);if(index>=n->api->parameter_count)throw std::runtime_error("Brak parametru");const auto& p=n->api->parameters[index];if(v<p.minimum||v>p.maximum||(p.integer&&v!=std::round(v)))throw std::runtime_error("Wartość poza zakresem");n->params[index].store(v);}
  else if(cmd=="LEARN"||cmd=="MAP"){unsigned id,p;int mapping=-1;if(!(in>>id>>p))throw std::runtime_error("Niepoprawne mapowanie MIDI");auto n=find(id);if(p>=n->api->parameter_count)throw std::runtime_error("Brak parametru MIDI");if(cmd=="LEARN"){learnParameter.store(p);learnNode.store(id);}else{if(!(in>>mapping)||mapping<-1||mapping>2047)throw std::runtime_error("Niepoprawny kanał lub CC");n->mapping[p].store(mapping);}}
  else if(cmd=="BYPASS"){unsigned id;int v;if(!(in>>id>>v)||(v!=0&&v!=1))throw std::runtime_error("Niepoprawny bypass");find(id)->bypass.store(v);}
  else if(cmd=="MIX"){int r,m,s;float g,p;if(!(in>>r>>g>>p>>m>>s)||r<0||r>1||!std::isfinite(g)||!std::isfinite(p)||g<0||g>2||p<-1||p>1||(m!=0&&m!=1)||(s!=0&&s!=1))throw std::runtime_error("Niepoprawne ustawienia miksera");bus[r].gain.store(g);bus[r].pan.store(p);bus[r].mute.store(m);bus[r].solo.store(s);}
  else if(cmd=="MASTER"||cmd=="BPM"||cmd=="CEILING"){float v;if(!(in>>v)||!std::isfinite(v))throw std::runtime_error("Niepoprawna wartość");if(cmd=="MASTER"&&v>=0&&v<=2)master.store(v);else if(cmd=="BPM"&&v>=20&&v<=400)bpm.store(v);else if(cmd=="CEILING"&&v>=.1&&v<=1)ceiling.store(v);else throw std::runtime_error("Wartość poza zakresem");}
  else if(cmd=="LIMITER"){int v;if(!(in>>v)||(v!=0&&v!=1))throw std::runtime_error("Niepoprawny limiter");limiter.store(v);}
  else throw std::runtime_error("Nieznane polecenie");
  return "{\"ok\":true}";
 }
};
}
int main(int argc,char** argv){
 try{std::string path=argc>1?argv[1]:"/tmp/jerzy-audio-platform.sock";
  if(path.size()>=sizeof(sockaddr_un::sun_path))throw std::runtime_error("Zbyt długa ścieżka gniazda");
  std::signal(SIGINT,signalHandler);std::signal(SIGTERM,signalHandler);std::signal(SIGPIPE,SIG_IGN);
  // Never unlink another live engine's socket.
  int fd=socket(AF_UNIX,SOCK_STREAM,0);if(fd<0)throw std::runtime_error("Brak gniazda sterowania");sockaddr_un addr{};addr.sun_family=AF_UNIX;std::strcpy(addr.sun_path,path.c_str());
  if(bind(fd,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))){close(fd);throw std::runtime_error("Gniazdo istnieje; sprawdź czy poprzedni silnik nadal działa");}
  chmod(path.c_str(),0600);if(listen(fd,8)){close(fd);unlink(path.c_str());throw std::runtime_error("Nie można nasłuchiwać");}
  try{Engine e;e.start();std::cout<<"Silnik gotowy: "<<jack_get_client_name(e.client)<<std::endl;
   while(running){pollfd p{fd,POLLIN,0};if(poll(&p,1,250)<=0)continue;int peer=accept(fd,nullptr,nullptr);if(peer<0)continue;timeval timeout{2,0};setsockopt(peer,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));setsockopt(peer,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout));
    std::string line;char buffer[1024];while(line.find('\n')==std::string::npos&&line.size()<8192){ssize_t n=read(peer,buffer,sizeof(buffer));if(n<=0)break;line.append(buffer,size_t(n));}
    std::string reply;try{if(line.size()>=8192)throw std::runtime_error("Za długie polecenie");reply=e.command(line);}catch(const std::exception& ex){reply="{\"ok\":false,\"error\":"+json(ex.what())+"}";}reply+='\n';size_t pos=0;while(pos<reply.size()){ssize_t n=write(peer,reply.data()+pos,reply.size()-pos);if(n<=0)break;pos+=size_t(n);}close(peer);
   }
  }catch(...){close(fd);unlink(path.c_str());throw;}close(fd);unlink(path.c_str());return 0;
 }catch(const std::exception& e){std::cerr<<"Błąd: "<<e.what()<<'\n';return 1;}
}
