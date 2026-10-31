#include "vdplet_host_shim.h"
#include "wolf3d_scene_contract.h"

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
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
    std::uint32_t next_lease = 1;
    unsigned max_leases = 0;
    unsigned surface_calls = 0;
    unsigned pixel_calls = 0;
};

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

int32_t acquire(void *opaque, std::uint16_t id, std::uint16_t access,
                std::uint32_t offset, std::uint32_t count, vdplet_view_v1 *view) {
    auto& context = *static_cast<Context *>(opaque);
    auto found = context.buffers.find(id);
    if (!view || found == context.buffers.end() ||
        (access != VDPL_READ && access != VDPL_WRITE)) return VDPL_E_BUFFER;
    if (count == VDPL_WHOLE_BUFFER) count = found->second.size() - offset;
    if (offset > found->second.size() || count > found->second.size() - offset)
        return VDPL_E_BOUNDS;
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
    return context.leases.erase(lease) == 1 ? VDPL_OK : VDPL_E_HANDLE;
}

int32_t surface_info(void *opaque, vdplet_surface_v1 *surface) {
    auto& context = *static_cast<Context *>(opaque);
    if (!surface || surface->struct_bytes != sizeof(*surface)) return VDPL_E_ARGUMENT;
    ++context.surface_calls;
    *surface = {sizeof(*surface), W3V_SCREEN_WIDTH, W3V_SCREEN_HEIGHT,
                VDPL_NATIVE_RGB222, 3, 64,
                VDPL_SURFACE_PHYSICAL | VDPL_SURFACE_DOUBLE_BUFFERED};
    return VDPL_OK;
}

int32_t pixels_write(void *opaque, const vdplet_pixels_v1 *pixels) {
    auto& context = *static_cast<Context *>(opaque);
    if (!pixels || pixels->struct_bytes != sizeof(*pixels) ||
        pixels->format != VDPL_PIXELS_RGB222 || !pixels->source ||
        pixels->x != 0 || pixels->y != 0 ||
        pixels->width != W3V_SCREEN_WIDTH || pixels->height != W3V_SCREEN_HEIGHT ||
        pixels->stride != W3V_SCREEN_WIDTH || pixels->source_bytes < W3V_FRAME_BYTES)
        return VDPL_E_ARGUMENT;
    for (std::uint32_t i = 0; i < W3V_FRAME_BYTES; ++i)
        if (pixels->source[i] > 63) return VDPL_E_FORMAT;
    std::copy(pixels->source, pixels->source + W3V_FRAME_BYTES, context.hidden.begin());
    ++context.pixel_calls;
    return VDPL_OK;
}

vdplet_request_v1 request(std::uint16_t operation, std::uint16_t entry = 0,
                          std::uint16_t arguments = 0, std::uint32_t bytes = 0) {
    return {sizeof(vdplet_request_v1), operation, entry, arguments, 0, bytes};
}

}  // namespace

int main(int argc, char **argv) {
    if (argc != 7) {
        std::cerr << "usage: host_runner MAP TEXTURES CONFIG WORKSPACE FRAME GEOMETRY\n";
        return 2;
    }
    try {
        Context context;
        context.buffers[0x7101] = read_file(argv[1]);
        context.buffers[0x7102] = read_file(argv[2]);
        context.buffers[0x7103] = read_file(argv[3]);
        context.buffers[0x7100] = read_file(argv[4]);

        vdplet_host_v1_3 api{};
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

        auto init = request(VDPL_INIT);
        if (vdplet_entry(&base, &init) != VDPL_OK) throw std::runtime_error("INIT failed");
        auto config = request(VDPL_RUN, W3V_ENTRY_CONFIG, 0x7103, W3V_CONFIG_BYTES);
        if (vdplet_entry(&base, &config) != VDPL_OK) throw std::runtime_error("CONFIG failed");
        if (!context.leases.empty()) throw std::runtime_error("CONFIG leaked a lease");
        auto render = request(VDPL_RUN, W3V_ENTRY_RENDER);
        if (vdplet_entry(&base, &render) != VDPL_OK) throw std::runtime_error("RENDER failed");
        if (!context.leases.empty()) throw std::runtime_error("RENDER leaked a lease");
        if (context.max_leases != 3 || context.surface_calls != 1 || context.pixel_calls != 1)
            throw std::runtime_error("unexpected service/lease observation");

        write_file(argv[5], context.hidden.data(), context.hidden.size());
        auto& workspace = context.buffers.at(0x7100);
        write_file(argv[6], workspace.data() + W3V_FRAME_BYTES,
                   W3V_SPRITE_ARENA_OFFSET - W3V_FRAME_BYTES);

        auto fini = request(VDPL_FINI);
        if (vdplet_entry(&base, &fini) != VDPL_OK) throw std::runtime_error("FINI failed");
        if (vdplet_entry(&base, &render) != VDPL_E_INIT)
            throw std::runtime_error("render after FINI retained state");
        std::cout << "host_runner: pass leases=" << context.max_leases
                  << " pixels=" << context.pixel_calls
                  << " bytes=" << context.hidden.size() << "\n";
    } catch (const std::exception& error) {
        std::cerr << "host_runner: " << error.what() << "\n";
        return 1;
    }
    return 0;
}
