#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>
#include <atomic>
#include <memory>
#include "ModalExciter.h"

namespace jerzy {
constexpr double pi = 3.14159265358979323846;
template<class T> T clamp(T x, T a, T b) { return std::max(a, std::min(b, x)); }
inline double hz(double n) { return 440.0 * std::exp2((n - 69.0) / 12.0); }
inline uint32_t hash(uint32_t x) { x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; return x ^ (x >> 16); }
inline double unit(uint32_t seed, uint32_t index) { return double(hash(seed ^ hash(index))) / 4294967296.0; }
inline double smooth(double a, double b, double t) { t = clamp(t, 0.0, 1.0); return a + (b-a)*t*t*(3.0-2.0*t); }
struct Stereo { double l=0, r=0; Stereo operator+(Stereo b) const { return {l+b.l,r+b.r}; } Stereo operator*(double g) const { return {l*g,r*g}; } };

struct FXParameters {
    bool fxDrive=true, fxChorus=true, fxDelay=true, fxGrain=false, fxReverb=true, fxWidth=true, freeze=false;
    std::array<int,6> order{{0,1,2,3,4,5}};
    double compThreshold=-18, compRatio=3, compAttack=.015, compRelease=.15, compMakeup=0, fxSaturation=.2;
    double chorusMix=.2, chorusRate=.3, chorusDepth=.5; int chorusMode=0;
    double delayMix=.2, feedback=.35, delayTone=4500, wow=.15, flutter=.12, damage=0;
    int delayMode=2, delayDivision=2, delayType=1;
    double grainSize=.15, grainMix=.3, grainPitch=0, grainScatter=.4;
    double reverbMix=.25, reverbSize=.7, reverbDamp=.5, width=1;
};

struct DrumSettings { double level=.7, drive=.1, tone=.5, cutoff=12000, decay=.2, pan=0; bool enabled=true; };
struct Parameters : FXParameters {
    bool modularMidi=false;int performanceSource=0;int bassMidiMode=1,padMidiMode=0,arpMidiMode=1,krellMidiMode=1,drumsMidiMode=0;
    bool bass=true, pad=false, direct=false, latch=false, restart=false, evolve=false, legato=false;
    int model=0, bassWave=0, style=0, scale=1, division=2, bars=1, meter=0, numerator=4, denominator=4;
    int seed=71, chord=1, padMode=1, engine1=0, engine2=1;
    int guitarArticulation=0;double guitarTone=.6,guitarDamping=.2,guitarDecay=2.5,guitarPickPosition=.22;
    double density=.75, movement=.4, gate=.55, swing=0, variation=.15, slide=.3, accent=.5;
    double bassLevel=.6, cutoff=1200, resonance=.35, filterEnv=.65, drive=.2;
    double bassAttack=.003, bassDecay=.25, bassSustain=.25, bassRelease=.1, glide=.09, sub=.3, pulse=.5;
    double bassBody=0, bassAttackTransient=0;
    double padLevel=.45, padAttack=2, padDecay=3, padSustain=.8, padRelease=5, padCutoff=2600;
    double padBlend=.5, padDrift=.25, motion=.4, evolution=4, spread=.7;
    double padBody=0, padAttackTransient=0;
    double bassFX=.15, padFX=1, master=.65, masterFX=0;
    bool limiter=true;
    bool composerEnabled=false,composerPlaying=false,composerSongMode=true,composerLoop=false,separateOutputs=false,midiPlayback=false;
    int composerScene=1;double composerIntensity=1;
    FXParameters padRack, masterRack,arpRack,drumsRack,krellRack;
    double arpFX=0,drumsFX=0,krellFX=0;
    bool krell=false,harmonyLink=false;int harmonyRoot=36,krellEngine=0;
    double krellLevel=.35,krellCycleMin=.6,krellCycleMax=5,krellAttack=.5,krellRelease=1.5,krellCutoff=3200,krellResonance=.2,krellTimbre=.5,krellStereo=.85,krellPitchRange=14;
    bool fxEnabled=true, autoPlay=false, arp=false, drums=false;
    int autoRoot=36, autoHarmony=0, harmonyBars=4; double internalTempo=120;
    double humanize=.2, fill=.2; int bassOctaves=2;
    double padDetune=9, padShimmer=.2, padResonance=.18;
    double krellMin=.8, krellMax=9, krellSpace=.2, krellRange=14;
    int arpModel=0, arpPattern=0, arpDivision=2, arpOctaves=2, arpSteps=16, arpPulses=12;
    int arpRange=7, arpPanMode=1;
    double arpGate=.55, arpGateRandom=.2, arpPitchRandom=0, arpSwing=0, arpVelocity=.2;
    double arpWidth=.8, arpLevel=.35, arpAttack=.003, arpDecay=.3, arpSustain=.15, arpRelease=.2;
    double arpCutoff=4200, arpResonance=.2, arpFilterEnv=.5;
    int drumLength=16, drumDivision=2, drumAux=0;
    double drumSwing=0, drumLevel=.6, drumHumanize=.15;
    std::array<DrumSettings,4> drumSounds{{DrumSettings{},DrumSettings{},DrumSettings{.7,.1,.5,12000,.06,0,true},DrumSettings{}}};
    std::array<std::array<int,64>,4> drumGrid=defaultDrumGrid();
    double mix0Gain=1;
    double mix0Pan=0;
    double mix0Delay=0;
    double mix0Reverb=0;
    bool mix0Mute=false;
    bool mix0Solo=false;
    double mix1Gain=1;
    double mix1Pan=0;
    double mix1Delay=0;
    double mix1Reverb=0;
    bool mix1Mute=false;
    bool mix1Solo=false;
    double mix2Gain=1;
    double mix2Pan=0;
    double mix2Delay=0;
    double mix2Reverb=0;
    bool mix2Mute=false;
    bool mix2Solo=false;
    double mix3Gain=1;
    double mix3Pan=0;
    double mix3Delay=0;
    double mix3Reverb=0;
    bool mix3Mute=false;
    bool mix3Solo=false;
    double mix4Gain=1;
    double mix4Pan=0;
    double mix4Delay=0;
    double mix4Reverb=0;
    bool mix4Mute=false;
    bool mix4Solo=false;
    double mix5Gain=1;
    double mix5Pan=0;
    double mix5Delay=0;
    double mix5Reverb=0;
    bool mix5Mute=false;
    bool mix5Solo=false;
    double mix6Gain=1;
    double mix6Pan=0;
    double mix6Delay=0;
    double mix6Reverb=0;
    bool mix6Mute=false;
    bool mix6Solo=false;
    double sendDelayReturn=.7,sendReverbReturn=.7,sendFeedback=.35,sendRoom=.7;
    int sendDivision=1,clockSource=0;
    bool sendDelayPower=true,sendReverbPower=true,transportRun=false,sceneMixer=false;
    double mix7Gain=1,mix7Pan=0,mix7Delay=0,mix7Reverb=0;bool mix7Mute=false,mix7Solo=false;
    struct Mix { double gain,pan,delay,reverb;bool mute,solo; };
    Mix mix(int track) const {
        switch(track) {
        case 0:return {mix0Gain,mix0Pan,mix0Delay,mix0Reverb,mix0Mute,mix0Solo};
        case 1:return {mix1Gain,mix1Pan,mix1Delay,mix1Reverb,mix1Mute,mix1Solo};
        case 2:return {mix2Gain,mix2Pan,mix2Delay,mix2Reverb,mix2Mute,mix2Solo};
        case 3:return {mix3Gain,mix3Pan,mix3Delay,mix3Reverb,mix3Mute,mix3Solo};
        case 4:return {mix4Gain,mix4Pan,mix4Delay,mix4Reverb,mix4Mute,mix4Solo};
        case 5:return {mix5Gain,mix5Pan,mix5Delay,mix5Reverb,mix5Mute,mix5Solo};
        case 6:return {mix6Gain,mix6Pan,mix6Delay,mix6Reverb,mix6Mute,mix6Solo};
        case 7:return {mix7Gain,mix7Pan,mix7Delay,mix7Reverb,mix7Mute,mix7Solo};
        default:return {1,0,0,0,false,false};
        }
    }
    static std::array<std::array<int,64>,4> defaultDrumGrid() {
        std::array<std::array<int,64>,4> grid{};
        for(int k=0;k<64;++k) { grid[0][k]=(k%4==0?110:0);grid[1][k]=(k%8==4?100:0);grid[2][k]=(k%2==0?75:0);grid[3][k]=(k%16==12?70:0); }
        return grid;
    }

};

class Envelope {
    enum Stage { Off, Attack, Decay, Sustain, Release } stage=Off;
    double value=0, rate=48000, releaseStart=0, elapsed=0;
public:
    void prepare(double sr) { rate=sr; reset(); }
    void reset() { stage=Off; value=elapsed=0; }
    void on() { stage=Attack; elapsed=0; }
    void off() { if (stage!=Off && stage!=Release) { stage=Release; releaseStart=value; elapsed=0; } }
    bool active() const { return stage!=Off; }
    double next(double a,double d,double s,double r) {
        const double dt=1.0/rate; elapsed+=dt;
        switch(stage) {
        case Off: value=0; break;
        case Attack: value += (1.0-value)*(1.0-std::exp(-6.0*dt/std::max(a,.0002))); if(elapsed>=a) { value=1; stage=Decay; elapsed=0; } break;
        case Decay: value=s+(1-s)*std::exp(-5.0*elapsed/std::max(d,.001)); if(elapsed>=d) { value=s; stage=Sustain; } break;
        case Sustain: value=s; break;
        case Release: value=releaseStart*std::exp(-7.0*elapsed/std::max(r,.001)); if(elapsed>=r) { stage=Off; value=0; } break;
        }
        return value;
    }
};

inline double blep(double t,double dt) {
    if(t<dt) { t/=dt; return t+t-t*t-1; }
    if(t>1-dt) { t=(t-1)/dt; return t*t+t+t+1; }
    return 0;
}
struct Oscillator {
    double phase=0;
    double next(double frequency,double sr,int shape,double pw=.5) {
        const double dt=clamp(frequency/sr,.0000001,.4), t=phase;
        phase+=dt; phase-=std::floor(phase);
        if(shape==0) return 2*t-1-blep(t,dt);
        if(shape==1) { const double edge=t-pw-std::floor(t-pw); return (t<pw?1.0:-1.0)+blep(t,dt)-blep(edge,dt); }
        if(shape==2) return std::sin(2*pi*t);
        // Smooth triangle: no discontinuity, modest harmonics.
        return (8/(pi*pi))*(std::sin(2*pi*t)-std::sin(6*pi*t)/9+std::sin(10*pi*t)/25);
    }
};

// Nonlinear four-stage feedback ladder, run at 2x voice rate.
struct Ladder {
    std::array<double,4> z{};
    double process(double x,double cutoff,double resonance,double sr,double saturation) {
        double g=1-std::exp(-2*pi*clamp(cutoff,20.0,sr*.18)/sr);
        x=std::tanh(x*(1+saturation*3)-clamp(resonance,0.0,.96)*3.7*z[3]);
        for(auto& s:z) { s+=g*(std::tanh(x)-std::tanh(s)); x=s; }
        return z[3]*(1+resonance*.35);
    }
    void reset() { z.fill(0); }
};

struct Step { int degree=0, octave=0,semitones=0; double velocity=.8, length=.5; bool rest=false, accent=false, slide=false; };
inline double divisionBeats(int i) {
    constexpr double v[]{1,.5,.25,.125,1.0/3,1.0/6,.375};
    return v[clamp(i,0,6)];
}
inline int scaleOffset(int degree,int scale) {
    static constexpr int scales[5][7]={{0,2,4,5,7,9,11},{0,2,3,5,7,8,10},{0,2,3,5,7,9,10},{0,2,3,5,7,8,11},{0,3,5,7,10,12,15}};
    const int count=scale==4?5:7;
    int octave=int(std::floor(double(degree)/count));
    int index=degree-octave*count;
    return scales[clamp(scale,0,4)][index]+12*octave;
}
inline Step makeStep(const Parameters& p,int64_t index,int count) {
    int k=int((index%count+count)%count), m=k%16;
    uint32_t cycle=p.evolve?uint32_t(index/count):0;
    uint32_t salt=uint32_t(p.seed)^hash(cycle);
    static constexpr int motifs[5][16]={
        {0,0,0,4,0,0,2,0,0,0,4,0,0,2,4,6},
        {0,0,4,4,0,0,4,0,0,0,4,4,0,2,4,0},
        {0,0,2,0,4,0,6,2,0,4,0,2,6,0,4,2},
        {0,0,4,0,2,0,0,6,0,4,2,0,0,6,4,2},
        {0,0,0,0,0,4,0,0,0,0,2,0,0,0,4,0}};
    static constexpr double weights[5][16]={
        {1,.4,1,.6,1,.4,1,.6,1,.4,1,.6,1,.4,1,.8},
        {1,.25,.8,.25,1,.25,.8,.4,1,.25,.8,.25,1,.4,.8,.5},
        {1,.65,.8,.4,.85,.7,.5,.9,.8,.5,.9,.7,.5,.85,.6,.8},
        {1,.15,.45,.9,.2,.65,.95,.3,.7,.2,.85,.4,.15,.9,.3,.75},
        {1,.2,.7,.2,1,.3,.65,.2,1,.2,.7,.2,1,.3,.7,.4}};
    int style=clamp(p.style,0,4);
    Step s; s.degree=unit(salt,k*11+1)<p.movement?motifs[style][m]:0;
    s.octave=(style==0 && m%4==2)?1:0;
    if(unit(salt,k*11+2)<p.variation*p.movement) s.degree=int(unit(salt,k*11+3)*7);
    s.rest=unit(salt,k*11+4)>clamp(p.density*weights[style][m]*1.3,0.0,1.0);
    if(k==0 && p.density>0) s.rest=false;
    s.accent=unit(salt,k*11+5)<p.accent*(m%4==0?1.0:.65);
    s.slide=unit(salt,k*11+6)<p.slide && !s.rest;
    s.velocity=s.accent?1.0:(style==3?.45+.4*unit(salt,k*11+7):.75);
    s.length=clamp(p.gate*(style==3?.65:1.0),.03,1.0);
    if(p.style>=5&&p.style<=9) {
        static constexpr int extra[5][16]={
            {0,0,4,0,0,2,0,6,0,0,4,0,2,0,6,4},
            {0,0,0,4,0,0,2,0,0,4,0,0,6,0,2,0},
            {0,4,0,2,0,6,0,4,0,2,0,4,0,6,2,4},
            {0,0,0,0,2,0,0,4,0,0,6,0,0,4,2,0},
            {0,2,4,6,4,2,0,-1,0,2,4,2,6,4,2,0}};
        s.degree=unit(salt,k*11+1)<p.movement?extra[clamp(p.style-5,0,4)][m]:0;
        s.rest=unit(salt,k*11+4)>p.density*(m%4==0?1.0:(p.style==8?.45:.85));
        s.slide=unit(salt,k*11+6)<p.slide;
        s.length=clamp(p.gate*(p.style==7?.5:1.0),.03,1.0);
    }
    if(p.style>=10){
        static constexpr int rock[]{0,0,0,0,4,0,0,4,0,0,0,0,4,4,2,4};
        static constexpr int metal[]{0,0,0,0,0,0,1,0,0,0,0,0,4,3,1,0};
        static constexpr int punk[]{0,0,0,0,0,0,4,4,0,0,0,0,4,4,4,4};
        static constexpr int blues[]{0,0,4,4,7,7,9,9,10,10,9,9,7,7,6,3};
        const bool pulse=p.style==11?(m%4!=1):(m%2==0);
        s.rest=!pulse||unit(salt,k*11+4)>p.density;
        s.degree=unit(salt,k*11+1)<p.movement?(p.style==10?rock[m]:p.style==11?metal[m]:p.style==12?punk[m]:0):0;
        s.semitones=p.style==13&&unit(salt,k*11+1)<p.movement?blues[m]:0;s.octave=0;
        s.slide=false;s.accent=m%4==0;s.velocity=s.accent?1:.82;
        s.length=clamp(p.gate*(p.style==11?.55:p.style==12?.85:1.0),.03,1.0);
    }
    if(k>=count-std::max(1,count/4)&&unit(salt,k*17+71)<p.fill) {
        s.rest=false;s.degree+=int(unit(salt,k*17+72)*4);s.length*=.65;
    }
    if(unit(salt,k*13+90)<p.movement*.3) s.octave=int(unit(salt,k*13+91)*p.bassOctaves);
    s.velocity*=1-p.humanize*.55*unit(salt,k*13+92);
    return s;
}

class BassVoice {
    double rate=48000, pitch=36,target=36, elapsed=0, filterLevel=0, velocity=.8;
    bool connected=false, accented=false;
    Oscillator o1,o2,subOsc; Ladder filter; Envelope env;
    ModalExciter body; StrikeTransient strike; bool excitePending=false;uint32_t hitCounter=0;
    std::vector<double> string;size_t stringCursor=0;uint32_t plucks=0;bool pluckPending=true;double stringPrevious=0,guitarBody=0;
    double guitar(const Parameters& p,double frequency){
        const double damping=.5*(1-p.guitarTone*.8);
        const double delay=clamp(rate/frequency-damping,2.0,double(string.size()-2));
        if(pluckPending){const int period=std::max(2,int(std::lround(delay)));const int pick=std::max(1,int(period*p.guitarPickPosition));const uint32_t seed=hash(uint32_t(p.seed)^++plucks);
            for(size_t i=0;i<string.size();++i){const int phase=int(i%size_t(period));const double a=unit(seed,uint32_t(phase))*2-1,b=unit(seed,uint32_t((phase+pick)%period))*2-1;string[i]=(a-b)*.55;}
            stringCursor=0;stringPrevious=guitarBody=0;pluckPending=false;
        }
        double position=double(stringCursor)-delay;if(position<0)position+=double(string.size());if(position>=double(string.size()))position=0;
        const size_t i=size_t(position);const double fraction=position-double(i);const double value=string[i]*(1-fraction)+string[(i+1)%string.size()]*fraction;
        const double decay=p.guitarDecay*(1-p.guitarDamping*.92);
        const double feedback=std::exp(-6.907755/(std::max(.08,decay)*frequency));
        string[stringCursor]=((1-damping)*value+damping*stringPrevious)*feedback;stringPrevious=value;stringCursor=(stringCursor+1)%string.size();
        guitarBody+=(value-guitarBody)*(1-std::exp(-2*pi*180/rate));
        const double attack=p.guitarArticulation==0?.08:p.guitarArticulation==1?.22:.5;
        const double noise=(unit(uint32_t(p.seed)+plucks,uint32_t(elapsed*rate))*2-1)*std::exp(-elapsed/(p.guitarArticulation==2?.012:.004))*attack;
        double sound=value*(p.guitarArticulation==0?.8:1.1)+guitarBody*.45+noise;
        sound=filter.process(sound,p.cutoff*std::exp2(p.filterEnv*.7),p.resonance*.4,rate,p.drive*.5);
        elapsed+=1/rate;return sound;
    }
public:
    bool active() const {return env.active();}

    void prepare(double sr) { rate=sr;string.assign(size_t(std::ceil(sr/hz(12)))+8,0);env.prepare(sr);body.prepare(sr);strike.prepare(sr);reset(); }
    void reset() { env.reset(); filter.reset(); o1={};o2={};subOsc={};elapsed=filterLevel=0;connected=false;pluckPending=true;stringCursor=0;stringPrevious=guitarBody=0;plucks=0;body.reset();strike.reset();excitePending=false;hitCounter=0; }
    void note(int n,double v,bool legato,bool accent) {
        target=clamp(double(n),12.0,108.0);velocity=v;accented=accent;
        if(!legato || !env.active()) { pitch=target;env.on();filterLevel=1;elapsed=0;pluckPending=true;excitePending=true; }
        connected=legato;
    }
    void off() { env.off();connected=false; }
    double next(const Parameters& p,double bend) {
        if(!env.active()) return 0;
        if(excitePending) {body.strike(hz(target),.10+p.bassDecay*1.5,++hitCounter);strike.trigger(hitCounter);excitePending=false;}
        double amp=env.next(p.bassAttack,p.bassDecay,p.bassSustain,p.bassRelease);
        double glideTime=connected?p.glide:.001;
        pitch+=(target-pitch)*(1-std::exp(-1/(rate*std::max(glideTime,.001))));
        filterLevel*=std::exp(-1/(rate*std::max(.025,p.bassDecay*(accented?1.4:1))));
        if(p.model==3) {
            const double legacy=guitar(p,hz(pitch+bend))*amp*velocity*.9;
            if(p.bassBody<=0&&p.bassAttackTransient<=0)return legacy;
            const double resonant=p.bassBody>0?body.next():0.0;
            const double transient=p.bassAttackTransient>0?strike.next():0.0;
            return legacy+velocity*(resonant*p.bassBody*.24*amp+transient*p.bassAttackTransient*.12);
        }
        double result=0;
        for(int i=0;i<2;++i) {
            const double f=hz(pitch+bend);
            if(p.model==1) {
                const double sweep=24*std::exp(-elapsed/.012);
                double body=o1.next(hz(pitch+bend+sweep),rate*2,2);
                double click=std::sin(2*pi*1800*elapsed)*std::exp(-elapsed/.0025)*.22;
                double x=std::tanh((body+click)*(1+3*p.drive))/(1+p.drive);
                double fc=p.cutoff*std::exp2(filterLevel*p.filterEnv*(accented?4.5:3.5));
                result+=filter.process(x,fc,p.resonance,rate*2,p.drive*.3);
            } else {
                double x=o1.next(f,rate*2,p.bassWave,p.pulse);
                if(p.model==2) x=.6*x+.4*o2.next(f*1.003,rate*2,1-p.bassWave,p.pulse);
                x=x*.7+subOsc.next(f*.5,rate*2,2)*p.sub*.45;
                double fc=p.cutoff*std::exp2(filterLevel*p.filterEnv*(accented?5.5:4));
                result+=filter.process(x,fc,p.resonance,rate*2,p.drive);
            }
            elapsed+=1/(rate*2);
        }
        const double legacy=result*.5*amp*velocity*.7;
        if(p.bassBody<=0&&p.bassAttackTransient<=0)return legacy;
        const double resonant=p.bassBody>0?body.next():0.0;
        const double transient=p.bassAttackTransient>0?strike.next():0.0;
        return legacy+velocity*(resonant*p.bassBody*.24*amp+transient*p.bassAttackTransient*.12);
    }
};

struct PadVoice {
    Oscillator a,b,c,d,shimmer; Ladder fl,fr; Envelope env;
    ModalExciter body; StrikeTransient strike; bool excitePending=false;
    double note=60, pan=0, age=0, lifetime=4, velocity=1, wait=0, attackScale=1, decayScale=1, releaseScale=1, motionRate=1; bool releasing=false;
    uint32_t identity=0,eventId=0;
    void prepare(double sr) { env.prepare(sr);fl.reset();fr.reset();body.prepare(sr);strike.prepare(sr);age=0;releasing=false;excitePending=false; }
    void start(double n,double position,uint32_t id,double v=1) { note=n;pan=position;identity=id;age=0;releasing=false;velocity=v;wait=0;attackScale=decayScale=releaseScale=motionRate=1;env.on();excitePending=true; }
    void off() { env.off(); releasing=true; }
    double engine(Oscillator& o,int mode,double f,double sr,double motion,double grain) {
        if(mode==0) return o.next(f,sr,0);
        if(mode==1) return o.next(f,sr,1,.5+.2*motion);
        double t=o.phase; o.phase+=clamp(f/sr,0.0,.3);o.phase-=std::floor(o.phase);
        if(mode==2) return .6*std::sin(2*pi*t)+.25*std::sin(4*pi*t+motion*2)+.15*std::sin(6*pi*t-motion);
        if(mode==3) return std::sin(2*pi*t+(1.5+motion)*std::sin(4*pi*t));
        // Procedural granular-style spectral oscillator, not sample playback.
        double window=.55+.45*std::cos(2*pi*age/std::max(.025,grain));
        return window*(.7*std::sin(2*pi*t)+.3*std::sin(2*pi*t*3+motion));
    }
    Stereo next(const Parameters& p,double sr,double bend) {
        if(!env.active()) return {};
        if(age<wait) {age+=1/sr;return {};}
        if(excitePending) {body.strike(hz(note+bend),.3+p.padRelease*.8,identity);strike.trigger(identity);excitePending=false;}
        double amp=env.next(p.padAttack*attackScale,p.padDecay*decayScale,p.padSustain,p.padRelease*releaseScale);
        age+=1/sr;
        double period=std::max(.5,p.evolution), pos=age*motionRate/period;
        uint32_t segment=uint32_t(std::floor(pos));
        double random=smooth(unit(identity,segment)*2-1,unit(identity,segment+1)*2-1,pos-segment);
        double modulation=p.motion*(.5*random+.5*std::sin(age*.37+pan*3));
        double cents=p.padDrift*(random*7+std::sin(age*.17+pan)*3);
        double x=0,stereoRight=0;
        for(int i=0;i<2;++i) {
            double x1=engine(a,p.engine1,hz(note+bend+cents/100),sr*2,modulation,p.padRack.grainSize);
            double x2=engine(b,p.engine2,hz(note+bend-cents/120+.045),sr*2,-modulation,p.padRack.grainSize);
            double u1=engine(c,p.engine1,hz(note+bend+cents/100+p.padDetune/100),sr*2,modulation,p.padRack.grainSize);
            double u2=engine(d,p.engine2,hz(note+bend-cents/120-p.padDetune/100),sr*2,-modulation,p.padRack.grainSize);
            double upper=shimmer.next(hz(note+bend+12),sr*2,2)*p.padShimmer*.3;
            double left=(.65*x1+.35*u1)*(1-p.padBlend)+(.65*x2+.35*u2)*p.padBlend+upper;
            double right=(.65*u1+.35*x1)*(1-p.padBlend)+(.65*u2+.35*x2)*p.padBlend+upper;
            x+=fl.process(left,p.padCutoff*std::exp2(modulation*2),p.padResonance,sr*2,.12);
            right=fr.process(right,p.padCutoff*std::exp2(-modulation*1.6),p.padResonance,sr*2,.12);
            stereoRight+=right;
        }
        const double modal=p.padBody>0?body.next()*p.padBody*.50:0.0;
        const double transient=p.padAttackTransient>0?strike.next()*p.padAttackTransient*.18:0.0;
        x+=modal+transient;stereoRight+=modal*.87+transient*.95;
        double position=clamp(pan*p.spread+modulation*.12,-1.0,1.0);
        double angle=(position+1)*pi*.25;
        return {x*.5*amp*.38*velocity*std::cos(angle),stereoRight*.5*amp*.38*velocity*std::sin(angle)};
    }
};

class DelayLine {
    std::vector<double> data; size_t cursor=0;
public:
    void prepare(size_t size) { data.assign(std::max(size,size_t(8)),0);cursor=0; }
    size_t memoryBytes() const {return data.capacity()*sizeof(double);}
    void clear() { std::fill(data.begin(),data.end(),0);cursor=0; }
    void push(double x) { data[cursor]=x;cursor=(cursor+1)%data.size(); }
    double read(double delay) const {
        if(data.empty()) return 0;
        delay=clamp(delay,1.0,double(data.size()-2));
        double position=double(cursor)-delay;
        if(position<0) position+=double(data.size());
        // Floating-point wrap can round a tiny negative position to exactly size.
        if(position>=double(data.size())) position=0;
        size_t a=size_t(position);double frac=position-double(a);
        return data[a]*(1-frac)+data[(a+1)%data.size()]*frac;
    }
};

class FXRack {
public: int allocationMask=0;
private:
    double sr=48000, clock=0, detector=0, delayLpf=0,delayRpf=0, delayTime=12000;
    DelayLine delayL,delayR,chorusL,chorusR,grainL,grainR;
    std::array<DelayLine,8> room;
    std::array<double,8> damp{};
    std::array<double,4> grainPhase{{0,.25,.5,.75}};
    double grainAvailable=0;
    static constexpr std::array<double,8> roomSeconds{{.0297,.0371,.0411,.0437,.0307,.0353,.0399,.0479}};
    Stereo driveFX(Stereo x,const FXParameters& p) {
        double level=std::max(std::abs(x.l),std::abs(x.r));
        double tau=level>detector?p.compAttack:p.compRelease;
        detector+=(level-detector)*(1-std::exp(-1/(sr*std::max(.0001,tau))));
        double db=20*std::log10(std::max(detector,1e-9));
        double over=db-p.compThreshold,knee=6, reduction=0;
        if(over>knee*.5) reduction=over*(1-1/p.compRatio);
        else if(over>-knee*.5) reduction=(1-1/p.compRatio)*(over+knee*.5)*(over+knee*.5)/(2*knee);
        double gain=std::pow(10,(p.compMakeup-reduction)/20);
        double amount=1+p.fxSaturation*5;
        return {std::tanh(x.l*gain*amount)/std::sqrt(amount),std::tanh(x.r*gain*amount)/std::sqrt(amount)};
    }
    Stereo chorusFX(Stereo x,const FXParameters& p) {
        double base=p.chorusMode==1?.002:.012;
        double depth=(p.chorusMode==1?.0017:.004)*p.chorusDepth;
        double rate=p.chorusMode==2?.65:p.chorusRate;
        double dl=(base+depth*std::sin(2*pi*clock*rate))*sr;
        double dr=(base+depth*std::sin(2*pi*clock*rate+pi*.5))*sr;
        Stereo wet{chorusL.read(dl),chorusR.read(dr)};
        chorusL.push(x.l+(p.chorusMode==1?wet.l*.45:0));chorusR.push(x.r+(p.chorusMode==1?wet.r*.45:0));
        return x*(1-p.chorusMix)+wet*p.chorusMix;
    }
    Stereo delayFX(Stereo x,const FXParameters& p,double bpm) {
        double target=divisionBeats(p.delayDivision)*60/bpm*sr;
        delayTime+=(target-delayTime)*.0005;
        double wander=smooth(unit(710,uint32_t(clock/2)),unit(710,uint32_t(clock/2)+1),std::fmod(clock/2,1.0))*2-1;
        double flutter=(std::sin(clock*73)+.4*std::sin(clock*113))*p.flutter*.0012;
        double modulation=p.delayType==0?0:p.wow*.008*wander+flutter;
        Stereo wet{delayL.read(delayTime*(1+modulation)),delayR.read(delayTime*(p.delayMode==1?1.013:1)*(1-modulation*.7))};
        double coefficient=1-std::exp(-2*pi*clamp(p.delayTone,200.0,sr*.2)/sr);
        delayLpf+=coefficient*(wet.l-delayLpf);delayRpf+=coefficient*(wet.r-delayRpf);
        double damage=p.delayType==0?1:1-p.damage*.85*(.5+.5*std::sin(clock*19+wander*11));
        wet={delayLpf*damage,delayRpf*damage};
        auto colour=[&](double v){ return p.delayType==0?v:std::tanh(v*1.35)/1.35; };
        if(p.delayMode==2) { delayL.push(colour(x.l+wet.r*p.feedback));delayR.push(colour(x.r+wet.l*p.feedback)); }
        else if(p.delayMode==0) { double mono=.5*(x.l+x.r)+.5*(wet.l+wet.r)*p.feedback;delayL.push(colour(mono));delayR.push(colour(mono));wet.r=wet.l; }
        else { delayL.push(colour(x.l+wet.l*p.feedback));delayR.push(colour(x.r+wet.r*p.feedback)); }
        return x*(1-p.delayMix)+wet*p.delayMix;
    }
    Stereo grainFX(Stereo x,const FXParameters& p) {
        if(!p.freeze) { grainL.push(x.l);grainR.push(x.r);grainAvailable=std::min(grainAvailable+1,sr*3.5); }
        double length=std::max(64.0,p.grainSize*sr),ratio=std::exp2(p.grainPitch/12);
        Stereo wet{}; double total=0;
        for(size_t k=0;k<grainPhase.size();++k) {
            double phase=grainPhase[k];double w=.5-.5*std::cos(2*pi*phase);
            double offset=sr*(.07+p.grainScatter*(.1+.09*double(k)));
            double distance=offset+length*(ratio>=1? (1-phase)*(ratio-1):phase*(1-ratio));
            // Frozen buffer still scans; normal mode pitch uses moving write cursor.
            if(p.freeze) distance=offset+phase*length*ratio;
            wet.l+=grainL.read(distance)*w;wet.r+=grainR.read(distance+double(k)*11)*w;total+=w;
            grainPhase[k]+=1/length;grainPhase[k]-=std::floor(grainPhase[k]);
        }
        if(grainAvailable<sr*.05) wet={};
        return x*(1-p.grainMix)+wet*(p.grainMix/std::max(total,.001));
    }
    Stereo reverbFX(Stereo x,const FXParameters& p) {
        std::array<double,8> out{};
        double sum=0;
        for(size_t k=0;k<8;++k) {
            out[k]=room[k].read(roomSeconds[k]*sr*(.65+p.reverbSize*.9));
            damp[k]+=(out[k]-damp[k])*(.08+.8*(1-p.reverbDamp));sum+=damp[k];
        }
        double feedback=.55+.4*p.reverbSize;
        // Householder feedback matrix: orthogonal mixing, bounded feedback.
        for(size_t k=0;k<8;++k) room[k].push((sum*.25-damp[k])*feedback+(k%2?x.r:x.l)*.22);
        Stereo wet{(out[0]+out[2]-out[4]+out[6])*.5,(out[1]+out[3]-out[5]+out[7])*.5};
        return x*(1-p.reverbMix)+wet*p.reverbMix;
    }
public:
    void prepare(double sampleRate,int mask=63) {
        sr=sampleRate;allocationMask=mask;
        if(mask&4) { delayL.prepare(size_t(sr*5));delayR.prepare(size_t(sr*5)); }
        if(mask&2) {chorusL.prepare(size_t(sr*.06));chorusR.prepare(size_t(sr*.06));}
        if(mask&8) {grainL.prepare(size_t(sr*4));grainR.prepare(size_t(sr*4));}
        if(mask&16) for(auto& r:room) r.prepare(size_t(sr*.12));
        reset();
    }
    void reset() {
        delayL.clear();delayR.clear();chorusL.clear();chorusR.clear();grainL.clear();grainR.clear();
        for(auto& r:room) r.clear();
        damp.fill(0);clock=detector=delayLpf=delayRpf=grainAvailable=0;delayTime=sr*.25;
        grainPhase={{0,.25,.5,.75}};
    }
    size_t memoryBytes() const {size_t n=delayL.memoryBytes()+delayR.memoryBytes()+chorusL.memoryBytes()+chorusR.memoryBytes()+grainL.memoryBytes()+grainR.memoryBytes();for(const auto& r:room)n+=r.memoryBytes();return n;}
    Stereo process(Stereo x,const FXParameters& p,double bpm) {
        clock+=1/sr;std::array<bool,6> used{};
        // Sanitize automated permutations: no repeated processing or omitted FX.
        std::array<int,6> valid{};int n=0;
        for(int id:p.order) if(id>=0&&id<6&&!used[size_t(id)]) { used[size_t(id)]=true;valid[size_t(n++)]=id; }
        for(int id=0;id<6;++id) if(!used[size_t(id)]) valid[size_t(n++)]=id;
        for(int id:valid) {
            switch(id) {
            case 0: if(p.fxDrive) x=driveFX(x,p);break;
            case 1: if(p.fxChorus) x=chorusFX(x,p);break;
            case 2: if(p.fxDelay) x=delayFX(x,p,bpm);break;
            case 3: if(p.fxGrain) x=grainFX(x,p);break;
            case 4: if(p.fxReverb) x=reverbFX(x,p);break;
            case 5: if(p.fxWidth) { double mid=(x.l+x.r)*.5,side=(x.l-x.r)*.5*p.width;x={mid+side,mid-side}; } break;
            }
        }
        return x;
    }
};

#include "ProEngines.h"

class Instrument {
    struct Held { int note=-1, channel=1;double velocity=0;uint64_t serial=0;bool key=false,sustained=false; };
    std::array<Held,128*16> held{};
    std::array<bool,16> sustain{};
    std::array<double,16> bend{};
    uint64_t serial=0;
    int root=-1,rootChannel=1;double velocity=.8, rate=48000,bpm=120,anchor=0,padClock=0,lastPPQ=0;
    bool wasPlaying=false,havePosition=false,previousSlide=false,previousBass=true,previousPad=false,previousDirect=false;
    int64_t lastStep=std::numeric_limits<int64_t>::min(); double gateUntil=-1;
    uint32_t voiceSerial=0;
    BassVoice bass;
    std::array<PadVoice,12> pads;
    ManagedRack bassRack,padRack,masterRack,arpRack,krellRack;std::array<ManagedRack,4> drumRacks;ManagedRack delaySendRack,reverbSendRack;
    std::array<Stereo,2> returns{};
    Arpeggiator arpeggiator;DrumMachine drumMachine;KrellSynth krellSynth;
    std::array<Stereo,8> stems{};uint32_t externalBassId=0;
    std::array<int,128> arpNotes{};int arpNoteCount=0;
    bool previousArp=false,previousDrums=false,previousKrell=false;int midiRoot=-1;
    int padMidiRoot=-1,arpMidiRoot=-1,krellMidiRoot=-1,previousPadRoot=-1;
    double dcInL=0,dcInR=0,dcOutL=0,dcOutR=0;
    void setupKrell(PadVoice& v,const Parameters& p,uint32_t id) {
        const double lo=std::min(p.krellMin,p.krellMax),hi=std::max(p.krellMin,p.krellMax);
        v.lifetime=lo+(hi-lo)*unit(uint32_t(p.seed),id*19+1);
        v.wait=v.lifetime*p.krellSpace*unit(uint32_t(p.seed),id*19+7);
        v.attackScale=clamp(v.lifetime*(.12+.4*unit(uint32_t(p.seed),id*19+2))/p.padAttack,.05,8.0);
        v.releaseScale=clamp(v.lifetime*(.2+.6*p.krellSpace)/p.padRelease,.05,8.0);
        v.decayScale=.4+unit(uint32_t(p.seed),id*19+3)*2;
        v.motionRate=.3+unit(uint32_t(p.seed),id*19+4)*2;
        v.pan=unit(uint32_t(p.seed),id*19+5)*2-1;
        v.velocity*=.45+.55*unit(uint32_t(p.seed),id*19+6);
    }
    void startPad(const Parameters& p,bool replace,int suppliedRoot=-2) {
        const int padRoot=suppliedRoot==-2?root:suppliedRoot;
        if(replace) for(auto& v:pads) v.off();
        if(padRoot<0) return;
        constexpr int chords[8][4]={{0,4,7,12},{0,3,7,12},{0,7,12,19},{0,5,7,12},{0,3,7,10},{0,4,7,11},{0,3,10,14},{0,4,11,14}};
        for(int i=0;i<4;++i) {
            PadVoice* selected=nullptr;
            for(auto& v:pads) if(!v.env.active()) { selected=&v;break; }
            if(!selected) { double oldest=-1;for(auto& v:pads) if(v.releasing&&v.age>oldest) { selected=&v;oldest=v.age; } }
            if(!selected) selected=&*std::max_element(pads.begin(),pads.end(),[](const auto& a,const auto& b){return a.age<b.age;});
            double n=padRoot+chords[clamp(p.chord,0,7)][i];
            while(n<48) n+=12;
            while(n>84) n-=12;
            if(p.padMode==2) n+=12*(unit(uint32_t(p.seed),++voiceSerial)>.8?1:0);
            selected->start(n,-.8+i*.53,hash(uint32_t(p.seed)^++voiceSerial),velocity);
            selected->lifetime=p.evolution*(.5+unit(uint32_t(p.seed),voiceSerial));
            if(p.padMode==2) setupKrell(*selected,p,voiceSerial);
        }
        padClock=0;
    }
    void chooseRoot(const Parameters& p,double ppq) {
        Held* latest=nullptr;
        for(auto& h:held) if((h.key||h.sustained)&&(!p.modularMidi||h.channel==1)&&(!latest||h.serial>latest->serial)) latest=&h;
        if(p.modularMidi){
            auto channelRoot=[&](int channel){const Held* chosen=nullptr;for(const auto& h:held)if(h.channel==channel&&(h.key||h.sustained)&&(!chosen||h.serial>chosen->serial))chosen=&h;return chosen?chosen->note:-1;};
            padMidiRoot=channelRoot(2);arpMidiRoot=channelRoot(3);krellMidiRoot=channelRoot(4);
        }
        midiRoot=latest?latest->note:-1;
        arpNoteCount=0;
        // As-played ordering is stable by key serial, other patterns use pitch order.
        std::array<const Held*,128> keys{};
        for(const auto& h:held) if((h.key||h.sustained)&&(!p.modularMidi||h.channel==3)&&arpNoteCount<128) keys[size_t(arpNoteCount++)]=&h;
        std::sort(keys.begin(),keys.begin()+arpNoteCount,[&](const Held* a,const Held* b){return p.arpPattern==3?a->serial<b->serial:a->note<b->note;});
        for(int i=0;i<arpNoteCount;++i)arpNotes[size_t(i)]=keys[size_t(i)]->note;
        int nextRoot=latest?latest->note:(p.latch?root:(p.autoPlay?p.autoRoot:-1));
        int channel=latest?latest->channel:rootChannel;
        if(nextRoot!=root || channel!=rootChannel) {
            bool overlapping=root>=0;
            root=nextRoot;rootChannel=channel;
            velocity=latest?latest->velocity:velocity;
            if(root>=0) {
                if(p.restart) { anchor=ppq;lastStep=std::numeric_limits<int64_t>::min(); }
                if(p.direct) bass.note(root,velocity,p.legato&&overlapping,false);
                else { bass.note(root,velocity,false,false);gateUntil=ppq+divisionBeats(p.division)*p.gate;previousSlide=false; }
                if(p.pad&&!p.modularMidi) startPad(p,true);
            } else { bass.off();if(!p.modularMidi)for(auto& v:pads)v.off();previousSlide=false; }
        } else if(latest) velocity=latest->velocity;
    }
public:
    void prepare(double sr) { rate=sr;arpeggiator.prepare(sr);drumMachine.prepare(sr);krellSynth.prepare(sr);bass.prepare(sr);for(auto& v:pads)v.prepare(sr);bassRack.prepare(sr);padRack.prepare(sr);masterRack.prepare(sr);arpRack.prepare(sr);krellRack.prepare(sr);for(auto& rack:drumRacks)rack.prepare(sr);delaySendRack.prepare(sr);reverbSendRack.prepare(sr);reset(); }
    void reset() {
        arpeggiator.reset();drumMachine.reset();krellSynth.reset();arpNoteCount=0;midiRoot=-1;padMidiRoot=arpMidiRoot=krellMidiRoot=previousPadRoot=-1;
        held={};sustain.fill(false);bend.fill(0);serial=0;root=-1;rootChannel=1;bass.reset();
        for(auto& v:pads) { v.env.reset();v.fl.reset();v.fr.reset();v.a={};v.b={};v.c={};v.d={};v.shimmer={};v.age=0;v.body.reset();v.strike.reset();v.excitePending=false; }
        bassRack.reset();padRack.reset();masterRack.reset();arpRack.reset();krellRack.reset();for(auto& rack:drumRacks)rack.reset();delaySendRack.reset();reverbSendRack.reset();lastStep=std::numeric_limits<int64_t>::min();previousSlide=false;
        anchor=padClock=0;gateUntil=-1;havePosition=wasPlaying=false;voiceSerial=0;dcInL=dcInR=dcOutL=dcOutR=0;
        previousBass=true;previousPad=false;previousDirect=false;
    }
    static FXParameters sendPatch(const Parameters& p,bool delay) {
        FXParameters fx;fx.fxDrive=fx.fxChorus=fx.fxGrain=fx.fxWidth=false;fx.fxDelay=delay;fx.fxReverb=!delay;
        fx.delayMix=fx.reverbMix=1;fx.feedback=p.sendFeedback;fx.delayDivision=p.sendDivision;fx.delayType=0;fx.reverbSize=p.sendRoom;return fx;
    }
    void configureResources(const Parameters& p) {
        bool delayNeeded=false,reverbNeeded=false;for(int t=0;t<8;++t){delayNeeded|=p.mix(t).delay>0;reverbNeeded|=p.mix(t).reverb>0;}
        const bool source=p.bass||p.pad||p.arp||p.drums||p.krell;
        delaySendRack.configure(sendPatch(p,true),source&&delayNeeded&&p.fxEnabled&&p.sendDelayPower&&p.sendDelayReturn>0);
        reverbSendRack.configure(sendPatch(p,false),source&&reverbNeeded&&p.fxEnabled&&p.sendReverbPower&&p.sendReverbReturn>0);
        krellRack.configure(p.krellRack,p.fxEnabled&&p.krell&&p.krellFX>0);
        arpRack.configure(p.arpRack,p.fxEnabled&&p.arp&&p.arpFX>0);
        for(int lane=0;lane<4;++lane)drumRacks[size_t(lane)].configure(p.drumsRack,p.fxEnabled&&p.drums&&p.drumSounds[size_t(lane)].enabled&&p.drumsFX>0);
        bassRack.configure(p,p.fxEnabled&&p.bass&&p.bassFX>0);
        padRack.configure(p.padRack,p.fxEnabled&&p.pad&&p.padFX>0);
        masterRack.configure(p.masterRack,p.fxEnabled&&p.masterFX>0&&(p.bass||p.pad||p.arp||p.drums||p.krell));
    }
    void serviceResources() {bassRack.maintenance();padRack.maintenance();masterRack.maintenance();arpRack.maintenance();krellRack.maintenance();for(auto& rack:drumRacks)rack.maintenance();delaySendRack.maintenance();reverbSendRack.maintenance();}
    size_t fxMemoryBytes() const {size_t drums=0;for(const auto& rack:drumRacks)drums+=rack.memoryBytes();return drums+arpRack.memoryBytes()+krellRack.memoryBytes()+bassRack.memoryBytes()+padRack.memoryBytes()+masterRack.memoryBytes()+delaySendRack.memoryBytes()+reverbSendRack.memoryBytes();}
    const std::array<Stereo,2>& returnOutputs() const {return returns;}
    const std::array<Stereo,8>& stemOutputs() const {return stems;}
    void externalNote(int track,int note,double velocity,double pan,uint32_t id,bool on,bool accent=false,bool slide=false,const Parameters* patch=nullptr) {
        if(track==0){if(on){externalBassId=id;bass.note(note,velocity,slide,accent);}else if(externalBassId==id)bass.off();}
        else if(track==1){if(!on){for(auto& v:pads)if(v.eventId==id)v.off();return;}
            PadVoice* voice=nullptr;for(auto& v:pads)if(!v.env.active()){voice=&v;break;}
            if(!voice)voice=&*std::max_element(pads.begin(),pads.end(),[](const auto& a,const auto& b){return a.age<b.age;});
            voice->start(note,pan,hash(id),velocity);voice->eventId=id;
            if(patch&&patch->padMode==2)setupKrell(*voice,*patch,id);
        }else if(track==2){if(on)arpeggiator.trigger(note,velocity,pan,std::numeric_limits<double>::max(),id);else arpeggiator.noteOff(id);}
        else if(track==7){if(on)krellSynth.trigger(note,velocity,pan,id);else krellSynth.noteOff(id);}
        else if(on&&track>=3&&track<7)drumMachine.trigger(track-3,velocity);
    }
    int drumPosition() const {return drumMachine.stepDisplay();}
    int arpNoteDisplay() const {return arpeggiator.noteDisplay();}
    std::array<bool,8> activeTracks() const {
        std::array<bool,8> result{};result[7]=krellSynth.active();result[0]=bass.active();for(const auto& v:pads)result[1]|=v.env.active();result[2]=arpeggiator.active();
        for(int i=0;i<4;++i) result[size_t(i+3)]=drumMachine.active(i);
        return result;
    }
    void resetMidiPart(int track){int channel=track==0?1:track==1?2:track==2?3:track==7?4:10;for(auto& h:held)if(h.channel==channel)h=Held{};
        if(track==0){bass.reset();root=midiRoot=-1;externalBassId=0;previousSlide=false;gateUntil=-1;}
        else if(track==1){for(auto& v:pads)v.env.reset();padMidiRoot=previousPadRoot=-1;}
        else if(track==2){arpeggiator.reset();arpMidiRoot=-1;arpNoteCount=0;}
        else if(track==7){krellSynth.reset();krellMidiRoot=-1;}else drumMachine.reset();
    }
    int currentRoot() const {return root;}
    int64_t stepPosition() const { return lastStep; }
    void allOff() { arpeggiator.reset();drumMachine.reset();krellSynth.reset();midiRoot=-1;padMidiRoot=arpMidiRoot=krellMidiRoot=previousPadRoot=-1;arpNoteCount=0;held={};sustain.fill(false);root=-1;bass.off();for(auto& v:pads)v.off();previousSlide=false;gateUntil=-1; }
    void noteOn(int note,int channel,double v,const Parameters& p,double ppq) {
        if(note<0||note>127||channel<1||channel>16) return;
        if(v<=0) { noteOff(note,channel,p,ppq);return; }
        if(channel==10&&p.drums) {int lane=note==36?0:(note==38||note==40)?1:(note==42||note==44)?2:(note==39||note==46||note==45||note==47)?3:-1;if(lane>=0)drumMachine.trigger(lane,v);return;}
        bool sameRoot=root==note&&rootChannel==channel;
        auto& h=held[size_t((channel-1)*128+note)];h={note,channel,clamp(v,0.0,1.0),++serial,true,false};
        chooseRoot(p,ppq);
        // Repeated same-pitch MIDI notes still articulate in DIRECT mode.
        if(p.direct&&sameRoot) bass.note(note,v,p.legato,false);
    }
    void noteOff(int note,int channel,const Parameters& p,double ppq) {
        if(note<0||note>127||channel<1||channel>16) return;
        if(channel==10&&p.drums)return;
        auto& h=held[size_t((channel-1)*128+note)];
        if(h.note<0) return;
        h.key=false;h.sustained=sustain[size_t(channel-1)];chooseRoot(p,ppq);
    }
    void controller(int channel,int number,int value,const Parameters& p,double ppq) {
        if(channel<1||channel>16) return;
        if(number==64) {
            sustain[size_t(channel-1)]=value>=64;
            if(value<64) for(auto& h:held) if(h.channel==channel&&!h.key) h.sustained=false;
            chooseRoot(p,ppq);
        }
        if(number==120||number==123) allOff();
    }
    void pitchBend(int channel,int value) { if(channel>=1&&channel<=16) bend[size_t(channel-1)]=double(value-8192)/8192*2; }
    void beginBlock(double ppq,double tempo,bool playing) {
        bpm=clamp(tempo,20.0,400.0);
        if(havePosition && playing && (ppq<lastPPQ-.001 || ppq-lastPPQ>.25)) {
            // Host seek/loop: no stale keys or hanging scheduled gates. FX tails survive.
            allOff();lastStep=std::numeric_limits<int64_t>::min();anchor=0;
        }
        if(wasPlaying&&!playing) allOff();
        wasPlaying=playing;havePosition=true;lastPPQ=ppq;
    }
    Stereo next(const Parameters& p,double ppq,int hostNumerator=4,int hostDenominator=4,bool external=false,unsigned splitMask=0) {
        if(!external) {
        int generatedRoot=clamp(p.harmonyLink||p.performanceSource==2?p.harmonyRoot:p.autoRoot,12,96);const int baseRoot=generatedRoot;
        if(p.autoPlay&&p.autoHarmony>0) {
            const double beatsPerBar=double(p.meter?p.numerator:hostNumerator)*4/std::max(1,p.meter?p.denominator:hostDenominator);
            const auto section=int64_t(std::floor(ppq/(std::max(1,p.harmonyBars)*beatsPerBar)));
            static constexpr int changes[3][4]={{0,5,3,4},{0,3,4,0},{0,4,5,3}};
            int degree=p.autoHarmony==4?int(unit(uint32_t(p.seed),uint32_t(section))*7):changes[clamp(p.autoHarmony-1,0,2)][size_t((section%4+4)%4)];
            generatedRoot+=scaleOffset(degree,p.scale);while(generatedRoot>baseRoot+7)generatedRoot-=12;
        }
        if(p.autoPlay&&root<0) {root=generatedRoot;rootChannel=1;velocity=.8;}
        if(!p.autoPlay&&midiRoot<0&&root>=0&&!p.latch) {root=-1;bass.off();for(auto& v:pads)v.off();}
        if(p.autoPlay&&midiRoot<0&&root!=generatedRoot) {root=generatedRoot;lastStep=std::numeric_limits<int64_t>::min();if(p.pad)startPad(p,true);}
        }
        const double period=divisionBeats(p.division);
        if(previousPad&&!p.pad) for(auto& v:pads) {v.env.reset();v.fl.reset();v.fr.reset();}
        if(previousBass&&!p.bass) bass.reset();
        if(!external&&root>=0&&((!previousBass&&p.bass)||(previousDirect!=p.direct))) {
            bass.note(root,velocity,false,false);lastStep=std::numeric_limits<int64_t>::min();
        }
        previousPad=p.pad;previousBass=p.bass;previousDirect=p.direct;
        if(!external&&p.bass&&!p.direct&&root>=0) {
            double pos=ppq-(p.restart?anchor:0);
            int64_t pair=int64_t(std::floor(pos/(period*2)));
            double inside=pos-double(pair)*period*2;
            int64_t step=pair*2+(inside>=period*(1+p.swing*.5)?1:0);
            if(step!=lastStep) {
                int num=p.meter?p.numerator:hostNumerator,den=p.meter?p.denominator:hostDenominator;
                int count=std::max(1,int(std::lround(double(num)*4/std::max(1,den)*p.bars/period)));
                auto s=makeStep(p,step,count);
                if(!s.rest) {
                    bass.note(root+scaleOffset(s.degree,p.scale)+s.semitones+12*s.octave,velocity*s.velocity,previousSlide,s.accent);
                    gateUntil=ppq+period*s.length;previousSlide=s.slide;
                } else { bass.off();previousSlide=false;gateUntil=-1; }
                lastStep=step;
            }
            if(gateUntil>=0&&ppq>=gateUntil&&!previousSlide) { bass.off();gateUntil=-1; }
        }
        const bool routed=p.modularMidi&&!external;
        const int padRoot=routed?(p.harmonyLink&&root>=0?root:padMidiRoot):root;
        const bool generatePad=!external&&(!routed||p.padMidiMode==1);
        if(routed&&generatePad&&padRoot!=previousPadRoot){startPad(p,true,padRoot);previousPadRoot=padRoot;}
        if(generatePad&&padRoot>=0&&p.pad) {
            bool active=false;for(auto& v:pads) if(v.env.active()&&!v.releasing) active=true;
            if(!active) startPad(p,false,padRoot);
            padClock+=1/rate;
            if(p.padMode==1&&padClock>=p.evolution) { for(auto& v:pads)v.off();startPad(p,false,padRoot); }
            if(p.padMode==2) {
                // Each active voice ends its own cycle; release tails overlap its replacement.
                for(size_t k=0;k<pads.size();++k) if(pads[k].env.active()&&!pads[k].releasing&&pads[k].age>pads[k].lifetime) {
                    auto pan=pads[k].pan;pads[k].off();
                    PadVoice* replacement=nullptr;
                    for(auto& candidate:pads) if(!candidate.env.active()) {replacement=&candidate;break;}
                    if(!replacement) for(auto& candidate:pads) if(candidate.releasing && &candidate!=&pads[k]) {replacement=&candidate;break;}
                    if(replacement) {
                        int degree=int(unit(uint32_t(p.seed),++voiceSerial)*(p.krellRange+1));
                        double n=padRoot+scaleOffset(degree,p.scale);while(n<48)n+=12;while(n>84)n-=12;
                        replacement->start(n,pan,hash(uint32_t(p.seed)^voiceSerial),velocity);
                        setupKrell(*replacement,p,voiceSerial);
                    }
                }
            }
        }
        double b=p.bass?bass.next(p,bend[size_t(rootChannel-1)])*p.bassLevel:0;
        Stereo dryBass{b,b},dryPad{};
        if(p.pad) for(auto& v:pads) dryPad=dryPad+v.next(p,rate,bend[size_t(routed?1:rootChannel-1)]);
        dryPad=dryPad*p.padLevel;
        if(p.fxEnabled) {
            if(p.bass&&p.bassFX>0)dryBass=dryBass*(1-p.bassFX)+bassRack.process(dryBass,p,bpm)*p.bassFX;
            if(p.pad&&p.padFX>0)dryPad=dryPad*(1-p.padFX)+padRack.process(dryPad,p.padRack,bpm)*p.padFX;
        }
        if(previousArp&&!p.arp) arpeggiator.reset();
        if(previousDrums&&!p.drums)drumMachine.reset();
        previousArp=p.arp;previousDrums=p.drums;
        const bool generateArp=!external&&(!routed||p.arpMidiMode==1);
        const int arpRoot=routed?(p.harmonyLink&&root>=0?root:arpMidiRoot):root;
        const int arpTranspose=routed&&p.harmonyLink&&root>=0&&arpNoteCount>0?root-*std::min_element(arpNotes.begin(),arpNotes.begin()+arpNoteCount):0;
        Stereo arpOut{};if(p.arp)arpOut=arpeggiator.next(p,ppq,generateArp?arpRoot:1,arpNotes.data(),arpNoteCount,bend[size_t(routed?2:rootChannel-1)],generateArp,arpTranspose);
        if(p.drums)drumMachine.next(p,ppq,!external&&(!routed||p.drumsMidiMode==1)&&(wasPlaying||root>=0||p.autoPlay));
        if(p.fxEnabled&&p.arp&&p.arpFX>0)arpOut=arpOut*(1-p.arpFX)+arpRack.process(arpOut,p.arpRack,bpm)*p.arpFX;
        const int krellRoot=routed?(p.harmonyLink&&root>=0?root:krellMidiRoot):root;
        auto krellOut=p.krell?krellSynth.next(p,krellRoot,external||(routed&&p.krellMidiMode==0)):Stereo{};if(previousKrell&&!p.krell)krellSynth.reset();previousKrell=p.krell;
        if(p.fxEnabled&&p.krell&&p.krellFX>0)krellOut=krellOut*(1-p.krellFX)+krellRack.process(krellOut,p.krellRack,bpm)*p.krellFX;
        stems={dryBass,dryPad,arpOut};stems[7]=krellOut;
        if(p.drums)for(int lane=0;lane<4;++lane){auto drum=drumMachine.outputs[size_t(lane)];if(p.fxEnabled&&p.drumSounds[size_t(lane)].enabled&&p.drumsFX>0)drum=drum*(1-p.drumsFX)+drumRacks[size_t(lane)].process(drum,p.drumsRack,bpm)*p.drumsFX;stems[size_t(lane+3)]=drum;}
        bool solo=false;for(int t=0;t<8;++t)solo|=p.mix(t).solo;
        Stereo out{},delayInput{},reverbInput{};
        for(int track=0;track<8;++track){const auto mix=p.mix(track);auto& stem=stems[size_t(track)];
            // Balance preserves original stereo at centre, including ARP ping-pong.
            const double gain=mix.mute||(solo&&!mix.solo)?0:mix.gain;
            stem={stem.l*gain*(mix.pan>0?1-mix.pan:1),stem.r*gain*(mix.pan<0?1+mix.pan:1)};
            delayInput=delayInput+stem*mix.delay;reverbInput=reverbInput+stem*mix.reverb;
            if(!(splitMask&(1U<<track)))out=out+stem;
            stem=stem*p.master;
        }
        returns={};
        if(p.fxEnabled&&p.sendDelayPower)returns[0]=delaySendRack.processWet(delayInput,sendPatch(p,true),bpm)*p.sendDelayReturn;
        if(p.fxEnabled&&p.sendReverbPower)returns[1]=reverbSendRack.processWet(reverbInput,sendPatch(p,false),bpm)*p.sendReverbReturn;
        for(int k=0;k<2;++k){if(!(splitMask&(1U<<(8+k))))out=out+returns[size_t(k)];returns[size_t(k)]=returns[size_t(k)]*p.master;}

        if(p.fxEnabled&&p.masterFX>0) out=out*(1-p.masterFX)+masterRack.process(out,p.masterRack,bpm)*p.masterFX;
        out=out*p.master;

        if(!p.bass&&!p.pad&&!p.arp&&!p.drums&&!p.krell&&std::abs(returns[0].l)+std::abs(returns[0].r)+std::abs(returns[1].l)+std::abs(returns[1].r)<1e-15){dcInL=dcInR=dcOutL=dcOutR=0;return {};}
        const double dcCoefficient=std::exp(-2*pi*5/rate);
        double l=out.l-dcInL+dcCoefficient*dcOutL,r=out.r-dcInR+dcCoefficient*dcOutR;
        dcInL=out.l;dcInR=out.r;dcOutL=l;dcOutR=r;
        if(!std::isfinite(l)||!std::isfinite(r)) { dcInL=dcInR=dcOutL=dcOutR=0;return {}; }
        if(p.limiter) { l=std::tanh(l);r=std::tanh(r); }
        lastPPQ=ppq;
        return {l,r};
    }
};
} // namespace jerzy
