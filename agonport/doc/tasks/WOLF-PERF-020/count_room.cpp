// Host-only work census using the exact unchanged control raycast and setup.
#include "../WOLF-PERF-019/build/r01/original/production/wolf3d_renderer.cpp"
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
    require(argc==3,"expected exact room W3L and output directory");
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
    std::ofstream csv(std::string(argv[2])+"/poses.csv");
    require(bool(csv),"new CSV output");
    csv<<"step,angle,wall_pixels,post_source_reads,avoided_source_reads,groups,multi_column_groups,max_width\n";
    uint64_t total_pixels=0,total_reads=0,total_groups=0,total_multi=0;
    unsigned widest=0;
    for(unsigned pose=1;pose<=600;++pose) {
        world.player.angle=uint16_t((720*pose/600)%360);
        std::array<int32_t,256> heights{};
        std::array<uint8_t,256> tiles{},u{},sides{};
        const ViewState view=setup_view(world);
        require(cast_walls(world,b.data()+map_at,heights.data(),tiles.data(),u.data(),sides.data(),view)==RenderDetail::ok,"actual cast");
        const auto clipped=[&](int h) {
            const int top=kCenterY-h/2;
            return std::max(0,std::min(top+h,kViewHeight)-std::max(top,0));
        };
        uint64_t pixels=0,reads=0,group_pixels=0;
        unsigned groups=0,multi=0,maximum=0;
        for(unsigned c=0;c<256;++c) {
            if(heights[c]<=0)continue;
            const auto id=wall_texture_id(world,tiles[c]);
            if(id<1||id>127)continue;
            require(u[c]<64,"actual U domain");pixels+=clipped(heights[c]);
        }
        for(unsigned c=0;c<256;) {
            const auto id=wall_texture_id(world,tiles[c]);
            if(heights[c]<=0||id<1||id>127){++c;continue;}
            unsigned width=1;
            while(c+width<256&&heights[c+width]==heights[c]&&u[c+width]==u[c]&&
                  wall_texture_id(world,tiles[c+width])==id)++width;
            const unsigned count=unsigned(clipped(heights[c]));
            if(count!=0) {reads+=count;group_pixels+=uint64_t(count)*width;
                ++groups;multi+=width>1;maximum=std::max(maximum,width);}
            c+=width;
        }
        require(group_pixels==pixels&&reads<=pixels,"independent per-column/group work identity");
        total_pixels+=pixels;total_reads+=reads;total_groups+=groups;total_multi+=multi;
        widest=std::max(widest,maximum);
        csv<<pose<<','<<world.player.angle<<','<<pixels<<','<<reads<<','<<(pixels-reads)<<','
            <<groups<<','<<multi<<','<<maximum<<'\n';
    }
    std::cout<<"{\"poses\":600,\"wall_pixel_stores_unchanged\":"<<total_pixels
        <<",\"scalar_texture_reads\":"<<total_pixels<<",\"post_texture_reads_if_admitted\":"<<total_reads
        <<",\"avoided_texture_reads_if_admitted\":"<<(total_pixels-total_reads)
        <<",\"groups\":"<<total_groups<<",\"multi_column_groups\":"<<total_multi
        <<",\"maximum_width\":"<<widest<<"}\n";
} catch(const std::exception &error) { std::cerr<<error.what()<<'\n';return 1; } }
