"""Restricted JACK service configuration, with a timed rollback checkpoint."""
import json,os,re,shlex,subprocess,threading,time,uuid
from pathlib import Path
SERVICE='jerzy-jack.service'
class Audio:
 def __init__(self,state,dropin=Path('/etc/systemd/system/jerzy-jack.service.d/90-jerzy-audio-platform.conf'),runner=None,proc=Path('/proc'),cgroup=Path('/sys/fs/cgroup')):
  self.state=Path(state);self.state.mkdir(parents=True,exist_ok=True);self.dropin=Path(dropin);self.proc=proc;self.cgroup=cgroup;self.run=runner or self.command;self.lock=threading.RLock()
 @staticmethod
 def command(*args):
  value=subprocess.run(args,check=True,capture_output=True,text=True,timeout=30);return value.stdout.strip()
 def save(self,name,value):
  path=self.state/name;temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value));temp.chmod(0o600);os.replace(temp,path)
 @staticmethod
 def trusted_jack(executable):
  if executable.name not in ('jackd','jackdmp'):return False
  # A root broker must never persist a user-writable executable as ExecStart.
  try:return executable.is_file() and all(p.stat().st_uid==0 and not p.stat().st_mode&0o022 for p in (executable,*executable.parents))
  except OSError:return False
 def process_args(self,pid):
  executable=(self.proc/str(pid)/'exe').resolve()
  if not self.trusted_jack(executable):return None
  args=[v.decode() for v in (self.proc/str(pid)/'cmdline').read_bytes().split(b'\0') if v]
  if not args:return None
  command=Path(args[0])
  if command.is_absolute():
   if command.resolve()!=executable:return None
  elif command.name!=args[0] or command.name not in ('jackd','jackdmp'):return None
  return [str(executable),*args[1:]]
 def argv(self):
  pid=int(self.run('systemctl','show',SERVICE,'--property=MainPID','--value'))
  if pid<=0:raise RuntimeError('JACK nie działa; najpierw użyj Uruchom JACK')
  args=self.process_args(pid)
  if args is None:
   # Type=simple services may keep a shell wrapper as MainPID. Select only
   # an unambiguous JACK process from this unit, never another running JACK.
   group=self.run('systemctl','show',SERVICE,'--property=ControlGroup','--value')
   path=self.cgroup/group.lstrip('/')
   if not group.startswith('/') or group=='/' or '..' in Path(group).parts or not path.resolve().is_relative_to(self.cgroup.resolve()):raise RuntimeError('Nie można rozpoznać grupy procesów usługi JACK')
   candidates=[]
   for child in set((path/'cgroup.procs').read_text().split()):
    if not child.isdecimal():continue
    try:found=self.process_args(int(child))
    except (FileNotFoundError,ProcessLookupError):continue
    if found is not None:candidates.append(found)
   if len(candidates)!=1:raise RuntimeError('Usługa JACK musi zawierać jeden rozpoznany proces jackd/jackdmp; nie zmieniono konfiguracji')
   args=candidates[0]
  self.backend_start(args)
  return args
 @staticmethod
 def backend_start(args):
  for i,token in enumerate(args[1:],1):
   if token in ('-d','--driver'):
    if i+1<len(args) and args[i+1]=='alsa':return i+2
    break
   if token in ('-dalsa','--driver=alsa'):return i+1
  raise RuntimeError('Wymagany standardowy sterownik JACK ALSA')
 @staticmethod
 def settings(args):
  start=Audio.backend_start(args);values={'rate':48000,'buffer':1024,'periods':2}
  for short,long,key in [('-r','--rate','rate'),('-p','--period','buffer'),('-n','--nperiods','periods')]:
   for i in range(start,len(args)):
    if args[i] in (short,long) and i+1<len(args):values[key]=int(args[i+1])
    elif args[i].startswith(short) and args[i][len(short):].isdigit():values[key]=int(args[i][len(short):])
    elif args[i].startswith(long+'='):values[key]=int(args[i].split('=',1)[1])
  return values
 @staticmethod
 def configured(args,rate,buffer,periods):
  if rate not in (44100,48000) or buffer not in (64,128,256,512,1024) or periods not in (2,3):raise ValueError('Nieobsługiwany profil audio')
  start=Audio.backend_start(args);out=args[:start];i=start
  options=(('-r','--rate'),('-p','--period'),('-n','--nperiods'))
  while i<len(args):
   token=args[i];found=False
   for short,long in options:
    if token in (short,long):i+=2;found=True;break
    if (token.startswith(short) and token[len(short):].isdigit()) or token.startswith(long+'='):i+=1;found=True;break
   if not found:out.append(token);i+=1
  return out+['-r',str(rate),'-p',str(buffer),'-n',str(periods)]
 def status(self):
  try:return {'last_transaction':{k:v for k,v in (self.pending() or {}).items() if k in ('id','phase')},'available':True,'service':SERVICE,'running':True,**self.settings(self.argv())}
  except (OSError,ValueError,RuntimeError,subprocess.SubprocessError,StopIteration) as error:return {'available':True,'service':SERVICE,'running':False,'error':str(error)}
 def pending(self):
  file=self.state/'audio-transaction.json';return json.loads(file.read_text()) if file.exists() else None
 def apply(self,rate,buffer,periods):
  with self.lock:
   old=self.pending()
   if old and old['phase']=='pending':raise RuntimeError('Poprzednia zmiana audio nie została zakończona')
   if self.dropin.exists() and not self.dropin.read_text().startswith('# Managed by Jerzy Audio Platform\n'):raise RuntimeError('Istniejąca konfiguracja JACK nie należy do platformy; nie nadpisano jej')
   args=self.argv();new=self.configured(args,rate,buffer,periods)
   checkpoint={'id':uuid.uuid4().hex,'phase':'pending','deadline':time.monotonic()+90,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'previous':self.dropin.read_text() if self.dropin.exists() else None,'before':self.settings(args)}
   self.save('audio-transaction.json',checkpoint)
   self.dropin.parent.mkdir(parents=True,exist_ok=True)
   # systemd quoting, no shell and no user-provided executable/extra arguments.
   quote=lambda arg:'"'+arg.replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'
   try:
    temp=self.dropin.with_suffix('.tmp');temp.write_text('# Managed by Jerzy Audio Platform\n[Service]\nExecStart=\nExecStart='+ ' '.join(map(quote,new))+'\n');temp.chmod(0o644);os.replace(temp,self.dropin)
    self.run('systemctl','daemon-reload');self.run('systemctl','restart',SERVICE)
    actual=self.settings(self.argv())
    if actual!={'rate':rate,'buffer':buffer,'periods':periods}:raise RuntimeError('Urządzenie nie potwierdziło wybranego profilu')
    return {'transaction':checkpoint['id'],**actual}
   except BaseException:self.rollback(checkpoint['id']);raise
 def rollback(self,identifier):
  with self.lock:
   record=self.pending()
   if not record or record['id']!=identifier:raise ValueError('Niepoprawny punkt przywracania audio')
   if record['phase']=='rolled-back':return
   if record['previous'] is None:self.dropin.unlink(missing_ok=True)
   else:
    self.dropin.parent.mkdir(parents=True,exist_ok=True);self.dropin.write_text(record['previous']);self.dropin.chmod(0o644)
   self.run('systemctl','daemon-reload');self.run('systemctl','restart',SERVICE);record['phase']='rolled-back';record['needs_user_recovery']=True;self.save('audio-transaction.json',record)
 def commit(self,identifier):
  with self.lock:
   record=self.pending()
   if not record or record['id']!=identifier or record['phase']!='pending':raise ValueError('Niepoprawna transakcja audio')
   record['phase']='committed';self.save('audio-transaction.json',record)
 def recovered(self,identifier):
  with self.lock:
   record=self.pending()
   if record and record['id']==identifier:record['needs_user_recovery']=False;self.save('audio-transaction.json',record)
 def expired(self):
  record=self.pending()
  return record and record['phase']=='pending' and (time.monotonic()>record['deadline'] or record['boot']!=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
