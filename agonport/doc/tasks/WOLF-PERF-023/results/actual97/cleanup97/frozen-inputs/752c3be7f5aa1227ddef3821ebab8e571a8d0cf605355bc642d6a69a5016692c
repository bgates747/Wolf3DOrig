#ifndef AGON_VDPLET_POLICY_H
#define AGON_VDPLET_POLICY_H
/* Admission ceilings, not guarantees of currently available contiguous memory. */
#define VDPL_MAX_TEXT 65536u
#define VDPL_TEXT96_MAX_TEXT 98304u
/* Explicit experimental build profile; ordinary policy remains 64 KiB. */
#ifndef VDPL_TEXT96
#define VDPL_TEXT96 0
#endif
#if VDPL_TEXT96 != 0 && VDPL_TEXT96 != 1
#error "VDPL_TEXT96 must be 0 or 1"
#endif
#if VDPL_TEXT96
#define VDPL_TEXT_CEILING VDPL_TEXT96_MAX_TEXT
#else
#define VDPL_TEXT_CEILING VDPL_MAX_TEXT
#endif
#define VDPL_MAX_DATA 16384u
#define VDPL_MAX_IMAGE 131072u
#define VDPL_MAX_STACK 2048u
#define VDPL_DEFAULT_TEXT 32768u
#define VDPL_DEFAULT_DATA 4096u
#define VDPL_DEFAULT_IMAGE 65536u
#define VDPL_DEFAULT_STACK 2048u
#endif
