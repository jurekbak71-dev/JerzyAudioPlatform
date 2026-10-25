"""Bluetooth MIDI 1.0 packet decoding; no radio or audio dependencies."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Event:
 timestamp: int
 data: bytes

class Decoder:
 def __init__(self):self.running=0;self.sysex=False
 def decode(self,packet):
  packet=bytes(packet)
  if len(packet)<3 or packet[0]&0xc0!=0x80 or not packet[1]&0x80:raise ValueError('Niepoprawny nagłówek BLE MIDI')
  high=(packet[0]&0x3f)<<7;stamp=high|(packet[1]&0x7f);i=2;result=[];timestamp=False
  while i<len(packet):
   if timestamp and packet[i]&0x80:
    stamp=high|(packet[i]&0x7f);i+=1
    if i==len(packet):raise ValueError('Brak komunikatu po znaczniku czasu')
   timestamp=False
   value=packet[i]
   if self.sysex:
    i+=1
    if value==0xf7:self.sysex=False;timestamp=True
    continue
   if value==0xf0:self.sysex=True;self.running=0;i+=1;continue
   if value&0x80:
    status=value;i+=1
    if status>=0xf8:result.append(Event(stamp,bytes([status])));timestamp=True;continue
    if status<0xf0:self.running=status
    else:self.running=0
   else:
    status=self.running
    if not status:raise ValueError('Dane MIDI bez statusu')
   if status<0xf0:size=1 if status&0xf0 in (0xc0,0xd0) else 2
   elif status in (0xf1,0xf3):size=1
   elif status==0xf2:size=2
   elif status==0xf6:size=0
   elif status==0xf7:timestamp=True;continue
   else:raise ValueError('Nieobsługiwany status MIDI')
   data=[]
   while len(data)<size:
    if i==len(packet):raise ValueError('Ucięty komunikat MIDI')
    value=packet[i];i+=1
    if value>=0xf8:result.append(Event(stamp,bytes([value])));continue
    if value&0x80:raise ValueError('Status wewnątrz danych MIDI')
    data.append(value)
   result.append(Event(stamp,bytes([status,*data])));timestamp=True
  return result

def describe(data):
 data=bytes(data)
 if not data:return {}
 status=data[0];kind={0x80:'note-off',0x90:'note-on',0xa0:'pressure',0xb0:'cc',0xc0:'pc',0xd0:'pressure',0xe0:'bend'}.get(status&0xf0,'system')
 result={'type':kind,'channel':(status&15)+1,'bytes':list(data)}
 if len(data)>1:result['number']=data[1]
 if len(data)>2:result['value']=data[2]
 elif len(data)>1:result['value']=data[1]
 return result
