static jerzy::Parameters referenceParameters(const float* values) {
    jerzy::Parameters p;size_t i=0;
#define BOOL(f,l,g) p.f=values[i++]>.5f;
#define FLOAT(f,a,b,s,l,g) p.f=values[i++];
#define INT(f,a,b,l,g) p.f=int(std::lround(values[i++]));
#define CHOICE(f,l,g,c) p.f=int(std::lround(values[i++]));
#define CHOICE_DEN(f,l,g) { constexpr int d[]{2,4,8,16};p.f=d[std::clamp(int(std::lround(values[i++])),0,3)]; }
#include "../modules/bass-ambient-pro-original/vendor/Parameters.def"
#undef BOOL
#undef FLOAT
#undef INT
#undef CHOICE
#undef CHOICE_DEN
    for(int k=0;k<6;++k) p.order[size_t(k)]=int(std::lround(values[i++]));
    for(auto* rack:{&p.padRack,&p.masterRack}) {
#define BOOL(f,l,g) rack->f=values[i++]>.5f;
#define FLOAT(f,a,b,s,l,g) rack->f=values[i++];
#define CHOICE(f,l,g,c) rack->f=int(std::lround(values[i++]));
#include "../modules/bass-ambient-pro-original/vendor/FXParameters.def"
#undef BOOL
#undef FLOAT
#undef CHOICE
        for(int k=0;k<6;++k) rack->order[size_t(k)]=int(std::lround(values[i++]));
    }
    p.masterFX=values[i++];
    for(auto& sound:p.drumSounds) {
        sound.enabled=values[i++]>.5f;sound.level=values[i++];sound.drive=values[i++];
        sound.tone=values[i++];sound.cutoff=values[i++];sound.decay=values[i++];sound.pan=values[i++];
        for(auto& step:p.drumGrid[size_t(&sound-p.drumSounds.data())])step=int(std::lround(values[i++]));
    }
    for(auto* rack:{&p.arpRack,&p.drumsRack,&p.krellRack}) {
#define BOOL(f,l,g) rack->f=values[i++]>.5f;
#define FLOAT(f,a,b,s,l,g) rack->f=values[i++];
#define CHOICE(f,l,g,c) rack->f=int(std::lround(values[i++]));
#include "../modules/bass-ambient-pro-original/vendor/FXParameters.def"
#undef BOOL
#undef FLOAT
#undef CHOICE
        for(int k=0;k<6;++k)rack->order[size_t(k)]=int(std::lround(values[i++]));
    }
#define BOOL(f,l,g) p.f=values[i++]>.5f;
#define CHOICE(f,l,g,c) p.f=int(std::lround(values[i++]));
#include "../modules/bass-ambient-pro-original/vendor/PerformanceParameters.def"
#undef BOOL
#undef CHOICE
    p.bassBody=values[i++];
    p.bassAttackTransient=values[i++];
    p.padBody=values[i++];
    p.padAttackTransient=values[i++];
    return p;
}
