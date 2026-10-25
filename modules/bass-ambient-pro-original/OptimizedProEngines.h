// Included inside namespace jerzy, after the shared voice/FX definitions.
inline int64_t swungStep(double ppq,double period,double swing) {
    const auto pair=int64_t(std::floor(ppq/(period*2)));
    return pair*2+(ppq-double(pair)*period*2>=period*(1+clamp(swing,0.0,.9)*.5)?1:0);
}
inline Stereo panSample(double value,double pan) {
    const double a=(clamp(pan,-1.0,1.0)+1)*pi*.25;
    return {value*std::cos(a),value*std::sin(a)};
}
struct ArpEvent { int note=-1; double gate=0,velocity=0,pan=0; };
inline ArpEvent makeArpEvent(const Parameters& p,int64_t step,const int* notes,int count,int root) {
    ArpEvent e;
    const int length=clamp(p.arpSteps,1,32), pulses=clamp(p.arpPulses,0,length);
    const int k=int((step%length+length)%length);
    if(pulses==0||(k*pulses)%length>=pulses) return e;
    const uint32_t seed=uint32_t(p.seed)^0xabc913U;
    const uint32_t index=uint32_t(p.evolve?step:k);
    static constexpr int chords[8][4]={{0,4,7,12},{0,3,7,12},{0,7,12,19},{0,5,7,12},{0,3,7,10},{0,4,7,11},{0,3,10,14},{0,4,11,14}};
    std::array<int,4> generated{};
    if(count==0) {for(int i=0;i<4;++i)generated[size_t(i)]=root+12+chords[clamp(p.chord,0,7)][i];notes=generated.data();count=4;}
    const int n=std::max(1,count), total=n*clamp(p.arpOctaves,1,4);
    int position=int((step%total+total)%total);
    if(p.arpPattern==1) position=total-1-position;
    if(p.arpPattern==2) { const int span=std::max(1,2*total-2);position=int((step%span+span)%span);if(position>=total)position=span-position; }
    if(p.arpPattern==4) position=int(unit(seed,index*9+1)*total);
    if(p.arpPattern==5) {
        // Bounded repeatable walk, including when jumping directly to a step.
        position=total/2;
        for(uint32_t i=0;i<=uint32_t(k);++i) position=clamp(position+(unit(seed,i*9+2)>.5?1:-1),0,total-1);
    }
    e.note=(count?notes[position%n]:root+12)+12*(position/n);
    if(unit(seed,index*9+3)<p.arpPitchRandom) {
        const int range=clamp(p.arpRange,0,21);
        e.note=root+12+scaleOffset(int(unit(seed,index*9+4)*(2*range+1))-range,p.scale);
    }
    e.note=clamp(e.note,12,108);
    const double random=unit(seed,index*9+5);
    e.gate=clamp(p.arpGate*(1-p.arpGateRandom+p.arpGateRandom*random*2),.02,1.8);
    e.velocity=1-p.arpVelocity*.7*unit(seed,index*9+6);
    if(p.arpPanMode==1) e.pan=(step%2==0?-1:1)*p.arpWidth;
    if(p.arpPanMode==2) e.pan=(unit(seed,index*9+7)*2-1)*p.arpWidth;
    if(p.arpPanMode==3) e.pan=std::sin(double(step)*pi/4)*p.arpWidth;
    return e;
}
class Arpeggiator {
    struct Voice { Oscillator a,b; Ladder filter; Envelope env; double note=60,pan=0,velocity=0,age=0,offPPQ=0; uint32_t id=0; };
    std::array<Voice,8> voices{};
    double rate=48000; int64_t previous=std::numeric_limits<int64_t>::min();
    int lastNote=-1;
public:
    void prepare(double sr) { rate=sr;for(auto& v:voices)v.env.prepare(sr);reset(); }
    void reset() { for(auto& v:voices) {v.env.reset();v.filter.reset();v.a={};v.b={};}previous=std::numeric_limits<int64_t>::min();lastNote=-1; }
    bool active() const {for(const auto& v:voices)if(v.env.active())return true;return false;}
    int noteDisplay() const {return lastNote;}
    void trigger(int note,double velocity,double pan,double offPPQ,uint32_t id) {
        Voice* selected=nullptr;for(auto& v:voices)if(!v.env.active()){selected=&v;break;}
        if(!selected)selected=&*std::max_element(voices.begin(),voices.end(),[](const auto& a,const auto& b){return a.age<b.age;});
        auto& v=*selected;v.note=note;v.pan=pan;v.velocity=velocity;v.age=0;v.offPPQ=offPPQ;v.id=id;v.env.on();lastNote=note;
    }
    void noteOff(uint32_t id) {for(auto& v:voices)if(v.id==id)v.env.off();}
    Stereo next(const Parameters& p,double ppq,int root,const int* notes,int count,double bend,bool generate=true,int transpose=0) {
        const double period=divisionBeats(p.arpDivision);const auto step=swungStep(ppq,period,p.arpSwing);
        if(generate&&root>=0&&step!=previous) {const auto e=makeArpEvent(p,step,notes,count,root);previous=step;if(e.note>=0)trigger(clamp(e.note+transpose,0,127),e.velocity,e.pan,ppq+period*e.gate,0);}
        Stereo out{};
        for(auto& v:voices) if(v.env.active()) {
            if(root<0||ppq>=v.offPPQ)v.env.off();
            const double env=v.env.next(p.arpAttack,p.arpDecay,p.arpSustain,p.arpRelease);
            const double f=hz(v.note+bend);double x=0;
            if(p.arpModel==0) x=.7*v.a.next(f,rate,0)+.3*v.b.next(f*1.003,rate,1);
            if(p.arpModel==1) { const double mod=v.b.next(f*2,rate,2); const double t=v.a.phase;v.a.next(f,rate,2);x=std::sin(2*pi*t+mod*3*std::exp(-v.age*3)); }
            if(p.arpModel==2)x=v.a.next(f,rate,3);
            if(p.arpModel==3)x=v.a.next(f,rate,1,.5+.25*std::sin(v.age*2));
            x=v.filter.process(x,p.arpCutoff*std::exp2(p.arpFilterEnv*env*3),p.arpResonance,rate,.1);
            out=out+panSample(x*env*v.velocity*p.arpLevel*.3,v.pan);v.age+=1/rate;
        }
        return out;
    }
};
class DrumMachine {
    struct Voice { Oscillator osc,metal; double age=100,velocity=0,filter=0;uint32_t noise=1; };
    std::array<Voice,4> voices{};std::array<bool,4> sounding{};double rate=48000;
    int64_t previous=std::numeric_limits<int64_t>::min();int position=-1;
public:
    void prepare(double sr) {rate=sr;reset();}
    void reset() {voices={};sounding={};previous=std::numeric_limits<int64_t>::min();position=-1;}
    std::array<Stereo,4> outputs{};
    bool active(int lane) const {return sounding[size_t(lane)];}
    int stepDisplay() const {return position;}
    void trigger(int lane,double velocity) {if(lane>=0&&lane<4) { auto& v=voices[size_t(lane)];v.age=0;v.velocity=velocity;v.osc={};v.metal={};v.filter=0;v.noise=hash(uint32_t(lane+1)*71); }}
    Stereo next(const Parameters& p,double ppq,bool running) {
        const auto step=swungStep(ppq,divisionBeats(p.drumDivision),p.drumSwing);
        if(running&&step!=previous) {
            previous=step;const int length=clamp(p.drumLength,1,64);position=int((step%length+length)%length);
            for(int lane=0;lane<4;++lane) if(p.drumSounds[size_t(lane)].enabled) {
                const int velocity=p.drumGrid[size_t(lane)][size_t(position)];
                if(velocity>0) trigger(lane,double(velocity)/127*(1-p.drumHumanize*.35*unit(uint32_t(p.seed),uint32_t(step)*7+uint32_t(lane))));
            }
        }
        Stereo out{};outputs={};
        for(int lane=0;lane<4;++lane) {
            auto& v=voices[size_t(lane)];const auto& s=p.drumSounds[size_t(lane)];
            sounding[size_t(lane)]=false;
            if(!s.enabled) {v.age=100;continue;}
            const bool open=lane==3&&p.drumAux==1;
            const double decay=clamp(s.decay*(open?2.5:1),.015,3.0);
            if(v.age>decay*9)continue;
            sounding[size_t(lane)]=true;
            const double amp=std::exp(-v.age/decay);
            v.noise=hash(v.noise);const double noise=double(v.noise)/2147483648.0-1;
            double x=0;
            if(lane==0) {
                const double base=35+s.tone*45;
                x=v.osc.next(base+130*std::exp(-v.age/(.012+s.tone*.025)),rate,2)*amp+noise*.12*std::exp(-v.age/.003);
            } else if(lane==1) {
                x=(noise*(.4+s.tone*.5)+v.osc.next(140+s.tone*130,rate,2)*.45)*amp;
            } else if(lane==2||open) {
                const double metal=v.osc.next(3100+s.tone*4000,rate,1)*v.metal.next(4307+s.tone*1900,rate,1);
                x=(.6*noise+.4*metal)*amp*.45;
            } else if(p.drumAux==2) {
                x=v.osc.next(75+s.tone*180+70*std::exp(-v.age/.025),rate,2)*amp;
            } else {
                const double burst=std::fmod(v.age,.012);
                const double envelope=v.age<.036?std::exp(-burst/.003):std::exp(-(v.age-.036)/decay);
                x=noise*envelope*.65;
            }
            const double coefficient=1-std::exp(-2*pi*clamp(s.cutoff,40.0,rate*.45)/rate);
            v.filter+=coefficient*(x-v.filter);
            // Hats/clap retain a high-pass character as tone rises.
            x=(lane==2||open)?v.filter-x*(.2+s.tone*.45):v.filter;
            const double gain=1+s.drive*7;x=std::tanh(x*gain)/std::sqrt(gain);
            outputs[size_t(lane)]=panSample(x*v.velocity*s.level*p.drumLevel,s.pan);out=out+outputs[size_t(lane)];v.age+=1/rate;
        }
        return out;
    }
};

// Independent Krell engine: eight evolving FM/noise/harmonic-cloud voices.
class KrellSynth {
    struct Voice {Oscillator carrier,modulator;Ladder filter;Envelope env;double note=48,velocity=.8,pan=0,age=0,life=1;uint32_t id=0;bool releasing=false;};
    std::array<Voice,8> voices{};double rate=48000;uint32_t serial=0;int oldRoot=-1;
    void automatic(const Parameters& p,int root){
        const uint32_t id=++serial;const int degree=int(unit(uint32_t(p.seed),id*19+1)*(p.krellPitchRange+1));
        const int note=clamp(root+12+scaleOffset(degree,p.scale),24,100);trigger(note,.5+.45*unit(uint32_t(p.seed),id*19+2),(unit(uint32_t(p.seed),id*19+3)*2-1)*p.krellStereo,id);
        for(auto& v:voices)if(v.id==id){v.life=std::min(p.krellCycleMin,p.krellCycleMax)+std::abs(p.krellCycleMax-p.krellCycleMin)*unit(uint32_t(p.seed),id*19+4);break;}
    }
public:
    void prepare(double sr){rate=sr;for(auto& v:voices)v.env.prepare(sr);reset();}
    void reset(){for(auto& v:voices){v.env.reset();v.filter.reset();v.carrier={};v.modulator={};v.releasing=false;}oldRoot=-1;serial=0;}
    bool active() const {for(const auto& v:voices)if(v.env.active())return true;return false;}
    void trigger(int note,double velocity,double pan,uint32_t id){Voice* chosen=nullptr;for(auto& v:voices)if(!v.env.active()){chosen=&v;break;}if(!chosen)chosen=&*std::max_element(voices.begin(),voices.end(),[](const auto& a,const auto& b){return a.age<b.age;});auto& v=*chosen;v.note=note;v.velocity=velocity;v.pan=pan;v.id=id;v.age=0;v.life=1;v.releasing=false;v.env.on();}
    void noteOff(uint32_t id){for(auto& v:voices)if(v.id==id){v.env.off();v.releasing=true;}}
    Stereo next(const Parameters& p,int root,bool external){
        if(!external){
            if(root!=oldRoot){for(auto& v:voices)if(v.env.active()){v.env.off();v.releasing=true;}if(root>=0)for(int i=0;i<4;++i)automatic(p,root);oldRoot=root;}
            if(root>=0)for(size_t i=0;i<voices.size();++i)if(voices[i].env.active()&&!voices[i].releasing&&voices[i].age>=voices[i].life){voices[i].env.off();voices[i].releasing=true;automatic(p,root);}
        }
        Stereo out{};for(auto& v:voices)if(v.env.active()){
            const double modulation=.5+.5*std::sin(v.age*.31+v.pan*3),f=hz(v.note+.05*std::sin(v.age*.7));
            const double phase=v.carrier.phase;v.carrier.next(f,rate,2);const double mod=v.modulator.next(f*(1.5+p.krellTimbre*2),rate,2);
            double x=std::sin(2*pi*phase+mod*(.2+p.krellTimbre*5)*modulation);
            if(p.krellEngine==1)x=.6*(unit(uint32_t(p.seed)^v.id,uint32_t(v.age*rate))*2-1)+.4*x;
            if(p.krellEngine==2)x=.6*x+.25*std::sin(4*pi*phase+mod)+.15*std::sin(6*pi*phase-mod);
            const double env=v.env.next(p.krellAttack*(.6+modulation),.5,.7,p.krellRelease);
            x=v.filter.process(x,p.krellCutoff*std::exp2((modulation-.5)*2*p.krellTimbre),p.krellResonance,rate,.12);
            out=out+panSample(x*env*v.velocity*p.krellLevel*.23,v.pan*p.krellStereo);v.age+=1/rate;
        }return out;
    }
};

// Single audio consumer and single maintenance producer. Allocation and deletion
// happen only in service(), never in the audio callback. At most one retired rack.
class ManagedRack {
    std::atomic<FXRack*> ready{nullptr},retired{nullptr};
    std::atomic<int> wanted{0},attached{0};
    FXRack* active=nullptr;int activeMask=0;double rate=48000;
public:
    ~ManagedRack() {delete active;delete ready.load();delete retired.load();}
    ManagedRack()=default;ManagedRack(const ManagedRack&)=delete;
    void prepare(double sr) {delete active;active=nullptr;delete ready.exchange(nullptr);delete retired.exchange(nullptr);wanted=0;attached=0;activeMask=0;rate=sr;}
    static int mask(const FXParameters& p) {return (p.fxDrive?1:0)|(p.fxChorus?2:0)|(p.fxDelay?4:0)|(p.fxGrain?8:0)|(p.fxReverb?16:0)|(p.fxWidth?32:0);}
    void configure(const FXParameters& p,bool enabled) {
        const int requested=enabled?mask(p):0;wanted.store(requested,std::memory_order_release);
        if(active&&activeMask!=requested&&retired.load(std::memory_order_acquire)==nullptr) {
            retired.store(active,std::memory_order_release);active=nullptr;activeMask=0;attached.store(0,std::memory_order_release);
        }
        if(!active) if(auto* replacement=ready.exchange(nullptr,std::memory_order_acquire)) {
            active=replacement;activeMask=replacement->allocationMask;attached.store(activeMask,std::memory_order_release);
        }
    }
    void service() {
        delete retired.exchange(nullptr,std::memory_order_acquire);
        const int requested=wanted.load(std::memory_order_acquire);
        if(auto* pending=ready.load(std::memory_order_acquire)) {
            if(pending->allocationMask!=requested)delete ready.exchange(nullptr,std::memory_order_acquire);
        }
        if(!requested||ready.load(std::memory_order_acquire))return;
        // Producer does not inspect audio-owned active pointer.
        if(attached.load(std::memory_order_acquire)==requested)return;
        auto rack=std::make_unique<FXRack>();rack->prepare(rate,requested);
        ready.store(rack.release(),std::memory_order_release);
    }
    void reset() { // Request disposal at the next block boundary, off audio thread.
        activeMask=-1;
        if(active&&retired.load(std::memory_order_acquire)==nullptr) {retired.store(active,std::memory_order_release);active=nullptr;activeMask=0;attached.store(0,std::memory_order_release);}

    }
    void maintenance() {service();}
    Stereo process(Stereo x,const FXParameters& p,double bpm) {return active&&activeMask==mask(p)?active->process(x,p,bpm):x;}
    Stereo processWet(Stereo x,const FXParameters& p,double bpm) {return active&&activeMask==mask(p)?active->process(x,p,bpm):Stereo{};}
    size_t memoryBytes() const {return active?active->memoryBytes():0;}
private:

};
