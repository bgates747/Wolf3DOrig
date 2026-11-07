#ifndef WOLF007_ORIGINAL_RAYWALK_H
#define WOLF007_ORIGINAL_RAYWALK_H

#include <stdint.h>
#include "wolf3d_world_mirror.h"
#include "original_tangents.inc"

namespace wolf3d_production {
namespace original_raywalk {

// Original WL_DR_A.ASM word/long arithmetic, expressed without signed overflow.
inline int32_t signed_bits(uint32_t value) {
    return (value & 0x80000000u) ? -1 - static_cast<int32_t>(~value)
                                 : static_cast<int32_t>(value);
}
inline int high_word(uint32_t value) {
    const int high = static_cast<int>(value >> 16);
    return high >= 32768 ? high - 65536 : high;
}
inline uint32_t arithmetic_shift(uint32_t value, unsigned bits) {
    return (value >> bits) | ((value & 0x80000000u) ? (~uint32_t(0) << (32-bits)) : 0u);
}
inline uint32_t partial_product(int32_t slope, uint16_t partial) {
    const uint32_t magnitude = slope < 0 ? uint32_t(0)-static_cast<uint32_t>(slope)
                                         : static_cast<uint32_t>(slope);
    const uint32_t scaled = static_cast<uint32_t>((uint64_t(magnitude)*partial) >> 16);
    return slope < 0 ? uint32_t(0)-scaled : scaled;
}

struct Ray {
    int step_x, step_y;
    int32_t xstep, ystep;
    int xtile, ytile;
    uint32_t xintercept, yintercept;
};

inline Ray setup(int fine, int32_t px, int32_t py) {
    Ray r{};
    uint16_t xp,yp;
    const uint16_t xd=static_cast<uint16_t>(px), yd=static_cast<uint16_t>(py);
    // Original WORD upper partial wraps to zero on exact grid alignment.
    const uint16_t xu=static_cast<uint16_t>(65536u-xd), yu=static_cast<uint16_t>(65536u-yd);
    if (fine < 900) {
        r.step_x=1; r.step_y=-1;
        r.xstep=kWolfFineTangent[899-fine]; r.ystep=-kWolfFineTangent[fine]; xp=xu;yp=yd;
    } else if (fine < 1800) {
        r.step_x=-1; r.step_y=-1;
        r.xstep=-kWolfFineTangent[fine-900]; r.ystep=-kWolfFineTangent[1799-fine]; xp=xd;yp=yd;
    } else if (fine < 2700) {
        r.step_x=-1; r.step_y=1;
        r.xstep=-kWolfFineTangent[2699-fine]; r.ystep=kWolfFineTangent[fine-1800]; xp=xd;yp=yu;
    } else {
        r.step_x=1; r.step_y=1;
        r.xstep=kWolfFineTangent[fine-2700]; r.ystep=kWolfFineTangent[3599-fine]; xp=xu;yp=yu;
    }
    r.xtile=high_word(static_cast<uint32_t>(px))+r.step_x;
    r.ytile=high_word(static_cast<uint32_t>(py))+r.step_y;
    r.yintercept=static_cast<uint32_t>(py)+partial_product(r.ystep,xp);
    r.xintercept=static_cast<uint32_t>(px)+partial_product(r.xstep,yp);
    return r;
}

struct Hit {
    bool found, valid;
    int32_t x,y;
    int map_x,map_y,step_x,step_y;
    uint8_t side,tile,u;
    bool moving;
};

template<class TileAt>
uint8_t logical_tile(const WorldMirror &world, TileAt tile_at, int x,int y) {
    if (x<0 || y<0 || x>=64 || y>=64) return 1;
    const PushwallState &w=world.pushwall;
    if (w.status==1) {
        if (x==w.current_x && y==w.current_y) return uint8_t(w.texture|0xc0u);
        int dx=0,dy=0;
        if (w.direction==0) dx=1;
        else if (w.direction==2) dy=-1;
        else if (w.direction==4) dx=-1;
        else if (w.direction==6) dy=1;
        if (x==int(w.current_x)+dx && y==int(w.current_y)+dy) return w.texture;
    }
    // Caller supplies existing completed-wall overlays and cleared corridor.
    return tile_at(x,y);
}

template<class TileAt>
Hit trace(const WorldMirror &world, TileAt tile_at, int fine,int32_t px,int32_t py) {
    Ray r=setup(fine,px,py);
    Hit result{};result.valid=true;result.step_x=r.step_x;result.step_y=r.step_y;
    bool check_vertical=true;
    for (unsigned crossed=0;crossed<128;++crossed) {
        bool vertical;
        if (check_vertical) {
            const int yi=high_word(r.yintercept);
            vertical=!(r.step_y<0 ? yi<=r.ytile : yi>=r.ytile);
        } else {
            const int xi=high_word(r.xintercept);
            vertical=(r.step_x<0 ? xi<=r.xtile : xi>=r.xtile);
        }
        const int mx=vertical ? r.xtile : high_word(r.xintercept);
        const int my=vertical ? high_word(r.yintercept) : r.ytile;
        const uint8_t tile=logical_tile(world,tile_at,mx,my);
        uint32_t across=vertical ? r.yintercept : r.xintercept;
        const int32_t slope=vertical ? r.ystep : r.xstep;
        uint32_t plane=static_cast<uint32_t>(vertical ? r.xtile : r.ytile)<<16;
        bool hit=tile!=0;
        const bool moving=tile>=0xc0;
        const bool door=tile>=0x80 && tile<0xc0;
        if (hit && (door || moving)) {
            uint32_t offset;
            if (moving) {
                const uint32_t product=static_cast<uint32_t>(slope)*world.pushwall.position;
                offset=arithmetic_shift(product,6);
            } else {
                if ((tile & 0x7fu)>=world.door_count) {result.valid=false;return result;}
                offset=arithmetic_shift(static_cast<uint32_t>(slope),1);
            }
            const uint32_t adjusted=across+offset;
            hit=high_word(adjusted)==high_word(across);
            if (door && hit) hit=static_cast<uint16_t>(adjusted)>=world.doors[tile&0x7fu].position;
            if (hit) {
                across=adjusted;
                if (door) plane+=0x8000u;
                else {
                    const uint32_t amount=uint32_t(world.pushwall.position)<<10;
                    plane+=(vertical ? r.step_x : r.step_y)<0 ? 65536u-amount : amount;
                }
            }
        } else if (hit && (vertical ? r.step_x : r.step_y)<0) plane+=65536u;
        if (hit) {
            uint8_t u=static_cast<uint8_t>(static_cast<uint16_t>(across)>>10);
            if (door) u=static_cast<uint8_t>(static_cast<uint16_t>(across-world.doors[tile&0x7fu].position)>>10);
            else if (vertical ? r.step_x<0 : r.step_y>0) u=uint8_t(63-u);
            result.found=true;result.x=signed_bits(vertical ? plane : across);
            result.y=signed_bits(vertical ? across : plane);result.map_x=mx;result.map_y=my;
            result.side=vertical ? 0 : 1;result.tile=moving ? world.pushwall.texture : tile;
            result.u=u;result.moving=moving;return result;
        }
        if (vertical) {
            r.xtile+=r.step_x;r.yintercept+=static_cast<uint32_t>(r.ystep);check_vertical=true;
        } else {
            r.ytile+=r.step_y;r.xintercept+=static_cast<uint32_t>(r.xstep);check_vertical=false;
        }
    }
    return result;
}

} // namespace original_raywalk
} // namespace wolf3d_production
#endif
