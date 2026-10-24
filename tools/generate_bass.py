"""Generate ABI metadata and assignments from audited original parameter definitions."""
import re,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=Path('/workspace/reference/JerzyBassAmbientVST3/Source')
# This generator is a one-time import tool; generated sources build without the reference checkout.
fx=(source/'FXParameters.def').read_text()
text=(source/'Parameters.def').read_text().replace('#include "FXParameters.def"',fx)
items=[]
def parse(text,prefix='',member=''):
 for line in text.splitlines():
  m=re.match(r'(BOOL|FLOAT|INT|CHOICE|CHOICE_DEN)\((.*)\)',line)
  if not m:continue
  kind=m[1];args=re.findall(r'"[^"]*"|[^,]+',m[2]);args=[a.strip() for a in args]
  f=args[0];choices='';unit=''
  if kind=='FLOAT':lo,hi=args[1:3];label=json.loads(args[4]);integer=0
  elif kind=='INT':lo,hi=args[1:3];label=json.loads(args[3]);integer=1
  else:
   label=json.loads(args[1]);integer=1;lo='0';hi='1'
   if kind=='CHOICE':choices=json.loads(args[3]);hi=str(len(choices.split('|'))-1)
   if kind=='CHOICE_DEN':choices='2|4|8|16';hi='3'
  label=label.replace('enabled','włączony').replace('level','poziom').replace('cutoff','częstotliwość').replace('seconds','sekundy').replace('amount','ilość')
  if f in ('bass','pad'):label='Bass START/STOP' if f=='bass' else 'Ambient START/STOP'
  if f=='scale':choices='Durowa|Molowa|Dorycka|Molowa harmoniczna|Pentatonika molowa';label='Skala'
  if f=='style':label='Styl frazy'
  if f=='chord':label='Akord';choices='Durowy|Molowy|Kwinta|Sus4|Molowy 7'
  expr='p.'+member+f;value='b->parameters['+str(len(items))+']'
  initial='float('+expr+')'
  if kind=='CHOICE_DEN':initial='1.f';value='den[std::clamp(int('+value+'),0,3)]'
  if f in ('bass','pad') and not prefix:initial='0.f'
  items.append(dict(id=prefix+f,expr=expr,kind=kind,lo=lo,hi=hi,label=prefix+label,choices=choices,integer=integer,initial=initial,value=value))
def orders(prefix='',member=''):
 for k in range(6):
  n=len(items);items.append(dict(id=prefix+'order'+str(k),expr=f'p.{member}order[{k}]',kind='INT',lo='0',hi='5',label=f'{prefix}Kolejność FX {k+1}',choices='Drive / Comp|Chorus|Delay|Granular|Reverb|Szerokość',integer=1,initial=str(k)+'.f',value=f'b->parameters[{n}]'))
parse(text);orders()
for prefix,member in [('pad_','padRack.'),('master_','masterRack.')]:parse(fx,prefix,member);orders(prefix,member)
n=len(items);items.append(dict(id='masterFX',expr='p.masterFX',kind='FLOAT',lo='0',hi='1',label='Ilość FX master',choices='',integer=0,initial='0.f',value=f'b->parameters[{n}]'))
for id,label,lo,hi,initial in [('root','Nuta podstawowa MIDI',24,84,40),('free_bpm','Tempo własne BPM',20,400,120),('sync','Synchronizacja z hostem',0,1,1)]:
 n=len(items);items.append(dict(id=id,expr='',kind='FLOAT' if id=='free_bpm' else 'INT',lo=str(lo),hi=str(hi),label=label,choices='',integer=int(id!='free_bpm'),initial=str(initial)+'.f',value=f'b->parameters[{n}]'))
meta=[];assign=[];smooth=[]
for i,x in enumerate(items):
 meta.append('{'+','.join([json.dumps(x['id']),json.dumps(x['label'],ensure_ascii=False),'""',json.dumps(x['choices'],ensure_ascii=False),str(x['lo']),str(x['hi']),x['initial'],str(x['integer'])])+'}')
 if x['expr']:
  cast='bool' if x['kind']=='BOOL' else 'int' if x['integer'] else 'double'
  assign.append(x['expr']+'='+cast+'('+x['value']+');')
  if x['kind']=='FLOAT':smooth.append(x['expr'].replace('p.','s.current.')+'+=('+x['expr']+'-'+x['expr'].replace('p.','s.current.')+')*smoothing;')
(root/'modules/bass-ambient/metadata.inc').write_text(',\n'.join(meta))
(root/'modules/bass-ambient/assign.inc').write_text('\n'.join(assign))
(root/'modules/bass-ambient/smooth.inc').write_text('\n'.join(smooth))
(root/'modules/bass-ambient/continuous.inc').write_text('\n'.join(x['expr'].replace('p.','s.current.')+'='+x['expr'].replace('p.','previous.')+';' for x in items if x['expr'] and x['kind']=='FLOAT'))
(root/'modules/bass-ambient/ids.json').write_text(json.dumps({x['id']:i for i,x in enumerate(items)},indent=2))
