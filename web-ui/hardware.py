"""Hardware jobs, explicit instrument transport and four MIDI controller bindings."""
import copy,json,os,re,subprocess,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'deploy/connectivity'))
from client import call as hardware_call,status as hardware_status
from manager import atomic_json

class Hardware:
 def init_hardware(self):self.operation={'pending':False};self.last_core=None;self.midi_learning=None
 def core_state(self):
  try:
   if self.operation.get('pending'):raise RuntimeError('Trwa operacja sprzętowa')
   value=self.core('STATUS');value['nodes']=self.core('LIST')['nodes'];value['engine_available']=True;self.last_core=copy.deepcopy(value);return value
  except (OSError,ValueError,RuntimeError) as error:
   fallback=self.last_core
   if fallback is None:
    file=self.data/'last-session.json'
    if file.exists():
     try:fallback=json.loads(file.read_text())
     except (OSError,ValueError):pass
   value=copy.deepcopy(fallback) if fallback else {'ok':False,'client':'JerzyAudioPlatform','sample_rate':44100,'buffer':512,'buffer_ms':512/44.1,'cpu':0,'xruns':0,'clips':0,'invalid_samples':0,'blocks':0,'peak':0,'rms':0,'master':.7,'bpm':120,'limiter':True,'ceiling':.98,'nodes':[],'buses':[{'gain':.7,'pan':0,'mute':False,'solo':False,'peak':0,'rms':0} for _ in range(2)]}
   value['engine_available']=False;value['engine_error']=str(error);return value
 def hardware_state(self):
  value=hardware_status();value['operation']=dict(self.operation)
  file=self.data/'bluetooth-midi.json';bridge=self.data/'bluetooth-midi-bridge.json'
  for key,path in [('relay',file),('jack_midi',bridge)]:
   try:value[key]=json.loads(path.read_text()) if path.exists() else {}
   except (OSError,ValueError):value[key]={}
  if self.midi_learning:
   event=value.get('relay',{}).get('last_event') or {}
   if event.get('monotonic',0)>self.midi_learning['armed'] and event.get('bytes'):
    data=event['bytes'];kind=data[0]&240
    if kind in (176,192):
     bindings=self.bindings();slot=self.midi_learning['slot'];entry=next(b for b in bindings if b['slot']==slot);entry.update(type='cc' if kind==176 else 'pc',channel=(data[0]&15)+1,number=data[1],bound=True);atomic_json(self.data/'midi-bindings.json',bindings);self.midi_learning=None;self.sync_midi_bindings()
   elif time.monotonic()>self.midi_learning['armed']+30:self.midi_learning=None
  value['midi_learning']=self.midi_learning;value['midi_bindings']=self.bindings();return value
 def start_job(self,name,command):
  if self.operation.get('pending'):raise ValueError('Poprzednia operacja audio jeszcze trwa')
  record={'pending':True,'name':name,'error':None,'started':time.time()};self.operation=record
  def worker():
   try:subprocess.run(command,check=True,capture_output=True,text=True,timeout=120)
   except subprocess.CalledProcessError as error:record['error']=(error.stderr or error.stdout or str(error))[-3000:]
   except Exception as error:record['error']=str(error)
   finally:
    with self.lock:record['pending']=False;record['finished']=time.time()
  threading.Thread(target=worker,name='audio-control',daemon=True).start();return {'ok':True,'pending':True,'message':'Trwa '+name+'. Panel pozostaje dostępny.'}
 def bindings(self):
  file=self.data/'midi-bindings.json'
  try:values=json.loads(file.read_text()) if file.exists() else []
  
  except (OSError,ValueError):values=[]
  values=[b for b in values if isinstance(b,dict)] if isinstance(values,list) else []
  return [next((b for b in values if b.get('slot')==i),{'slot':i,'bound':False,'type':'cc','channel':1,'number':i-1,'action':'none','mode':'toggle'}) for i in range(1,5)]
 def save_binding(self,p):
  b={k:p[k] for k in ['slot','bound','type','channel','number','action','mode']};b['slot']=int(b['slot']);b['channel']=int(b['channel']);b['number']=int(b['number'])
  if b['slot'] not in range(1,5) or b['channel'] not in range(1,17) or b['number'] not in range(128) or b['type'] not in ('cc','pc') or b['action'] not in ('none','bypass','preset') or b['mode'] not in ('toggle','value') or type(b['bound']) is not bool:raise ValueError('Niepoprawne mapowanie kontrolera')
  if b['action']=='bypass':
   target=p['target'];module=str(target['module']);route=int(target['route']);ordinal=int(target['ordinal'])
   if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',module) or route not in (0,1) or ordinal not in range(32):raise ValueError('Niepoprawny cel MIDI')
   b['target']={'module':module,'route':route,'ordinal':ordinal}
  if b['action']=='preset':
   name=str(p['preset'])
   if not re.fullmatch(r'[\w -]{1,64}',name) or not (self.data/'presets'/(name+'.json')).is_file():raise ValueError('Nie ma takiego presetu')
   b['preset']=name
  values=self.bindings();values[b['slot']-1]=b
  targets=[(v.get('target',{}).get('module'),v.get('target',{}).get('route'),v.get('target',{}).get('ordinal')) for v in values if v.get('bound') and v.get('action')=='bypass']
  if len(targets)!=len(set(targets)):raise ValueError('Jeden bypass może mieć jedno mapowanie kontrolera')
  atomic_json(self.data/'midi-bindings.json',values);self.sync_midi_bindings();return {'ok':True}
 def sync_midi_bindings(self):
  if not (self.data/'midi-bindings.json').exists():return
  try:nodes=self.core('LIST')['nodes']
  except (OSError,ValueError):return
  for node in nodes:self.core(f'MAPBYPASS {node["id"]} -1 0')
  assigned=set()
  for b in self.bindings():
   if not b.get('bound') or b.get('action')!='bypass':continue
   target=b['target'];matches=[n for n in nodes if n['module']==target['module'] and n['route']==target['route']]
   if len(matches)<=target['ordinal']:continue
   node=matches[target['ordinal']]
   if node['id'] in assigned:continue
   assigned.add(node['id']);key=(int(b['channel'])-1)*128+int(b['number'])+(2048 if b['type']=='pc' else 0)
   self.core(f'MAPBYPASS {node["id"]} {key} {int(b["mode"]=="value")}')
 def instrument(self,p):
  node=next(n for n in self.core('LIST')['nodes'] if n['id']==int(p['id']))
  if node['module']!='bass-ambient-pro-original':raise ValueError('Transport jest przeznaczony dla Bass Ambient PRO')
  def set_parameter(key,value):
   index=next(i for i,v in enumerate(node['parameters']) if v['id']==key);self.core(f'PARAM {node["id"]} {index} {value}')
  if p.get('command')=='stop':set_parameter('autoPlay',0)
  elif p.get('command')=='start':
   set_parameter('performanceSource',2)
   if p.get('part'):
    if p['part'] not in ('bass','pad','arp','drums','krell'):raise ValueError('Niepoprawny instrument')
    set_parameter(p['part'],1)
   elif not any(v['value'] for v in node['parameters'] if v['id'] in ('bass','pad','arp','drums','krell')):set_parameter('bass',1)
   set_parameter('autoPlay',1);self.core(f'BYPASS {node["id"]} 0')
  else:raise ValueError('Niepoprawny transport')
  return {'ok':True}
 def hardware_action(self,p):
  action=p['action']
  if action=='instrument-transport':return self.instrument(p)
  if action=='midi-binding':return self.save_binding(p)
  if action=='midi-learn':
   slot=int(p['slot'])
   if slot not in range(1,5):raise ValueError('Niepoprawny przycisk')
   self.midi_learning={'slot':slot,'armed':time.monotonic()};return {'ok':True,'message':'Naciśnij przycisk kontrolera w ciągu 30 sekund.'}
  if action=='bluetooth':
   allowed={'scan','pair','confirm','midi-connect','midi-disconnect','pan-connect','pan-disconnect'};operation=p['operation']
   if operation not in allowed:raise ValueError('Niepoprawna operacja Bluetooth')
   args={k:p[k] for k in ('address','id','value') if k in p};return hardware_call(operation,**args)
  if action=='audio-config':
   status=self.state()
   if not status.get('hardware',{}).get('available'):raise ValueError('Usługa sprzętowa nie odpowiada. Zaktualizuj i aktywuj kompletną paczkę tej wersji.')
   rate=int(p['rate']);buffer=int(p['buffer']);periods=int(p['periods'])
   if rate not in (44100,48000) or buffer not in (64,128,256,512,1024) or periods not in (2,3):raise ValueError('Nieobsługiwany profil audio')
   if status.get('engine_available'):status['schema']=1;atomic_json(self.data/'last-session.json',status)
   helper=getattr(self.args,'audio_helper',None)
   if not helper:raise ValueError('Nie zainstalowano kontrolera audio')
   return self.start_job('zmiana profilu audio',[sys.executable,helper,'audio','--rate',str(rate),'--buffer',str(buffer),'--periods',str(periods)])
  if action in ('restart-audio','recover-audio','repair-jack'):
   helper=getattr(self.args,'audio_helper',None)
   if not helper:raise ValueError('Nie zainstalowano kontrolera audio')
   return self.start_job('odzyskiwanie audio',[sys.executable,helper,'repair' if action=='repair-jack' else 'recover' if action=='recover-audio' else 'restart'])
  return None
