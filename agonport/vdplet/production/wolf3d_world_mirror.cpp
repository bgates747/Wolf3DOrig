#include "wolf3d_world_mirror.h"

namespace wolf3d_production {
namespace {

struct BatchHeader {
    uint32_t fingerprint;
    uint16_t flags;
    uint16_t total_bytes;
    uint16_t record_count;
    uint16_t generation;
    bool replay;
};

struct Validation {
    bool level_seen;
    bool player_seen;
    bool hud_seen;
    bool view_weapon_seen;
    uint8_t door_count;
    uint16_t static_count;
    bool doors[W3P_MAX_DOORS];
    bool actors[W3P_MAX_ACTORS];
    bool statics[W3P_MAX_STATICS];
};

uint16_t load_u16(const uint8_t *p) {
    return static_cast<uint16_t>(p[0]) |
        static_cast<uint16_t>(static_cast<uint16_t>(p[1]) << 8);
}

int16_t load_i16(const uint8_t *p) {
    return static_cast<int16_t>(load_u16(p));
}

uint32_t load_u32(const uint8_t *p) {
    return static_cast<uint32_t>(load_u16(p)) |
        (static_cast<uint32_t>(load_u16(p + 2)) << 16);
}

uint32_t fingerprint(const uint8_t *bytes, size_t byte_count) {
    uint32_t hash = 2166136261u;
    while (byte_count-- != 0) {
        hash ^= *bytes++;
        hash *= 16777619u;
    }
    return hash;
}

int32_t load_i32(const uint8_t *p) {
    return static_cast<int32_t>(load_u32(p));
}

void clear_bytes(void *destination, size_t count) {
    uint8_t *p = static_cast<uint8_t *>(destination);
    while (count-- != 0) *p++ = 0;
}

void clear_render_state(WorldMirror &mirror) {
    const uint16_t generation = mirror.generation;
    const uint16_t presented_generation = mirror.presented_generation;
    const uint16_t configured_tilemap_id = mirror.configured_tilemap_id;
    const uint32_t last_batch_fingerprint = mirror.last_batch_fingerprint;
    const uint8_t pending_present = mirror.pending_present;
    clear_bytes(&mirror, sizeof(mirror));
    mirror.generation = generation;
    mirror.presented_generation = presented_generation;
    mirror.configured_tilemap_id = configured_tilemap_id;
    mirror.last_batch_fingerprint = last_batch_fingerprint;
    mirror.pending_present = pending_present;
    mirror.view_weapon_shape = -1;
    for (size_t i = 0; i < W3P_MAX_ACTORS; ++i) {
        mirror.actors[i].shape = -1;
    }
    for (size_t i = 0; i < W3P_MAX_STATICS; ++i) {
        mirror.statics[i].shape = -1;
    }
}

bool valid_position(int32_t value) {
    return value >= 0 &&
        static_cast<uint32_t>(value) < (W3P_MAP_SIZE << 16);
}

bool valid_shape(int16_t value, bool removal_allowed) {
    return (removal_allowed && value == -1) ||
        (value >= 0 && value <= static_cast<int16_t>(W3P_MAX_SHAPE));
}

BatchDetail parse_header(
    const WorldMirror &mirror, const uint8_t *bytes, size_t byte_count,
    BatchHeader &header) {
    if (bytes == nullptr) return BatchDetail::argument;
    if (byte_count < W3P_BATCH_HEADER_BYTES ||
        byte_count > W3P_BATCH_MAX_BYTES) return BatchDetail::bounds;
    if (load_u32(bytes + W3P_BATCH_MAGIC_OFFSET) != W3P_BATCH_MAGIC ||
        bytes[W3P_BATCH_SCHEMA_OFFSET] != W3P_SCHEMA_VERSION ||
        bytes[W3P_BATCH_HEADER_OFFSET] != W3P_BATCH_HEADER_BYTES ||
        load_u16(bytes + W3P_BATCH_RESERVED_OFFSET) != 0) {
        return BatchDetail::argument;
    }
    header.flags = load_u16(bytes + W3P_BATCH_FLAGS_OFFSET);
    header.total_bytes = load_u16(bytes + W3P_BATCH_TOTAL_OFFSET);
    header.record_count = load_u16(bytes + W3P_BATCH_RECORDS_OFFSET);
    header.generation = load_u16(bytes + W3P_BATCH_GENERATION_OFFSET);
    header.fingerprint = fingerprint(bytes, byte_count);
    header.replay = false;
    if ((header.flags & ~W3P_BATCH_KNOWN_FLAGS) != 0) {
        return BatchDetail::argument;
    }
    if (header.total_bytes != byte_count ||
        header.record_count > W3P_BATCH_MAX_RECORDS) {
        return BatchDetail::bounds;
    }
    if (header.generation == 0) return BatchDetail::generation;
    if (header.generation == mirror.generation) {
        if (!mirror.pending_present ||
            header.fingerprint != mirror.last_batch_fingerprint) {
            return BatchDetail::generation;
        }
        header.replay = true;
    } else {
        if (mirror.pending_present || mirror.generation == 0xFFFFu ||
            header.generation != static_cast<uint16_t>(mirror.generation + 1u)) {
            return BatchDetail::generation;
        }
    }
    if (!mirror.ready && (header.flags & W3P_BATCH_FLAG_FULL) == 0) {
        return BatchDetail::incomplete;
    }
    return BatchDetail::ok;
}

BatchDetail mark_once(bool &value) {
    if (value) return BatchDetail::duplicate;
    value = true;
    return BatchDetail::ok;
}

BatchDetail validate_record(
    const WorldMirror &mirror, const BatchHeader &header,
    Validation &validation, uint16_t record_index, uint8_t type,
    const uint8_t *p, uint8_t payload_bytes) {
    const bool full = (header.flags & W3P_BATCH_FLAG_FULL) != 0;
    BatchDetail detail;
    switch (type) {
    case W3P_RECORD_LEVEL:
        if (!full || record_index != 0) return BatchDetail::order;
        if (payload_bytes != W3P_LEVEL_BYTES) return BatchDetail::bounds;
        detail = mark_once(validation.level_seen);
        if (detail != BatchDetail::ok) return detail;
        if (load_u16(p) == 0 ||
            load_u16(p) != mirror.configured_tilemap_id ||
            p[2] > W3P_MAX_DOORS ||
            load_u16(p + 3) > W3P_MAX_STATICS || p[5] != 0) {
            return BatchDetail::argument;
        }
        validation.door_count = p[2];
        validation.static_count = load_u16(p + 3);
        return BatchDetail::ok;

    case W3P_RECORD_PLAYER:
        if (payload_bytes != W3P_PLAYER_BYTES) return BatchDetail::bounds;
        detail = mark_once(validation.player_seen);
        if (detail != BatchDetail::ok) return detail;
        if (!valid_position(load_i32(p)) || !valid_position(load_i32(p + 4)) ||
            load_u16(p + 8) >= 360u) return BatchDetail::argument;
        return BatchDetail::ok;

    case W3P_RECORD_DOOR: {
        if (payload_bytes != W3P_DOOR_BYTES) return BatchDetail::bounds;
        const uint8_t index = p[0];
        const uint8_t limit = full ? validation.door_count : mirror.door_count;
        if (index >= limit) return BatchDetail::argument;
        detail = mark_once(validation.doors[index]);
        if (detail != BatchDetail::ok) return detail;
        if (p[1] >= W3P_MAP_SIZE || p[2] >= W3P_MAP_SIZE || p[3] > 1 ||
            p[4] > 5 || p[5] > 3 || p[8] == 0 ||
            p[8] > W3P_MAX_WALL_TEXTURE) return BatchDetail::argument;
        return BatchDetail::ok;
    }

    case W3P_RECORD_ACTOR_SET: {
        if (payload_bytes != W3P_ACTOR_SET_BYTES) return BatchDetail::bounds;
        const uint16_t index = load_u16(p);
        const int16_t shape = load_i16(p + 2);
        const uint8_t rotations = p[14];
        if (index == 0 || index >= W3P_MAX_ACTORS ||
            !valid_shape(shape, false) ||
            !valid_position(load_i32(p + 4)) ||
            !valid_position(load_i32(p + 8)) || load_u16(p + 12) >= 360u ||
            (rotations != 0 && rotations != 2 && rotations != 8) ||
            (rotations == 2 && shape > static_cast<int16_t>(W3P_MAX_SHAPE - 4)) ||
            (rotations == 8 && shape > static_cast<int16_t>(W3P_MAX_SHAPE - 7))) {
            return BatchDetail::argument;
        }
        return mark_once(validation.actors[index]);
    }

    case W3P_RECORD_ACTOR_REMOVE: {
        if (payload_bytes != W3P_ACTOR_REMOVE_BYTES) return BatchDetail::bounds;
        if (full) return BatchDetail::argument;
        const uint16_t index = load_u16(p);
        if (index == 0 || index >= W3P_MAX_ACTORS) {
            return BatchDetail::argument;
        }
        return mark_once(validation.actors[index]);
    }

    case W3P_RECORD_STATIC: {
        if (payload_bytes != W3P_STATIC_BYTES) return BatchDetail::bounds;
        const uint16_t index = load_u16(p);
        const int16_t shape = load_i16(p + 4);
        if (full) {
            if (index >= validation.static_count) return BatchDetail::argument;
        } else {
            // Gameplay appends dropped items to the authoritative static
            // array.  A partial batch may therefore extend the mirror by one
            // or more contiguous slots.  The eZ80 serializer emits statics in
            // ascending order, so validation.static_count is also the next
            // legal append index during this atomic first pass.
            if (validation.static_count == 0)
                validation.static_count = mirror.static_count;
            if (index > validation.static_count ||
                (index == validation.static_count && shape == -1) ||
                index >= W3P_MAX_STATICS) return BatchDetail::argument;
            if (index == validation.static_count) ++validation.static_count;
        }
        detail = mark_once(validation.statics[index]);
        if (detail != BatchDetail::ok) return detail;
        if (p[2] >= W3P_MAP_SIZE || p[3] >= W3P_MAP_SIZE ||
            !valid_shape(shape, true) || (p[6] & ~2u) != 0) {
            return BatchDetail::argument;
        }
        return BatchDetail::ok;
    }

    case W3P_RECORD_HUD:
        if (payload_bytes != W3P_HUD_BYTES) return BatchDetail::bounds;
        detail = mark_once(validation.hud_seen);
        if (detail != BatchDetail::ok) return detail;
        if (p[0] > 100 || p[1] > 99 || (p[2] & ~3u) != 0 || p[3] > 3 ||
            p[8] == 0 || p[8] > 10 || p[9] > 2 || p[11] != 0) {
            return BatchDetail::argument;
        }
        return BatchDetail::ok;

    case W3P_RECORD_VIEW_WEAPON:
        if (payload_bytes != W3P_VIEW_WEAPON_BYTES) return BatchDetail::bounds;
        detail = mark_once(validation.view_weapon_seen);
        if (detail != BatchDetail::ok) return detail;
        return valid_shape(load_i16(p), true)
            ? BatchDetail::ok : BatchDetail::argument;

    default:
        return BatchDetail::record;
    }
}

BatchDetail validate_batch(
    const WorldMirror &mirror, const uint8_t *bytes, size_t byte_count,
    BatchHeader &header) {
    BatchDetail detail = parse_header(mirror, bytes, byte_count, header);
    if (detail != BatchDetail::ok) return detail;

    Validation validation;
    clear_bytes(&validation, sizeof(validation));
    size_t cursor = W3P_BATCH_HEADER_BYTES;
    for (uint16_t i = 0; i < header.record_count; ++i) {
        if (cursor + W3P_RECORD_HEADER_BYTES > byte_count) {
            return BatchDetail::bounds;
        }
        const uint8_t type = bytes[cursor];
        const uint8_t payload_bytes = bytes[cursor + 1];
        cursor += W3P_RECORD_HEADER_BYTES;
        if (cursor + payload_bytes > byte_count) return BatchDetail::bounds;
        detail = validate_record(
            mirror, header, validation, i, type, bytes + cursor, payload_bytes);
        if (detail != BatchDetail::ok) return detail;
        cursor += payload_bytes;
    }
    if (cursor != byte_count) return BatchDetail::bounds;

    if ((header.flags & W3P_BATCH_FLAG_FULL) != 0) {
        if (!validation.level_seen || !validation.player_seen ||
            !validation.hud_seen || !validation.view_weapon_seen) {
            return BatchDetail::incomplete;
        }
        for (uint8_t i = 0; i < validation.door_count; ++i) {
            if (!validation.doors[i]) return BatchDetail::incomplete;
        }
        for (uint16_t i = 0; i < validation.static_count; ++i) {
            if (!validation.statics[i]) return BatchDetail::incomplete;
        }
    }
    return BatchDetail::ok;
}

void apply_record(WorldMirror &mirror, uint8_t type, const uint8_t *p) {
    switch (type) {
    case W3P_RECORD_LEVEL:
        mirror.tilemap_id = load_u16(p);
        mirror.door_count = p[2];
        mirror.static_count = load_u16(p + 3);
        break;
    case W3P_RECORD_PLAYER:
        mirror.player.x = load_i32(p);
        mirror.player.y = load_i32(p + 4);
        mirror.player.angle = load_u16(p + 8);
        break;
    case W3P_RECORD_DOOR: {
        Door &door = mirror.doors[p[0]];
        door.tile_x = p[1];
        door.tile_y = p[2];
        door.vertical = p[3];
        door.lock = p[4];
        door.action = p[5];
        door.position = load_u16(p + 6);
        door.texture_id = p[8];
        break;
    }
    case W3P_RECORD_ACTOR_SET: {
        Actor &actor = mirror.actors[load_u16(p)];
        actor.shape = load_i16(p + 2);
        actor.x = load_i32(p + 4);
        actor.y = load_i32(p + 8);
        actor.facing = load_u16(p + 12);
        actor.rotations = p[14];
        break;
    }
    case W3P_RECORD_ACTOR_REMOVE:
        mirror.actors[load_u16(p)].shape = -1;
        break;
    case W3P_RECORD_STATIC: {
        const uint16_t index = load_u16(p);
        StaticObject &object = mirror.statics[index];
        object.tile_x = p[2];
        object.tile_y = p[3];
        object.shape = load_i16(p + 4);
        object.flags = p[6];
        if (index == mirror.static_count) ++mirror.static_count;
        break;
    }
    case W3P_RECORD_HUD:
        mirror.hud.health = p[0];
        mirror.hud.ammo = p[1];
        mirror.hud.keys = p[2];
        mirror.hud.weapon = p[3];
        mirror.hud.score = load_u32(p + 4);
        mirror.hud.level = p[8];
        mirror.hud.face = p[9];
        mirror.hud.lives = p[10];
        break;
    case W3P_RECORD_VIEW_WEAPON:
        mirror.view_weapon_shape = load_i16(p);
        break;
    default:
        break;
    }
}

}  // namespace

void initialize_world_mirror(
    WorldMirror &mirror, uint16_t generation_seed,
    uint16_t configured_tilemap_id) {
    clear_bytes(&mirror, sizeof(mirror));
    mirror.generation = generation_seed;
    mirror.presented_generation = generation_seed;
    mirror.configured_tilemap_id = configured_tilemap_id;
    mirror.view_weapon_shape = -1;
    for (size_t i = 0; i < W3P_MAX_ACTORS; ++i) {
        mirror.actors[i].shape = -1;
    }
    for (size_t i = 0; i < W3P_MAX_STATICS; ++i) {
        mirror.statics[i].shape = -1;
    }
}

BatchDetail validate_resource_descriptor(
    ResourceDescriptor &output, const uint8_t *bytes, size_t byte_count) {
    if (bytes == nullptr) return BatchDetail::argument;
    if (byte_count != W3P_ARGUMENT_BYTES) return BatchDetail::bounds;
    if (load_u32(bytes + W3P_ARG_MAGIC) != W3P_ARGUMENT_MAGIC ||
        bytes[W3P_ARG_SCHEMA] != W3P_SCHEMA_VERSION ||
        bytes[W3P_ARG_BYTES] != W3P_ARGUMENT_BYTES ||
        load_u16(bytes + W3P_ARG_RESERVED) != 0) {
        return BatchDetail::argument;
    }

    ResourceDescriptor candidate;
    candidate.flags = load_u16(bytes + W3P_ARG_FLAGS);
    candidate.workspace_id = load_u16(bytes + W3P_ARG_WORKSPACE);
    candidate.update_id = load_u16(bytes + W3P_ARG_UPDATE);
    candidate.tilemap_id = load_u16(bytes + W3P_ARG_TILEMAP);
    candidate.wall_base = load_u16(bytes + W3P_ARG_WALL_BASE);
    candidate.sprite_base = load_u16(bytes + W3P_ARG_SPRITE_BASE);
    candidate.hud_base = load_u16(bytes + W3P_ARG_HUD_BASE);
    candidate.generation_seed = load_u16(bytes + W3P_ARG_GENERATION_SEED);
    if (candidate.flags != W3P_ARG_FLAG_COPIED_PIXELS ||
        (candidate.flags & ~W3P_ARG_KNOWN_FLAGS) != 0 ||
        candidate.workspace_id == 0 || candidate.update_id == 0 ||
        candidate.tilemap_id == 0 ||
        candidate.workspace_id == candidate.update_id ||
        candidate.workspace_id == candidate.tilemap_id ||
        candidate.update_id == candidate.tilemap_id ||
        candidate.wall_base != W3P_DEFAULT_WALL_BASE ||
        candidate.sprite_base != W3P_DEFAULT_SPRITE_BASE ||
        candidate.hud_base != W3P_DEFAULT_HUD_BASE ||
        candidate.generation_seed == 0xFFFFu) {
        return BatchDetail::argument;
    }
    output = candidate;
    return BatchDetail::ok;
}

BatchDetail apply_update_batch(
    WorldMirror &mirror, const uint8_t *bytes, size_t byte_count) {
    BatchHeader header;
    const BatchDetail detail = validate_batch(mirror, bytes, byte_count, header);
    if (detail != BatchDetail::ok) return detail;

    if ((header.flags & W3P_BATCH_FLAG_FULL) != 0) clear_render_state(mirror);
    size_t cursor = W3P_BATCH_HEADER_BYTES;
    for (uint16_t i = 0; i < header.record_count; ++i) {
        const uint8_t type = bytes[cursor];
        const uint8_t payload_bytes = bytes[cursor + 1];
        cursor += W3P_RECORD_HEADER_BYTES;
        apply_record(mirror, type, bytes + cursor);
        cursor += payload_bytes;
    }
    mirror.generation = header.generation;
    mirror.last_batch_fingerprint = header.fingerprint;
    mirror.pending_present = 1;
    mirror.ready = 1;
    return BatchDetail::ok;
}

void mark_mirror_presented(WorldMirror &mirror) {
    if (!mirror.pending_present) return;
    mirror.presented_generation = mirror.generation;
    mirror.pending_present = 0;
}

const char *batch_detail_name(BatchDetail detail) {
    switch (detail) {
    case BatchDetail::ok: return "ok";
    case BatchDetail::argument: return "argument";
    case BatchDetail::bounds: return "bounds";
    case BatchDetail::generation: return "generation";
    case BatchDetail::duplicate: return "duplicate";
    case BatchDetail::incomplete: return "incomplete";
    case BatchDetail::order: return "order";
    case BatchDetail::record: return "record";
    }
    return "unknown";
}

}  // namespace wolf3d_production
