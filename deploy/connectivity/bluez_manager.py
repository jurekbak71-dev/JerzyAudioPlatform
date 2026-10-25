import stat as stat_module
"""BlueZ BLE MIDI client and PANU connection to an iPhone personal hotspot."""
import asyncio,ipaddress,json,re,socket,time,uuid
from pathlib import Path
from dbus_next import Variant,DBusError
from dbus_next.service import ServiceInterface,method
from ble_midi import Decoder,describe
MIDI_SERVICE='03b80e5a-ede8-4b33-a751-6ce34ec4c700'
MIDI_CHAR='7772e5db-3868-4112-a1a9-f2669d106bf3'
NAP='00001116-0000-1000-8000-00805f9b34fb'
def mac(value):
 value=str(value).upper()
 if not re.fullmatch(r'(?:[0-9A-F]{2}:){5}[0-9A-F]{2}',value):raise ValueError('Niepoprawny adres Bluetooth')
 return value

def unbox(values):return {k:v.value for k,v in values.items()}

class Agent(ServiceInterface):
 def __init__(self,owner):super().__init__('org.bluez.Agent1');self.owner=owner
 def check(self,device):
  if device!=self.owner.pair_path or time.monotonic()>self.owner.pair_deadline:raise DBusError('org.bluez.Error.Rejected','Parowanie nie zostało wybrane w panelu')
 @method()
 def Release(self):pass
 @method()
 async def RequestConfirmation(self,device:'o',passkey:'u'):
  self.check(device)
  if not await self.owner.challenge('confirm',passkey):raise DBusError('org.bluez.Error.Rejected','Odrzucono kod')
 @method()
 async def RequestPinCode(self,device:'o')->'s':
  self.check(device);value=await self.owner.challenge('pin',None)
  if not isinstance(value,str) or not re.fullmatch(r'[ -~]{1,16}',value):raise DBusError('org.bluez.Error.Rejected','Niepoprawny PIN')
  return value
 @method()
 async def RequestPasskey(self,device:'o')->'u':
  self.check(device);value=await self.owner.challenge('passkey',None)
  if not isinstance(value,int) or not 0<=value<=999999:raise DBusError('org.bluez.Error.Rejected','Niepoprawny kod')
  return value
 @method()
 def DisplayPasskey(self,device:'o',passkey:'u',entered:'q'):
  self.check(device);self.owner.prompt={'kind':'display','code':passkey,'entered':entered}
 @method()
 def DisplayPinCode(self,device:'o',pincode:'s'):
  self.check(device);self.owner.prompt={'kind':'display','code':pincode}
 @method()
 def RequestAuthorization(self,device:'o'):
  if device not in self.owner.trusted_paths():self.check(device)
 @method()
 def AuthorizeService(self,device:'o',service:'s'):
  if device!=self.owner.pair_path and device not in self.owner.trusted_paths():raise DBusError('org.bluez.Error.Rejected','Urządzenie nie jest zaufane')
 @method()
 def Cancel(self):self.owner.cancel_challenge()

class Bluetooth:
 def __init__(self,bus,config,path,runner):
  self.bus=bus;self.config=config;self.path=Path(path);self.run=runner;self.objects={};self.adapter=None;self.agent=None;self.pair_path=None;self.pair_deadline=0;self.prompt=None;self.answer=None;self.error=None;self.scanning=False;self.midi={};self.pan={};self.notify_proxy=None;self.notify_handler=None;self.decoder=Decoder();self.events=0;self.invalid=0;self.last_event=None;self.last_reconnect=0;self.scan_task=None
 def save(self):
  temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(self.config));temp.chmod(0o600);temp.replace(self.path)
 async def interface(self,path,name):
  tree=await self.bus.introspect('org.bluez',path);return self.bus.get_proxy_object('org.bluez',path,tree).get_interface(name)
 async def refresh(self):
  try:
   manager=await self.interface('/','org.freedesktop.DBus.ObjectManager');self.objects=await manager.call_get_managed_objects()
   adapters=[p for p,interfaces in self.objects.items() if 'org.bluez.Adapter1' in interfaces]
   self.adapter=adapters[0] if adapters else None
   if not self.adapter:raise RuntimeError('Brak adaptera Bluetooth')
   if self.agent is None:
    agent=Agent(self);self.bus.export('/org/jerzy/AudioAgent',agent);api=await self.interface('/org/bluez','org.bluez.AgentManager1');await api.call_register_agent('/org/jerzy/AudioAgent','KeyboardDisplay');await api.call_request_default_agent('/org/jerzy/AudioAgent');self.agent=agent
   self.error=None
  except Exception as error:self.error=str(error)
 def devices(self):
  result=[]
  for path,interfaces in self.objects.items():
   if 'org.bluez.Device1' not in interfaces:continue
   d=unbox(interfaces['org.bluez.Device1']);services=[s.lower() for s in d.get('UUIDs',[])];result.append({'path':path,'address':d['Address'],'name':d.get('Name',d.get('Alias',d['Address'])),'paired':d.get('Paired',False),'trusted':d.get('Trusted',False),'connected':d.get('Connected',False),'midi':MIDI_SERVICE in services,'pan':NAP in services,'uuids':services})
  return result
 def trusted_paths(self):return {d['path'] for d in self.devices() if d['trusted']}
 async def device(self,address):
  address=mac(address);await self.refresh()
  found=next((d for d in self.devices() if d['address'].upper()==address),None)
  if not found:raise ValueError('Urządzenie nie jest widoczne. Otwórz jego parowanie i wykonaj skan')
  return found
 async def powered(self):
  await self.refresh()
  if not self.adapter:raise RuntimeError(self.error or 'Brak Bluetooth')
  props=await self.interface(self.adapter,'org.freedesktop.DBus.Properties');await props.call_set('org.bluez.Adapter1','Powered',Variant('b',True))
 async def scan(self):
  await self.powered()
  if self.scanning:return
  adapter=await self.interface(self.adapter,'org.bluez.Adapter1');await adapter.call_set_discovery_filter({'Transport':Variant('s','auto')});await adapter.call_start_discovery();self.scanning=True
  async def finish():
   await asyncio.sleep(12)
   try:await adapter.call_stop_discovery()
   except Exception:pass
   self.scanning=False;await self.refresh()
  self.scan_task=asyncio.create_task(finish())
 def cancel_challenge(self):
  if self.answer and not self.answer.done():self.answer.set_result(False)
  self.prompt=None
 async def challenge(self,kind,code):
  self.answer=asyncio.get_running_loop().create_future();self.prompt={'id':uuid.uuid4().hex,'kind':kind,'code':code}
  try:return await asyncio.wait_for(self.answer,60)
  finally:self.prompt=None;self.answer=None
 def confirm(self,identifier,value):
  if not self.prompt or self.prompt.get('id')!=identifier or not self.answer or self.answer.done():raise ValueError('Kod wygasł albo dotyczy innego parowania')
  self.answer.set_result(value)
 async def pair(self,address):
  d=await self.device(address)
  if self.pair_path:raise RuntimeError('Inne parowanie nadal trwa')
  self.pair_path=d['path'];self.pair_deadline=time.monotonic()+75
  try:
   api=await self.interface(d['path'],'org.bluez.Device1')
   if not d['paired']:await asyncio.wait_for(api.call_pair(),70)
   props=await self.interface(d['path'],'org.freedesktop.DBus.Properties');await props.call_set('org.bluez.Device1','Trusted',Variant('b',True));await self.refresh()
  finally:self.pair_path=None;self.cancel_challenge()
 def send(self,address,data=None,panic=False):
  path=Path('/run/user')/str(self.config['uid'])/'jerzy-midi-ble.sock'
  try:
   stat=path.lstat()
   if stat.st_uid!=self.config['uid'] or not stat_module.S_ISSOCK(stat.st_mode):raise RuntimeError('Niepoprawny właściciel odbiornika MIDI')
   packet=json.dumps({'device':address,'data':list(data or []),'panic':panic,'time':time.monotonic()}).encode()
   with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as s:s.setblocking(False);s.sendto(packet,str(path))
   self.midi.pop('delivery_error',None)
  except (OSError,RuntimeError) as error:self.midi['delivery_error']=str(error)
 async def connect_midi(self,address):
  d=await self.device(address)
  # BLE MIDI may intentionally be unbonded. Explicit selection authorizes
  # this device; only the standard MIDI characteristic is subscribed.
  if self.midi.get('connected'):await self.disconnect_midi()
  props=await self.interface(d['path'],'org.freedesktop.DBus.Properties');await props.call_set('org.bluez.Device1','Trusted',Variant('b',True));self.objects[d['path']]['org.bluez.Device1']['Trusted']=Variant('b',True)
  api=await self.interface(d['path'],'org.bluez.Device1')
  if not d['connected']:
   try:await api.call_connect()
   except DBusError as error:
    if error.type not in ('org.bluez.Error.AlreadyConnected','org.bluez.Error.InProgress'):raise
  end=time.monotonic()+20;characteristic=None
  while time.monotonic()<end:
   await self.refresh()
   characteristic=next((p for p,interfaces in self.objects.items() if p.startswith(d['path']+'/') and 'org.bluez.GattCharacteristic1' in interfaces and interfaces['org.bluez.GattCharacteristic1'].get('UUID',Variant('s','')).value.lower()==MIDI_CHAR),None)
   if characteristic:break
   await asyncio.sleep(.3)
  if not characteristic:raise RuntimeError('Kontroler nie udostępnił standardowej charakterystyki BLE MIDI. Zamknij aplikację Hotone i sprawdź tryb MIDI kontrolera')
  char=await self.interface(characteristic,'org.bluez.GattCharacteristic1');props=await self.interface(characteristic,'org.freedesktop.DBus.Properties');self.decoder=Decoder()
  def notified(interface,changed,invalidated):
   if interface!='org.bluez.GattCharacteristic1' or 'Value' not in changed:return
   try:
    packet=bytes(changed['Value'].value)
    if len(packet)>512:raise ValueError('Za duża ramka MIDI')
    for event in self.decoder.decode(packet):
     self.events+=1;self.last_event={**describe(event.data),'device':d['address'],'sequence':self.events,'received':time.time()};self.send(d['address'],event.data)
   except (ValueError,TypeError):self.invalid+=1
  props.on_properties_changed(notified)
  try:await char.call_start_notify()
  except BaseException:props.off_properties_changed(notified);raise
  self.notify_proxy=(char,props);self.notify_handler=notified;self.midi={'connected':True,'device':d['address'],'name':d['name']};self.config['midi_device']=d['address'];self.save()
 async def disconnect_midi(self,forget=True):
  address=self.midi.get('device','')
  if address:self.send(address,panic=True)
  if self.notify_proxy:
   char,props=self.notify_proxy
   try:await char.call_stop_notify()
   except Exception:pass
   props.off_properties_changed(self.notify_handler)
  self.notify_proxy=None;self.notify_handler=None;self.midi={'connected':False};
  if forget:self.config.pop('midi_device',None)
  self.save()
 async def pan_connect(self,address):
  d=await self.device(address)
  if not d['paired']:raise ValueError('Najpierw sparuj iPhone')
  identifier=self.config.get('pan_profiles',{}).get(d['address'])
  if not identifier:
   identifier=str(uuid.uuid4())
   await self.run('nmcli','connection','add','type','bluetooth','con-name','Jerzy-iPhone-PAN','ifname','*','connection.uuid',identifier,'bluetooth.bdaddr',d['address'],'bluetooth.type','panu','ipv4.method','auto','ipv4.never-default','yes','ipv6.method','disabled','connection.autoconnect','yes')
   self.config.setdefault('pan_profiles',{})[d['address']]=identifier;self.save()
  try:
   await self.run('nmcli','--wait','25','connection','up','uuid',identifier)
   output=await self.run('nmcli','-g','IP4.ADDRESS','connection','show','uuid',identifier)
   addresses=[]
   for line in output.splitlines():
    try:ip=ipaddress.ip_interface(line)
    except ValueError:continue
    if ip.version==4 and not ip.ip.is_link_local and not ip.ip.is_unspecified:addresses.append(str(ip.ip))
   if not addresses:raise RuntimeError('Hotspot Bluetooth nie przydzielił IPv4')
   await self.run('nmcli','connection','modify','uuid',identifier,'connection.autoconnect','yes')
   self.pan={'connected':True,'device':d['address'],'addresses':addresses,'url':'http://'+addresses[0]+':8093/'};self.config['pan_device']=d['address'];self.save()
  except BaseException:
   await self.run('nmcli','connection','modify','uuid',identifier,'connection.autoconnect','no');self.pan={'connected':False,'error':'Połączenie PAN nie zostało potwierdzone'};raise
 async def refresh_pan(self):
  address=self.config.get('pan_device');identifier=self.config.get('pan_profiles',{}).get(address)
  if not identifier:return
  try:
   output=await self.run('nmcli','-g','IP4.ADDRESS','connection','show','uuid',identifier)
   addresses=[]
   for line in output.splitlines():
    try:ip=ipaddress.ip_interface(line)
    except ValueError:continue
    if ip.version==4 and not ip.ip.is_link_local and not ip.ip.is_unspecified:addresses.append(str(ip.ip))
   self.pan={'connected':bool(addresses),'device':address,'addresses':addresses}
   if addresses:self.pan['url']='http://'+addresses[0]+':8093/'
  except Exception as error:self.pan={'connected':False,'device':address,'error':str(error)}
 async def pan_disconnect(self):
  address=self.config.get('pan_device');identifier=self.config.get('pan_profiles',{}).get(address)
  if identifier:
   await self.run('nmcli','connection','modify','uuid',identifier,'connection.autoconnect','no');await self.run('nmcli','connection','down','uuid',identifier)
  self.pan={'connected':False};self.config.pop('pan_device',None);self.save()
 def status(self):
  adapter=unbox(self.objects.get(self.adapter,{}).get('org.bluez.Adapter1',{}))
  return {'error':self.error,'powered':adapter.get('Powered',False),'scanning':self.scanning,'devices':self.devices(),'pairing':self.prompt,'pairing_device':self.pair_path,'midi':self.midi,'pan':self.pan,'events':self.events,'invalid_packets':self.invalid,'last_event':self.last_event}
