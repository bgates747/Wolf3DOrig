#ifndef AGON_VDPLET_ABI_H
#define AGON_VDPLET_ABI_H
#include <stdint.h>
#include <stddef.h>

/* VDPlet Runtime ABI, classic ESP32 / windowed Xtensa GCC 8.4. */
#include "vdplet_protocol.h"
#include "vdplet_services.h"
#include "vdplet_pcm_sink.h"

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
    int32_t (*buffer_acquire)(void *, uint16_t, uint16_t, uint32_t, uint32_t, vdplet_view_v1 *);
    int32_t (*buffer_release)(void *, uint32_t);
    int32_t (*frame_begin)(void *, int32_t, int32_t, uint32_t, uint32_t, vdplet_frame_v1 *);
    int32_t (*frame_row)(void *, uint32_t, uint32_t, vdplet_view_v1 *);
    int32_t (*frame_end)(void *, uint32_t);
} vdplet_host_v1;
/* ABI1.1 extends, rather than changes, the original prefix. */
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
/* ABI1.4 shares application audio queues with ordinary command15. Its result
   codes are AUDIOQ_* (include vdp_audio_queue.h), not VDPL_E_*. */
typedef struct vdplet_host_v1_4 {
    vdplet_host_v1_3 base;
    uint32_t (*audio_queue)(void *, uint8_t, uint8_t, const uint8_t *, uint32_t, uint32_t *);
} vdplet_host_v1_4;
/* ABI1.5 appends an optional copied PCM sink; unsupported prior slots may be
   null in lean builds. Check capability bits before calling any service. */
typedef struct vdplet_host_v1_5 {
    vdplet_host_v1_4 base;
    int32_t (*pcm_sink)(void *, uint32_t, vdplet_pcm_sink_v1 *);
} vdplet_host_v1_5;
/* ABI1.6 appends an optional scoped colour-row transaction. */
typedef struct vdplet_host_v1_6 {
    vdplet_host_v1_5 base;
    int32_t (*color_frame)(void *, uint32_t, vdplet_color_frame_v1 *);
} vdplet_host_v1_6;
static inline const vdplet_host_v1_6 *vdplet_color_frame_host(const vdplet_host_v1 *h) {
    if (!h || h->abi_major!=VDPL_ABI_MAJOR || h->abi_minor<VDPL_ABI_MINOR_COLOR_FRAME ||
        h->struct_bytes<sizeof(vdplet_host_v1_6) || !(h->capabilities&VDPL_CAP_COLOR_FRAME)) return 0;
    const vdplet_host_v1_6 *f=(const vdplet_host_v1_6 *)h;
    return f->color_frame ? f : 0;
}
static inline const vdplet_host_v1_5 *vdplet_pcm_sink_host(const vdplet_host_v1 *h) {
    if (!h || h->abi_major!=VDPL_ABI_MAJOR || h->abi_minor<VDPL_ABI_MINOR_PCM_SINK ||
        h->struct_bytes<sizeof(vdplet_host_v1_5) || !(h->capabilities&VDPL_CAP_PCM_SINK)) return 0;
    const vdplet_host_v1_5 *s=(const vdplet_host_v1_5 *)h;
    return s->pcm_sink ? s : 0;
}
static inline const vdplet_host_v1_4 *vdplet_audio_queue_host(const vdplet_host_v1 *h) {
    if (!h || h->abi_major!=VDPL_ABI_MAJOR || h->abi_minor<VDPL_ABI_MINOR_AUDIO_QUEUE ||
        h->struct_bytes<sizeof(vdplet_host_v1_4) || !(h->capabilities&VDPL_CAP_AUDIO_QUEUE)) return 0;
    const vdplet_host_v1_4 *q=(const vdplet_host_v1_4 *)h;
    return q->audio_queue ? q : 0;
}
/* Independent optional services: neither accessor requires the other feature. */
static inline const vdplet_host_v1_3 *vdplet_pixels_host(const vdplet_host_v1 *h) {
    if (!h || h->abi_major != VDPL_ABI_MAJOR || h->abi_minor < VDPL_ABI_MINOR_MEDIA ||
        h->struct_bytes < sizeof(vdplet_host_v1_3) || !(h->capabilities & VDPL_CAP_PIXELS)) return 0;
    const vdplet_host_v1_3 *m=(const vdplet_host_v1_3 *)h;
    return m->surface_info && m->pixels_write ? m : 0;
}
static inline const vdplet_host_v1_3 *vdplet_pcm_host(const vdplet_host_v1 *h) {
    if (!h || h->abi_major != VDPL_ABI_MAJOR || h->abi_minor < VDPL_ABI_MINOR_MEDIA ||
        h->struct_bytes < sizeof(vdplet_host_v1_3) || !(h->capabilities & VDPL_CAP_PCM)) return 0;
    const vdplet_host_v1_3 *m=(const vdplet_host_v1_3 *)h;
    return m->pcm_open && m->pcm_enqueue && m->pcm_state && m->pcm_control && m->pcm_close ? m : 0;
}
static inline const vdplet_host_v1_3 *vdplet_media_host(const vdplet_host_v1 *h) {
    if (!h || h->abi_major != VDPL_ABI_MAJOR || h->abi_minor < VDPL_ABI_MINOR_MEDIA ||
        h->struct_bytes < sizeof(vdplet_host_v1_3) ||
        (h->capabilities&(VDPL_CAP_PIXELS|VDPL_CAP_PCM))!=(VDPL_CAP_PIXELS|VDPL_CAP_PCM)) return 0;
    const vdplet_host_v1_3 *m=(const vdplet_host_v1_3 *)h;
    return m->surface_info && m->pixels_write && m->pcm_open && m->pcm_enqueue &&
        m->pcm_state && m->pcm_control && m->pcm_close ? m : 0;
}
static inline const vdplet_host_v1_1 *vdplet_vdu_host(const vdplet_host_v1 *h) {
    if (!h || h->abi_major != VDPL_ABI_MAJOR || h->abi_minor < VDPL_ABI_MINOR_VDU ||
        h->struct_bytes < sizeof(vdplet_host_v1_1) || !(h->capabilities & VDPL_CAP_VDU)) return 0;
    const vdplet_host_v1_1 *extended = (const vdplet_host_v1_1 *)h;
    return extended->vdu_submit ? extended : 0;
}
static inline const vdplet_host_v1_2 *vdplet_lines_host(const vdplet_host_v1 *h) {
    if (!h || h->abi_major != VDPL_ABI_MAJOR || h->abi_minor < VDPL_ABI_MINOR_LINES ||
        h->struct_bytes < sizeof(vdplet_host_v1_2) || !(h->capabilities & VDPL_CAP_LINES)) return 0;
    const vdplet_host_v1_2 *extended = (const vdplet_host_v1_2 *)h;
    return extended->draw_lines ? extended : 0;
}
typedef int32_t (*vdplet_entry_v1)(const vdplet_host_v1 *, const vdplet_request_v1 *);

#if defined(__cplusplus)
static_assert(sizeof(void *) == 4, "ESP32 pointer ABI");
static_assert(sizeof(vdplet_host_v1) == 36, "host ABI");
static_assert(sizeof(vdplet_host_v1_1) == 40, "extended host ABI");
static_assert(sizeof(vdplet_host_v1_2) == 44, "line batch host ABI");
static_assert(sizeof(vdplet_host_v1_3) == 72, "media host ABI");
static_assert(sizeof(vdplet_host_v1_4) == 76, "audio queue host ABI");
static_assert(sizeof(vdplet_host_v1_5) == 80, "PCM sink host ABI");
static_assert(sizeof(vdplet_host_v1_6) == 84, "colour-frame host ABI");
static_assert(offsetof(vdplet_host_v1_6,color_frame) == 80, "colour-frame callback offset");
static_assert(sizeof(vdplet_color_frame_v1) == 56, "colour-frame descriptor ABI");
static_assert(offsetof(vdplet_color_frame_v1,data) == 32, "colour-frame row pointer offset");
static_assert(offsetof(vdplet_color_frame_v1,preserve_mask) == 52, "colour-frame mask offset");
static_assert(sizeof(vdplet_pcm_sink_v1) == 56, "PCM sink request ABI");
static_assert(sizeof(vdplet_surface_v1) == 28, "surface ABI");
static_assert(sizeof(vdplet_pixels_v1) == 36, "pixel request ABI");
static_assert(sizeof(vdplet_pcm_config_v1) == 20, "PCM config ABI");
static_assert(sizeof(vdplet_pcm_state_v1) == 48, "PCM state ABI");
static_assert(sizeof(vdplet_line_v1) == 8, "line endpoint ABI");
static_assert(sizeof(vdplet_request_v1) == 16, "request ABI");
static_assert(sizeof(vdplet_view_v1) == 20, "view ABI");
static_assert(sizeof(vdplet_frame_v1) == 24, "frame ABI");
#endif
#endif
