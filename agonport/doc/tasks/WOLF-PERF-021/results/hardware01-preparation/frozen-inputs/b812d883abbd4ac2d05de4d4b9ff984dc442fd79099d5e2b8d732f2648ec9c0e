// Independent original painter equations, not the new exterior rectangles.
#include "wolf3d_renderer.cpp"
#include <array>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace wolf3d_production;
namespace {
unsigned cases=0;
void run(uint8_t cm,uint8_t pm,unsigned bias,unsigned xr,bool linear) {
    constexpr unsigned stride=352;
    std::vector<uint8_t> storage(stride*240+32),expected;
    for(unsigned i=0;i<storage.size();++i)storage[i]=static_cast<uint8_t>(i*17u+i/stride*31u);
    expected=storage;
    std::array<uintptr_t,240> rows{};
    for(unsigned y=0;y<240;++y)rows[y]=reinterpret_cast<uintptr_t>(storage.data()+16+((y*37u)%240u)*stride);
    const RenderTarget target={linear?storage.data()+16:nullptr,linear?nullptr:rows.data(),bias,xr,cm,pm};
    for(unsigned y=0;y<240;++y)for(unsigned x=0;x<320;++x) {
        const unsigned at=linear?16+y*320+x:16+((y*37u)%240u)*stride+((bias+x)^xr);
        auto paint=[&](uint8_t color){expected[at]=linear?color:static_cast<uint8_t>((expected[at]&pm)|(color&cm));};
        // Original layers, with original corner overwrite order and RGB values.
        paint(y>=200?21:20);
        if(x>=32&&x<288&&y>=20&&y<180)paint(y<100?42:21);
        if(y==19&&x>=31&&x<=288)paint(0);
        if(y==180&&x>=31&&x<=288)paint(40);
        if(x==31&&y>=19&&y<=180)paint(0);
        if(x==288&&y>=19&&y<=180)paint(40);
    }
    compose_background(target);
    if(storage!=expected)throw std::runtime_error("background/mask/corner/guard mismatch");
    ++cases;
}
}
int main() {
    try {
        const uint8_t masks[]={0,1,3,15,20,42,63,64,85,128,170,192,254,255};
        for(uint8_t cm:masks)for(uint8_t pm:masks) {
            for(unsigned bias:{0u,1u,4u})for(unsigned xr:{0u,1u,3u})run(cm,pm,bias,xr,false);
            run(cm,pm,0,0,true);
        }
        std::cout<<"PASS "<<cases<<" background cases: independent original layers, disjoint/overlapping masks, arbitrary initial bytes, linear/noncontiguous/permuted rows, bevel corners and full storage guards\n";
    } catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}
}
