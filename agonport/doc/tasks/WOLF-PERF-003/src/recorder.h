#ifndef WOLF_PERF003_RECORDER_H
#define WOLF_PERF003_RECORDER_H
#include <stdint.h>
#include <stddef.h>

// Caller-owned byte store, no allocator, logging, UART or framebuffer calls.
// Both elapsed intervals end before recorder writes. Raw modulo-32 CCOUNT.
struct WolfPerfRecorder {
    uint8_t *data = nullptr;
    uint32_t count = 0, core = 0;
    bool failed = false;
    static constexpr uint32_t capacity = 600;
    static constexpr uint32_t bytes = 16 + capacity * 20;
    static void put(uint8_t *p, uint32_t value) {
        for (unsigned i=0; i<4; ++i) p[i]=uint8_t(value>>(8*i));
    }
    bool reset(uint8_t *store, size_t size, uint32_t current_core) {
        data=nullptr; count=0; failed=false;
        if (!store || size<bytes) { failed=true; return false; }
        data=store; core=current_core;
        put(data,0x314e5057); put(data+4,1); put(data+8,0); put(data+12,core);
        return true;
    }
    bool finish(uint32_t angle, uint32_t draw, uint32_t dispatch,
                uint32_t first_core, uint32_t last_core) {
        if (!data) return !failed; // pre-reset warm-up only
        if (failed || count>=capacity || first_core!=core || last_core!=core ||
            angle>=360 || !draw || draw>dispatch || dispatch>=0x80000000u) {
            failed=true; return false;
        }
        uint8_t *p=data+16+count*20;
        put(p,count); put(p+4,angle); put(p+8,draw);
        put(p+12,draw); put(p+16,dispatch);
        ++count; put(data+8,count); return true;
    }
    bool read16(uint32_t offset, uint16_t &value) const {
        if (!data || failed || (offset&1) || offset>=16+count*20-1) return false;
        value=uint16_t(data[offset]) | uint16_t(data[offset+1])<<8;
        return true;
    }
};
#endif
