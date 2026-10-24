#!/usr/bin/env python3
"""Package only actual compiled ELF files. Refuses to mislabel an architecture."""
import argparse,gzip,hashlib,json,shutil,struct,tarfile,tempfile,zipfile,subprocess,datetime,os
from pathlib import Path
from package_module import package
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--arch',choices=['arm64','x86_64'],required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 machine=struct.unpack_from('<H',(a.build/'jerzy-audio-core').read_bytes(),18)[0]
 if machine!={'arm64':183,'x86_64':62}[a.arch]:raise ValueError('Binarium nie odpowiada zadeklarowanej architekturze')
 sums={}
 for d in sorted((ROOT/'modules').iterdir()):
  if not (d/'manifest.json').exists():continue
  name=f'{d.name}-0.1.0-linux-{a.arch}.jamod';sums[name]=package(d/'manifest.json',a.build/'modules'/d.name/(d.name+'.so'),a.out/name)
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp)/'JerzyAudioPlatform';root.mkdir();(root/'bin').mkdir();(root/'tests').mkdir()
  shutil.copy2(a.build/'jerzy-audio-core',root/'bin/jerzy-audio-core');shutil.copy2(a.build/'module-tests',root/'tests/module-tests')
  for name in ['web-ui','module-manager','deploy','module-sdk']:
   shutil.copytree(ROOT/name,root/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
  for d in sorted((ROOT/'modules').iterdir()):
   if not (d/'manifest.json').exists():continue
   target=root/'modules'/d.name;target.mkdir(parents=True);shutil.copy2(d/'manifest.json',target/'manifest.json');shutil.copy2(a.build/'modules'/d.name/(d.name+'.so'),target/(d.name+'.so'))
  for name in ['README.md','CHANGELOG.md','docs/INSTRUKCJA_PL.html','docs/AUDYT.md','docs/TESTY_SPRZETOWE.md','docs/OGRANICZENIA.md','docs/RAPORT_TESTOW.md','docs/POMIARY_DSP.json','docs/BUILD-TESTS.log','docs/PACKAGE-TESTS.log','docs/DSP-TESTS.log','docs/INTEGRATION-TESTS.log','docs/POWERSHELL-PARSER.log']:
   target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
  try:commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
  except (subprocess.CalledProcessError,FileNotFoundError):commit=os.environ.get('GITHUB_SHA')
  (root/'BUILD-METADATA.json').write_text(json.dumps({'version':'0.1.0','status':'development','source_commit':commit,'architecture':a.arch,'hardware_validated':False,'windows_installation_validated':False,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
  files={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(root.rglob('*')) if f.is_file()}
  (root/'FILES-SHA256.json').write_text(json.dumps(files,indent=2)+'\n')
  name=f'JerzyAudioPlatform-v0.1.0-{"RPi4-arm64" if a.arch=="arm64" else "Linux-x86_64"}.tar.gz'
  archive=a.out/name
  with archive.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as gz,tarfile.open(fileobj=gz,mode='w') as tar:
   for f in sorted(root.rglob('*')):
    if f.is_dir():continue
    info=tar.gettarinfo(str(f),arcname='JerzyAudioPlatform/'+str(f.relative_to(root)));info.mtime=0;info.uid=info.gid=0;info.uname=info.gname='';info.mode=0o755 if f.name in ['jerzy-audio-core','module-tests'] else 0o644
    with f.open('rb') as src:tar.addfile(info,src)
  sums[name]=hashlib.sha256(archive.read_bytes()).hexdigest()
 if a.arch=='arm64':
  name='JerzyAudioPlatform-v0.1.0-Windows-Installer.zip'
  with zipfile.ZipFile(a.out/name,'w',zipfile.ZIP_DEFLATED) as z:
   def write(name,data):
    info=zipfile.ZipInfo(name,(2026,10,24,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
   for f in sorted((ROOT/'deploy/windows').iterdir()):write(f.name,f.read_bytes())
   write('recover_jack.sh',(ROOT/'deploy/raspberry-pi/recover_jack.sh').read_bytes())
   write('INSTRUKCJA_PL.html',(ROOT/'docs/INSTRUKCJA_PL.html').read_bytes())
   write('RAPORT_TESTOW.md',(ROOT/'docs/RAPORT_TESTOW.md').read_bytes())
   write(archive.name,archive.read_bytes());write('SHA256.json',(json.dumps(sums,indent=2)+'\n').encode())
   for n in sums:
    if n.endswith('.jamod'):write('moduly/'+n,(a.out/n).read_bytes())
  sums[name]=hashlib.sha256((a.out/name).read_bytes()).hexdigest()
 (a.out/'SHA256.json').write_text(json.dumps(sums,indent=2)+'\n')
 (a.out/'SHA256SUMS.txt').write_text(''.join(f'{value}  {name}\n' for name,value in sorted(sums.items())))
 print(json.dumps(sums,indent=2))
if __name__=='__main__':main()
