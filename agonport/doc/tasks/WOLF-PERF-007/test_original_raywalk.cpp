// Source arithmetic checks and independent analytic closed-room checks are
// separate evidence. This is not execution of a historical DOS binary.
#include "original_raywalk.h"
#include <array>
#include <cmath>
#include <cstdio>
#include <stdexcept>
using namespace wolf3d_production;
namespace ray=original_raywalk;
void require(bool v,const char *m) {if(!v)throw std::runtime_error(m);}
int main() {
 try {
    const float radtoint=static_cast<float>(1800.0/3.141592657);
    for(int i=0;i<450;++i) {
        const double tangent=std::tan((i+0.5)/radtoint);
        require(kWolfFineTangent[i]==static_cast<int32_t>(tangent*65536),"low original table value");
        require(kWolfFineTangent[899-i]==static_cast<int32_t>((1/tangent)*65536),"reciprocal original table value");
    }
    unsigned arithmetic=0;
    for(int32_t slope: {57,-57,65536,-65536,75098708,-75098708}) {
        for(uint32_t partial: {0u,1u,32768u,65535u}) {
            const int64_t exact=(int64_t(slope)*partial)/65536;
            require(ray::signed_bits(ray::partial_product(slope,uint16_t(partial)))==exact,"initial partial product truncation");
            ++arithmetic;
        }
    }
    for(uint32_t v: {0u,1u,0x7fffffffu,0x80000000u,0xffffffffu}) {
        for(unsigned shift: {1u,6u}) {
            const int64_t signed_value=ray::signed_bits(v);
            const int64_t divisor=int64_t(1)<<shift;
            const int64_t floor=signed_value>=0 ? signed_value/divisor : -((-signed_value+divisor-1)/divisor);
            require(ray::signed_bits(ray::arithmetic_shift(v,shift))==floor,"defined arithmetic shift");++arithmetic;
        }
    }
    require(ray::setup(0,12<<16,12<<16).yintercept==uint32_t(12<<16),"original upper partial WORD narrowing");
    std::array<uint8_t,4096> map{};
    for(int i=0;i<64;++i) {map[i]=map[63*64+i]=map[i*64]=map[i*64+63]=1;}
    WorldMirror world{};
    auto tile=[&](int x,int y) {return map[y*64+x];};
    unsigned geometric=0,near_corner=0;
    // No grid-aligned focal coordinates in this analytic-domain comparison;
    // the original WORD wrapping case is checked separately above.
    for(int x: {3,17,32,49,60}) for(int y: {4,19,33,47,59}) for(int fine=0;fine<3600;++fine) {
        const int32_t px=(x<<16)+23611,py=(y<<16)+41917;
        const auto hit=ray::trace(world,tile,fine,px,py);
        require(hit.valid && hit.found && hit.tile==1,"closed room ray failed");
        const double angle=(fine%900+0.5)/radtoint;
        double dx,dy;
        if(fine<900) {dx=std::cos(angle);dy=-std::sin(angle);}
        else if(fine<1800) {dx=-std::sin(angle);dy=-std::cos(angle);}
        else if(fine<2700) {dx=-std::cos(angle);dy=std::sin(angle);}
        else {dx=std::sin(angle);dy=std::cos(angle);}
        const double fx=px/65536.0,fy=py/65536.0;
        const double tx=((dx>0 ? 63.0 : 1.0)-fx)/dx;
        const double ty=((dy>0 ? 63.0 : 1.0)-fy)/dy;
        // Integer slope quantization can change which face owns a corner.
        // Do not claim an independent exact arithmetic oracle for that domain.
        if(std::abs(tx-ty)<0.01) {++near_corner;continue;}
        const bool vertical=tx<ty;
        require(hit.side==(vertical ? 0 : 1),"analytic room face mismatch");
        const double t=vertical ? tx : ty;
        require(std::abs(hit.x-(fx+dx*t)*65536)<128 && std::abs(hit.y-(fy+dy*t)*65536)<128,"analytic room intercept beyond fixed-point error bound");
        ++geometric;
    }
    unsigned doors=0;
    for(int fine: {0,900,1800,2700}) {
        world.door_count=1;world.doors[0].tile_x=32;world.doors[0].tile_y=32;world.doors[0].position=0;
        world.doors[0].vertical=(fine==0 || fine==1800);
        map[32*64+32]=0x80;
        const int32_t px=((fine==0?29:fine==1800?35:32)<<16)+32768;
        const int32_t py=((fine==900?35:fine==2700?29:32)<<16)+32768;
        const auto closed=ray::trace(world,tile,fine,px,py);
        require(closed.valid && closed.found && closed.tile==0x80,"original closed door missed");
        const uint16_t fraction=static_cast<uint16_t>(closed.side==0 ? closed.y : closed.x);
        world.doors[0].position=fraction;
        require(ray::trace(world,tile,fine,px,py).tile==0x80,"original aperture equality must hit");
        world.doors[0].position=uint16_t(fraction+1);
        require(ray::trace(world,tile,fine,px,py).tile!=0x80,"original aperture opening must pass");
        world.doors[0].position=65535;
        require(ray::trace(world,tile,fine,px,py).tile!=0x80,"open door blocked ray");
        map[32*64+32]=0;++doors;
    }
    world.door_count=0;world.pushwall.status=1;world.pushwall.texture=4;
    world.pushwall.origin_x=world.pushwall.current_x=32;world.pushwall.origin_y=world.pushwall.current_y=32;
    unsigned moving=0;
    for(int direction: {0,2,4,6}) {
        world.pushwall.direction=uint8_t(direction);
        const int fine=direction*450;
        const int32_t px=((direction==0?29:direction==4?35:32)<<16)+32768;
        const int32_t py=((direction==2?35:direction==6?29:32)<<16)+32768;
        world.pushwall.position=0;const auto before=ray::trace(world,tile,fine,px,py);
        world.pushwall.position=32;const auto after=ray::trace(world,tile,fine,px,py);
        require(before.found && before.moving && after.found && after.moving && after.tile==4,"moving wall missing");
        const int64_t a=std::abs(int64_t(before.x)-px)+std::abs(int64_t(before.y)-py);
        const int64_t b=std::abs(int64_t(after.x)-px)+std::abs(int64_t(after.y)-py);
        require(b>a,"original pushwall did not move away");++moving;
    }
    std::printf("PASS original tables900; word arithmetic%u; analytic room rays%u (near-corner cases outside independent analytic domain%u); door orientations/apertures%u; moving directions%u\n",arithmetic,geometric,near_corner,doors,moving);
 } catch(const std::exception &e) {std::fprintf(stderr,"FAIL %s\n",e.what());return 1;}
}
