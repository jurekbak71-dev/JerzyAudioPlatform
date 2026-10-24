#!/usr/bin/env python3
"""Offline signal measurements on the current host; not physical Pi measurements."""
import argparse,ctypes as C,json,math,time
from pathlib import Path
class Parameter(C.Structure):_fields_=[('id',C.c_char_p),('label',C.c_char_p),('unit',C.c_char_p),('choices',C.c_char_p),('min',C.c_float),('max',C.c_float),('initial',C.c_float),('integer',C.c_uint32)]
class Block(C.Structure):_fields_=[('size',C.c_uint32),('frames',C.c_uint32),('sample_rate',C.c_double),('bpm',C.c_double),('beat',C.c_double),('playing',C.c_uint32),('input',C.POINTER(C.c_float)*2),('output',C.POINTER(C.c_float)*2),('parameters',C.POINTER(C.c_float)),('midi',C.c_void_p),('midi_count',C.c_uint32)]
class Module(C.Structure):_fields_=[('size',C.c_uint32),('abi',C.c_uint32),('id',C.c_char_p),('name',C.c_char_p),('version',C.c_char_p),('instrument',C.c_uint32),('count',C.c_uint32),('parameters',C.POINTER(Parameter)),('create',C.c_void_p),('destroy',C.c_void_p),('process',C.c_void_p),('latency',C.c_void_p)]
def render(root,id,sr,frequency,changes={}):
 lib=C.CDLL(str(root/id/(id+'.so')));lib.ja_module.restype=C.POINTER(Module);m=lib.ja_module().contents
 assert m.size==C.sizeof(Module) and m.abi==1
 create=C.CFUNCTYPE(C.c_void_p,C.c_double,C.c_uint32,C.c_char_p)(m.create);destroy=C.CFUNCTYPE(None,C.c_void_p)(m.destroy);process=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Block))(m.process)
 instance=create(sr,128,b'');values=(C.c_float*m.count)(*[changes.get(m.parameters[i].id.decode(),m.parameters[i].initial) for i in range(m.count)])
 arrays=[(C.c_float*128)() for i in range(4)];block=Block(C.sizeof(Block),128,sr,120,0,1,(C.POINTER(C.c_float)*2)(arrays[0],arrays[1]),(C.POINTER(C.c_float)*2)(arrays[2],arrays[3]),values,None,0);output=[];start=time.perf_counter()
 try:
  for chunk in range(96):
   for i in range(128):arrays[0][i]=arrays[1][i]=.1*math.sin(2*math.pi*frequency*(chunk*128+i)/sr)
   process(instance,C.byref(block))
   if chunk>=64:output.extend(arrays[2])
 finally:destroy(instance)
 elapsed=time.perf_counter()-start
 assert all(math.isfinite(v) for v in output)
 rms=math.sqrt(sum(v*v for v in output)/len(output));peak=max(map(abs,output))
 amplitudes=[]
 for harmonic in range(1,11):
  real=sum(v*math.cos(2*math.pi*frequency*harmonic*i/sr) for i,v in enumerate(output));imag=sum(v*math.sin(2*math.pi*frequency*harmonic*i/sr) for i,v in enumerate(output));amplitudes.append(2*math.hypot(real,imag)/len(output))
 thd=math.sqrt(sum(v*v for v in amplitudes[1:]))/max(amplitudes[0],1e-12)
 return dict(sample_rate=sr,frequency_hz=frequency,rms=rms,peak=peak,thd_h2_h10=thd,render_wall_seconds_including_python=elapsed)
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);a=p.parse_args();result={'environment':'Linux x86_64 cloud, offline, not Raspberry Pi','modules':{}}
 for id in ['big-muff','tape-drive']:
  result['modules'][id]=[]
  for sr in [44100,48000]:
   for value in [.1,.5,.9]:
    key='sustain' if id=='big-muff' else 'drive';entry=render(a.build/'modules',id,sr,sr/128,{key:value});entry[key]=value;result['modules'][id].append(entry)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
