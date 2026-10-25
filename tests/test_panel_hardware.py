import importlib.util,json,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'web-ui'));sys.path.insert(0,str(ROOT/'module-manager'))
from hardware import Hardware
class Panel(Hardware):
 def __init__(self,data):self.data=data;self.lock=threading.RLock();self.init_hardware();self.commands=[]
 def core(self,command):
  self.commands.append(command)
  if command=='LIST':return {'nodes':[{'id':1,'module':'bass-ambient-pro-original','route':1,'parameters':[{'id':k,'value':v} for k,v in [('bass',1),('pad',0),('autoPlay',0),('performanceSource',0)]]}]}
  if command=='STATUS':raise OSError('engine down')
  return {'ok':True}
class HardwarePanel(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.panel=Panel(Path(self.temp.name))
 def test_silent_legacy_state_start_sets_jam_and_autoplay(self):
  self.panel.instrument({'id':1,'command':'start'})
  self.assertIn('PARAM 1 3 2',self.panel.commands);self.assertIn('PARAM 1 2 1',self.panel.commands);self.assertIn('BYPASS 1 0',self.panel.commands)
 def test_faulted_jam_recreates_before_enabling(self):
  original=self.panel.core
  def faulted(command):
   value=original(command)
   if command=='LIST':value['nodes'][0]['fault']=1
   return value
  self.panel.core=faulted;self.panel.instrument({'id':1,'command':'start'})
  commands=self.panel.commands
  self.assertLess(commands.index('PARAM 1 2 1'),commands.index('RESET 1'));self.assertLess(commands.index('RESET 1'),commands.index('BYPASS 1 0'))
 def test_stop_does_not_change_instrument_levels(self):
  self.panel.instrument({'id':1,'command':'stop'});self.assertEqual(self.panel.commands,['LIST','PARAM 1 2 0'])
 def test_offline_core_returns_panel_state(self):
  result=self.panel.core_state();self.assertFalse(result['engine_available']);self.assertEqual(result['nodes'],[]);self.assertIn('engine down',result['engine_error'])
 def test_async_job_preserves_failure_for_panel(self):
  with patch('hardware.subprocess.run',side_effect=RuntimeError('driver rejected configuration')):
   self.panel.start_job('apply',['fake'])
   for _ in range(50):
    if not self.panel.operation['pending']:break
    time.sleep(.01)
  self.assertFalse(self.panel.operation['pending']);self.assertIn('driver rejected',self.panel.operation['error'])
