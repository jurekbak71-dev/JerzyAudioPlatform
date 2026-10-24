from pathlib import Path
import re,json,hashlib,shutil,csv
root=Path('/workspace/JerzyAudioPlatform');src=Path('/workspace/reference/bass-pro-modal/PRO/Source');dst=root/'modules/bass-ambient-pro-original';(dst/'vendor').mkdir(parents=True,exist_ok=True)
files=['Core.h','ProEngines.h','ModalExciter.h','Parameters.def','ProParameters.def','FXParameters.def','MixerParameters.def','PerformanceParameters.def','PluginProcessor.cpp']
for name in files:shutil.copy2(src/name,dst/'vendor'/name)
provenance={'repository':'https://github.com/jurekbak71-dev/JerzyBassAmbientVST3','commit':'673e0def70d06e29d35ba3e69c40d04f0e9c9abf','original_files_sha256':{'PRO/Source/'+n:hashlib.sha256((src/n).read_bytes()).hexdigest() for n in files},'import':'Original PRO modal DSP, separate native adapter. No VST GUI or composer timeline port.'}
(dst/'PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n');shutil.copy2(root/'modules/bass-ambient-original/LICENSE.txt',dst/'LICENSE.txt')
items=[]
def item(key,label,expr,lo,hi,kind='float',choices='',group=0):items.append(dict(key=key,label=label,expr=expr,lo=str(lo),hi=str(hi),kind=kind,choices=choices,group=int(group)))
def defs(name,prefix='',expr='p',labelprefix=''):
 for line in (src/name).read_text().splitlines():
  m=re.match(r'#include "(.*?)"',line)
  if m:defs(m[1],prefix,expr,labelprefix);continue
  m=re.match(r'(BOOL|FLOAT|INT|CHOICE|CHOICE_DEN)\((.*)\)',line)
  if not m:continue
  kind=m[1];a=next(csv.reader([m[2]],skipinitialspace=True));f=a[0];e=expr+'.'+f
  if kind=='BOOL':lo,hi,label,g,ch=0,1,a[1],a[2],''
  elif kind in ('FLOAT','INT'):lo,hi,label,g,ch=a[1],a[2],a[4 if kind=='FLOAT' else 3],a[5 if kind=='FLOAT' else 4],''
  elif kind=='CHOICE':lo,hi,label,g,ch=0,len(a[3].split('|'))-1,a[1],a[2],a[3]
  else:lo,hi,label,g,ch=0,3,a[1],a[2],'2|4|8|16'
  item(prefix+f,labelprefix+label,e,lo,hi,kind.lower(),ch,g)
def order(prefix,expr,labelprefix=''):
 for k in range(6):item(prefix+'order'+str(k),labelprefix+'FX slot '+str(k+1),expr+f'.order[{k}]',0,5,'choice','Drive / Comp|Chorus|Delay|Granular|Reverb|Width',3)
defs('Parameters.def');order('','p')
for prefix,expr,label in [('pad_','p.padRack','Ambient '),('master_','p.masterRack','Master ')]:defs('FXParameters.def',prefix,expr,label);order(prefix,expr,label)
item('masterFX','Master FX amount','p.masterFX',0,1)
for lane,label in enumerate(['Kick','Snare','Hi-hat','Aux']):
 for key,lo,hi,kind in [('enabled',0,1,'bool'),('level',0,1,'float'),('drive',0,1,'float'),('tone',0,1,'float'),('cutoff',40,18000,'float'),('decay',.015,2,'float'),('pan',-1,1,'float')]:item(f'drum{lane}_{key}',label+' '+key,f'p.drumSounds[{lane}].{key}',lo,hi,kind,group=8+lane)
 for step in range(64):item(f'drum{lane}_step{step}',label+' step '+str(step+1),f'p.drumGrid[{lane}][{step}]',0,127,'int',group=12)
for prefix,expr,label in [('arp_','p.arpRack','Arpeggio '),('drums_','p.drumsRack','Drums '),('krell_','p.krellRack','Krell ')]:defs('FXParameters.def',prefix,expr,label);order(prefix,expr,label)
defs('PerformanceParameters.def')
for f,label in [('bassBody','Bass: modal body'),('bassAttackTransient','Bass: strike excitation'),('padBody','Ambient: modal body'),('padAttackTransient','Ambient: strike excitation')]:item(f,label,'p.'+f,0,1,group=27)
assert len({i['key'] for i in items})==len(items)
q=lambda s:json.dumps(str(s),ensure_ascii=False)
assign=[];metadata=[];continuous=[];smooth=[]
for idx,i in enumerate(items):
 e=i['expr'];k=i['kind'];v=f'v[{idx}]'
 value=f'({v}>.5f)' if k=='bool' else f'den[std::clamp(int(std::lround({v})),0,3)]' if k=='choice_den' else f'int(std::lround({v}))' if k in ('int','choice') else v
 assign.append(e+'='+value+';')
 initial='1' if k=='choice_den' else '0' if i['key']=='bass' else f'float({e})'
 if i['key']=='clockSource':i['hi']='1';i['choices']='Wewnętrzny|Host JACK'
 if i['key']=='performanceSource':i['hi']='2';i['choices']='Legacy|MIDI|JAM'
 metadata.append('{'+','.join([q(i['key']),q(i['label']),q(''),q(i['choices']),i['lo'],i['hi'],initial,'0' if k=='float' else '1'])+'}')
 if k=='float':
  c=e.replace('p.','s.current.',1);prev=e.replace('p.','previous.',1);continuous.append(c+'='+prev+';');smooth.append(c+f'+=({e}-{c})*smoothing;')
(dst/'assign.inc').write_text('\n'.join(assign)+'\n');(dst/'metadata.inc').write_text(',\n'.join(metadata)+'\n');(dst/'continuous.inc').write_text('\n'.join(continuous)+'\n');(dst/'smooth.inc').write_text('\n'.join(smooth)+'\n')
manifest={'id':dst.name,'name':'Jerzy Bass Ambient PRO — modalny DSP','version':'0.2.1','minimum_host_version':'0.2.1','abi':1,'library':dst.name+'.so','instrument':True,'category':'instrument','source':provenance,'compatibility':'reference-comparison-required','parameter_groups':{i['key']:i['group'] for i in items},'scope':'PRO modal instruments: bass, ambient, arp, drums, Krell, mixer, resource-managed FX. VST GUI, composer arrangement and file export are not implemented.'}
(dst/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');(dst/'README_PL.txt').write_text(manifest['scope']+'\nWłączaj instrumenty pojedynczo. Początkowo bass/pad/arp/drums/krell wyłączone. JAM uruchamia generatory; MIDI przyjmuje kanały1/2/3/4/10. Pełne DSP może przekroczyć budżet Pi: host pokazuje przeciążenie i ustawia bypass.\n')
print(len(items),'PRO parameters generated')
