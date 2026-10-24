#!/usr/bin/env python3
"""Explicit activation and rollback. Uses user units; never enables or stops JACK/network."""
import argparse,json,os,shutil,socket,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'module-manager'))
from manager import atomic_json
from jack_graph import Jack
BASE=Path.home()/'.local/share/jerzy-audio-platform'
UNITS=['jerzy-audio-platform-core.service','jerzy-audio-platform-web.service']
# Conservative list from audited deployments. Only active user units are stopped.
OLD=[base+suffix+'.service' for base in ['jerzy-multifx','jerzy-multifx2','jerzy-multifx3','jerzy-multifx4'] for suffix in ['', '-panel','-routing','-midi']]
def manage(record,action):
 prefix=['sudo','-n','systemctl'] if record['scope']=='system' else ['systemctl','--user']
 subprocess.run(prefix+[action,record['unit']],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
def stale_socket():
 path=BASE/'core.sock'
 if not path.exists():return
 import stat
 if not stat.S_ISSOCK(path.stat().st_mode):raise RuntimeError('Ścieżka sterowania nie jest gniazdem; nie usunięto jej')
 with socket.socket(socket.AF_UNIX) as connection:
  try:connection.connect(str(path))
  except ConnectionRefusedError:path.unlink();return
 raise RuntimeError('Pod gniazdem działa inny silnik; przerwano operację')

def systemctl(*args,check=True):return subprocess.run(['systemctl','--user',*args],check=check,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
def core(command):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(5);s.connect(str(BASE/'core.sock'));s.sendall((command+'\n').encode());raw=b''
  while not raw.endswith(b'\n'):raw+=s.recv(65536)
  value=json.loads(raw)
  if not value.get('ok'):raise RuntimeError(value.get('error','Błąd silnika'))
  return value
def ready():
 end=time.monotonic()+20
 while time.monotonic()<end:
  try:
   import urllib.request
   state=json.load(urllib.request.urlopen('http://127.0.0.1:8093/api/state',timeout=2))
   if state['blocks']>2 and not state['restart_required']:return state
  except (OSError,ValueError,KeyError):time.sleep(.2)
 raise RuntimeError('Nowa platforma nie potwierdziła gotowości')
def quote(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'
def units(release):
 directory=Path.home()/'.config/systemd/user';directory.mkdir(parents=True,exist_ok=True)
 commands=[quote(release/'bin/jerzy-audio-core')+' '+quote(BASE/'core.sock'),'/usr/bin/python3 '+quote(release/'web-ui/server.py')+' --host 0.0.0.0 --port 8093 --socket '+quote(BASE/'core.sock')+' --modules '+quote(BASE/'modules')+' --data '+quote(BASE)+' --restore --audio-helper '+quote(release/'deploy/raspberry-pi/control.py')]
 for index,name in enumerate(UNITS):
  path=directory/name
  if path.exists() and not (BASE/(name+'.previous')).exists():shutil.copy2(path,BASE/(name+'.previous'))
  path.write_text('[Unit]\nDescription=Jerzy Audio Platform\n'+('After='+UNITS[0]+'\nWants='+UNITS[0]+'\n' if index else '')+'\n[Service]\nType=simple\nExecStart='+commands[index]+'\nRestart=no\n\n[Install]\nWantedBy=default.target\n')
 systemctl('daemon-reload')
def rollback():
 state=json.loads((BASE/'rollback.json').read_text())
 for unit in reversed(UNITS):systemctl('stop',unit,check=False)
 stale_socket()
 for unit in UNITS:
  backup=BASE/(unit+'.previous');target=Path.home()/'.config/systemd/user'/unit
  if backup.exists():shutil.copy2(backup,target)
 systemctl('daemon-reload')
 for record in state['services']:manage(record,'start')
 jack=Jack()
 try:
  end=time.monotonic()+15
  while time.monotonic()<end:
   available=set(jack.ports())
   if all(a in available and b in available for a,b in state['connections']):break
   time.sleep(.2)
  jack.restore(state['connections'])
  missing=[pair for pair in state['connections'] if pair[0] not in set(jack.ports()) or pair[1] not in set(jack.ports())]
  if missing:raise RuntimeError('Nie odtworzono portów poprzedniego systemu: '+str(missing))
 finally:jack.close()
 print('Przywrócono poprzednie usługi i dostępny routing. Sieć i presety bez zmian.')
def activate():
 release=Path((BASE/'staged').read_text().strip()).resolve()
 if not release.is_relative_to(BASE/'releases') or not (release/'bin/jerzy-audio-core').is_file():raise RuntimeError('Nieprawidłowa paczka staging')
 # Inspect both system and user scopes before changing any service.
 previous=[]
 for unit in OLD+UNITS:
  for scope,command in [('system',['systemctl']),('user',['systemctl','--user'])]:
   if subprocess.run(command+['is-active','--quiet',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:previous.append({'scope':scope,'unit':unit})
 if any(r['scope']=='system' for r in previous):
  subprocess.run(['sudo','-n','true'],check=True)
 systemctl('show-environment')
 jack=Jack()
 try:
  physical_in=jack.strings(jack.lib.jack_get_ports(jack.client,None,b'32 bit float mono audio',2|4));physical_out=jack.strings(jack.lib.jack_get_ports(jack.client,None,b'32 bit float mono audio',1|4))
  if len(physical_out)<2:raise RuntimeError('Brak dwóch fizycznych wyjść JACK. Nie wyłączono MultiFX.')
  state={'services':previous,'connections':jack.connections(),'release':str(release)}
  # Preserve the first rollback checkpoint across interrupted/repeated activation.
  if not (BASE/'rollback.json').exists():atomic_json(BASE/'rollback.json',state)
  units(release)
  try:
   for record in reversed(previous):manage(record,'stop')
   stale_socket()
   systemctl('start',UNITS[0]);systemctl('start',UNITS[1]);status=ready();client=status['client']
   for c in range(2):
    if physical_in:jack.connect(physical_in[min(c,len(physical_in)-1)],client+':wejscie_'+str(c+1))
    jack.connect(client+':wyjscie_'+str(c+1),physical_out[c])
   connections=jack.connections()
   if not all([client+':wyjscie_'+str(c+1),physical_out[c]] in connections for c in range(2)):raise RuntimeError('Nie potwierdzono routingu wyjściowego')
   ready();print('AKTYWACJA ZAKOŃCZONA. Panel: port 8093 na adresie Raspberry Pi. Autostart nie został włączony przed testami sprzętowymi.')
  except BaseException:
   rollback();raise
 finally:jack.close()
def buffer_change(size):
 if size not in (64,128,256,512,1024):raise RuntimeError('Niepoprawny bufor')
 before=core('STATUS');old=int(before['buffer']);jack=Jack();connections=jack.connections()
 jack.lib.jack_set_buffer_size.argtypes=[__import__('ctypes').c_void_p,__import__('ctypes').c_uint]
 def start_engine():
  stale_socket();systemctl('start',UNITS[0]);end=time.monotonic()+15
  while time.monotonic()<end:
   try:
    status=core('STATUS')
    if status['blocks']>2:return status
   except (OSError,ValueError):pass
   time.sleep(.1)
  raise RuntimeError('Silnik nie wystartował')
 try:
  systemctl('stop',UNITS[0])
  try:
   if jack.lib.jack_set_buffer_size(jack.client,size):raise RuntimeError('JACK odrzucił rozmiar bufora')
   status=start_engine()
   if status['buffer']!=size:raise RuntimeError('JACK zgłosił inny bufor')
   jack.restore(connections)
  except BaseException:
   systemctl('stop',UNITS[0],check=False);jack.lib.jack_set_buffer_size(jack.client,old);start_engine();jack.restore(connections);raise
 finally:jack.close()
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['activate','rollback','diagnostics','buffer']);p.add_argument('size',type=int,nargs='?');args=p.parse_args()
 try:
  if args.action=='activate':activate()
  elif args.action=='rollback':rollback()
  elif args.action=='buffer':buffer_change(args.size)
  else:
   print(subprocess.check_output(['uname','-a'],text=True));print(Path('/etc/os-release').read_text());print(json.dumps(core('STATUS'),ensure_ascii=False,indent=2))
 except Exception as error:print('BŁĄD: '+str(error),file=sys.stderr);return 1
 return 0
if __name__=='__main__':raise SystemExit(main())
