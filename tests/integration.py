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
   # The native Bluetooth bridge delivers real CC/PC into the JACK callback.
   bridge=start([str(build/'jerzy-midi-bridge'),str(tmp/'midi.sock'),str(tmp/'midi-status.json')],'midi')
   def bridge_ready():
    if not (tmp/'midi.sock').exists():raise ValueError('bridge starting')
    return True
   wait(bridge_ready)
   def midi(data):
    with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as channel:channel.sendto(data,str(tmp/'midi.sock'))
   midi(('@'+status['client']+':midi').encode())
   def connected_bridge():
    value=json.loads((tmp/'midi-status.json').read_text())
    if not value.get('connected'):raise ValueError('connecting MIDI')
    return value
   wait(connected_bridge)
   core(f'MAPBYPASS {node} 21 0')
   def bypass_is(expected):
    value=core('LIST')['nodes'][0]['user_bypass']
    if value!=expected:raise ValueError('MIDI not delivered yet')
    return True
   midi(bytes([176,21,127]));wait(lambda:bypass_is(False))
   midi(bytes([176,21,127]));time.sleep(.04);bypass_is(False)
   midi(bytes([176,21,0]));midi(bytes([176,21,127]));wait(lambda:bypass_is(True))
   core(f'MAPBYPASS {node} 2055 0');time.sleep(.03)
   midi(bytes([192,7]));wait(lambda:bypass_is(False))
   midi(bytes([192,7]));wait(lambda:bypass_is(True))
   core(f'MAPBYPASS {node} -1 0')
   # Live graph swapping while JACK callback continues.
   before=core('STATUS')['blocks']
   for i in range(12):
    n=core('ADD 0 '+json.dumps(str(build/'modules/big-muff/big-muff.so'))+' ""')['id'];core(f'MOVE {n} 0');core(f'REMOVE {n}')
   assert core('STATUS')['blocks']>before
   # A scheduler delay is not evidence that a module consumed the CPU budget.
   delayed=core('ADD 0 '+json.dumps(str(build/'overload-fixture.so'))+' "-6"')['id']
   time.sleep(.3)
   delayed_state=next(n for n in core('LIST')['nodes'] if n['id']==delayed)
   assert delayed_state['fault']==0 and not delayed_state['bypass'],delayed_state
   core(f'REMOVE {delayed}')
   # A costly module must not take away bypass/control of the rest of the graph.
   overload=core('ADD 0 '+json.dumps(str(build/'overload-fixture.so'))+' ""')['id']
   def protected():
    value=next(n for n in core('LIST')['nodes'] if n['id']==overload)
    if value['fault']!=1 or not value['bypass']:raise ValueError('guard pending')
    return value
   guard=wait(protected);assert guard['fault_cause'] in (1,3) and guard['cpu_percent']>95 and guard['fault_budget_ms']>0,guard;core(f'REMOVE {overload}');assert core('STATUS')['blocks']>before
   # Exercise the real buffer helper against this JACK server. Any service
   # restart is an error; node IDs, parameters and actual connections survive.
   bufferCode="import importlib.util,pathlib,sys; sys.path.insert(0,"+repr(str(ROOT/'deploy/raspberry-pi'))+"); p="+repr(str(ROOT/'deploy/raspberry-pi/control.py'))+"; s=importlib.util.spec_from_file_location('control',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.BASE=pathlib.Path("+repr(str(tmp))+ "); m.systemctl=lambda *a,**k: (_ for _ in ()).throw(AssertionError('unexpected service restart')); m.buffer_change(512); m.buffer_change(128); m.buffer_change(256)"
   ids=[n['id'] for n in core('LIST')['nodes']]
   subprocess.run([sys.executable,'-c',bufferCode],env=env,check=True,timeout=30)
   assert core('STATUS')['buffer']==256 and [n['id'] for n in core('LIST')['nodes']]==ids
   assert probe()['rms']>.01
   # Combined load is protected even if each individual module fits its budget.
   subprocess.run([sys.executable,'-c',bufferCode.replace('m.buffer_change(512); m.buffer_change(128); m.buffer_change(256)','m.buffer_change(512)')],env=env,check=True,timeout=15)
   medium=[core('ADD 0 '+json.dumps(str(build/'overload-fixture.so'))+' "7"')['id'] for _ in range(2)]
   def aggregate_protected():
    nodes=[n for n in core('LIST')['nodes'] if n['id'] in medium]
    if not any(n['fault']==1 and n['bypass'] for n in nodes):raise ValueError('aggregate guard pending')
    return nodes
   guarded=wait(aggregate_protected);assert any(n.get('fault_cause')==3 and n['fault_graph_cpu_percent']>105 for n in guarded),guarded
   for n in medium:core(f'REMOVE {n}')
   subprocess.run([sys.executable,'-c',bufferCode],env=env,check=True,timeout=30)
   # Distinguish a single expensive callback from sustained or graph overload.
   subprocess.run([sys.executable,'-c',bufferCode.replace('m.buffer_change(512); m.buffer_change(128); m.buffer_change(256)','m.buffer_change(128)')],env=env,check=True,timeout=15)
   overload=core('ADD 0 '+json.dumps(str(build/'overload-fixture.so'))+' ""')['id']
   spike=wait(protected);assert spike['fault_cause']==2 and spike['cpu_percent']>800 and 2<spike['fault_budget_ms']<4,spike
   core(f'REMOVE {overload}')
   subprocess.run([sys.executable,'-c',bufferCode],env=env,check=True,timeout=30)
   # 23 ms / 1024 frames = 99%: above the 95% node limit, below 105% graph limit.
   subprocess.run([sys.executable,'-c',bufferCode.replace('m.buffer_change(512); m.buffer_change(128); m.buffer_change(256)','m.buffer_change(1024)')],env=env,check=True,timeout=15)
   overload=core('ADD 0 '+json.dumps(str(build/'overload-fixture.so'))+' "23"')['id']
   sustained=wait(protected);assert sustained['fault_cause']==1 and sustained['cpu_average_percent']>95,sustained
   core(f'REMOVE {overload}')
   subprocess.run([sys.executable,'-c',bufferCode],env=env,check=True,timeout=30)
   # THRU affects only direct physical audio edges, preserving host routing.
   thruCode="import importlib.util,pathlib,sys; sys.path.insert(0,"+repr(str(ROOT/'deploy/raspberry-pi'))+"); p="+repr(str(ROOT/'deploy/raspberry-pi/control.py'))+"; s=importlib.util.spec_from_file_location('control',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.BASE=pathlib.Path("+repr(str(tmp))+"); j=m.Jack(); j.connect('system:capture_1','system:playback_2'); assert j.direct_thru(); m.thru(False); assert not j.direct_thru(); m.thru(True); assert ['system:capture_1','system:playback_2'] in j.direct_thru(); j.disconnect('system:capture_1','system:playback_2'); j.close()"
   subprocess.run([sys.executable,'-c',thruCode],env=env,check=True,timeout=15)
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
   # Real IR import, visible controls and migration of a one-control CAB preset.
   import base64,io,wave,struct
   raw=io.BytesIO()
   with wave.open(raw,'wb') as wav:wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(44100);wav.writeframes(struct.pack('<h',16384)+b'\0\0'*255)
   action({'action':'ir-import','name':'Test IR.wav','data':base64.b64encode(raw.getvalue()).decode()})
   cab=action({'action':'add','module':'cab-ir','route':0,'asset':'Test IR.wav'})['id'];nodeState=next(n for n in get('/api/state')['nodes'] if n['id']==cab)
   assert nodeState['asset'].endswith('Test IR.wav') and [p['id'] for p in nodeState['parameters']]==['level','mix','polarity']
   action({'action':'param','id':cab,'index':0,'value':.6});action({'action':'preset-save','name':'CAB migration'})
   old=tmp/'data/presets/CAB migration.json';legacy=json.loads(old.read_text());next(n for n in legacy['nodes'] if n['module']=='cab-ir')['parameters']=nodeState['parameters'][:1];old.write_text(json.dumps(legacy))
   action({'action':'preset-load','name':'CAB migration'});cab=next(n for n in get('/api/state')['nodes'] if n['module']=='cab-ir');assert len(cab['parameters'])==3
   action({'action':'bypass','id':cab['id'],'value':1});action({'action':'remove','id':cab['id']})
   synth=action({'action':'add','module':'bass-ambient-pro-original','route':1})['id'];nodes=get('/api/state')['nodes'];bass=next(n for n in nodes if n['id']==synth);idx=next(i for i,p in enumerate(bass['parameters']) if p['id']=='bass');action({'action':'param','id':synth,'index':idx,'value':1});action({'action':'instrument-transport','id':synth,'command':'start'});time.sleep(.2);assert get('/api/state')['buses'][1]['peak']>0
   # Exercise the installed service entry without changing HOME or systemd.
   payload=tmp/'payload';(payload/'bin').mkdir(parents=True);(payload/'bin/jerzy-audio-core').symlink_to(build/'jerzy-audio-core')
   (payload/'web-ui').symlink_to(ROOT/'web-ui',target_is_directory=True)
   base=tmp/'restart-data';base.mkdir();shutil.copytree(build/'modules',base/'modules')
   (base/'audio-settings.json').write_text(json.dumps({'buffer':512}))
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
    assert command_socket(base/'core.sock','STATUS')['buffer']==512
    return value
   wait(restored);boot.terminate();boot.wait(timeout=10)
   boot=start([sys.executable,'-c',bootCode],'bootstrap-restart');wait(restored)
   # The actual recovery helper can empty the graph without rebooting JACK/Pi.
   import importlib.util
   sys.path.insert(0,str(ROOT/'deploy/raspberry-pi'))
   spec=importlib.util.spec_from_file_location('recovery_control',ROOT/'deploy/raspberry-pi/control.py');recovery_control=importlib.util.module_from_spec(spec);spec.loader.exec_module(recovery_control);recovery_control.BASE=base
   def restart_unit(action,unit):
    nonlocal boot
    assert action=='restart' and unit==recovery_control.UNITS[0]
    boot.terminate();boot.wait(timeout=10);boot=start([sys.executable,'-c',bootCode],'bootstrap-recovery')
   recovery_control.systemctl=restart_unit;recovery_control.restart_audio(True)
   assert not command_socket(base/'core.sock','LIST')['nodes'] and list(base.glob('last-session-before-recovery-*.json'))
   recovery_control.restart_audio(False);wait(restored);boot.terminate();boot.wait(timeout=10)
   subprocess.run([sys.executable,'-c',bufferCode],env=env,check=True,timeout=30)
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
   host.terminate();host.wait(timeout=10)
   offline=get('/api/state');assert offline['engine_available'] is False and 'hardware' in offline
   print(json.dumps({'result':'PASS','checks':['JACK ports and unique names','real audio gain and bypass','native MIDI CC learn','module preset restore','live graph add/move/remove','HTTP panel','session save/load with Unicode','failed graph transaction','invalid parameter rejection','BassAmbient in independent instrument bus','service entry restores graph and saved buffer after engine restart','recover empty graph without Pi restart','live JACK buffer keeps instances','THRU preserves host routing','overload triggers automatic bypass'],'audio':{'baseline':baseline,'gain_minus_12dB':quiet,'bypass':bypass},'status':offline},ensure_ascii=False,indent=2))
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
