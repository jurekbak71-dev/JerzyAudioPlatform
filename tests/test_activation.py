"""Failure injection, not a substitute for real systemd/HeadRush tests."""
import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'deploy/raspberry-pi'))
import control
class Activation(unittest.TestCase):
 def test_failed_readiness_restores_old_service_and_connections(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);release=base/'releases/test';(release/'bin').mkdir(parents=True);(release/'bin/jerzy-audio-core').write_bytes(b'fixture');(base/'staged').write_text(str(release))
   old='jerzy-multifx2.service';active={old};ports={'system:capture_1','system:capture_2','system:playback_1','system:playback_2','Old:in','Old:out'};original=[['system:capture_1','Old:in'],['Old:out','system:playback_1']];connections=[pair[:] for pair in original]
   class FakeJack:
    def __init__(self):self.lib=self;self.client=None
    def jack_get_ports(self,client,name,type,flags):return ['system:capture_1','system:capture_2'] if flags==6 else ['system:playback_1','system:playback_2']
    def strings(self,value):return value
    def ports(self):return list(ports)
    def connections(self):return [p[:] for p in connections]
    def restore(self,pairs):
     for pair in pairs:
      if pair not in connections:connections.append(pair)
    def close(self):pass
   def ctl(*args,check=True):
    if args[0]=='stop':active.discard(args[1])
    if args[0]=='start':active.add(args[1])
    return subprocess.CompletedProcess(args,0,'','')
   def manage(record,verb):
    unit=record['unit']
    if verb=='stop':active.discard(unit);connections.clear();ports.difference_update({'Old:in','Old:out'})
    else:active.add(unit);ports.update({'Old:in','Old:out'})
   def run(args,**kwargs):
    if 'is-active' in args:return subprocess.CompletedProcess(args,0 if args[-1] in active and '--user' not in args else 3)
    return subprocess.CompletedProcess(args,0)
   with patch.object(control,'BASE',base),patch.object(control,'UNIT_DIR',base/'user-units'),patch.object(control,'Jack',FakeJack),patch.object(control,'systemctl',ctl),patch.object(control,'manage',manage),patch.object(control,'units'),patch.object(control,'ready',side_effect=RuntimeError('forced readiness failure')),patch.object(control.subprocess,'run',side_effect=run):
    with self.assertRaisesRegex(RuntimeError,'forced readiness failure'):control.activate()
   self.assertIn(old,active);self.assertFalse(set(control.UNITS)&active);self.assertEqual(connections,original)
   checkpoint=json.loads((base/'rollback.json').read_text());self.assertEqual(checkpoint['services'],[{'scope':'system','unit':old}]);self.assertEqual(checkpoint['connections'],original)
if __name__=='__main__':unittest.main()
