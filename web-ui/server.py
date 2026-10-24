#!/usr/bin/env python3
"""Small standard-library HTTP control service. DSP remains in the C++ JACK client."""
import zipfile
import argparse,base64,hashlib,http.server,json,os,re,secrets,socket,subprocess,sys,tempfile,threading,time,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'module-manager'))
from manager import Library,atomic_json,ID
class Application:
 def __init__(self,args):
  self.args=args;self.data=Path(args.data).resolve();self.data.mkdir(parents=True,exist_ok=True)
  self.library=Library(args.modules);self.lock=threading.RLock();self.token=secrets.token_urlsafe(32)
 def core(self,command):
  with socket.socket(socket.AF_UNIX) as s:
   s.settimeout(10);s.connect(self.args.socket);s.sendall((command+'\n').encode());data=bytearray()
   while not data.endswith(b'\n'):
    part=s.recv(65536)
    if not part or len(data)>4*1024*1024:raise ValueError('Brak poprawnej odpowiedzi silnika')
    data.extend(part)
  result=json.loads(data)
  if not result.get('ok'):raise ValueError(result.get('error','Błąd silnika'))
  return result
 def state(self):
  status=self.core('STATUS');status['nodes']=self.core('LIST')['nodes'];status['library']=self.library.list()
  status['presets']=[p.stem for p in sorted((self.data/'presets').glob('*.json'))]
  status['irs']=[p.name for p in sorted((self.data/'irs').glob('*.wav'))]
  status['module_presets']=[{'name':p.stem,'module':json.loads(p.read_text())['module']} for p in sorted((self.data/'module-presets').glob('*.json'))]
  status['version']='0.1.0-dev';status['platform']=os.uname().machine
  try:
   pages=int(Path('/proc/self/statm').read_text().split()[1]);status['web_ram_mb']=pages*os.sysconf('SC_PAGE_SIZE')/1048576
  except (OSError,ValueError):pass
  return status
 def add(self,module,route,asset=''):
  entry=next((x for x in self.library.list() if x['id']==module),None)
  if not entry:raise ValueError('Moduł nie jest zainstalowany')
  if route not in (0,1):raise ValueError('Nieprawidłowy tor')
  assetPath=''
  if asset:
   if Path(asset).name!=asset or not asset.endswith('.wav'):raise ValueError('Niepoprawna nazwa IR')
   assetPath=str(self.data/'irs'/asset)
   if not Path(assetPath).is_file():raise ValueError('Brak IR')
  return self.core(f'ADD {route} {json.dumps(entry["path"],ensure_ascii=False)} {json.dumps(assetPath,ensure_ascii=False)}')
 def apply_preset(self,value):
  if value.get('schema')!=1 or not isinstance(value.get('nodes'),list):raise ValueError('Nieprawidłowy preset')
  self.core('BEGIN')
  try:
   for node in value['nodes']:
    id=self.add(node['module'],int(node['route']),Path(node.get('asset','')).name)['id']
    # Parameter IDs must match the loaded version; unknown IDs are not silently ignored.
    actual=next(x for x in self.core('PENDING')['nodes'] if x['id']==id)
    if [x['id'] for x in actual['parameters']]!=[x['id'] for x in node['parameters']]:raise ValueError('Preset wymaga innej wersji parametrów modułu')
    # Presets store both ABI parameter positions and stable IDs. Metadata was captured at save time.
    for i,p in enumerate(node['parameters']):
     self.core(f'PARAM {id} {i} {float(p["value"])}')
     self.core(f'MAP {id} {i} {int(p.get("mapping",-1))}')
    self.core(f'BYPASS {id} {int(node.get("bypass",False))}')
   self.core('COMMIT')
  except BaseException:
   self.core('ABORT');raise
  for i,b in enumerate(value['buses']):self.core(f'MIX {i} {float(b["gain"])} {float(b["pan"])} {int(b["mute"])} {int(b["solo"])}')
  for key,cmd in [('master','MASTER'),('bpm','BPM'),('ceiling','CEILING')]:self.core(f'{cmd} {float(value[key])}')
  self.core('LIMITER '+str(int(value['limiter'])))
 def action(self,p):
  with self.lock:
   action=p['action']
   if action=='add':return self.add(p['module'],int(p['route']),p.get('asset',''))
   if action in ('remove','bypass','move'):
    id=int(p['id']);cmd={'remove':'REMOVE','bypass':'BYPASS','move':'MOVE'}[action];tail='' if action=='remove' else ' '+str(int(p['value']));return self.core(f'{cmd} {id}{tail}')
   if action=='learn':return self.core(f'LEARN {int(p["id"])} {int(p["index"])}')
   if action=='param':return self.core(f'PARAM {int(p["id"])} {int(p["index"])} {float(p["value"])}')
   if action=='mix':return self.core(f'MIX {int(p["route"])} {float(p["gain"])} {float(p["pan"])} {int(p["mute"])} {int(p["solo"])}')
   if action in ('master','bpm','ceiling','limiter'):return self.core(action.upper()+' '+str(float(p['value']) if action!='limiter' else int(p['value'])))
   if action in ('module-preset-save','module-preset-load'):
    name=p['name']
    if not re.fullmatch(r'[\w -]{1,64}',name):raise ValueError('Niepoprawna nazwa presetu modułu')
    node=next(x for x in self.core('LIST')['nodes'] if x['id']==int(p['id']))
    file=self.data/'module-presets'/(name+'.json')
    if action=='module-preset-save':atomic_json(file,node)
    else:
     saved=json.loads(file.read_text())
     if saved['module']!=node['module'] or [x['id'] for x in saved['parameters']]!=[x['id'] for x in node['parameters']]:raise ValueError('Preset wymaga innego modułu lub wersji parametrów')
     import math
     for actual,stored in zip(node['parameters'],saved['parameters']):
      value=float(stored['value'])
      if not math.isfinite(value) or not actual['min']<=value<=actual['max'] or (actual['integer'] and value!=round(value)):raise ValueError('Niepoprawny parametr presetu')
     for index,item in enumerate(saved['parameters']):
      self.core(f'PARAM {node["id"]} {index} {float(item["value"])}')
      self.core(f'MAP {node["id"]} {index} {int(item.get("mapping",-1))}')
    return {'ok':True}
   if action=='preset-save':
    name=p['name']
    if not re.fullmatch(r'[\w -]{1,64}',name):raise ValueError('Nazwa presetu: maksymalnie 64 znaki, litery i cyfry')
    state=self.state();state['schema']=1;atomic_json(self.data/'presets'/(name+'.json'),state);return {'ok':True}
   if action=='preset-load':
    name=p['name']
    if not re.fullmatch(r'[\w -]{1,64}',name):raise ValueError('Niepoprawna nazwa')
    self.apply_preset(json.loads((self.data/'presets'/(name+'.json')).read_text()));return {'ok':True}
   if action=='ir-import':
    name=p['name']
    if Path(name).name!=name or not re.fullmatch(r'[\w .-]+\.wav',name):raise ValueError('Niepoprawna nazwa IR')
    raw=base64.b64decode(p['data'],validate=True)
    if len(raw)>8*1024*1024 or raw[:4]!=b'RIFF' or raw[8:12]!=b'WAVE':raise ValueError('Wymagany WAV, maksymalnie 8 MB')
    path=self.data/'irs'/name;path.parent.mkdir(exist_ok=True);tmp=path.with_suffix('.upload');tmp.write_bytes(raw);os.replace(tmp,path);return {'ok':True}
   if action=='module-import':
    if p.get('trust') is not True:raise ValueError('Potwierdź zaufanie do autora wykonywalnego kodu')
    raw=base64.b64decode(p['data'],validate=True)
    if len(raw)>64*1024*1024:raise ValueError('Za duża paczka')
    with tempfile.NamedTemporaryFile(suffix='.jamod') as f:
     f.write(raw);f.flush()
     import zipfile
     with zipfile.ZipFile(f.name) as archive:module=json.loads(archive.read('manifest.json'))['id']
     if any(n['module']==module for n in self.core('LIST')['nodes']):raise ValueError('Przed aktualizacją usuń instancje modułu z grafu')
     m=self.library.install(f.name,p['sha256']);return {'ok':True,'module':m['id']}
   if action in ('module-remove','module-rollback'):
    if any(n['module']==p['module'] for n in self.core('LIST')['nodes']):raise ValueError('Najpierw usuń instancje tego modułu z grafu')
    (self.library.remove if action=='module-remove' else self.library.rollback)(p['module']);return {'ok':True}
   if action=='buffer':
    size=int(p['value'])
    if size not in (64,128,256,512,1024):raise ValueError('Nieobsługiwany bufor')
    if not self.args.audio_helper:raise ValueError('Zmiana bufora wymaga instalacji usługi na Raspberry Pi')
    snapshot=self.state();snapshot['schema']=1
    try:
     subprocess.run([sys.executable,self.args.audio_helper,'buffer',str(size)],check=True,timeout=60)
     self.apply_preset(snapshot)
    except BaseException:
     subprocess.run([sys.executable,self.args.audio_helper,'buffer',str(snapshot['buffer'])],check=False,timeout=60)
     self.apply_preset(snapshot)
     raise
    return {'ok':True}
   raise ValueError('Nieznana operacja')
class Handler(http.server.BaseHTTPRequestHandler):
 server_version='JerzyAudioPlatform/0.1.0'
 def log_message(self,*args):pass
 def send(self,code,data,kind='application/json; charset=utf-8'):
  raw=json.dumps(data,ensure_ascii=False).encode() if isinstance(data,dict) else data
  self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'");self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  try:
   if self.path=='/api/state':
    with self.server.app.lock:self.send(200,self.server.app.state())
   elif self.path=='/api/session':self.send(200,{'token':self.server.app.token})
   elif self.path in ('/','/app.js','/style.css'):
    file={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[self.path];kind={'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}[self.path];self.send(200,(ROOT/'web-ui'/file).read_bytes(),kind)
   else:self.send(404,{'error':'Nie znaleziono'})
  except (OSError,ValueError,KeyError) as e:self.send(503,{'error':str(e)})
 def do_POST(self):
  try:
   origin=self.headers.get('Origin');host=self.headers.get('Host','')
   if origin and urllib.parse.urlsplit(origin).netloc!=host:raise ValueError('Odrzucono żądanie z innej strony')
   if not secrets.compare_digest(self.headers.get('X-Jerzy-Token',''),self.server.app.token):self.send(403,{'error':'Odśwież sesję panelu'});return
   if self.path!='/api/action':self.send(404,{'error':'Nie znaleziono'});return
   size=int(self.headers.get('Content-Length','0'))
   if size<1 or size>90*1024*1024:raise ValueError('Nieprawidłowy rozmiar żądania')
   p=json.loads(self.rfile.read(size));app=self.server.app
   with app.lock:
    result=app.action(p)
    state=app.state();state['schema']=1;atomic_json(app.data/'last-session.json',state)
   self.send(200,result)
  except (OSError,ValueError,KeyError,subprocess.SubprocessError,StopIteration,zipfile.BadZipFile) as e:self.send(400,{'error':str(e)})
def main():
 p=argparse.ArgumentParser();p.add_argument('--socket',default='/tmp/jerzy-audio-platform.sock');p.add_argument('--modules',default=str(ROOT/'modules'));p.add_argument('--data',default=str(Path.home()/'.local/share/jerzy-audio-platform'));p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8093);p.add_argument('--audio-helper');p.add_argument('--restore',action='store_true');args=p.parse_args()
 app=Application(args)
 if args.restore and (app.data/'last-session.json').exists():
  end=time.monotonic()+15
  while True:
   try:app.core('STATUS');break
   except OSError:
    if time.monotonic()>=end:raise
    time.sleep(.1)
  app.apply_preset(json.loads((app.data/'last-session.json').read_text()))
 server=http.server.ThreadingHTTPServer((args.host,args.port),Handler);server.app=app
 print(f'Panel gotowy, port {args.port}',flush=True);server.serve_forever()
if __name__=='__main__':main()
