import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('lv2_boot',ROOT/'deploy/raspberry-pi/start_engine.py');boot=importlib.util.module_from_spec(spec);spec.loader.exec_module(boot)
class Migration(unittest.TestCase):
 def test_archives_legacy_session_and_preserves_mix(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);old={'schema':1,'nodes':[{'module':'bass-ambient-pro-original','parameters':[{'id':'master','value':.37}]}],'master':.6,'bpm':121};file=root/'last-session.json';file.write_text(json.dumps(old))
   with patch.object(boot,'BASE',root):boot.migrate_lv2_session()
   saved=json.loads(file.read_text());self.assertEqual(saved['nodes'],[]);self.assertEqual(saved['master'],.6);self.assertEqual(saved['plugin_format'],'lv2');archive=list(root.glob('session-before-lv2-*.json'));self.assertEqual(len(archive),1);self.assertEqual(json.loads(archive[0].read_text()),old)
 def test_lv2_session_is_unchanged(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);file=root/'last-session.json';text=json.dumps({'nodes':[{'module':'lv2:urn:example'}]});file.write_text(text)
   with patch.object(boot,'BASE',root):boot.migrate_lv2_session()
   self.assertEqual(file.read_text(),text);self.assertFalse(list(root.glob('session-before-lv2-*')))
 def test_corrupt_session_is_not_overwritten(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);file=root/'last-session.json';file.write_text('broken json')
   with patch.object(boot,'BASE',root),self.assertRaises(ValueError):boot.migrate_lv2_session()
   self.assertEqual(file.read_text(),'broken json')
