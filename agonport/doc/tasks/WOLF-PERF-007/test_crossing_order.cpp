// Hand-derived transcripts from pinned WL_DR_A.ASM entry/partial/check flow.
// No historical x86 executable oracle is claimed. Separate from analytic rays.
#include "original_raywalk.h"
#include <cstdio>
#include <stdexcept>
using namespace wolf3d_production;
struct Example {int fine; int32_t x,y; int cells[3][2]; uint8_t last_side;};
int main() {
    const Example examples[]={
        {450,  (3<<16)+32768,(4<<16)+32768,{{3,3},{4,3},{4,2}},1},
        {1350, (3<<16)+32768,(4<<16)+32768,{{2,4},{2,3},{1,3}},0},
        {2250, (3<<16)+32768,(4<<16)+32768,{{3,5},{2,5},{2,6}},1},
        {3150, (3<<16)+32768,(4<<16)+32768,{{4,4},{4,5},{5,5}},0},
        // Original upper partial65536 narrows to WORD0 at a grid coordinate.
        {0,    3<<16,4<<16,{{4,4},{3,3},{5,3}},0},
        {900,  3<<16,4<<16,{{2,4},{3,3},{2,2}},1},
    };
    try {
        WorldMirror world{};
        for(const auto &e:examples) {
            unsigned visited=0;
            auto tile=[&](int x,int y)->uint8_t {
                if(visited>=3 || x!=e.cells[visited][0] || y!=e.cells[visited][1])
                    throw std::runtime_error("original crossing transcript differs");
                return ++visited==3 ? 1 : 0;
            };
            const auto h=original_raywalk::trace(world,tile,e.fine,e.x,e.y);
            if(!h.valid || !h.found || visited!=3 || h.side!=e.last_side)
                throw std::runtime_error("original crossing terminal state differs");
        }
        std::puts("PASS 6 hand-derived original quadrant/grid-alignment crossing transcripts; no historical executable-oracle claim");
    } catch(const std::exception &e) {std::fprintf(stderr,"FAIL %s\n",e.what());return 1;}
}
