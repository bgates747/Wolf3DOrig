#include "wolf3d_world_mirror.h"

#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using wolf3d_production::BatchDetail;
using wolf3d_production::ResourceDescriptor;
using wolf3d_production::WorldMirror;
using wolf3d_production::apply_update_batch;
using wolf3d_production::batch_detail_name;
using wolf3d_production::initialize_world_mirror;
using wolf3d_production::mark_mirror_presented;
using wolf3d_production::validate_resource_descriptor;

namespace {

void require(bool condition, const std::string &message) {
    if (!condition) throw std::runtime_error(message);
}

void store_u16(std::vector<uint8_t> &bytes, size_t offset, uint16_t value) {
    bytes.at(offset) = static_cast<uint8_t>(value);
    bytes.at(offset + 1) = static_cast<uint8_t>(value >> 8);
}

void store_u32(std::vector<uint8_t> &bytes, size_t offset, uint32_t value) {
    store_u16(bytes, offset, static_cast<uint16_t>(value));
    store_u16(bytes, offset + 2, static_cast<uint16_t>(value >> 16));
}

void append_u16(std::vector<uint8_t> &bytes, uint16_t value) {
    bytes.push_back(static_cast<uint8_t>(value));
    bytes.push_back(static_cast<uint8_t>(value >> 8));
}

void append_u32(std::vector<uint8_t> &bytes, uint32_t value) {
    append_u16(bytes, static_cast<uint16_t>(value));
    append_u16(bytes, static_cast<uint16_t>(value >> 16));
}

struct Batch {
    std::vector<uint8_t> bytes = std::vector<uint8_t>(W3P_BATCH_HEADER_BYTES, 0);
    uint16_t records = 0;

    void record(uint8_t type, const std::vector<uint8_t> &payload) {
        require(payload.size() <= 255, "test payload too large");
        bytes.push_back(type);
        bytes.push_back(static_cast<uint8_t>(payload.size()));
        bytes.insert(bytes.end(), payload.begin(), payload.end());
        ++records;
    }

    std::vector<uint8_t> finish(uint16_t generation, uint16_t flags) {
        store_u32(bytes, W3P_BATCH_MAGIC_OFFSET, W3P_BATCH_MAGIC);
        bytes[W3P_BATCH_SCHEMA_OFFSET] = W3P_SCHEMA_VERSION;
        bytes[W3P_BATCH_HEADER_OFFSET] = W3P_BATCH_HEADER_BYTES;
        store_u16(bytes, W3P_BATCH_FLAGS_OFFSET, flags);
        store_u16(bytes, W3P_BATCH_TOTAL_OFFSET,
                  static_cast<uint16_t>(bytes.size()));
        store_u16(bytes, W3P_BATCH_RECORDS_OFFSET, records);
        store_u16(bytes, W3P_BATCH_GENERATION_OFFSET, generation);
        store_u16(bytes, W3P_BATCH_RESERVED_OFFSET, 0);
        return bytes;
    }
};

std::vector<uint8_t> level_payload(
    uint16_t tilemap, uint8_t doors, uint16_t statics) {
    std::vector<uint8_t> p;
    append_u16(p, tilemap);
    p.push_back(doors);
    append_u16(p, statics);
    p.push_back(0);
    return p;
}

std::vector<uint8_t> player_payload(int32_t x, int32_t y, uint16_t angle) {
    std::vector<uint8_t> p;
    append_u32(p, static_cast<uint32_t>(x));
    append_u32(p, static_cast<uint32_t>(y));
    append_u16(p, angle);
    return p;
}

std::vector<uint8_t> door_payload(uint8_t index, uint16_t position = 0) {
    std::vector<uint8_t> p = {
        index, static_cast<uint8_t>((10 + index) % W3P_MAP_SIZE), 20,
                              static_cast<uint8_t>(index & 1u), 0, 0};
    append_u16(p, position);
    p.push_back(121);
    return p;
}

std::vector<uint8_t> actor_payload(
    uint16_t index, int16_t shape = 50, uint8_t rotations = 8) {
    std::vector<uint8_t> p;
    append_u16(p, index);
    append_u16(p, static_cast<uint16_t>(shape));
    append_u32(p, 0x00128000u + (static_cast<uint32_t>(index) << 8));
    append_u32(p, 0x00148000u);
    append_u16(p, static_cast<uint16_t>(index % 360u));
    p.push_back(rotations);
    return p;
}

std::vector<uint8_t> static_payload(uint16_t index, int16_t shape = 16) {
    std::vector<uint8_t> p;
    append_u16(p, index);
    p.push_back(static_cast<uint8_t>(index % W3P_MAP_SIZE));
    p.push_back(static_cast<uint8_t>((index + 1) % W3P_MAP_SIZE));
    append_u16(p, static_cast<uint16_t>(shape));
    p.push_back(shape < 0 ? 0 : static_cast<uint8_t>((index & 1u) ? 2 : 0));
    return p;
}

std::vector<uint8_t> hud_payload(uint8_t health = 100, uint32_t score = 12345) {
    std::vector<uint8_t> p = {health, 8, 3, 1};
    append_u32(p, score);
    p.push_back(1);
    p.push_back(0);
    p.push_back(3);
    p.push_back(0);
    return p;
}

std::vector<uint8_t> weapon_payload(int16_t shape = 10) {
    std::vector<uint8_t> p;
    append_u16(p, static_cast<uint16_t>(shape));
    return p;
}

std::vector<uint8_t> pushwall_payload(
    uint8_t status = 0, uint8_t origin_x = 0, uint8_t origin_y = 0,
    uint8_t current_x = 0, uint8_t current_y = 0, uint8_t direction = 0,
    uint8_t position = 0, uint8_t texture = 0) {
    std::vector<uint8_t> p(W3P_PUSHWALL_BYTES, 0);
    p[W3P_PUSHWALL_STATUS] = status;
    p[W3P_PUSHWALL_ORIGIN_X] = origin_x;
    p[W3P_PUSHWALL_ORIGIN_Y] = origin_y;
    p[W3P_PUSHWALL_CURRENT_X] = current_x;
    p[W3P_PUSHWALL_CURRENT_Y] = current_y;
    p[W3P_PUSHWALL_DIRECTION] = direction;
    p[W3P_PUSHWALL_POSITION] = position;
    p[W3P_PUSHWALL_TEXTURE] = texture;
    return p;
}

std::vector<uint8_t> full_batch(
    uint16_t generation, uint8_t doors, uint16_t statics,
    uint16_t actors = 1, uint16_t tilemap = 2) {
    Batch batch;
    batch.record(W3P_RECORD_LEVEL, level_payload(tilemap, doors, statics));
    batch.record(W3P_RECORD_PLAYER,
                 player_payload(0x001D8000, 0x00398000, 0));
    batch.record(W3P_RECORD_PUSHWALL, pushwall_payload());
    for (uint8_t i = 0; i < doors; ++i) {
        batch.record(W3P_RECORD_DOOR, door_payload(i));
    }
    for (uint16_t i = 1; i <= actors; ++i) {
        batch.record(W3P_RECORD_ACTOR_SET, actor_payload(i));
    }
    for (uint16_t i = 0; i < statics; ++i) {
        batch.record(W3P_RECORD_STATIC, static_payload(i));
    }
    batch.record(W3P_RECORD_HUD, hud_payload());
    batch.record(W3P_RECORD_VIEW_WEAPON, weapon_payload());
    return batch.finish(generation, W3P_BATCH_FLAG_FULL);
}

std::vector<uint8_t> descriptor(
    uint16_t workspace = 0x7100, uint16_t update = 0x7101,
    uint16_t tilemap = 2, uint16_t seed = 0) {
    std::vector<uint8_t> bytes(W3P_ARGUMENT_BYTES, 0);
    store_u32(bytes, W3P_ARG_MAGIC, W3P_ARGUMENT_MAGIC);
    bytes[W3P_ARG_SCHEMA] = W3P_SCHEMA_VERSION;
    bytes[W3P_ARG_BYTES] = W3P_ARGUMENT_BYTES;
    store_u16(bytes, W3P_ARG_FLAGS, W3P_ARG_FLAG_COPIED_PIXELS);
    store_u16(bytes, W3P_ARG_WORKSPACE, workspace);
    store_u16(bytes, W3P_ARG_UPDATE, update);
    store_u16(bytes, W3P_ARG_TILEMAP, tilemap);
    store_u16(bytes, W3P_ARG_WALL_BASE, W3P_DEFAULT_WALL_BASE);
    store_u16(bytes, W3P_ARG_SPRITE_BASE, W3P_DEFAULT_SPRITE_BASE);
    store_u16(bytes, W3P_ARG_HUD_BASE, W3P_DEFAULT_HUD_BASE);
    store_u16(bytes, W3P_ARG_GENERATION_SEED, seed);
    return bytes;
}

void expect_preserved(
    WorldMirror &mirror, const std::vector<uint8_t> &batch,
    BatchDetail expected, const std::string &label) {
    const WorldMirror before = mirror;
    const BatchDetail actual = apply_update_batch(mirror, batch.data(), batch.size());
    require(actual == expected,
            label + ": expected " + batch_detail_name(expected) + ", got " +
                batch_detail_name(actual));
    require(std::memcmp(&before, &mirror, sizeof(mirror)) == 0,
            label + ": rejected batch mutated the mirror");
}

void test_valid_full_and_partial() {
    WorldMirror mirror;
    initialize_world_mirror(mirror, 0, 2);
    const auto full = full_batch(1, 2, 3, 2);
    require(apply_update_batch(mirror, full.data(), full.size()) == BatchDetail::ok,
            "valid full snapshot rejected");
    require(mirror.ready == 1 && mirror.generation == 1 &&
                mirror.tilemap_id == 2 && mirror.door_count == 2 &&
                mirror.static_count == 3,
            "full snapshot header state mismatch");
    require(mirror.player.x == 0x001D8000 && mirror.doors[1].texture_id == 121 &&
                mirror.actors[2].shape == 50 && mirror.statics[2].shape == 16 &&
                mirror.hud.score == 12345 && mirror.view_weapon_shape == 10,
            "full snapshot values mismatch");

    const WorldMirror applied = mirror;
    require(apply_update_batch(mirror, full.data(), full.size()) == BatchDetail::ok,
            "exact pending batch replay rejected");
    require(std::memcmp(&applied, &mirror, sizeof(mirror)) == 0,
            "exact pending replay changed mirror state");
    auto altered_replay = full;
    altered_replay.back() ^= 1;
    expect_preserved(mirror, altered_replay, BatchDetail::generation,
                     "altered pending replay");

    Batch premature;
    premature.record(W3P_RECORD_PLAYER, player_payload(1, 1, 0));
    expect_preserved(mirror, premature.finish(2, 0), BatchDetail::generation,
                     "new generation while publication pending");
    mark_mirror_presented(mirror);
    require(mirror.pending_present == 0 && mirror.presented_generation == 1,
            "publication commit did not clear pending generation");

    Batch partial;
    partial.record(W3P_RECORD_PLAYER,
                   player_payload(0x001E8000, 0x00388000, 90));
    partial.record(W3P_RECORD_DOOR, door_payload(1, 0x8000));
    std::vector<uint8_t> remove;
    append_u16(remove, 2);
    partial.record(W3P_RECORD_ACTOR_REMOVE, remove);
    partial.record(W3P_RECORD_STATIC, static_payload(2, -1));
    partial.record(W3P_RECORD_HUD, hud_payload(75, 999));
    partial.record(W3P_RECORD_VIEW_WEAPON, weapon_payload(-1));
    partial.record(W3P_RECORD_PUSHWALL,
                   pushwall_payload(1, 10, 10, 10, 10, 0, 32, 4));
    const auto update = partial.finish(2, 0);
    require(apply_update_batch(mirror, update.data(), update.size()) ==
                BatchDetail::ok,
            "valid partial update rejected");
    require(mirror.generation == 2 && mirror.player.angle == 90 &&
                mirror.doors[1].position == 0x8000 &&
                mirror.actors[2].shape == -1 && mirror.statics[2].shape == -1 &&
                mirror.hud.health == 75 && mirror.hud.score == 999 &&
                mirror.view_weapon_shape == -1 &&
                mirror.pushwall.status == 1 &&
                mirror.pushwall.position == 32,
            "partial update values mismatch");
    mark_mirror_presented(mirror);

    // Captured production failure: killing an actor appends its dropped item
    // at the old static_count.  That first free slot is a legal contiguous
    // extension, not an out-of-range update.
    Batch dropped_item;
    dropped_item.record(W3P_RECORD_STATIC, static_payload(3, 28));
    const auto drop_update = dropped_item.finish(3, 0);
    require(apply_update_batch(mirror, drop_update.data(), drop_update.size()) ==
                BatchDetail::ok,
            "dynamic dropped-item static rejected");
    require(mirror.generation == 3 && mirror.static_count == 4 &&
                mirror.statics[3].shape == 28,
            "dynamic dropped-item static did not extend mirror");
    mark_mirror_presented(mirror);

    initialize_world_mirror(mirror, 2, 7);
    const auto replacement = full_batch(3, 0, 0, 0, 7);
    require(apply_update_batch(mirror, replacement.data(), replacement.size()) ==
                BatchDetail::ok,
            "replacement full snapshot rejected");
    require(mirror.tilemap_id == 7 && mirror.door_count == 0 &&
                mirror.static_count == 0 && mirror.actors[1].shape == -1 &&
                mirror.statics[0].shape == -1,
            "full replacement did not clear old slots");
    mark_mirror_presented(mirror);
}

void test_atomic_rejections() {
    WorldMirror unready;
    initialize_world_mirror(unready, 0, 2);
    Batch partial;
    partial.record(W3P_RECORD_PLAYER, player_payload(1, 1, 0));
    expect_preserved(unready, partial.finish(1, 0), BatchDetail::incomplete,
                     "partial before full");

    WorldMirror mirror;
    initialize_world_mirror(mirror, 0, 2);
    auto valid = full_batch(1, 1, 1);
    require(apply_update_batch(mirror, valid.data(), valid.size()) == BatchDetail::ok,
            "setup full snapshot rejected");
    mark_mirror_presented(mirror);

    auto bad_magic = full_batch(2, 1, 1);
    bad_magic[0] ^= 0xFF;
    expect_preserved(mirror, bad_magic, BatchDetail::argument, "bad magic");

    auto bad_total = full_batch(2, 1, 1);
    store_u16(bad_total, W3P_BATCH_TOTAL_OFFSET,
              static_cast<uint16_t>(bad_total.size() - 1));
    expect_preserved(mirror, bad_total, BatchDetail::bounds, "bad total");

    auto stale = full_batch(1, 1, 1);
    expect_preserved(mirror, stale, BatchDetail::generation, "stale generation");

    Batch duplicate;
    duplicate.record(W3P_RECORD_DOOR, door_payload(0));
    duplicate.record(W3P_RECORD_DOOR, door_payload(0));
    expect_preserved(mirror, duplicate.finish(2, 0), BatchDetail::duplicate,
                     "duplicate door");

    Batch missing;
    missing.record(W3P_RECORD_LEVEL, level_payload(2, 1, 1));
    missing.record(W3P_RECORD_PLAYER, player_payload(1, 1, 0));
    missing.record(W3P_RECORD_HUD, hud_payload());
    missing.record(W3P_RECORD_VIEW_WEAPON, weapon_payload());
    expect_preserved(mirror, missing.finish(2, W3P_BATCH_FLAG_FULL),
                     BatchDetail::incomplete, "missing full coverage");

    Batch wrong_order;
    wrong_order.record(W3P_RECORD_PLAYER, player_payload(1, 1, 0));
    wrong_order.record(W3P_RECORD_LEVEL, level_payload(2, 0, 0));
    wrong_order.record(W3P_RECORD_HUD, hud_payload());
    wrong_order.record(W3P_RECORD_VIEW_WEAPON, weapon_payload());
    expect_preserved(mirror, wrong_order.finish(2, W3P_BATCH_FLAG_FULL),
                     BatchDetail::order, "level order");

    Batch unknown;
    unknown.record(99, {});
    expect_preserved(mirror, unknown.finish(2, 0), BatchDetail::record,
                     "unknown record");

    Batch invalid_actor;
    invalid_actor.record(W3P_RECORD_ACTOR_SET, actor_payload(0));
    expect_preserved(mirror, invalid_actor.finish(2, 0), BatchDetail::argument,
                     "actor slot zero");

    Batch static_gap;
    static_gap.record(W3P_RECORD_STATIC, static_payload(2, 16));
    expect_preserved(mirror, static_gap.finish(2, 0), BatchDetail::argument,
                     "noncontiguous dynamic static append");

    Batch rotation_overflow;
    rotation_overflow.record(
        W3P_RECORD_ACTOR_SET,
        actor_payload(1, static_cast<int16_t>(W3P_MAX_SHAPE - 6), 8));
    expect_preserved(mirror, rotation_overflow.finish(2, 0),
                     BatchDetail::argument, "actor rotation shape overflow");

    Batch bad_pushwall;
    bad_pushwall.record(W3P_RECORD_PUSHWALL,
                        pushwall_payload(1, 10, 10, 11, 10, 2, 32, 4));
    expect_preserved(mirror, bad_pushwall.finish(2, 0),
                     BatchDetail::argument, "pushwall direction mismatch");

    Batch short_record;
    short_record.record(W3P_RECORD_PLAYER, std::vector<uint8_t>(9, 0));
    expect_preserved(mirror, short_record.finish(2, 0), BatchDetail::bounds,
                     "short record");
}

void test_maximum_snapshot_and_wrap_refusal() {
    WorldMirror mirror;
    initialize_world_mirror(mirror, 0, 2);
    const auto maximum = full_batch(
        1, W3P_MAX_DOORS, W3P_MAX_STATICS, W3P_MAX_ACTORS - 1);
    require(maximum.size() == 6982, "maximum snapshot size drifted");
    require(maximum.size() <= W3P_BATCH_MAX_BYTES,
            "maximum snapshot exceeds contract bound");
    require(apply_update_batch(mirror, maximum.data(), maximum.size()) ==
                BatchDetail::ok,
            "maximum snapshot rejected");
    require(mirror.doors[63].texture_id == 121 &&
                mirror.actors[149].shape == 50 &&
                mirror.statics[399].shape == 16,
            "maximum snapshot tail slots missing");
    mark_mirror_presented(mirror);

    mirror.generation = 0xFFFF;
    Batch wrapped;
    wrapped.record(W3P_RECORD_PLAYER, player_payload(1, 1, 0));
    expect_preserved(mirror, wrapped.finish(0, 0), BatchDetail::generation,
                     "generation wrap");
}

void test_resource_descriptor() {
    ResourceDescriptor resources = {};
    const auto valid = descriptor();
    require(validate_resource_descriptor(resources, valid.data(), valid.size()) ==
                BatchDetail::ok,
            "valid resource descriptor rejected");
    require(resources.workspace_id == 0x7100 && resources.update_id == 0x7101 &&
                resources.tilemap_id == 2 && resources.generation_seed == 0,
            "resource descriptor values mismatch");

    const ResourceDescriptor accepted = resources;
    auto collision = descriptor(0x7100, 0x7100);
    require(validate_resource_descriptor(resources, collision.data(),
                                         collision.size()) ==
                BatchDetail::argument,
            "colliding resources accepted");
    require(std::memcmp(&accepted, &resources, sizeof(resources)) == 0,
            "rejected descriptor mutated accepted resources");

    auto wrong_base = descriptor();
    store_u16(wrong_base, W3P_ARG_WALL_BASE, 0x1100);
    require(validate_resource_descriptor(resources, wrong_base.data(),
                                         wrong_base.size()) ==
                BatchDetail::argument,
            "wrong asset base accepted");
    require(validate_resource_descriptor(resources, valid.data(), valid.size() - 1) ==
                BatchDetail::bounds,
            "short descriptor accepted");
}

}  // namespace

int main() {
    try {
        require(sizeof(WorldMirror) == 5448,
                "host world-mirror layout drifted from 5,448 bytes");
        test_valid_full_and_partial();
        test_atomic_rejections();
        test_maximum_snapshot_and_wrap_refusal();
        test_resource_descriptor();
        std::cout << "wolf3d production mirror: all tests passed\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << "wolf3d production mirror: " << error.what() << "\n";
        return 1;
    }
}
