// Census only: exact compose_background in a telemetry-only renderer copy.
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

struct SpanCounts { uint64_t calls{}, bytes{}, eligible_calls{}, eligible_bytes{}; };
static SpanCounts counts;
static void count_span(bool linear, uint32_t start, uint32_t pixel_xor, uint32_t count) {
    ++counts.calls; counts.bytes += count;
    if (!linear && count != 0 && pixel_xor <= 3 && (start & 3u) == 0 &&
        (count & 3u) == 0 && count <= UINT32_MAX - start) {
        ++counts.eligible_calls; counts.eligible_bytes += count;
    }
}
#include "production/wolf3d_renderer.cpp"
using namespace wolf3d_production;
static void require(bool value, const char *why) { if (!value) throw std::runtime_error(why); }

int main(int argc, char **argv) { try {
    require(argc == 2, "expected new pose CSV path");
    std::array<std::vector<uint8_t>, 240> storage;
    std::array<uintptr_t, 240> rows{};
    for (unsigned y = 0; y < 240; ++y) {
        storage[y].resize(352 + (y % 3) * 16, 0xa5);
        rows[y] = reinterpret_cast<uintptr_t>(storage[y].data() + 16);
        for (unsigned x = 0; x < 320; ++x)
            storage[y][16+x] = uint8_t((((x+y)&3u)<<6) | ((x*7+y*3)&63u));
    }
    const RenderTarget target{nullptr, rows.data(), 0, 2, 0x3f, 0xc0};
    std::vector<uint8_t> first;
    std::ofstream csv(argv[1]); require(bool(csv), "CSV open failed");
    csv << "pose,angle,calls,bytes,eligible_calls,eligible_bytes\n";
    for (unsigned pose = 1; pose <= 600; ++pose) {
        const SpanCounts before = counts;
        compose_background(target);
        const SpanCounts delta{counts.calls-before.calls, counts.bytes-before.bytes,
            counts.eligible_calls-before.eligible_calls, counts.eligible_bytes-before.eligible_bytes};
        // Independent dimensions/accounting of this exact background domain.
        require(delta.calls == 886 && delta.bytes == 77640, "background call/byte accounting changed");
        require(delta.eligible_calls == 560 && delta.eligible_bytes == 76800, "eligible accounting changed");
        std::vector<uint8_t> output;
        for (unsigned y = 0; y < 240; ++y) {
            const auto &row = storage[y];
            for (unsigned x = 0; x < 16; ++x) require(row[x] == 0xa5, "prefix guard changed");
            for (size_t x = 336; x < row.size(); ++x) require(row[x] == 0xa5, "suffix guard changed");
            for (unsigned x = 0; x < 320; ++x) {
                require((row[16+x] & 0xc0u) == (((x+y)&3u)<<6), "sync bits changed");
                output.push_back(row[16+x]);
            }
        }
        if (pose == 1) first = output;
        else require(output == first, "pose-independent background output changed");
        csv << pose << ',' << (720*pose/600)%360 << ',' << delta.calls << ',' << delta.bytes
            << ',' << delta.eligible_calls << ',' << delta.eligible_bytes << '\n';
    }
    std::cout << "{\"background_calls\":600,\"span_calls\":" << counts.calls
        << ",\"span_bytes\":" << counts.bytes << ",\"eligible_calls\":" << counts.eligible_calls
        << ",\"eligible_bytes\":" << counts.eligible_bytes
        << ",\"full_scene_executed\":false,\"candidate_executed\":false}" << '\n';
} catch (const std::exception &error) { std::cerr << error.what() << '\n'; return 1; } }
