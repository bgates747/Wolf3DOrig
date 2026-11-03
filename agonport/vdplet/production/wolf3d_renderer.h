#ifndef WOLF3D_PRODUCTION_RENDERER_H
#define WOLF3D_PRODUCTION_RENDERER_H

#include <stddef.h>
#include <stdint.h>

#include "wolf3d_world_mirror.h"

namespace wolf3d_production {

// One finite lease returned by the module wrapper. The pure renderer never
// retains this pointer or token after render_world returns.
struct AssetSpan {
    const uint8_t *bytes;
    uint32_t byte_count;
    uint32_t lease;
};

enum class RenderDetail : uint8_t {
    ok = 0,
    argument,
    bounds,
    world,
    asset,
    release,
};

typedef RenderDetail (*AcquireAsset)(
    void *context, uint16_t buffer_id, AssetSpan &span);
typedef RenderDetail (*ReleaseAsset)(void *context, uint32_t lease);

struct AssetProvider {
    void *context;
    AcquireAsset acquire;
    ReleaseAsset release;
};

struct RenderResources {
    const uint8_t *tilemap;
    uint32_t tilemap_bytes;
    uint8_t *workspace;
    uint32_t workspace_bytes;
    uint16_t wall_base;
    uint16_t sprite_base;
    uint16_t hud_base;
    AssetProvider assets;
};

// A render target is either the copied RGB222 oracle buffer or the VDP's
// native hidden-framebuffer rows. Native rows preserve the host-owned sync
// bits while replacing only the six RGB222 colour bits.
struct RenderTarget {
    uint8_t *linear;
    uintptr_t *rows;
    uint32_t x_bias;
    uint32_t pixel_xor;
    uint8_t color_mask;
    uint8_t preserve_mask;
};

#define W3P_DIRECT_ROW_POINTER_BYTES \
    (W3P_SCREEN_HEIGHT * sizeof(uintptr_t))
#define W3P_DIRECT_WALL_HEIGHT_OFFSET W3P_DIRECT_ROW_POINTER_BYTES
#define W3P_DIRECT_WALL_TILE_OFFSET \
    (W3P_DIRECT_WALL_HEIGHT_OFFSET + W3P_WALL_HEIGHT_BYTES)
#define W3P_DIRECT_WALL_TEXU_OFFSET \
    (W3P_DIRECT_WALL_TILE_OFFSET + 256u)
#define W3P_DIRECT_WALL_SIDE_OFFSET \
    (W3P_DIRECT_WALL_TEXU_OFFSET + 256u)
#define W3P_DIRECT_SPRITE_ARENA_OFFSET \
    (W3P_DIRECT_WALL_SIDE_OFFSET + 256u)
#define W3P_DIRECT_WORKSPACE_BYTES \
    (W3P_DIRECT_SPRITE_ARENA_OFFSET + W3P_SPRITE_ARENA_BYTES)
static_assert(sizeof(uintptr_t) != 4 ||
                  W3P_DIRECT_WORKSPACE_BYTES ==
                      W3P_DIRECT_TARGET_WORKSPACE_BYTES,
              "direct workspace target pointer layout drifted");

struct RenderStats {
    uint16_t visible_sprites;
    uint16_t wall_acquires;
    uint16_t sprite_acquires;
    uint16_t weapon_acquires;
    uint16_t hud_acquires;
};

// Composes the 320x240 RGB222 frame at workspace offset zero and leaves the
// exact DDA metadata in the schema-2 scratch regions. This tranche covers the
// play surround, walls, moving doors, actors/statics, view weapon and HUD.
RenderDetail render_world(
    const WorldMirror &world, const RenderResources &resources,
    RenderStats *stats = nullptr);

// Same compositor, but scratch starts after the row-pointer table and pixels
// go straight to the acquired native rows. No 320x240 intermediate exists.
RenderDetail render_world_direct(
    const WorldMirror &world, const RenderResources &resources,
    const RenderTarget &target, RenderStats *stats = nullptr);

const char *render_detail_name(RenderDetail detail);

}  // namespace wolf3d_production

#endif
