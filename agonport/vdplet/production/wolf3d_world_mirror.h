#ifndef WOLF3D_PRODUCTION_WORLD_MIRROR_H
#define WOLF3D_PRODUCTION_WORLD_MIRROR_H

#include <stddef.h>
#include <stdint.h>

#include "wolf3d_production_contract.h"

namespace wolf3d_production {

struct Player {
    int32_t x;
    int32_t y;
    uint16_t angle;
};

struct Door {
    uint16_t position;
    uint8_t tile_x;
    uint8_t tile_y;
    uint8_t vertical;
    uint8_t lock;
    uint8_t action;
    uint8_t texture_id;
};

struct Actor {
    int32_t x;
    int32_t y;
    int16_t shape;
    uint16_t facing;
    uint8_t rotations;
};

struct StaticObject {
    int16_t shape;
    uint8_t tile_x;
    uint8_t tile_y;
    uint8_t flags;
};

struct Hud {
    uint8_t health;
    uint8_t ammo;
    uint8_t keys;
    uint8_t weapon;
    uint32_t score;
    uint8_t level;
    uint8_t face;
    uint8_t lives;
};

struct PushwallCompletion {
    uint8_t origin_x;
    uint8_t origin_y;
    uint8_t current_x;
    uint8_t current_y;
    uint8_t texture;
};

struct PushwallState {
    uint8_t status;
    uint8_t origin_x;
    uint8_t origin_y;
    uint8_t current_x;
    uint8_t current_y;
    uint8_t direction;
    uint8_t position;
    uint8_t texture;
    uint8_t completed_count;
    PushwallCompletion completed[W3P_MAX_PUSHWALLS];
};

static_assert(sizeof(PushwallCompletion) == W3P_PUSHWALL_COMPLETED_BYTES,
              "pushwall completion wire layout drifted");
static_assert(sizeof(PushwallState) == W3P_PUSHWALL_BYTES,
              "pushwall state wire layout drifted");

struct ResourceDescriptor {
    uint16_t flags;
    uint16_t workspace_id;
    uint16_t update_id;
    uint16_t tilemap_id;
    uint16_t wall_base;
    uint16_t sprite_base;
    uint16_t hud_base;
    uint16_t generation_seed;
};

struct WorldMirror {
    uint32_t last_batch_fingerprint;
    uint16_t generation;
    uint16_t presented_generation;
    uint16_t configured_tilemap_id;
    uint16_t tilemap_id;
    uint16_t static_count;
    uint8_t door_count;
    uint8_t ready;
    uint8_t pending_present;
    Player player;
    Door doors[W3P_MAX_DOORS];
    Actor actors[W3P_MAX_ACTORS];
    StaticObject statics[W3P_MAX_STATICS];
    Hud hud;
    int16_t view_weapon_shape;
    PushwallState pushwall;
};

static_assert(sizeof(WorldMirror) <= W3P_MIRROR_MAX_BYTES,
              "production world mirror exceeded its resident-data budget");

enum class BatchDetail : uint8_t {
    ok = W3P_DETAIL_OK,
    argument = W3P_DETAIL_ARGUMENT,
    bounds = W3P_DETAIL_BOUNDS,
    generation = W3P_DETAIL_GENERATION,
    duplicate = W3P_DETAIL_DUPLICATE,
    incomplete = W3P_DETAIL_INCOMPLETE,
    order = W3P_DETAIL_ORDER,
    record = W3P_DETAIL_RECORD,
};

// Establishes an unready mirror whose first accepted batch must be a complete
// generation seed+1 snapshot. No dynamic allocation or standard library state
// is used, so this code remains suitable for the freestanding module.
void initialize_world_mirror(
    WorldMirror &mirror, uint16_t generation_seed,
    uint16_t configured_tilemap_id);

// Validates the exact 24-byte CONFIG descriptor without mutating output on
// failure. Schema 2 deliberately pins the established application asset bases
// and copied-pixel workspace while the standalone backend remains the oracle.
BatchDetail validate_resource_descriptor(
    ResourceDescriptor &output, const uint8_t *bytes, size_t byte_count);

// Two-pass atomic update: the first pass validates structure, generation,
// values, uniqueness and complete-snapshot coverage without mutation. The
// second pass cannot fail and applies the already validated records.
BatchDetail apply_update_batch(
    WorldMirror &mirror, const uint8_t *bytes, size_t byte_count);

// Commit publication only after pixels_write succeeds. A failed publication
// leaves pending_present set, allowing the exact same batch/generation to be
// retried while refusing both altered retries and newer generations.
void mark_mirror_presented(WorldMirror &mirror);

const char *batch_detail_name(BatchDetail detail);

}  // namespace wolf3d_production

#endif
