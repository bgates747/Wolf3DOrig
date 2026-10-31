#ifndef WOLF3D_VDPLET_SCENE_ROWS_CONTRACT_H
#define WOLF3D_VDPLET_SCENE_ROWS_CONTRACT_H

#include "wolf3d_scene_contract.h"

// Optional ABI1.6 direct-row candidate. Row pointers are native-width values
// because the exact source also runs in the 64-bit host qualifier. The real
// classic ESP32 target has 32-bit pointers and therefore needs exactly 11,552
// bytes; the host qualifier naturally needs 12,512 bytes.
#define W3V_ROW_POINTER_OFFSET 0u
#define W3V_ROW_POINTER_BYTES  (W3V_SCREEN_HEIGHT * sizeof(uintptr_t))
#define W3V_DIRECT_WALL_HEIGHT_OFFSET W3V_ROW_POINTER_BYTES
#define W3V_DIRECT_WALL_HEIGHT_BYTES  W3V_WALL_HEIGHT_BYTES
#define W3V_DIRECT_WALL_TILE_OFFSET \
    (W3V_DIRECT_WALL_HEIGHT_OFFSET + W3V_DIRECT_WALL_HEIGHT_BYTES)
#define W3V_DIRECT_WALL_TEXU_OFFSET \
    (W3V_DIRECT_WALL_TILE_OFFSET + W3V_VIEW_WIDTH)
#define W3V_DIRECT_WALL_SIDE_OFFSET \
    (W3V_DIRECT_WALL_TEXU_OFFSET + W3V_VIEW_WIDTH)
#define W3V_DIRECT_SPRITE_ARENA_OFFSET \
    (W3V_DIRECT_WALL_SIDE_OFFSET + W3V_VIEW_WIDTH)
#define W3V_DIRECT_WORKSPACE_BYTES \
    (W3V_DIRECT_SPRITE_ARENA_OFFSET + W3V_SPRITE_ARENA_BYTES)
#define W3V_DIRECT_TARGET_WORKSPACE_BYTES 11552u

#endif
