"""Unprivileged interface to the bounded local hardware service."""
import json,os,socket,time
from pathlib import Path
SOCKET='/run/jerzy-audio-platform/control.sock'
def call(operation,timeout=40,**values):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(timeout);s.connect(SOCKET);s.sendall((json.dumps({'operation':operation,**values})+'\n').encode());raw=b''
  while not raw.endswith(b'\n'):
   chunk=s.recv(65536)
   if not chunk or len(raw)>1024*1024:raise RuntimeError('Niepełna odpowiedź usługi sprzętowej')
   raw+=chunk
 result=json.loads(raw)
 if not result.get('ok'):raise RuntimeError(result.get('error','Błąd usługi sprzętowej'))
 return result

def status():
 path=Path('/run/jerzy-audio-platform/status.json')
 try:
  value=json.loads(path.read_text())
  if time.time()-value.get('updated',0)>12:return {'available':False,'error':'Usługa sprzętowa nie odpowiada'}
  if value.get('uid')!=os.getuid():return {'available':False,'error':'Usługa jest przypisana do innego użytkownika'}
  return {'available':True,**value}
 except (OSError,ValueError):return {'available':False,'error':'Nie zainstalowano usługi sprzętowej tej wersji'}
