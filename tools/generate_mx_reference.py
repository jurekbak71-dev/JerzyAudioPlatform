from pathlib import Path
import re
r=Path(__file__).resolve().parents[1];src=Path('/workspace/reference/JerzyMXAnalogDelayVST3/source/mxdelay_processor.cpp').read_text()
a=src.index('void MXDelayProcessor::setNormalized(');b=src.index('\nvoid MXDelayProcessor::readChanges',a)
function=src[a:b].replace('void MXDelayProcessor::setNormalized(ParamID id,double v)','void setNormalized(unsigned id,double v)')
(r/'tests/reference_mx.h').write_text('#pragma once\n#include "../modules/mx-delay-original/vendor/mxdelay_params.h"\nusing namespace JerzyAudio;\nstruct OriginalMXMapping {MXDelayParams p;\n'+function+'\n};\n')
ids=[]
for expr,index in re.findall(r'(p\.[^=]+)=b->parameters\[(\d+)\];',(r/'modules/mx-delay-original/assign.inc').read_text()):
 if expr.startswith('p.fx['):
  i,field=re.match(r'p.fx\[(\d+)\]\.(\w+)',expr).groups();n=1008+int(i)*6+['type','amount','rate','depth','drive','route'].index(field)
 elif expr.startswith('p.slot['):
  i,rest=re.match(r'p.slot\[(\d+)\]\.(.*)',expr).groups();base=1100+int(i)*300
  if rest.startswith('headPan'):n=base+10+int(re.search(r'\[(\d+)\]',rest)[1])
  elif rest.startswith('c['):alg,c=map(int,re.findall(r'\d+',rest));n=base+20+alg*16+c
  else:n=base+['algorithm','enable','sync','division','time','feedback','level','pan','duck'].index(rest)
 else:n={'p.mix':1000,'p.inputTrim':1001,'p.outputTrim':1002,'p.routing':1003,'p.bypass':1004,'p.spill':1005,'p.machineCondition':1007}[expr]
 ids.append(str(n))
(r/'tests/mx_vst_ids.inc').write_text(','.join(ids))
