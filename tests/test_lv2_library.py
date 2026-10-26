import hashlib,os,platform,shutil,stat,struct,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'module-manager'))
from lv2_library import LV2Library
BUILD=Path(os.environ.get('JERZY_TEST_BUILD',ROOT/'build-lv2'))
class LV2Packages(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.library=LV2Library(BUILD/'jerzy-audio-core',self.root/'plugins')
 def bundle(self,files):
  path=self.root/'test.zip'
  with zipfile.ZipFile(path,'w') as z:
   for name,value in files.items():z.writestr(name,value)
  return path,hashlib.sha256(path.read_bytes()).hexdigest()
 def test_failed_rescan_keeps_previous_catalog(self):
  previous=[{'id':'lv2:existing'}];self.library.cache=previous
  with patch('lv2_library.subprocess.run',side_effect=subprocess.TimeoutExpired('core',30)):
   self.assertEqual(self.library.list(refresh=True),previous)
  self.assertIn('biblioteki',self.library.last_error)
 def test_rejects_path_escape(self):
  path,checksum=self.bundle({'x.lv2/../../escape':b'x'})
  with self.assertRaisesRegex(ValueError,'ścieżka'):self.library.install(path,checksum)
  self.assertFalse((self.root/'escape').exists())
 def test_rejects_symlink(self):
  path=self.root/'test.zip'
  with zipfile.ZipFile(path,'w') as z:
   entry=zipfile.ZipInfo('x.lv2/file');entry.create_system=3;entry.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(entry,'/etc/passwd')
  with self.assertRaisesRegex(ValueError,'symlink'):self.library.install(path,hashlib.sha256(path.read_bytes()).hexdigest())
 def test_rejects_wrong_architecture(self):
  data=bytearray(64);data[:6]=b'\x7fELF\x02\x01';struct.pack_into('<H',data,16,3);struct.pack_into('<H',data,18,183 if platform.machine()=='x86_64' else 62)
  path,checksum=self.bundle({'x.lv2/manifest.ttl':b'','x.lv2/x.so':data})
  with self.assertRaisesRegex(ValueError,'architektury'):self.library.install(path,checksum)
 def test_rejects_bad_checksum(self):
  path,_=self.bundle({'x.lv2/manifest.ttl':b''})
  with self.assertRaisesRegex(ValueError,'SHA256'):self.library.install(path,'0'*64)
 def test_rejects_incomplete_or_multiple_bundles(self):
  for files in [{'x.lv2/manifest.ttl':b''},{'x.lv2/a':b'','y.lv2/b':b''}]:
   path,checksum=self.bundle(files)
   with self.assertRaises(ValueError):self.library.install(path,checksum)
 def test_installs_replaces_and_rolls_back_real_fixture(self):
  fixture=BUILD/'lv2/jerzy-test.lv2';path,checksum=self.bundle({'test.lv2/'+p.name:p.read_bytes() for p in fixture.iterdir()})
  self.library.install(path,checksum);self.assertTrue((self.library.root/'test.lv2/fixture.so').is_file())
  first=(self.library.root/'test.lv2/plugins.ttl').read_text();files={'test.lv2/'+p.name:p.read_bytes() for p in fixture.iterdir()};files['test.lv2/plugins.ttl']=files['test.lv2/plugins.ttl'].replace(b'Test LV2 Gain',b'Updated LV2 Gain');path,checksum=self.bundle(files);self.library.install(path,checksum)
  self.assertIn('Updated LV2 Gain',(self.library.root/'test.lv2/plugins.ttl').read_text());self.library.rollback('lv2:urn:jerzy:test:gain');self.assertEqual((self.library.root/'test.lv2/plugins.ttl').read_text(),first)
 def test_invalid_metadata_preserves_installed_bundle(self):
  fixture=BUILD/'lv2/jerzy-test.lv2';files={'test.lv2/'+p.name:p.read_bytes() for p in fixture.iterdir()};path,checksum=self.bundle(files);self.library.install(path,checksum)
  original=(self.library.root/'test.lv2/manifest.ttl').read_bytes();files['test.lv2/manifest.ttl']=b'not turtle metadata';path,checksum=self.bundle(files)
  with self.assertRaisesRegex(ValueError,'Manifest'):self.library.install(path,checksum)
  self.assertEqual((self.library.root/'test.lv2/manifest.ttl').read_bytes(),original)
if __name__=='__main__':unittest.main()
