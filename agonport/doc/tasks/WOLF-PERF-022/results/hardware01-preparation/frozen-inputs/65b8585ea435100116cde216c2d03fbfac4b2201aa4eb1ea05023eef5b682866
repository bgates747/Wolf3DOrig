// Original ordered paint layers, including destination-row aliases.
// The earlier per-logical-pixel final-colour oracle assumes distinct pixels;
// this oracle executes the original global layer order instead.
#include "wolf3d_renderer.cpp"
#include <array>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace wolf3d_production;
namespace {
unsigned cases=0;
void run(unsigned layout,uint8_t cm,uint8_t pm) {
    std::vector<uint8_t> storage(352*240+64),expected;
    for(unsigned i=0;i<storage.size();++i)storage[i]=uint8_t(i*31u+(i/352u)*17u);
    expected=storage;
    std::array<unsigned,240> offsets{};
    std::array<uintptr_t,240> rows{};
    for(unsigned y=0;y<240;++y) {
        switch(layout) {
        case 0: offsets[y]=32;break; // all rows share the same320 bytes
        case 1: offsets[y]=32+(y%7)*17;break; // shifted overlapping rows
        case 2: offsets[y]=32+((y*37)%16)*13;break;
        case 3: offsets[y]=32+((y*37)%240)*352;break;
        case 4: offsets[y]=32+y*320;break;
        default: offsets[y]=32+y*320;break;
        }
        rows[y]=reinterpret_cast<uintptr_t>(storage.data()+offsets[y]);
    }
    const bool linear=layout==5;
    const RenderTarget target={linear?storage.data()+32:nullptr,linear?nullptr:rows.data(),4,3,cm,pm};
    const auto paint=[&](unsigned x,unsigned y,uint8_t color) {
        const unsigned at=linear?32+y*320+x:offsets[y]+((4+x)^3);
        if(at>=expected.size())throw std::runtime_error("oracle address outside backing storage");
        expected[at]=linear?color:uint8_t((expected[at]&pm)|(color&cm));
    };
    const auto rect=[&](unsigned left,unsigned top,unsigned right,unsigned bottom,uint8_t color) {
        for(unsigned y=top;y<=bottom;++y)for(unsigned x=left;x<=right;++x)paint(x,y,color);
    };
    // Original compose_background global write order, independent constants.
    rect(0,200,319,239,21);
    rect(0,0,319,199,20);
    rect(32,20,287,99,42);
    rect(32,100,287,179,21);
    rect(31,19,288,19,0);
    rect(31,180,288,180,40);
    rect(31,19,31,180,0);
    rect(288,19,288,180,40);
    compose_background(target);
    if(storage!=expected)throw std::runtime_error("ordered background/row alias/mask/guard mismatch");
    ++cases;
}
}
int main(){try{
    const uint8_t masks[]={0,1,3,15,20,42,63,64,85,128,170,192,254,255};
    for(unsigned layout=0;layout<6;++layout)for(uint8_t cm:masks)for(uint8_t pm:masks)run(layout,cm,pm);
    std::cout<<"PASS "<<cases<<" original globally ordered background cases: same/shifted/permuted destination-row aliases, arbitrary masks, linear and full storage guards\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
