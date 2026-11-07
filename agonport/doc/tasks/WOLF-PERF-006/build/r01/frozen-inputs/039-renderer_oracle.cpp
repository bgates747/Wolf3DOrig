#include <algorithm>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

#include "renderer_fixture.h"

class OracleBuffer {
public:
    explicit OracleBuffer(std::vector<std::uint8_t> value)
        : bytes(std::move(value)) {}
    std::size_t size() const { return bytes.size(); }
    std::uint8_t *getBuffer() { return bytes.data(); }
    const std::uint8_t *getBuffer() const { return bytes.data(); }
    std::vector<std::uint8_t> bytes;
};

std::unordered_map<std::uint16_t,
                   std::vector<std::shared_ptr<OracleBuffer>>> buffers;

#define BUFFERS_H
#include "video/wolf3d/render/wolf3d_draw.h"

namespace fixture = wolf3d_renderer_fixture;
namespace {

constexpr int kScreenWidth = 320;
constexpr int kScreenHeight = 240;
constexpr int kFrameBytes = kScreenWidth * kScreenHeight;
constexpr int kViewX = 32;
constexpr int kViewY = 20;
constexpr int kGeometryBytes = 1792;

void require(bool condition, const char *message) {
    if (!condition) throw std::runtime_error(message);
}

void fill_rect(std::vector<uint8_t> &frame, int left, int top,
               int right, int bottom, uint8_t color) {
    for (int y = top; y <= bottom; ++y)
        for (int x = left; x <= right; ++x)
            frame[static_cast<size_t>(y) * kScreenWidth + x] = color;
}

void compose_background(std::vector<uint8_t> &frame) {
    std::fill(frame.begin(), frame.end(), 21);
    fill_rect(frame, 0, 0, 319, 199, 20);
    fill_rect(frame, 32, 20, 287, 99, 42);
    fill_rect(frame, 32, 100, 287, 179, 21);
    fill_rect(frame, 31, 19, 288, 19, 0);
    fill_rect(frame, 31, 180, 288, 180, 40);
    fill_rect(frame, 31, 19, 31, 180, 0);
    fill_rect(frame, 288, 19, 288, 180, 40);
}

std::shared_ptr<OracleBuffer> texture(uint16_t id) {
    std::vector<uint8_t> bytes(fixture::asset_bytes(id));
    fixture::fill_asset(id, bytes.data());
    return std::make_shared<OracleBuffer>(std::move(bytes));
}

void install_assets(const std::vector<uint8_t> &map) {
    buffers.clear();
    buffers[fixture::kMapId].push_back(
        std::make_shared<OracleBuffer>(map));
    for (uint16_t id : {uint16_t(1), uint16_t(2), uint16_t(3),
                        uint16_t(4), uint16_t(122)}) {
        buffers[fixture::kWallBase + id].push_back(
            texture(static_cast<uint16_t>(fixture::kWallBase + id)));
    }
    for (uint16_t shape = 0; shape < 64; ++shape) {
        buffers[fixture::kSpriteBase + shape].push_back(
            texture(static_cast<uint16_t>(fixture::kSpriteBase + shape)));
    }
    buffers[fixture::kHudBase + 98].push_back(
        texture(fixture::kHudBase + 98));
    for (uint16_t chunk = 103; chunk <= 143; ++chunk) {
        buffers[fixture::kHudBase + chunk].push_back(
            texture(static_cast<uint16_t>(fixture::kHudBase + chunk)));
    }
}

Wolf3dWorldState make_world(int scenario) {
    Wolf3dWorldState world{};
    world.init_level(fixture::kMapId);
    const fixture::SceneSpec spec = fixture::scene(scenario);
    world.set_player_pose(spec.player_x, spec.player_y, spec.player_angle);
    for (uint8_t i = 0; i < 2; ++i) {
        world.set_door(i, spec.doors[i].x, spec.doors[i].y,
                       spec.doors[i].vertical != 0, 0, 0,
                       spec.doors[i].position, spec.doors[i].texture);
    }
    for (const fixture::ActorSpec &actor : spec.actors) {
        world.set_actor(actor.slot, actor.shape, actor.x, actor.y,
                        actor.facing, actor.rotations);
    }
    for (uint16_t i = 0; i < 3; ++i) {
        world.set_static(i, spec.statics[i].x, spec.statics[i].y,
                         spec.statics[i].shape, 0);
    }
    return world;
}

void render_walls(std::vector<uint8_t> &frame, const Wolf3dWorldState &world,
                  const Wolf3dRenderer &renderer) {
    const int *heights = renderer.WallHeights();
    const uint8_t *tiles = renderer.WallTiles();
    const uint8_t *tex_u = renderer.WallTexU();
    for (int column = 0; column < renderer.ViewWidth(); ++column) {
        const int full_height = heights[column];
        if (full_height <= 0) continue;
        const uint8_t tile = tiles[column];
        const uint8_t texture_id = tile >= 0x80 && tile <= 0xbf
            ? world.doors[tile & 0x7f].textureId : tile;
        auto found = buffers.find(fixture::kWallBase + texture_id);
        if (found == buffers.end()) continue;
        const uint8_t *source = found->second[0]->getBuffer();
        const int top = renderer.CenterY() - full_height / 2;
        const int clipped_top = std::max(top, 0);
        const int clipped_bottom = std::min(
            top + full_height, renderer.ViewHeight());
        const int destination_height = clipped_bottom - clipped_top;
        if (destination_height <= 0) continue;
        std::vector<uint8_t> scratch(destination_height);
        Wolf3dRenderer::SampleWallColumn(
            source + tex_u[column], 64, full_height, clipped_top - top,
            scratch.data(), destination_height);
        for (int y = 0; y < destination_height; ++y) {
            frame[static_cast<size_t>(kViewY + clipped_top + y) *
                  kScreenWidth + kViewX + column] = scratch[y] & 63u;
        }
    }
}

void render_sprites(std::vector<uint8_t> &frame,
                    const Wolf3dRenderer &renderer) {
    const int *heights = renderer.WallHeights();
    for (int index = 0; index < renderer.VisSpriteCount(); ++index) {
        const auto &sprite = renderer.VisSprites()[index];
        auto found = buffers.find(
            fixture::kSpriteBase + static_cast<uint16_t>(sprite.shapenum));
        if (found == buffers.end()) continue;
        const int size = static_cast<int>(sprite.viewheight);
        const int left = sprite.viewx - size / 2;
        const int top = renderer.ViewHeight() / 2 - size / 2;
        const int clipped_left = std::max(left, 0);
        const int clipped_right = std::min(left + size, renderer.ViewWidth());
        const int clipped_top = std::max(top, 0);
        const int clipped_bottom = std::min(top + size, renderer.ViewHeight());
        const int width = clipped_right - clipped_left;
        const int height = clipped_bottom - clipped_top;
        if (width <= 0 || height <= 0) continue;
        std::vector<uint8_t> scratch(static_cast<size_t>(width) * height);
        Wolf3dRenderer::SampleSprite(
            found->second[0]->getBuffer(), 64, 64, size, size,
            clipped_left - left, clipped_top - top,
            scratch.data(), width, height);
        Wolf3dRenderer::MaskSpriteColumnsBehindWalls(
            scratch.data(), width, height, clipped_left, heights,
            renderer.ViewWidth(), size);
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                const uint8_t pixel = scratch[static_cast<size_t>(y) * width + x];
                if ((pixel & 0xc0u) != 0) {
                    frame[static_cast<size_t>(kViewY + clipped_top + y) *
                          kScreenWidth + kViewX + clipped_left + x] = pixel & 63u;
                }
            }
        }
    }
}

void render_view_weapon(std::vector<uint8_t> &frame,
                        int16_t shape) {
    if (shape < 0) return;
    auto found = buffers.find(
        fixture::kSpriteBase + static_cast<uint16_t>(shape));
    if (found == buffers.end()) return;
    constexpr int size = 161;
    constexpr int left = 128 - size / 2;
    constexpr int top = (160 - size) / 2;
    const int clipped_left = std::max(left, 0);
    const int clipped_right = std::min(left + size, 256);
    const int clipped_top = std::max(top, 0);
    const int clipped_bottom = std::min(top + size, 160);
    const int width = clipped_right - clipped_left;
    const int height = clipped_bottom - clipped_top;
    std::vector<uint8_t> scratch(static_cast<size_t>(width) * height);
    Wolf3dRenderer::SampleSprite(
        found->second[0]->getBuffer(), 64, 64, size, size,
        clipped_left - left, clipped_top - top,
        scratch.data(), width, height);
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            const uint8_t pixel = scratch[static_cast<size_t>(y) * width + x];
            if ((pixel & 0xc0u) != 0) {
                frame[static_cast<size_t>(kViewY + clipped_top + y) *
                      kScreenWidth + kViewX + clipped_left + x] = pixel & 63u;
            }
        }
    }
}

void draw_hud_pic(std::vector<uint8_t> &frame, uint16_t chunk,
                  int left, int top) {
    const uint16_t id = static_cast<uint16_t>(fixture::kHudBase + chunk);
    auto found = buffers.find(id);
    require(found != buffers.end(), "oracle HUD asset missing");
    int width;
    int height;
    fixture::asset_dimensions(id, width, height);
    const uint8_t *source = found->second[0]->getBuffer();
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            const uint8_t pixel = source[y * width + x];
            if ((pixel & 0xc0u) != 0) {
                frame[static_cast<size_t>(top + y) * kScreenWidth + left + x] =
                    pixel & 63u;
            }
        }
    }
}

void draw_hud_number(std::vector<uint8_t> &frame, int x, int y, int width,
                     uint32_t value) {
    uint32_t modulus = 1;
    for (int i = 0; i < width; ++i) modulus *= 10;
    value %= modulus;
    uint32_t divisor = modulus / 10;
    bool started = false;
    for (int i = 0; i < width; ++i) {
        const uint8_t digit = static_cast<uint8_t>(value / divisor);
        value %= divisor;
        uint16_t chunk = 111 + digit;
        if (!started && digit == 0 && i != width - 1) chunk = 110;
        else started = true;
        draw_hud_pic(frame, chunk, x + i * 8, 200 + y);
        if (divisor > 1) divisor /= 10;
    }
}

void render_hud(std::vector<uint8_t> &frame,
                const fixture::SceneSpec &spec) {
    std::fill(frame.begin() + 200 * kScreenWidth, frame.end(), 21);
    draw_hud_pic(frame, 98, 0, 200);
    draw_hud_number(frame, 16, 16, 2, spec.level);
    draw_hud_number(frame, 48, 16, 6, spec.score);
    draw_hud_number(frame, 112, 16, 1, spec.lives);
    const uint16_t face = spec.health == 0
        ? 142
        : spec.face == 3
            ? 143
            : static_cast<uint16_t>(121 + ((100 - spec.health) / 16) * 3 + spec.face);
    draw_hud_pic(frame, face, 136, 204);
    draw_hud_number(frame, 168, 16, 3, spec.health);
    draw_hud_number(frame, 216, 16, 2, spec.ammo);
    draw_hud_pic(frame, (spec.keys & 1) != 0 ? 108 : 107, 240, 204);
    draw_hud_pic(frame, (spec.keys & 2) != 0 ? 109 : 107, 240, 220);
    draw_hud_pic(frame, static_cast<uint16_t>(103 + spec.weapon), 256, 208);
}

uint8_t shifted_component(uint8_t component, uint8_t target,
                          uint8_t level, uint8_t steps) {
    const int value = component +
        (static_cast<int>(target) - component) * level / steps;
    return static_cast<uint8_t>(value < 0 ? 0 : (value > 63 ? 63 : value));
}

uint8_t quantize_component(uint8_t component) {
    const uint8_t quantized = static_cast<uint8_t>((component + 10u) / 21u);
    return quantized > 3 ? 3 : quantized;
}

void apply_palette_shift(std::vector<uint8_t> &frame, uint8_t shift) {
    if (shift == 0) return;
    for (uint8_t &color : frame) {
        const uint8_t red = static_cast<uint8_t>((color & 3u) * 21u);
        const uint8_t green = static_cast<uint8_t>(((color >> 2) & 3u) * 21u);
        const uint8_t blue = static_cast<uint8_t>(((color >> 4) & 3u) * 21u);
        uint8_t shifted_red;
        uint8_t shifted_green;
        uint8_t shifted_blue;
        if ((shift & W3P_HUD_PALETTE_WHITE_FLAG) != 0) {
            const uint8_t level = static_cast<uint8_t>(
                shift & ~W3P_HUD_PALETTE_WHITE_FLAG);
            shifted_red = shifted_component(red, 64, level, 20);
            shifted_green = shifted_component(green, 62, level, 20);
            shifted_blue = shifted_component(blue, 0, level, 20);
        } else {
            shifted_red = shifted_component(red, 64, shift, 8);
            shifted_green = shifted_component(green, 0, shift, 8);
            shifted_blue = shifted_component(blue, 0, shift, 8);
        }
        color = static_cast<uint8_t>(quantize_component(shifted_red) |
            (quantize_component(shifted_green) << 2) |
            (quantize_component(shifted_blue) << 4));
    }
}

void write_all(std::ofstream &stream, const void *data, size_t bytes) {
    stream.write(static_cast<const char *>(data), bytes);
    require(static_cast<bool>(stream), "cannot write oracle output");
}

}  // namespace

int main(int argc, char **argv) {
    if (argc != 3) {
        std::cerr << "usage: renderer_oracle FRAME GEOMETRY\n";
        return 2;
    }
    try {
        std::vector<uint8_t> map(fixture::kMapBytes);
        fixture::fill_map(map.data());
        install_assets(map);
        std::ofstream frame_output(argv[1], std::ios::binary);
        std::ofstream geometry_output(argv[2], std::ios::binary);
        require(frame_output && geometry_output, "cannot open oracle output");
        for (int scenario = 0; scenario < fixture::kScenarioCount; ++scenario) {
            const fixture::SceneSpec spec = fixture::scene(scenario);
            Wolf3dWorldState world = make_world(scenario);
            Wolf3dRenderer renderer(world);
            renderer.ThreeDRefresh();
            std::vector<uint8_t> frame(kFrameBytes);
            compose_background(frame);
            render_walls(frame, world, renderer);
            render_sprites(frame, renderer);
            render_view_weapon(frame, spec.view_weapon_shape);
            render_hud(frame, spec);
            apply_palette_shift(frame, spec.palette_shift);
            write_all(frame_output, frame.data(), frame.size());
            std::vector<uint8_t> geometry(kGeometryBytes);
            size_t at = 0;
            std::memcpy(geometry.data() + at, renderer.WallHeights(), 1024);
            at += 1024;
            std::memcpy(geometry.data() + at, renderer.WallTiles(), 256);
            at += 256;
            std::memcpy(geometry.data() + at, renderer.WallTexU(), 256);
            at += 256;
            std::memcpy(geometry.data() + at, renderer.WallSides(), 256);
            write_all(geometry_output, geometry.data(), geometry.size());
        }
        std::cout << "standalone oracle: production scenes rendered\n";
    } catch (const std::exception &error) {
        std::cerr << "standalone oracle: " << error.what() << "\n";
        return 1;
    }
    return 0;
}
