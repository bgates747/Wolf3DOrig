// Exercise the actual candidate wall sampler against scalar destination/sample
// equations, including native masks that differ from the physical 0x3f/0xc0.
#include "wolf3d_renderer.cpp"
#include <array>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace wolf3d_production;
namespace {
unsigned cases = 0;
void check(bool ok) { if (!ok) throw std::runtime_error("wall sampling / bytes / guards mismatch"); }
void run(int full_height, uint8_t source_x, unsigned bias, unsigned xr,
         uint8_t cm, uint8_t pm, bool linear) {
    std::array<uint8_t,4096> texture{};
    for (unsigned i=0; i<texture.size(); ++i) texture[i]=static_cast<uint8_t>(i*137u+i/64*71u+source_x);
    constexpr unsigned stride=352;
    std::vector<uint8_t> storage(stride*240+32), expected;
    for (unsigned i=0; i<storage.size(); ++i) storage[i]=static_cast<uint8_t>(i*17u+i/stride*31u);
    expected=storage;
    std::array<uintptr_t,240> rows{};
    for (unsigned y=0; y<240; ++y) rows[y]=reinterpret_cast<uintptr_t>(storage.data()+16+((y*37u)%240u)*stride);
    const RenderTarget target={linear ? storage.data()+16 : nullptr,
        linear ? nullptr : rows.data(),bias,xr,cm,pm};
    const int top=80-full_height/2;
    const int first=top<0 ? 0 : top;
    const int last=top+full_height>160 ? 160 : top+full_height;
    const int32_t step=(64<<16)/full_height;
    const int32_t fraction=step*(first-top);
    const uint32_t x=32+source_x*3u;
    // Independent closed-form fraction per output, and explicit logical mapping.
    for (int y=first; y<last; ++y) {
        const unsigned sy=std::min(63u,static_cast<unsigned>((fraction+(y-first)*step)>>16));
        const uint8_t color=texture[sy*64+source_x]&63u;
        const unsigned dy=20+static_cast<unsigned>(y);
        const unsigned at=linear ? 16+dy*320+x : 16+((dy*37u)%240u)*stride+((bias+x)^xr);
        expected[at]=linear ? color : static_cast<uint8_t>((expected[at]&pm)|(color&cm));
    }
    draw_wall_column(target,x,static_cast<uint32_t>(20+first),last-first,texture.data(),source_x,fraction,step);
    check(storage==expected);
    ++cases;
}
}
int main() {
    try {
        const int heights[]={1,2,3,7,31,63,64,65,127,159,160,161,255,256,1023,22272};
        for (int h:heights) for (unsigned sx: {0u,1u,31u,63u})
            for (unsigned bias: {0u,1u,4u}) for (unsigned xr=0; xr<4; ++xr)
                for (bool linear: {false,true}) run(h,static_cast<uint8_t>(sx),bias,xr,0x3f,0xc0,linear);
        for (unsigned cm=0; cm<256; ++cm) for (unsigned pm=0; pm<256; ++pm)
            run(1+static_cast<int>((cm*17u+pm*7u)%300u),static_cast<uint8_t>((cm+pm)%64u),cm%5u,pm%4u,
                static_cast<uint8_t>(cm),static_cast<uint8_t>(pm),false);
        std::cout<<"PASS "<<cases<<" wall-column cases: scalar sampling, all mask pairs, native permutation/noncontiguous rows, clipping, linear and full storage guards\n";
    } catch (const std::exception &e) { std::cerr<<e.what()<<'\n'; return 1; }
}
