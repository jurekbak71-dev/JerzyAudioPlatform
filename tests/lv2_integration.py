#!/usr/bin/env python3
"""Real JACK/HTTP tests using test-only LV2 FX and synth bundles."""
import argparse,base64,hashlib,json,os,shutil,socket,subprocess,sys,tempfile,time,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--build',type=Path,required=True);parser.add_argument('--browser',action='store_true');args=parser.parse_args();build=args.build.resolve();processes=[]
 with tempfile.TemporaryDirectory(prefix='jerzy-lv2-') as name:
  temp=Path(name);env={**os.environ,'JACK_DEFAULT_SERVER':'jerzy-lv2-'+str(os.getpid()),'LV2_PATH':str(build/'lv2'),'JERZY_LV2_PATH':str(temp/'data/lv2')}
  def start(command,label):
   with (temp/(label+'.log')).open('w') as log:p=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT)
   processes.append(p);return p
  def wait(fn,timeout=15):
   end=time.monotonic()+timeout
   while time.monotonic()<end:
    try:return fn()
    except (OSError,ValueError,KeyError,AssertionError):time.sleep(.05)
   raise RuntimeError('Readiness timeout')
  def core(command):
   with socket.socket(socket.AF_UNIX) as s:
    s.settimeout(8);s.connect(str(temp/'core.sock'));s.sendall((command+'\n').encode());raw=b''
    while not raw.endswith(b'\n'):
     chunk=s.recv(65536)
     if not chunk:raise RuntimeError('core disconnected')
     raw+=chunk
   result=json.loads(raw)
   if not result.get('ok'):raise ValueError(result.get('error'))
   return result
  try:
   start(['jackd','--name',env['JACK_DEFAULT_SERVER'],'--no-realtime','-d','dummy','-r','44100','-p','256'],'jack');time.sleep(.6)
   start([str(build/'jerzy-audio-core'),str(temp/'core.sock')],'core');status=wait(lambda:core('STATUS'))
   with socket.socket() as free:free.bind(('127.0.0.1',0));port=free.getsockname()[1]
   start([sys.executable,str(ROOT/'web-ui/server.py'),'--core-binary',str(build/'jerzy-audio-core'),'--lv2-dir',str(temp/'data/lv2'),'--socket',str(temp/'core.sock'),'--data',str(temp/'data'),'--port',str(port)],'web')
   url=f'http://127.0.0.1:{port}'
   def get(path='/api/state'):return json.load(urllib.request.urlopen(url+path,timeout=10))
   token=wait(lambda:get('/api/session'))['token']
   def action(**body):return json.load(urllib.request.urlopen(urllib.request.Request(url+'/api/action',json.dumps(body).encode(),{'Content-Type':'application/json','X-Jerzy-Token':token}),timeout=15))
   catalog=get()['library'];assert len(catalog)==4 and all(p['format']=='lv2' for p in catalog)
   assert next(p for p in catalog if p['id'].endswith('unsupported'))['supported'] is False
   def probe():return json.loads(subprocess.check_output([str(build/'jack-probe'),status['client'],'400'],env=env,stderr=subprocess.DEVNULL))
   baseline=probe();fx=action(action='add',module='lv2:urn:jerzy:test:gain',route=0)['id'];action(action='param',id=fx,index=0,value=.25);quiet=probe();assert quiet['rms']<baseline['rms']*.4,(baseline,quiet)
   action(action='bypass',id=fx,value=1);assert probe()['rms']>quiet['rms']*2
   action(action='bypass',id=fx,value=0)
   synth=action(action='add',module='lv2:urn:jerzy:test:synth',route=1)['id'];action(action='midi-channel',id=synth,channel=2)
   action(action='midi',id=synth,status=145,a=69,b=100)
   def audible():s=get();assert s['buses'][1]['peak']>.001;return s
   wait(audible);action(action='midi',id=synth,status=129,a=69,b=0);time.sleep(.05);assert get()['buses'][1]['peak']==0
   action(action='preset-save',name='LV2 żółć');saved=json.loads((temp/'data/presets/LV2 żółć.json').read_text());assert all(Path(n['lv2_state']).is_file() for n in saved['nodes'])
   action(action='remove',id=synth);action(action='remove',id=fx);action(action='preset-load',name='LV2 żółć')
   nodes=get()['nodes'];assert len(nodes)==2;assert next(n for n in nodes if n['instrument'])['midi_channel']==2;assert nodes[0]['parameters'][0]['value']==.25
   action(action='module-preset-save',name='LV2 FX',id=nodes[0]['id']);action(action='param',id=nodes[0]['id'],index=0,value=1);action(action='module-preset-load',name='LV2 FX',id=nodes[0]['id']);assert get()['nodes'][0]['parameters'][0]['value']==.25
   if args.browser:subprocess.run(['node',str(ROOT/'tests/ui_lv2.cjs'),url,str(build/'lv2-ui-mobile.png')],env=env,check=True,timeout=90)
   for n in nodes:action(action='remove',id=n['id'])
   bundle=temp/'plugin.zip'
   with zipfile.ZipFile(bundle,'w') as z:
    for f in (build/'lv2/jerzy-test.lv2').iterdir():z.write(f,'installed.lv2/'+f.name)
   action(action='module-import',data=base64.b64encode(bundle.read_bytes()).decode(),sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),trust=True)
   action(action='lv2-rescan');assert (temp/'data/lv2/installed.lv2/manifest.ttl').is_file()
   worker=action(action='add',module='lv2:urn:jerzy:test:worker',route=0)['id'];assert worker>0
   print('PASS LV2 catalog, FX audio/bypass, synth MIDI audio/note-off, channels, state/presets, bundle import/rescan, worker plugin')
  except BaseException:
   for log in temp.glob('*.log'):print(log.name,log.read_text()[-2000:],file=sys.stderr)
   raise
  finally:
   for process in reversed(processes):
    if process.poll() is None:
     process.terminate()
     try:process.wait(timeout=8)
     except subprocess.TimeoutExpired:process.kill();process.wait()
if __name__=='__main__':main()
