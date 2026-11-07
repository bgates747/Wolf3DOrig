// Independent scalar oracle for the actual private fill_span implementation.
#include "wolf3d_renderer.cpp"
#include <array>
#include <cstring>
#include <iostream>
#include <new>
#include <stdexcept>
#include <vector>
using namespace wolf3d_production;
namespace {
uint64_t cases = 0;
void require(bool value, const char *why) { if (!value) throw std::runtime_error(why); }

void one(uint32_t x, uint32_t bias, uint32_t pixel_xor, uint32_t count,
         uint8_t color, uint8_t cm, uint8_t pm, bool linear = false) {
    constexpr unsigned prefix = 32;
    std::vector<uint8_t> actual(1536);
    for (unsigned i = 0; i < actual.size(); ++i) actual[i] = uint8_t(i*31u + (i>>4)*17u);
    auto expected = actual;
    std::array<uintptr_t, 2> rows = {{reinterpret_cast<uintptr_t>(actual.data()+prefix),
                                   reinterpret_cast<uintptr_t>(actual.data()+prefix+19)}};
    const RenderTarget frame{linear ? actual.data()+prefix : nullptr,
                             linear ? nullptr : rows.data(), bias, pixel_xor, cm, pm};
    // The oracle enumerates logical pixels in original order and computes
    // addresses from the original formula; it has no fast-path predicate.
    for (uint32_t i = 0; i < count; ++i) {
        const uint32_t at = linear ? prefix + 320u + x + i
                                  : prefix + 19u + ((bias + x + i) ^ pixel_xor);
        require(at < expected.size(), "oracle input outside allocation");
        expected[at] = linear ? color : uint8_t((expected[at]&pm) | (color&cm));
    }
    fill_span(frame, x, 1, count, color);
    require(actual == expected, "span bytes or surrounding guard mismatch");
    ++cases;
}

void aliased_sequence(unsigned layout, uint8_t cm, uint8_t pm, uint32_t pixel_xor) {
    std::vector<uint8_t> actual(2048);
    for (unsigned i = 0; i < actual.size(); ++i) actual[i] = uint8_t(i*43u + (i>>5));
    auto expected = actual;
    std::array<uintptr_t, 4> rows{};
    std::array<unsigned, 4> offsets{};
    for (unsigned y = 0; y < 4; ++y) {
        offsets[y] = 32 + (layout == 0 ? 0 : layout == 1 ? y*13 : ((y*3)%4)*352);
        rows[y] = reinterpret_cast<uintptr_t>(actual.data()+offsets[y]);
    }
    const RenderTarget frame{nullptr, rows.data(), 4, pixel_xor, cm, pm};
    for (unsigned pass = 0; pass < 3; ++pass) for (unsigned y = 0; y < 4; ++y) {
        const uint32_t x = pass == 1 ? 1 : 0;
        const uint32_t count = pass == 1 ? 31 : 320;
        const uint8_t color = uint8_t(pass*73u+y*31u);
        for (uint32_t i = 0; i < count; ++i) {
            const unsigned at = offsets[y] + ((4+x+i)^pixel_xor);
            expected[at] = uint8_t((expected[at]&pm) | (color&cm));
        }
        fill_span(frame, x, y, count, color);
        require(actual == expected, "ordered aliased-row sequence differs");
    }
    ++cases;
}

void metadata_alias(uint8_t cm, uint8_t pm) {
    // The descriptor is non-const storage passed by const reference. Cached
    // metadata must not be reread after byte stores overwrite its representation.
    alignas(RenderTarget) std::array<uint8_t, 512> bytes{};
    for (unsigned i = 0; i < bytes.size(); ++i) bytes[i] = uint8_t(i*19u);
    std::array<uintptr_t, 1> rows = {{reinterpret_cast<uintptr_t>(bytes.data()+32)}};
    auto *frame = new(bytes.data()+64) RenderTarget{nullptr, rows.data(), 0, 2, cm, pm};
    auto expected = bytes;
    for (unsigned x = 0; x < 128; ++x) {
        const unsigned at = 32 + (x^2u);
        expected[at] = uint8_t((expected[at]&pm) | (0xb5u&cm));
    }
    fill_span(*frame, 0, 0, 128, 0xb5);
    // Do not read the overwritten typed descriptor again.
    require(bytes == expected, "span reloaded overwritten target metadata");
    ++cases;
}
}

int main() { try {
    const RenderTarget empty{nullptr, nullptr, UINT32_MAX, UINT32_MAX, 255, 255};
    fill_span(empty, UINT32_MAX, UINT32_MAX, 0, 255);
    ++cases; // Native zero count must not fetch rows[y] or form a pixel pointer.
    const uint32_t counts[] = {0,1,2,3,4,7,8,12,15,16,31,32,63,64,128,256};
    const uint32_t biases[] = {0,1,2,3,4,8,17,32};
    const uint32_t xors[] = {0,1,2,3,4,7,15,63,127};
    const uint8_t masks[] = {0,1,20,42,63,64,85,128,170,192,254,255};
    for (uint32_t n : counts) for (uint32_t bias : biases) for (uint32_t px : xors)
        for (uint32_t x : {0u,1u,4u,31u})
            one(x,bias,px,n,uint8_t(n*13u+px),0x3f,0xc0);
    // All65536 mask pairs with varying colour; not an exhaustive colour triple.
    for (unsigned cm=0; cm<256; ++cm) for (unsigned pm=0; pm<256; ++pm)
        one(0,4,2,16,uint8_t(cm*17u+pm*31u),uint8_t(cm),uint8_t(pm));
    for (uint8_t cm : masks) for (uint8_t pm : masks) {
        for (unsigned layout=0; layout<3; ++layout) for (uint32_t px : xors)
            aliased_sequence(layout,cm,pm,px);
        metadata_alias(cm,pm);
        for (uint8_t color : {uint8_t(0),uint8_t(63),uint8_t(128),uint8_t(255)})
            one(0,0,0,320,color,cm,pm,true);
    }
    // Inherit defined uint32 initial-addition wrapping; this is not allocation
    // admission. All resulting mapped accesses in these test inputs are valid.
    one(4,UINT32_MAX-3u,2,16,0xff,0x3f,0xc0);
    one(8,UINT32_MAX-3u,3,16,0x15,0xff,0x80);
    std::cout << "PASS " << cases << " independent actual span cases: complete/partial quads, arbitrary XOR/bias/masks, zero, initial wrapping, linear, ordered row aliases and metadata alias\n";
} catch(const std::exception &error) { std::cerr << error.what() << '\n'; return 1; } }
