// Exact native helper bodies, renamed to avoid host runtime replacement.
#include <stdint.h>
#include "original_numeric.inc"
#include "candidate_numeric.inc"
#include <array>
#include <iostream>
#include <limits>
#include <stdexcept>
namespace {
uint64_t count=0,narrow=0,wide=0,zero=0,seed=0x19e3779b27acdb1fULL;
uint64_t next() { seed^=seed<<13;seed^=seed>>7;seed^=seed<<17;return seed; }
void pair(uint64_t n,uint64_t d) {
    uint64_t expected=d==0 ? UINT64_MAX : n/d;
    if(original::original_udiv(n,d)!=expected || candidate::candidate_udiv(n,d)!=expected)
        throw std::runtime_error("actual unsigned body differs from mathematical/zero oracle");
    const int64_t sn=static_cast<int64_t>(n),sd=static_cast<int64_t>(d);
    uint64_t signed_expected;
    if(sd==0)signed_expected=sn<0 ? 1 : UINT64_MAX;
    else if(sn==INT64_MIN && sd==-1)signed_expected=uint64_t(1)<<63;
    else signed_expected=static_cast<uint64_t>(sn/sd);
    if(static_cast<uint64_t>(original::original_sdiv(sn,sd))!=signed_expected ||
       static_cast<uint64_t>(candidate::candidate_sdiv(sn,sd))!=signed_expected)
        throw std::runtime_error("actual signed body differs from defined/exceptional-bit oracle");
    if(d==0)++zero;
    else if((n>>32)==0 && (d>>32)==0)++narrow;
    else ++wide;
    ++count;
}
}
int main() {
    try {
        static_assert(sizeof(uint32_t)==4 && sizeof(uint64_t)==8,"word widths differ");
        // Verify the inherited low/high representation used by these bodies.
        original::WideWords repr={0x123456789abcdef0ULL};
        if(repr.words.low!=0x9abcdef0u || repr.words.high!=0x12345678u)
            throw std::runtime_error("host word layout differs from selected target");
        constexpr uint64_t u32=uint64_t(1)<<32,u63=uint64_t(1)<<63;
        const uint64_t directed[]={0,1,2,3,7,31,32,63,64,127,128,
            (uint64_t(1)<<31)-1,uint64_t(1)<<31,(uint64_t(1)<<31)+1,
            u32-1,u32,u32+1,u32+2,u32*2-1,u63-1,u63,u63+1,UINT64_MAX-1,UINT64_MAX};
        for(uint64_t n:directed)for(uint64_t d:directed)pair(n,d);
        for(unsigned i=0;i<100000;++i) {
            const uint64_t n=next(),d=next();
            pair(n,d);pair(n&0xffffffffu,d&0xffffffffu);
            // Both signs with magnitudes covering the unsigned32 high half.
            pair(uint64_t(0)-(n&0xffffffffu),d&0xffffffffu);
            pair(n&0xffffffffu,uint64_t(0)-(d&0xffffffffu));
            // Adjacent magnitudes/equality and exact multiples, without overflow.
            const uint64_t base=(d&0x7fffffffu)+1;
            const uint64_t multiple=base*(n&0xffffu);
            pair(multiple,base);pair(multiple+1,base);pair(multiple==0?0:multiple-1,base);
            pair(n,n);pair(n,d==0?1:d);pair(n,0);
        }
        if(narrow==0 || wide==0 || zero==0)throw std::runtime_error("missing boundary partition");
        std::cout<<"PASS "<<count<<" unsigned+signed actual-body pairs; narrow="<<narrow
                 <<" wide="<<wide<<" zero="<<zero
                 <<"; mathematical quotient, exact old body, boundary/sign/extreme/zero/overflow-bit oracles; host execution not Xtensa execution\n";
    } catch(const std::exception &e) { std::cerr<<e.what()<<'\n';return 1; }
}
