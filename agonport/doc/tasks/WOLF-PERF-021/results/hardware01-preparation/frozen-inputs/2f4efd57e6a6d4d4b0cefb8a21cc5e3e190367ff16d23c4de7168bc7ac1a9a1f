#ifndef WOLF3D_VDPLET_HOST_SHIM_H
#define WOLF3D_VDPLET_HOST_SHIM_H

// Native-pointer mirror used only to run the exact module source in a 64-bit
// host process. Target builds include the maintained SDK's real vdplet.h and
// its strict classic-ESP32 layout assertions instead.
#include "vdplet_protocol.h"
#include "vdplet_services.h"

typedef struct vdplet_view_v1 {
    uint32_t struct_bytes;
    uint32_t lease;
    uint8_t *data;
    uint32_t bytes;
    uint32_t access;
} vdplet_view_v1;

typedef struct vdplet_frame_v1 {
    uint32_t struct_bytes;
    uint32_t lease;
    uint32_t format;
    uint32_t width;
    uint32_t height;
    uint32_t row_bytes;
} vdplet_frame_v1;

typedef struct vdplet_request_v1 {
    uint32_t struct_bytes;
    uint16_t operation;
    uint16_t entry_id;
    uint16_t argument_buffer;
    uint16_t reserved;
    uint32_t argument_bytes;
} vdplet_request_v1;

typedef struct vdplet_host_v1 {
    uint32_t struct_bytes;
    uint16_t abi_major;
    uint16_t abi_minor;
    uint32_t capabilities;
    void *context;
    int32_t (*buffer_acquire)(void *, uint16_t, uint16_t, uint32_t, uint32_t,
                              vdplet_view_v1 *);
    int32_t (*buffer_release)(void *, uint32_t);
    int32_t (*frame_begin)(void *, int32_t, int32_t, uint32_t, uint32_t,
                           vdplet_frame_v1 *);
    int32_t (*frame_row)(void *, uint32_t, uint32_t, vdplet_view_v1 *);
    int32_t (*frame_end)(void *, uint32_t);
} vdplet_host_v1;

typedef struct vdplet_host_v1_1 {
    vdplet_host_v1 base;
    int32_t (*vdu_submit)(void *, const uint8_t *, uint32_t);
} vdplet_host_v1_1;

typedef struct vdplet_line_v1 {
    int16_t x1, y1, x2, y2;
} vdplet_line_v1;

typedef struct vdplet_host_v1_2 {
    vdplet_host_v1_1 base;
    int32_t (*draw_lines)(void *, const vdplet_line_v1 *, uint32_t);
} vdplet_host_v1_2;

typedef struct vdplet_host_v1_3 {
    vdplet_host_v1_2 base;
    int32_t (*surface_info)(void *, vdplet_surface_v1 *);
    int32_t (*pixels_write)(void *, const vdplet_pixels_v1 *);
    int32_t (*pcm_open)(void *, const vdplet_pcm_config_v1 *, vdplet_pcm_state_v1 *);
    int32_t (*pcm_enqueue)(void *, uint32_t, const uint8_t *, uint32_t);
    int32_t (*pcm_state)(void *, uint32_t, vdplet_pcm_state_v1 *);
    int32_t (*pcm_control)(void *, uint32_t, uint32_t);
    int32_t (*pcm_close)(void *, uint32_t);
} vdplet_host_v1_3;

// Native-pointer mirrors of the ABI1.4/1.5 tail slots. Their services are not
// used by this qualifier; the opaque pointer-sized fields preserve the table
// prefix so ABI1.6's colour callback occupies the correct relative slot.
typedef struct vdplet_host_v1_4 {
    vdplet_host_v1_3 base;
    void *audio_queue;
} vdplet_host_v1_4;

typedef struct vdplet_host_v1_5 {
    vdplet_host_v1_4 base;
    void *pcm_sink;
} vdplet_host_v1_5;

typedef struct vdplet_host_v1_6 {
    vdplet_host_v1_5 base;
    int32_t (*color_frame)(void *, uint32_t, vdplet_color_frame_v1 *);
} vdplet_host_v1_6;

static inline const vdplet_host_v1_3 *vdplet_pixels_host(
    const vdplet_host_v1 *host) {
    if (!host || host->abi_major != VDPL_ABI_MAJOR ||
        host->abi_minor < VDPL_ABI_MINOR_MEDIA ||
        host->struct_bytes < sizeof(vdplet_host_v1_3) ||
        !(host->capabilities & VDPL_CAP_PIXELS)) return 0;
    const vdplet_host_v1_3 *media = (const vdplet_host_v1_3 *)host;
    return media->surface_info && media->pixels_write ? media : 0;
}

static inline const vdplet_host_v1_6 *vdplet_color_frame_host(
    const vdplet_host_v1 *host) {
    if (!host || host->abi_major != VDPL_ABI_MAJOR ||
        host->abi_minor < VDPL_ABI_MINOR_COLOR_FRAME ||
        host->struct_bytes < sizeof(vdplet_host_v1_6) ||
        !(host->capabilities & VDPL_CAP_COLOR_FRAME)) return nullptr;
    const vdplet_host_v1_6 *frame = (const vdplet_host_v1_6 *)host;
    return frame->color_frame ? frame : nullptr;
}

#endif
