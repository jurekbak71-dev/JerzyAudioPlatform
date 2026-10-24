"""Local module packages. No network or executable code is used during inspection."""
import hashlib,json,os,platform,re,shutil,struct,tempfile,zipfile
from pathlib import Path
ID=re.compile(r'^[a-z][a-z0-9-]{0,63}$')
VERSION=re.compile(r'^\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?$')
def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.save-')
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def elf_arch(data):
 if len(data)<64 or data[:6]!=b'\x7fELF\x02\x01':raise ValueError('Wymagany moduł ELF64 little-endian')
 if struct.unpack_from('<H',data,16)[0]!=3:raise ValueError('Wymagana biblioteka współdzielona ELF')
 return {183:'aarch64',62:'x86_64'}.get(struct.unpack_from('<H',data,18)[0],'nieznana')
class Library:
 def __init__(self,root):
  self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
  # Recover interrupted directory renames without deleting either version.
  for temporary in self.root.glob('*.swapping'):
   id=temporary.name[:-len('.swapping')]
   if not ID.fullmatch(id):continue
   current=self.root/id;previous=self.root/(id+'.previous')
   if not current.exists():os.replace(temporary,current)
   elif not previous.exists():os.replace(temporary,previous)
   else:raise ValueError('Niejednoznaczne przerwane przełączenie modułu: '+id)
  for previous in self.root.glob('*.previous'):
   id=previous.name[:-len('.previous')]
   if ID.fullmatch(id) and not (self.root/id).exists():os.replace(previous,self.root/id)
 def list(self):
  result=[]
  for p in sorted(self.root.glob('*/manifest.json')):
   if not ID.fullmatch(p.parent.name):continue
   item=json.loads(p.read_text())
   if p.parent.name!=item.get('id') or not ID.fullmatch(item['id']):continue
   item['path']=str(p.parent/item['library']);item['previous']=(self.root/(item['id']+'.previous')).exists();result.append(item)
  return result
 def install(self,package,expected_sha256):
  if not re.fullmatch('[a-fA-F0-9]{64}',expected_sha256):raise ValueError('Podaj SHA256 z zaufanego źródła')
  package=Path(package)
  if package.stat().st_size>64*1024*1024:raise ValueError('Paczka przekracza 64 MB')
  if hashlib.sha256(package.read_bytes()).hexdigest()!=expected_sha256.lower():raise ValueError('Niezgodna suma SHA256 paczki')
  with zipfile.ZipFile(package) as z:
   names=z.namelist()
   if len(names)!=len(set(names)) or len(names)>64:raise ValueError('Powielone pliki lub zbyt duża paczka')
   if any('/' in n or '\\' in n or n in ('.','..') for n in names):raise ValueError('Niedozwolona ścieżka w paczce')
   if sum(x.file_size for x in z.infolist())>128*1024*1024:raise ValueError('Rozpakowana paczka przekracza 128 MB')
   manifest=json.loads(z.read('manifest.json'));checks=json.loads(z.read('SHA256.json'))
   id=manifest.get('id','');version=manifest.get('version','');lib=manifest.get('library','')
   if not ID.fullmatch(id) or not VERSION.fullmatch(version) or lib!=id+'.so' or manifest.get('abi')!=1:raise ValueError('Nieprawidłowy manifest lub ABI')
   if set(names)!={'manifest.json','SHA256.json',lib} or set(checks)!={'manifest.json',lib}:raise ValueError('Niekompletna paczka')
   data={n:z.read(n) for n in checks}
   for n,value in data.items():
    if hashlib.sha256(value).hexdigest()!=checks[n]:raise ValueError('Uszkodzony plik: '+n)
   if elf_arch(data[lib])!=platform.machine():raise ValueError('Paczka dla innej architektury')
   required=manifest.get('minimum_glibc')
   family,current=platform.libc_ver()
   if required:
    if not re.fullmatch(r'\d+(?:\.\d+)+',required):raise ValueError('Niepoprawne wymagania glibc')
    if family!='glibc' or tuple(map(int,current.split('.')))<tuple(map(int,required.split('.'))):raise ValueError('Moduł wymaga nowszej glibc: '+required)
   stage=Path(tempfile.mkdtemp(dir=self.root,prefix='.stage-'));target=self.root/id;previous=self.root/(id+'.previous')
   try:
    for n,value in data.items():(stage/n).write_bytes(value)
    if previous.exists():shutil.rmtree(previous)
    if target.exists():os.replace(target,previous)
    try:os.replace(stage,target)
    except BaseException:
     if previous.exists() and not target.exists():os.replace(previous,target)
     raise
   finally:
    if stage.exists():shutil.rmtree(stage)
   return manifest
 def rollback(self,id):
  if not ID.fullmatch(id):raise ValueError('Nieprawidłowe ID')
  current=self.root/id;previous=self.root/(id+'.previous');temp=self.root/(id+'.swapping')
  if not previous.exists():raise ValueError('Brak poprzedniej wersji')
  if temp.exists():raise ValueError('Poprzednie przełączenie wymaga sprawdzenia')
  os.replace(current,temp)
  try:os.replace(previous,current);os.replace(temp,previous)
  except BaseException:
   if not current.exists():os.replace(temp,current)
   raise
 def remove(self,id):
  if not ID.fullmatch(id):raise ValueError('Nieprawidłowe ID')
  p=self.root/id
  if not p.is_dir():raise ValueError('Moduł nie jest zainstalowany')
  shutil.rmtree(p)
  previous=self.root/(id+'.previous')
  if previous.exists():shutil.rmtree(previous)
