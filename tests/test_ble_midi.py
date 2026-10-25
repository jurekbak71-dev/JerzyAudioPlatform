import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deploy/connectivity'))
from ble_midi import Decoder,describe
class BleMidi(unittest.TestCase):
 def test_channel_messages_and_running_status(self):
  events=Decoder().decode(bytes([0x80,0x81,0xb0,20,127,0x82,20,0,0x83,0xc1,12]))
  self.assertEqual([e.data for e in events],[bytes([0xb0,20,127]),bytes([0xb0,20,0]),bytes([0xc1,12])]);self.assertEqual([e.timestamp for e in events],[1,2,3])
 def test_notes_bend_and_clock(self):
  d=Decoder();self.assertEqual(d.decode(bytes([0x81,0xfe,0x90,60,100]))[0].timestamp,254)
  self.assertEqual(d.decode(bytes([0x80,0x80,0xe0,0,64]))[0].data,b'\xe0\0@')
  self.assertEqual(d.decode(bytes([0x80,0x80,0xf8]))[0].data,b'\xf8')
 def test_realtime_can_interleave_data(self):
  self.assertEqual([x.data for x in Decoder().decode(bytes([0x80,0x80,0x90,60,0xf8,100]))],[b'\xf8',bytes([0x90,60,100])])
 def test_truncated_or_invalid_is_rejected(self):
  for packet in [b'',b'\0\x80\xc0\0',b'\x80\0\xc0\0',b'\x80\x80\x90\x3c',b'\x80\x80\xb0\x80\0']:
   with self.assertRaises(ValueError):Decoder().decode(packet)
 def test_sysex_does_not_turn_into_channel_events(self):
  d=Decoder();self.assertEqual(d.decode(bytes([0x80,0x80,0xf0,1,2])),[])
  self.assertEqual(d.decode(bytes([0x80,0x81,3,4,0xf7])),[])
  self.assertEqual(d.decode(bytes([0x80,0x82,0xc0,5]))[0].data,b'\xc0\5')
 def test_cc_and_pc_description(self):
  self.assertEqual(describe(bytes([0xb3,21,127]))['channel'],4);self.assertEqual(describe(bytes([0xc0,0]))['type'],'pc')
if __name__=='__main__':unittest.main()
