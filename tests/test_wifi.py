import contextlib,importlib.util,io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wifi_home',ROOT/'deploy/network/wifi_home.py');wifi=importlib.util.module_from_spec(spec);spec.loader.exec_module(wifi)
class Wifi(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)/'state';self.profiles=Path(self.tmp.name)/'profiles';self.profiles.mkdir();self.old=self.profiles/'old.nmconnection';self.old.write_text('existing hotspot, unchanged');self.commands=[];self.active='old-uuid';self.new='';self.clock=1000.;self.fail=False
  self.patches=[patch.object(wifi,'BASE',self.base),patch.object(wifi,'PROFILES',self.profiles),patch.object(wifi,'run',side_effect=self.nm_run),patch.object(wifi.os,'geteuid',return_value=0),patch.object(wifi.shutil,'which',return_value='/usr/bin/nmcli'),patch('builtins.input',return_value='Dom WiFi'),patch.object(wifi.getpass,'getpass',return_value='test-password 71'),patch.object(wifi.time,'time',side_effect=lambda:self.clock),patch.object(wifi.time,'monotonic',side_effect=lambda:self.clock)]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def nm_run(self,*args,check=True,timeout=30):
  self.commands.append(args)
  if args[:2]==('systemctl','is-active'):return 'active'
  if args[:4]==('nmcli','-t','-f','DEVICE,TYPE'):return 'wlan0:wifi'
  if args[:4]==('nmcli','-t','-f','UUID,DEVICE'):return self.active+':wlan0'
  if args[:3]==('nmcli','-g','connection.autoconnect-priority'):return '100'
  if args[:3]==('nmcli','-g','IP4.ADDRESS'):return '192.168.1.71/24'
  if args[:3]==('nmcli','connection','load'):
   text=Path(args[3]).read_text();self.new=next(line.split('=',1)[1] for line in text.splitlines() if line.startswith('uuid='))
  if 'up' in args and 'uuid' in args:
   target=args[-1]
   if target==self.new and self.fail:raise RuntimeError('injected Wi-Fi failure')
   self.active=target
  if not check:return type('Result',(),{'returncode':0,'stderr':''})()
  return ''
 def prepare(self):
  with contextlib.redirect_stdout(io.StringIO()):wifi.prepare()
 def state(self):return json.loads((self.base/'state.json').read_text())
 def test_prepare_preserves_hotspot_and_keeps_password_out_of_commands(self):
  self.prepare();self.assertEqual(self.old.read_text(),'existing hotspot, unchanged');self.assertEqual(self.active,'old-uuid');self.assertFalse(any('test-password 71' in part for cmd in self.commands for part in cmd));self.assertNotIn('test-password',json.dumps(self.state()))
  file=next(self.profiles.glob('jerzy-home-*.nmconnection'));self.assertEqual(file.stat().st_mode&0o777,0o600);text=file.read_text();self.assertIn('autoconnect=false',text);self.assertIn('autoconnect-priority=110',text);self.assertIn('test-password\\s71',text)
 def test_unconfirmed_change_returns_to_previous_uuid(self):
  self.prepare();state=self.state();state['deadline']=self.clock+12;state['deadline_monotonic']=self.clock+12;wifi.save(state)
  def sleep(seconds):self.clock+=seconds
  with patch.object(wifi.time,'sleep',side_effect=sleep),contextlib.redirect_stdout(io.StringIO()):wifi.worker()
  self.assertEqual(self.state()['phase'],'rolled-back');self.assertEqual(self.active,'old-uuid');self.assertEqual(self.old.read_text(),'existing hotspot, unchanged')
 def test_confirmation_keeps_home_profile_and_stop_post_does_not_revert(self):
  self.prepare()
  def sleep(seconds):
   self.clock+=seconds
   if self.state()['phase']=='awaiting-confirmation':wifi.confirm()
  with patch.object(wifi.time,'sleep',side_effect=sleep),contextlib.redirect_stdout(io.StringIO()):wifi.worker();wifi.rollback()
  self.assertEqual(self.active,self.new);self.assertEqual(self.state()['phase'],'confirmed');self.assertTrue(any(cmd[-2:]==('connection.autoconnect','yes') for cmd in self.commands));self.assertEqual(self.old.read_text(),'existing hotspot, unchanged')
 def test_connection_failure_rolls_back(self):
  self.prepare();self.fail=True
  with patch.object(wifi.time,'sleep',side_effect=lambda s:None),contextlib.redirect_stdout(io.StringIO()):
   with self.assertRaisesRegex(RuntimeError,'injected'):wifi.worker()
  self.assertEqual(self.state()['phase'],'rolled-back');self.assertEqual(self.active,'old-uuid')
 def test_placeholder_and_link_local_addresses_are_not_readiness(self):
  with patch.object(wifi,'run',return_value='--\n169.254.1.2/16\n127.0.0.1/8'):
   self.assertEqual(wifi.address('wlan0'),[])
 def test_late_confirmation_is_rejected(self):
  self.prepare();state=self.state();state['phase']='awaiting-confirmation';state['deadline']=self.clock-1;state['deadline_monotonic']=self.clock-1;wifi.save(state)
  with self.assertRaises(RuntimeError):wifi.confirm()
  self.assertFalse(self.state()['confirmed'])
if __name__=='__main__':unittest.main()
