#!/usr/bin/env python3
"""NetworkManager Wi-Fi change with explicit acknowledgement and rollback.
Passwords are entered on the Pi, never command arguments or reports.
"""
import ipaddress
import argparse,configparser,fcntl,getpass,io,json,os,shutil,subprocess,sys,time,uuid
from pathlib import Path
BASE=Path('/var/lib/jerzy-audio-platform-wifi')
PROFILES=Path('/etc/NetworkManager/system-connections')
UNIT='jerzy-home-wifi-change'
WINDOW=300
def boot_id():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
def unexpired(state):return state.get('boot_id')==boot_id() and time.monotonic()<state['deadline_monotonic']

def run(*args,check=True,timeout=30):
 result=subprocess.run(list(args),capture_output=True,text=True,timeout=timeout)
 if check and result.returncode:raise RuntimeError('Polecenie nie powiodło się: '+args[0]+' — '+result.stderr.strip())
 return result.stdout.strip() if check else result

def save(state):
 BASE.mkdir(parents=True,exist_ok=True,mode=0o700)
 tmp=BASE/'state.tmp';tmp.write_text(json.dumps(state));tmp.chmod(0o600);os.replace(tmp,BASE/'state.json')

def load():return json.loads((BASE/'state.json').read_text())
def active_uuid(device):
 for line in run('nmcli','-t','-f','UUID,DEVICE','connection','show','--active').splitlines():
  identifier,_,dev=line.partition(':')
  if dev==device:return identifier
 return ''
def address(device):
 result=[]
 for value in run('nmcli','-g','IP4.ADDRESS','device','show',device).splitlines():
  try:interface=ipaddress.ip_interface(value)
  except ValueError:continue
  if interface.version==4 and not interface.ip.is_link_local and not interface.ip.is_loopback and not interface.ip.is_unspecified:result.append(value)
 return result

def key_escape(value):
 # GLib keyfile string escaping; do not interpolate passwords through a shell.
 return value.replace('\\','\\\\').replace('\t','\\t').replace('\r','\\r').replace('\n','\\n').replace(' ','\\s')

def locked(function):
 def inner(*args,**kwargs):
  BASE.mkdir(parents=True,exist_ok=True,mode=0o700)
  with (BASE/'lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   return function(*args,**kwargs)
 return inner

@locked
def rollback():
 state=load()
 if state['phase'] in ('confirmed','rolled-back'):return
 result=run('nmcli','--wait','40','connection','up','uuid',state['previous'],check=False,timeout=50)
 if result.returncode:
  state['phase']='rollback-failed';state['error']=result.stderr.strip();save(state)
  print('Nie przywrócono poprzedniego profilu. Pozostawiono nowy profil i jego dane do odzyskania.',flush=True)
  return
 # Only remove the new profile created by this transaction.
 run('nmcli','connection','delete','uuid',state['new'],check=False)
 state['phase']='rolled-back';save(state);print('Przywrócono poprzedni profil Wi-Fi/hotspot.',flush=True)

@locked
def prepare():
 if os.geteuid()!=0:raise RuntimeError('Uruchom przez sudo.')
 if not shutil.which('nmcli'):raise RuntimeError('Brak NetworkManager/nmcli. Nie zmieniono sieci.')
 if run('systemctl','is-active','NetworkManager')!='active':raise RuntimeError('NetworkManager nie działa.')
 BASE.mkdir(parents=True,exist_ok=True,mode=0o700)
 if (BASE/'state.json').exists():
  old=load()
  if old['phase'] in ('prepared','switching','awaiting-confirmation') and unexpired(old):raise RuntimeError('Poprzednia zmiana Wi-Fi nadal czeka na potwierdzenie; nie rozpoczęto kolejnej.')
 devices=[]
 for line in run('nmcli','-t','-f','DEVICE,TYPE','device','status').splitlines():
  device,_,kind=line.partition(':')
  if kind=='wifi' and active_uuid(device):devices.append(device)
 if len(devices)!=1:raise RuntimeError('Wymagany dokładnie jeden aktywny interfejs Wi-Fi zarządzany przez NetworkManager. Nie zmieniono sieci.')
 device=devices[0];previous=active_uuid(device)
 ssid=input('Nazwa domowej sieci Wi-Fi (SSID): ')
 password=getpass.getpass('Hasło domowego Wi-Fi (nie będzie wyświetlane): ')
 if not ssid or len(ssid.encode())>32 or any(c in ssid for c in '\n\r\x00'):raise RuntimeError('Nieprawidłowy SSID.')
 valid=(8<=len(password.encode())<=63) or (len(password)==64 and all(c in '0123456789abcdefABCDEF' for c in password))
 if not valid or any(c in password for c in '\n\r\x00'):raise RuntimeError('Wymagane hasło WPA2: 8–63 bajty lub 64 cyfry szesnastkowe.')
 priority=min(2147483647,int(run('nmcli','-g','connection.autoconnect-priority','connection','show','uuid',previous))+10)
 identifier=str(uuid.uuid4());profile=PROFILES/('jerzy-home-'+identifier+'.nmconnection')
 config=configparser.ConfigParser(interpolation=None)
 config['connection']={'id':'Jerzy — domowe Wi-Fi','uuid':identifier,'type':'wifi','interface-name':device,'autoconnect':'false','autoconnect-priority':str(priority)}
 config['wifi']={'mode':'infrastructure','ssid':key_escape(ssid),'hidden':'true'}
 config['wifi-security']={'key-mgmt':'wpa-psk','psk':key_escape(password),'psk-flags':'0'}
 config['ipv4']={'method':'auto'};config['ipv6']={'method':'auto'}
 buffer=io.StringIO();config.write(buffer,space_around_delimiters=False)
 descriptor=os.open(profile,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(descriptor,'w') as f:f.write(buffer.getvalue())
 password='';buffer.close()
 try:run('nmcli','connection','load',str(profile))
 except BaseException:profile.unlink();raise
 state={'phase':'prepared','device':device,'previous':previous,'new':identifier,'deadline':time.time()+WINDOW,'deadline_monotonic':time.monotonic()+WINDOW,'boot_id':boot_id(),'addresses':[],'confirmed':False}
 save(state)
 worker=BASE/('tool-'+identifier+'.py');shutil.copyfile(Path(__file__).resolve(),worker);worker.chmod(0o700)
 try:
  run('systemd-run','--quiet','--collect','--unit='+UNIT,'--property=Type=exec','--property=ExecStopPost=/usr/bin/python3 '+str(worker)+' rollback','/usr/bin/python3',str(worker),'worker')
 except BaseException:
  run('nmcli','connection','delete','uuid',identifier,check=False);state['phase']='rolled-back';save(state);raise
 print('Za 8 sekund Pi przełączy się do domowej sieci. Połącz z nią Windows i potwierdź połączenie w instalatorze.',flush=True)
 print('Bez potwierdzenia w ciągu 5 minut poprzedni profil zostanie przywrócony. Hotspot nie jest usuwany.',flush=True)

def worker():
 time.sleep(8);state=load();state['phase']='switching';save(state)
 try:
  run('nmcli','--wait','50','connection','up','uuid',state['new'],timeout=60)
  # NetworkManager may mark activation complete after IPv6 while DHCPv4
  # is still performing address conflict detection. Wait for usable IPv4.
  ipv4_end=min(time.monotonic()+60,state['deadline_monotonic'])
  while active_uuid(state['device'])!=state['new'] or not address(state['device']):
   if time.monotonic()>=ipv4_end:raise RuntimeError('Brak potwierdzonego połączenia lub IPv4 po oczekiwaniu DHCP.')
   time.sleep(1)
  state['addresses']=address(state['device']);state['phase']='awaiting-confirmation';save(state)
  while unexpired(state):
   if load().get('confirmed'):return
   time.sleep(1)
 finally:
  if not load().get('confirmed'):rollback()

@locked
def confirm():
 state=load()
 if state['phase']!='awaiting-confirmation' or not unexpired(state):raise RuntimeError('Brak zmiany oczekującej na potwierdzenie. Poprzedni profil mógł zostać przywrócony.')
 if active_uuid(state['device'])!=state['new'] or not address(state['device']):raise RuntimeError('Domowy profil nie jest aktywny.')
 # A successful SSH connection from the new LAN and host-key verification in
 # the Windows helper are required before this explicit confirmation.
 run('nmcli','connection','modify','uuid',state['new'],'connection.autoconnect','yes')
 state['phase']='confirmed';state['confirmed']=True;state['addresses']=address(state['device']);save(state)
 print('Domowe Wi-Fi potwierdzone. Hotspot zachowany jako osobny profil. Adresy: '+', '.join(state['addresses']))

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','worker','confirm','rollback','status']);args=p.parse_args()
 try:
  if os.geteuid()!=0:raise RuntimeError('Wymagane sudo.')
  if args.action=='status':print(json.dumps(load(),ensure_ascii=False,indent=2))
  else:globals()[args.action]()
 except Exception as e:print('BŁĄD: '+str(e),file=sys.stderr);return 1
 return 0
if __name__=='__main__':raise SystemExit(main())
