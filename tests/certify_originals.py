#!/usr/bin/env python3
"""Attach only completed, current-build reference test results to module packages."""
import argparse,hashlib,json,platform,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);a=p.parse_args()
 log=(a.build/'Testing/Temporary/LastTest.log').read_text();records={}
 for line in log.splitlines():
  if line.startswith('{"module":'):
   record=json.loads(line);records[record['module']]=record
 expected={d.name for d in (ROOT/'modules').glob('*-original')}
 if set(records)!=expected:raise RuntimeError('Niekompletny bieżący zestaw testów: '+str(expected-set(records)))
 pin=json.loads((ROOT/'licenses/JUCE-DSP-PIN.json').read_text())
 cache=(a.build/'CMakeCache.txt').read_text();prefix='JERZY_JUCE_ROOT:PATH='
 entry=next((line[len(prefix):] for line in cache.splitlines() if line.startswith(prefix)),'')
 juce=Path(entry) if entry else a.build/'_deps/juce_original-src'
 for name,expected_hash in pin['files'].items():
  if hashlib.sha256((juce/name).read_bytes()).hexdigest()!=expected_hash:raise RuntimeError('Zmieniony przypięty JUCE DSP: '+name)
 output=a.build/'compatibility';output.mkdir(exist_ok=True)
 for id,record in records.items():
  source=ROOT/'modules'/id;provenance=json.loads((source/'PROVENANCE.json').read_text())
  for original,expected_hash in provenance['original_files_sha256'].items():
   file=source/'vendor'/Path(original).name
   if '/Circuit/' in original:file=source/'vendor/Circuit'/Path(original).name
   if hashlib.sha256(file.read_bytes()).hexdigest()!=expected_hash:raise RuntimeError('Zmieniony oryginalny DSP: '+str(file))
  if record['max_error']>1e-7 or record['samples']<=0:raise RuntimeError('Niezgodny DSP: '+id)
  library=a.build/'modules'/id/(id+'.so')
  # LastTest.log must describe these binaries, not a prior build.
  if library.stat().st_mtime>(a.build/'Testing/Temporary/LastTest.log').stat().st_mtime:raise RuntimeError('Biblioteka nowsza niż testy: '+id)
  result={**record,'passed':True,'abi':1,'sample_rates':[44100,48000],'block_sizes':[64,128,256,512,1024],'reference_commit':provenance['commit'],'library_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'reference_files_verified':True,'hardware_validated':False,'scope':'float32 DSP, tested parameter/MIDI/tempo scenarios; not complete VST GUI/state format or physical hardware certification'}
  manifest=json.loads((source/'manifest.json').read_text());manifest['compatibility']=result
  (a.build/'modules'/id/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
  (output/(id+'.json')).write_text(json.dumps(result,indent=2)+'\n')
 print('PASS: siedem raportów zgodności przypisano do dokładnych bibliotek i źródeł.')
if __name__=='__main__':main()
