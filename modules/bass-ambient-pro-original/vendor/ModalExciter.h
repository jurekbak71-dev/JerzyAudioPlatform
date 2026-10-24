// Jerzy Audio original DSP. No third-party Drum Foundry source included.
// Lightweight strike excitation + three damped second-order tuned modes.
// No allocations, mutexes or dynamic dispatch inside the audio callback.
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
namespace jerzy {
class ModalExciter {
    struct Mode {
        double a=0,b=0,y1=0,y2=0,norm=0,weight=0;
        void prepare(double hz,double decay,double sr,double w) noexcept {
            const double omega=6.283185307179586*std::clamp(hz,16.0,sr*.42)/sr;
            const double radius=std::exp(-1.0/(sr*std::max(.01,decay)));
            a=2.0*radius*std::cos(omega);b=radius*radius;
            norm=2.0*std::sin(omega); weight=w; y1=y2=0.0;
        }
        double next(double x) noexcept {
            const double y=x+a*y1-b*y2;
            y2=y1;y1=y;
            return y*norm*weight;
        }
        void reset() noexcept { y1=y2=0; }
    };
    std::array<Mode,3> modes{};
    double sr=48000;
    bool pending=false,active=false;
    uint64_t tailRemaining=0;
public:
    void prepare(double sampleRate) noexcept { sr=std::max(8000.0,sampleRate);reset(); }
    void reset() noexcept {
        for(auto& mode:modes)mode.reset();
        pending=active=false;tailRemaining=0;
    }
    void strike(double fundamental,double seconds,uint32_t identity=0) noexcept {
        // Partial ratios are deliberately inharmonic for richer body resonance.
        constexpr double ratios[3]={1.0,1.52,2.37};
        constexpr double life[3]={1.0,.72,.46};
        constexpr double weights[3]={.56,.29,.15};
        for(size_t i=0;i<modes.size();++i)
            modes[i].prepare(fundamental*ratios[i],seconds*life[i],sr,weights[i]);
        (void)identity;
        pending=active=true;
        tailRemaining=static_cast<uint64_t>(std::max(1.0,std::min(12.0,seconds*8.0))*sr);
    }
    double next() noexcept {
        if(!active)return 0;
        const double excite=pending?1.0:0.0;
        pending=false;
        double result=0;
        for(auto& m:modes)result+=m.next(excite);
        // Bounded feedback states are explicitly zeroed when the tail is inaudible.
        if(tailRemaining>0 && --tailRemaining==0)reset();
        if(!std::isfinite(result)) {reset();return 0;}
        return std::tanh(result*.6);
    }
};
class StrikeTransient {
    double sr=48000,env=0,coefficient=.99,phase=0;
    uint32_t noiseState=0x1a2b3c4du;
public:
    void prepare(double sampleRate) noexcept {
        sr=std::max(8000.0,sampleRate);
        coefficient=std::exp(-1.0/(sr*.003));
        reset();
    }
    void reset() noexcept {env=phase=0;}
    void trigger(uint32_t identity=1) noexcept {
        env=1;phase=0;noiseState^=identity+0x6d2b79f5u;
    }
    double next() noexcept {
        if(env<1e-7)return 0;
        noiseState^=noiseState<<13;noiseState^=noiseState>>17;noiseState^=noiseState<<5;
        const double noise=double(noiseState>>8)*(2.0/16777215.0)-1.0;
        phase+=2*3.141592653589793*1700.0/sr;
        if(phase>=2*3.141592653589793)phase-=2*3.141592653589793;
        const double x=(.67*std::sin(phase)+.33*noise)*env;
        env*=coefficient;
        return x;
    }
};
} // namespace jerzy
