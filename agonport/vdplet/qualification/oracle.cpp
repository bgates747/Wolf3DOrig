#include <algorithm>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

class OracleBuffer {
public:
    explicit OracleBuffer(std::vector<std::uint8_t> value)
        : bytes(std::move(value)) {}
    std::size_t size() const { return bytes.size(); }
    std::uint8_t *getBuffer() { return bytes.data(); }
    const std::uint8_t *getBuffer() const { return bytes.data(); }
    std::vector<std::uint8_t> bytes;
};

std::unordered_map<std::uint16_t, std::vector<std::shared_ptr<OracleBuffer>>> buffers;

#define BUFFERS_H
#include "video/wolf3d/render/wolf3d_draw.h"
#include "wolf3d_scene_contract.h"

namespace {

std::vector<std::uint8_t> read_file(const char *path) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) throw std::runtime_error(std::string("cannot read ") + path);
    return std::vector<std::uint8_t>(std::istreambuf_iterator<char>(stream), {});
}

void write_file(const char *path, const std::uint8_t *data, std::size_t bytes) {
    std::ofstream stream(path, std::ios::binary);
    if (!stream) throw std::runtime_error(std::string("cannot write ") + path);
    stream.write(reinterpret_cast<const char *>(data), bytes);
}

std::uint16_t u16(const std::uint8_t *p) {
    return std::uint16_t(p[0]) | (std::uint16_t(p[1]) << 8);
}

std::uint32_t u32(const std::uint8_t *p) {
    return std::uint32_t(u16(p)) | (std::uint32_t(u16(p + 2)) << 16);
}

void fill_rect(std::vector<std::uint8_t>& frame, int left, int top,
               int right, int bottom, std::uint8_t color) {
    for (int y = top; y <= bottom; ++y)
        for (int x = left; x <= right; ++x)
            frame[std::size_t(y) * W3V_SCREEN_WIDTH + x] = color;
}

void compose_background(std::vector<std::uint8_t>& frame) {
    std::fill(frame.begin(), frame.end(), 21);
    fill_rect(frame, 0, 0, 319, 199, 20);
    fill_rect(frame, 32, 20, 287, 99, 42);
    fill_rect(frame, 32, 100, 287, 179, 21);
    fill_rect(frame, 31, 19, 288, 19, 0);
    fill_rect(frame, 31, 180, 288, 180, 40);
    fill_rect(frame, 31, 19, 31, 180, 0);
    fill_rect(frame, 288, 19, 288, 180, 40);
}

}  // namespace

int main(int argc, char **argv) {
    if (argc != 6) {
        std::cerr << "usage: oracle MAP TEXTURES CONFIG FRAME GEOMETRY\n";
        return 2;
    }
    try {
        auto map = read_file(argv[1]);
        auto textures = read_file(argv[2]);
        auto config = read_file(argv[3]);
        if (map.size() != W3V_MAP_BYTES || textures.size() != W3V_TEXTURE_SET_BYTES ||
            config.size() != W3V_CONFIG_BYTES || u32(config.data()) != W3V_CONFIG_MAGIC) {
            throw std::runtime_error("fixture contract mismatch");
        }

        const std::uint16_t map_id = u16(config.data() + 6);
        buffers[map_id].push_back(std::make_shared<OracleBuffer>(map));
        Wolf3dWorldState world{};
        world.init_level(map_id);
        world.set_player_pose((std::int32_t)u32(config.data() + 12),
                              (std::int32_t)u32(config.data() + 16),
                              (std::int16_t)u16(config.data() + 10));
        world.set_static(0, config[20], config[21], 0, 0);
        Wolf3dRenderer renderer(world);
        renderer.ThreeDRefresh();

        std::vector<std::uint8_t> frame(W3V_FRAME_BYTES);
        compose_background(frame);
        const int *heights = renderer.WallHeights();
        const std::uint8_t *tiles = renderer.WallTiles();
        const std::uint8_t *tex_u = renderer.WallTexU();
        const std::uint8_t *wall_texture = textures.data();
        for (int column = 0; column < (int)W3V_VIEW_WIDTH; ++column) {
            int full_height = heights[column];
            if (full_height <= 0) continue;
            int top = renderer.CenterY() - full_height / 2;
            int clipped_top = std::max(top, 0);
            int clipped_bottom = std::min(top + full_height, renderer.ViewHeight());
            int destination_height = clipped_bottom - clipped_top;
            if (destination_height <= 0) continue;
            std::vector<std::uint8_t> scratch(destination_height);
            Wolf3dRenderer::SampleWallColumn(
                wall_texture + tex_u[column], W3V_TEXTURE_SIZE, full_height,
                clipped_top - top, scratch.data(), destination_height);
            for (int y = 0; y < destination_height; ++y) {
                frame[std::size_t(W3V_VIEW_Y + clipped_top + y) * W3V_SCREEN_WIDTH +
                      W3V_VIEW_X + column] = scratch[y] & 63u;
            }
        }

        const std::uint8_t *sprite_texture = textures.data() + W3V_TEXTURE_BYTES;
        for (int index = 0; index < renderer.VisSpriteCount(); ++index) {
            const auto& sprite = renderer.VisSprites()[index];
            int size = (int)sprite.viewheight;
            int left = sprite.viewx - size / 2;
            int top = renderer.ViewHeight() / 2 - size / 2;
            int clipped_left = std::max(left, 0);
            int clipped_right = std::min(left + size, renderer.ViewWidth());
            int clipped_top = std::max(top, 0);
            int clipped_bottom = std::min(top + size, renderer.ViewHeight());
            int width = clipped_right - clipped_left;
            int height = clipped_bottom - clipped_top;
            if (width <= 0 || height <= 0) continue;
            std::vector<std::uint8_t> scratch(std::size_t(width) * height);
            Wolf3dRenderer::SampleSprite(
                sprite_texture, W3V_TEXTURE_SIZE, W3V_TEXTURE_SIZE,
                size, size, clipped_left - left, clipped_top - top,
                scratch.data(), width, height);
            Wolf3dRenderer::MaskSpriteColumnsBehindWalls(
                scratch.data(), width, height, clipped_left, heights,
                renderer.ViewWidth(), size);
            for (int y = 0; y < height; ++y) {
                for (int x = 0; x < width; ++x) {
                    std::uint8_t pixel = scratch[std::size_t(y) * width + x];
                    if (pixel & 0xc0u) {
                        frame[std::size_t(W3V_VIEW_Y + clipped_top + y) *
                              W3V_SCREEN_WIDTH + W3V_VIEW_X + clipped_left + x] =
                            pixel & 63u;
                    }
                }
            }
        }

        write_file(argv[4], frame.data(), frame.size());
        std::vector<std::uint8_t> geometry(W3V_SPRITE_ARENA_OFFSET - W3V_FRAME_BYTES);
        std::size_t at = 0;
        std::memcpy(geometry.data() + at, renderer.WallHeights(), W3V_WALL_HEIGHT_BYTES);
        at += W3V_WALL_HEIGHT_BYTES;
        std::memcpy(geometry.data() + at, tiles, W3V_VIEW_WIDTH);
        at += W3V_VIEW_WIDTH;
        std::memcpy(geometry.data() + at, tex_u, W3V_VIEW_WIDTH);
        at += W3V_VIEW_WIDTH;
        std::memcpy(geometry.data() + at, renderer.WallSides(), W3V_VIEW_WIDTH);
        write_file(argv[5], geometry.data(), geometry.size());
        std::cout << "oracle: frame and DDA geometry generated\n";
    } catch (const std::exception& error) {
        std::cerr << "oracle: " << error.what() << "\n";
        return 1;
    }
    return 0;
}
