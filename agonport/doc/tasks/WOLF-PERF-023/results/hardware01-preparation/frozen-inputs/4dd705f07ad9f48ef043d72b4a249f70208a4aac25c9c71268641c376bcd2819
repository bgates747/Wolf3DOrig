#include "../qualification/vdplet_host_shim.h"
#include "renderer_fixture.h"
#include "wolf3d_production_contract.h"
#include "wolf3d_renderer.h"

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

extern "C" int32_t vdplet_entry(
    const vdplet_host_v1 *, const vdplet_request_v1 *);

namespace fixture = wolf3d_renderer_fixture;
namespace {

constexpr uint16_t kWorkspaceId = 0x7100;
constexpr uint16_t kUpdateId = 0x7101;
constexpr uint16_t kArgumentId = 0x7102;

struct Lease {
    uint16_t buffer;
    uint16_t access;
};

struct Context {
    std::unordered_map<uint16_t, std::vector<uint8_t>> buffers;
    std::unordered_map<uint32_t, Lease> leases;
    std::vector<uint8_t> hidden = std::vector<uint8_t>(W3P_FRAME_BYTES, 0x2a);
    std::vector<uint8_t> native_hidden =
        std::vector<uint8_t>(W3P_FRAME_BYTES, 0x80);
    vdplet_surface_v1 surface = {
        sizeof(vdplet_surface_v1), W3P_SCREEN_WIDTH, W3P_SCREEN_HEIGHT,
        VDPL_NATIVE_RGB222, VDPL_PIXELS_RGB222, 64,
        VDPL_SURFACE_PHYSICAL | VDPL_SURFACE_DOUBLE_BUFFERED};
    uint32_t next_lease = 1;
    uint32_t acquire_calls = 0;
    uint32_t release_calls = 0;
    uint32_t surface_calls = 0;
    uint32_t pixel_calls = 0;
    uint32_t max_leases = 0;
    int32_t pixel_error = VDPL_OK;
    int32_t color_error_operation = 0;
    int32_t color_fail_row = -1;
    uint32_t color_begin_calls = 0;
    uint32_t color_row_calls = 0;
    uint32_t color_end_calls = 0;
    uint32_t color_lease = 0;
    bool color_active = false;
    std::set<uint16_t> acquired_buffers;
};

struct Batch {
    std::vector<uint8_t> bytes = std::vector<uint8_t>(W3P_BATCH_HEADER_BYTES, 0);
    uint16_t records = 0;

    void record(uint8_t type, const std::vector<uint8_t> &payload) {
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
        return bytes;
    }

    static void store_u16(std::vector<uint8_t> &target, size_t offset,
                          uint16_t value) {
        target[offset] = static_cast<uint8_t>(value);
        target[offset + 1] = static_cast<uint8_t>(value >> 8);
    }

    static void store_u32(std::vector<uint8_t> &target, size_t offset,
                          uint32_t value) {
        store_u16(target, offset, static_cast<uint16_t>(value));
        store_u16(target, offset + 2, static_cast<uint16_t>(value >> 16));
    }
};

void require(bool condition, const std::string &message) {
    if (!condition) throw std::runtime_error(message);
}

void expect(const std::string &label, int32_t actual, int32_t expected) {
    require(actual == expected, label + " returned " + std::to_string(actual) +
                                ", expected " + std::to_string(expected));
}

void append_u16(std::vector<uint8_t> &target, uint16_t value) {
    target.push_back(static_cast<uint8_t>(value));
    target.push_back(static_cast<uint8_t>(value >> 8));
}

void append_u32(std::vector<uint8_t> &target, uint32_t value) {
    append_u16(target, static_cast<uint16_t>(value));
    append_u16(target, static_cast<uint16_t>(value >> 16));
}

int32_t acquire(void *opaque, uint16_t id, uint16_t access,
                uint32_t offset, uint32_t count, vdplet_view_v1 *view) {
    Context &context = *static_cast<Context *>(opaque);
    ++context.acquire_calls;
    auto found = context.buffers.find(id);
    if (view == nullptr || found == context.buffers.end() ||
        (access != VDPL_READ && access != VDPL_WRITE)) return VDPL_E_BUFFER;
    if (offset > found->second.size()) return VDPL_E_BOUNDS;
    if (count == VDPL_WHOLE_BUFFER)
        count = static_cast<uint32_t>(found->second.size() - offset);
    if (count > found->second.size() - offset) return VDPL_E_BOUNDS;
    if (context.leases.size() >= 4) return VDPL_E_LIMIT;
    for (const auto &active : context.leases) {
        if (active.second.buffer == id &&
            (active.second.access == VDPL_WRITE || access == VDPL_WRITE))
            return VDPL_E_BUSY;
    }
    const uint32_t lease = context.next_lease++;
    context.leases.emplace(lease, Lease{id, access});
    context.acquired_buffers.insert(id);
    context.max_leases = std::max(
        context.max_leases, static_cast<uint32_t>(context.leases.size()));
    *view = {sizeof(*view), lease, found->second.data() + offset, count, access};
    return VDPL_OK;
}

int32_t release(void *opaque, uint32_t lease) {
    Context &context = *static_cast<Context *>(opaque);
    ++context.release_calls;
    return context.leases.erase(lease) == 1 ? VDPL_OK : VDPL_E_HANDLE;
}

[[maybe_unused]] int32_t surface_info(
    void *opaque, vdplet_surface_v1 *surface) {
    Context &context = *static_cast<Context *>(opaque);
    ++context.surface_calls;
    if (surface == nullptr || surface->struct_bytes != sizeof(*surface))
        return VDPL_E_ARGUMENT;
    *surface = context.surface;
    return VDPL_OK;
}

[[maybe_unused]] int32_t pixels_write(
    void *opaque, const vdplet_pixels_v1 *pixels) {
    Context &context = *static_cast<Context *>(opaque);
    ++context.pixel_calls;
    if (context.pixel_error != VDPL_OK) return context.pixel_error;
    if (pixels == nullptr || pixels->struct_bytes != sizeof(*pixels) ||
        pixels->format != VDPL_PIXELS_RGB222 || pixels->source == nullptr ||
        pixels->x != 0 || pixels->y != 0 ||
        pixels->width != W3P_SCREEN_WIDTH ||
        pixels->height != W3P_SCREEN_HEIGHT ||
        pixels->stride != W3P_SCREEN_WIDTH ||
        pixels->source_bytes < W3P_FRAME_BYTES) return VDPL_E_ARGUMENT;
    for (uint32_t i = 0; i < W3P_FRAME_BYTES; ++i)
        if (pixels->source[i] > 63) return VDPL_E_FORMAT;
    std::copy(pixels->source, pixels->source + W3P_FRAME_BYTES,
              context.hidden.begin());
    return VDPL_OK;
}

int32_t color_frame(void *opaque, uint32_t operation,
                    vdplet_color_frame_v1 *frame) {
    Context &context = *static_cast<Context *>(opaque);
    if (frame == nullptr || frame->struct_bytes != sizeof(*frame))
        return VDPL_E_ARGUMENT;
    if (context.color_error_operation == static_cast<int32_t>(operation))
        return VDPL_E_FORMAT;
    if (operation == VDPL_COLOR_FRAME_BEGIN) {
        ++context.color_begin_calls;
        if (context.color_active || frame->x < 0 || frame->y < 0 ||
            frame->width == 0 || frame->height == 0 ||
            static_cast<uint32_t>(frame->x) + frame->width > W3P_SCREEN_WIDTH ||
            static_cast<uint32_t>(frame->y) + frame->height > W3P_SCREEN_HEIGHT)
            return VDPL_E_ARGUMENT;
        context.color_active = true;
        context.color_lease = context.next_lease++;
        frame->lease = context.color_lease;
        return VDPL_OK;
    }
    if (!context.color_active || frame->lease != context.color_lease)
        return VDPL_E_HANDLE;
    if (operation == VDPL_COLOR_FRAME_ROW) {
        ++context.color_row_calls;
        if (frame->row >= frame->height) return VDPL_E_BOUNDS;
        if (frame->row == static_cast<uint32_t>(context.color_fail_row))
            return VDPL_E_FORMAT;
        frame->native_format = VDPL_NATIVE_RGB222;
        frame->data = context.native_hidden.data() +
            (static_cast<uint32_t>(frame->y) + frame->row) * W3P_SCREEN_WIDTH;
        frame->row_bytes = W3P_SCREEN_WIDTH;
        frame->x_bias = static_cast<uint32_t>(frame->x);
        frame->pixel_xor = 2;
        frame->color_mask = 0x3f;
        frame->preserve_mask = 0xc0;
        return VDPL_OK;
    }
    if (operation == VDPL_COLOR_FRAME_END) {
        ++context.color_end_calls;
        context.color_active = false;
        for (uint32_t y = 0; y < W3P_SCREEN_HEIGHT; ++y) {
            for (uint32_t x = 0; x < W3P_SCREEN_WIDTH; ++x) {
                const uint32_t native = y * W3P_SCREEN_WIDTH + (x ^ 2u);
                context.hidden[y * W3P_SCREEN_WIDTH + x] =
                    context.native_hidden[native] & 0x3fu;
            }
        }
        return VDPL_OK;
    }
    return VDPL_E_ARGUMENT;
}

std::vector<std::pair<uint16_t, uint16_t>> fizzle_order() {
    std::vector<std::pair<uint16_t, uint16_t>> order;
    uint32_t state = 1;
    do {
        const uint16_t y = static_cast<uint16_t>(
            ((state & 0xffu) - 1u) & 0xffu);
        const uint16_t x = static_cast<uint16_t>((state >> 8) & 0x1ffu);
        const bool low_bit = (state & 1u) != 0;
        state >>= 1;
        if (low_bit) state ^= 0x12000u;
        if (x < W3P_VIEW_WIDTH && y < W3P_VIEW_HEIGHT)
            order.emplace_back(x, y);
    } while (state != 1u);
    return order;
}

std::vector<uint8_t> expected_fizzle(
    const std::vector<uint8_t> &base,
    const std::vector<std::pair<uint16_t, uint16_t>> &order,
    uint32_t target) {
    std::vector<uint8_t> expected = base;
    for (uint32_t index = 0; index < target; ++index) {
        const auto [x, y] = order[index];
        expected[(W3P_VIEW_Y + y) * W3P_SCREEN_WIDTH + W3P_VIEW_X + x] =
            W3P_FIZZLE_RED;
    }
    return expected;
}

vdplet_request_v1 request(uint16_t operation, uint16_t entry = 0,
                          uint16_t arguments = 0, uint32_t bytes = 0) {
    return {sizeof(vdplet_request_v1), operation, entry, arguments, 0, bytes};
}

std::vector<uint8_t> descriptor() {
    std::vector<uint8_t> bytes(W3P_ARGUMENT_BYTES, 0);
    Batch::store_u32(bytes, W3P_ARG_MAGIC, W3P_ARGUMENT_MAGIC);
    bytes[W3P_ARG_SCHEMA] = W3P_SCHEMA_VERSION;
    bytes[W3P_ARG_BYTES] = W3P_ARGUMENT_BYTES;
    Batch::store_u16(bytes, W3P_ARG_FLAGS, W3P_ARG_FLAG_DIRECT_ROWS);
    Batch::store_u16(bytes, W3P_ARG_WORKSPACE, kWorkspaceId);
    Batch::store_u16(bytes, W3P_ARG_UPDATE, kUpdateId);
    Batch::store_u16(bytes, W3P_ARG_TILEMAP, fixture::kMapId);
    Batch::store_u16(bytes, W3P_ARG_WALL_BASE, fixture::kWallBase);
    Batch::store_u16(bytes, W3P_ARG_SPRITE_BASE, fixture::kSpriteBase);
    Batch::store_u16(bytes, W3P_ARG_HUD_BASE, fixture::kHudBase);
    return bytes;
}

std::vector<uint8_t> hud_payload(const fixture::SceneSpec &spec,
                                 uint32_t score_override) {
    std::vector<uint8_t> payload = {
        spec.health, spec.ammo, spec.keys, spec.weapon};
    append_u32(payload, score_override);
    payload.push_back(spec.level);
    payload.push_back(spec.face);
    payload.push_back(spec.lives);
    payload.push_back(spec.palette_shift);
    return payload;
}

std::vector<uint8_t> full_batch() {
    const fixture::SceneSpec spec = fixture::scene(0);
    Batch batch;
    std::vector<uint8_t> level;
    append_u16(level, fixture::kMapId);
    level.push_back(2);
    append_u16(level, 3);
    level.push_back(0);
    batch.record(W3P_RECORD_LEVEL, level);
    std::vector<uint8_t> player;
    append_u32(player, static_cast<uint32_t>(spec.player_x));
    append_u32(player, static_cast<uint32_t>(spec.player_y));
    append_u16(player, spec.player_angle);
    batch.record(W3P_RECORD_PLAYER, player);
    batch.record(W3P_RECORD_PUSHWALL,
                 std::vector<uint8_t>(W3P_PUSHWALL_BYTES, 0));
    for (uint8_t index = 0; index < 2; ++index) {
        const fixture::DoorSpec &door = spec.doors[index];
        std::vector<uint8_t> payload = {
            index, door.x, door.y, door.vertical, 0, 0};
        append_u16(payload, door.position);
        payload.push_back(door.texture);
        batch.record(W3P_RECORD_DOOR, payload);
    }
    for (const fixture::ActorSpec &actor : spec.actors) {
        std::vector<uint8_t> payload;
        append_u16(payload, actor.slot);
        append_u16(payload, static_cast<uint16_t>(actor.shape));
        append_u32(payload, static_cast<uint32_t>(actor.x));
        append_u32(payload, static_cast<uint32_t>(actor.y));
        append_u16(payload, actor.facing);
        payload.push_back(actor.rotations);
        batch.record(W3P_RECORD_ACTOR_SET, payload);
    }
    for (uint16_t index = 0; index < 3; ++index) {
        const fixture::StaticSpec &object = spec.statics[index];
        std::vector<uint8_t> payload;
        append_u16(payload, index);
        payload.push_back(object.x);
        payload.push_back(object.y);
        append_u16(payload, static_cast<uint16_t>(object.shape));
        payload.push_back(0);
        batch.record(W3P_RECORD_STATIC, payload);
    }
    batch.record(W3P_RECORD_HUD, hud_payload(spec, spec.score));
    std::vector<uint8_t> weapon;
    append_u16(weapon, static_cast<uint16_t>(spec.view_weapon_shape));
    batch.record(W3P_RECORD_VIEW_WEAPON, weapon);
    return batch.finish(1, W3P_BATCH_FLAG_FULL);
}

std::vector<uint8_t> hud_batch(uint16_t generation, uint32_t score,
                               uint8_t face = 0,
                               uint8_t palette_shift = 0) {
    Batch batch;
    fixture::SceneSpec spec = fixture::scene(0);
    spec.face = face;
    spec.palette_shift = palette_shift;
    batch.record(W3P_RECORD_HUD, hud_payload(spec, score));
    return batch.finish(generation, 0);
}

std::vector<uint8_t> dropped_item_batch(uint16_t generation) {
    Batch batch;
    std::vector<uint8_t> dropped_item;
    append_u16(dropped_item, 3);  // full snapshot declared slots 0..2
    dropped_item.push_back(23);
    dropped_item.push_back(47);
    append_u16(dropped_item, 28);
    dropped_item.push_back(2);
    batch.record(W3P_RECORD_STATIC, dropped_item);
    return batch.finish(generation, 0);
}

void install_assets(Context &context) {
    std::vector<uint8_t> map(fixture::kMapBytes);
    fixture::fill_map(map.data());
    context.buffers[fixture::kMapId] = std::move(map);
    context.buffers[kWorkspaceId] =
        std::vector<uint8_t>(W3P_DIRECT_WORKSPACE_BYTES);
    context.buffers[kArgumentId] = descriptor();
    for (uint16_t id : {uint16_t(1), uint16_t(2), uint16_t(3),
                        uint16_t(4), uint16_t(122)}) {
        const uint16_t buffer = fixture::kWallBase + id;
        context.buffers[buffer].resize(fixture::asset_bytes(buffer));
        fixture::fill_asset(buffer, context.buffers[buffer].data());
    }
    for (uint16_t shape = 0; shape < 64; ++shape) {
        const uint16_t buffer = fixture::kSpriteBase + shape;
        context.buffers[buffer].resize(fixture::asset_bytes(buffer));
        fixture::fill_asset(buffer, context.buffers[buffer].data());
    }
    context.buffers[fixture::kHudBase + 98].resize(320 * 40);
    fixture::fill_asset(fixture::kHudBase + 98,
                        context.buffers[fixture::kHudBase + 98].data());
    for (uint16_t chunk = 103; chunk <= 143; ++chunk) {
        const uint16_t buffer = fixture::kHudBase + chunk;
        context.buffers[buffer].resize(fixture::asset_bytes(buffer));
        fixture::fill_asset(buffer, context.buffers[buffer].data());
    }
}

void write_file(const std::filesystem::path &path,
                const std::vector<uint8_t> &bytes) {
    std::ofstream stream(path, std::ios::binary);
    require(static_cast<bool>(stream), "cannot open module output");
    stream.write(reinterpret_cast<const char *>(bytes.data()), bytes.size());
    require(static_cast<bool>(stream), "cannot write module output");
}

void export_target_fixture(const std::filesystem::path &directory,
                           const Context &context,
                           const std::vector<uint8_t> &full_update,
                           const std::vector<uint8_t> &retry_update,
                           const std::vector<uint8_t> &full_frame,
                           const std::vector<uint8_t> &retry_frame) {
    std::filesystem::create_directories(directory);
    write_file(directory / "argument.bin", context.buffers.at(kArgumentId));
    write_file(directory / "update-full.bin", full_update);
    write_file(directory / "update-retry.bin", retry_update);
    write_file(directory / "workspace.bin",
               std::vector<uint8_t>(W3P_DIRECT_WORKSPACE_BYTES));
    write_file(directory / "tilemap.bin", context.buffers.at(fixture::kMapId));
    write_file(directory / "expected-full.bin", full_frame);
    write_file(directory / "expected-retry.bin", retry_frame);

    std::ofstream manifest(directory / "assets.txt");
    require(static_cast<bool>(manifest), "cannot open target asset manifest");
    for (uint16_t id : context.acquired_buffers) {
        if (id == kArgumentId || id == kUpdateId || id == kWorkspaceId ||
            id == fixture::kMapId) continue;
        const auto found = context.buffers.find(id);
        if (found == context.buffers.end()) continue;
        std::ostringstream name;
        name << "buffer-" << std::hex << std::setfill('0')
             << std::setw(4) << id << ".bin";
        write_file(directory / name.str(), found->second);
        manifest << "0x" << std::hex << std::setfill('0') << std::setw(4)
                 << id << std::dec << " " << found->second.size() << " "
                 << name.str() << "\n";
    }
    require(static_cast<bool>(manifest), "cannot write target asset manifest");
}

void require_clean(const Context &context, const std::string &label) {
    require(context.leases.empty(), label + " leaked leases");
}

}  // namespace

int main(int argc, char **argv) {
    if (argc != 2 && argc != 3) {
        std::cerr << "usage: test_module FRAME [TARGET_FIXTURE_DIR]\n";
        return 2;
    }
    try {
        Context context;
        install_assets(context);
        vdplet_host_v1_6 api{};
        vdplet_host_v1 &host = api.base.base.base.base.base.base;
        host.struct_bytes = sizeof(api);
        host.abi_major = VDPL_ABI_MAJOR;
        host.abi_minor = VDPL_ABI_MINOR_COLOR_FRAME;
        host.capabilities = VDPL_CAP_BUFFERS | VDPL_CAP_COLOR_FRAME;
        host.context = &context;
        host.buffer_acquire = acquire;
        host.buffer_release = release;
        api.color_frame = color_frame;

        auto init = request(VDPL_INIT);
        auto fini = request(VDPL_FINI);
        auto config = request(
            VDPL_RUN, W3P_ENTRY_CONFIG, kArgumentId, W3P_ARGUMENT_BYTES);
        auto apply = request(
            VDPL_RUN, W3P_ENTRY_APPLY_AND_RENDER,
            kArgumentId, W3P_ARGUMENT_BYTES);
        auto reset = request(
            VDPL_RUN, W3P_ENTRY_RESET, kArgumentId, W3P_ARGUMENT_BYTES);

        expect("null host", vdplet_entry(nullptr, &init), VDPL_E_ABI);
        expect("INIT", vdplet_entry(&host, &init), VDPL_OK);
        const std::vector<uint8_t> initial_batch = full_batch();
        context.buffers[kUpdateId] = initial_batch;
        expect("apply before CONFIG", vdplet_entry(&host, &apply), VDPL_E_INIT);
        expect("CONFIG", vdplet_entry(&host, &config), VDPL_OK);
        require_clean(context, "CONFIG");
        expect("full APPLY", vdplet_entry(&host, &apply), VDPL_OK);
        require_clean(context, "full APPLY");
        require(context.max_leases == 3, "production transaction exceeded 3 leases");
        require(context.color_begin_calls == 1 &&
                context.color_row_calls == W3P_SCREEN_HEIGHT &&
                context.color_end_calls == 1,
                "direct frame did not acquire exactly one complete row set");
        const auto &direct_workspace = context.buffers.at(kWorkspaceId);
        require(std::all_of(
                    direct_workspace.begin(),
                    direct_workspace.begin() + W3P_DIRECT_ROW_POINTER_BYTES,
                    [](uint8_t value) { return value == 0; }),
                "direct row pointers survived END");
        require(std::all_of(
                    context.native_hidden.begin(), context.native_hidden.end(),
                    [](uint8_t value) { return (value & 0xc0u) == 0x80u; }),
                "direct rendering damaged native sync bits");
        write_file(argv[1], context.hidden);

        const std::vector<uint8_t> accepted_frame = context.hidden;
        auto malformed = hud_batch(2, 222222);
        malformed[0] = 0;
        context.buffers[kUpdateId] = malformed;
        expect("malformed batch", vdplet_entry(&host, &apply), VDPL_E_ARGUMENT);
        require(context.hidden == accepted_frame, "malformed batch changed pixels");
        require_clean(context, "malformed batch");

        const auto retry_batch = hud_batch(2, 222222, 3, 6);
        context.buffers[kUpdateId] = retry_batch;
        context.color_fail_row = 117;
        expect("publication failure", vdplet_entry(&host, &apply), VDPL_E_FORMAT);
        context.color_fail_row = -1;
        require(context.color_end_calls == 2,
                "failed row acquisition did not close the frame transaction");
        require(std::all_of(
                    direct_workspace.begin(),
                    direct_workspace.begin() + W3P_DIRECT_ROW_POINTER_BYTES,
                    [](uint8_t value) { return value == 0; }),
                "failed row acquisition retained a native pointer");
        require_clean(context, "publication failure");

        context.buffers[kUpdateId] = hud_batch(2, 333333, 3, 6);
        expect("altered retry", vdplet_entry(&host, &apply), VDPL_E_ARGUMENT);
        require_clean(context, "altered retry");
        context.buffers[kUpdateId] = retry_batch;
        expect("exact retry", vdplet_entry(&host, &apply), VDPL_OK);
        require(context.hidden != accepted_frame, "exact retry did not publish");
        const std::vector<uint8_t> retry_frame = context.hidden;
        require_clean(context, "exact retry");

        context.buffers[kUpdateId] = dropped_item_batch(3);
        expect("dynamic dropped-item static", vdplet_entry(&host, &apply),
               VDPL_OK);
        require_clean(context, "dynamic dropped-item static");

        context.buffers[kUpdateId] = hud_batch(4, 444444);
        auto status_bar = std::move(context.buffers[fixture::kHudBase + 98]);
        context.buffers.erase(fixture::kHudBase + 98);
        expect("missing render asset", vdplet_entry(&host, &apply), VDPL_E_BUFFER);
        require_clean(context, "missing render asset");
        context.buffers[fixture::kHudBase + 98] = std::move(status_bar);
        expect("asset recovery exact retry", vdplet_entry(&host, &apply), VDPL_OK);
        require_clean(context, "asset recovery");

        if (argc == 3) {
            export_target_fixture(argv[2], context, initial_batch, retry_batch,
                                  accepted_frame, retry_frame);
        }

        auto fizzle = request(
            VDPL_RUN, W3P_ENTRY_FIZZLE_BEGIN,
            kArgumentId, W3P_ARGUMENT_BYTES);
        auto fizzle_step = request(
            VDPL_RUN, W3P_ENTRY_FIZZLE_STEP,
            kArgumentId, W3P_ARGUMENT_BYTES);
        const std::vector<uint8_t> fizzle_base = context.hidden;
        const std::vector<uint8_t> native_base = context.native_hidden;
        std::vector<uint8_t> surface0 = native_base;
        std::vector<uint8_t> surface1 = native_base;
        const auto order = fizzle_order();
        require(order.size() == W3P_VIEW_WIDTH * W3P_VIEW_HEIGHT,
                "fizzle LFSR did not cover the viewport exactly once");
        expect("FIZZLE_BEGIN", vdplet_entry(&host, &fizzle), VDPL_OK);
        require(context.hidden == fizzle_base,
                "FIZZLE_BEGIN changed the published frame");
        expect("overlapping FIZZLE_BEGIN", vdplet_entry(&host, &fizzle),
               VDPL_E_BUSY);

        context.native_hidden = surface0;
        context.color_fail_row = 17;
        expect("failed first FIZZLE_STEP",
               vdplet_entry(&host, &fizzle_step), VDPL_E_FORMAT);
        context.color_fail_row = -1;
        expect("retried first FIZZLE_STEP",
               vdplet_entry(&host, &fizzle_step), VDPL_OK);
        surface0 = context.native_hidden;
        uint32_t target = W3P_VIEW_WIDTH * W3P_VIEW_HEIGHT /
            W3P_FIZZLE_DISPLAY_FRAMES;
        require(context.hidden == expected_fizzle(fizzle_base, order, target),
                "first fizzle slice or exact retry differed from oracle");

        for (uint32_t step = 1; step < W3P_FIZZLE_DISPLAY_FRAMES; ++step) {
            context.native_hidden = (step & 1u) != 0 ? surface1 : surface0;
            expect("FIZZLE_STEP", vdplet_entry(&host, &fizzle_step), VDPL_OK);
            if ((step & 1u) != 0) surface1 = context.native_hidden;
            else surface0 = context.native_hidden;
            target = W3P_VIEW_WIDTH * W3P_VIEW_HEIGHT * (step + 1u) /
                W3P_FIZZLE_DISPLAY_FRAMES;
            require(context.hidden == expected_fizzle(fizzle_base, order, target),
                    "cumulative fizzle slice differed from oracle");
        }

        // The displayed sixtieth slice leaves the other physical surface one
        // slice behind. One final no-swap STEP mirrors full red into it.
        context.native_hidden = surface0;
        expect("FIZZLE_STEP mirror sync",
               vdplet_entry(&host, &fizzle_step), VDPL_OK);
        surface0 = context.native_hidden;
        const auto all_red = expected_fizzle(
            fizzle_base, order, W3P_VIEW_WIDTH * W3P_VIEW_HEIGHT);
        require(context.hidden == all_red,
                "fizzle mirror sync did not finish the hidden surface");
        context.native_hidden = surface1;
        vdplet_color_frame_v1 rebuild = {
            sizeof(rebuild), 0, 0, 0, W3P_SCREEN_WIDTH, W3P_SCREEN_HEIGHT,
            0, 0, nullptr, 0, 0, 0, 0, 0};
        expect("fizzle verification BEGIN",
               color_frame(&context, VDPL_COLOR_FRAME_BEGIN, &rebuild), VDPL_OK);
        expect("fizzle verification END",
               color_frame(&context, VDPL_COLOR_FRAME_END, &rebuild), VDPL_OK);
        require(context.hidden == all_red,
                "displayed fizzle surface was not fully red");
        expect("FIZZLE_STEP after completion",
               vdplet_entry(&host, &fizzle_step), VDPL_E_INIT);
        expect("RESET", vdplet_entry(&host, &reset), VDPL_OK);
        expect("apply after RESET", vdplet_entry(&host, &apply), VDPL_E_INIT);
        expect("FINI", vdplet_entry(&host, &fini), VDPL_OK);
        expect("repeated FINI", vdplet_entry(&host, &fini), VDPL_OK);
        require_clean(context, "FINI");

        Context copied;
        install_assets(copied);
        copied.buffers[kWorkspaceId].assign(W3P_WORKSPACE_BYTES, 0);
        copied.buffers[kArgumentId] = descriptor();
        Batch::store_u16(copied.buffers[kArgumentId], W3P_ARG_FLAGS,
                         W3P_ARG_FLAG_COPIED_PIXELS);
        copied.buffers[kUpdateId] = initial_batch;
        vdplet_host_v1_6 copied_api{};
        vdplet_host_v1 &copied_host =
            copied_api.base.base.base.base.base.base;
        vdplet_host_v1_3 &copied_media = copied_api.base.base.base;
        copied_host.struct_bytes = sizeof(copied_api);
        copied_host.abi_major = VDPL_ABI_MAJOR;
        copied_host.abi_minor = VDPL_ABI_MINOR_COLOR_FRAME;
        copied_host.capabilities =
            VDPL_CAP_BUFFERS | VDPL_CAP_PIXELS | VDPL_CAP_COLOR_FRAME;
        copied_host.context = &copied;
        copied_host.buffer_acquire = acquire;
        copied_host.buffer_release = release;
        copied_media.surface_info = surface_info;
        copied_media.pixels_write = pixels_write;
        copied_api.color_frame = color_frame;
        expect("copied INIT", vdplet_entry(&copied_host, &init), VDPL_OK);
        expect("copied CONFIG", vdplet_entry(&copied_host, &config), VDPL_OK);
        expect("copied APPLY", vdplet_entry(&copied_host, &apply), VDPL_OK);
        require(copied.hidden == accepted_frame,
                "named copied fallback differs from direct rows");
        require(copied.pixel_calls == 1 && copied.color_begin_calls == 0,
                "copied fallback used the wrong publication service");
        expect("copied FINI", vdplet_entry(&copied_host, &fini), VDPL_OK);
        require_clean(copied, "copied fallback");
        std::cout << "production module: lifecycle, retry, recovery passed"
                  << " direct/copy parity max_leases="
                  << context.max_leases << "\n";
    } catch (const std::exception &error) {
        std::cerr << "production module: " << error.what() << "\n";
        return 1;
    }
    return 0;
}
