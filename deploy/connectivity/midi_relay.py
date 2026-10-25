#!/usr/bin/env python3
"""User-owned BLE-to-JACK bridge supervisor and non-realtime preset switching."""
import argparse,asyncio,fcntl,json,os,re,signal,socket,stat,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=Path.home()/'.local/share/jerzy-audio-platform'
class Relay(asyncio.DatagramProtocol):
 def __init__(self,runtime,base,binary):self.runtime=runtime;self.base=base;self.binary=binary;self.bridge=None;self.tasks=[];self.last=None;self.received=0;self.dropped=0;self.error=None;self.triggers=asyncio.Queue(32);self.pressed={};self.stopping=False
 def connection_made(self,transport):self.transport=transport
 def send(self,data):
  try:
   with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as s:s.setblocking(False);s.sendto(data,str(self.runtime/'jerzy-midi-jack.sock'))
   if self.error and self.error.startswith('JACK:'):self.error=None
  except OSError as error:self.error='JACK: '+str(error);self.dropped+=1
 def datagram_received(self,data,address):
  try:
   if len(data)>2048:raise ValueError('Za duże MIDI')
   value=json.loads(data);message=bytes(value.get('data',[]))
   if value.get('panic'):self.send(b'!');return
   if not 1<=len(message)<=3 or message[0]<128 or any(b>127 for b in message[1:]):raise ValueError('Niepoprawny komunikat MIDI')
   self.send(message);self.received+=1;self.last={'device':value.get('device',''),'bytes':list(message),'received':time.time(),'monotonic':time.monotonic(),'sequence':self.received}
   if message[0]&0xf0 in (0xb0,0xc0):
    try:self.triggers.put_nowait(value)
    except asyncio.QueueFull:self.dropped+=1
  except (ValueError,TypeError):self.dropped+=1
 def http(self,path,data=None):
  url='http://127.0.0.1:8093'+path
  if data is None:return json.load(urllib.request.urlopen(url,timeout=4))
  token=self.http('/api/session')['token'];request=urllib.request.Request(url,json.dumps(data).encode(),{'Content-Type':'application/json','X-Jerzy-Token':token});return json.load(urllib.request.urlopen(request,timeout=8))
 async def actions(self):
  while True:
   value=await self.triggers.get()
   try:
    file=self.base/'midi-bindings.json';bindings=json.loads(file.read_text()) if file.exists() else []
    data=value['data'];kind='pc' if data[0]&240==192 else 'cc';channel=(data[0]&15)+1;number=data[1]
    for binding in bindings:
     if binding.get('action')!='preset' or binding.get('type')!=kind or binding.get('channel')!=channel or binding.get('number')!=number or binding.get('device') not in ('',None,value.get('device')):continue
     key=binding['slot'];pressed=kind=='pc' or data[2]>0;previous=self.pressed.get(key,False);self.pressed[key]=pressed
     if pressed and (kind=='pc' or not previous):await asyncio.to_thread(self.http,'/api/action',{'action':'preset-load','name':binding['preset']})
   except Exception as error:self.error='Przełączanie presetu: '+str(error)
   finally:self.triggers.task_done()
 async def bridge_loop(self):
  path=self.runtime/'jerzy-midi-jack.sock';status_file=self.base/'bluetooth-midi-bridge.json'
  while not self.stopping:
   if path.exists():
    if path.lstat().st_uid!=os.getuid() or not stat.S_ISSOCK(path.lstat().st_mode):raise RuntimeError('Niepoprawny właściciel gniazda JACK MIDI')
    old=json.loads(status_file.read_text()) if status_file.exists() else {}
    pid=old.get('pid',0)
    if old.get('running') and pid and (Path('/proc')/str(pid)/'cmdline').exists() and str(self.binary).encode() in (Path('/proc')/str(pid)/'cmdline').read_bytes():raise RuntimeError('Poprzedni most MIDI nadal działa')
    path.unlink()
   self.bridge=await asyncio.create_subprocess_exec(str(self.binary),str(path),str(status_file))
   await self.bridge.wait()
   if not self.stopping:await asyncio.sleep(2)
 def core_status(self):
  with socket.socket(socket.AF_UNIX) as s:
   s.settimeout(2);s.connect(str(self.base/'core.sock'));s.sendall(b'STATUS\n');raw=b''
   while not raw.endswith(b'\n'):
    part=s.recv(65536)
    if not part:raise RuntimeError('Brak silnika')
    raw+=part
  return json.loads(raw)
 async def status_loop(self):
  while True:
   try:
    state=await asyncio.to_thread(self.core_status)
    if state.get('engine_available',True) and re.fullmatch(r'JerzyAudioPlatform[\w-]*',state.get('client','')):self.send(('@'+state['client']+':midi').encode())
   except Exception:pass
   file=self.base/'bluetooth-midi.json';temp=file.with_suffix('.tmp');temp.write_text(json.dumps({'running':True,'received':self.received,'dropped':self.dropped,'last_event':self.last,'error':self.error}));os.replace(temp,file)
   await asyncio.sleep(1)
 async def start(self):
  self.runtime.mkdir(parents=True,exist_ok=True);self.lock=(self.runtime/'jerzy-midi-relay.lock').open('a');fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB);self.base.mkdir(parents=True,exist_ok=True);path=self.runtime/'jerzy-midi-ble.sock'
  if path.exists():
   if path.lstat().st_uid!=os.getuid() or not stat.S_ISSOCK(path.lstat().st_mode):raise RuntimeError('Niepoprawne gniazdo BLE MIDI')
   path.unlink()
  await asyncio.get_running_loop().create_datagram_endpoint(lambda:self,local_addr=str(path),family=socket.AF_UNIX);path.chmod(0o600)
  self.tasks=[asyncio.create_task(self.bridge_loop()),asyncio.create_task(self.actions()),asyncio.create_task(self.status_loop())]
 async def close(self):
  self.stopping=True
  if self.bridge and self.bridge.returncode is None:
   self.bridge.terminate()
   try:await asyncio.wait_for(self.bridge.wait(),3)
   except asyncio.TimeoutError:self.bridge.kill();await self.bridge.wait()
  for task in self.tasks:task.cancel()
  if hasattr(self,'transport'):self.transport.close()
  (self.runtime/'jerzy-midi-ble.sock').unlink(missing_ok=True)
async def main():
 parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path,default=Path('/run/user')/str(os.getuid()));parser.add_argument('--data',type=Path,default=BASE);parser.add_argument('--binary',type=Path,default=ROOT/'bin/jerzy-midi-bridge');args=parser.parse_args();relay=Relay(args.runtime,args.data,args.binary);await relay.start();done=asyncio.Event()
 for signum in (signal.SIGTERM,signal.SIGINT):asyncio.get_running_loop().add_signal_handler(signum,done.set)
 try:
  stop=asyncio.create_task(done.wait());await asyncio.wait([stop,*relay.tasks],return_when=asyncio.FIRST_COMPLETED)
  for task in relay.tasks:
   if task.done() and task.exception():raise task.exception()
 finally:await relay.close()
if __name__=='__main__':asyncio.run(main())
