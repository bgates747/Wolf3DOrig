#include "recorder.h"
#include <array>
#include <cassert>
#include <cstring>
#include <iostream>

static uint32_t word(const uint8_t *p) {
    return uint32_t(p[0])|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;
}
int main() {
    std::array<uint8_t,WolfPerfRecorder::bytes+16> guarded;
    guarded.fill(0xa5);
    WolfPerfRecorder r;
    assert(r.finish(0,1,1,0,0)); // inactive warm-up emits nothing
    assert(!r.reset(guarded.data()+8,15,0xcdcd));
    for (auto b:guarded) assert(b==0xa5);
    assert(r.reset(guarded.data()+8,WolfPerfRecorder::bytes,0xcdcd));
    assert(word(guarded.data()+8)==0x314e5057);
    uint16_t value=0;
    assert(r.read16(0,value) && value==0x5057);
    assert(!r.read16(1,value) && !r.read16(16,value));
    for (uint32_t n=0;n<600;++n) {
        const uint32_t begin=0xfffffff0u, end=0x20u;
        assert(r.finish((720*(n+1)/600)%360,end-begin,64,0xcdcd,0xcdcd));
        const uint8_t *p=guarded.data()+8+16+n*20;
        assert(word(p)==n && word(p+8)==48 && word(p+16)==64);
    }
    assert(word(guarded.data()+8+8)==600);
    assert(r.read16(WolfPerfRecorder::bytes-2,value));
    assert(!r.read16(WolfPerfRecorder::bytes,value));
    const auto full=guarded;
    assert(!r.finish(0,48,64,0xcdcd,0xcdcd));
    assert(guarded==full && !r.read16(0,value));
    for (size_t i=0;i<8;++i) assert(guarded[i]==0xa5 && guarded[guarded.size()-1-i]==0xa5);
    for (unsigned which=0;which<5;++which) {
        assert(r.reset(guarded.data()+8,WolfPerfRecorder::bytes,0xcdcd));
        const auto before=guarded;
        assert(!r.finish(which==0?360:0,which==1?0:48,
                         which==2?47:which==3?0x80000000u:64,
                         0xcdcd,which==4?0xebeb:0xcdcd));
        assert(guarded==before && r.failed);
    }
    std::cout<<"PASS recorder: 600 rows, bytes/guards, bounded readout, wrap delta, overflow, invalid intervals and core migration\n";
}
