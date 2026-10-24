from pathlib import Path
import json,re
R=Path(__file__).resolve().parents[1]
for id,namespace,entries in [
 ('small-clone-original','jerzy',[('rate','Tempo LFO'),('depth','Głębokość'),('mix','Proporcja efektu'),('color','Barwa i sprzężenie'),('level','Poziom'),('model','Model obwodu'),('stereo','Szerokość stereo'),('filter','Zatrzymanie modulacji'),('bypass','Bypass oryginału'),('sync','Synchronizacja tempa'),('division','Podział rytmiczny')]),
 ('atomic-cluster-original','atomiccluster',[('volume','Poziom'),('blend','Proporcja efektu'),('speed','Prędkość'),('atoms','Liczba atomów'),('smooth','Wygładzanie'),('flat','Wyrównanie dynamiki'),('bypass','Bypass oryginału'),('sync','Synchronizacja tempa'),('division','Podział rytmiczny'),('tapEnabled','Tap tempo'),('motion','Ruch atomów'),('stereo','Ruch stereo')])]:
 params=',\n'.join('{'+json.dumps(key)+','+json.dumps(label,ensure_ascii=False)+',"0–1","",0,1,float(defaults['+str(i)+']),0}' for i,(key,label) in enumerate(entries))
 offset='-atomiccluster::fftSize' if id.startswith('atomic') else ''
 source=f'''#include "jerzy_module.h"
#include <memory>
#include "vendor/Dsp.h"
using namespace {namespace};
static void* create(double sr,uint32_t,const char*){{try{{auto s=std::make_unique<Engine>();s->reset(sr,defaults());return s.release();}}catch(...){{return nullptr;}}}}
static void destroy(void* s){{delete static_cast<Engine*>(s);}}
static void process(void* s,const JAProcess* b){{Values p;for(int i=0;i<NumParams;++i)p[i]=b->parameters[i];for(uint32_t i=0;i<b->frames;++i){{double beat=b->playing?b->beat+(double(i){offset})*b->bpm/(60*b->sample_rate):NAN;auto y=static_cast<Engine*>(s)->process(b->input[0][i],b->input[1][i],p,b->bpm,beat);for(int c=0;c<2;++c)b->output[c][i]=float(y[c]);}}}}
static uint32_t latency(void*){{return {2048 if id.startswith('atomic') else 0};}}
extern "C" const JAModule* ja_module(){{static const auto defaults={namespace}::defaults();static const JAParameter params[]={{
{params}
}};static const JAModule m{{sizeof(JAModule),JA_ABI,"{id}","Jerzy {id.replace('-original','').replace('-',' ')} — oryginalny DSP","0.2.0",0,NumParams,params,create,destroy,process,latency}};return &m;}}
'''
 (R/'modules'/id/'module.cpp').write_text(source)
# Memory Delay: exact original single-sample API.
entries=[('blend','Proporcja efektu'),('level','Poziom'),('feedback','Sprzężenie'),('modRate','Tempo modulacji'),('depth','Głębokość'),('delay','Czas opóźnienia'),('model','Model'),('wave','Kształt modulacji'),('bypass','Bypass oryginału'),('boost','Wzmocnienie'),('squelch','Bramka'),('modEnable','Modulacja'),('tempoSync','Synchronizacja tempa'),('division','Podział rytmiczny')]
params=',\n'.join('{'+json.dumps(key)+','+json.dumps(label,ensure_ascii=False)+',"0–1","",0,1,float(Jerzy::defaults['+str(i)+']),0}' for i,(key,label) in enumerate(entries))
(R/'modules/memory-delay-original/module.cpp').write_text('''#include "jerzy_module.h"
#include <memory>
#include "vendor/dsp.h"
static void* create(double sr,uint32_t,const char*){try{auto s=std::make_unique<Jerzy::Engine>();s->prepare(sr);return s.release();}catch(...){return nullptr;}}
static void destroy(void* s){delete static_cast<Jerzy::Engine*>(s);}
static void process(void* s,const JAProcess* b){Jerzy::Parameters p;for(int i=0;i<Jerzy::Count;++i)p.value[i]=b->parameters[i];for(uint32_t i=0;i<b->frames;++i){double x[]{b->input[0][i],b->input[1][i]},y[2];static_cast<Jerzy::Engine*>(s)->tick(x,y,2,p,b->bpm);for(int c=0;c<2;++c)b->output[c][i]=float(y[c]);}}
static uint32_t latency(void*){return 0;}
extern "C" const JAModule* ja_module(){static const JAParameter p[]={
'''+params+'''
};static const JAModule m{sizeof(JAModule),JA_ABI,"memory-delay-original","Jerzy Memory Delay — oryginalny DSP","0.2.0",0,Jerzy::Count,p,create,destroy,process,latency};return &m;}
''')
# All MX parameters, including both engines, all algorithms and four wet FX slots.
items=[]
def add(expr,key,label):items.append((expr,key,label))
for f,label in [('mix','Proporcja efektu'),('inputTrim','Poziom wejściowy'),('outputTrim','Poziom wyjściowy'),('routing','Routing'),('bypass','Bypass oryginału'),('spill','Ogon efektu'),('machineCondition','Stan mechanizmu')]:add('p.'+f,f,label)
for i in range(4):
 for f,label in [('type','Typ'),('amount','Ilość'),('rate','Tempo'),('depth','Głębokość'),('drive','Nasycenie'),('route','Routing')]:add(f'p.fx[{i}].{f}',f'fx{i}_{f}',f'FX {i+1}: {label}')
for i in range(2):
 for f,label in [('algorithm','Algorytm'),('enable','Włączony'),('sync','Synchronizacja'),('division','Podział'),('time','Czas'),('feedback','Sprzężenie'),('level','Poziom'),('pan','Panorama'),('duck','Ducking')]:add(f'p.slot[{i}].{f}',f'slot{i}_{f}',f'Silnik {"AB"[i]}: {label}')
 for h in range(4):add(f'p.slot[{i}].headPan[{h}]',f'slot{i}_headPan{h}',f'Silnik {"AB"[i]}: panorama głowicy {h+1}')
 for a,name in enumerate(['Volante','El Capistan','Olivera','EC1','Brig','Deco','DIG','Space Echo 202','DM101']):
  for c in range(16):
   controller=Path('/workspace/reference/JerzyMXAnalogDelayVST3/source/mxdelay_controller.cpp').read_text()
   table=controller.split('const char* ctl[kAlgorithmCount][kAlgoControls]={',1)[1].split('};',1)[0]
   labels=re.findall(r'"([^"]*)"',table);assert len(labels)==144
   label=labels[a*16+c]
   if label.startswith('Unused'):continue
   add(f'p.slot[{i}].c[{a}][{c}]',f'slot{i}_algo{a}_{c}',f'Silnik {"AB"[i]}: {name} — {label}')
(R/'modules/mx-delay-original/assign.inc').write_text('\n'.join(expr+'=b->parameters['+str(i)+'];' for i,(expr,key,label) in enumerate(items)))
(R/'modules/mx-delay-original/metadata.inc').write_text(',\n'.join('{'+json.dumps(key)+','+json.dumps(label,ensure_ascii=False)+',"0–1","",0,1,float('+expr+'),0}' for expr,key,label in items))
(R/'modules/mx-delay-original/module.cpp').write_text('''#include "jerzy_module.h"
#include <memory>
#include "vendor/mxdelay_dsp.h"
using DSP=JerzyAudio::MXDelayDSP<float>;
static void* create(double sr,uint32_t,const char*){try{auto s=std::make_unique<DSP>();s->prepare(sr,2);return s.release();}catch(...){return nullptr;}}
static void destroy(void* s){delete static_cast<DSP*>(s);}
static void process(void* ptr,const JAProcess* b){JerzyAudio::MXDelayParams p;
#include "assign.inc"
 float* in[]{const_cast<float*>(b->input[0]),const_cast<float*>(b->input[1])};float* out[]{b->output[0],b->output[1]};double peak=0;static_cast<DSP*>(ptr)->process(in,out,2,int(b->frames),p,b->bpm,peak);
}
static uint32_t latency(void*){return 0;}
extern "C" const JAModule* ja_module(){static const JerzyAudio::MXDelayParams p;static const JAParameter params[]={
#include "metadata.inc"
};static const JAModule m{sizeof(JAModule),JA_ABI,"mx-delay-original","Jerzy MX Analog Delay — oryginalny DSP","0.2.0",0,uint32_t(sizeof(params)/sizeof(params[0])),params,create,destroy,process,latency};return &m;}
''')
