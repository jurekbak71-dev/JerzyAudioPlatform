import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'deploy/raspberry-pi'))
spec=importlib.util.spec_from_file_location('upgrade_control',ROOT/'deploy/raspberry-pi/control.py');control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
class ModuleUpgrade(unittest.TestCase):
 def test_upgrade_uses_new_directory_and_rollback_restores_old_bytes(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp)/'data';release=Path(tmp)/'release';history=base/'history';history.mkdir(parents=True)
   for parent,version,payload in [(base,'0.1.0',b'old loaded ELF'),(release,'0.2.1',b'new ELF')]:
    path=parent/'modules/cab-ir';path.mkdir(parents=True);(path/'manifest.json').write_text(json.dumps({'id':'cab-ir','version':version}));(path/'cab-ir.so').write_bytes(payload)
   with patch.object(control,'BASE',base):
    backups=control.module_upgrade_plan(release,history)
    self.assertEqual((base/'modules/cab-ir/cab-ir.so').read_bytes(),b'old loaded ELF')
    control.upgrade_modules(release,backups)
    self.assertEqual((base/'modules/cab-ir/cab-ir.so').read_bytes(),b'new ELF')
    control.restore_modules({'module_backups':backups})
    self.assertEqual((base/'modules/cab-ir/cab-ir.so').read_bytes(),b'old loaded ELF')
    self.assertTrue(list(history.glob('failed-cab-ir-*')))
 def test_local_newer_version_is_preserved(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp)/'data';release=Path(tmp)/'release';history=base/'history';history.mkdir(parents=True)
   for parent,version in [(base,'9.0.0-custom'),(release,'0.2.1')]:
    path=parent/'modules/cab-ir';path.mkdir(parents=True);(path/'manifest.json').write_text(json.dumps({'id':'cab-ir','version':version}))
   with patch.object(control,'BASE',base):self.assertEqual(control.module_upgrade_plan(release,history),{})
if __name__=='__main__':unittest.main()
