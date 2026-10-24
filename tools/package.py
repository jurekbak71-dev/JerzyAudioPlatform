#!/usr/bin/env python3
"""Package tested ELF files, certificates and offline Windows tools."""
import argparse,datetime,gzip,hashlib,json,os,shutil,struct,subprocess,tarfile,tempfile,zipfile
from pathlib import Path
from package_module import package
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def archive_zip(path,files):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for name,data in sorted(files.items()):
   info=zipfile.ZipInfo(name,(2026,10,24,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
def source_juce(build,out):
 cache=(build/'CMakeCache.txt').read_text();prefix='JERZY_JUCE_ROOT:PATH='
 entry=next((line[len(prefix):] for line in cache.splitlines() if line.startswith(prefix)),'')
 root=Path(entry) if entry else build/'_deps/juce_original-src'
 if not (root/'modules/juce_dsp/juce_dsp.h').is_file():raise RuntimeError('Nie odnaleziono źródeł JUCE potrzebnych do dystrybucji modułu GPL')
 with tarfile.open(out,'w:gz') as tar:
  for path in sorted(root.rglob('*')):
   relative=path.relative_to(root)
   if '.git' in relative.parts or path.is_dir():continue
   tar.add(path,arcname='JUCE-7.0.12/'+str(relative),recursive=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--arch',choices=['arm64','x86_64'],required=True);a=p.parse_args();a.build=a.build.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
 machine=struct.unpack_from('<H',(a.build/'jerzy-audio-core').read_bytes(),18)[0]
 if machine!={'arm64':183,'x86_64':62}[a.arch]:raise ValueError('Binarium nie odpowiada zadeklarowanej architekturze')
 dirs=[d for d in sorted((ROOT/'modules').iterdir()) if (d/'manifest.json').is_file()]
 modules=[d for d in dirs if d.name.endswith('-original') or d.name in ('utility-gain-meter','cab-ir')]
 sums={};module_files={};catalog={}
 notes=a.out/'RELEASE-NOTES.md';shutil.copy2(ROOT/'docs/NAPRAWY_0.2.1_PL.md',notes);sums[notes.name]=digest(notes)
 for d in modules:
  m=json.loads((d/'manifest.json').read_text());name=f'{d.name}-{m["version"]}-linux-{a.arch}.jamod';path=a.out/name
  if d.name.endswith('-original') and not (a.build/'compatibility'/(d.name+'.json')).is_file():raise RuntimeError('Brak ukończonych testów zgodności: '+d.name)
  sums[name]=package(d/'manifest.json',a.build/'modules'/d.name/(d.name+'.so'),path);module_files[name]=path.read_bytes()
  if d.name.endswith('-original') and d.name!='bass-ambient-original':catalog[name]={'sha256':sums[name],'module':d.name,'version':m['version'],'reference_commit':m['source']['commit']}
 catalog_data=(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode()
 (a.out/'MODULE-CATALOG.json').write_bytes(catalog_data)
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp)/'JerzyAudioPlatform';root.mkdir();(root/'bin').mkdir();(root/'tests').mkdir()
  for name in ['VERSION','LICENSE']:shutil.copy2(ROOT/name,root/name)
  for binary in a.build.glob('compare-*'):
   if binary.is_file() and binary.suffix=='':shutil.copy2(binary,root/'tests'/binary.name)
  shutil.copy2(a.build/'module-health',root/'tests/module-health')
  shutil.copy2(a.build/'jerzy-audio-core',root/'bin/jerzy-audio-core');shutil.copy2(a.build/'module-tests',root/'tests/module-tests')
  # Legacy algorithms are kept only as test fixtures, not offered as new FX.
  legacy=root/'tests/legacy-modules'
  for d in dirs:
   if d.name.endswith('-original'):continue
   target=legacy/d.name;target.mkdir(parents=True);shutil.copy2(a.build/'modules'/d.name/(d.name+'.so'),target/(d.name+'.so'))
  for name in ['web-ui','module-manager','deploy','module-sdk','licenses']:
   shutil.copytree(ROOT/name,root/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
  for d in modules:
   target=root/'modules'/d.name;target.mkdir(parents=True);m=json.loads((d/'manifest.json').read_text())
   with zipfile.ZipFile(a.out/f'{d.name}-{m["version"]}-linux-{a.arch}.jamod') as source:
    for name in source.namelist():(target/name).write_bytes(source.read(name))
  for name in ['README.md','CHANGELOG.md','docs/INSTRUKCJA_PL.html','docs/MODULY_I_WIFI_PL.html','docs/ORYGINALNE_DSP_0.2.md','docs/NAPRAWY_0.2.1_PL.md','docs/AUDYT.md','docs/TESTY_SPRZETOWE.md','docs/OGRANICZENIA.md','docs/RAPORT_TESTOW.md']:
   target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
  try:commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
  except (subprocess.CalledProcessError,FileNotFoundError):commit=os.environ.get('GITHUB_SHA')
  (root/'BUILD-METADATA.json').write_text(json.dumps({'version':VERSION,'status':'development','source_commit':commit,'architecture':a.arch,'hardware_validated':False,'windows_installation_validated':False,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
  checks={str(f.relative_to(root)):digest(f) for f in sorted(root.rglob('*')) if f.is_file()};(root/'FILES-SHA256.json').write_text(json.dumps(checks,indent=2)+'\n')
  name=f'JerzyAudioPlatform-v{VERSION}-{"RPi4-arm64" if a.arch=="arm64" else "Linux-x86_64"}.tar.gz';archive=a.out/name
  with archive.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as gz,tarfile.open(fileobj=gz,mode='w') as tar:
   for file in sorted(root.rglob('*')):
    if not file.is_file():continue
    info=tar.gettarinfo(str(file),arcname='JerzyAudioPlatform/'+str(file.relative_to(root)));info.mtime=0;info.uid=info.gid=0;info.uname=info.gname='';info.mode=0o755 if file.parent==root/'bin' or (file.parent==root/'tests' and file.suffix=='') else 0o644
    with file.open('rb') as stream:tar.addfile(info,stream)
  sums[name]=digest(archive)
 if a.arch=='arm64':
  tool_files={f.name:f.read_bytes() for f in (ROOT/'deploy/windows').iterdir() if f.is_file()}
  tool_files.update({'wifi_home.py':(ROOT/'deploy/network/wifi_home.py').read_bytes(),'recover_jack.sh':(ROOT/'deploy/raspberry-pi/recover_jack.sh').read_bytes(),'install_module.py':(ROOT/'deploy/raspberry-pi/install_module.py').read_bytes(),'MODULE-CATALOG.json':catalog_data,'MODULY_I_WIFI_PL.html':(ROOT/'docs/MODULY_I_WIFI_PL.html').read_bytes(),'LICENSE.txt':(ROOT/'LICENSE').read_bytes(),'NAPRAWY_0.2.1_PL.md':(ROOT/'docs/NAPRAWY_0.2.1_PL.md').read_bytes()})
  full={**tool_files,archive.name:archive.read_bytes(),'SHA256.json':(json.dumps(sums,indent=2)+'\n').encode(),'INSTRUKCJA_PL.html':(ROOT/'docs/INSTRUKCJA_PL.html').read_bytes()}
  for name,data in module_files.items():full['moduly/'+name]=data
  name=f'JerzyAudioPlatform-v{VERSION}-Windows-Installer.zip';archive_zip(a.out/name,full);sums[name]=digest(a.out/name)
  wifi={name:tool_files[name] for name in ['WIFI-DOMOWE.cmd','Wifi.ps1','wifi_home.py','MODULY_I_WIFI_PL.html','LICENSE.txt']}
  name='Jerzy-WiFi-Domowe.zip';archive_zip(a.out/name,wifi);sums[name]=digest(a.out/name)
  bundle={name:tool_files[name] for name in ['INSTALUJ-MODUL.cmd','Moduly.ps1','install_module.py','MODULE-CATALOG.json','MODULY_I_WIFI_PL.html','LICENSE.txt']}
  for name,data in module_files.items():
   if name in catalog:bundle['moduly/'+name]=data
  name=f'Jerzy-Oryginalne-Moduly-v{VERSION}-ARM64.zip';archive_zip(a.out/name,bundle);sums[name]=digest(a.out/name)
  name='JUCE-7.0.12-Source.tar.gz';source_juce(a.build,a.out/name);sums[name]=digest(a.out/name)
 (a.out/'SHA256.json').write_text(json.dumps(sums,indent=2)+'\n');(a.out/'SHA256SUMS.txt').write_text(''.join(value+'  '+name+'\n' for name,value in sorted(sums.items())))
 print(json.dumps(sums,indent=2))
if __name__=='__main__':main()
