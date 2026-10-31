#include "vdplet_host_shim.h"
#include "wolf3d_scene_contract.h"

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

extern "C" int32_t vdplet_entry(const vdplet_host_v1 *, const vdplet_request_v1 *);

namespace {

struct Lease {
    std::uint16_t buffer;
    std::uint16_t access;
};

struct Context {
    std::unordered_map<std::uint16_t, std::vector<std::uint8_t>> buffers;
    std::unordered_map<std::uint32_t, Lease> leases;
    std::vector<std::uint8_t> hidden = std::vector<std::uint8_t>(W3V_FRAME_BYTES);
    vdplet_surface_v1 surface{};
    std::uint32_t next_lease = 1;
    unsigned acquire_calls = 0;
    unsigned release_calls = 0;
    unsigned surface_calls = 0;
    unsigned pixel_calls = 0;
    unsigned max_leases = 0;
    unsigned fail_acquire_call = 0;
    unsigned fail_release_call = 0;
    int32_t acquire_error = VDPL_E_BUFFER;
    int32_t release_error = VDPL_E_HANDLE;
    int32_t surface_error = VDPL_OK;
    int32_t pixel_error = VDPL_OK;
};

unsigned checks = 0;

std::vector<std::uint8_t> read_file(const char *path) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) throw std::runtime_error(std::string("cannot read ") + path);
    return std::vector<std::uint8_t>(std::istreambuf_iterator<char>(stream), {});
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

void reset_observations(Context& context) {
    if (!context.leases.empty())
        throw std::runtime_error("test attempted reset with live leases");
    context.acquire_calls = 0;
    context.release_calls = 0;
    context.surface_calls = 0;
    context.pixel_calls = 0;
    context.max_leases = 0;
    context.fail_acquire_call = 0;
    context.fail_release_call = 0;
    context.acquire_error = VDPL_E_BUFFER;
    context.release_error = VDPL_E_HANDLE;
    context.surface_error = VDPL_OK;
    context.pixel_error = VDPL_OK;
}

int32_t acquire(void *opaque, std::uint16_t id, std::uint16_t access,
                std::uint32_t offset, std::uint32_t count, vdplet_view_v1 *view) {
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
    if (context.surface_error) return context.surface_error;
    if (!surface || surface->struct_bytes != sizeof(*surface))
        return VDPL_E_ARGUMENT;
    *surface = context.surface;
    return VDPL_OK;
}

int32_t pixels_write(void *opaque, const vdplet_pixels_v1 *pixels) {
    auto& context = *static_cast<Context *>(opaque);
    ++context.pixel_calls;
    if (context.pixel_error) return context.pixel_error;
    if (!pixels || pixels->struct_bytes != sizeof(*pixels) ||
        pixels->format != VDPL_PIXELS_RGB222 || !pixels->source ||
        pixels->x != 0 || pixels->y != 0 ||
        pixels->width != W3V_SCREEN_WIDTH || pixels->height != W3V_SCREEN_HEIGHT ||
        pixels->stride != W3V_SCREEN_WIDTH || pixels->source_bytes < W3V_FRAME_BYTES)
        return VDPL_E_ARGUMENT;
    std::copy(pixels->source, pixels->source + W3V_FRAME_BYTES,
              context.hidden.begin());
    return VDPL_OK;
}

vdplet_request_v1 request(std::uint16_t operation, std::uint16_t entry = 0,
                          std::uint16_t arguments = 0,
                          std::uint32_t bytes = 0) {
    return {sizeof(vdplet_request_v1), operation, entry, arguments, 0, bytes};
}

void initialize_api(vdplet_host_v1_3& api, Context& context) {
    api = {};
    auto& base = api.base.base.base;
    base.struct_bytes = sizeof(api);
    base.abi_major = VDPL_ABI_MAJOR;
    base.abi_minor = VDPL_ABI_MINOR_MEDIA;
    base.capabilities = VDPL_CAP_BUFFERS | VDPL_CAP_PIXELS;
    base.context = &context;
    base.buffer_acquire = acquire;
    base.buffer_release = release;
    api.surface_info = surface_info;
    api.pixels_write = pixels_write;
}

void expect_no_leases(const std::string& label, const Context& context) {
    expect_true(label + " leaked leases", context.leases.empty());
}

void store_u16(std::vector<std::uint8_t>& bytes, std::size_t offset,
               std::uint16_t value) {
    bytes[offset] = (std::uint8_t)value;
    bytes[offset + 1] = (std::uint8_t)(value >> 8);
}

void store_u32(std::vector<std::uint8_t>& bytes, std::size_t offset,
               std::uint32_t value) {
    store_u16(bytes, offset, (std::uint16_t)value);
    store_u16(bytes, offset + 2, (std::uint16_t)(value >> 16));
}

}  // namespace

int main(int argc, char **argv) {
    if (argc != 5) {
        std::cerr << "usage: error_runner MAP TEXTURES CONFIG WORKSPACE\n";
        return 2;
    }
    try {
        Context context;
        context.buffers[0x7101] = read_file(argv[1]);
        context.buffers[0x7102] = read_file(argv[2]);
        const auto valid_config = read_file(argv[3]);
        context.buffers[0x7103] = valid_config;
        context.buffers[0x7100] = read_file(argv[4]);
        context.surface = {
            sizeof(context.surface), W3V_SCREEN_WIDTH, W3V_SCREEN_HEIGHT,
            VDPL_NATIVE_RGB222, 3, 64,
            VDPL_SURFACE_PHYSICAL | VDPL_SURFACE_DOUBLE_BUFFERED
        };

        vdplet_host_v1_3 api{};
        initialize_api(api, context);
        auto& host = api.base.base.base;
        auto init = request(VDPL_INIT);
        auto fini = request(VDPL_FINI);
        auto render = request(VDPL_RUN, W3V_ENTRY_RENDER);
        auto config = request(VDPL_RUN, W3V_ENTRY_CONFIG, 0x7103,
                              W3V_CONFIG_BYTES);

        expect("null host", vdplet_entry(nullptr, &init), VDPL_E_ABI);
        expect("null request", vdplet_entry(&host, nullptr), VDPL_E_ABI);
        auto bad_api = api;
        bad_api.base.base.base.abi_major = VDPL_ABI_MAJOR + 1;
        expect("wrong ABI major", vdplet_entry(&bad_api.base.base.base, &init),
               VDPL_E_ABI);
        bad_api = api;
        bad_api.base.base.base.capabilities = VDPL_CAP_PIXELS;
        expect("missing buffer capability",
               vdplet_entry(&bad_api.base.base.base, &init), VDPL_E_ABI);

        expect("INIT", vdplet_entry(&host, &init), VDPL_OK);
        expect("render before CONFIG", vdplet_entry(&host, &render), VDPL_E_INIT);
        auto unsupported_operation = request(0x7fff);
        expect("unsupported operation", vdplet_entry(&host, &unsupported_operation),
               VDPL_E_UNSUPPORTED);
        auto unsupported_entry = request(VDPL_RUN, 0x7fff);
        expect("unsupported entry", vdplet_entry(&host, &unsupported_entry),
               VDPL_E_UNSUPPORTED);

        auto short_config = request(VDPL_RUN, W3V_ENTRY_CONFIG, 0x7103,
                                    W3V_CONFIG_BYTES - 1);
        expect("short CONFIG declaration", vdplet_entry(&host, &short_config),
               VDPL_E_ARGUMENT);
        expect_true("short CONFIG acquired a buffer", context.acquire_calls == 0);
        context.buffers.erase(0x7103);
        expect("missing CONFIG buffer", vdplet_entry(&host, &config), VDPL_E_BUFFER);
        expect_no_leases("missing CONFIG", context);
        context.buffers[0x7103] = valid_config;

        struct InvalidConfig {
            const char *name;
            std::size_t offset;
            std::uint32_t value;
            bool wide;
        };
        const InvalidConfig invalid[] = {
            {"magic", 0, 0, true},
            {"workspace zero", 4, 0, false},
            {"map zero", 6, 0, false},
            {"texture zero", 8, 0, false},
            {"duplicate workspace/map", 6, 0x7100, false},
            {"angle negative", 10, 0xffff, false},
            {"angle 360", 10, 360, false},
            {"player x below map", 12, 0xffff, true},
            {"player x above map", 12, 63u << 16, true},
            {"player y below map", 16, 0xffff, true},
            {"player y above map", 16, 63u << 16, true},
            {"static x zero", 20, 0, false},
            {"static x above map", 20, 63, false},
            {"static y zero", 21, 0, false},
            {"static y above map", 21, 63, false},
        };
        for (const auto& item : invalid) {
            auto bytes = valid_config;
            if (item.offset >= 20) bytes[item.offset] = (std::uint8_t)item.value;
            else if (item.wide) store_u32(bytes, item.offset, item.value);
            else store_u16(bytes, item.offset, (std::uint16_t)item.value);
            context.buffers[0x7103] = std::move(bytes);
            reset_observations(context);
            expect(std::string("invalid CONFIG ") + item.name,
                   vdplet_entry(&host, &config), VDPL_E_ARGUMENT);
            expect_no_leases(std::string("invalid CONFIG ") + item.name, context);
        }

        context.buffers[0x7103] = valid_config;
        reset_observations(context);
        expect("valid CONFIG", vdplet_entry(&host, &config), VDPL_OK);
        expect_no_leases("valid CONFIG", context);
        context.buffers.erase(0x7103);  // State must be an owned copy.

        bad_api = api;
        bad_api.base.base.base.capabilities = VDPL_CAP_BUFFERS;
        expect("missing pixel capability",
               vdplet_entry(&bad_api.base.base.base, &render), VDPL_E_ABI);
        bad_api = api;
        bad_api.base.base.base.abi_minor = VDPL_ABI_MINOR_MEDIA - 1;
        expect("old media ABI", vdplet_entry(&bad_api.base.base.base, &render),
               VDPL_E_ABI);
        bad_api = api;
        bad_api.surface_info = nullptr;
        expect("missing surface service",
               vdplet_entry(&bad_api.base.base.base, &render), VDPL_E_ABI);
        bad_api = api;
        bad_api.pixels_write = nullptr;
        expect("missing pixel service",
               vdplet_entry(&bad_api.base.base.base, &render), VDPL_E_ABI);

        reset_observations(context);
        context.surface_error = VDPL_E_BUSY;
        expect("surface service error", vdplet_entry(&host, &render), VDPL_E_BUSY);
        expect_no_leases("surface service error", context);
        context.surface_error = VDPL_OK;

        const auto valid_surface = context.surface;
        context.surface.width = W3V_SCREEN_WIDTH - 1;
        expect("wrong surface width", vdplet_entry(&host, &render), VDPL_E_FORMAT);
        context.surface = valid_surface;
        context.surface.native_format = 0xffff;
        expect("wrong surface format", vdplet_entry(&host, &render), VDPL_E_FORMAT);
        context.surface = valid_surface;
        context.surface.flags = VDPL_SURFACE_PHYSICAL;
        expect("single-buffered surface", vdplet_entry(&host, &render), VDPL_E_FORMAT);
        context.surface = valid_surface;
        expect_no_leases("invalid surfaces", context);

        for (unsigned fail = 1; fail <= 3; ++fail) {
            reset_observations(context);
            context.fail_acquire_call = fail;
            context.acquire_error = fail == 1 ? VDPL_E_BUSY
                                  : fail == 2 ? VDPL_E_BUFFER : VDPL_E_LIMIT;
            expect("acquire failure " + std::to_string(fail),
                   vdplet_entry(&host, &render), context.acquire_error);
            expect_no_leases("acquire failure " + std::to_string(fail), context);
            expect_true("acquire failure cleanup count",
                        context.release_calls == fail - 1);
        }

        reset_observations(context);
        context.pixel_error = VDPL_E_FORMAT;
        expect("pixel service error", vdplet_entry(&host, &render), VDPL_E_FORMAT);
        expect_no_leases("pixel service error", context);
        expect_true("pixel error did not release all leases",
                    context.release_calls == 3);

        for (unsigned fail = 1; fail <= 3; ++fail) {
            reset_observations(context);
            context.fail_release_call = fail;
            expect("release failure " + std::to_string(fail),
                   vdplet_entry(&host, &render), VDPL_E_HANDLE);
            expect_no_leases("release failure " + std::to_string(fail), context);
            expect_true("release failure stopped later cleanup",
                        context.release_calls == 3);
        }

        reset_observations(context);
        expect("successful render", vdplet_entry(&host, &render), VDPL_OK);
        expect_no_leases("successful render", context);
        expect_true("successful render service counts",
                    context.surface_calls == 1 && context.pixel_calls == 1 &&
                    context.acquire_calls == 3 && context.release_calls == 3 &&
                    context.max_leases == 3);

        auto invalid_after_valid = valid_config;
        store_u32(invalid_after_valid, 0, 0);
        context.buffers[0x7103] = invalid_after_valid;
        reset_observations(context);
        expect("invalid reconfigure", vdplet_entry(&host, &config), VDPL_E_ARGUMENT);
        expect_no_leases("invalid reconfigure", context);
        reset_observations(context);
        expect("state preserved after invalid reconfigure",
               vdplet_entry(&host, &render), VDPL_OK);
        expect_no_leases("preserved render", context);

        expect("FINI", vdplet_entry(&host, &fini), VDPL_OK);
        expect("render after FINI", vdplet_entry(&host, &render), VDPL_E_INIT);
        expect("repeated FINI", vdplet_entry(&host, &fini), VDPL_OK);

        std::cout << "error_runner: pass checks=" << checks
                  << " invalid_configs=" << (sizeof(invalid) / sizeof(invalid[0]))
                  << " max_leases=3\n";
    } catch (const std::exception& error) {
        std::cerr << "error_runner: " << error.what() << "\n";
        return 1;
    }
    return 0;
}
