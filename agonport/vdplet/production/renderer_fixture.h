#ifndef WOLF3D_PRODUCTION_RENDERER_FIXTURE_H
#define WOLF3D_PRODUCTION_RENDERER_FIXTURE_H

#include <stdint.h>

namespace wolf3d_renderer_fixture {

constexpr uint16_t kMapId = 2;
constexpr uint16_t kWallBase = 0x1000;
constexpr uint16_t kSpriteBase = 0x2000;
constexpr uint16_t kHudBase = 0x4000;
constexpr uint32_t kMapBytes = 4096;
constexpr uint32_t kTextureBytes = 4096;
constexpr uint32_t kMaximumAssetBytes = 12800;
constexpr int kScenarioCount = 3;

struct DoorSpec {
    uint16_t position;
    uint8_t x;
    uint8_t y;
    uint8_t vertical;
    uint8_t texture;
};

struct ActorSpec {
    uint16_t slot;
    int16_t shape;
    int32_t x;
    int32_t y;
    uint16_t facing;
    uint8_t rotations;
};

struct StaticSpec {
    int16_t shape;
    uint8_t x;
    uint8_t y;
};

struct SceneSpec {
    int32_t player_x;
    int32_t player_y;
    uint16_t player_angle;
    int16_t view_weapon_shape;
    uint8_t health;
    uint8_t ammo;
    uint8_t keys;
    uint8_t weapon;
    uint32_t score;
    uint8_t level;
    uint8_t face;
    uint8_t lives;
    DoorSpec doors[2];
    ActorSpec actors[3];
    StaticSpec statics[3];
};

inline int32_t tile_center(int tile) {
    return (tile << 16) + 0x8000;
}

inline void fill_map(uint8_t *map) {
    for (uint32_t i = 0; i < kMapBytes; ++i) map[i] = 0;
    for (int coordinate = 0; coordinate < 64; ++coordinate) {
        map[coordinate] = 1;
        map[63 * 64 + coordinate] = 1;
        map[coordinate * 64] = 1;
        map[coordinate * 64 + 63] = 1;
    }
    for (int y = 1; y <= 12; ++y) map[y * 64 + 12] = 2;
    for (int x = 1; x <= 12; ++x) map[12 * 64 + x] = 2;

    // A vertical center-plane door in an east-facing corridor.
    for (int x = 7; x <= 9; ++x) {
        map[3 * 64 + x] = 2;
        map[5 * 64 + x] = 2;
    }
    map[4 * 64 + 8] = 0x80;

    // A horizontal center-plane door in a south-facing corridor.
    for (int y = 7; y <= 9; ++y) {
        map[y * 64 + 3] = 2;
        map[y * 64 + 5] = 2;
    }
    map[8 * 64 + 4] = 0x81;

    // Nonuniform depths and a second ordinary texture exercise column
    // grouping without changing the accepted one-buffer-per-texture model.
    for (int y = 6; y <= 11; ++y) map[y * 64 + 10] = 4;
    for (int x = 7; x <= 11; ++x) map[10 * 64 + x] = 4;
}

inline SceneSpec scene(int index) {
    SceneSpec result{};
    result.doors[0] = {0x2800, 8, 4, 1, 3};
    result.doors[1] = {0x5000, 4, 8, 0, 3};
    result.actors[0] = {1, 10, tile_center(7), tile_center(6), 180, 8};
    result.actors[1] = {2, 20, tile_center(9), tile_center(7), 90, 2};
    result.actors[2] = {3, 28, tile_center(6), tile_center(9), 0, 0};
    result.statics[0] = {30, 7, 5};
    result.statics[1] = {31, 9, 9};
    result.statics[2] = {-1, 2, 2};
    if (index == 0) {
        result.player_x = tile_center(3);
        result.player_y = tile_center(4);
        result.player_angle = 0;
        result.view_weapon_shape = 32;
        result.health = 100;
        result.ammo = 8;
        result.keys = 0;
        result.weapon = 1;
        result.score = 12345;
        result.level = 1;
        result.face = 0;
        result.lives = 3;
    } else if (index == 1) {
        result.player_x = tile_center(4);
        result.player_y = tile_center(3);
        result.player_angle = 270;
        result.view_weapon_shape = 33;
        result.health = 47;
        result.ammo = 37;
        result.keys = 3;
        result.weapon = 3;
        result.score = 987654;
        result.level = 9;
        result.face = 2;
        result.lives = 7;
    } else {
        result.player_x = tile_center(8);
        result.player_y = tile_center(8);
        result.player_angle = 135;
        result.view_weapon_shape = -1;
        result.health = 0;
        result.ammo = 0;
        result.keys = 1;
        result.weapon = 0;
        result.score = 1000003;
        result.level = 10;
        result.face = 2;
        result.lives = 0;
        result.doors[0].position = 0xd000;
        result.doors[1].position = 0xe000;
    }
    return result;
}

inline uint8_t rgba2222(int red, int green, int blue, int alpha = 3) {
    return static_cast<uint8_t>(((alpha & 3) << 6) | ((blue & 3) << 4) |
                                ((green & 3) << 2) | (red & 3));
}

inline bool valid_buffer(uint16_t buffer_id) {
    if (buffer_id == kWallBase + 1 || buffer_id == kWallBase + 2 ||
        buffer_id == kWallBase + 3 || buffer_id == kWallBase + 4 ||
        buffer_id == kWallBase + 122) return true;
    if (buffer_id >= kSpriteBase && buffer_id < kSpriteBase + 64) return true;
    const uint16_t chunk = static_cast<uint16_t>(buffer_id - kHudBase);
    return buffer_id >= kHudBase &&
        (chunk == 98 || (chunk >= 103 && chunk <= 142));
}

inline uint32_t asset_bytes(uint16_t buffer_id) {
    if (buffer_id < kHudBase) return kTextureBytes;
    const uint16_t chunk = static_cast<uint16_t>(buffer_id - kHudBase);
    if (chunk == 98) return 320 * 40;
    if (chunk >= 103 && chunk <= 106) return 48 * 24;
    if (chunk >= 107 && chunk <= 120) return 8 * 16;
    if (chunk >= 121 && chunk <= 142) return 24 * 32;
    return 0;
}

inline void asset_dimensions(uint16_t buffer_id, int &width, int &height) {
    if (buffer_id < kHudBase) {
        width = height = 64;
        return;
    }
    const uint16_t chunk = static_cast<uint16_t>(buffer_id - kHudBase);
    if (chunk == 98) { width = 320; height = 40; }
    else if (chunk <= 106) { width = 48; height = 24; }
    else if (chunk <= 120) { width = 8; height = 16; }
    else { width = 24; height = 32; }
}

inline void fill_asset(uint16_t buffer_id, uint8_t *texture) {
    const bool wall = buffer_id >= kWallBase && buffer_id < kSpriteBase;
    const bool sprite = buffer_id >= kSpriteBase && buffer_id < kHudBase;
    const int seed = wall ? buffer_id - kWallBase
        : sprite ? buffer_id - kSpriteBase : buffer_id - kHudBase;
    int width;
    int height;
    asset_dimensions(buffer_id, width, height);
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            uint8_t pixel = 0;
            if (wall) {
                const bool mortar = y % 16 == 0 ||
                    x % 16 == ((y / 16) & 1 ? 8 : 0);
                pixel = mortar
                    ? rgba2222(1, 1, 1)
                    : rgba2222((seed + x / 8) & 3,
                               (seed / 2 + y / 8) & 3,
                               (seed + x / 16 + y / 16) & 3);
            } else if (sprite) {
                const int dx = x - 31;
                const int dy = y - 31;
                const bool body = dx * dx + dy * dy <= 25 * 25;
                const bool notch = (x < 11 || x > 52) && (y < 15 || y > 48);
                if (body && !notch) {
                    pixel = rgba2222((seed + x / 12) & 3,
                                     (seed / 3 + y / 12) & 3,
                                     (seed / 5 + x / 20) & 3);
                    if (y >= 40 && y <= 44 && x >= 20 && x <= 43)
                        pixel = rgba2222(3, 0, 0);
                }
            } else {
                // HUD assets use their real dimensions and opaque/transparent
                // structure, while remaining synthetic and deterministic.
                const bool border = x == 0 || y == 0 ||
                    x == width - 1 || y == height - 1;
                const bool transparent_corner =
                    buffer_id != kHudBase + 98 && x < 2 && y < 2;
                if (!transparent_corner) {
                    pixel = border
                        ? rgba2222(0, 0, 0)
                        : rgba2222((seed + x / 4) & 3,
                                   (seed / 2 + y / 4) & 3,
                                   (seed / 3 + x / 8 + y / 8) & 3);
                }
            }
            texture[y * width + x] = pixel;
        }
    }
}

}  // namespace wolf3d_renderer_fixture

#endif
