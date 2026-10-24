import hashlib,importlib.util,json,os,platform,shutil,sys,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'module-manager'));sys.path.insert(0,str(ROOT/'tools'))
from manager import Library
from package_module import package
BUILD=Path(os.environ.get('JERZY_TEST_BUILD','/workspace/shared/build-platform'))
class Packages(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.tmp=Path(self.temp.name);self.library=Library(self.tmp/'library');self.manifest=json.loads((ROOT/'modules/utility-gain-meter/manifest.json').read_text());self.source=BUILD/'modules/utility-gain-meter/utility-gain-meter.so'
 def tearDown(self):self.temp.cleanup()
 def make(self,version='0.1.0'):
  self.manifest['version']=version;manifest=self.tmp/'manifest.json';manifest.write_text(json.dumps(self.manifest));out=self.tmp/(version+'.jamod');checksum=package(manifest,self.source,out);return out,checksum
 def test_install_update_rollback_remove(self):
  file,sum=self.make();self.library.install(file,sum);self.assertEqual(self.library.list()[0]['version'],'0.1.0')
  file,sum=self.make('0.2.0');self.library.install(file,sum);self.assertEqual(self.library.list()[0]['version'],'0.2.0')
  self.library.rollback('utility-gain-meter');self.assertEqual(self.library.list()[0]['version'],'0.1.0');self.library.remove('utility-gain-meter');self.assertEqual(self.library.list(),[])
 def test_interrupted_install_preserves_previous_version(self):
  file,sum=self.make();self.library.install(file,sum)
  os.replace(self.library.root/'utility-gain-meter',self.library.root/'utility-gain-meter.previous')
  recovered=Library(self.library.root);self.assertEqual(recovered.list()[0]['version'],'0.1.0')
 def test_interrupted_rollback_recovers_without_losing_a_version(self):
  file,sum=self.make();self.library.install(file,sum);file,sum=self.make('0.2.0');self.library.install(file,sum)
  os.replace(self.library.root/'utility-gain-meter',self.library.root/'utility-gain-meter.swapping')
  recovered=Library(self.library.root);self.assertEqual(recovered.list()[0]['version'],'0.2.0');recovered.rollback('utility-gain-meter');self.assertEqual(recovered.list()[0]['version'],'0.1.0')
 def test_verified_original_package_import(self):
  self.manifest=json.loads((ROOT/'modules/tape-drive-original/manifest.json').read_text());self.source=BUILD/'modules/tape-drive-original/tape-drive-original.so'
  file,sum=self.make('0.2.0');self.library.install(file,sum);entry=self.library.list()[0];self.assertTrue(entry['compatibility']['passed']);self.assertFalse(entry['compatibility']['hardware_validated'])
 def test_original_without_report_is_rejected(self):
  self.manifest['id']='uncertified-original';self.manifest['library']='uncertified-original.so';file,sum=self.make('0.2.0')
  with self.assertRaisesRegex(ValueError,'Brak raportu'):self.library.install(file,sum)
 def test_wrong_checksum_does_not_change_installation(self):
  file,sum=self.make();self.library.install(file,sum)
  with self.assertRaises(ValueError):self.library.install(file,'0'*64)
  self.assertEqual(self.library.list()[0]['version'],'0.1.0')
 def test_zip_path_traversal_is_rejected(self):
  file=self.tmp/'bad.jamod'
  with zipfile.ZipFile(file,'w') as z:z.writestr('../escaped',b'bad')
  with self.assertRaises(ValueError):self.library.install(file,hashlib.sha256(file.read_bytes()).hexdigest())
  self.assertFalse((self.tmp/'escaped').exists());self.assertEqual(self.library.list(),[])
 def test_corrupted_internal_payload_is_rejected(self):
  file,sum=self.make();bad=self.tmp/'bad.jamod'
  with zipfile.ZipFile(file) as source,zipfile.ZipFile(bad,'w') as dest:
   for name in source.namelist():dest.writestr(name,b'bad ELF' if name.endswith('.so') else source.read(name))
  with self.assertRaises(ValueError):self.library.install(bad,hashlib.sha256(bad.read_bytes()).hexdigest())
  self.assertEqual(self.library.list(),[])
 def test_incompatible_abi_is_rejected(self):
  self.manifest['abi']=999;file,sum=self.make()
  with self.assertRaises(ValueError):self.library.install(file,sum)
 def test_duplicate_zip_entry_is_rejected(self):
  import warnings
  file=self.tmp/'bad.jamod'
  with warnings.catch_warnings():
   warnings.simplefilter('ignore')
   with zipfile.ZipFile(file,'w') as z:z.writestr('manifest.json','{}');z.writestr('manifest.json','{}')
  with self.assertRaises(ValueError):self.library.install(file,hashlib.sha256(file.read_bytes()).hexdigest())
if __name__=='__main__':unittest.main()
