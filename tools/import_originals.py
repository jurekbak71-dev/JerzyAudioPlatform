#!/usr/bin/env python3
"""Audited imports. Copies DSP without modifying reference repositories."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];REF=Path('/workspace/reference')
projects={
 'tape-drive-original':('JerzyTapeDriveVST3',['source/tapedrive_dsp.h','source/tapedrive_params.h']),
 'mx-delay-original':('JerzyMXAnalogDelayVST3',['source/mxdelay_dsp.h','source/mxdelay_params.h','source/mxdelay_mechanics.h']),
 'small-clone-original':('JerzySmallCloneChorus',['src/Dsp.h']),
 'atomic-cluster-original':('JerzyAtomicClusterVST3',['src/Dsp.h']),
 'memory-delay-original':('JerzyMemoryDelayOriginal',['source/dsp.h','source/parameters.h']),
 'big-muff-original':('JerzyBigMuffCollectionVST3',['Source/MuffDSP.h','Source/MuffProcessor.h','Source/Circuit/AnalogCircuit.h','Source/Circuit/Catalog.h']),
 'bass-ambient-original':('JerzyBassAmbientVST3',['Source/Core.h','Source/Parameters.def','Source/FXParameters.def'])}
for id,(repo,files) in projects.items():
 dst=ROOT/'modules'/id;dst.mkdir(exist_ok=True);(dst/'vendor').mkdir(exist_ok=True)
 hashes={}
 for file in files:
  target=dst/'vendor'/Path(file).name
  if 'Circuit/' in file:target=dst/'vendor/Circuit'/Path(file).name;target.parent.mkdir(exist_ok=True)
  shutil.copy2(REF/repo/file,target);hashes[file]=hashlib.sha256(target.read_bytes()).hexdigest()
 sha=subprocess.check_output(['git','-C',str(REF/repo),'rev-parse','HEAD'],text=True).strip()
 remote='JerzyMemoryDelay' if repo=='JerzyMemoryDelayOriginal' else repo
 provenance={'repository':'https://github.com/jurekbak71-dev/'+remote,'commit':sha,'original_files_sha256':hashes,'import':'byte-for-byte DSP; native ABI wrapper is separate'}
 (dst/'PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
 (dst/'manifest.json').write_text(json.dumps(dict(id=id,name='Jerzy '+id.replace('-original','').replace('-',' ').title()+' — oryginalny DSP',version='0.2.0',abi=1,library=id+'.so',instrument=id.startswith('bass-'),category='instrument' if id.startswith('bass-') else 'effect',source=provenance,compatibility='reference-comparison-required'),ensure_ascii=False,indent=2)+'\n')
 if (REF/repo/'LICENSE').exists():shutil.copy2(REF/repo/'LICENSE',dst/'LICENSE.txt')
 else:(dst/'LICENSE.txt').write_text('Kod DSP: prawa autora jurekbak71-dev. Użycie i dystrybucja zaakceptowane przez właściciela w sesji konfiguracji.\n')
# Extract ONLY original preparation/process code; keep the original source alongside it.
src=(REF/'JerzyBigMuffCollectionVST3/Source/MuffProcessor.h').read_text()
fields=src[src.index('    static constexpr size_t legacyCount'):src.index('public:')]
def method(name):
 start=src.index('    void '+name);a=src.index('{',start);depth=1;b=a+1
 while depth:
  depth+=(src[b]=='{')-(src[b]=='}');b+=1
 return src[start:b].replace(' override','')
prepare=method('prepareToPlay').replace('setLatencySamples(int(oversampling->getLatencyInSamples()));','latencyFrames=int(oversampling->getLatencyInSamples());')
process=method('processBlock')
header='''#pragma once
#include <juce_dsp/juce_dsp.h>
#include "vendor/MuffDSP.h"
#include "vendor/Circuit/AnalogCircuit.h"
// Mechanical extraction of the original DSP processor. No GUI/VST host code.
class OriginalMuffDSP {
'''+fields+'''
public:
 int latencyFrames=0;
 std::array<std::atomic<float>,6> controls;
 OriginalMuffDSP(){const float d[]{.5,.5,.5,0,0,float(circuitCount)};for(int i=0;i<6;++i)controls[i].store(d[i]);volumeParam=&controls[0];toneParam=&controls[1];sustainParam=&controls[2];modelParam=&controls[3];bypassParam=&controls[4];circuitParam=&controls[5];}
 int selectedModel() const {int c=juce::jlimit(0,int(circuitCount),int(circuitParam->load()));return c==0?juce::jlimit(0,5,int(modelParam->load())):5+c;}
 bool isReady() const{return ready;}
'''+prepare+'\n'+process+'\n};\n'
(ROOT/'modules/big-muff-original/OriginalProcessor.h').write_text(header)
