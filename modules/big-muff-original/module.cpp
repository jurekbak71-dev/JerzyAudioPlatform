#include "jerzy_module.h"
#include "OriginalProcessor.h"
static void* create(double sr,uint32_t frames,const char*){try{auto s=std::make_unique<OriginalMuffDSP>();s->prepareToPlay(sr,int(frames));return s->isReady()?s.release():nullptr;}catch(...){return nullptr;}}
static void destroy(void* s){delete static_cast<OriginalMuffDSP*>(s);}
static void process(void* ptr,const JAProcess* b){auto& s=*static_cast<OriginalMuffDSP*>(ptr);for(int p=0;p<6;++p)s.controls[p].store(b->parameters[p]);for(int c=0;c<2;++c)std::copy_n(b->input[c],b->frames,b->output[c]);juce::AudioBuffer<float> buffer(b->output,2,int(b->frames));juce::MidiBuffer midi;s.processBlock(buffer,midi);}
static uint32_t latency(void* s){return uint32_t(static_cast<OriginalMuffDSP*>(s)->latencyFrames);}
extern "C" const JAModule* ja_module(){
 static std::string names=[](){std::string s="Legacy 0.1.0";for(const auto& r:muff::circuit::revisions){s+='|';s+=r.name;}return s;}();
 static const JAParameter p[]={{"volume","Poziom","","",0,1,.5,0},{"tone","Barwa","","",0,1,.5,0},{"sustain","Sustain","","",0,1,.5,0},{"model","Model klasyczny","","Triangle|Ram's Head|Op-Amp|Civil War|Green Russian|NYC",0,5,0,1},{"bypass","Bypass oryginału","","",0,1,0,1},{"circuit","Model obwodu","",names.c_str(),0,float(muff::circuit::revisions.size()),float(muff::circuit::revisions.size()),1}};
 static const JAModule m{sizeof(JAModule),JA_ABI,"big-muff-original","Jerzy Big Muff — oryginalny DSP","0.2.0",0,6,p,create,destroy,process,latency};return &m;
}
