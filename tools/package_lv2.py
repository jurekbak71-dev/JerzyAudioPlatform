#!/usr/bin/env python3
"""Package the LV2 host only: no archived DSP modules or JUCE dependencies."""
import argparse,gzip,hashlib,json,os,platform,shutil,struct,subprocess,tarfile,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--arch',choices=['arm64','x86_64'],required=True);p.add_argument('--library-dir',type=Path);a=p.parse_args();a.build=a.build.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True);version=(ROOT/'VERSION').read_text().strip()
 machine=struct.unpack_from('<H',(a.build/'jerzy-audio-core').read_bytes(),18)[0]
 if machine!={'arm64':183,'x86_64':62}[a.arch]:raise ValueError('Wrong binary architecture')
 library=a.library_dir or Path('/usr/lib')/('aarch64-linux-gnu' if a.arch=='arm64' else 'x86_64-linux-gnu')
 with tempfile.TemporaryDirectory() as temporary:
  root=Path(temporary)/'JerzyAudioPlatform';(root/'bin').mkdir(parents=True);(root/'lib').mkdir()
  for name in ['jerzy-audio-core','jerzy-midi-bridge']:shutil.copy2(a.build/name,root/'bin'/name)
  for name in ['web-ui','module-manager','deploy','licenses']:shutil.copytree(ROOT/name,root/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
  for name in ['VERSION','LICENSE','README.md','CHANGELOG.md']:shutil.copy2(ROOT/name,root/name)
  (root/'docs').mkdir();shutil.copy2(ROOT/'docs/LV2_PL.md',root/'docs/LV2_PL.md')
  libraries=['liblilv-0.so.0','libserd-0.so.0','libsord-0.so.0','libsratom-0.so.0']
  if (library/'libzix-0.so.0').exists():libraries.append('libzix-0.so.0')
  for name in libraries:
   source=(library/name).resolve()
   if not source.is_file():raise ValueError('Missing runtime LV2 library: '+str(library/name))
   if struct.unpack_from('<H',source.read_bytes(),18)[0]!=machine:raise ValueError('Wrong library architecture: '+name)
   shutil.copy2(source,root/'lib'/name)
  # Redistribute dependency copyright/license notices beside the runtime libs.
  doc=library.parent.parent/'share/doc'
  for name in ['liblilv-0-0','libserd-0-0','libsord-0-0','libsratom-0-0','libzix-0-0']:
   if (doc/name/'copyright').is_file():shutil.copy2(doc/name/'copyright',root/'licenses'/(name+'-copyright.txt'))
  commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
  (root/'BUILD-METADATA.json').write_text(json.dumps({'version':version,'source_commit':commit,'architecture':a.arch,'plugin_format':'lv2','hardware_validated':False,'windows_installation_validated':False},indent=2)+'\n')
  (root/'FILES-SHA256.json').write_text(json.dumps({str(f.relative_to(root)):sha(f) for f in sorted(root.rglob('*')) if f.is_file()},indent=2)+'\n')
  archive=a.out/f'JerzyAudioPlatform-v{version}-{"RPi4-arm64" if a.arch=="arm64" else "Linux-x86_64"}.tar.gz'
  with archive.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as gz,tarfile.open(fileobj=gz,mode='w') as tar:
   for f in sorted(root.rglob('*')):
    if not f.is_file():continue
    info=tar.gettarinfo(str(f),arcname='JerzyAudioPlatform/'+str(f.relative_to(root)));info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0;info.mode=0o755 if f.parent==root/'bin' else 0o644
    with f.open('rb') as source:tar.addfile(info,source)
 sums={archive.name:sha(archive)}
 if a.arch=='arm64':
  windows=a.out/f'JerzyAudioPlatform-v{version}-Windows-Installer.zip'
  files=['START-INSTALACJA.cmd','Instaluj.ps1','AKTYWUJ.cmd','OTWORZ-PANEL.cmd','DIAGNOSTYKA.cmd','Diagnostyka.ps1','PRZYWROC-MULTIFX.cmd','Przywroc.ps1','WLACZ-AUTOSTART.cmd','Autostart.ps1','NAPRAW-I-AKTYWUJ.cmd','Napraw.ps1','START_TUTAJ.txt','WIFI-DOMOWE.cmd','Wifi.ps1']
  with zipfile.ZipFile(windows,'w',zipfile.ZIP_DEFLATED) as z:
   for name in files:z.write(ROOT/'deploy/windows'/name,name)
   z.write(ROOT/'deploy/raspberry-pi/recover_jack.sh','recover_jack.sh');z.write(ROOT/'deploy/network/wifi_home.py','wifi_home.py')
   z.write(archive,archive.name);z.writestr('SHA256.json',json.dumps(sums,indent=2)+'\n');z.write(ROOT/'docs/LV2_PL.md','LV2_PL.md')
  sums[windows.name]=sha(windows)
 shutil.copy2(ROOT/'docs/LV2_PL.md',a.out/'RELEASE-NOTES.md');sums['RELEASE-NOTES.md']=sha(a.out/'RELEASE-NOTES.md')
 (a.out/'SHA256.json').write_text(json.dumps(sums,indent=2)+'\n');(a.out/'SHA256SUMS.txt').write_text(''.join(v+'  '+k+'\n' for k,v in sums.items()))
 print(json.dumps(sums,indent=2))
if __name__=='__main__':main()
