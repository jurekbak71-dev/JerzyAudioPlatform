#include <jack/jack.h>
#include <jack/midiport.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <poll.h>
#include <unistd.h>
#include <array>
#include <atomic>
#include <chrono>
#include <csignal>
#include <cstring>
#include <fstream>
#include <string>
#include <algorithm>
struct Event{unsigned size;std::array<unsigned char,3> bytes;};
struct Bridge{
 jack_client_t* client=nullptr;jack_port_t* port=nullptr;std::array<Event,1024> queue{};std::atomic<unsigned> head{0},tail{0};std::atomic<bool> panic{false},running{true};std::atomic<unsigned long long> sent{0},dropped{0};
 static int callback(jack_nframes_t frames,void* ptr){auto& b=*static_cast<Bridge*>(ptr);void* buffer=jack_port_get_buffer(b.port,frames);jack_midi_clear_buffer(buffer);
  if(b.panic.exchange(false)){b.tail.store(b.head.load(std::memory_order_acquire),std::memory_order_release);for(unsigned ch=0;ch<16;++ch){unsigned char off[]{static_cast<unsigned char>(0xb0+ch),123,0};jack_midi_event_write(buffer,0,off,3);}return 0;}
  unsigned tail=b.tail.load(std::memory_order_relaxed);const unsigned head=b.head.load(std::memory_order_acquire);unsigned count=0;
  while(tail!=head&&count++<128){auto& e=b.queue[tail%b.queue.size()];if(jack_midi_event_write(buffer,0,e.bytes.data(),e.size)){b.dropped++;b.panic.store(true);}else b.sent++;++tail;}b.tail.store(tail,std::memory_order_release);return 0;
 }
 bool push(const unsigned char* bytes,unsigned n){if(n==0||n>3||bytes[0]<0x80)return false;for(unsigned i=1;i<n;++i)if(bytes[i]>=0x80)return false;unsigned headNow=head.load(std::memory_order_relaxed);if(headNow-tail.load(std::memory_order_acquire)>=queue.size()){dropped++;panic.store(true);return false;}auto& e=queue[headNow%queue.size()];e.size=n;std::copy_n(bytes,n,e.bytes.begin());head.store(headNow+1,std::memory_order_release);return true;}
 ~Bridge(){if(client){jack_deactivate(client);jack_client_close(client);}}
};
static Bridge* active=nullptr;
static void stop(int){if(active)active->running.store(false);}
int main(int argc,char** argv){if(argc!=3)return 2;std::string path=argv[1],status=argv[2];if(path.size()>=sizeof(sockaddr_un::sun_path))return 2;Bridge b;active=&b;std::signal(SIGINT,stop);std::signal(SIGTERM,stop);jack_status_t code{};b.client=jack_client_open("JerzyBluetoothMIDI",JackNoStartServer,&code);if(!b.client)return 3;b.port=jack_port_register(b.client,"out",JACK_DEFAULT_MIDI_TYPE,JackPortIsOutput,0);if(!b.port)return 4;jack_set_process_callback(b.client,Bridge::callback,&b);jack_on_shutdown(b.client,[](void* p){static_cast<Bridge*>(p)->running.store(false);},&b);if(jack_activate(b.client))return 5;
 int fd=socket(AF_UNIX,SOCK_DGRAM|SOCK_CLOEXEC,0);sockaddr_un addr{};addr.sun_family=AF_UNIX;std::strcpy(addr.sun_path,path.c_str());if(fd<0||bind(fd,reinterpret_cast<sockaddr*>(&addr),sizeof(addr)))return 6;chmod(path.c_str(),0600);std::string target;auto updated=std::chrono::steady_clock::now()-std::chrono::seconds(2);
 while(b.running){pollfd item{fd,POLLIN,0};if(poll(&item,1,200)>0){unsigned char data[256];auto n=recv(fd,data,sizeof(data),0);if(n==1&&data[0]=='!')b.panic.store(true);else if(n>1&&data[0]=='@'){std::string name(reinterpret_cast<char*>(data+1),size_t(n-1));if(name.size()<90&&name.starts_with("JerzyAudioPlatform")&&name.ends_with(":midi")&&std::all_of(name.begin(),name.end(),[](unsigned char c){return std::isalnum(c)||c=='_'||c=='-'||c==':';}))target=name;}else if(n>0)b.push(data,unsigned(n));}
  if(std::chrono::steady_clock::now()-updated>=std::chrono::seconds(1)){bool connected=false;if(!target.empty()){jack_connect(b.client,jack_port_name(b.port),target.c_str());connected=jack_port_connected_to(b.port,target.c_str());}
   std::ofstream out(status+".tmp");out<<"{\"pid\":"<<getpid()<<",\"running\":true,\"connected\":"<<(connected?"true":"false")<<",\"sent\":"<<b.sent<<",\"dropped\":"<<b.dropped<<"}\n";out.close();rename((status+".tmp").c_str(),status.c_str());updated=std::chrono::steady_clock::now();}
 }
 b.panic.store(true);usleep(30000);close(fd);unlink(path.c_str());std::ofstream(status)<<"{\"running\":false,\"connected\":false}\n";return 0;
}
