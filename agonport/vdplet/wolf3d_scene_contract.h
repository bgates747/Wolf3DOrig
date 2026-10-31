#ifndef WOLF3D_VDPLET_SCENE_CONTRACT_H
#define WOLF3D_VDPLET_SCENE_CONTRACT_H

#include <stdint.h>

// Bounded GOLEM-057 proof contract. This is deliberately separate from the
// production game protocol: the prototype proves the module/resource/render
// boundary before any eZ80 integration is attempted.
#define W3V_CONFIG_MAGIC       0x50443357u  // "W3DP" little endian
#define W3V_CONFIG_BYTES       24u
#define W3V_ENTRY_CONFIG       0u
#define W3V_ENTRY_RENDER       1u

#define W3V_SCREEN_WIDTH       320u
#define W3V_SCREEN_HEIGHT      240u
#define W3V_FRAME_BYTES        (W3V_SCREEN_WIDTH * W3V_SCREEN_HEIGHT)
#define W3V_PLAY_HEIGHT        200u
#define W3V_VIEW_WIDTH         256u
#define W3V_VIEW_HEIGHT        160u
#define W3V_VIEW_X             32u
#define W3V_VIEW_Y             20u

#define W3V_MAP_WIDTH          64u
#define W3V_MAP_HEIGHT         64u
#define W3V_MAP_BYTES          (W3V_MAP_WIDTH * W3V_MAP_HEIGHT)
#define W3V_TEXTURE_SIZE       64u
#define W3V_TEXTURE_BYTES      (W3V_TEXTURE_SIZE * W3V_TEXTURE_SIZE)
#define W3V_TEXTURE_SET_BYTES  (2u * W3V_TEXTURE_BYTES)

// Frame + actual column scratch + a reserved 8,800-byte sprite arena and
// alignment/headroom. The bounded proof uses one sprite, but deliberately
// allocates the feasibility study's full approximately-90-KiB workspace.
#define W3V_WALL_HEIGHT_OFFSET W3V_FRAME_BYTES
#define W3V_WALL_HEIGHT_BYTES  (W3V_VIEW_WIDTH * 4u)
#define W3V_WALL_TILE_OFFSET   (W3V_WALL_HEIGHT_OFFSET + W3V_WALL_HEIGHT_BYTES)
#define W3V_WALL_TEXU_OFFSET   (W3V_WALL_TILE_OFFSET + W3V_VIEW_WIDTH)
#define W3V_WALL_SIDE_OFFSET   (W3V_WALL_TEXU_OFFSET + W3V_VIEW_WIDTH)
#define W3V_SPRITE_ARENA_OFFSET (W3V_WALL_SIDE_OFFSET + W3V_VIEW_WIDTH)
#define W3V_SPRITE_ARENA_BYTES 8800u
#define W3V_WORKSPACE_BYTES    92160u

// Config bytes, little endian:
//   0 magic:u32, 4 workspace:u16, 6 map:u16, 8 textures:u16,
//  10 angle:i16, 12 player_x:i32, 16 player_y:i32,
//  20 static_tile_x:u8, 21 static_tile_y:u8, 22 reserved:u16.

#endif
