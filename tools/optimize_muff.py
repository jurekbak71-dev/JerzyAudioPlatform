#!/usr/bin/env python3
"""Cache repeated linear circuit stamps without changing the nonlinear solver."""
from pathlib import Path
import argparse
ROOT=Path(__file__).resolve().parents[1]/'modules/big-muff-original'
def generated():
 source=(ROOT/'vendor/Circuit/AnalogCircuit.h').read_text()
 def replace(old,new):
  nonlocal source
  if source.count(old)!=1:raise RuntimeError('Original Muff source changed: '+old[:60])
  source=source.replace(old,new)
 replace('#include "Catalog.h"','#include "vendor/Circuit/Catalog.h"')
 replace('namespace muff::circuit {','namespace muff_opt::circuit {\nusing namespace muff::circuit;')
 replace('void rebuild() {','''struct LinearCache {
        bool valid=false; double rate=0,s=0,t=0,v=0,supplyVoltage=0;size_t model=0;
        Matrix matrix{};Vector rhs{},input{};
    };
    std::array<LinearCache,3> linearCache{};size_t cacheCursor=0;
    void rebuild() {
        if(dcMode){rebuildUncached();return;}
        for(const auto& item:linearCache)if(item.valid&&item.rate==fs&&item.s==sustain&&item.t==tone&&item.v==volume&&item.supplyVoltage==rail&&item.model==revisionIndex){passive=item.matrix;constant=item.rhs;inputCoefficient=item.input;return;}
        rebuildUncached();auto& item=linearCache[cacheCursor++%linearCache.size()];
        item.valid=true;item.rate=fs;item.s=sustain;item.t=tone;item.v=volume;item.supplyVoltage=rail;item.model=revisionIndex;
        item.matrix=passive;item.rhs=constant;item.input=inputCoefficient;
    }
    void rebuildUncached() {''')
 replace('fs=sampleRate;revisionIndex=model;sustain=s;tone=t;volume=v;', 'for(auto& item:linearCache)item.valid=false;cacheCursor=0;\n        fs=sampleRate;revisionIndex=model;sustain=s;tone=t;volume=v;')
 replace('void nonlinear(Matrix& m,Vector& rhs,const Vector& x) const {','''static std::array<double,2> exponentialPair(double a,double b) {
        using Pair = double __attribute__((vector_size(16)));
        a=std::clamp(a,-80.,40.);b=std::clamp(b,-80.,40.);
        const double sa=a*1.4426950408889634074,sb=b*1.4426950408889634074;
        const int ka=int(sa+(sa>=0?.5:-.5)),kb=int(sb+(sb>=0?.5:-.5));
        const Pair x=Pair{a,b}-Pair{double(ka),double(kb)}*.69314718055994530942;
        const Pair one{1,1},half{.5,.5};
        const Pair p=one+x*(one+x*(half+x*(1./6+x*(1./24+x*(1./120+x*(1./720+x*(1./5040+x/40320)))))));
        const std::array<uint64_t,2> bits{uint64_t(ka+1023)<<52,uint64_t(kb+1023)<<52};
        Pair scale;std::memcpy(&scale,bits.data(),sizeof(scale));const Pair result=p*scale;
        return {result[0],result[1]};
    }
    void nonlinear(Matrix& m,Vector& rhs,const Vector& x) const {''')
 replace('const double ef=exponential(be/vt),er=exponential(bc/vt);','const auto pair=exponentialPair(be/vt,bc/vt);const double ef=pair[0],er=pair[1];')
 replace('double f=exponential(v/(s.diodeN*vt)),r=exponential(-v/(s.diodeN*vt));','const auto pair=exponentialPair(v/(s.diodeN*vt),-v/(s.diodeN*vt));double f=pair[0],r=pair[1];')
 processor=(ROOT/'OriginalProcessor.h').read_text().replace('"vendor/Circuit/AnalogCircuit.h"','"OptimizedCircuit.h"').replace('OriginalMuffDSP','OptimizedMuffDSP').replace('muff::circuit::AnalogCircuit','muff_opt::circuit::AnalogCircuit')
 return {'OptimizedCircuit.h':source,'OptimizedProcessor.h':processor}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
 for name,data in generated().items():
  path=ROOT/name
  if args.check:
   if not path.exists() or path.read_text()!=data:raise RuntimeError('Stale generated Muff: '+name)
  else:path.write_text(data)
if __name__=='__main__':main()
