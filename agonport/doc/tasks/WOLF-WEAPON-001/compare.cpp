// Compare the actual Wolf weapon draw with the retained VGA64 bitmap plot model.
// Include the renderer so the control uses the production weapon entry point.
#include "../../../vdplet/production/wolf3d_renderer.cpp"
#include "stock.hpp"

#include <algorithm>
#include <array>
#include <cstdio>
#include <fstream>
#include <stdexcept>
#include <string_view>
#include <time.h>
#include <vector>

namespace {
using namespace wolf3d_production;

constexpr int first_shape = 416;
constexpr int shape_count = 20;
constexpr int source_bytes = kTextureSize * kTextureSize;
constexpr int width = W3P_SCREEN_WIDTH;
constexpr int height = W3P_SCREEN_HEIGHT;
constexpr int extent = kViewHeight + 1;
constexpr int left = kViewX + (kViewWidth - extent + 1) / 2;
constexpr int top = kViewY;
constexpr std::array<uint8_t, 10> shifts{0, 1, 2, 3, 4, 5, 6, 129, 130, 131};

struct Picture {
    int x, y, w, h;
    std::vector<uint8_t> pixels;
};

Picture prepare(const uint8_t *source) {
    Picture result{left, top, extent, kViewHeight, {}};
    constexpr int step = (kTextureSize << 16) / extent;
    for (int y = 0; y < result.h; ++y) {
        const int row = std::min(y * step >> 16, kTextureSize - 1);
        for (int x = 0; x < result.w; ++x) {
            const int column = std::min(x * step >> 16, kTextureSize - 1);
            result.pixels.push_back(source[row * kTextureSize + column]);
        }
    }
    return result;
}

Picture crop(const Picture &source) {
    int l = source.w, t = source.h, r = 0, b = 0;
    for (int y = 0; y < source.h; ++y) {
        for (int x = 0; x < source.w; ++x) {
            if (!(source.pixels[y * source.w + x] & 0xc0)) continue;
            l = std::min(l, x);
            t = std::min(t, y);
            r = std::max(r, x + 1);
            b = std::max(b, y + 1);
        }
    }
    if (l >= r || t >= b) throw std::runtime_error("Empty weapon frame");
    Picture result{source.x + l, source.y + t, r - l, b - t, {}};
    for (int y = t; y < b; ++y) {
        const auto start = source.pixels.begin() + y * source.w;
        result.pixels.insert(result.pixels.end(), start + l, start + r);
    }
    return result;
}

void plot(stock::StockSurface &surface, const Picture &picture) {
    const stock::Bitmap bitmap(picture.w, picture.h, picture.pixels.data());
    surface.draw_plain(bitmap,
                       {kViewX, kViewY, kViewX + kViewWidth - 1, kViewY + kViewHeight - 1},
                       picture.x, picture.y);
}

RenderDetail acquire(void *source, uint16_t id, AssetSpan &span) {
    if (id < W3P_DEFAULT_SPRITE_BASE + first_shape ||
        id >= W3P_DEFAULT_SPRITE_BASE + first_shape + shape_count)
        return RenderDetail::asset;
    span = {static_cast<const uint8_t *>(source) +
            (id - W3P_DEFAULT_SPRITE_BASE - first_shape) * source_bytes, source_bytes, 1};
    return RenderDetail::ok;
}

RenderDetail release(void *, uint32_t lease) {
    return lease == 1 ? RenderDetail::ok : RenderDetail::release;
}

RenderTarget rows_for(stock::StockSurface &surface, std::array<uintptr_t, height> &rows) {
    for (int y = 0; y < height; ++y)
        rows[y] = reinterpret_cast<uintptr_t>(surface.pixels().data() + width * y);
    return {nullptr, rows.data(), 0, 2, 0x3f, 0xc0};
}

uint64_t cpu_ns() {
    timespec time{};
    if (clock_gettime(CLOCK_THREAD_CPUTIME_ID, &time) != 0)
        throw std::runtime_error("Thread clock unavailable");
    return 1000000000ull * time.tv_sec + time.tv_nsec;
}

template<class Draw> double measure(Draw draw, int repeats) {
    draw();
    const uint64_t start = cpu_ns();
    for (int i = 0; i < repeats; ++i) {
        draw();
        asm volatile("" ::: "memory");
    }
    return double(cpu_ns() - start) / repeats;
}

void compare(int shape, const uint8_t *source, const RenderResources &resources, bool timed) {
    const auto start = cpu_ns();
    const Picture full = prepare(source);
    const Picture cropped = crop(full);
    const auto preparation_ns = cpu_ns() - start;
    stock::StockSurface expected, actual;
    std::array<uintptr_t, height> expected_rows{}, actual_rows{};
    const RenderTarget reference = rows_for(expected, expected_rows);
    const RenderTarget model = rows_for(actual, actual_rows);
    WorldMirror world{};
    world.view_weapon_shape = static_cast<int16_t>(shape);
    const auto draw_control = [&] {
        if (draw_view_weapon(world, resources, reference, nullptr) != RenderDetail::ok)
            throw std::runtime_error("Production weapon refused input");
    };

    for (uint8_t shift : shifts) {
        for (unsigned page = 0; page < 2; ++page) {
            for (size_t i = 0; i < expected.pixels().size(); ++i)
                expected.pixels()[i] = 0xc0u | ((37u * i + 57u * page) & 63u);
            std::copy(expected.pixels().begin(), expected.pixels().end(), actual.pixels().begin());
            draw_control();
            apply_palette_shift(reference, shift);
            apply_palette_shift(model, shift);
            const auto background = actual.pixels();
            for (const Picture *prepared : {&full, &cropped}) {
                Picture mapped = *prepared;
                for (auto &pixel : mapped.pixels) {
                    if (pixel & 0xc0)
                        pixel = (pixel & 0xc0) | palette_shift_color(pixel & 63, shift);
                }
                std::copy(background.begin(), background.end(), actual.pixels().begin());
                plot(actual, mapped);
                if (actual.pixels() != expected.pixels())
                    throw std::runtime_error("Whole-surface or scanout byte mismatch");
            }
        }
    }

    if (!timed) return;
    for (int trial = 0; trial < 6; ++trial) {
        std::array<double, 3> ns{};
        for (int order = 0; order < 3; ++order) {
            const int method = (trial & 1) ? 2 - order : order;
            if (method == 0) ns[method] = measure(draw_control, 250);
            if (method == 1) ns[method] = measure([&] { plot(actual, full); }, 250);
            if (method == 2) ns[method] = measure([&] { plot(actual, cropped); }, 250);
        }
        std::printf("%d,%d,%zu,%d,%d,%zu,%llu,%.2f,%.2f,%.2f\n", shape, trial, full.pixels.size(),
                    cropped.w, cropped.h, cropped.pixels.size(),
                    static_cast<unsigned long long>(preparation_ns), ns[0], ns[1], ns[2]);
    }
}
}  // namespace

int main(int argc, char **argv) {
    if (argc < 2 || argc > 3 || (argc == 3 && std::string_view(argv[2]) != "--time")) return 2;
    try {
        std::array<uint8_t, shape_count * source_bytes> frames{};
        std::ifstream stream(argv[1], std::ios::binary);
        stream.read(reinterpret_cast<char *>(frames.data()), frames.size());
        if (!stream || stream.peek() != std::char_traits<char>::eof())
            throw std::runtime_error("Incomplete or oversized weapon frame set");
        const RenderResources resources{nullptr, 0, nullptr, 0, 0, W3P_DEFAULT_SPRITE_BASE,
                                        0, {frames.data(), acquire, release}};
        const bool timed = argc == 3;
        if (timed)
            std::puts("shape,trial,full_bytes,cropped_width,cropped_height,cropped_bytes,preparation_ns,"
                      "control_cpu_ns,full_plot_cpu_ns,cropped_plot_cpu_ns");
        for (int i = 0; i < shape_count; ++i)
            compare(first_shape + i, frames.data() + i * source_bytes, resources, timed);
        std::fprintf(stderr, "PASS: %zu whole-surface comparisons across %d shapes\n",
                     shifts.size() * shape_count * 2 * 2, shape_count);
        return 0;
    } catch (const std::exception &error) {
        std::fprintf(stderr, "%s\n", error.what());
        return 1;
    }
}
