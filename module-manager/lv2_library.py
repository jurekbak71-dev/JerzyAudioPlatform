"""LV2 metadata discovery and atomic installation of trusted native LV2 bundles."""
import hashlib,json,os,platform,shutil,stat,subprocess,tempfile,time,urllib.parse,zipfile
from pathlib import Path
from manager import elf_arch
class LV2Library:
 def __init__(self,core,root=None):
  self.core=str(core);self.root=Path(root or Path.home()/'.lv2').resolve();self.root.mkdir(parents=True,exist_ok=True);self.cache=None;self.updated=0;self.last_error=None
 def list(self,refresh=False):
  if self.cache is None or refresh or time.monotonic()-self.updated>30:
   try:
    process=subprocess.run([self.core,'--list-lv2'],capture_output=True,text=True,timeout=30,check=True,env={**os.environ,'JERZY_LV2_PATH':str(self.root),'LD_LIBRARY_PATH':str(Path(self.core).parent.parent/'lib')+':'+os.environ.get('LD_LIBRARY_PATH','')})
    self.cache=json.loads(process.stdout)['plugins'];self.updated=time.monotonic();self.last_error=None
    for entry in self.cache:
     path=Path(urllib.parse.unquote(urllib.parse.urlsplit(entry['bundle']).path)).resolve();entry['managed']=path.parent==self.root;entry['previous']=entry['managed'] and path.with_name(path.name+'.previous').is_dir()
   except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
    self.last_error='Nie odświeżono biblioteki LV2: '+str(error);self.updated=time.monotonic()
    if self.cache is None:self.cache=[]
  return self.cache
 def install(self,package,expected_sha256):
  import re
  if not re.fullmatch('[a-fA-F0-9]{64}',expected_sha256):raise ValueError('Podaj SHA256 paczki LV2')
  package=Path(package)
  if package.stat().st_size>64*1024*1024:raise ValueError('Paczka LV2 przekracza 64 MB')
  with package.open('rb') as f:
   if hashlib.file_digest(f,'sha256').hexdigest()!=expected_sha256.lower():raise ValueError('Niezgodna suma SHA256 paczki LV2')
  with zipfile.ZipFile(package) as archive:
   entries=archive.infolist();names=[e.filename for e in entries]
   if len(names)!=len(set(names)) or len(names)>2048 or sum(e.file_size for e in entries)>128*1024*1024:raise ValueError('Niepoprawny lub zbyt duży ZIP LV2')
   roots=set()
   for entry in entries:
    path=Path(entry.filename)
    if path.is_absolute() or '\\' in entry.filename or '..' in path.parts or not path.parts or stat.S_ISLNK(entry.external_attr>>16):raise ValueError('Niedozwolona ścieżka lub symlink w ZIP LV2')
    roots.add(path.parts[0])
   if len(roots)!=1 or not next(iter(roots)).endswith('.lv2') or next(iter(roots)).startswith('.'):raise ValueError('ZIP musi zawierać jeden katalog nazwa.lv2')
   name=next(iter(roots));stage=Path(tempfile.mkdtemp(dir=self.root,prefix='.stage-'))
   try:
    for entry in entries:
     path=stage/entry.filename
     if entry.is_dir():path.mkdir(parents=True,exist_ok=True);continue
     path.parent.mkdir(parents=True,exist_ok=True)
     with archive.open(entry) as source,path.open('wb') as target:shutil.copyfileobj(source,target)
     if path.suffix=='.so':
      with path.open('rb') as binary:arch=elf_arch(binary.read(64))
      if arch!=platform.machine():raise ValueError('Wtyczka LV2 jest dla innej architektury niż '+platform.machine())
    incoming=stage/name
    if not (incoming/'manifest.ttl').is_file() or not any(incoming.rglob('*.so')):raise ValueError('Brak manifest.ttl lub biblioteki Linux .so')
    discovery=subprocess.run([self.core,'--list-lv2'],capture_output=True,text=True,timeout=30,check=True,env={**os.environ,'LV2_PATH':str(stage),'JERZY_LV2_PATH':str(stage)})
    if not json.loads(discovery.stdout)['plugins']:raise ValueError('Manifest LV2 nie zawiera poprawnej wtyczki')
    target=self.root/name;previous=self.root/(name+'.previous')
    if previous.exists():shutil.rmtree(previous)
    if target.exists():os.replace(target,previous)
    try:os.replace(incoming,target)
    except BaseException:
     if previous.exists() and not target.exists():os.replace(previous,target)
     raise
   finally:shutil.rmtree(stage)
  self.cache=None;return {'id':name}
 def _bundle(self,id):
  entry=next((p for p in self.list() if p['id']==id),None)
  if not entry:raise ValueError('Nie znaleziono wtyczki LV2')
  bundle=Path(urllib.parse.unquote(urllib.parse.urlsplit(entry['bundle']).path)).resolve()
  if bundle.parent!=self.root or not bundle.name.endswith('.lv2'):raise ValueError('Wtyczki systemowe usuwa się przez menedżer pakietów systemu')
  return bundle
 def remove(self,id):shutil.rmtree(self._bundle(id));self.cache=None
 def rollback(self,id):
  target=self._bundle(id);previous=target.with_name(target.name+'.previous')
  if not previous.is_dir():raise ValueError('Brak poprzedniej wersji LV2')
  parked=target.with_name('.swap-'+target.name);os.replace(target,parked)
  try:os.replace(previous,target);os.replace(parked,previous)
  except BaseException:
   if not target.exists():os.replace(parked,target)
   raise
  self.cache=None
