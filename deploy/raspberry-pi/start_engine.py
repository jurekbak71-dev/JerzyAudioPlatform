#!/usr/bin/env python3
"""Restartable user-service entry: wait for JACK, restore graph and own routing."""
import argparse,json,os,signal,socket,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=Path.home()/'.local/share/jerzy-audio-platform'
sys.path.insert(0,str(ROOT/'module-manager'));from manager import atomic_json
sys.path.insert(0,str(ROOT/'deploy/raspberry-pi'));from jack_graph import Jack

def core(command):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(3);s.connect(str(BASE/'core.sock'));s.sendall((command+'\n').encode());raw=b''
  while not raw.endswith(b'\n'):
   chunk=s.recv(65536)
   if not chunk:raise RuntimeError('Silnik zamknął gniazdo')
   raw+=chunk
  value=json.loads(raw)
  if not value.get('ok'):raise RuntimeError(value.get('error','Błąd silnika'))
  return value

def migrate_lv2_session():
 file=BASE/'last-session.json'
 if not file.exists():return
 old=json.loads(file.read_text())
 if any(not n.get('module','').startswith('lv2:') for n in old.get('nodes',[])):
  atomic_json(BASE/('session-before-lv2-'+str(time.time_ns())+'.json'),old)
  old['nodes']=[];old['schema']=1;old['plugin_format']='lv2';atomic_json(file,old)

def main():
 end=time.monotonic()+60
 while True:
  try:
   jack=Jack()
   try:ports=jack.ports()
   finally:jack.close()
   if any(port.startswith('system:playback_') for port in ports):break
  except (OSError,RuntimeError):pass
  if time.monotonic()>=end:raise RuntimeError('JACK nie potwierdził portów; nie uruchomiono drugiego serwera')
  time.sleep(1)
 settings=BASE/'audio-settings.json'
 if settings.exists():
  desired=json.loads(settings.read_text()).get('buffer')
  if desired in (64,128,256,512,1024):
   import ctypes
   jack=Jack()
   try:
    jack.lib.jack_set_buffer_size.argtypes=[ctypes.c_void_p,ctypes.c_uint]
    jack.lib.jack_set_buffer_size.restype=ctypes.c_int
    jack.lib.jack_get_buffer_size.argtypes=[ctypes.c_void_p];jack.lib.jack_get_buffer_size.restype=ctypes.c_uint
    if jack.lib.jack_get_buffer_size(jack.client)!=desired:
     sys.path.insert(0,str(ROOT/'deploy/connectivity'))
     try:
      from client import status as hardware_status
      managed=hardware_status().get('available',False)
     except ImportError:managed=False
     if not managed and jack.lib.jack_set_buffer_size(jack.client,desired):raise RuntimeError('Nie przywrócono zapisanego bufora JACK')
   finally:jack.close()
 path=BASE/'core.sock'
 if path.exists():
  import stat
  if not stat.S_ISSOCK(path.stat().st_mode):raise RuntimeError('Ścieżka sterowania nie jest gniazdem')
  try:core('STATUS')
  except ConnectionRefusedError:path.unlink()
  else:raise RuntimeError('Pod gniazdem działa już silnik')
 atomic_json(BASE/'session-recovery.json',{'error':None,'pending':True})
 environment=os.environ.copy();environment['LD_LIBRARY_PATH']=str(ROOT/'lib')+(':'+environment['LD_LIBRARY_PATH'] if environment.get('LD_LIBRARY_PATH') else '');process=subprocess.Popen([str(ROOT/'bin/jerzy-audio-core'),str(path)],env=environment)
 def stop(signum,frame):
  if process.poll() is None:process.terminate()
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 try:
  end=time.monotonic()+15
  while True:
   if process.poll() is not None:raise RuntimeError('Silnik zakończył pracę przy starcie')
   try:
    status=core('STATUS')
    if status['blocks']>2:break
   except (OSError,ValueError):pass
   if time.monotonic()>=end:raise RuntimeError('Brak gotowości silnika')
   time.sleep(.1)
  recovery=BASE/'session-recovery.json';session_error=None
  skip=BASE/'skip-session-once'
  if (BASE/'last-session.json').exists() and not skip.exists():
   try:
    migrate_lv2_session()
    sys.path.insert(0,str(ROOT/'web-ui'));from server import Application
    args=argparse.Namespace(data=str(BASE),modules=str(BASE/'modules'),socket=str(path))
    Application(args).apply_preset(json.loads((BASE/'last-session.json').read_text()))
    session_error=None
   except Exception as error:session_error=str(error)
  else:session_error=None
  if (BASE/'audio-routing.json').exists():
   routing=json.loads((BASE/'audio-routing.json').read_text());jack=Jack()
   try:
    for i,source in enumerate(routing.get('inputs',[])):jack.connect(source,status['client']+':wejscie_'+str(i+1))
    for i,target in enumerate(routing.get('outputs',[])):jack.connect(status['client']+':wyjscie_'+str(i+1),target)
   finally:jack.close()
  thru=BASE/'thru-jack.json'
  if thru.exists() and json.loads(thru.read_text()).get('disabled'):
   jack=Jack()
   try:
    for source,target in jack.direct_thru():jack.disconnect(source,target)
   finally:jack.close()
  atomic_json(recovery,{'error':session_error,'pending':False})
  if skip.exists():skip.unlink()
  print('Silnik, odtworzenie sesji i routing przygotowane.',flush=True)
  last_blocks=core('STATUS')['blocks'];last_progress=time.monotonic()
  while process.poll() is None:
   time.sleep(.5)
   try:
    status=core('STATUS')
    if status['blocks']!=last_blocks:last_blocks=status['blocks'];last_progress=time.monotonic()
   except (OSError,ValueError,RuntimeError):pass
   if time.monotonic()-last_progress>10:
    print('Brak postępu audio: restart procesu silnika.',flush=True)
    process.terminate()
    try:process.wait(timeout=2)
    except subprocess.TimeoutExpired:process.kill();process.wait()
    return 70
  return process.returncode
 finally:
  if process.poll() is None:
   process.terminate()
   try:process.wait(timeout=10)
   except subprocess.TimeoutExpired:process.kill();process.wait()
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as error:print('BŁĄD STARTU: '+str(error),file=sys.stderr);raise SystemExit(1)
