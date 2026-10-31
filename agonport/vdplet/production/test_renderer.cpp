#include "wolf3d_renderer.h"
#include "renderer_fixture.h"

#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace wolf3d_production;
namespace fixture = wolf3d_renderer_fixture;

namespace {

struct ProviderState {
    uint8_t texture[fixture::kMaximumAssetBytes];
    uint16_t fail_buffer;
    uint16_t short_buffer;
    bool fail_release;
    uint32_t next_lease;
    uint32_t acquired;
    uint32_t released;
    uint32_t active;
};

void require(bool condition, const char *message) {
    if (!condition) throw std::runtime_error(message);
}

RenderDetail acquire(void *opaque, uint16_t buffer_id, AssetSpan &span) {
    ProviderState &state = *static_cast<ProviderState *>(opaque);
    if (buffer_id == state.fail_buffer || !fixture::valid_buffer(buffer_id))
        return RenderDetail::asset;
    fixture::fill_asset(buffer_id, state.texture);
    const uint32_t bytes = fixture::asset_bytes(buffer_id);
    span.bytes = state.texture;
    span.byte_count = buffer_id == state.short_buffer
        ? bytes - 1 : bytes;
    span.lease = ++state.next_lease;
    ++state.acquired;
    ++state.active;
    return RenderDetail::ok;
}

RenderDetail release(void *opaque, uint32_t lease) {
    ProviderState &state = *static_cast<ProviderState *>(opaque);
    if (lease == 0 || state.active == 0) return RenderDetail::release;
    --state.active;
    ++state.released;
    return state.fail_release ? RenderDetail::release : RenderDetail::ok;
}

WorldMirror make_world(int scenario) {
    WorldMirror world{};
    world.ready = 1;
    world.tilemap_id = fixture::kMapId;
    world.configured_tilemap_id = fixture::kMapId;
    world.door_count = 2;
    world.static_count = 3;
    world.view_weapon_shape = -1;
    for (uint16_t i = 0; i < W3P_MAX_ACTORS; ++i) world.actors[i].shape = -1;
    for (uint16_t i = 0; i < W3P_MAX_STATICS; ++i) world.statics[i].shape = -1;
    const fixture::SceneSpec spec = fixture::scene(scenario);
    world.player = {spec.player_x, spec.player_y, spec.player_angle};
    world.view_weapon_shape = spec.view_weapon_shape;
    world.hud = {spec.health, spec.ammo, spec.keys, spec.weapon, spec.score,
                 spec.level, spec.face, spec.lives};
    for (uint8_t i = 0; i < 2; ++i) {
        world.doors[i].position = spec.doors[i].position;
        world.doors[i].tile_x = spec.doors[i].x;
        world.doors[i].tile_y = spec.doors[i].y;
        world.doors[i].vertical = spec.doors[i].vertical;
        world.doors[i].texture_id = spec.doors[i].texture;
    }
    for (const fixture::ActorSpec &actor : spec.actors) {
        world.actors[actor.slot] = {
            actor.x, actor.y, actor.shape, actor.facing, actor.rotations};
    }
    for (uint16_t i = 0; i < 3; ++i) {
        world.statics[i] = {spec.statics[i].shape, spec.statics[i].x,
                            spec.statics[i].y, 0};
    }
    return world;
}

RenderResources resources(uint8_t *map, uint8_t *workspace,
                          ProviderState &provider) {
    return {map, fixture::kMapBytes, workspace, W3P_WORKSPACE_BYTES,
            fixture::kWallBase, fixture::kSpriteBase, fixture::kHudBase,
            {&provider, acquire, release}};
}

void write_all(std::ofstream &stream, const uint8_t *bytes, size_t count) {
    stream.write(reinterpret_cast<const char *>(bytes), count);
    require(static_cast<bool>(stream), "cannot write renderer evidence");
}

void exercise_errors(uint8_t *map) {
    std::vector<uint8_t> workspace(W3P_WORKSPACE_BYTES);
    ProviderState provider{};
    WorldMirror world = make_world(0);
    RenderResources supplied = resources(map, workspace.data(), provider);

    WorldMirror unready = world;
    unready.ready = 0;
    require(render_world(unready, supplied) == RenderDetail::argument,
            "unready mirror accepted");
    RenderResources short_map = supplied;
    short_map.tilemap_bytes = fixture::kMapBytes - 1;
    require(render_world(world, short_map) == RenderDetail::bounds,
            "short map accepted");
    RenderResources short_workspace = supplied;
    short_workspace.workspace_bytes = W3P_WORKSPACE_BYTES - 1;
    require(render_world(world, short_workspace) == RenderDetail::bounds,
            "short workspace accepted");

    provider = {};
    provider.fail_buffer = fixture::kWallBase + 1;
    require(render_world(world, supplied) == RenderDetail::asset,
            "missing wall asset accepted");
    require(provider.active == 0 && provider.acquired == provider.released,
            "missing asset leaked a prior lease");

    provider = {};
    provider.short_buffer = fixture::kWallBase + 1;
    require(render_world(world, supplied) == RenderDetail::bounds,
            "short wall asset accepted");
    require(provider.active == 0 && provider.acquired == provider.released,
            "short asset lease not released");

    provider = {};
    provider.fail_release = true;
    require(render_world(world, supplied) == RenderDetail::release,
            "release failure not propagated");
    require(provider.active == 0 && provider.released == 1,
            "release failure path retained a lease");

    provider = {};
    provider.fail_buffer = fixture::kSpriteBase + 32;
    require(render_world(world, supplied) == RenderDetail::asset,
            "missing view weapon accepted");
    require(provider.active == 0 && provider.acquired == provider.released,
            "missing view weapon leaked prior leases");

    provider = {};
    provider.fail_buffer = fixture::kHudBase + 98;
    require(render_world(world, supplied) == RenderDetail::asset,
            "missing HUD status bar accepted");
    require(provider.active == 0 && provider.acquired == provider.released,
            "missing HUD asset leaked prior leases");

    provider = {};
    provider.short_buffer = fixture::kHudBase + 98;
    require(render_world(world, supplied) == RenderDetail::bounds,
            "short HUD status bar accepted");
    require(provider.active == 0 && provider.acquired == provider.released,
            "short HUD asset lease not released");

    std::vector<uint8_t> bad_map(map, map + fixture::kMapBytes);
    bad_map[4 * 64 + 7] = 0xbf;
    provider = {};
    supplied = resources(bad_map.data(), workspace.data(), provider);
    require(render_world(world, supplied) == RenderDetail::world,
            "out-of-world door reference accepted");
    require(provider.active == 0, "world validation leaked a lease");
}

void exercise_capacity(uint8_t *map) {
    WorldMirror world = make_world(0);
    world.static_count = W3P_MAX_STATICS;
    for (uint16_t index = 1; index < W3P_MAX_ACTORS; ++index) {
        world.actors[index] = {
            fixture::tile_center(6), fixture::tile_center(4), 28, 0, 0};
    }
    for (uint16_t index = 0; index < W3P_MAX_STATICS; ++index) {
        world.statics[index] = {30, 7, 4, 0};
    }
    std::vector<uint8_t> guarded(W3P_WORKSPACE_BYTES + 32, 0x5a);
    ProviderState provider{};
    RenderResources supplied = resources(map, guarded.data() + 16, provider);
    RenderStats stats{};
    require(render_world(world, supplied, &stats) == RenderDetail::ok,
            "maximum visible sprite scene failed");
    require(stats.visible_sprites == W3P_MAX_ACTORS - 1 + W3P_MAX_STATICS,
            "maximum visible sprite count truncated");
    require(stats.sprite_acquires == stats.visible_sprites &&
                provider.active == 0 && provider.acquired == provider.released,
            "maximum visible sprite scene leaked a lease");
    for (int i = 0; i < 16; ++i) {
        require(guarded[i] == 0x5a, "maximum scene workspace underflow");
        require(guarded[W3P_WORKSPACE_BYTES + 16 + i] == 0x5a,
                "maximum scene workspace overflow");
    }
}

}  // namespace

int main(int argc, char **argv) {
    if (argc != 3) {
        std::cerr << "usage: test_renderer FRAME GEOMETRY\n";
        return 2;
    }
    try {
        std::vector<uint8_t> map(fixture::kMapBytes);
        fixture::fill_map(map.data());
        exercise_errors(map.data());
        exercise_capacity(map.data());
        std::ofstream frame_output(argv[1], std::ios::binary);
        std::ofstream geometry_output(argv[2], std::ios::binary);
        require(frame_output && geometry_output, "cannot open renderer output");
        for (int scenario = 0; scenario < fixture::kScenarioCount; ++scenario) {
            std::vector<uint8_t> guarded(W3P_WORKSPACE_BYTES + 32, 0xa5);
            uint8_t *workspace = guarded.data() + 16;
            ProviderState provider{};
            WorldMirror world = make_world(scenario);
            RenderResources supplied = resources(map.data(), workspace, provider);
            RenderStats stats{};
            require(render_world(world, supplied, &stats) == RenderDetail::ok,
                    "valid scene render failed");
            require(provider.active == 0 && provider.acquired == provider.released,
                    "valid render leaked an asset lease");
            require(stats.wall_acquires >= 2 && stats.sprite_acquires != 0 &&
                    stats.visible_sprites == stats.sprite_acquires,
                    "renderer stats do not cover exercised scene");
            require(stats.weapon_acquires ==
                        (world.view_weapon_shape < 0 ? 0 : 1) &&
                    stats.hud_acquires != 0 && stats.hud_acquires <= 19,
                    "weapon/HUD acquisition accounting mismatch");
            for (int i = 0; i < 16; ++i) {
                require(guarded[i] == 0xa5, "workspace underflow");
                require(guarded[W3P_WORKSPACE_BYTES + 16 + i] == 0xa5,
                        "workspace overflow");
            }
            write_all(frame_output, workspace, W3P_FRAME_BYTES);
            write_all(geometry_output,
                      workspace + W3P_WALL_HEIGHT_OFFSET,
                      W3P_SPRITE_ARENA_OFFSET - W3P_WALL_HEIGHT_OFFSET);
        }
        std::cout << "production renderer: parity fixture and error matrix passed\n";
    } catch (const std::exception &error) {
        std::cerr << "production renderer: " << error.what() << "\n";
        return 1;
    }
    return 0;
}
