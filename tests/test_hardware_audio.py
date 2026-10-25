import importlib.util,json,shlex,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'deploy/connectivity'))
from audio import Audio
class HardwareAudio(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.proc=self.root/'proc';(self.proc/'42').mkdir(parents=True);(self.proc/'42/exe').symlink_to('/usr/bin/jackd');self.args=['/usr/bin/jackd','-R','-P','70','-d','alsa','-d','hw:CARD=Core,DEV=0','-r','44100','-p','64','-n','3','-i','6','-o','4'];self.dropin=self.root/'systemd/90-jerzy-audio-platform.conf';self.calls=[];self.fail=False;self.write_args(self.args);self.audio=Audio(self.root/'state',self.dropin,self.command,self.proc)
 def tearDown(self):self.tmp.cleanup()
 def write_args(self,args):(self.proc/'42/cmdline').write_bytes(b'\0'.join(a.encode() for a in args)+b'\0')
 def command(self,*args):
  self.calls.append(args)
  if '--property=MainPID' in args:return '42'
  if args==('systemctl','restart','jerzy-jack.service'):
   current=shlex.split(self.dropin.read_text().split('ExecStart=')[-1].strip()) if self.dropin.exists() else self.args
   if self.fail:self.fail=False;raise RuntimeError('injected ALSA failure')
   self.write_args(current)
  return ''
 def test_profile_changes_only_rate_buffer_periods_and_commits(self):
  result=self.audio.apply(48000,512,3);current=self.audio.argv();self.assertIn('hw:CARD=Core,DEV=0',current);self.assertIn('70',current);self.assertEqual(current[-6:],['-r','48000','-p','512','-n','3']);self.assertIn('6',current);self.audio.commit(result['transaction']);self.assertFalse(self.audio.expired());self.assertEqual(self.audio.status()['buffer'],512)
 def test_failed_driver_restart_restores_exact_previous_file(self):
  original='# Managed by Jerzy Audio Platform\n[Service]\nExecStart=\nExecStart='+shlex.join(self.args)+'\n';self.dropin.parent.mkdir();self.dropin.write_text(original);self.fail=True
  with self.assertRaisesRegex(RuntimeError,'ALSA'):self.audio.apply(48000,512,2)
  self.assertEqual(self.dropin.read_text(),original);self.assertEqual(self.audio.settings(self.audio.argv()),{'rate':44100,'buffer':64,'periods':3});self.assertEqual(self.audio.pending()['phase'],'rolled-back')
 def test_unacknowledged_change_expires_and_can_restore(self):
  result=self.audio.apply(44100,256,3)
  with patch('audio.time.monotonic',return_value=self.audio.pending()['deadline']+1):self.assertTrue(self.audio.expired())
  self.audio.rollback(result['transaction']);self.assertFalse(self.dropin.exists());self.assertTrue(self.audio.pending()['needs_user_recovery']);self.audio.recovered(result['transaction']);self.assertFalse(self.audio.pending()['needs_user_recovery'])
 def test_rejects_other_units_bad_profiles_and_unknown_dropin(self):
  for args in [(96000,256,3),(44100,42,3),(44100,256,7)]:
   with self.assertRaises(ValueError):self.audio.apply(*args)
  self.dropin.parent.mkdir();self.dropin.write_text('administrator configuration')
  with self.assertRaisesRegex(RuntimeError,'nie należy'):self.audio.apply(44100,512,3)
  self.assertEqual(self.dropin.read_text(),'administrator configuration')
 def test_preserves_other_backend_options_and_replaces_attached_flags(self):
  args=['/usr/bin/jackd','-R','-P70','-d','alsa','-dhw:Core','-r44100','--period=64','-n3','-i6','-o4']
  updated=Audio.configured(args,48000,512,2);self.assertEqual(updated[:7],['/usr/bin/jackd','-R','-P70','-d','alsa','-dhw:Core','-i6']);self.assertEqual(updated[-6:],['-r','48000','-p','512','-n','2'])
if __name__=='__main__':unittest.main()
