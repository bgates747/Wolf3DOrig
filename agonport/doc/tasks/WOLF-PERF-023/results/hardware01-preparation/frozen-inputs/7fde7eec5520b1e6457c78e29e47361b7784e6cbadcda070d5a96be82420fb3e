#include "wolf3d_renderer.h"
#include "original_raywalk.h"

#include "../wolf3d_tables.inc"

namespace wolf3d_production {
namespace {

constexpr int32_t kTileGlobal = 1L << 16;
constexpr int32_t kMinDist = 0x5800L;
constexpr int32_t kActorSize = 0x4000L;
constexpr int32_t kFocalLength = 0x5700L;
constexpr int32_t kFineAngles = 3600;
constexpr int32_t kScale = 87;
constexpr int32_t kHeightNumerator = (kTileGlobal * kScale) >> 8;
constexpr int32_t kCenterX = 127;
constexpr int32_t kCenterY = 80;
constexpr int32_t kInt32Max = 0x7fffffffL;
constexpr int kViewWidth = 256;
constexpr int kViewHeight = 160;
constexpr int kViewX = 32;
constexpr int kViewY = 20;
constexpr int kPlayHeight = 200;
constexpr int kTextureSize = 64;
constexpr uint8_t kDoorFlag = 0x80;
constexpr uint8_t kDoorMax = 0xbf;
constexpr uint8_t kDoorMask = 0x7f;
constexpr uint8_t kDoorJambTexture = 122;
constexpr uint16_t kHudStatusBar = 98;
constexpr uint16_t kHudKnife = 103;
constexpr uint16_t kHudNoKey = 107;
constexpr uint16_t kHudGoldKey = 108;
constexpr uint16_t kHudSilverKey = 109;
constexpr uint16_t kHudBlank = 110;
constexpr uint16_t kHudDigit0 = 111;
constexpr uint16_t kHudFace1A = 121;
constexpr uint16_t kHudFaceDead = 142;
constexpr uint16_t kHudFaceGotGatling = 143;

constexpr uint8_t kBlack = 0;
constexpr uint8_t kDarkCyan = 20;
constexpr uint8_t kDarkGray = 21;
constexpr uint8_t kLightGray = 42;
constexpr uint8_t kCyanBevel = 40;

struct ViewState {
    int32_t x;
    int32_t y;
    int32_t sine;
    int32_t cosine;
};

struct VisSprite {
    int32_t view_x;
    uint32_t view_height;
    int16_t shape;
    uint16_t reserved;
    int32_t depth;
};

struct HudDraw {
    uint16_t chunk;
    int16_t x;
    int16_t y;
};

static_assert(sizeof(VisSprite) == 16, "sprite arena record must remain 16 bytes");
static_assert((W3P_MAX_ACTORS + W3P_MAX_STATICS) * sizeof(VisSprite) ==
              W3P_SPRITE_ARENA_BYTES,
              "sprite arena no longer covers every render slot");

void clear_bytes(void *destination, uint8_t value, uint32_t count) {
    uint8_t *p = static_cast<uint8_t *>(destination);
    while (count-- != 0) *p++ = value;
}

uint8_t *target_pixel(const RenderTarget &target, uint32_t x, uint32_t y) {
    if (target.linear != nullptr)
        return target.linear + y * W3P_SCREEN_WIDTH + x;
    return reinterpret_cast<uint8_t *>(target.rows[y]) +
        ((target.x_bias + x) ^ target.pixel_xor);
}

void put_pixel(const RenderTarget &target, uint32_t x, uint32_t y,
               uint8_t color) {
    uint8_t *const pixel = target_pixel(target, x, y);
    if (target.linear != nullptr) {
        *pixel = color;
    } else {
        *pixel = static_cast<uint8_t>((*pixel & target.preserve_mask) |
                                     (color & target.color_mask));
    }
}

void fill_span(const RenderTarget &target, uint32_t x, uint32_t y,
               uint32_t count, uint8_t color) {
    if (target.linear != nullptr) {
        clear_bytes(target_pixel(target, x, y), color, count);
        return;
    }
    if (count == 0) return;
    uint8_t *const row = reinterpret_cast<uint8_t *>(target.rows[y]);
    uint32_t mapped_x = target.x_bias + x;
    const uint32_t pixel_xor = target.pixel_xor;
    const uint8_t preserve_mask = target.preserve_mask;
    const uint8_t color_bits = static_cast<uint8_t>(color & target.color_mask);
    while (count-- != 0) {
        uint8_t *const pixel = row + (mapped_x++ ^ pixel_xor);
        *pixel = static_cast<uint8_t>((*pixel & preserve_mask) | color_bits);
    }
}

void clear_stats(RenderStats *stats) {
    if (stats == nullptr) return;
    stats->visible_sprites = 0;
    stats->wall_acquires = 0;
    stats->sprite_acquires = 0;
    stats->weapon_acquires = 0;
    stats->hud_acquires = 0;
}

int32_t fixed_mul(int32_t a, int32_t b) {
    return static_cast<int32_t>(
        (static_cast<int64_t>(a) * static_cast<int64_t>(b)) >> 16);
}

int32_t normalize_fine(int32_t angle) {
    angle %= kFineAngles;
    if (angle < 0) angle += kFineAngles;
    return angle;
}

void fill_rect(const RenderTarget &frame, int left, int top, int right, int bottom,
               uint8_t color) {
    if (left < 0) left = 0;
    if (top < 0) top = 0;
    if (right >= static_cast<int>(W3P_SCREEN_WIDTH))
        right = static_cast<int>(W3P_SCREEN_WIDTH) - 1;
    if (bottom >= static_cast<int>(W3P_SCREEN_HEIGHT))
        bottom = static_cast<int>(W3P_SCREEN_HEIGHT) - 1;
    if (left > right || top > bottom) return;
    for (int y = top; y <= bottom; ++y) {
        fill_span(frame, static_cast<uint32_t>(left), static_cast<uint32_t>(y),
                  static_cast<uint32_t>(right - left + 1), color);
    }
}

void compose_background(const RenderTarget &frame) {
    for (uint32_t y = kPlayHeight; y < W3P_SCREEN_HEIGHT; ++y)
        fill_span(frame, 0, y, W3P_SCREEN_WIDTH, kDarkGray);
    // A later viewport fill fully replaces cyan only under overwrite masks.
    if (frame.linear != nullptr ||
        (frame.color_mask & frame.preserve_mask) == 0) {
        fill_rect(frame, 0, 0, W3P_SCREEN_WIDTH - 1, kViewY - 1, kDarkCyan);
        fill_rect(frame, 0, kViewY + kViewHeight,
                  W3P_SCREEN_WIDTH - 1, kPlayHeight - 1, kDarkCyan);
        fill_rect(frame, 0, kViewY, kViewX - 1,
                  kViewY + kViewHeight - 1, kDarkCyan);
        fill_rect(frame, kViewX + kViewWidth, kViewY,
                  W3P_SCREEN_WIDTH - 1, kViewY + kViewHeight - 1, kDarkCyan);
    } else {
        // Overlapping masks can retain bits contributed by the first fill.
        fill_rect(frame, 0, 0, W3P_SCREEN_WIDTH - 1,
                  kPlayHeight - 1, kDarkCyan);
    }
    fill_rect(frame, kViewX, kViewY, kViewX + kViewWidth - 1,
              kViewY + kCenterY - 1, kLightGray);
    fill_rect(frame, kViewX, kViewY + kCenterY, kViewX + kViewWidth - 1,
              kViewY + kViewHeight - 1, kDarkGray);
    fill_rect(frame, kViewX - 1, kViewY - 1, kViewX + kViewWidth,
              kViewY - 1, kBlack);
    fill_rect(frame, kViewX - 1, kViewY + kViewHeight, kViewX + kViewWidth,
              kViewY + kViewHeight, kCyanBevel);
    fill_rect(frame, kViewX - 1, kViewY - 1, kViewX - 1,
              kViewY + kViewHeight, kBlack);
    fill_rect(frame, kViewX + kViewWidth, kViewY - 1,
              kViewX + kViewWidth, kViewY + kViewHeight, kCyanBevel);
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

uint8_t palette_shift_color(uint8_t color, uint8_t shift) {
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
    return static_cast<uint8_t>(quantize_component(shifted_red) |
        (quantize_component(shifted_green) << 2) |
        (quantize_component(shifted_blue) << 4));
}

void apply_palette_shift(const RenderTarget &frame, uint8_t shift) {
    if (shift == 0) return;
    uint8_t shifted[64];
    for (uint8_t color = 0; color < 64; ++color)
        shifted[color] = palette_shift_color(color, shift);
    for (uint32_t y = 0; y < W3P_SCREEN_HEIGHT; ++y) {
        for (uint32_t x = 0; x < W3P_SCREEN_WIDTH; ++x) {
            const uint8_t color = static_cast<uint8_t>(
                *target_pixel(frame, x, y) & frame.color_mask);
            put_pixel(frame, x, y, shifted[color]);
        }
    }
}

ViewState setup_view(const WorldMirror &world) {
    const uint32_t degree = static_cast<uint32_t>(world.player.angle) % 360u;
    ViewState view;
    view.sine = kWolfSinDegree[degree];
    view.cosine = kWolfSinDegree[(degree + 90u) % 360u];
    view.x = world.player.x - fixed_mul(kFocalLength, view.cosine);
    view.y = world.player.y + fixed_mul(kFocalLength, view.sine);
    return view;
}

uint8_t base_tile_at(const uint8_t *map, int x, int y) {
    if (x < 0 || x >= static_cast<int>(W3P_MAP_SIZE) ||
        y < 0 || y >= static_cast<int>(W3P_MAP_SIZE)) return 1;
    return map[static_cast<uint32_t>(y) * W3P_MAP_SIZE +
               static_cast<uint32_t>(x)];
}

bool completion_tile(const PushwallCompletion &wall, int x, int y,
                     uint8_t &value) {
    if (x == wall.current_x && y == wall.current_y) {
        value = wall.texture;
        return true;
    }
    if (wall.origin_y == wall.current_y && y == wall.origin_y) {
        if ((wall.current_x > wall.origin_x &&
             x >= wall.origin_x && x < wall.current_x) ||
            (wall.current_x < wall.origin_x &&
             x <= wall.origin_x && x > wall.current_x)) {
            value = 0;
            return true;
        }
    } else if (wall.origin_x == wall.current_x && x == wall.origin_x) {
        if ((wall.current_y > wall.origin_y &&
             y >= wall.origin_y && y < wall.current_y) ||
            (wall.current_y < wall.origin_y &&
             y <= wall.origin_y && y > wall.current_y)) {
            value = 0;
            return true;
        }
    }
    return false;
}

bool active_pushwall_cell(const PushwallState &wall, int x, int y) {
    if (wall.origin_y == wall.current_y && y == wall.origin_y) {
        return wall.current_x >= wall.origin_x
            ? x >= wall.origin_x && x <= wall.current_x
            : x <= wall.origin_x && x >= wall.current_x;
    }
    if (wall.origin_x == wall.current_x && x == wall.origin_x) {
        return wall.current_y >= wall.origin_y
            ? y >= wall.origin_y && y <= wall.current_y
            : y <= wall.origin_y && y >= wall.current_y;
    }
    return false;
}

uint8_t tile_at(const WorldMirror &world, const uint8_t *map, int x, int y) {
    uint8_t value = base_tile_at(map, x, y);
    for (uint8_t i = 0; i < world.pushwall.completed_count; ++i)
        completion_tile(world.pushwall.completed[i], x, y, value);
    if (world.pushwall.status != 1) return value;
    if (active_pushwall_cell(world.pushwall, x, y)) return 0;
    return value;
}

int32_t projected_height(int32_t intercept_x, int32_t intercept_y,
                         const ViewState &view) {
    const int32_t gx = intercept_x - view.x;
    const int32_t gy = intercept_y - view.y;
    int32_t nx = fixed_mul(gx, view.cosine) - fixed_mul(gy, view.sine);
    if (nx < kMinDist) nx = kMinDist;
    return kHeightNumerator / (nx >> 8);
}

RenderDetail cast_walls(const WorldMirror &world, const uint8_t *map,
                        int32_t *heights, uint8_t *tiles, uint8_t *tex_u,
                        uint8_t *sides, const ViewState &view) {
    const int32_t fine_view = static_cast<int32_t>(world.player.angle) * 10;
    for (int col=0;col<kViewWidth;++col) {
        const int fine=normalize_fine(fine_view+kWolfPixelAngleFine[col]);
        const auto tile=[&](int x,int y) {return tile_at(world,map,x,y);};
        const original_raywalk::Hit hit=original_raywalk::trace(world,tile,fine,view.x,view.y);
        if (!hit.valid) return RenderDetail::world;
        if (!hit.found) {heights[col]=0;tiles[col]=tex_u[col]=sides[col]=0;continue;}
        heights[col]=projected_height(hit.x,hit.y,view);
        uint8_t value=hit.tile;
        // Bind original adjacent-door wall flags to this port's immutable map
        // and one-bank texture IDs, without changing its wire/asset format.
        if (!hit.moving && value<=0x7f) {
            const int previous_x=hit.map_x-(hit.side==0 ? hit.step_x : 0);
            const int previous_y=hit.map_y-(hit.side==1 ? hit.step_y : 0);
            const uint8_t previous=tile_at(world,map,previous_x,previous_y);
            if (previous>=kDoorFlag && previous<=kDoorMax) {
                const uint8_t index=previous&kDoorMask;
                if (index>=world.door_count) return RenderDetail::world;
                const Door &door=world.doors[index];
                if ((hit.side==1 && door.vertical!=0) || (hit.side==0 && door.vertical==0))
                    value=kDoorJambTexture;
            }
        }
        tiles[col]=value;sides[col]=hit.side;tex_u[col]=hit.u;
    }
    return RenderDetail::ok;
}

uint8_t wall_texture_id(const WorldMirror &world, uint8_t tile) {
    if (tile >= kDoorFlag && tile <= kDoorMax)
        return world.doors[tile & kDoorMask].texture_id;
    return tile;
}

RenderDetail release_asset(const AssetProvider &provider, uint32_t lease) {
    const RenderDetail detail = provider.release(provider.context, lease);
    return detail == RenderDetail::ok ? RenderDetail::ok : RenderDetail::release;
}

// Private scalar wall sampler. No borrowed pointer survives this column.
template<bool Linear>
void sample_wall_column(const RenderTarget &frame, uint32_t x, uint32_t y,
                        int count, const uint8_t *texture, uint8_t source_x,
                        int32_t fraction, int32_t step) {
    const uint32_t mapped_x = (frame.x_bias + x) ^ frame.pixel_xor;
    const uint8_t preserve_mask = frame.preserve_mask;
    const uint8_t color_mask = static_cast<uint8_t>(frame.color_mask & 63u);
    const uint8_t *const column = texture + source_x;
    for (int row = 0; row < count; ++row) {
        int source_y = fraction >> 16;
        if (source_y >= kTextureSize) source_y = kTextureSize - 1;
        const uint8_t color = column[source_y * kTextureSize];
        if constexpr (Linear) {
            frame.linear[(y + static_cast<uint32_t>(row)) * W3P_SCREEN_WIDTH + x] =
                static_cast<uint8_t>(color & 63u);
        } else {
            uint8_t *const pixel = reinterpret_cast<uint8_t *>(
                frame.rows[y + static_cast<uint32_t>(row)]) + mapped_x;
            *pixel = static_cast<uint8_t>((*pixel & preserve_mask) |
                                         (color & color_mask));
        }
        fraction += step;
    }
}

void draw_wall_column(const RenderTarget &frame, uint32_t x, uint32_t y,
                      int count, const uint8_t *texture, uint8_t source_x,
                      int32_t fraction, int32_t step) {
    if (frame.linear != nullptr)
        sample_wall_column<true>(frame, x, y, count, texture, source_x, fraction, step);
    else
        sample_wall_column<false>(frame, x, y, count, texture, source_x, fraction, step);
}

RenderDetail draw_walls(const WorldMirror &world, const RenderResources &resources,
                        const RenderTarget &frame, const int32_t *heights,
                        const uint8_t *tiles, const uint8_t *tex_u,
                        RenderStats *stats) {
    static_assert(kViewWidth == 256, "column-chain byte domain changed");
    static_assert(W3P_MAX_WALL_TEXTURE < 128, "column-chain head domain changed");
    uint16_t heads[128];
    uint8_t next[kViewWidth];
    for (int id = 0; id < 128; ++id) heads[id] = kViewWidth;
    clear_bytes(next, 0, sizeof(next));
    for (int col = kViewWidth - 1; col >= 0; --col) {
        if (heights[col] <= 0) continue;
        const uint8_t id = wall_texture_id(world, tiles[col]);
        if (id < 1 || id > W3P_MAX_WALL_TEXTURE) continue;
        next[col] = heads[id] < kViewWidth
            ? static_cast<uint8_t>(heads[id]) : static_cast<uint8_t>(col);
        heads[id] = static_cast<uint16_t>(col);
    }
    for (uint16_t id = 1; id <= W3P_MAX_WALL_TEXTURE; ++id) {
        if (heads[id] == kViewWidth) continue;
        AssetSpan span{};
        RenderDetail detail = resources.assets.acquire(
            resources.assets.context,
            static_cast<uint16_t>(resources.wall_base + id), span);
        if (detail != RenderDetail::ok) return RenderDetail::asset;
        if (stats != nullptr) ++stats->wall_acquires;
        if (span.bytes == nullptr || span.byte_count < kTextureSize * kTextureSize) {
            const RenderDetail released = release_asset(resources.assets, span.lease);
            return released == RenderDetail::ok ? RenderDetail::bounds : released;
        }
        int cached_height = 0;
        int cached_top = 0;
        int cached_count = 0;
        int32_t cached_step = 0;
        int32_t cached_fraction = 0;
        for (int col = heads[id]; col < kViewWidth;
             col = next[col] == col ? kViewWidth : next[col]) {
            const int full_height = heights[col];
            if (full_height != cached_height) {
                cached_height = full_height;
                const int top = kCenterY - full_height / 2;
                cached_top = top < 0 ? 0 : top;
                const int bottom = top + full_height;
                const int clipped_bottom = bottom > kViewHeight ? kViewHeight : bottom;
                cached_count = clipped_bottom - cached_top;
                cached_step = cached_count > 0
                    ? (kTextureSize << 16) / full_height : 0;
                cached_fraction = cached_step * (cached_top - top);
            }
            if (cached_count <= 0) continue;
            draw_wall_column(frame, static_cast<uint32_t>(kViewX + col),
                             static_cast<uint32_t>(kViewY + cached_top),
                             cached_count, span.bytes, tex_u[col],
                             cached_fraction, cached_step);
        }
        detail = release_asset(resources.assets, span.lease);
        if (detail != RenderDetail::ok) return detail;
    }
    return RenderDetail::ok;
}

bool transform_point(int32_t x, int32_t y, const ViewState &view,
                     int32_t &trans_x, int32_t &trans_y, int32_t &screen_x,
                     uint32_t &height) {
    const int32_t gx = x - view.x;
    const int32_t gy = y - view.y;
    trans_x = fixed_mul(gx, view.cosine) - fixed_mul(gy, view.sine) - kActorSize;
    trans_y = fixed_mul(gy, view.cosine) + fixed_mul(gx, view.sine);
    if (trans_x < kMinDist) {
        screen_x = kCenterX;
        height = 0;
        return false;
    }
    screen_x = kCenterX + static_cast<int32_t>(
        (static_cast<int64_t>(trans_y) * kScale) / trans_x);
    height = static_cast<uint32_t>(kHeightNumerator / (trans_x >> 8));
    return height != 0 && screen_x >= -kCenterX &&
           screen_x <= kViewWidth + kCenterX;
}

int rotation_offset(const WorldMirror &world, const Actor &actor,
                    int32_t screen_x) {
    if (actor.rotations != 2 && actor.rotations != 8) return 0;
    const int view_angle = world.player.angle + (kCenterX - screen_x) / 8;
    int angle = (view_angle - 180) - actor.facing;
    angle += 360 / 16;
    while (angle >= 360) angle -= 360;
    while (angle < 0) angle += 360;
    return actor.rotations == 2 ? 4 * (angle / 180) : angle / 45;
}

void swap_sprites(VisSprite &a, VisSprite &b) {
    const VisSprite temporary = a;
    a = b;
    b = temporary;
}

void sift_min(VisSprite *sprites, uint16_t count, uint16_t root) {
    for (;;) {
        uint16_t child = static_cast<uint16_t>(root * 2u + 1u);
        if (child >= count) return;
        if (child + 1u < count && sprites[child + 1u].depth < sprites[child].depth)
            ++child;
        if (sprites[root].depth <= sprites[child].depth) return;
        swap_sprites(sprites[root], sprites[child]);
        root = child;
    }
}

// A min-heap moved to the tail produces descending depth: far to near.
void sort_far_to_near(VisSprite *sprites, uint16_t count) {
    if (count < 2) return;
    for (int root = count / 2 - 1; root >= 0; --root)
        sift_min(sprites, count, static_cast<uint16_t>(root));
    for (uint16_t remaining = count; remaining > 1; --remaining) {
        swap_sprites(sprites[0], sprites[remaining - 1]);
        sift_min(sprites, static_cast<uint16_t>(remaining - 1), 0);
    }
}

uint16_t collect_sprites(const WorldMirror &world, const ViewState &view,
                         VisSprite *sprites) {
    uint16_t count = 0;
    for (uint16_t index = 0; index < W3P_MAX_ACTORS; ++index) {
        const Actor &actor = world.actors[index];
        if (actor.shape < 0) continue;
        int32_t depth;
        int32_t lateral;
        int32_t screen_x;
        uint32_t height;
        if (!transform_point(actor.x, actor.y, view, depth, lateral,
                             screen_x, height)) continue;
        sprites[count++] = {screen_x, height,
            static_cast<int16_t>(actor.shape +
                rotation_offset(world, actor, screen_x)), 0, depth};
    }
    for (uint16_t index = 0; index < world.static_count; ++index) {
        const StaticObject &object = world.statics[index];
        if (object.shape < 0) continue;
        const int32_t x = (static_cast<int32_t>(object.tile_x) << 16) + 0x8000;
        const int32_t y = (static_cast<int32_t>(object.tile_y) << 16) + 0x8000;
        int32_t depth;
        int32_t lateral;
        int32_t screen_x;
        uint32_t height;
        if (!transform_point(x, y, view, depth, lateral, screen_x, height))
            continue;
        sprites[count++] = {screen_x, height, object.shape, 0, depth};
    }
    sort_far_to_near(sprites, count);
    return count;
}

RenderDetail draw_sprites(const RenderResources &resources,
                          const RenderTarget &frame,
                          const int32_t *wall_heights,
                          const VisSprite *sprites, uint16_t count,
                          RenderStats *stats) {
    for (uint16_t index = 0; index < count; ++index) {
        const VisSprite &sprite = sprites[index];
        AssetSpan span{};
        RenderDetail detail = resources.assets.acquire(
            resources.assets.context,
            static_cast<uint16_t>(resources.sprite_base +
                                  static_cast<uint16_t>(sprite.shape)), span);
        if (detail != RenderDetail::ok) return RenderDetail::asset;
        if (stats != nullptr) ++stats->sprite_acquires;
        if (span.bytes == nullptr || span.byte_count < kTextureSize * kTextureSize) {
            const RenderDetail released = release_asset(resources.assets, span.lease);
            return released == RenderDetail::ok ? RenderDetail::bounds : released;
        }

        const int size = static_cast<int>(sprite.view_height);
        const int left = sprite.view_x - size / 2;
        const int top = kCenterY - size / 2;
        const int clipped_left = left < 0 ? 0 : left;
        const int right = left + size;
        const int clipped_right = right > kViewWidth ? kViewWidth : right;
        const int clipped_top = top < 0 ? 0 : top;
        const int bottom = top + size;
        const int clipped_bottom = bottom > kViewHeight ? kViewHeight : bottom;
        const int width = clipped_right - clipped_left;
        const int height = clipped_bottom - clipped_top;
        if (width > 0 && height > 0) {
            const int32_t x_step = (kTextureSize << 16) / size;
            const int32_t y_step = (kTextureSize << 16) / size;
            int32_t y_fraction = (clipped_top - top) * y_step;
            for (int y = 0; y < height; ++y) {
                int source_y = y_fraction >> 16;
                if (source_y >= kTextureSize) source_y = kTextureSize - 1;
                int32_t x_fraction = (clipped_left - left) * x_step;
                for (int x = 0; x < width; ++x) {
                    const int screen_x = clipped_left + x;
                    int source_x = x_fraction >> 16;
                    if (source_x >= kTextureSize) source_x = kTextureSize - 1;
                    if (wall_heights[screen_x] < size) {
                        const uint8_t pixel =
                            span.bytes[source_y * kTextureSize + source_x];
                        if ((pixel & 0xc0u) != 0) {
                            put_pixel(frame,
                                static_cast<uint32_t>(kViewX + screen_x),
                                static_cast<uint32_t>(kViewY + clipped_top + y),
                                pixel & 63u);
                        }
                    }
                    x_fraction += x_step;
                }
                y_fraction += y_step;
            }
        }
        detail = release_asset(resources.assets, span.lease);
        if (detail != RenderDetail::ok) return detail;
    }
    return RenderDetail::ok;
}

RenderDetail draw_view_weapon(const WorldMirror &world,
                              const RenderResources &resources,
                              const RenderTarget &frame, RenderStats *stats) {
    if (world.view_weapon_shape < 0) return RenderDetail::ok;
    AssetSpan span{};
    RenderDetail detail = resources.assets.acquire(
        resources.assets.context,
        static_cast<uint16_t>(resources.sprite_base +
                              static_cast<uint16_t>(world.view_weapon_shape)),
        span);
    if (detail != RenderDetail::ok) return RenderDetail::asset;
    if (stats != nullptr) ++stats->weapon_acquires;
    if (span.bytes == nullptr || span.byte_count < kTextureSize * kTextureSize) {
        const RenderDetail released = release_asset(resources.assets, span.lease);
        return released == RenderDetail::ok ? RenderDetail::bounds : released;
    }

    const int size = kViewHeight + 1;
    const int left = kViewWidth / 2 - size / 2;
    const int top = (kViewHeight - size) / 2;
    const int clipped_left = left < 0 ? 0 : left;
    const int clipped_right = left + size > kViewWidth
        ? kViewWidth : left + size;
    const int clipped_top = top < 0 ? 0 : top;
    const int clipped_bottom = top + size > kViewHeight
        ? kViewHeight : top + size;
    const int32_t x_step = (kTextureSize << 16) / size;
    const int32_t y_step = (kTextureSize << 16) / size;
    int32_t y_fraction = (clipped_top - top) * y_step;
    for (int y = clipped_top; y < clipped_bottom; ++y) {
        int source_y = y_fraction >> 16;
        if (source_y >= kTextureSize) source_y = kTextureSize - 1;
        int32_t x_fraction = (clipped_left - left) * x_step;
        for (int x = clipped_left; x < clipped_right; ++x) {
            int source_x = x_fraction >> 16;
            if (source_x >= kTextureSize) source_x = kTextureSize - 1;
            const uint8_t pixel = span.bytes[source_y * kTextureSize + source_x];
            if ((pixel & 0xc0u) != 0) {
                put_pixel(frame, static_cast<uint32_t>(kViewX + x),
                          static_cast<uint32_t>(kViewY + y), pixel & 63u);
            }
            x_fraction += x_step;
        }
        y_fraction += y_step;
    }
    detail = release_asset(resources.assets, span.lease);
    return detail;
}

bool hud_dimensions(uint16_t chunk, uint16_t &width, uint16_t &height) {
    if (chunk == kHudStatusBar) {
        width = 320;
        height = 40;
        return true;
    }
    if (chunk >= kHudKnife && chunk <= kHudKnife + 3) {
        width = 48;
        height = 24;
        return true;
    }
    if (chunk >= kHudNoKey && chunk <= kHudDigit0 + 9) {
        width = 8;
        height = 16;
        return true;
    }
    if (chunk >= kHudFace1A && chunk <= kHudFaceGotGatling) {
        width = 24;
        height = 32;
        return true;
    }
    return false;
}

bool append_hud_draw(HudDraw *draws, uint8_t &count, uint16_t chunk,
                     int x, int y) {
    if (count >= 20) return false;
    draws[count++] = {chunk, static_cast<int16_t>(x), static_cast<int16_t>(y)};
    return true;
}

bool append_hud_number(HudDraw *draws, uint8_t &count, int x, int y,
                       int width, uint32_t value) {
    uint32_t modulus = 1;
    for (int i = 0; i < width; ++i) modulus *= 10;
    value %= modulus;
    uint32_t divisor = modulus / 10;
    bool started = false;
    for (int i = 0; i < width; ++i) {
        const uint8_t digit = static_cast<uint8_t>(value / divisor);
        value %= divisor;
        uint16_t chunk = kHudDigit0 + digit;
        if (!started && digit == 0 && i != width - 1) chunk = kHudBlank;
        else started = true;
        if (!append_hud_draw(draws, count, chunk, x + i * 8, y)) return false;
        if (divisor > 1) divisor /= 10;
    }
    return true;
}

void blit_rgba2222(const RenderTarget &frame, const uint8_t *source,
                   uint16_t width, uint16_t height, int left, int top) {
    for (uint16_t source_y = 0; source_y < height; ++source_y) {
        const int destination_y = top + source_y;
        if (destination_y < 0 || destination_y >= static_cast<int>(W3P_SCREEN_HEIGHT))
            continue;
        for (uint16_t source_x = 0; source_x < width; ++source_x) {
            const int destination_x = left + source_x;
            if (destination_x < 0 ||
                destination_x >= static_cast<int>(W3P_SCREEN_WIDTH)) continue;
            const uint8_t pixel = source[static_cast<uint32_t>(source_y) * width +
                                         source_x];
            if ((pixel & 0xc0u) != 0) {
                put_pixel(frame, static_cast<uint32_t>(destination_x),
                          static_cast<uint32_t>(destination_y), pixel & 63u);
            }
        }
    }
}

RenderDetail draw_hud(const WorldMirror &world,
                      const RenderResources &resources,
                      const RenderTarget &frame, RenderStats *stats) {
    HudDraw draws[20];
    uint8_t count = 0;
    if (!append_hud_draw(draws, count, kHudStatusBar, 0, 200) ||
        !append_hud_number(draws, count, 16, 216, 2, world.hud.level) ||
        !append_hud_number(draws, count, 48, 216, 6, world.hud.score) ||
        !append_hud_number(draws, count, 112, 216, 1, world.hud.lives))
        return RenderDetail::world;
    const uint16_t face = world.hud.health == 0
        ? kHudFaceDead
        : world.hud.face == 3
            ? kHudFaceGotGatling
            : static_cast<uint16_t>(kHudFace1A +
                ((100u - world.hud.health) / 16u) * 3u + world.hud.face);
    if (!append_hud_draw(draws, count, face, 136, 204) ||
        !append_hud_number(draws, count, 168, 216, 3, world.hud.health) ||
        !append_hud_number(draws, count, 216, 216, 2, world.hud.ammo) ||
        !append_hud_draw(draws, count,
            (world.hud.keys & 1u) != 0 ? kHudGoldKey : kHudNoKey, 240, 204) ||
        !append_hud_draw(draws, count,
            (world.hud.keys & 2u) != 0 ? kHudSilverKey : kHudNoKey, 240, 220) ||
        !append_hud_draw(draws, count, kHudKnife + world.hud.weapon, 256, 208))
        return RenderDetail::world;

    for (uint8_t i = 0; i < count; ++i) {
        bool already_drawn = false;
        for (uint8_t prior = 0; prior < i; ++prior) {
            if (draws[prior].chunk == draws[i].chunk) already_drawn = true;
        }
        if (already_drawn) continue;
        uint16_t width;
        uint16_t height;
        if (!hud_dimensions(draws[i].chunk, width, height))
            return RenderDetail::world;
        AssetSpan span{};
        RenderDetail detail = resources.assets.acquire(
            resources.assets.context,
            static_cast<uint16_t>(resources.hud_base + draws[i].chunk), span);
        if (detail != RenderDetail::ok) return RenderDetail::asset;
        if (stats != nullptr) ++stats->hud_acquires;
        const uint32_t required = static_cast<uint32_t>(width) * height;
        if (span.bytes == nullptr || span.byte_count < required) {
            const RenderDetail released = release_asset(resources.assets, span.lease);
            return released == RenderDetail::ok ? RenderDetail::bounds : released;
        }
        for (uint8_t draw = i; draw < count; ++draw) {
            if (draws[draw].chunk == draws[i].chunk) {
                blit_rgba2222(frame, span.bytes, width, height,
                              draws[draw].x, draws[draw].y);
            }
        }
        detail = release_asset(resources.assets, span.lease);
        if (detail != RenderDetail::ok) return detail;
    }
    return RenderDetail::ok;
}

}  // namespace

RenderDetail render_world_to_target(const WorldMirror &world,
                                    const RenderResources &resources,
                                    const RenderTarget &frame,
                                    uint32_t height_offset,
                                    uint32_t tile_offset,
                                    uint32_t tex_u_offset,
                                    uint32_t side_offset,
                                    uint32_t sprite_offset,
                                    uint32_t required_workspace,
                                    RenderStats *stats) {
    clear_stats(stats);
    if (!world.ready || resources.tilemap == nullptr ||
        resources.workspace == nullptr || resources.assets.acquire == nullptr ||
        resources.assets.release == nullptr) return RenderDetail::argument;
    if (world.tilemap_id == 0 || resources.wall_base != W3P_DEFAULT_WALL_BASE ||
        resources.sprite_base != W3P_DEFAULT_SPRITE_BASE ||
        resources.hud_base != W3P_DEFAULT_HUD_BASE)
        return RenderDetail::argument;
    if (resources.tilemap_bytes < W3P_MAP_SIZE * W3P_MAP_SIZE ||
        resources.workspace_bytes < required_workspace ||
        (frame.linear == nullptr && frame.rows == nullptr))
        return RenderDetail::bounds;

    int32_t *const heights = reinterpret_cast<int32_t *>(
        resources.workspace + height_offset);
    uint8_t *const tiles = resources.workspace + tile_offset;
    uint8_t *const tex_u = resources.workspace + tex_u_offset;
    uint8_t *const sides = resources.workspace + side_offset;
    VisSprite *const sprites = reinterpret_cast<VisSprite *>(
        resources.workspace + sprite_offset);

    compose_background(frame);
    const ViewState view = setup_view(world);
    RenderDetail detail = cast_walls(
        world, resources.tilemap, heights, tiles, tex_u, sides, view);
    if (detail != RenderDetail::ok) return detail;
    detail = draw_walls(world, resources, frame, heights, tiles, tex_u, stats);
    if (detail != RenderDetail::ok) return detail;
    const uint16_t count = collect_sprites(world, view, sprites);
    if (stats != nullptr) stats->visible_sprites = count;
    detail = draw_sprites(resources, frame, heights, sprites, count, stats);
    if (detail != RenderDetail::ok) return detail;
    detail = draw_view_weapon(world, resources, frame, stats);
    if (detail != RenderDetail::ok) return detail;
    detail = draw_hud(world, resources, frame, stats);
    if (detail != RenderDetail::ok) return detail;
    apply_palette_shift(frame, world.hud.palette_shift);
    return RenderDetail::ok;
}

RenderDetail render_world(const WorldMirror &world,
                          const RenderResources &resources,
                          RenderStats *stats) {
    const RenderTarget frame = {
        resources.workspace, nullptr, 0, 0, 0x3fu, 0u};
    return render_world_to_target(
        world, resources, frame, W3P_WALL_HEIGHT_OFFSET,
        W3P_WALL_TILE_OFFSET, W3P_WALL_TEXU_OFFSET, W3P_WALL_SIDE_OFFSET,
        W3P_SPRITE_ARENA_OFFSET, W3P_WORKSPACE_BYTES, stats);
}

RenderDetail render_world_direct(const WorldMirror &world,
                                 const RenderResources &resources,
                                 const RenderTarget &target,
                                 RenderStats *stats) {
    return render_world_to_target(
        world, resources, target, W3P_DIRECT_WALL_HEIGHT_OFFSET,
        W3P_DIRECT_WALL_TILE_OFFSET, W3P_DIRECT_WALL_TEXU_OFFSET,
        W3P_DIRECT_WALL_SIDE_OFFSET, W3P_DIRECT_SPRITE_ARENA_OFFSET,
        W3P_DIRECT_WORKSPACE_BYTES, stats);
}

const char *render_detail_name(RenderDetail detail) {
    switch (detail) {
    case RenderDetail::ok: return "ok";
    case RenderDetail::argument: return "argument";
    case RenderDetail::bounds: return "bounds";
    case RenderDetail::world: return "world";
    case RenderDetail::asset: return "asset";
    case RenderDetail::release: return "release";
    }
    return "unknown";
}

}  // namespace wolf3d_production
