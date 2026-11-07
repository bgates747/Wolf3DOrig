#ifndef AGON_VDPLET_SERVICES_H
#define AGON_VDPLET_SERVICES_H
#include <stdint.h>
/* ABI1.3 descriptors: physical top-left pixels, replacement writes, no implicit
   graphics origin/clip conversion. Source bytes are consumed before return. */
#define VDPL_PIXELS_RGB222 1u
#define VDPL_PIXELS_INDEX8 2u
#define VDPL_NATIVE_PALETTE2 2u
#define VDPL_NATIVE_PALETTE4 4u
#define VDPL_NATIVE_PALETTE8 8u
#define VDPL_NATIVE_PALETTE16 16u
#define VDPL_NATIVE_RGB222 64u
#define VDPL_SURFACE_PHYSICAL 1u
#define VDPL_SURFACE_DOUBLE_BUFFERED 2u
#define VDPL_PCM_S8 1u
#define VDPL_PCM_U8 2u
#define VDPL_PCM_RESET 1u
#define VDPL_PCM_MUTE 2u
#define VDPL_PCM_UNMUTE 3u
#define VDPL_PCM_OPEN 1u
#define VDPL_PCM_STARTED 2u
#define VDPL_PCM_MUTED 4u
#define VDPL_PCM_MAX_FRAMES 8192u
#define VDPL_PCM_DEFAULT_FRAMES 2048u

/* ABI1.6 optional hidden SBGR2222 rows. Rectangles use physical coordinates.
   BEGIN returns a scoped token; ROW returns one independently mapped row group.
   Store only admitted pixels: data[(x_bias+x)^pixel_xor] =
       (old & preserve_mask) | (rgb222 & color_mask).
   Data expires at END/current RUN cleanup. A module must not present failed work. */
#define VDPL_COLOR_FRAME_BEGIN 1u
#define VDPL_COLOR_FRAME_ROW 2u
#define VDPL_COLOR_FRAME_END 3u
typedef struct vdplet_color_frame_v1 {
    uint32_t struct_bytes, lease;
    int32_t x, y;
    uint32_t width, height, row, native_format;
    uint8_t *data;
    uint32_t row_bytes, x_bias, pixel_xor, color_mask, preserve_mask;
} vdplet_color_frame_v1;

typedef struct vdplet_surface_v1 {
    uint32_t struct_bytes, width, height, native_format, source_formats, palette_colors, flags;
} vdplet_surface_v1;
typedef struct vdplet_pixels_v1 {
    uint32_t struct_bytes, format;
    int32_t x, y;
    uint32_t width, height, stride, source_bytes;
    const uint8_t *source;
} vdplet_pixels_v1;
typedef struct vdplet_pcm_config_v1 {
    uint32_t struct_bytes, sample_rate, format, capacity_frames, start_frames;
} vdplet_pcm_config_v1;
typedef struct vdplet_pcm_state_v1 {
    uint32_t struct_bytes, handle, generation, sample_rate, format, capacity_frames,
             queued_frames, free_frames, submitted_frames, consumed_frames, underrun_frames, flags;
} vdplet_pcm_state_v1;
#endif
