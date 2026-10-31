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

struct RenderStats {
    uint16_t visible_sprites;
    uint16_t wall_acquires;
    uint16_t sprite_acquires;
    uint16_t weapon_acquires;
    uint16_t hud_acquires;
};

// Composes the 320x240 RGB222 frame at workspace offset zero and leaves the
// exact DDA metadata in the schema-1 scratch regions. This tranche covers the
// play surround, walls, moving doors, actors/statics, view weapon and HUD.
RenderDetail render_world(
    const WorldMirror &world, const RenderResources &resources,
    RenderStats *stats = nullptr);

const char *render_detail_name(RenderDetail detail);

}  // namespace wolf3d_production

#endif
