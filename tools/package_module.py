#!/usr/bin/env python3
import argparse,hashlib,json,struct,zipfile,re,subprocess
from pathlib import Path
def package(manifest_path,library_path,output):
 manifest=json.loads(Path(manifest_path).read_text());data=Path(library_path).read_bytes()
 if data[:6]!=b'\x7fELF\x02\x01':raise ValueError('Wymagany moduł Linux ELF64')
 arch={183:'linux-arm64',62:'linux-x86_64'}.get(struct.unpack_from('<H',data,18)[0])
 if not arch:raise ValueError('Nieobsługiwana architektura')
 manifest['architecture']=arch
 versions=subprocess.check_output(['readelf','--version-info',str(library_path)],text=True)
 for family,field in [('GLIBC','minimum_glibc'),('GLIBCXX','minimum_glibcxx')]:
  found=re.findall(r'\b'+family+r'_(\d+(?:\.\d+)+)',versions)
  manifest[field]=max(found,key=lambda value:tuple(map(int,value.split('.')))) if found else None
 dynamic=subprocess.check_output(['readelf','-d',str(library_path)],text=True)
 manifest['runtime_libraries']=re.findall(r'\(NEEDED\).*\[(.*?)\]',dynamic)
 files={'manifest.json':(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode(),manifest['library']:data}
 files['SHA256.json']=json.dumps({n:hashlib.sha256(b).hexdigest() for n,b in files.items()},indent=2).encode()
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for name,raw in sorted(files.items()):
   info=zipfile.ZipInfo(name,(2026,10,24,0,0,0));info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw)
 return hashlib.sha256(output.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('library');p.add_argument('output');a=p.parse_args();print(package(a.manifest,a.library,a.output))
if __name__=='__main__':main()
