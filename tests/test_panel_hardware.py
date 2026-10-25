import importlib.util,json,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'web-ui'));sys.path.insert(0,str(ROOT/'module-manager'))
from hardware import Hardware,pi_health
class PiHealth(unittest.TestCase):
 def test_sensors_and_current_versus_historical_flags(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   for name,value in [('class/thermal/thermal_zone0/temp','62500'),('devices/system/cpu/cpu0/cpufreq/scaling_cur_freq','1500000')]:
    file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(value)
   with patch('hardware.subprocess.run') as run:
    run.return_value.stdout='throttled=0x50001\n'
    value=pi_health(root)
   self.assertEqual(value['temperature_c'],62.5);self.assertEqual(value['cpu_frequency_mhz'],1500)
   self.assertTrue(value['flags']['under_voltage']);self.assertFalse(value['flags']['throttled']);self.assertTrue(value['flags']['throttled_occurred'])
   self.assertEqual(run.call_args.kwargs['timeout'],1)
 def test_missing_sensors_and_command_are_unknown(self):
  with tempfile.TemporaryDirectory() as temp,patch('hardware.subprocess.run',side_effect=FileNotFoundError):
   self.assertTrue(all(v is None for v in pi_health(Path(temp)).values()))
 def test_invalid_sensor_and_firmware_output_are_unknown(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);file=root/'class/thermal/thermal_zone0/temp';file.parent.mkdir(parents=True);file.write_text('invalid')
   with patch('hardware.subprocess.run') as run:
    run.return_value.stdout='unexpected'
    value=pi_health(root)
   self.assertIsNone(value['temperature_c']);self.assertIsNone(value['flags'])
 def test_firmware_timeout_does_not_break_report(self):
  import subprocess
  with tempfile.TemporaryDirectory() as temp,patch('hardware.subprocess.run',side_effect=subprocess.TimeoutExpired('vcgencmd',1)):
   self.assertIsNone(pi_health(Path(temp))['throttled_raw'])

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
 def test_health_is_cached_and_included_without_engine(self):
  with patch('hardware.hardware_status',return_value={}),patch('hardware.pi_health',return_value={'temperature_c':60}) as read,patch('hardware.time.monotonic',side_effect=[10,11,16]):
   first=self.panel.hardware_state();first['host_health']['temperature_c']=0
   self.assertEqual(self.panel.hardware_state()['host_health']['temperature_c'],60)
   self.panel.hardware_state();self.assertEqual(read.call_count,2)
 def test_async_job_preserves_failure_for_panel(self):
  with patch('hardware.subprocess.run',side_effect=RuntimeError('driver rejected configuration')):
   self.panel.start_job('apply',['fake'])
   for _ in range(50):
    if not self.panel.operation['pending']:break
    time.sleep(.01)
  self.assertFalse(self.panel.operation['pending']);self.assertIn('driver rejected',self.panel.operation['error'])
