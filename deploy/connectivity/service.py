#!/usr/bin/env python3
"""Root-owned hardware broker. Only the installed owner's UID may use its socket."""
import argparse,asyncio,json,os,pwd,re,socket,struct,sys,time,signal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'vendor'))
from dbus_next.aio import MessageBus
from dbus_next.constants import BusType
from audio import Audio
from bluez_manager import Bluetooth,mac
MONITOR_TIMEOUT=3

async def run(*args):
 process=await asyncio.create_subprocess_exec(*args,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
 try:out,err=await asyncio.wait_for(process.communicate(),40)
 except BaseException:process.kill();await process.wait();raise
 if process.returncode:raise RuntimeError(args[0]+': '+err.decode(errors='replace')[-2000:])
 return out.decode().strip()

class Broker:
 def __init__(self,config,config_path,state,socket_path,bus,audio=None):
  self.config=config;self.state=Path(state);self.socket=Path(socket_path);self.bus=bus;self.audio=audio or Audio(self.state);self.bt=Bluetooth(bus,config,config_path,run);self.jobs={};self.last_error=None;self.cached={'uid':config['uid'],'audio':{},'bluetooth':{}};self.server=None;self.monitor=None;self.update_lock=asyncio.Lock()
 def background(self,name,coro):
  if name in self.jobs and not self.jobs[name]['task'].done():coro.close();raise RuntimeError('Operacja '+name+' nadal trwa')
  record={'pending':True,'error':None};self.jobs[name]=record
  async def work():
   try:await coro
   except Exception as error:record['error']=str(error);self.last_error=str(error)
   finally:record['pending']=False;await self.update()
  record['task']=asyncio.create_task(work())
 async def update(self):
  async with self.update_lock:
   self.cached={'uid':self.config['uid'],'pid':os.getpid(),'audio':await asyncio.to_thread(self.audio.status),'bluetooth':self.bt.status(),'operations':{name:{k:v for k,v in item.items() if k!='task'} for name,item in self.jobs.items()},'last_error':self.last_error,'updated':time.time()}
   file=self.socket.parent/'status.json';temp=file.with_suffix('.tmp');temp.write_text(json.dumps(self.cached));temp.chmod(0o644);os.replace(temp,file)
 async def dispatch(self,p):
  operation=p.get('operation')
  if operation=='status':return self.cached
  if operation=='audio-apply':return await asyncio.to_thread(self.audio.apply,int(p['rate']),int(p['buffer']),int(p['periods']))
  if operation=='audio-commit':await asyncio.to_thread(self.audio.commit,p['transaction']);return {}
  if operation=='audio-rollback':await asyncio.to_thread(self.audio.rollback,p['transaction']);return {}
  if operation in ('jack-start','jack-restart'):await run('systemctl','restart' if operation=='jack-restart' else 'start','jerzy-jack.service');await self.update();return self.cached
  if operation=='scan':await self.bt.scan();return {}
  if operation=='pair':self.background('pair',self.bt.pair(mac(p['address'])));return {'pending':True}
  if operation=='confirm':self.bt.confirm(str(p['id']),p.get('value'));return {}
  if operation=='midi-connect':self.background('midi',self.bt.connect_midi(mac(p['address'])));return {'pending':True}
  if operation=='midi-disconnect':await self.bt.disconnect_midi();return {}
  if operation=='pan-connect':self.background('pan',self.bt.pan_connect(mac(p['address'])));return {'pending':True}
  if operation=='pan-disconnect':await self.bt.pan_disconnect();return {}
  raise ValueError('Nieobsługiwana operacja sprzętowa')
 async def handle(self,reader,writer):
  try:
   credentials=writer.get_extra_info('socket').getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12);_,uid,_=struct.unpack('3i',credentials)
   if uid not in (0,self.config['uid']):raise PermissionError('Niedozwolony użytkownik')
   raw=await asyncio.wait_for(reader.readline(),5)
   if len(raw)>16384 or not raw.endswith(b'\n'):raise ValueError('Niepoprawne żądanie')
   payload=json.loads(raw)
   if not isinstance(payload,dict):raise ValueError('Wymagany obiekt JSON')
   result=await self.dispatch(payload);await self.update();reply={'ok':True,**result}
  except Exception as error:reply={'ok':False,'error':str(error)}
  try:writer.write((json.dumps(reply)+'\n').encode());await writer.drain()
  finally:writer.close();await writer.wait_closed()
 async def watch(self):
  while True:
   try:
    # A stalled BlueZ or NetworkManager read must not hide working audio
    # or postpone the audio transaction rollback checkpoint.
    if self.audio.expired():
     record=self.audio.pending();await asyncio.to_thread(self.audio.rollback,record['id']);await self.update()
     self.last_error='Przekroczono czas zmiany audio. Przywrócono poprzednią konfigurację JACK.'
    recovery=self.audio.pending()
    if recovery and recovery.get('needs_user_recovery'):
     await self.update();user=pwd.getpwuid(self.config['uid']).pw_name;uid=str(self.config['uid'])
     await run('runuser','-u',user,'--','env','XDG_RUNTIME_DIR=/run/user/'+uid,'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/'+uid+'/bus','systemctl','--user','start','jerzy-audio-platform-rollback.service')
     await asyncio.to_thread(self.audio.recovered,recovery['id'])
    await self.refresh_connectivity()
    if self.bt.midi.get('connected'):
     active=next((d for d in self.bt.devices() if d['address']==self.bt.midi['device']),{})
     if not active.get('connected'):await self.bt.disconnect_midi(forget=False)
    address=self.config.get('midi_device')
    if address and not self.bt.midi.get('connected') and time.monotonic()-self.bt.last_reconnect>20 and not self.bt.pair_path:
     self.bt.last_reconnect=time.monotonic()
     if not self.jobs.get('midi',{}).get('pending'):self.background('midi',self.bt.connect_midi(address))
    await self.update()
   except Exception as error:self.last_error=str(error)
   await asyncio.sleep(2)
 async def refresh_connectivity(self):
  for name,refresh in [('Bluetooth',self.bt.refresh),('PAN',self.bt.refresh_pan)]:
   try:await asyncio.wait_for(refresh(),MONITOR_TIMEOUT)
   except asyncio.TimeoutError:
    message=name+': przekroczono czas odczytu statusu';self.last_error=message
    if name=='Bluetooth':self.bt.error=message
    else:self.bt.pan={**self.bt.pan,'error':message}
   except Exception as error:
    self.last_error=name+': '+str(error)
    if name=='Bluetooth':self.bt.error=self.last_error
    else:self.bt.pan={**self.bt.pan,'error':self.last_error}
 async def start(self):
  self.socket.parent.mkdir(parents=True,exist_ok=True);self.socket.unlink(missing_ok=True)
  self.server=await asyncio.start_unix_server(self.handle,path=str(self.socket),limit=16385);os.chown(self.socket,0 if os.geteuid()==0 else os.getuid(),pwd.getpwuid(self.config['uid']).pw_gid);self.socket.chmod(0o660)
  await self.refresh_connectivity();await self.update();self.monitor=asyncio.create_task(self.watch())
 async def close(self):
  tasks=[record['task'] for record in self.jobs.values()]
  if self.monitor:tasks.append(self.monitor)
  if self.bt.scan_task:tasks.append(self.bt.scan_task)
  for task in tasks:task.cancel()
  if tasks:await asyncio.gather(*tasks,return_exceptions=True)
  if self.bt.notify_proxy:
   try:await asyncio.wait_for(self.bt.disconnect_midi(forget=False),2)
   except Exception:pass
  if self.server:self.server.close();await self.server.wait_closed()
  self.socket.unlink(missing_ok=True)

async def main(args):
 if os.geteuid()!=0:raise RuntimeError('Usługa sprzętowa wymaga instalacji przez administratora')
 config_path=Path(args.config);config=json.loads(config_path.read_text());bus=await MessageBus(bus_type=BusType.SYSTEM).connect();broker=Broker(config,config_path,Path(args.state),Path(args.socket),bus)
 await broker.start();done=asyncio.Event()
 for sig in (signal.SIGTERM,signal.SIGINT):asyncio.get_running_loop().add_signal_handler(sig,done.set)
 try:await done.wait()
 finally:await broker.close();bus.disconnect()
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--config',default='/var/lib/jerzy-audio-platform/config.json');parser.add_argument('--state',default='/var/lib/jerzy-audio-platform');parser.add_argument('--socket',default='/run/jerzy-audio-platform/control.sock');asyncio.run(main(parser.parse_args()))
