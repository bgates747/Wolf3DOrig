#ifdef WOLF3D_HOST_TEST
#include "../qualification/vdplet_host_shim.h"
#else
#include "vdplet.h"
#endif

#include "wolf3d_renderer.h"

// The production package is intentionally one freestanding translation unit.
// Host tests also compile these components separately, while the module build
// includes their exact sources to satisfy the SDK's single-source admission
// driver without introducing a second implementation.
#include "wolf3d_world_mirror.cpp"
#include "wolf3d_renderer.cpp"

#ifndef WOLF3D_HOST_TEST
extern "C" void *memcpy(void *destination, const void *source, unsigned count) {
    volatile uint8_t *d = static_cast<volatile uint8_t *>(destination);
    const volatile uint8_t *s = static_cast<const volatile uint8_t *>(source);
    while (count-- != 0) *d++ = *s++;
    return destination;
}

extern "C" void *memset(void *destination, int value, unsigned count) {
    volatile uint8_t *d = static_cast<volatile uint8_t *>(destination);
    while (count-- != 0) *d++ = static_cast<uint8_t>(value);
    return destination;
}

union WideWords {
    uint64_t value;
    struct { uint32_t low, high; } words;
};

static bool wide_at_least(const WideWords &left, const WideWords &right) {
    return left.words.high > right.words.high ||
        (left.words.high == right.words.high && left.words.low >= right.words.low);
}

static void wide_subtract(WideWords &left, const WideWords &right) {
    const uint32_t old_low = left.words.low;
    left.words.low -= right.words.low;
    left.words.high -= right.words.high + (old_low < right.words.low ? 1u : 0u);
}

static WideWords wide_negate(WideWords value) {
    value.words.low = ~value.words.low + 1u;
    value.words.high = ~value.words.high + (value.words.low == 0 ? 1u : 0u);
    return value;
}

static uint64_t divide_u64(uint64_t numerator, uint64_t denominator) {
    WideWords dividend = {numerator};
    WideWords divisor = {denominator};
    if (divisor.words.low == 0 && divisor.words.high == 0) return UINT64_MAX;
    if ((dividend.words.high | divisor.words.high) == 0)
        return static_cast<uint64_t>(dividend.words.low / divisor.words.low);
    WideWords quotient = {0};
    WideWords remainder = {0};
    for (int bit = 63; bit >= 0; --bit) {
        const uint32_t source_bit = bit >= 32
            ? ((dividend.words.high >> (bit - 32)) & 1u)
            : ((dividend.words.low >> bit) & 1u);
        remainder.words.high = (remainder.words.high << 1) |
                               (remainder.words.low >> 31);
        remainder.words.low = (remainder.words.low << 1) | source_bit;
        if (wide_at_least(remainder, divisor)) {
            wide_subtract(remainder, divisor);
            if (bit >= 32) quotient.words.high |= 1u << (bit - 32);
            else quotient.words.low |= 1u << bit;
        }
    }
    return quotient.value;
}

extern "C" uint64_t __udivdi3(uint64_t numerator, uint64_t denominator) {
    return divide_u64(numerator, denominator);
}

extern "C" int64_t __divdi3(int64_t numerator, int64_t denominator) {
    const bool negative = (numerator < 0) != (denominator < 0);
    WideWords unsigned_numerator = {static_cast<uint64_t>(numerator)};
    WideWords unsigned_denominator = {static_cast<uint64_t>(denominator)};
    if (numerator < 0) unsigned_numerator = wide_negate(unsigned_numerator);
    if (denominator < 0) unsigned_denominator = wide_negate(unsigned_denominator);
    WideWords quotient = {
        divide_u64(unsigned_numerator.value, unsigned_denominator.value)};
    if (negative) quotient = wide_negate(quotient);
    return static_cast<int64_t>(quotient.value);
}
#endif

namespace wolf3d_production {
namespace {

struct ModuleState {
    ResourceDescriptor resources;
    WorldMirror mirror;
    struct FizzleCursor {
        uint32_t state;
        uint32_t emitted;
    } fizzle[2];
    uint8_t fizzle_step;
    uint8_t fizzle_active;
    uint8_t configured;
};

struct ServiceAssets {
    const vdplet_host_v1 *host;
    int32_t native_error;
};

static ModuleState g_module;

void clear_module() {
    uint8_t *bytes = reinterpret_cast<uint8_t *>(&g_module);
    for (size_t i = 0; i < sizeof(g_module); ++i) bytes[i] = 0;
    g_module.mirror.view_weapon_shape = -1;
}

void reset_fizzle() {
    for (uint32_t surface = 0; surface < 2; ++surface) {
        g_module.fizzle[surface].state = 1;
        g_module.fizzle[surface].emitted = 0;
    }
    g_module.fizzle_step = 0;
    g_module.fizzle_active = 0;
}

uint32_t advance_fizzle_state(uint32_t state) {
    const bool low_bit = (state & 1u) != 0;
    state >>= 1;
    if (low_bit) state ^= 0x12000u;
    return state;
}

uint32_t fizzle_target(uint8_t step) {
    const uint32_t pixels = W3P_VIEW_WIDTH * W3P_VIEW_HEIGHT;
    if (step >= W3P_FIZZLE_DISPLAY_FRAMES) return pixels;
    return pixels * step / W3P_FIZZLE_DISPLAY_FRAMES;
}

void emit_fizzle(ModuleState::FizzleCursor &cursor, uint32_t target,
                  uint8_t *linear, uintptr_t *rows, uint32_t x_bias,
                  uint32_t pixel_xor, uint8_t color_mask,
                  uint8_t preserve_mask) {
    while (cursor.emitted < target) {
        const uint32_t state = cursor.state;
        const uint16_t y = static_cast<uint16_t>(
            ((state & 0xffu) - 1u) & 0xffu);
        const uint16_t x = static_cast<uint16_t>((state >> 8) & 0x1ffu);
        cursor.state = advance_fizzle_state(state);
        if (x >= W3P_VIEW_WIDTH || y >= W3P_VIEW_HEIGHT) continue;
        uint8_t *pixel;
        if (linear != nullptr) {
            pixel = linear + (W3P_VIEW_Y + y) * W3P_SCREEN_WIDTH +
                W3P_VIEW_X + x;
        } else {
            pixel = reinterpret_cast<uint8_t *>(rows[y]) +
                ((x_bias + x) ^ pixel_xor);
        }
        *pixel = static_cast<uint8_t>(
            (*pixel & preserve_mask) | (W3P_FIZZLE_RED & color_mask));
        ++cursor.emitted;
    }
}

int32_t batch_status(BatchDetail detail) {
    return detail == BatchDetail::bounds ? VDPL_E_BOUNDS : VDPL_E_ARGUMENT;
}

int32_t render_status(RenderDetail detail) {
    switch (detail) {
    case RenderDetail::ok: return VDPL_OK;
    case RenderDetail::bounds: return VDPL_E_BOUNDS;
    case RenderDetail::asset: return VDPL_E_BUFFER;
    case RenderDetail::release: return VDPL_E_HANDLE;
    case RenderDetail::argument:
    case RenderDetail::world:
        return VDPL_E_ARGUMENT;
    }
    return VDPL_E_ARGUMENT;
}

bool same_descriptor(const ResourceDescriptor &left,
                     const ResourceDescriptor &right) {
    return left.flags == right.flags &&
        left.workspace_id == right.workspace_id &&
        left.update_id == right.update_id &&
        left.tilemap_id == right.tilemap_id &&
        left.wall_base == right.wall_base &&
        left.sprite_base == right.sprite_base &&
        left.hud_base == right.hud_base &&
        left.generation_seed == right.generation_seed;
}

int32_t copy_descriptor(const vdplet_host_v1 *host,
                        const vdplet_request_v1 *request,
                        ResourceDescriptor &descriptor) {
    if (request->argument_bytes != W3P_ARGUMENT_BYTES)
        return VDPL_E_BOUNDS;
    vdplet_view_v1 view = {sizeof(view), 0, nullptr, 0, 0};
    int32_t status = host->buffer_acquire(
        host->context, request->argument_buffer, VDPL_READ, 0,
        W3P_ARGUMENT_BYTES, &view);
    if (status != VDPL_OK) return status;
    uint8_t bytes[W3P_ARGUMENT_BYTES];
    if (view.data == nullptr || view.bytes < W3P_ARGUMENT_BYTES) {
        status = VDPL_E_BOUNDS;
    } else {
        for (uint32_t i = 0; i < W3P_ARGUMENT_BYTES; ++i)
            bytes[i] = view.data[i];
    }
    const int32_t released = host->buffer_release(host->context, view.lease);
    if (status == VDPL_OK) status = released;
    if (status != VDPL_OK) return status;
    const BatchDetail detail = validate_resource_descriptor(
        descriptor, bytes, sizeof(bytes));
    return detail == BatchDetail::ok ? VDPL_OK : batch_status(detail);
}

int32_t require_matching_descriptor(const vdplet_host_v1 *host,
                                    const vdplet_request_v1 *request) {
    if (!g_module.configured) return VDPL_E_INIT;
    ResourceDescriptor descriptor{};
    const int32_t status = copy_descriptor(host, request, descriptor);
    if (status != VDPL_OK) return status;
    return same_descriptor(descriptor, g_module.resources)
        ? VDPL_OK : VDPL_E_ARGUMENT;
}

int32_t configure(const vdplet_host_v1 *host,
                  const vdplet_request_v1 *request) {
    ResourceDescriptor descriptor{};
    const int32_t status = copy_descriptor(host, request, descriptor);
    if (status != VDPL_OK) return status;
    g_module.resources = descriptor;
    initialize_world_mirror(g_module.mirror, descriptor.generation_seed,
                            descriptor.tilemap_id);
    reset_fizzle();
    g_module.configured = 1;
    return VDPL_OK;
}

RenderDetail acquire_asset(void *opaque, uint16_t buffer_id, AssetSpan &span) {
    ServiceAssets &assets = *static_cast<ServiceAssets *>(opaque);
    vdplet_view_v1 view = {sizeof(view), 0, nullptr, 0, 0};
    const int32_t status = assets.host->buffer_acquire(
        assets.host->context, buffer_id, VDPL_READ, 0,
        VDPL_WHOLE_BUFFER, &view);
    if (status != VDPL_OK) {
        if (assets.native_error == VDPL_OK) assets.native_error = status;
        return RenderDetail::asset;
    }
    span.bytes = view.data;
    span.byte_count = view.bytes;
    span.lease = view.lease;
    return RenderDetail::ok;
}

RenderDetail release_asset(void *opaque, uint32_t lease) {
    ServiceAssets &assets = *static_cast<ServiceAssets *>(opaque);
    const int32_t status = assets.host->buffer_release(
        assets.host->context, lease);
    if (status != VDPL_OK) {
        if (assets.native_error == VDPL_OK) assets.native_error = status;
        return RenderDetail::release;
    }
    return RenderDetail::ok;
}

void preserve_first_error(int32_t &status, int32_t candidate) {
    if (status == VDPL_OK && candidate != VDPL_OK) status = candidate;
}

int32_t apply_and_render(const vdplet_host_v1 *host,
                         const vdplet_request_v1 *request) {
    int32_t status = require_matching_descriptor(host, request);
    if (status != VDPL_OK) return status;
    if (g_module.fizzle_active) return VDPL_E_BUSY;
    const bool direct_rows =
        g_module.resources.flags == W3P_ARG_FLAG_DIRECT_ROWS;
    const vdplet_host_v1_6 *color = direct_rows
        ? vdplet_color_frame_host(host) : nullptr;
    const vdplet_host_v1_3 *media = direct_rows
        ? nullptr : vdplet_pixels_host(host);
    if ((direct_rows && color == nullptr) || (!direct_rows && media == nullptr))
        return VDPL_E_ABI;
    if (!direct_rows) {
        vdplet_surface_v1 surface = {sizeof(surface), 0, 0, 0, 0, 0, 0};
        status = media->surface_info(host->context, &surface);
        if (status != VDPL_OK) return status;
        if (surface.width != W3P_SCREEN_WIDTH ||
            surface.height != W3P_SCREEN_HEIGHT ||
            surface.native_format != VDPL_NATIVE_RGB222 ||
            (surface.source_formats & VDPL_PIXELS_RGB222) == 0 ||
            (surface.flags & (VDPL_SURFACE_PHYSICAL |
                              VDPL_SURFACE_DOUBLE_BUFFERED)) !=
                (VDPL_SURFACE_PHYSICAL | VDPL_SURFACE_DOUBLE_BUFFERED))
            return VDPL_E_FORMAT;
    }

    vdplet_view_v1 update = {sizeof(update), 0, nullptr, 0, 0};
    status = host->buffer_acquire(
        host->context, g_module.resources.update_id, VDPL_READ, 0,
        VDPL_WHOLE_BUFFER, &update);
    if (status != VDPL_OK) return status;
    BatchDetail batch = BatchDetail::bounds;
    if (update.data != nullptr && update.bytes <= W3P_BATCH_MAX_BYTES)
        batch = apply_update_batch(g_module.mirror, update.data, update.bytes);
    status = batch == BatchDetail::ok ? VDPL_OK : batch_status(batch);
    preserve_first_error(
        status, host->buffer_release(host->context, update.lease));
    if (status != VDPL_OK) return status;

    vdplet_view_v1 workspace = {sizeof(workspace), 0, nullptr, 0, 0};
    vdplet_view_v1 tilemap = {sizeof(tilemap), 0, nullptr, 0, 0};
    const uint32_t workspace_bytes = direct_rows
        ? static_cast<uint32_t>(W3P_DIRECT_WORKSPACE_BYTES)
        : W3P_WORKSPACE_BYTES;
    status = host->buffer_acquire(
        host->context, g_module.resources.workspace_id, VDPL_WRITE, 0,
        workspace_bytes, &workspace);
    if (status != VDPL_OK) return status;
    status = host->buffer_acquire(
        host->context, g_module.resources.tilemap_id, VDPL_READ, 0,
        W3P_MAP_SIZE * W3P_MAP_SIZE, &tilemap);
    if (status != VDPL_OK) {
        host->buffer_release(host->context, workspace.lease);
        return status;
    }

    ServiceAssets service_assets = {host, VDPL_OK};
    RenderResources resources = {
        tilemap.data, tilemap.bytes, workspace.data, workspace.bytes,
        g_module.resources.wall_base, g_module.resources.sprite_base,
        g_module.resources.hud_base,
        {&service_assets, acquire_asset, release_asset}};
    if (direct_rows) {
        uintptr_t *const rows = reinterpret_cast<uintptr_t *>(workspace.data);
        for (uint32_t row = 0; row < W3P_SCREEN_HEIGHT; ++row) rows[row] = 0;
        vdplet_color_frame_v1 frame = {
            sizeof(frame), 0, 0, 0, W3P_SCREEN_WIDTH, W3P_SCREEN_HEIGHT,
            0, 0, nullptr, 0, 0, 0, 0, 0};
        status = color->color_frame(
            host->context, VDPL_COLOR_FRAME_BEGIN, &frame);
        const bool began = status == VDPL_OK;
        uint32_t acquired_rows = 0;
        if (began) {
            for (uint32_t row = 0; row < W3P_SCREEN_HEIGHT; ++row) {
                frame.row = row;
                status = color->color_frame(
                    host->context, VDPL_COLOR_FRAME_ROW, &frame);
                if (status != VDPL_OK) break;
                if (frame.data == nullptr ||
                    (reinterpret_cast<uintptr_t>(frame.data) & 3u) != 0 ||
                    frame.x != 0 || frame.y != 0 ||
                    frame.width != W3P_SCREEN_WIDTH ||
                    frame.height != W3P_SCREEN_HEIGHT || frame.row != row ||
                    frame.native_format != VDPL_NATIVE_RGB222 ||
                    frame.row_bytes != W3P_SCREEN_WIDTH ||
                    frame.x_bias != 0 || frame.pixel_xor != 2 ||
                    frame.color_mask != 0x3fu ||
                    frame.preserve_mask != 0xc0u) {
                    status = VDPL_E_FORMAT;
                    break;
                }
                rows[row] = reinterpret_cast<uintptr_t>(frame.data);
                ++acquired_rows;
            }
        }
        if (status == VDPL_OK) {
            const RenderTarget target = {
                nullptr, rows, frame.x_bias, frame.pixel_xor,
                static_cast<uint8_t>(frame.color_mask),
                static_cast<uint8_t>(frame.preserve_mask)};
            const RenderDetail rendered = render_world_direct(
                g_module.mirror, resources, target);
            status = service_assets.native_error != VDPL_OK
                ? service_assets.native_error : render_status(rendered);
        }
        for (uint32_t row = 0; row < acquired_rows; ++row) rows[row] = 0;
        if (began) preserve_first_error(
            status, color->color_frame(
                host->context, VDPL_COLOR_FRAME_END, &frame));
    } else {
        const RenderDetail rendered = render_world(g_module.mirror, resources);
        status = service_assets.native_error != VDPL_OK
            ? service_assets.native_error : render_status(rendered);
        if (status == VDPL_OK) {
        const vdplet_pixels_v1 pixels = {
            sizeof(pixels), VDPL_PIXELS_RGB222, 0, 0,
            W3P_SCREEN_WIDTH, W3P_SCREEN_HEIGHT, W3P_SCREEN_WIDTH,
            W3P_FRAME_BYTES, workspace.data};
            status = media->pixels_write(host->context, &pixels);
        }
    }
    preserve_first_error(
        status, host->buffer_release(host->context, tilemap.lease));
    preserve_first_error(
        status, host->buffer_release(host->context, workspace.lease));
    if (status == VDPL_OK) mark_mirror_presented(g_module.mirror);
    return status;
}

int32_t require_published_frame(const vdplet_host_v1 *host,
                                const vdplet_request_v1 *request) {
    const int32_t status = require_matching_descriptor(host, request);
    if (status != VDPL_OK) return status;
    if (!g_module.mirror.ready || g_module.mirror.pending_present ||
        g_module.mirror.presented_generation != g_module.mirror.generation)
        return VDPL_E_INIT;
    return VDPL_OK;
}

int32_t fizzle_begin(const vdplet_host_v1 *host,
                     const vdplet_request_v1 *request) {
    const int32_t status = require_published_frame(host, request);
    if (status != VDPL_OK) return status;
    if (g_module.fizzle_active) return VDPL_E_BUSY;
    reset_fizzle();
    g_module.fizzle_active = 1;
    return VDPL_OK;
}

int32_t fizzle_copied(const vdplet_host_v1 *host, uint32_t target,
                      ModuleState::FizzleCursor &next) {
    const vdplet_host_v1_3 *media = vdplet_pixels_host(host);
    if (media == nullptr) return VDPL_E_ABI;
    vdplet_view_v1 workspace = {sizeof(workspace), 0, nullptr, 0, 0};
    int32_t status = host->buffer_acquire(
        host->context, g_module.resources.workspace_id, VDPL_WRITE, 0,
        W3P_FRAME_BYTES, &workspace);
    if (status != VDPL_OK) return status;
    if (workspace.data == nullptr || workspace.bytes < W3P_FRAME_BYTES) {
        status = VDPL_E_BOUNDS;
    } else {
        emit_fizzle(next, target, workspace.data, nullptr, 0, 0, 0x3f, 0);
        const vdplet_pixels_v1 pixels = {
            sizeof(pixels), VDPL_PIXELS_RGB222, 0, 0,
            W3P_SCREEN_WIDTH, W3P_SCREEN_HEIGHT, W3P_SCREEN_WIDTH,
            W3P_FRAME_BYTES, workspace.data};
        status = media->pixels_write(host->context, &pixels);
    }
    preserve_first_error(
        status, host->buffer_release(host->context, workspace.lease));
    return status;
}

int32_t fizzle_direct(const vdplet_host_v1 *host, uint32_t target,
                      ModuleState::FizzleCursor &next) {
    const vdplet_host_v1_6 *color = vdplet_color_frame_host(host);
    if (color == nullptr) return VDPL_E_ABI;
    const uint32_t pointer_bytes =
        W3P_VIEW_HEIGHT * static_cast<uint32_t>(sizeof(uintptr_t));
    vdplet_view_v1 workspace = {sizeof(workspace), 0, nullptr, 0, 0};
    int32_t status = host->buffer_acquire(
        host->context, g_module.resources.workspace_id, VDPL_WRITE, 0,
        pointer_bytes, &workspace);
    if (status != VDPL_OK) return status;
    if (workspace.data == nullptr || workspace.bytes < pointer_bytes) {
        status = VDPL_E_BOUNDS;
        preserve_first_error(
            status, host->buffer_release(host->context, workspace.lease));
        return status;
    }
    uintptr_t *const rows = reinterpret_cast<uintptr_t *>(workspace.data);
    for (uint32_t row = 0; row < W3P_VIEW_HEIGHT; ++row) rows[row] = 0;
    vdplet_color_frame_v1 frame = {
        sizeof(frame), 0, W3P_VIEW_X, W3P_VIEW_Y,
        W3P_VIEW_WIDTH, W3P_VIEW_HEIGHT,
        0, 0, nullptr, 0, 0, 0, 0, 0};
    status = color->color_frame(
        host->context, VDPL_COLOR_FRAME_BEGIN, &frame);
    const bool began = status == VDPL_OK;
    uint32_t acquired_rows = 0;
    uint32_t x_bias = 0;
    uint32_t pixel_xor = 0;
    uint8_t color_mask = 0;
    uint8_t preserve_mask = 0;
    if (began) {
        for (uint32_t row = 0; row < W3P_VIEW_HEIGHT; ++row) {
            frame.row = row;
            status = color->color_frame(
                host->context, VDPL_COLOR_FRAME_ROW, &frame);
            if (status != VDPL_OK) break;
            if (frame.data == nullptr ||
                (reinterpret_cast<uintptr_t>(frame.data) & 3u) != 0 ||
                frame.x != W3P_VIEW_X || frame.y != W3P_VIEW_Y ||
                frame.width != W3P_VIEW_WIDTH ||
                frame.height != W3P_VIEW_HEIGHT || frame.row != row ||
                frame.native_format != VDPL_NATIVE_RGB222 ||
                frame.row_bytes < frame.x_bias + W3P_VIEW_WIDTH ||
                frame.pixel_xor != 2 || frame.color_mask != 0x3fu ||
                frame.preserve_mask != 0xc0u) {
                status = VDPL_E_FORMAT;
                break;
            }
            if (row == 0) {
                x_bias = frame.x_bias;
                pixel_xor = frame.pixel_xor;
                color_mask = static_cast<uint8_t>(frame.color_mask);
                preserve_mask = static_cast<uint8_t>(frame.preserve_mask);
            } else if (frame.x_bias != x_bias ||
                       frame.pixel_xor != pixel_xor ||
                       frame.color_mask != color_mask ||
                       frame.preserve_mask != preserve_mask) {
                status = VDPL_E_FORMAT;
                break;
            }
            rows[row] = reinterpret_cast<uintptr_t>(frame.data);
            ++acquired_rows;
        }
    }
    if (status == VDPL_OK) {
        emit_fizzle(next, target, nullptr, rows, x_bias, pixel_xor,
                    color_mask, preserve_mask);
    }
    for (uint32_t row = 0; row < acquired_rows; ++row) rows[row] = 0;
    if (began) preserve_first_error(
        status, color->color_frame(
            host->context, VDPL_COLOR_FRAME_END, &frame));
    preserve_first_error(
        status, host->buffer_release(host->context, workspace.lease));
    return status;
}

int32_t fizzle_step(const vdplet_host_v1 *host,
                    const vdplet_request_v1 *request) {
    const int32_t ready = require_published_frame(host, request);
    if (ready != VDPL_OK) return ready;
    if (!g_module.fizzle_active ||
        g_module.fizzle_step > W3P_FIZZLE_DISPLAY_FRAMES)
        return VDPL_E_INIT;
    const bool direct_rows =
        g_module.resources.flags == W3P_ARG_FLAG_DIRECT_ROWS;
    const uint8_t surface = direct_rows
        ? static_cast<uint8_t>(g_module.fizzle_step & 1u) : 0;
    ModuleState::FizzleCursor next = g_module.fizzle[surface];
    const uint8_t target_step = g_module.fizzle_step <
        W3P_FIZZLE_DISPLAY_FRAMES
        ? static_cast<uint8_t>(g_module.fizzle_step + 1u)
        : static_cast<uint8_t>(W3P_FIZZLE_DISPLAY_FRAMES);
    const uint32_t target = fizzle_target(target_step);
    const int32_t status = direct_rows
        ? fizzle_direct(host, target, next)
        : fizzle_copied(host, target, next);
    if (status != VDPL_OK) return status;
    g_module.fizzle[surface] = next;
    ++g_module.fizzle_step;
    if (g_module.fizzle_step > W3P_FIZZLE_DISPLAY_FRAMES)
        g_module.fizzle_active = 0;
    return VDPL_OK;
}

int32_t reset(const vdplet_host_v1 *host,
              const vdplet_request_v1 *request) {
    const int32_t status = require_matching_descriptor(host, request);
    if (status != VDPL_OK) return status;
    clear_module();
    return VDPL_OK;
}

}  // namespace
}  // namespace wolf3d_production

extern "C" __attribute__((visibility("default")))
int32_t vdplet_entry(const vdplet_host_v1 *host,
                     const vdplet_request_v1 *request) {
    using namespace wolf3d_production;
    if (host == nullptr || request == nullptr ||
        host->abi_major != VDPL_ABI_MAJOR ||
        host->struct_bytes < sizeof(vdplet_host_v1) ||
        (host->capabilities & VDPL_CAP_BUFFERS) == 0 ||
        host->buffer_acquire == nullptr || host->buffer_release == nullptr)
        return VDPL_E_ABI;
    if (request->struct_bytes < sizeof(vdplet_request_v1) ||
        request->reserved != 0) return VDPL_E_ARGUMENT;
    if (request->operation == VDPL_INIT) {
        clear_module();
        return VDPL_OK;
    }
    if (request->operation == VDPL_FINI) {
        clear_module();
        return VDPL_OK;
    }
    if (request->operation != VDPL_RUN) return VDPL_E_UNSUPPORTED;
    switch (request->entry_id) {
    case W3P_ENTRY_CONFIG:
        return configure(host, request);
    case W3P_ENTRY_APPLY_AND_RENDER:
        return apply_and_render(host, request);
    case W3P_ENTRY_FIZZLE_BEGIN:
        return fizzle_begin(host, request);
    case W3P_ENTRY_FIZZLE_STEP:
        return fizzle_step(host, request);
    case W3P_ENTRY_RESET:
        return reset(host, request);
    case W3P_ENTRY_SELFTEST:
    default:
        return VDPL_E_UNSUPPORTED;
    }
}
