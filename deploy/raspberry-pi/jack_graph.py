"""Inspect and restore JACK connections through the actual JACK C API."""
import ctypes,ctypes.util
class Jack:
 def __init__(self):
  self.lib=ctypes.CDLL(ctypes.util.find_library('jack') or 'libjack.so.0');L=self.lib
  L.jack_client_open.restype=ctypes.c_void_p;L.jack_client_open.argtypes=[ctypes.c_char_p,ctypes.c_int,ctypes.POINTER(ctypes.c_int)]
  L.jack_client_close.argtypes=[ctypes.c_void_p];L.jack_get_ports.restype=ctypes.POINTER(ctypes.c_char_p);L.jack_get_ports.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_ulong]
  L.jack_port_by_name.restype=ctypes.c_void_p;L.jack_port_by_name.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
  L.jack_port_get_all_connections.restype=ctypes.POINTER(ctypes.c_char_p);L.jack_port_get_all_connections.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
  L.jack_connect.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_char_p];L.jack_disconnect.argtypes=L.jack_connect.argtypes
  L.jack_free.argtypes=[ctypes.c_void_p]
  status=ctypes.c_int();self.client=L.jack_client_open(b'JerzyPlatformRouting',1,ctypes.byref(status))
  if not self.client:raise RuntimeError('JACK nie działa. Nie zmieniono jego konfiguracji.')
 def strings(self,array):
  if not array:return []
  result=[];i=0
  while array[i]:result.append(array[i].decode());i+=1
  self.lib.jack_free(array);return result
 def ports(self,flags=0):return self.strings(self.lib.jack_get_ports(self.client,None,None,flags))
 def connections(self):
  result=[]
  for source in self.ports(2):
   port=self.lib.jack_port_by_name(self.client,source.encode())
   for dest in self.strings(self.lib.jack_port_get_all_connections(self.client,port)):result.append([source,dest])
  return result
 def connect(self,source,dest):
  code=self.lib.jack_connect(self.client,source.encode(),dest.encode())
  if code not in (0,17):raise RuntimeError('Nie można połączyć '+source+' → '+dest)
 def direct_thru(self):
  audio=b'32 bit float mono audio'
  sources=set(self.strings(self.lib.jack_get_ports(self.client,None,audio,2|4)));targets=set(self.strings(self.lib.jack_get_ports(self.client,None,audio,1|4)))
  return [pair for pair in self.connections() if pair[0] in sources and pair[1] in targets]
 def disconnect(self,source,dest):
  code=self.lib.jack_disconnect(self.client,source.encode(),dest.encode())
  if code not in (0,2):raise RuntimeError('Nie można rozłączyć '+source+' → '+dest)
 def restore(self,connections):
  available=set(self.ports())
  for source,dest in connections:
   if source in available and dest in available:self.connect(source,dest)
 def close(self):self.lib.jack_client_close(self.client)
