#ifndef AGON_VDPLET_PCM_SINK_H
#define AGON_VDPLET_PCM_SINK_H
#include <stdint.h>
#define VDPL_SINK_DISCOVER 0u
#define VDPL_SINK_OPEN 1u
#define VDPL_SINK_WRITE 2u
#define VDPL_SINK_STATE 3u
#define VDPL_SINK_RESET 4u
#define VDPL_SINK_MUTE 5u
#define VDPL_SINK_UNMUTE 6u
#define VDPL_SINK_STOP 7u
#define VDPL_SINK_CLOSE 8u
#define VDPL_SINK_OPENED 1u
#define VDPL_SINK_RUNNING 2u
#define VDPL_SINK_MUTED 4u
#define VDPL_SINK_DEFAULT_FRAMES 1024u
#define VDPL_SINK_MAX_FRAMES 8192u
/* OPEN inputs: channel (must be unallocated), sample_rate (0=current), capacity
   (0=1024), start_frames (0=1). Live operations require current generation.
   WRITE inputs samples/frames are copied before return. Outputs replace the
   scalar state fields only; no pointer is retained. All sample counters wrap.
   RESET/STOP/MUTE flush and return a new generation; MUTE refuses writes until
   UNMUTE. DISCOVER is generation-free and returns current output capability. */
typedef struct vdplet_pcm_sink_v1 {
    uint32_t struct_bytes, generation, channel, sample_rate, capacity_frames,
        start_frames, queued_frames, free_frames, accepted_frames,
        consumed_frames, underrun_frames, flags;
    const uint8_t *samples;
    uint32_t frames;
} vdplet_pcm_sink_v1;
#endif
