#include "vdplet_host_shim.h"
#include "wolf3d_scene_rows_contract.h"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

extern "C" int32_t vdplet_entry(const vdplet_host_v1 *,
                                 const vdplet_request_v1 *);

namespace {

constexpr std::uint16_t kWorkspaceId = 0x7100;
constexpr std::uint16_t kMapId = 0x7101;
constexpr std::uint16_t kTextureId = 0x7102;
constexpr std::uint16_t kConfigId = 0x7103;
constexpr std::uint32_t kGuardBefore = 0x53a7c91du;
constexpr std::uint32_t kGuardAfter = 0xe46b82f0u;
constexpr std::uint32_t kRowWords = W3V_SCREEN_WIDTH / 4u;

struct Lease {
    std::uint16_t buffer;
    std::uint16_t access;
};

struct RowBlock {
    std::array<std::uint32_t, kRowWords + 2u> words{};
};

bool operator==(const RowBlock& left, const RowBlock& right) {
    return left.words == right.words;
}

struct Context {
    std::unordered_map<std::uint16_t, std::vector<std::uint8_t>> buffers;
    std::unordered_map<std::uint32_t, Lease> leases;
    std::array<RowBlock, W3V_SCREEN_HEIGHT> rows{};
    std::array<RowBlock, W3V_SCREEN_HEIGHT> at_end{};
    std::uint32_t next_lease = 1;
    std::uint32_t frame_lease = 0;
    unsigned acquire_calls = 0;
    unsigned release_calls = 0;
    unsigned begin_calls = 0;
    unsigned row_calls = 0;
    unsigned end_calls = 0;
    unsigned surface_calls = 0;
    unsigned pixel_calls = 0;
    unsigned max_leases = 0;
    unsigned fail_acquire_call = 0;
    unsigned fail_release_call = 0;
    int fail_row = -1;
    int malformed_row = -1;
    int32_t acquire_error = VDPL_E_BUFFER;
    int32_t release_error = VDPL_E_HANDLE;
    int32_t begin_error = VDPL_OK;
    int32_t row_error = VDPL_E_BOUNDS;
    int32_t end_error = VDPL_OK;
    bool snapshot_valid = false;
};

unsigned checks = 0;

std::vector<std::uint8_t> read_file(const char *path) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) throw std::runtime_error(std::string("cannot read ") + path);
    return std::vector<std::uint8_t>(std::istreambuf_iterator<char>(stream), {});
}

void write_file(const char *path, const std::uint8_t *data, std::size_t bytes) {
    std::ofstream stream(path, std::ios::binary);
    if (!stream) throw std::runtime_error(std::string("cannot write ") + path);
    stream.write(reinterpret_cast<const char *>(data), bytes);
}

void expect(const std::string& label, int32_t actual, int32_t expected) {
    ++checks;
    if (actual != expected) {
        throw std::runtime_error(label + ": got " + std::to_string(actual) +
                                 ", expected " + std::to_string(expected));
    }
}

void expect_true(const std::string& label, bool condition) {
    ++checks;
    if (!condition) throw std::runtime_error(label);
}

std::uint32_t storage_index(std::uint32_t logical_row) {
    return (logical_row * 73u) % W3V_SCREEN_HEIGHT;
}

std::uint8_t *row_data(Context& context, std::uint32_t logical_row) {
    auto& block = context.rows[storage_index(logical_row)];
    return reinterpret_cast<std::uint8_t *>(block.words.data() + 1);
}

const std::uint8_t *row_data(const Context& context, std::uint32_t logical_row) {
    const auto& block = context.rows[storage_index(logical_row)];
    return reinterpret_cast<const std::uint8_t *>(block.words.data() + 1);
}

std::uint8_t seeded_byte(std::uint32_t logical_row, std::uint32_t physical) {
    return (std::uint8_t)((((logical_row * 3u + physical) & 3u) << 6) | 0x15u);
}

void seed_rows(Context& context) {
    for (std::uint32_t logical = 0; logical < W3V_SCREEN_HEIGHT; ++logical) {
        auto& block = context.rows[storage_index(logical)];
        block.words.front() = kGuardBefore ^ logical;
        block.words.back() = kGuardAfter ^ logical;
        std::uint8_t *data = row_data(context, logical);
        for (std::uint32_t physical = 0; physical < W3V_SCREEN_WIDTH; ++physical)
            data[physical] = seeded_byte(logical, physical);
    }
    context.snapshot_valid = false;
}

void clear_descriptor_output(vdplet_color_frame_v1 *descriptor) {
    if (!descriptor) return;
    descriptor->data = nullptr;
    descriptor->row_bytes = 0;
}

int32_t acquire(void *opaque, std::uint16_t id, std::uint16_t access,
                std::uint32_t offset, std::uint32_t count,
                vdplet_view_v1 *view) {
    auto& context = *static_cast<Context *>(opaque);
    ++context.acquire_calls;
    if (context.fail_acquire_call == context.acquire_calls)
        return context.acquire_error;
    auto found = context.buffers.find(id);
    if (!view || found == context.buffers.end() ||
        (access != VDPL_READ && access != VDPL_WRITE)) return VDPL_E_BUFFER;
    if (offset > found->second.size()) return VDPL_E_BOUNDS;
    if (count == VDPL_WHOLE_BUFFER) count = found->second.size() - offset;
    if (count > found->second.size() - offset) return VDPL_E_BOUNDS;
    if (context.leases.size() >= 4) return VDPL_E_LIMIT;
    for (const auto& active : context.leases) {
        if (active.second.buffer == id &&
            (active.second.access == VDPL_WRITE || access == VDPL_WRITE))
            return VDPL_E_BUSY;
    }
    std::uint32_t lease = context.next_lease++;
    context.leases.emplace(lease, Lease{id, access});
    context.max_leases = std::max(context.max_leases,
                                  (unsigned)context.leases.size());
    *view = {sizeof(*view), lease, found->second.data() + offset, count, access};
    return VDPL_OK;
}

int32_t release(void *opaque, std::uint32_t lease) {
    auto& context = *static_cast<Context *>(opaque);
    ++context.release_calls;
    auto found = context.leases.find(lease);
    if (found == context.leases.end()) return VDPL_E_HANDLE;
    context.leases.erase(found);
    if (context.fail_release_call == context.release_calls)
        return context.release_error;
    return VDPL_OK;
}

int32_t surface_info(void *opaque, vdplet_surface_v1 *surface) {
    auto& context = *static_cast<Context *>(opaque);
    ++context.surface_calls;
    if (!surface || surface->struct_bytes != sizeof(*surface))
        return VDPL_E_ARGUMENT;
    *surface = {sizeof(*surface), W3V_SCREEN_WIDTH, W3V_SCREEN_HEIGHT,
                VDPL_NATIVE_RGB222, 3, 64,
                VDPL_SURFACE_PHYSICAL | VDPL_SURFACE_DOUBLE_BUFFERED};
    return VDPL_OK;
}

int32_t pixels_write(void *opaque, const vdplet_pixels_v1 *) {
    auto& context = *static_cast<Context *>(opaque);
    ++context.pixel_calls;
    return VDPL_E_UNSUPPORTED;
}

int32_t color_frame(void *opaque, std::uint32_t operation,
                    vdplet_color_frame_v1 *descriptor) {
    auto& context = *static_cast<Context *>(opaque);
    if (!descriptor || descriptor->struct_bytes != sizeof(*descriptor))
        return VDPL_E_ARGUMENT;
    if (operation == VDPL_COLOR_FRAME_BEGIN) {
        ++context.begin_calls;
        clear_descriptor_output(descriptor);
        if (context.begin_error) return context.begin_error;
        if (context.frame_lease) return VDPL_E_BUSY;
        if (descriptor->lease || descriptor->x != 0 || descriptor->y != 0 ||
            descriptor->width != W3V_SCREEN_WIDTH ||
            descriptor->height != W3V_SCREEN_HEIGHT) return VDPL_E_ARGUMENT;
        seed_rows(context);
        context.frame_lease = context.next_lease++;
        descriptor->lease = context.frame_lease;
        return VDPL_OK;
    }
    if (operation == VDPL_COLOR_FRAME_ROW) {
        ++context.row_calls;
        clear_descriptor_output(descriptor);
        if (!context.frame_lease || descriptor->lease != context.frame_lease)
            return VDPL_E_HANDLE;
        if (descriptor->row >= W3V_SCREEN_HEIGHT) return VDPL_E_BOUNDS;
        if ((int)descriptor->row == context.fail_row) return context.row_error;
        descriptor->native_format = VDPL_NATIVE_RGB222;
        descriptor->data = row_data(context, descriptor->row);
        descriptor->row_bytes = W3V_SCREEN_WIDTH;
        descriptor->x_bias = 0;
        descriptor->pixel_xor = 2;
        descriptor->color_mask = 0x3f;
        descriptor->preserve_mask = 0xc0;
        if ((int)descriptor->row == context.malformed_row)
            descriptor->x_bias = 1;
        return VDPL_OK;
    }
    if (operation == VDPL_COLOR_FRAME_END) {
        ++context.end_calls;
        if (!context.frame_lease || descriptor->lease != context.frame_lease) {
            clear_descriptor_output(descriptor);
            descriptor->lease = 0;
            return VDPL_E_HANDLE;
        }
        context.at_end = context.rows;
        context.snapshot_valid = true;
        context.frame_lease = 0;
        clear_descriptor_output(descriptor);
        descriptor->lease = 0;
        return context.end_error;
    }
    clear_descriptor_output(descriptor);
    return VDPL_E_ARGUMENT;
}

vdplet_request_v1 request(std::uint16_t operation, std::uint16_t entry = 0,
                          std::uint16_t arguments = 0,
                          std::uint32_t bytes = 0) {
    return {sizeof(vdplet_request_v1), operation, entry, arguments, 0, bytes};
}

vdplet_host_v1& base(vdplet_host_v1_6& api) {
    return api.base.base.base.base.base.base;
}

vdplet_host_v1_3& media(vdplet_host_v1_6& api) {
    return api.base.base.base;
}

void initialize_api(vdplet_host_v1_6& api, Context& context) {
    api = {};
    auto& host = base(api);
    host.struct_bytes = sizeof(api);
    host.abi_major = VDPL_ABI_MAJOR;
    host.abi_minor = VDPL_ABI_MINOR_COLOR_FRAME;
    host.capabilities = VDPL_CAP_BUFFERS | VDPL_CAP_PIXELS |
                        VDPL_CAP_COLOR_FRAME;
    host.context = &context;
    host.buffer_acquire = acquire;
    host.buffer_release = release;
    media(api).surface_info = surface_info;
    media(api).pixels_write = pixels_write;
    api.color_frame = color_frame;
}

void reset_observations(Context& context) {
    if (!context.leases.empty() || context.frame_lease)
        throw std::runtime_error("reset attempted with live resource");
    context.acquire_calls = 0;
    context.release_calls = 0;
    context.begin_calls = 0;
    context.row_calls = 0;
    context.end_calls = 0;
    context.surface_calls = 0;
    context.pixel_calls = 0;
    context.max_leases = 0;
    context.fail_acquire_call = 0;
    context.fail_release_call = 0;
    context.fail_row = -1;
    context.malformed_row = -1;
    context.acquire_error = VDPL_E_BUFFER;
    context.release_error = VDPL_E_HANDLE;
    context.begin_error = VDPL_OK;
    context.row_error = VDPL_E_BOUNDS;
    context.end_error = VDPL_OK;
    context.snapshot_valid = false;
}

void expect_clean(const std::string& label, const Context& context) {
    expect_true(label + " leaked ordinary lease", context.leases.empty());
    expect_true(label + " leaked frame transaction", context.frame_lease == 0);
    const auto& workspace = context.buffers.at(kWorkspaceId);
    const auto *rows = reinterpret_cast<const uintptr_t *>(workspace.data());
    for (std::uint32_t row = 0; row < W3V_SCREEN_HEIGHT; ++row) {
        if (rows[row])
            throw std::runtime_error(label + " retained row pointer " +
                                     std::to_string(row));
    }
    ++checks;
}

std::vector<std::uint8_t> decoded_frame(const Context& context) {
    std::vector<std::uint8_t> result(W3V_FRAME_BYTES);
    for (std::uint32_t y = 0; y < W3V_SCREEN_HEIGHT; ++y) {
        const std::uint8_t *data = row_data(context, y);
        for (std::uint32_t x = 0; x < W3V_SCREEN_WIDTH; ++x)
            result[y * W3V_SCREEN_WIDTH + x] = data[x ^ 2u] & 0x3fu;
    }
    return result;
}

void expect_native_preserved(const Context& context) {
    expect_true("END did not snapshot rows", context.snapshot_valid);
    expect_true("row data changed after END", context.rows == context.at_end);
    for (std::uint32_t logical = 0; logical < W3V_SCREEN_HEIGHT; ++logical) {
        const auto& block = context.rows[storage_index(logical)];
        expect_true("row leading guard changed",
                    block.words.front() == (kGuardBefore ^ logical));
        expect_true("row trailing guard changed",
                    block.words.back() == (kGuardAfter ^ logical));
        const std::uint8_t *data = row_data(context, logical);
        for (std::uint32_t physical = 0; physical < W3V_SCREEN_WIDTH; ++physical) {
            if ((data[physical] & 0xc0u) !=
                (seeded_byte(logical, physical) & 0xc0u)) {
                throw std::runtime_error("native sync bits changed");
            }
        }
    }
    ++checks;
}

void store_u32(std::vector<std::uint8_t>& bytes, std::size_t offset,
               std::uint32_t value) {
    bytes[offset] = (std::uint8_t)value;
    bytes[offset + 1] = (std::uint8_t)(value >> 8);
    bytes[offset + 2] = (std::uint8_t)(value >> 16);
    bytes[offset + 3] = (std::uint8_t)(value >> 24);
}

}  // namespace

int main(int argc, char **argv) {
    if (argc != 7) {
        std::cerr << "usage: rows_runner MAP TEXTURES CONFIG WORKSPACE FRAME GEOMETRY\n";
        return 2;
    }
    try {
        Context context;
        context.buffers[kMapId] = read_file(argv[1]);
        context.buffers[kTextureId] = read_file(argv[2]);
        const auto valid_config = read_file(argv[3]);
        context.buffers[kConfigId] = valid_config;
        context.buffers[kWorkspaceId] = read_file(argv[4]);

        vdplet_host_v1_6 api{};
        initialize_api(api, context);
        auto init = request(VDPL_INIT);
        auto fini = request(VDPL_FINI);
        auto config = request(VDPL_RUN, W3V_ENTRY_CONFIG, kConfigId,
                              W3V_CONFIG_BYTES);
        auto render = request(VDPL_RUN, W3V_ENTRY_RENDER);

        expect("INIT", vdplet_entry(&base(api), &init), VDPL_OK);
        expect("CONFIG", vdplet_entry(&base(api), &config), VDPL_OK);
        reset_observations(context);
        expect("direct render", vdplet_entry(&base(api), &render), VDPL_OK);
        expect_clean("direct render", context);
        expect_true("direct service counts",
                    context.acquire_calls == 3 && context.release_calls == 3 &&
                    context.max_leases == 3 && context.begin_calls == 1 &&
                    context.row_calls == W3V_SCREEN_HEIGHT &&
                    context.end_calls == 1 && context.surface_calls == 0 &&
                    context.pixel_calls == 0);
        expect_native_preserved(context);

        const auto frame = decoded_frame(context);
        write_file(argv[5], frame.data(), frame.size());
        const auto& workspace = context.buffers.at(kWorkspaceId);
        write_file(argv[6], workspace.data() + W3V_DIRECT_WALL_HEIGHT_OFFSET,
                   W3V_DIRECT_SPRITE_ARENA_OFFSET -
                   W3V_DIRECT_WALL_HEIGHT_OFFSET);

        vdplet_host_v1_6 bad_api = api;
        base(bad_api).capabilities &= ~VDPL_CAP_COLOR_FRAME;
        expect("missing colour capability", vdplet_entry(&base(bad_api), &render),
               VDPL_E_ABI);
        bad_api = api;
        base(bad_api).abi_minor = VDPL_ABI_MINOR_COLOR_FRAME - 1;
        expect("old colour ABI", vdplet_entry(&base(bad_api), &render),
               VDPL_E_ABI);
        bad_api = api;
        base(bad_api).struct_bytes =
            (std::uint32_t)offsetof(vdplet_host_v1_6, color_frame);
        expect("truncated colour table", vdplet_entry(&base(bad_api), &render),
               VDPL_E_ABI);
        bad_api = api;
        bad_api.color_frame = nullptr;
        expect("missing colour callback", vdplet_entry(&base(bad_api), &render),
               VDPL_E_ABI);

        reset_observations(context);
        context.begin_error = VDPL_E_BUSY;
        expect("BEGIN failure", vdplet_entry(&base(api), &render), VDPL_E_BUSY);
        expect_true("BEGIN failure called END", context.end_calls == 0);
        expect_clean("BEGIN failure", context);

        for (int failed_row : {0, 119, 239}) {
            reset_observations(context);
            context.fail_row = failed_row;
            expect("ROW failure " + std::to_string(failed_row),
                   vdplet_entry(&base(api), &render), VDPL_E_BOUNDS);
            expect_true("ROW failure did not END", context.end_calls == 1);
            expect_clean("ROW failure", context);
        }

        reset_observations(context);
        context.malformed_row = 41;
        expect("malformed ROW descriptor", vdplet_entry(&base(api), &render),
               VDPL_E_FORMAT);
        expect_true("malformed ROW did not END", context.end_calls == 1);
        expect_clean("malformed ROW", context);

        reset_observations(context);
        context.end_error = VDPL_E_HANDLE;
        expect("END failure", vdplet_entry(&base(api), &render), VDPL_E_HANDLE);
        expect_clean("END failure", context);
        expect_native_preserved(context);

        for (unsigned fail = 1; fail <= 3; ++fail) {
            reset_observations(context);
            context.fail_acquire_call = fail;
            context.acquire_error = fail == 1 ? VDPL_E_BUSY
                                  : fail == 2 ? VDPL_E_BUFFER : VDPL_E_LIMIT;
            expect("acquire failure " + std::to_string(fail),
                   vdplet_entry(&base(api), &render), context.acquire_error);
            expect_true("acquire failure began a frame", context.begin_calls == 0);
            expect_clean("acquire failure", context);
        }

        for (unsigned fail = 1; fail <= 3; ++fail) {
            reset_observations(context);
            context.fail_release_call = fail;
            expect("release failure " + std::to_string(fail),
                   vdplet_entry(&base(api), &render), VDPL_E_HANDLE);
            expect_clean("release failure", context);
        }

        auto invalid_config = valid_config;
        store_u32(invalid_config, 0, 0);
        context.buffers[kConfigId] = invalid_config;
        reset_observations(context);
        expect("invalid reconfigure", vdplet_entry(&base(api), &config),
               VDPL_E_ARGUMENT);
        expect_clean("invalid reconfigure", context);
        reset_observations(context);
        expect("preserved render", vdplet_entry(&base(api), &render), VDPL_OK);
        expect_clean("preserved render", context);

        expect("FINI", vdplet_entry(&base(api), &fini), VDPL_OK);
        expect("render after FINI", vdplet_entry(&base(api), &render),
               VDPL_E_INIT);
        expect("repeated FINI", vdplet_entry(&base(api), &fini), VDPL_OK);

        std::cout << "rows_runner: pass checks=" << checks
                  << " workspace_target=" << W3V_DIRECT_TARGET_WORKSPACE_BYTES
                  << " workspace_host=" << W3V_DIRECT_WORKSPACE_BYTES
                  << " rows=" << W3V_SCREEN_HEIGHT << "\n";
    } catch (const std::exception& error) {
        std::cerr << "rows_runner: " << error.what() << "\n";
        return 1;
    }
    return 0;
}
