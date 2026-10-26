#include <lv2/core/lv2.h>
#include <lv2/atom/util.h>
#include <lv2/midi/midi.h>
#include <lv2/urid/urid.h>
#include <lv2/worker/worker.h>
#include <lv2/state/state.h>
#include <cmath>
#include <cstring>
#include <new>
struct State {float* input=nullptr;float* output=nullptr;float* level=nullptr;LV2_Atom_Sequence* midi=nullptr;double rate=44100,phase=0;int note=-1;LV2_URID midiType=0,stateKey=0,floatType=0;float memory=.25f;const LV2_Worker_Schedule* scheduler=nullptr;float worked=0,last=-1;bool synth=false,worker=false;};
static LV2_Handle create(const LV2_Descriptor* d,double sr,const char*,const LV2_Feature* const* features){auto s=new State;s->rate=sr;s->synth=std::strstr(d->URI,"synth");s->worker=std::strstr(d->URI,"worker");for(unsigned i=0;features&&features[i];++i){if(!std::strcmp(features[i]->URI,LV2_URID__map)){auto map=static_cast<const LV2_URID_Map*>(features[i]->data);s->midiType=map->map(map->handle,LV2_MIDI__MidiEvent);s->stateKey=map->map(map->handle,"urn:jerzy:test:memory");s->floatType=map->map(map->handle,LV2_ATOM__Float);}if(!std::strcmp(features[i]->URI,LV2_WORKER__schedule))s->scheduler=static_cast<const LV2_Worker_Schedule*>(features[i]->data);}return s;}
static void connect(LV2_Handle h,uint32_t index,void* p){auto s=static_cast<State*>(h);if(index==0){if(s->synth)s->midi=static_cast<LV2_Atom_Sequence*>(p);else s->input=static_cast<float*>(p);}if(index==1)s->output=static_cast<float*>(p);if(index==2)s->level=static_cast<float*>(p);}
static void run(LV2_Handle h,uint32_t n){auto s=static_cast<State*>(h);if(s->worker&&s->last!=*s->level){s->last=*s->level;s->scheduler->schedule_work(s->scheduler->handle,sizeof(float),s->level);}auto seq=s->midi;const LV2_Atom_Event* event=seq?lv2_atom_sequence_begin(&seq->body):nullptr;
 for(unsigned i=0;i<n;++i){while(event&&!lv2_atom_sequence_is_end(&seq->body,seq->atom.size,event)&&event->time.frames<=i){auto bytes=static_cast<const uint8_t*>(LV2_ATOM_BODY_CONST(&event->body));if(event->body.type==s->midiType&&event->body.size>=2){auto status=bytes[0]&240;if(status==192)s->memory=float(bytes[1])/127;else if(event->body.size>=3&&status==144&&bytes[2])s->note=bytes[1];else if(event->body.size>=3&&(status==128||(status==144&&!bytes[2])||(status==176&&bytes[1]==123)))s->note=-1;}event=lv2_atom_sequence_next(event);}
  if(s->synth){s->output[i]=s->note<0?0:float(std::sin(s->phase)*.2**s->level*s->memory);s->phase+=6.283185307179586*440*std::exp2((s->note-69)/12.)/s->rate;}else s->output[i]=s->input[i]*(s->worker?s->worked:*s->level);
 }}
static void cleanup(LV2_Handle h){delete static_cast<State*>(h);}
static LV2_Worker_Status work(LV2_Handle,LV2_Worker_Respond_Function respond,LV2_Worker_Respond_Handle handle,uint32_t size,const void* data){return respond(handle,size,data);}
static LV2_Worker_Status response(LV2_Handle h,uint32_t size,const void* data){if(size==sizeof(float))std::memcpy(&static_cast<State*>(h)->worked,data,size);return LV2_WORKER_SUCCESS;}
static LV2_State_Status save(LV2_Handle h,LV2_State_Store_Function store,LV2_State_Handle handle,uint32_t,const LV2_Feature* const*){auto s=static_cast<State*>(h);return store(handle,s->stateKey,&s->memory,sizeof(float),s->floatType,LV2_STATE_IS_POD|LV2_STATE_IS_PORTABLE);}
static LV2_State_Status restore(LV2_Handle h,LV2_State_Retrieve_Function retrieve,LV2_State_Handle handle,uint32_t,const LV2_Feature* const*){auto s=static_cast<State*>(h);size_t size=0;uint32_t type=0,flags=0;auto value=retrieve(handle,s->stateKey,&size,&type,&flags);if(value&&size==sizeof(float)&&type==s->floatType)std::memcpy(&s->memory,value,size);return LV2_STATE_SUCCESS;}
static const void* extension(const char* uri){static const LV2_State_Interface state{save,restore};if(!std::strcmp(uri,LV2_STATE__interface))return &state;static const LV2_Worker_Interface worker{work,response,nullptr};return !std::strcmp(uri,LV2_WORKER__interface)?&worker:nullptr;}
extern "C" LV2_SYMBOL_EXPORT const LV2_Descriptor* lv2_descriptor(uint32_t index){static const LV2_Descriptor list[]={{"urn:jerzy:test:gain",create,connect,nullptr,run,nullptr,cleanup,nullptr},{"urn:jerzy:test:synth",create,connect,nullptr,run,nullptr,cleanup,extension},{"urn:jerzy:test:worker",create,connect,nullptr,run,nullptr,cleanup,extension},{"urn:jerzy:test:unsupported",create,connect,nullptr,run,nullptr,cleanup,nullptr}};return index<4?&list[index]:nullptr;}
