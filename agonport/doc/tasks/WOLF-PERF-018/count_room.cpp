// Host-only work census using the exact unchanged control raycast and setup.
#include "build/r01/original/production/wolf3d_renderer.cpp"
#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <vector>
using namespace wolf3d_production;
namespace {
void require(bool value, const char *why) { if (!value) throw std::runtime_error(why); }
uint16_t u16(const std::vector<uint8_t> &b, size_t at) { return b.at(at) | uint16_t(b.at(at+1))<<8; }
uint32_t u32(const std::vector<uint8_t> &b, size_t at) { return u16(b,at) | uint32_t(u16(b,at+2))<<16; }
}
int main(int argc, char **argv) { try {
    require(argc==2,"expected exact room W3L");
    std::ifstream file(argv[1],std::ios::binary);
    const std::vector<uint8_t> b{std::istreambuf_iterator<char>(file),{}};
    require(b.size()>=64 && b[0]=='W' && b[1]=='3' && b[2]=='L' && b[3]=='1',"W3L identity");
    require(b[4]==1 && b[5]==0 && b[6]==0 && b[7]==1 && u16(b,14)==b.size(),"W3L version/extent/difficulty");
    WorldMirror world{};
    world.player={int32_t(u32(b,16)),int32_t(u32(b,20)),0};
    require(world.player.x==34*65536+32768 && world.player.y==36*65536+32768,"camera");
    world.door_count=b[8]; require(world.door_count<=W3P_MAX_DOORS,"door count");
    const size_t door_at=u16(b,26), map_at=u16(b,38);
    require(door_at==64 && door_at+world.door_count*10<=b.size() && map_at+4096+4==b.size(),"section extent");
    require(std::string(b.end()-4,b.end())=="E3L1","end marker");
    for(unsigned i=0;i<world.door_count;++i) {
        const size_t p=door_at+i*10;
        world.doors[i]={u16(b,p+5),b[p],b[p+1],b[p+2],b[p+3],b[p+4],b[p+7]};
    }
    uint64_t columns=0,reuses=0; unsigned minimum=256,maximum=0;
    for(unsigned pose=1;pose<=600;++pose) {
        world.player.angle=uint16_t((720*pose/600)%360);
        std::array<int32_t,256> heights{};
        std::array<uint8_t,256> tiles{},u{},sides{};
        const ViewState view=setup_view(world);
        require(cast_walls(world,b.data()+map_at,heights.data(),tiles.data(),u.data(),sides.data(),view)==RenderDetail::ok,"actual cast");
        std::array<int32_t,128> previous{};
        unsigned hits=0;
        for(unsigned c=0;c<256;++c) {
            if(heights[c]<=0) continue;
            const uint8_t tile=tiles[c];
            uint8_t id=tile;
            if(tile>=128 && tile<=191) {
                require((tile&63)<world.door_count,"door index");
                id=world.doors[tile&63].texture_id;
            }
            require(id==wall_texture_id(world,tile),"independent texture resolution");
            if(id<1 || id>127) continue;
            ++columns;
            if(previous[id]==heights[c]) ++hits;
            else previous[id]=heights[c];
        }
        reuses+=hits; minimum=std::min(minimum,hits);maximum=std::max(maximum,hits);
    }
    std::cout<<"{\"poses\":600,\"valid_columns\":"<<columns<<",\"eligible_reuses\":"<<reuses
        <<",\"remaining_setup_evaluations\":"<<columns-reuses<<",\"minimum_reuses_per_frame\":"<<minimum
        <<",\"maximum_reuses_per_frame\":"<<maximum<<"}\n";
} catch(const std::exception &error) { std::cerr<<error.what()<<'\n';return 1; } }
