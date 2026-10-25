"""Real private D-Bus + local RPC, simulated BlueZ radio objects (not hardware)."""
import asyncio,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'deploy/connectivity'),str(ROOT/'deploy/connectivity/vendor')]
from dbus_next import Variant
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface,method,dbus_property
from dbus_next.constants import PropertyAccess
from bluez_manager import MIDI_SERVICE,MIDI_CHAR,NAP
from service import Broker
import client
from unittest.mock import patch
ADAPTER='/org/bluez/hci0';MIDI=ADAPTER+'/dev_AA_BB_CC_DD_EE_01';PHONE=ADAPTER+'/dev_AA_BB_CC_DD_EE_02';CHAR=MIDI+'/service001/char001'
class Adapter(ServiceInterface):
 def __init__(self):super().__init__('org.bluez.Adapter1');self.power=False;self.scanning=False
 @dbus_property(access=PropertyAccess.READWRITE)
 def Powered(self)->'b':return self.power
 @Powered.setter
 def Powered(self,value:'b'):self.power=value
 @method()
 def SetDiscoveryFilter(self,settings:'a{sv}'):pass
 @method()
 def StartDiscovery(self):self.scanning=True
 @method()
 def StopDiscovery(self):self.scanning=False
class Device(ServiceInterface):
 def __init__(self,path,address,services,bus,hub):super().__init__('org.bluez.Device1');self.path=path;self.address=address;self.services=services;self.bus=bus;self.hub=hub;self.paired=False;self.trusted=False;self.connected=False
 @dbus_property(access=PropertyAccess.READ)
 def Address(self)->'s':return self.address
 @dbus_property(access=PropertyAccess.READ)
 def Name(self)->'s':return 'Ampero Control' if self.path==MIDI else 'Test iPhone'
 @dbus_property(access=PropertyAccess.READ)
 def Paired(self)->'b':return self.paired
 @dbus_property(access=PropertyAccess.READWRITE)
 def Trusted(self)->'b':return self.trusted
 @Trusted.setter
 def Trusted(self,value:'b'):self.trusted=value
 @dbus_property(access=PropertyAccess.READ)
 def Connected(self)->'b':return self.connected
 @dbus_property(access=PropertyAccess.READ)
 def UUIDs(self)->'as':return self.services
 @method()
 async def Pair(self):
  tree=await self.bus.introspect(self.hub.destination,self.hub.agent_path);agent=self.bus.get_proxy_object(self.hub.destination,self.hub.agent_path,tree).get_interface('org.bluez.Agent1');await agent.call_request_confirmation(self.path,123456);self.paired=True
 @method()
 def Connect(self):self.connected=True
class Characteristic(ServiceInterface):
 def __init__(self):super().__init__('org.bluez.GattCharacteristic1');self.value=b'';self.notifying=False
 @dbus_property(access=PropertyAccess.READ)
 def UUID(self)->'s':return MIDI_CHAR
 @dbus_property(access=PropertyAccess.READ)
 def Value(self)->'ay':return self.value
 @dbus_property(access=PropertyAccess.READ)
 def Notifying(self)->'b':return self.notifying
 @method()
 def StartNotify(self):self.notifying=True
 @method()
 def StopNotify(self):self.notifying=False
 def emit(self,value):self.value=value;self.emit_properties_changed({'Value':value})
class AgentManager(ServiceInterface):
 def __init__(self):super().__init__('org.bluez.AgentManager1');self.agent_path=None;self.destination=None
 @method()
 def RegisterAgent(self,path:'o',capability:'s'):self.agent_path=path
 @method()
 def RequestDefaultAgent(self,path:'o'):pass
class Objects(ServiceInterface):
 def __init__(self,adapter,midi,phone,char):super().__init__('org.freedesktop.DBus.ObjectManager');self.adapter=adapter;self.midi=midi;self.phone=phone;self.char=char
 @method()
 def GetManagedObjects(self)->'a{oa{sa{sv}}}':
  result={ADAPTER:{'org.bluez.Adapter1':{'Powered':Variant('b',self.adapter.power)}}}
  for device in [self.midi,self.phone]:result[device.path]={'org.bluez.Device1':{'Address':Variant('s',device.address),'Name':Variant('s',device.Name),'Paired':Variant('b',device.paired),'Trusted':Variant('b',device.trusted),'Connected':Variant('b',device.connected),'UUIDs':Variant('as',device.services)}}
  if self.midi.connected:result[CHAR]={'org.bluez.GattCharacteristic1':{'UUID':Variant('s',MIDI_CHAR)}}
  return result
class AudioFake:
 def status(self):return {'running':True,'rate':44100,'buffer':512,'periods':3}
 def pending(self):return None
 def expired(self):return False
class BluezContract(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.daemon=subprocess.Popen(['dbus-daemon','--session','--nofork','--print-address=1'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True);address=self.daemon.stdout.readline().strip();self.bus=await MessageBus(bus_address=address).connect();await self.bus.request_name('org.bluez');self.peer=await MessageBus(bus_address=address).connect();self.hub=AgentManager();self.hub.destination=self.peer.unique_name;self.adapter=Adapter();self.midi=Device(MIDI,'AA:BB:CC:DD:EE:01',[MIDI_SERVICE],self.bus,self.hub);self.phone=Device(PHONE,'AA:BB:CC:DD:EE:02',[NAP],self.bus,self.hub);self.char=Characteristic();self.bus.export('/org/bluez',self.hub);self.bus.export(ADAPTER,self.adapter);self.bus.export(MIDI,self.midi);self.bus.export(PHONE,self.phone);self.bus.export(CHAR,self.char);self.bus.export('/',Objects(self.adapter,self.midi,self.phone,self.char));self.config={'uid':os.getuid()};self.config_file=self.root/'config.json';self.config_file.write_text(json.dumps(self.config));self.broker=Broker(self.config,self.config_file,self.root/'state',self.root/'run/control.sock',self.peer,AudioFake());self.sent=[];self.broker.bt.send=lambda address,data=None,panic=False:self.sent.append((address,data,panic));await self.broker.start();self.patch=patch.object(client,'SOCKET',str(self.broker.socket));self.patch.start()
 async def asyncTearDown(self):
  self.patch.stop();await self.broker.close();self.bus.disconnect();self.peer.disconnect();self.daemon.terminate();self.daemon.wait(timeout=3);self.daemon.stdout.close();self.tmp.cleanup();await asyncio.sleep(.01)
 async def rpc(self,operation,**args):return await asyncio.to_thread(client.call,operation,**args)
 async def test_scan_and_reject_unknown_operations(self):
  await self.rpc('scan');self.assertTrue(self.adapter.power);self.assertTrue(self.adapter.scanning);status=await self.rpc('status');self.assertEqual(len(status['bluetooth']['devices']),2)
  with self.assertRaisesRegex(RuntimeError,'Nieobsługiwana'):await self.rpc('shell',command='anything')
 async def test_pair_requires_explicit_confirmation(self):
  await self.rpc('pair',address=self.phone.address)
  for _ in range(100):
   if self.broker.bt.prompt:break
   await asyncio.sleep(.01)
  self.assertFalse(self.phone.paired);self.assertEqual(self.broker.bt.prompt['code'],123456);await self.rpc('confirm',id=self.broker.bt.prompt['id'],value=True);await self.broker.jobs['pair']['task'];self.assertTrue(self.phone.paired);self.assertTrue(self.phone.trusted)
 async def test_unbonded_ble_midi_notifies_and_disconnects(self):
  self.assertFalse(self.midi.paired);await self.rpc('midi-connect',address=self.midi.address);await self.broker.jobs['midi']['task'];self.assertIsNone(self.broker.jobs['midi']['error']);self.assertTrue(self.char.notifying);self.char.emit(bytes([0x80,0x81,0xb0,21,127]));await asyncio.sleep(.05);self.assertEqual(self.sent[-1][1],bytes([0xb0,21,127]));self.assertEqual(self.broker.bt.last_event['number'],21);await self.rpc('midi-disconnect');self.assertFalse(self.char.notifying);self.assertTrue(self.sent[-1][2])
 async def test_pan_uses_own_profile_and_never_replaces_wifi_default(self):
  self.phone.paired=True;commands=[]
  async def runner(*args):commands.append(args);return '172.20.10.2/28' if args[:3]==('nmcli','-g','IP4.ADDRESS') else ''
  self.broker.bt.run=runner;await self.rpc('pan-connect',address=self.phone.address);await self.broker.jobs['pan']['task'];self.assertIsNone(self.broker.jobs['pan']['error']);self.assertEqual(self.broker.bt.pan['url'],'http://172.20.10.2:8093/');self.assertTrue(any('ipv4.never-default' in c and 'yes' in c for c in commands));identifier=self.config['pan_profiles'][self.phone.address];await self.rpc('pan-disconnect');self.assertIn(('nmcli','connection','down','uuid',identifier),commands)
if __name__=='__main__':unittest.main()
