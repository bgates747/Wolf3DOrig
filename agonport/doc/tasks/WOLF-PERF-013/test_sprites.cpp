// Independent pixel equations for actual sprite kernel. No candidate lookup is
// used by the oracle: every expected sample derives from destination coordinates.
#include "wolf3d_renderer.cpp"
#include <algorithm>
#include <array>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace wolf3d_production;
namespace {
unsigned cases=0;
void check(bool ok) { if (!ok) throw std::runtime_error("sprite pixels/guards/lifecycle mismatch"); }
struct Assets { std::array<std::array<uint8_t,4096>,2> data{}; unsigned acquired=0,released=0,active=0; };
RenderDetail acquire(void *opaque,uint16_t id,AssetSpan &span) {
    auto &a=*static_cast<Assets*>(opaque);check(id>=100&&id<102&&a.active==0);
    ++a.acquired;++a.active;span={a.data[id-100].data(),4096,id};return RenderDetail::ok;
}
RenderDetail release(void *opaque,uint32_t lease) {
    auto &a=*static_cast<Assets*>(opaque);check(a.active==1&&lease>=100&&lease<102);
    ++a.released;--a.active;return RenderDetail::ok;
}
void run(unsigned size,int center,unsigned bias,unsigned xr,uint8_t cm,uint8_t pm,bool linear,bool overlap) {
    Assets assets;
    for(unsigned shape=0;shape<2;++shape) for(unsigned at=0;at<4096;++at)
        assets.data[shape][at]=static_cast<uint8_t>(at*137u+(at/64)*71u+shape*53u);
    assets.data[0][0]=0xff; assets.data[1][0]=0x81; // opaque mask-pair witnesses
    constexpr unsigned stride=352;
    std::vector<uint8_t> storage(stride*240+32),expected;
    for(unsigned i=0;i<storage.size();++i) storage[i]=static_cast<uint8_t>(i*17u+i/stride*31u);
    expected=storage;
    std::array<uintptr_t,240> rows{};
    for(unsigned y=0;y<240;++y) rows[y]=reinterpret_cast<uintptr_t>(storage.data()+16+((y*37u)%240u)*stride);
    RenderTarget target={linear?storage.data()+16:nullptr,linear?nullptr:rows.data(),bias,xr,cm,pm};
    std::array<int32_t,256> walls{};
    for(unsigned x=0;x<256;++x) {
        // Exact equality must occlude. Other columns alternate nearer/farther walls.
        switch(x%4) { case 0:walls[x]=static_cast<int32_t>(size);break;
        case 1:walls[x]=static_cast<int32_t>(size)-1;break;
        case 2:walls[x]=static_cast<int32_t>(size)+1;break;
        default:walls[x]=0;break; }
    }
    std::array<VisSprite,2> sprites{{{center,size,0,0,777},{center+5,size,1,0,777}}};
    const unsigned count=overlap?2:1;
    for(unsigned n=0;n<count;++n) {
        const auto &s=sprites[n];const int side=static_cast<int>(s.view_height);
        const int left=s.view_x-side/2,top=80-side/2;
        const int right=std::min(256,left+side),bottom=std::min(160,top+side);
        const int32_t step=(64<<16)/side;
        for(int y=std::max(0,top);y<bottom;++y) for(int x=std::max(0,left);x<right;++x) {
            if(walls[x]>=side) continue;
            const int sx=std::min(63,((x-left)*step)>>16);
            const int sy=std::min(63,((y-top)*step)>>16);
            const uint8_t pixel=assets.data[s.shape][sy*64+sx];
            if((pixel&0xc0u)==0) continue;
            const unsigned dx=32+static_cast<unsigned>(x),dy=20+static_cast<unsigned>(y);
            const unsigned at=linear?16+dy*320+dx:16+((dy*37u)%240u)*stride+((bias+dx)^xr);
            const uint8_t color=pixel&63u;
            expected[at]=linear?color:static_cast<uint8_t>((expected[at]&pm)|(color&cm));
        }
    }
    RenderResources resources{};resources.sprite_base=100;resources.assets={&assets,acquire,release};
    RenderStats stats{};
    check(draw_sprites(resources,target,walls.data(),sprites.data(),count,&stats)==RenderDetail::ok);
    check(storage==expected&&assets.active==0&&assets.acquired==count&&assets.released==count&&stats.sprite_acquires==count);
    ++cases;
}
}
int main() {
    try {
        for(unsigned size:{1u,2u,3u,7u,31u,63u,64u,65u,127u,159u,160u,161u,255u,256u,1023u,22272u})
          for(int center:{-23000,-1024,-128,0,1,64,128,255,256,512,23000})
            for(unsigned bias:{0u,1u,4u}) for(unsigned xr:{0u,1u,3u})
              for(bool linear:{false,true}) run(size,center,bias,xr,0x3f,0xc0,linear,true);
        // Exhaust native mask pairs with an opaque/transparent-patterned clipped pixel.
        for(unsigned cm=0;cm<256;++cm) for(unsigned pm=0;pm<256;++pm)
            run(1,static_cast<int>((cm+pm)%256),cm%5,pm%4,static_cast<uint8_t>(cm),static_cast<uint8_t>(pm),false,true);
        std::cout<<"PASS "<<cases<<" sprite cases: independent scalar equations, clipping/size extremes, wall equality, alpha/overlap order, all mask pairs, linear/noncontiguous rows, byte guards and lease counts\n";
    } catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}
}
