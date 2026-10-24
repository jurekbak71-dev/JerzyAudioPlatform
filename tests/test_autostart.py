import json,sys,tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'deploy/raspberry-pi'));import control
class Boot(unittest.TestCase):
 def run_case(self,fail=False):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);base=Path(temporary.name);calls=[];(base/'active-release.json').write_text(json.dumps({'path':str(ROOT)}))
  def run(args,**kwargs):
   if 'is-enabled' in args:
    unit=args[-1];scope='user' if '--user' in args else 'system'
    state='enabled' if scope=='system' and unit in ['jerzy-jack.service','jerzy-multifx4.service'] else 'disabled' if scope=='user' and unit in control.UNITS else 'not-found'
    return subprocess.CompletedProcess(args,0,stdout=state+'\n',stderr='')
   return subprocess.CompletedProcess(args,0,stdout='',stderr='')
  def command(record,action):
   calls.append((record['scope'],record['unit'],action))
   if fail and action=='enable' and record['unit']==control.UNITS[1]:raise RuntimeError('injected boot failure')
  with patch.object(control,'BASE',base),patch.object(control,'ready',return_value={'version':'0.2.0-dev'}),patch.object(control.subprocess,'run',side_effect=run),patch.object(control,'boot_command',side_effect=command):
   if fail:
    with self.assertRaisesRegex(RuntimeError,'injected'):control.autostart()
   else:control.autostart();control.restore_autostart()
  return calls,json.loads((base/'autostart-backup.json').read_text())
 def test_enable_and_restore_preserve_original_boot_selection(self):
  calls,backup=self.run_case();self.assertIn(('system','jerzy-multifx4.service','disable'),calls);self.assertIn(('system','jerzy-multifx4.service','enable'),calls)
  self.assertIn(('user',control.UNITS[0],'enable'),calls);self.assertEqual(calls[-2:], [('user',control.UNITS[0],'disable'),('user',control.UNITS[1],'disable')]);self.assertTrue(backup)
 def test_failed_enable_restores_original_flags(self):
  calls,_=self.run_case(True);self.assertIn(('system','jerzy-multifx4.service','enable'),calls);self.assertIn(('user',control.UNITS[0],'disable'),calls)
if __name__=='__main__':unittest.main()
