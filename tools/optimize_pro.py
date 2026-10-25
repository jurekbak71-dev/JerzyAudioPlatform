#!/usr/bin/env python3
"""Deterministic, exact coefficient caching and redundant oversampling-work hoisting."""
from pathlib import Path
import argparse
ROOT=Path(__file__).resolve().parents[1]/'modules/bass-ambient-pro-original'
def generated():
 s=(ROOT/'vendor/Core.h').read_text()
 def replace(old,new):
  nonlocal s
  if s.count(old)!=1:raise RuntimeError('Original source changed: '+old[:70])
  s=s.replace(old,new)
 s=s.replace('#include "ModalExciter.h"','#include "vendor/ModalExciter.h"').replace('#include "ProEngines.h"','#include "OptimizedProEngines.h"')
 replace('namespace jerzy {','namespace jerzy_opt {\nusing jerzy::ModalExciter;using jerzy::StrikeTransient;')
 replace('double value=0, rate=48000, releaseStart=0, elapsed=0;', 'double value=0, rate=48000, releaseStart=0, elapsed=0;double attackTime=-1,attackRate=-1,attackCoefficient=0;')
 replace('case Attack: value += (1.0-value)*(1.0-std::exp(-6.0*dt/std::max(a,.0002)));', 'case Attack: if(a!=attackTime||rate!=attackRate){attackTime=a;attackRate=rate;attackCoefficient=1.0-std::exp(-6.0*dt/std::max(a,.0002));} value += (1.0-value)*attackCoefficient;')
 replace('std::array<double,4> z{};', 'std::array<double,4> z{},tanhZ{};double cachedCutoff=-1,cachedRate=-1,cachedCoefficient=0;')
 replace('double g=1-std::exp(-2*pi*clamp(cutoff,20.0,sr*.18)/sr);', 'if(cutoff!=cachedCutoff||sr!=cachedRate){cachedCutoff=cutoff;cachedRate=sr;cachedCoefficient=1-std::exp(-2*pi*clamp(cutoff,20.0,sr*.18)/sr);}double g=cachedCoefficient;')
 replace('for(auto& s:z) { s+=g*(std::tanh(x)-std::tanh(s)); x=s; }', 'double transfer=std::tanh(x);for(size_t i=0;i<z.size();++i){auto& s=z[i];s+=g*(transfer-tanhZ[i]);x=s;transfer=std::tanh(s);tanhZ[i]=transfer;}')
 replace('void reset() { z.fill(0); }', 'void reset() { z.fill(0);tanhZ.fill(0); }')
 old='''        double x=0,stereoRight=0;
        for(int i=0;i<2;++i) {'''
 new='''        double x=0,stereoRight=0;
        const double frequencyA=hz(note+bend+cents/100),frequencyB=hz(note+bend-cents/120+.045),frequencyC=hz(note+bend+cents/100+p.padDetune/100),frequencyD=hz(note+bend-cents/120-p.padDetune/100),frequencyShimmer=hz(note+bend+12);
        const double cutoffL=p.padCutoff*std::exp2(modulation*2),cutoffR=p.padCutoff*std::exp2(-modulation*1.6);
        for(int i=0;i<2;++i) {'''
 replace(old,new)
 for old,new in [('engine(a,p.engine1,hz(note+bend+cents/100),','engine(a,p.engine1,frequencyA,'),('engine(b,p.engine2,hz(note+bend-cents/120+.045),','engine(b,p.engine2,frequencyB,'),('engine(c,p.engine1,hz(note+bend+cents/100+p.padDetune/100),','engine(c,p.engine1,frequencyC,'),('engine(d,p.engine2,hz(note+bend-cents/120-p.padDetune/100),','engine(d,p.engine2,frequencyD,'),('shimmer.next(hz(note+bend+12),','shimmer.next(frequencyShimmer,'),('fl.process(left,p.padCutoff*std::exp2(modulation*2),','fl.process(left,cutoffL,'),('fr.process(right,p.padCutoff*std::exp2(-modulation*1.6),','fr.process(right,cutoffR,')]:replace(old,new)
 return {'OptimizedCore.h':s,'OptimizedProEngines.h':(ROOT/'vendor/ProEngines.h').read_text()}
def main():
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
 for name,data in generated().items():
  path=ROOT/name
  if a.check:
   if not path.exists() or path.read_text()!=data:raise RuntimeError('Stale generated DSP: '+name)
  else:path.write_text(data)
if __name__=='__main__':main()
