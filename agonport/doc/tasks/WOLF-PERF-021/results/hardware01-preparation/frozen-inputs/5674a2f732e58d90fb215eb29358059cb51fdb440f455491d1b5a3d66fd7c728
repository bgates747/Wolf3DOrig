// Exercise actual local span/rectangle functions against a scalar pixel oracle.
#include "wolf3d_renderer.cpp"
#include <array>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace wolf3d_production;
namespace {
void require(bool ok,const char *s) {if(!ok)throw std::runtime_error(s);}
void write(std::ofstream &f,const void *p,size_t n) {f.write(static_cast<const char *>(p),static_cast<std::streamsize>(n));require(bool(f),"output failure");}
unsigned cases=0;
void span(std::ofstream &out,unsigned x,unsigned n,unsigned bias,unsigned xr,uint8_t cm,uint8_t pm,uint8_t color,unsigned seed) {
    std::array<std::array<uint8_t,512>,3> storage{},expected{};
    for(unsigned r=0;r<3;++r)for(unsigned i=0;i<512;++i)storage[r][i]=static_cast<uint8_t>(i*13+r*41+seed);
    expected=storage;
    uintptr_t rows[]={reinterpret_cast<uintptr_t>(storage[2].data()+64),reinterpret_cast<uintptr_t>(storage[0].data()+64),reinterpret_cast<uintptr_t>(storage[1].data()+64)};
    const RenderTarget target={nullptr,rows,bias,xr,cm,pm};
    for(unsigned i=0;i<n;++i) {
        const unsigned at=64+((bias+x+i)^xr);require(at<512,"oracle span bounds");
        expected[0][at]=static_cast<uint8_t>((expected[0][at]&pm)|(color&cm));
    }
    fill_span(target,x,1,n,color);
    require(storage==expected,"span byte/guard/mapping/mask mismatch");
    write(out,storage[0].data(),storage[0].size());++cases;
}
void rectangles(std::ofstream &out) {
    struct R {int l,t,r,b;};
    const R rects[]={{-3,-2,323,243},{0,0,319,239},{-10,2,-1,5},{320,1,330,8},{1,240,3,250},{4,4,3,5},{319,239,323,242},{32,20,287,179},{-2,4,3,8},{4,-5,8,3},{0,200,319,239}};
    for(const auto &r:rects) {
        std::array<std::array<uint8_t,512>,240> storage{},expected{};
        std::array<uintptr_t,240> rows{};
        for(unsigned y=0;y<240;++y)for(unsigned x=0;x<512;++x)storage[y][x]=static_cast<uint8_t>(y*7+x*11);
        expected=storage;
        for(unsigned y=0;y<240;++y)rows[y]=reinterpret_cast<uintptr_t>(storage[(y*37)%240].data()+64);
        const RenderTarget target={nullptr,rows.data(),4,3,0x96,0x6d};
        // Full logical-page membership oracle, independent of clipping loops.
        for(int y=0;y<240;++y)for(int x=0;x<320;++x)if(x>=r.l&&x<=r.r&&y>=r.t&&y<=r.b) {
            auto &v=expected[(static_cast<unsigned>(y)*37)%240][64+((4+static_cast<unsigned>(x))^3u)];
            v=static_cast<uint8_t>((v&0x6d)|(0xb6&0x96));
        }
        fill_rect(target,r.l,r.t,r.r,r.b,0xb6);
        require(storage==expected,"clipped rectangle/row/guard mismatch");
        for(const auto &row:storage) {
            write(out,row.data(),row.size());
        }
        ++cases;
    }
}
}
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    try {
        std::ofstream out(argv[1],std::ios::binary);require(bool(out),"cannot open output");
        // Direct zero spans previously did not inspect a row or pixel address.
        const RenderTarget empty={nullptr,nullptr,0xffffffffu,0xffffffffu,0xff,0xff};
        fill_span(empty,0xffffffffu,0xffffffffu,0,0xff);
        for(unsigned pm=0;pm<256;++pm)for(unsigned cm=0;cm<256;++cm)
            span(out,cm%17,8,cm%5,pm%4,static_cast<uint8_t>(cm),static_cast<uint8_t>(pm),static_cast<uint8_t>(cm*13+pm*7),cm^pm);
        const unsigned lengths[]={0,1,2,3,4,7,15,31,64,319,320};
        for(unsigned x=0;x<=320;++x)for(unsigned n:lengths)if(x+n<=320)
            for(unsigned bias:{0u,1u,4u})for(unsigned xr=0;xr<4;++xr)
                span(out,x,n,bias,xr,0x3f,0xc0,static_cast<uint8_t>(x+n),x*17+n);
        rectangles(out);
        std::vector<uint8_t> linear(320*240+32,0xa5),expected=linear;
        const RenderTarget copied={linear.data()+16,nullptr,17,3,0,0};
        fill_rect(copied,-3,-2,323,243,0xe7);
        std::fill(expected.begin()+16,expected.end()-16,0xe7);
        require(linear==expected,"linear path or guard changed");write(out,linear.data(),linear.size());
        std::cout<<"PASS "<<cases<<" direct span/rectangle cases,65536mask pairs,edge counts/zero/noncontiguous rows/guards and unchanged linear path\n";
    } catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}
}
