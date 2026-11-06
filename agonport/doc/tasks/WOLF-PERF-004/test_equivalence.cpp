// Reuse the real renderer fixture/provider, without altering its original tests.
#define main wp004_existing_renderer_main
#include "test_renderer.cpp"
#undef main
#include <array>

namespace {
bool transparent_hud = false;
RenderDetail acquire_case(void *opaque, uint16_t id, AssetSpan &span) {
    const RenderDetail rc = acquire(opaque, id, span);
    if (rc == RenderDetail::ok && transparent_hud && id >= fixture::kHudBase)
        std::memset(const_cast<uint8_t *>(span.bytes), 0, span.byte_count);
    return rc;
}
}

int main(int argc, char **argv) {
    if (argc != 3) return 2;
    try {
        std::ofstream frames(argv[1], std::ios::binary);
        std::ofstream states(argv[2], std::ios::binary);
        require(frames && states, "cannot open equivalence outputs");
        std::vector<uint8_t> map(fixture::kMapBytes);
        fixture::fill_map(map.data());
        std::array<std::array<std::vector<uint8_t>, 240>, 2> pages;
        std::array<std::array<uintptr_t, 240>, 2> rows{};
        for (unsigned page = 0; page < 2; ++page) {
            for (unsigned y = 0; y < 240; ++y) {
                auto &r = pages[page][y];
                r.resize(352 + (y % 3) * 16, 0xa5);
                rows[page][y] = reinterpret_cast<uintptr_t>(r.data() + 16);
                require((rows[page][y] & 3u) == 0, "unaligned fixture row");
                for (unsigned x = 0; x < 320; ++x)
                    r[16 + x] = static_cast<uint8_t>((((x + y + page) & 3u) << 6) | ((x * 7 + y * 3 + page) & 63u));
            }
        }
        for (unsigned step = 1; step <= 600; ++step) {
            const unsigned page = step & 1u;
            WorldMirror world = make_world(static_cast<int>((step - 1) % fixture::kScenarioCount));
            world.player.angle = static_cast<uint16_t>((720 * step / 600) % 360);
            transparent_hud = step % 100 == 0;
            if (transparent_hud) world.hud.palette_shift = 0;
            const WorldMirror before = world;
            std::vector<uint8_t> scratch(W3P_DIRECT_WORKSPACE_BYTES + 32, 0xa5);
            ProviderState provider{};
            RenderResources supplied = resources(map.data(), scratch.data() + 16, provider);
            supplied.workspace_bytes = W3P_DIRECT_WORKSPACE_BYTES;
            supplied.assets.acquire = acquire_case;
            const RenderTarget target = {nullptr, rows[page].data(), 0, 2, 0x3f, 0xc0};
            RenderStats stats{};
            require(render_world_direct(world, supplied, target, &stats) == RenderDetail::ok,
                    "direct equivalence render failed");
            require(std::memcmp(&world, &before, sizeof(world)) == 0, "renderer mutated world");
            require(provider.active == 0 && provider.acquired == provider.released,
                    "equivalence leaked asset lease");
            for (unsigned i = 0; i < 16; ++i)
                require(scratch[i] == 0xa5 && scratch[W3P_DIRECT_WORKSPACE_BYTES + 16 + i] == 0xa5,
                        "scratch guard changed");
            // Check both pages each time, including the currently unrendered page.
            for (unsigned p = 0; p < 2; ++p) for (unsigned y = 0; y < 240; ++y) {
                const auto &r = pages[p][y];
                for (unsigned x = 0; x < 320; ++x)
                    require((r[16 + x] & 0xc0) == (((x + y + p) & 3u) << 6), "sync bits changed");
                for (unsigned x = 0; x < 16; ++x) require(r[x] == 0xa5, "row prefix changed");
                for (size_t x = 336; x < r.size(); ++x) require(r[x] == 0xa5, "row suffix changed");
            }
            for (unsigned y = 0; y < 240; ++y) {
                uint8_t decoded[320];
                for (unsigned x = 0; x < 320; ++x) {
                    decoded[x] = pages[page][y][16 + (x ^ 2u)] & 63u;
                    if (transparent_hud && y >= 200) require(decoded[x] == 21, "transparent HUD background stale");
                }
                write_all(frames, decoded, sizeof(decoded));
            }
            write_all(states, supplied.workspace + W3P_DIRECT_WALL_HEIGHT_OFFSET,
                      W3P_DIRECT_SPRITE_ARENA_OFFSET - W3P_DIRECT_WALL_HEIGHT_OFFSET);
            write_all(states, reinterpret_cast<const uint8_t *>(&stats), sizeof(stats));
        }
        std::cout << "PASS 600 direct frames / 300 scripted degree headings: alternating independent rows/pages, sync/guards/world/leases and transparent HUD\n";
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
