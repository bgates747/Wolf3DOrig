// Actual grouped painter versus scalar pixels and independent lease/error oracle.
#include "wolf3d_renderer.cpp"
#include <array>
#include <iostream>
#include <stdexcept>
#include <utility>
#include <vector>
using namespace wolf3d_production;
namespace {
void check(bool ok) { if (!ok) throw std::runtime_error("group pixels/order/lease/error mismatch"); }
unsigned cases = 0;
uint8_t texel(unsigned id, unsigned x, unsigned y) {
    return static_cast<uint8_t>((id * 17u + x * 13u + y * 7u) & 63u);
}
struct Provider {
    unsigned fail_at, kind, calls = 0, active = 0;
    std::array<uint8_t, 4096> texture{};
    std::vector<std::pair<char,unsigned>> events;
    static RenderDetail acquire(void *p, uint16_t buffer, AssetSpan &out) {
        auto &self = *static_cast<Provider *>(p);
        check(buffer > 400 && buffer <= 400 + W3P_MAX_WALL_TEXTURE && self.active == 0);
        unsigned id = buffer - 400;
        self.events.emplace_back('a', id);
        ++self.calls;
        if (self.calls == self.fail_at && self.kind == 1) return RenderDetail::argument;
        self.active = id;
        for (unsigned y = 0; y < 64; ++y) for (unsigned x = 0; x < 64; ++x)
            self.texture[y*64+x] = texel(id,x,y);
        out = {self.texture.data(),4096,id};
        if (self.calls == self.fail_at && self.kind == 2) out.bytes = nullptr;
        if (self.calls == self.fail_at && (self.kind == 3 || self.kind == 5)) out.byte_count = 4095;
        return RenderDetail::ok;
    }
    static RenderDetail release(void *p, uint32_t lease) {
        auto &self = *static_cast<Provider *>(p);
        check(self.active == lease && lease != 0);
        self.events.emplace_back('r',lease); self.active = 0;
        return self.calls == self.fail_at && (self.kind == 4 || self.kind == 5)
            ? RenderDetail::argument : RenderDetail::ok;
    }
};
void run(unsigned seed, unsigned kind, unsigned fail_at, bool linear,
         uint8_t cm, uint8_t pm, bool with_stats) {
    WorldMirror world{}; world.door_count = 64;
    for (unsigned i=0; i<64; ++i)
        world.doors[i].texture_id = static_cast<uint8_t>((i*11u+seed*7u)%129u);
    std::array<int32_t,256> heights{};
    std::array<uint8_t,256> tiles{}, u{}, resolved{};
    std::array<bool,128> used{};
    const int32_t samples[] = {0,-1,1,2,3,7,159,160,161,200,4096,32767};
    for (unsigned c=0;c<256;++c) {
        heights[c] = seed==31 ? 0 : samples[(c*7u+seed)%12u];
        tiles[c] = static_cast<uint8_t>(c+seed*19u);
        u[c] = static_cast<uint8_t>((c*17u+seed)%64u);
        // Resolve independently from the encoded door/static tile domain.
        resolved[c] = tiles[c]>=128 && tiles[c]<192
            ? world.doors[tiles[c]-128].texture_id : tiles[c];
        if (heights[c]>0 && resolved[c]>=1 && resolved[c]<=W3P_MAX_WALL_TEXTURE)
            used[resolved[c]]=true;
    }
    constexpr unsigned stride = 352;
    std::vector<uint8_t> actual(stride*240+32), expected;
    for (unsigned i=0;i<actual.size();++i) actual[i]=static_cast<uint8_t>(i*29u+seed*13u);
    expected=actual;
    std::array<uintptr_t,240> rows{};
    for (unsigned y=0;y<240;++y)
        rows[y]=reinterpret_cast<uintptr_t>(actual.data()+16+((y*37u)%240u)*stride);
    RenderTarget target{linear ? actual.data()+16 : nullptr,linear ? nullptr : rows.data(),4,3,cm,pm};
    std::vector<std::pair<char,unsigned>> events;
    unsigned acquires=0, visited=0;
    RenderDetail detail=RenderDetail::ok;
    // Original ascending texture-group side effects are part of the contract.
    for (unsigned id=1;id<=W3P_MAX_WALL_TEXTURE;++id) {
        if (!used[id]) continue;
        ++visited; events.emplace_back('a',id);
        bool bad=visited==fail_at;
        if (bad && kind==1) { detail=RenderDetail::asset; break; }
        ++acquires;
        if (bad && (kind==2 || kind==3 || kind==5)) {
            events.emplace_back('r',id);
            detail=kind==5 ? RenderDetail::release : RenderDetail::bounds; break;
        }
        // Independent destination-pixel formulation; no cached membership loop.
        for (unsigned c=0;c<256;++c) {
            if (heights[c]<=0 || resolved[c]!=id) continue;
            const int top=80-heights[c]/2;
            const int first=top<0 ? 0 : top;
            const int bottom=top+heights[c];
            const int last=bottom>160 ? 160 : bottom;
            const int32_t step=4194304/heights[c];
            for (int y=first;y<last;++y) {
                int sy=((y-top)*step)>>16; if (sy>63) sy=63;
                uint8_t color=texel(id,u[c],static_cast<unsigned>(sy));
                unsigned at=linear ? 16+(20+static_cast<unsigned>(y))*320+32+c
                    : 16+(((20+static_cast<unsigned>(y))*37u)%240u)*stride+((4u+32u+c)^3u);
                expected[at]=linear ? color : static_cast<uint8_t>((expected[at]&pm)|(color&cm));
            }
        }
        events.emplace_back('r',id);
        if (bad && kind==4) { detail=RenderDetail::release; break; }
    }
    Provider provider{fail_at,kind,0,0,{}, {}};
    RenderResources resources{}; resources.wall_base=400;
    resources.assets={&provider,Provider::acquire,Provider::release};
    RenderStats stats{};
    RenderDetail got=draw_walls(world,resources,target,heights.data(),tiles.data(),u.data(),with_stats ? &stats : nullptr);
    check(got==detail && actual==expected && provider.events==events && provider.active==0);
    check(stats.wall_acquires==(with_stats ? acquires : 0));
    check(stats.sprite_acquires==0 && stats.weapon_acquires==0 && stats.hud_acquires==0);
    ++cases;
}
}
int main() {
    try {
        for (unsigned seed=0;seed<32;++seed) for (bool linear : {false,true})
            for (bool stats : {false,true}) {
                run(seed,0,0,linear,63,192,stats);
                run(seed,0,0,linear,85,170,stats);
                run(seed,0,0,linear,255,255,stats);
                for (unsigned kind=1;kind<=5;++kind) for (unsigned fail_at : {1u,2u,7u,64u,127u})
                    run(seed,kind,fail_at,linear,63,192,stats);
            }
        std::cout<<"PASS "<<cases<<" actual wall-group cases: pixels/guards, every encoded tile, doors/invalid IDs, nonpositive heights, ascending leases, refused/null/short/release-error paths, stats/null stats and native/linear rows\n";
    } catch(const std::exception &e) { std::cerr<<e.what()<<'\n'; return 1; }
}
