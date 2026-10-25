#!/usr/bin/env python3
"""Install immutable root-owned broker code; never run mutable user code as a daemon."""
import re,argparse,hashlib,json,os,pwd,shutil,subprocess,time,uuid
from pathlib import Path

def run(*args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout.strip()
def install(release,uid):
 if os.geteuid()!=0 or uid<=0:raise RuntimeError('Wymagana instalacja przez sudo dla użytkownika audio')
 if int(os.environ.get('SUDO_UID',uid))!=uid:raise RuntimeError('Niepoprawny właściciel platformy')
 user=pwd.getpwuid(uid);release=release.resolve();base=Path(user.pw_dir)/'.local/share/jerzy-audio-platform/releases'
 if not release.is_relative_to(base):raise RuntimeError('Wymagana przygotowana paczka w katalogu releases')
 manifest=json.loads((release/'FILES-SHA256.json').read_text());source=release/'deploy/connectivity'
 for file in source.rglob('*'):
  if file.is_symlink():raise RuntimeError('Niedozwolony symlink w usłudze sprzętowej')
  if '__pycache__' in file.parts or file.suffix in ('.pyc','.pyo') or not file.is_file():continue
  name=str(file.relative_to(release))
  if file.is_symlink() or name not in manifest or hashlib.sha256(file.read_bytes()).hexdigest()!=manifest[name]:raise RuntimeError('Niezgodne pliki usługi sprzętowej: '+name)
 if not shutil.which('bluetoothctl'):
  # Existing audio continues during dependency installation; never pretend an
  # offline missing package is installed.
  run('apt-get','update');run('apt-get','install','--yes','--no-install-recommends','bluez')
 if not shutil.which('nmcli'):raise RuntimeError('Brak NetworkManager/nmcli; nie zmieniono sieci')
 state=Path('/var/lib/jerzy-audio-platform');state.mkdir(parents=True,exist_ok=True,mode=0o700);config=state/'config.json'
 checkpoint=state/'audio-transaction.json'
 if checkpoint.exists() and json.loads(checkpoint.read_text()).get('phase')=='pending':raise RuntimeError('Trwa transakcja audio. Zaczekaj na zakończenie lub przywracanie przed aktualizacją.')
 values=json.loads(config.read_text()) if config.exists() else {'uid':uid}
 if values['uid']!=uid:raise RuntimeError('Usługa sprzętowa jest już przypisana do innego użytkownika')
 config.write_text(json.dumps(values));config.chmod(0o600)
 version=json.loads((release/'BUILD-METADATA.json').read_text())['source_commit']
 if not isinstance(version,str) or not re.fullmatch('[a-f0-9]{40}',version):raise RuntimeError('Niepoprawny identyfikator źródeł paczki')
 target=Path('/usr/local/lib/jerzy-audio-platform-hardware')/(version+'-'+uuid.uuid4().hex[:8])
 shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 for file in [target,*target.rglob('*')]:
  file.chmod(0o755 if file.is_dir() else 0o644);os.chown(file,0,0)
 Path('/etc/systemd/system/jerzy-jack.service.d').mkdir(parents=True,exist_ok=True)
 unit=Path('/etc/systemd/system/jerzy-audio-hardware.service')
 unit.write_text('[Unit]\nDescription=Jerzy Audio hardware and Bluetooth broker\nAfter=dbus.service NetworkManager.service bluetooth.service\nWants=dbus.service NetworkManager.service bluetooth.service\n\n[Service]\nType=simple\nExecStart=/usr/bin/python3 '+str(target/'service.py')+'\nEnvironment=PYTHONDONTWRITEBYTECODE=1\nRestart=on-failure\nRestartSec=2\nRuntimeDirectory=jerzy-audio-platform\nRuntimeDirectoryMode=0755\nTimeoutStopSec=5\nNoNewPrivileges=yes\nProtectSystem=strict\nProtectHome=read-only\nPrivateTmp=yes\nReadWritePaths=/var/lib/jerzy-audio-platform /run/jerzy-audio-platform /etc/systemd/system/jerzy-jack.service.d /run/user/'+str(uid)+'\n\n[Install]\nWantedBy=multi-user.target\n');unit.chmod(0o644)
 run('systemctl','daemon-reload');run('systemctl','enable','jerzy-audio-hardware.service');run('systemctl','restart','jerzy-audio-hardware.service')
 end=time.monotonic()+8
 while time.monotonic()<end:
  status=Path('/run/jerzy-audio-platform/status.json')
  if status.exists() and json.loads(status.read_text()).get('uid')==uid and json.loads(status.read_text()).get('pid')==int(run('systemctl','show','jerzy-audio-hardware.service','--property=MainPID','--value')):print('Usługa sprzętowa i Bluetooth zainstalowana. Parowanie jest dostępne w panelu.');return
  time.sleep(.2)
 raise RuntimeError('Usługa sprzętowa nie potwierdziła gotowości; sprawdź journalctl -u jerzy-audio-hardware.service')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--release',type=Path,required=True);p.add_argument('--uid',type=int,required=True);args=p.parse_args();install(args.release,args.uid)
