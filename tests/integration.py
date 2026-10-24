#!/usr/bin/env python3
import argparse,json,os,platform,signal,socket,subprocess,sys,tempfile,time,urllib.request,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def wait(fn,timeout=15):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  try:return fn()
  except (OSError,ValueError,KeyError):time.sleep(.1)
 raise RuntimeError('Przekroczony czas gotowości')
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',required=True);p.add_argument('--browser',action='store_true');p.add_argument('--stress-seconds',type=float,default=0);a=p.parse_args();build=Path(a.build).resolve();processes=[]
 with tempfile.TemporaryDirectory(prefix='jerzy-test-') as temp:
  tmp=Path(temp);env=os.environ.copy();env['JACK_DEFAULT_SERVER']='jerzy-test-'+str(os.getpid())
  env.setdefault('JACK_DRIVER_DIR',f'/usr/lib/{platform.machine()}-linux-gnu/jack')
  def start(args,name):
   f=(tmp/(name+'.log')).open('w');proc=subprocess.Popen(args,env=env,stdout=f,stderr=subprocess.STDOUT);f.close();processes.append(proc);return proc
  def core(cmd):
   with socket.socket(socket.AF_UNIX) as s:
    s.settimeout(5);s.connect(str(tmp/'core.sock'));s.sendall((cmd+'\n').encode());data=b''
    while not data.endswith(b'\n'):data+=s.recv(65536)
   value=json.loads(data)
   if not value['ok']:raise ValueError(value['error'])
   return value
  try:
   jack=start(['jackd','--name',env['JACK_DEFAULT_SERVER'],'--no-realtime','-d','dummy','-r','44100','-p','256'],'jack')
   time.sleep(.7)
   host=start([str(build/'jerzy-audio-core'),str(tmp/'core.sock')],'core');status=wait(lambda:core('STATUS'));assert status['sample_rate']==44100
   # A second client receives a unique JACK name and cannot overwrite the first socket.
   other=start([str(build/'jerzy-audio-core'),str(tmp/'second.sock')],'second');second=wait(lambda:other.poll() is None and command_socket(tmp/'second.sock','STATUS'));assert second['client']!=status['client'];other.terminate();other.wait(timeout=10)
   node=core('ADD 0 '+json.dumps(str(build/'modules/utility-gain-meter/utility-gain-meter.so'))+' ""')['id']
   def probe():return json.loads(subprocess.check_output([str(build/'jack-probe'),status['client'],'500'],env=env,stderr=subprocess.DEVNULL))
   baseline=probe();assert baseline['samples']>0 and .015<baseline['rms']<.1,baseline
   core(f'LEARN {node} 0')
   subprocess.run([str(build/'jack-probe'),status['client'],'200','cc'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
   learned=core('LIST')['nodes'][0]['parameters'][0];assert learned['mapping']==74 and learned['value']==12,learned
   core(f'MAP {node} 0 -1')
   core(f'PARAM {node} 0 -12');quiet=probe();assert quiet['rms']<baseline['rms']*.4,(baseline,quiet)
   core(f'BYPASS {node} 1');bypass=probe();assert bypass['rms']>quiet['rms']*2
   # Live graph swapping while JACK callback continues.
   before=core('STATUS')['blocks']
   for i in range(12):
    n=core('ADD 0 '+json.dumps(str(build/'modules/big-muff/big-muff.so'))+' ""')['id'];core(f'MOVE {n} 0');core(f'REMOVE {n}')
   assert core('STATUS')['blocks']>before
   # Panel starts on a free local port; make real HTTP requests.
   with socket.socket() as portSocket:portSocket.bind(('127.0.0.1',0));port=portSocket.getsockname()[1]
   web=start([sys.executable,str(ROOT/'web-ui/server.py'),'--socket',str(tmp/'core.sock'),'--modules',str(build/'modules'),'--data',str(tmp/'data'),'--port',str(port)],'web')
   url=f'http://127.0.0.1:{port}'
   def get(path):return json.load(urllib.request.urlopen(url+path,timeout=5))
   token=wait(lambda:get('/api/session'))['token']
   def action(value):return json.load(urllib.request.urlopen(urllib.request.Request(url+'/api/action',json.dumps(value).encode(),{'Content-Type':'application/json','X-Jerzy-Token':token}),timeout=10))
   s=get('/api/state');assert len(s['library'])>=5 and len(s['nodes'])==1
   action({'action':'module-preset-save','name':'Gain test','id':node})
   action({'action':'param','id':node,'index':0,'value':-20})
   action({'action':'module-preset-load','name':'Gain test','id':node})
   assert get('/api/state')['nodes'][0]['parameters'][0]['value']==-12
   action({'action':'preset-save','name':'Próba żółć'});action({'action':'remove','id':node});assert get('/api/state')['nodes']==[]
   action({'action':'preset-load','name':'Próba żółć'});restored=get('/api/state')['nodes'];assert len(restored)==1 and restored[0]['parameters'][0]['value']==-12 and restored[0]['bypass']
   # Failed transactional replacement leaves the previous graph intact.
   core('BEGIN')
   try:core('ADD 1 "/does/not/exist.so" ""')
   except ValueError:pass
   else:raise AssertionError('invalid module accepted')
   core('ABORT');assert len(core('LIST')['nodes'])==1
   try:action({'action':'param','id':restored[0]['id'],'index':0,'value':999})
   except urllib.error.HTTPError as error:assert error.code==400
   else:raise AssertionError('invalid parameter accepted')
   synth=action({'action':'add','module':'bass-ambient-original','route':1})['id'];nodes=get('/api/state')['nodes'];bass=next(n for n in nodes if n['id']==synth);idx=next(i for i,p in enumerate(bass['parameters']) if p['id']=='bass');action({'action':'param','id':synth,'index':idx,'value':1});time.sleep(.2);assert get('/api/state')['buses'][1]['peak']>0
   # Exercise the installed service entry without changing HOME or systemd.
   payload=tmp/'payload';(payload/'bin').mkdir(parents=True);(payload/'bin/jerzy-audio-core').symlink_to(build/'jerzy-audio-core')
   (payload/'web-ui').symlink_to(ROOT/'web-ui',target_is_directory=True)
   base=tmp/'restart-data';base.mkdir();shutil.copytree(build/'modules',base/'modules')
   (base/'audio-routing.json').write_text(json.dumps({'inputs':['system:capture_1','system:capture_2'],'outputs':['system:playback_1','system:playback_2']}))
   saved=get('/api/state');saved['schema']=1;(base/'last-session.json').write_text(json.dumps(saved))
   bootCode="import importlib.util,pathlib,sys; p="+repr(str(ROOT/'deploy/raspberry-pi/start_engine.py'))+"; s=importlib.util.spec_from_file_location('entry',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.ROOT=pathlib.Path("+repr(str(payload))+"); m.BASE=pathlib.Path("+repr(str(base))+"); sys.exit(m.main())"
   boot=start([sys.executable,'-c',bootCode],'bootstrap')
   def restored():
    report=base/'session-recovery.json'
    if not report.exists():raise ValueError('pending')
    recovery=json.loads(report.read_text())
    if recovery.get('pending'):raise ValueError('pending')
    assert not recovery.get('error'),recovery
    value=command_socket(base/'core.sock','LIST')
    if len(value['nodes'])!=len(saved['nodes']):raise ValueError('pending nodes')
    return value
   wait(restored);boot.terminate();boot.wait(timeout=10)
   boot=start([sys.executable,'-c',bootCode],'bootstrap-restart');wait(restored);boot.terminate();boot.wait(timeout=10)
   if a.stress_seconds:
    # Capture real output throughout the run; pauses allow each fade to reopen.
    capture=subprocess.Popen([str(build/'jack-probe'),status['client'],str(int(a.stress_seconds*1000))],env=env,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
    end=time.monotonic()+a.stress_seconds;cycles=0;previousBlocks=core('STATUS')['blocks']
    while time.monotonic()<end:
     n=core('ADD 1 '+json.dumps(str(build/'modules/tape-drive/tape-drive.so'))+' ""')['id'];time.sleep(.03)
     core(f'PARAM {n} 0 0.9');core(f'BYPASS {n} 1');time.sleep(.03)
     core(f'MOVE {n} 0');time.sleep(.03);core(f'REMOVE {n}');time.sleep(.03);cycles+=1
     current=core('STATUS');assert current['invalid_samples']==0 and current['blocks']>previousBlocks;previousBlocks=current['blocks']
    captured=json.loads(capture.communicate(timeout=10)[0]);assert capture.returncode==0 and captured['rms']>.001,captured
    print(json.dumps({'stress_seconds':a.stress_seconds,'graph_cycles':cycles,'captured_audio':captured,'status':core('STATUS')},indent=2))
   if a.browser:subprocess.run(['node',str(ROOT/'tests/ui.cjs'),url,str(ROOT/'docs/panel-mobile.png')],env=env,check=True)
   print(json.dumps({'result':'PASS','checks':['JACK ports and unique names','real audio gain and bypass','native MIDI CC learn','module preset restore','live graph add/move/remove','HTTP panel','session save/load with Unicode','failed graph transaction','invalid parameter rejection','BassAmbient in independent instrument bus','service entry restores graph after engine restart'],'audio':{'baseline':baseline,'gain_minus_12dB':quiet,'bypass':bypass},'status':core('STATUS')},ensure_ascii=False,indent=2))
  except BaseException:
   for log in tmp.glob('*.log'):print(log.name,log.read_text()[-3000:],file=sys.stderr)
   raise
  finally:
   for proc in reversed(processes):
    if proc.poll() is None:
     proc.terminate()
     try:proc.wait(timeout=10)
     except subprocess.TimeoutExpired:proc.kill();proc.wait()
def command_socket(path,command):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(3);s.connect(str(path));s.sendall((command+'\n').encode());raw=b''
  while not raw.endswith(b'\n'):
   chunk=s.recv(65536)
   if not chunk:raise ValueError('socket closed')
   raw+=chunk
  return json.loads(raw)
if __name__=='__main__':main()
