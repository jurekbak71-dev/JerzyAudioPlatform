import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'deploy/raspberry-pi'));import control
class UnitRestore(unittest.TestCase):
 def test_rollback_restores_exact_previous_unit_files(self):
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);units=base/'units';units.mkdir();history=base/'backup';history.mkdir();backups={}
   for unit in control.UNITS:
    old='OLD CONFIG '+unit+'\n';(history/unit).write_text(old);backups[unit]=str(history/unit);(units/unit).write_text('NEW CONFIG\n')
   (base/'rollback.json').write_text(json.dumps({'services':[],'connections':[],'unit_backups':backups,'routing_before':None,'active_release_before':{'path':'old-release'}}))
   (base/'activation-transaction.json').write_text('{"phase":"pending"}')
   class FakeJack:
    def ports(self):return []
    def restore(self,value):pass
    def close(self):pass
   with patch.object(control,'BASE',base),patch.object(control,'UNIT_DIR',units),patch.object(control,'Jack',FakeJack),patch.object(control,'systemctl'),patch.object(control,'restore_autostart'):
    control.rollback()
   for unit in control.UNITS:self.assertEqual((units/unit).read_text(),'OLD CONFIG '+unit+'\n')
   self.assertEqual(json.loads((base/'active-release.json').read_text()),{'path':'old-release'})
   self.assertEqual(json.loads((base/'activation-transaction.json').read_text())['phase'],'rolled-back')
if __name__=='__main__':unittest.main()
