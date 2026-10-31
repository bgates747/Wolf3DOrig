#ifdef WOLF3D_HOST_TEST
#include "qualification/vdplet_host_shim.h"
#else
#include "vdplet.h"
#endif
#include "wolf3d_scene_contract.h"
#include "wolf3d_tables.inc"

#ifndef WOLF3D_HOST_TEST
// Freestanding modules supply compiler-generated aggregate helpers.
extern "C" void *memcpy(void *destination, const void *source, unsigned count) {
    volatile uint8_t *d = (volatile uint8_t *)destination;
    const volatile uint8_t *s = (const volatile uint8_t *)source;
    while (count--) *d++ = *s++;
    return destination;
}
extern "C" void *memset(void *destination, int value, unsigned count) {
    volatile uint8_t *d = (volatile uint8_t *)destination;
    while (count--) *d++ = (uint8_t)value;
    return destination;
}

// The pinned classic-ESP32 compiler lowers the renderer's 64-bit divisions
// to these two helpers. Supplying the tiny bounded implementation locally
// avoids importing libgcc (and the much broader --math link) into the module.
union WideWords {
    uint64_t value;
    struct { uint32_t low, high; } words;
};

static bool wide_at_least(const WideWords &left, const WideWords &right) {
    return left.words.high > right.words.high ||
        (left.words.high == right.words.high && left.words.low >= right.words.low);
}

static void wide_subtract(WideWords &left, const WideWords &right) {
    uint32_t old_low = left.words.low;
    left.words.low -= right.words.low;
    left.words.high -= right.words.high + (old_low < right.words.low ? 1u : 0u);
}

static WideWords wide_negate(WideWords value) {
    value.words.low = ~value.words.low + 1u;
    value.words.high = ~value.words.high + (value.words.low == 0 ? 1u : 0u);
    return value;
}

static uint64_t divide_u64(uint64_t numerator, uint64_t denominator) {
    WideWords dividend = {numerator};
    WideWords divisor = {denominator};
    if (!divisor.words.low && !divisor.words.high) return UINT64_MAX;
    WideWords quotient = {0};
    WideWords remainder = {0};
    for (int bit = 63; bit >= 0; --bit) {
        uint32_t source_bit = bit >= 32
            ? ((dividend.words.high >> (bit - 32)) & 1u)
            : ((dividend.words.low >> bit) & 1u);
        remainder.words.high = (remainder.words.high << 1) |
                               (remainder.words.low >> 31);
        remainder.words.low = (remainder.words.low << 1) | source_bit;
        if (wide_at_least(remainder, divisor)) {
            wide_subtract(remainder, divisor);
            if (bit >= 32) quotient.words.high |= 1u << (bit - 32);
            else quotient.words.low |= 1u << bit;
        }
    }
    return quotient.value;
}

extern "C" uint64_t __udivdi3(uint64_t numerator, uint64_t denominator) {
    return divide_u64(numerator, denominator);
}

extern "C" int64_t __divdi3(int64_t numerator, int64_t denominator) {
    bool negative = (numerator < 0) != (denominator < 0);
    WideWords unsigned_numerator = {(uint64_t)numerator};
    WideWords unsigned_denominator = {(uint64_t)denominator};
    if (numerator < 0) unsigned_numerator = wide_negate(unsigned_numerator);
    if (denominator < 0) unsigned_denominator = wide_negate(unsigned_denominator);
    WideWords quotient = {divide_u64(unsigned_numerator.value,
                                     unsigned_denominator.value)};
    if (negative) quotient = wide_negate(quotient);
    return (int64_t)quotient.value;
}
#endif

namespace {

constexpr int32_t kTileGlobal = 1L << 16;
constexpr int32_t kMinDist = 0x5800L;
constexpr int32_t kActorSize = 0x4000L;
constexpr int32_t kFocalLength = 0x5700L;
constexpr int32_t kFineAngles = 3600;
constexpr int32_t kScale = 87;
constexpr int32_t kHeightNumerator = (kTileGlobal * kScale) >> 8;
constexpr int32_t kCenterX = (int32_t)W3V_VIEW_WIDTH / 2 - 1;
constexpr int32_t kCenterY = (int32_t)W3V_VIEW_HEIGHT / 2;
constexpr int32_t kInt32Max = 0x7fffffffL;

constexpr uint8_t kBlack = 0;
constexpr uint8_t kDarkCyan = 20;   // RGB222(0,1,1)
constexpr uint8_t kDarkGray = 21;   // RGB222(1,1,1)
constexpr uint8_t kLightGray = 42;  // RGB222(2,2,2)
constexpr uint8_t kCyanBevel = 40;  // RGB222(0,2,2)

struct SceneState {
    uint32_t magic;
    uint16_t workspace_id;
    uint16_t map_id;
    uint16_t texture_id;
    uint16_t generation;
    int32_t player_x;
    int32_t player_y;
    int16_t player_angle;
    uint8_t static_tile_x;
    uint8_t static_tile_y;
    uint8_t configured;
    uint8_t reserved[3];
};

static SceneState g_scene;

static uint16_t load_u16(const uint8_t *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t load_u32(const uint8_t *p) {
    return (uint32_t)load_u16(p) | ((uint32_t)load_u16(p + 2) << 16);
}

static void copy_bytes(void *destination, const void *source, uint32_t count) {
    uint8_t *d = (uint8_t *)destination;
    const uint8_t *s = (const uint8_t *)source;
    while (count--) *d++ = *s++;
}

static void clear_scene() {
    uint8_t *p = (uint8_t *)&g_scene;
    for (uint32_t i = 0; i < sizeof(g_scene); ++i) p[i] = 0;
}

static int32_t fixed_mul(int32_t a, int32_t b) {
    return (int32_t)(((int64_t)a * (int64_t)b) >> 16);
}

static int32_t fixed_div(int32_t a, int32_t b) {
    return (int32_t)(((int64_t)a << 16) / b);
}

static int32_t normalize_fine(int32_t angle) {
    angle %= kFineAngles;
    if (angle < 0) angle += kFineAngles;
    return angle;
}

static int32_t sin_fine(int32_t angle) {
    angle = normalize_fine(angle);
    if (angle <= 900) return kWolfSinQuarter[angle];
    if (angle <= 1800) return kWolfSinQuarter[1800 - angle];
    if (angle <= 2700) return -kWolfSinQuarter[angle - 1800];
    return -kWolfSinQuarter[3600 - angle];
}

static int32_t cos_fine(int32_t angle) {
    return sin_fine(angle + 900);
}

static void fill_bytes(uint8_t *destination, uint8_t value, uint32_t count) {
    while (count--) *destination++ = value;
}

static void fill_rect(uint8_t *frame, int left, int top, int right, int bottom,
                      uint8_t color) {
    if (left < 0) left = 0;
    if (top < 0) top = 0;
    if (right >= (int)W3V_SCREEN_WIDTH) right = (int)W3V_SCREEN_WIDTH - 1;
    if (bottom >= (int)W3V_SCREEN_HEIGHT) bottom = (int)W3V_SCREEN_HEIGHT - 1;
    if (left > right || top > bottom) return;
    for (int y = top; y <= bottom; ++y) {
        fill_bytes(frame + (uint32_t)y * W3V_SCREEN_WIDTH + (uint32_t)left,
                   color, (uint32_t)(right - left + 1));
    }
}

static void compose_background(uint8_t *frame) {
    fill_bytes(frame, kDarkGray, W3V_FRAME_BYTES);
    fill_rect(frame, 0, 0, W3V_SCREEN_WIDTH - 1, W3V_PLAY_HEIGHT - 1,
              kDarkCyan);
    fill_rect(frame, W3V_VIEW_X, W3V_VIEW_Y,
              W3V_VIEW_X + W3V_VIEW_WIDTH - 1,
              W3V_VIEW_Y + kCenterY - 1, kLightGray);
    fill_rect(frame, W3V_VIEW_X, W3V_VIEW_Y + kCenterY,
              W3V_VIEW_X + W3V_VIEW_WIDTH - 1,
              W3V_VIEW_Y + W3V_VIEW_HEIGHT - 1, kDarkGray);
    fill_rect(frame, W3V_VIEW_X - 1, W3V_VIEW_Y - 1,
              W3V_VIEW_X + W3V_VIEW_WIDTH,
              W3V_VIEW_Y - 1, kBlack);
    fill_rect(frame, W3V_VIEW_X - 1,
              W3V_VIEW_Y + W3V_VIEW_HEIGHT,
              W3V_VIEW_X + W3V_VIEW_WIDTH,
              W3V_VIEW_Y + W3V_VIEW_HEIGHT, kCyanBevel);
    fill_rect(frame, W3V_VIEW_X - 1, W3V_VIEW_Y - 1,
              W3V_VIEW_X - 1, W3V_VIEW_Y + W3V_VIEW_HEIGHT, kBlack);
    fill_rect(frame, W3V_VIEW_X + W3V_VIEW_WIDTH, W3V_VIEW_Y - 1,
              W3V_VIEW_X + W3V_VIEW_WIDTH,
              W3V_VIEW_Y + W3V_VIEW_HEIGHT, kCyanBevel);
}

static uint8_t tile_at(const uint8_t *map, int x, int y) {
    if (x < 0 || x >= (int)W3V_MAP_WIDTH ||
        y < 0 || y >= (int)W3V_MAP_HEIGHT) return 1;
    return map[(uint32_t)y * W3V_MAP_WIDTH + (uint32_t)x];
}

static int32_t projected_height(int32_t intercept_x, int32_t intercept_y,
                                int32_t view_x, int32_t view_y,
                                int32_t view_cos, int32_t view_sin) {
    int32_t gx = intercept_x - view_x;
    int32_t gy = intercept_y - view_y;
    int32_t nx = fixed_mul(gx, view_cos) - fixed_mul(gy, view_sin);
    if (nx < kMinDist) nx = kMinDist;
    return kHeightNumerator / (nx >> 8);
}

static void render_walls(uint8_t *frame, int32_t *wall_heights,
                         uint8_t *wall_tiles, uint8_t *wall_tex_u,
                         uint8_t *wall_sides, const uint8_t *map,
                         const uint8_t *wall_texture) {
    const int32_t fine_view = (int32_t)g_scene.player_angle * 10;
    const int32_t view_sin = sin_fine(fine_view);
    const int32_t view_cos = cos_fine(fine_view);
    const int32_t view_x = g_scene.player_x - fixed_mul(kFocalLength, view_cos);
    const int32_t view_y = g_scene.player_y + fixed_mul(kFocalLength, view_sin);

    for (int col = 0; col < (int)W3V_VIEW_WIDTH; ++col) {
        int32_t fine = normalize_fine(fine_view + kWolfPixelAngleFine[col]);
        int32_t ray_x = cos_fine(fine);
        int32_t ray_y = -sin_fine(fine);
        int map_x = view_x >> 16;
        int map_y = view_y >> 16;
        int step_x;
        int step_y;
        int32_t delta_x;
        int32_t delta_y;
        int32_t side_x;
        int32_t side_y;

        if (!ray_x) {
            step_x = 0;
            delta_x = side_x = kInt32Max;
        } else if (ray_x < 0) {
            step_x = -1;
            delta_x = fixed_div(kTileGlobal, -ray_x);
            side_x = fixed_mul(delta_x, view_x - (map_x << 16));
        } else {
            step_x = 1;
            delta_x = fixed_div(kTileGlobal, ray_x);
            side_x = fixed_mul(delta_x, ((map_x + 1) << 16) - view_x);
        }
        if (!ray_y) {
            step_y = 0;
            delta_y = side_y = kInt32Max;
        } else if (ray_y < 0) {
            step_y = -1;
            delta_y = fixed_div(kTileGlobal, -ray_y);
            side_y = fixed_mul(delta_y, view_y - (map_y << 16));
        } else {
            step_y = 1;
            delta_y = fixed_div(kTileGlobal, ray_y);
            side_y = fixed_mul(delta_y, ((map_y + 1) << 16) - view_y);
        }

        int side = 0;
        uint8_t tile = 1;
        int32_t intercept_x = view_x;
        int32_t intercept_y = view_y;
        bool hit = false;
        for (int step = 0; step < (int)(W3V_MAP_WIDTH * 2); ++step) {
            int32_t traveled;
            if (side_x < side_y) {
                traveled = side_x;
                side_x += delta_x;
                map_x += step_x;
                side = 0;
            } else {
                traveled = side_y;
                side_y += delta_y;
                map_y += step_y;
                side = 1;
            }
            intercept_x = view_x + fixed_mul(ray_x, traveled);
            intercept_y = view_y + fixed_mul(ray_y, traveled);
            tile = tile_at(map, map_x, map_y);
            if (tile) {
                hit = true;
                break;
            }
        }

        if (!hit) {
            wall_heights[col] = 0;
            wall_tiles[col] = wall_tex_u[col] = wall_sides[col] = 0;
            continue;
        }

        int full_height = projected_height(intercept_x, intercept_y,
                                           view_x, view_y, view_cos, view_sin);
        uint16_t fraction = side == 0 ? (uint16_t)intercept_y
                                      : (uint16_t)intercept_x;
        uint8_t tex_u = (uint8_t)(fraction >> 10);
        wall_heights[col] = full_height;
        wall_tiles[col] = tile;
        wall_tex_u[col] = tex_u;
        wall_sides[col] = (uint8_t)side;

        int top = kCenterY - full_height / 2;
        int clipped_top = top < 0 ? 0 : top;
        int bottom = top + full_height;
        int clipped_bottom = bottom > (int)W3V_VIEW_HEIGHT
            ? (int)W3V_VIEW_HEIGHT : bottom;
        int dest_height = clipped_bottom - clipped_top;
        if (dest_height <= 0) continue;
        int32_t texture_step = ((int32_t)W3V_TEXTURE_SIZE << 16) / full_height;
        int32_t texture_frac = texture_step * (clipped_top - top);
        for (int y = 0; y < dest_height; ++y) {
            int source_y = texture_frac >> 16;
            if (source_y >= (int)W3V_TEXTURE_SIZE)
                source_y = (int)W3V_TEXTURE_SIZE - 1;
            uint8_t pixel = wall_texture[(uint32_t)source_y * W3V_TEXTURE_SIZE + tex_u];
            frame[(uint32_t)(W3V_VIEW_Y + clipped_top + y) * W3V_SCREEN_WIDTH +
                  W3V_VIEW_X + (uint32_t)col] = pixel & 63u;
            texture_frac += texture_step;
        }
    }
}

static void render_static(uint8_t *frame, const int32_t *wall_heights,
                          const uint8_t *sprite_texture) {
    int32_t fine_view = (int32_t)g_scene.player_angle * 10;
    int32_t view_sin = sin_fine(fine_view);
    int32_t view_cos = cos_fine(fine_view);
    int32_t view_x = g_scene.player_x - fixed_mul(kFocalLength, view_cos);
    int32_t view_y = g_scene.player_y + fixed_mul(kFocalLength, view_sin);
    int32_t x = ((int32_t)g_scene.static_tile_x << 16) + 0x8000;
    int32_t y = ((int32_t)g_scene.static_tile_y << 16) + 0x8000;
    int32_t gx = x - view_x;
    int32_t gy = y - view_y;
    int32_t trans_x = fixed_mul(gx, view_cos) - fixed_mul(gy, view_sin) - kActorSize;
    int32_t trans_y = fixed_mul(gy, view_cos) + fixed_mul(gx, view_sin);
    if (trans_x < kMinDist) return;
    int view_x_column = kCenterX + (int)(((int64_t)trans_y * kScale) / trans_x);
    int size = kHeightNumerator / (trans_x >> 8);
    if (size <= 0 || view_x_column < -kCenterX ||
        view_x_column > (int)W3V_VIEW_WIDTH + kCenterX) return;

    int left = view_x_column - size / 2;
    int top = kCenterY - size / 2;
    int clipped_left = left < 0 ? 0 : left;
    int clipped_right = left + size > (int)W3V_VIEW_WIDTH
        ? (int)W3V_VIEW_WIDTH : left + size;
    int clipped_top = top < 0 ? 0 : top;
    int clipped_bottom = top + size > (int)W3V_VIEW_HEIGHT
        ? (int)W3V_VIEW_HEIGHT : top + size;
    if (clipped_left >= clipped_right || clipped_top >= clipped_bottom) return;

    int32_t x_step = ((int32_t)W3V_TEXTURE_SIZE << 16) / size;
    int32_t y_step = ((int32_t)W3V_TEXTURE_SIZE << 16) / size;
    int32_t y_frac = y_step * (clipped_top - top);
    for (int screen_y = clipped_top; screen_y < clipped_bottom; ++screen_y) {
        int source_y = y_frac >> 16;
        if (source_y >= (int)W3V_TEXTURE_SIZE)
            source_y = (int)W3V_TEXTURE_SIZE - 1;
        int32_t x_frac = x_step * (clipped_left - left);
        for (int screen_x = clipped_left; screen_x < clipped_right; ++screen_x) {
            if (wall_heights[screen_x] < size) {
                int source_x = x_frac >> 16;
                if (source_x >= (int)W3V_TEXTURE_SIZE)
                    source_x = (int)W3V_TEXTURE_SIZE - 1;
                uint8_t pixel = sprite_texture[(uint32_t)source_y * W3V_TEXTURE_SIZE +
                                               (uint32_t)source_x];
                if (pixel & 0xc0u) {
                    frame[(uint32_t)(W3V_VIEW_Y + screen_y) * W3V_SCREEN_WIDTH +
                          W3V_VIEW_X + (uint32_t)screen_x] = pixel & 63u;
                }
            }
            x_frac += x_step;
        }
        y_frac += y_step;
    }
}

static int32_t configure(const vdplet_host_v1 *host,
                         const vdplet_request_v1 *request) {
    if (request->argument_bytes != W3V_CONFIG_BYTES) return VDPL_E_ARGUMENT;
    vdplet_view_v1 view = {sizeof(view), 0, 0, 0, 0};
    int32_t rc = host->buffer_acquire(host->context, request->argument_buffer,
                                      VDPL_READ, 0, W3V_CONFIG_BYTES, &view);
    if (rc) return rc;
    uint8_t bytes[W3V_CONFIG_BYTES];
    copy_bytes(bytes, view.data, W3V_CONFIG_BYTES);
    int32_t release = host->buffer_release(host->context, view.lease);
    if (release) return release;

    uint32_t magic = load_u32(bytes);
    uint16_t workspace_id = load_u16(bytes + 4);
    uint16_t map_id = load_u16(bytes + 6);
    uint16_t texture_id = load_u16(bytes + 8);
    int16_t angle = (int16_t)load_u16(bytes + 10);
    int32_t player_x = (int32_t)load_u32(bytes + 12);
    int32_t player_y = (int32_t)load_u32(bytes + 16);
    uint8_t static_x = bytes[20];
    uint8_t static_y = bytes[21];
    if (magic != W3V_CONFIG_MAGIC || !workspace_id || !map_id || !texture_id ||
        workspace_id == map_id || workspace_id == texture_id || map_id == texture_id ||
        angle < 0 || angle >= 360 ||
        player_x < kTileGlobal || player_x >= 63 * kTileGlobal ||
        player_y < kTileGlobal || player_y >= 63 * kTileGlobal ||
        static_x == 0 || static_x >= 63 || static_y == 0 || static_y >= 63) {
        return VDPL_E_ARGUMENT;
    }

    SceneState next = {};
    next.magic = magic;
    next.workspace_id = workspace_id;
    next.map_id = map_id;
    next.texture_id = texture_id;
    next.generation = (uint16_t)(g_scene.generation + 1u);
    next.player_x = player_x;
    next.player_y = player_y;
    next.player_angle = angle;
    next.static_tile_x = static_x;
    next.static_tile_y = static_y;
    next.configured = 1;
    g_scene = next;
    return VDPL_OK;
}

static int32_t render(const vdplet_host_v1 *host) {
    if (!g_scene.configured || g_scene.magic != W3V_CONFIG_MAGIC)
        return VDPL_E_INIT;
    const vdplet_host_v1_3 *media = vdplet_pixels_host(host);
    if (!media) return VDPL_E_ABI;
    vdplet_surface_v1 surface = {sizeof(surface), 0, 0, 0, 0, 0, 0};
    int32_t rc = media->surface_info(host->context, &surface);
    if (rc) return rc;
    if (surface.width != W3V_SCREEN_WIDTH || surface.height != W3V_SCREEN_HEIGHT ||
        surface.native_format != VDPL_NATIVE_RGB222 ||
        (surface.flags & (VDPL_SURFACE_PHYSICAL | VDPL_SURFACE_DOUBLE_BUFFERED)) !=
        (VDPL_SURFACE_PHYSICAL | VDPL_SURFACE_DOUBLE_BUFFERED)) {
        return VDPL_E_FORMAT;
    }

    vdplet_view_v1 workspace = {sizeof(workspace), 0, 0, 0, 0};
    vdplet_view_v1 map = {sizeof(map), 0, 0, 0, 0};
    vdplet_view_v1 textures = {sizeof(textures), 0, 0, 0, 0};
    rc = host->buffer_acquire(host->context, g_scene.workspace_id, VDPL_WRITE,
                              0, W3V_WORKSPACE_BYTES, &workspace);
    if (rc) return rc;
    rc = host->buffer_acquire(host->context, g_scene.map_id, VDPL_READ,
                              0, W3V_MAP_BYTES, &map);
    if (rc) {
        host->buffer_release(host->context, workspace.lease);
        return rc;
    }
    rc = host->buffer_acquire(host->context, g_scene.texture_id, VDPL_READ,
                              0, W3V_TEXTURE_SET_BYTES, &textures);
    if (rc) {
        host->buffer_release(host->context, map.lease);
        host->buffer_release(host->context, workspace.lease);
        return rc;
    }

    uint8_t *frame = workspace.data;
    int32_t *wall_heights = (int32_t *)(workspace.data + W3V_WALL_HEIGHT_OFFSET);
    uint8_t *wall_tiles = workspace.data + W3V_WALL_TILE_OFFSET;
    uint8_t *wall_tex_u = workspace.data + W3V_WALL_TEXU_OFFSET;
    uint8_t *wall_sides = workspace.data + W3V_WALL_SIDE_OFFSET;
    compose_background(frame);
    render_walls(frame, wall_heights, wall_tiles, wall_tex_u, wall_sides,
                 map.data, textures.data);
    render_static(frame, wall_heights, textures.data + W3V_TEXTURE_BYTES);

    vdplet_pixels_v1 pixels = {
        sizeof(pixels), VDPL_PIXELS_RGB222, 0, 0,
        W3V_SCREEN_WIDTH, W3V_SCREEN_HEIGHT, W3V_SCREEN_WIDTH,
        W3V_FRAME_BYTES, frame
    };
    rc = media->pixels_write(host->context, &pixels);
    int32_t release = host->buffer_release(host->context, textures.lease);
    if (!rc) rc = release;
    release = host->buffer_release(host->context, map.lease);
    if (!rc) rc = release;
    release = host->buffer_release(host->context, workspace.lease);
    if (!rc) rc = release;
    return rc;
}

}  // namespace

extern "C" __attribute__((visibility("default")))
int32_t vdplet_entry(const vdplet_host_v1 *host,
                     const vdplet_request_v1 *request) {
    if (!host || !request || host->abi_major != VDPL_ABI_MAJOR ||
        !(host->capabilities & VDPL_CAP_BUFFERS)) return VDPL_E_ABI;
    if (request->operation == VDPL_INIT) {
        clear_scene();
        return VDPL_OK;
    }
    if (request->operation == VDPL_FINI) {
        clear_scene();
        return VDPL_OK;
    }
    if (request->operation != VDPL_RUN) return VDPL_E_UNSUPPORTED;
    if (request->entry_id == W3V_ENTRY_CONFIG) return configure(host, request);
    if (request->entry_id == W3V_ENTRY_RENDER) return render(host);
    return VDPL_E_UNSUPPORTED;
}
