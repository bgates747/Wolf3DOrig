; Wolf3D eZ80 authoritative gameplay-world contracts.
;
; Multi-byte values are little-endian in memory. Public world positions are
; signed 16.16, but valid level coordinates are always non-negative and below
; 64 tiles.

W3D_MAP_SIZE:               equ 64
W3D_MAP_BYTES:              equ W3D_MAP_SIZE*W3D_MAP_SIZE
W3D_MAX_ACTORS:             equ 150
W3D_MAX_DOORS:              equ 64

W3D_TILE_OPEN:              equ 0x00
W3D_TILE_WALL_MIN:          equ 0x01
W3D_TILE_WALL_MAX:          equ 0x7f
W3D_TILE_DOOR_MIN:          equ 0x80
W3D_TILE_DOOR_MAX:          equ 0xbf
W3D_TILE_DOOR_MASK:         equ 0x7f

; Fixed stock-VDP bitmap-buffer ranges. init_level associates only the
; tilemap buffer; wall and sprite bitmaps are found from these formulas.
W3D_WALL_BUFFER_BASE:       equ 0x1000   ; + texture id 1..127
W3D_SPRITE_BUFFER_BASE:     equ 0x2000   ; + shapenum 0..8191

W3D_DIR_EAST:               equ 0
W3D_DIR_NORTHEAST:          equ 1
W3D_DIR_NORTH:              equ 2
W3D_DIR_NORTHWEST:          equ 3
W3D_DIR_WEST:               equ 4
W3D_DIR_SOUTHWEST:          equ 5
W3D_DIR_SOUTH:              equ 6
W3D_DIR_SOUTHEAST:          equ 7
W3D_DIR_NODIR:              equ 8

W3D_DOOR_ACTION_CLOSED:     equ 0
W3D_DOOR_ACTION_OPENING:    equ 1
W3D_DOOR_ACTION_OPEN:       equ 2
W3D_DOOR_ACTION_CLOSING:    equ 3

; Wolf3dDoor, matching the eZ80-to-VDP wire field order.
W3D_DOOR_TILEX:             equ 0       ; uint8
W3D_DOOR_TILEY:             equ 1       ; uint8
W3D_DOOR_VERTICAL:          equ 2       ; uint8 boolean
W3D_DOOR_LOCK:              equ 3       ; uint8
W3D_DOOR_ACTION:            equ 4       ; uint8
W3D_DOOR_POSITION:          equ 5       ; uint16 unsigned 0.16
W3D_DOOR_TEXTURE_ID:        equ 7       ; uint8 wall-buffer texture id
W3D_DOOR_SIZE:              equ 8

; Minimal stable actor view required by CheckLine/CheckSight. This is named
; explicitly as a sight view rather than prematurely freezing the eventual
; complete gameplay objtype layout.
W3D_SIGHT_ACTOR_X:          equ 0       ; int32 signed 16.16
W3D_SIGHT_ACTOR_Y:          equ 4       ; int32 signed 16.16
W3D_SIGHT_ACTOR_TILEX:      equ 8       ; uint8 cached tile
W3D_SIGHT_ACTOR_TILEY:      equ 9       ; uint8 cached tile
W3D_SIGHT_ACTOR_AREA:       equ 10      ; uint8
W3D_SIGHT_ACTOR_DIR:        equ 11      ; uint8 W3D_DIR_*
W3D_SIGHT_ACTOR_SIZE:       equ 12

; Context passed in IY to the sight routines. Pointers are 24-bit ADL
; addresses. Position fields are int32 signed 16.16.
W3D_SIGHT_CTX_TILEMAP:      equ 0       ; uint24 -> 4096 map bytes
W3D_SIGHT_CTX_DOORS:        equ 3       ; uint24 -> W3D_MAX_DOORS entries
W3D_SIGHT_CTX_AREAS:        equ 6       ; uint24 -> byte connectivity table
W3D_SIGHT_CTX_PLAYER_X:     equ 9       ; int32
W3D_SIGHT_CTX_PLAYER_Y:     equ 13      ; int32
W3D_SIGHT_CTX_MADENOISE:   equ 17      ; uint8 boolean
W3D_SIGHT_CTX_SIZE:         equ 18

; CheckSight's automatic near-distance square: 1.5 tiles in 16.16.
W3D_MIN_SIGHT_16_16:        equ 0x00018000
