; Wolf3D eZ80 authoritative gameplay-world contracts.
;
; Multi-byte values are little-endian in memory. Public world positions are
; signed 16.16, but valid level coordinates are always non-negative and below
; 64 tiles.

W3D_MAP_SIZE:               equ 64
W3D_MAP_BYTES:              equ W3D_MAP_SIZE*W3D_MAP_SIZE
W3D_NUM_AREAS:              equ 37
W3D_MAX_ACTORS:             equ 150
W3D_MAX_DOORS:              equ 64
W3D_MAX_STATICS:            equ 400
W3D_TILE_GLOBAL:            equ 010000h
W3D_MIN_ACTOR_DISTANCE:     equ 010000h

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

W3D_SLOT_NONE:              equ 0ffh

; Original objtype flag values. Render visibility remains VDP-owned, but the
; bit positions stay source-compatible for gameplay/state transitions.
W3D_ACTOR_FLAG_SHOOTABLE:    equ 001h
W3D_ACTOR_FLAG_BONUS:        equ 002h
W3D_ACTOR_FLAG_NEVERMARK:    equ 004h
W3D_ACTOR_FLAG_VISIBLE:      equ 008h
W3D_ACTOR_FLAG_ATTACKMODE:   equ 010h
W3D_ACTOR_FLAG_FIRSTATTACK:  equ 020h
W3D_ACTOR_FLAG_AMBUSH:       equ 040h
W3D_ACTOR_FLAG_NONMARK:      equ 080h

W3D_ACTOR_ACTIVE_NO:         equ 0
W3D_ACTOR_ACTIVE_YES:        equ 1
W3D_ACTOR_ACTIVE_ALWAYS:     equ 2
W3D_ACTOR_ACTIVE_FREE:       equ 0ffh

W3D_ACTOR_DIRTY_NONE:        equ 0
W3D_ACTOR_DIRTY_SET:         equ 1
W3D_ACTOR_DIRTY_REMOVE:      equ 2

; Original non-SPEAR classtype values used by movement/action dispatch.
W3D_CLASS_NOTHING:           equ 0
W3D_CLASS_PLAYER:            equ 1
W3D_CLASS_INERT:             equ 2
W3D_CLASS_GUARD:             equ 3
W3D_CLASS_OFFICER:           equ 4
W3D_CLASS_SS:                equ 5
W3D_CLASS_DOG:               equ 6
W3D_CLASS_BOSS:              equ 7
W3D_CLASS_SCHABBS:           equ 8
W3D_CLASS_FAKE:              equ 9
W3D_CLASS_MECHA_HITLER:      equ 10
W3D_CLASS_MUTANT:            equ 11
W3D_CLASS_GHOST:             equ 15

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
W3D_DOOR_WIRE_SIZE:         equ 8
W3D_DOOR_AREA1:             equ 8       ; uint8 eZ80-only area endpoint
W3D_DOOR_AREA2:             equ 9       ; uint8 eZ80-only area endpoint
W3D_DOOR_SIZE:              equ 10

; Compact eZ80-owned statobj record.  This preserves the mutable fields from
; the original statobj_t while omitting its render-visibility pointer (the VDP
; owns visibility).  The first five bytes are exactly the set_static wire
; payload after its uint16 slot index; itemnumber remains local gameplay state.
W3D_STATIC_TILEX:           equ 0       ; uint8
W3D_STATIC_TILEY:           equ 1       ; uint8
W3D_STATIC_SHAPENUM:        equ 2       ; int16; -1 means removed
W3D_STATIC_FLAGS:           equ 4       ; uint8; original FL_* bits
W3D_STATIC_ITEMNUMBER:      equ 5       ; uint8; original stat_t value
W3D_STATIC_WIRE_SIZE:       equ 5
W3D_STATIC_SIZE:            equ 6

W3D_STATIC_FLAG_BONUS:     equ 2       ; original FL_BONUS

; Original non-SPEAR stat_t values used by pickup dispatch.  Dressing and
; block records are never collectible; blocking itself lives in a separate
; immutable 64x64 occupancy bitset because both have wire flags == 0.
W3D_ITEM_DRESSING:          equ 0
W3D_ITEM_BLOCK:             equ 1
W3D_ITEM_GIBS:              equ 2
W3D_ITEM_ALPO:              equ 3
W3D_ITEM_FIRSTAID:          equ 4
W3D_ITEM_KEY1:              equ 5
W3D_ITEM_KEY2:              equ 6
W3D_ITEM_KEY3:              equ 7
W3D_ITEM_KEY4:              equ 8
W3D_ITEM_CROSS:             equ 9
W3D_ITEM_CHALICE:           equ 10
W3D_ITEM_BIBLE:             equ 11
W3D_ITEM_CROWN:             equ 12
W3D_ITEM_CLIP:              equ 13
W3D_ITEM_CLIP2:             equ 14
W3D_ITEM_MACHINEGUN:        equ 15
W3D_ITEM_CHAINGUN:          equ 16
W3D_ITEM_FOOD:              equ 17
W3D_ITEM_FULLHEAL:          equ 18

; Fixed authoritative objtype pool record. The first twelve bytes deliberately
; preserve the already-regressed W3D_SIGHT_ACTOR_* ABI, so IX may point at a
; live actor directly for CheckLine/CheckSight. State is a uint16 table id,
; not a 24-bit pointer; stable byte slot ids replace the original next/prev
; pointers and map exactly to VDP actorId. Slot zero remains reserved for the
; player, while 1..149 are reusable actor slots.
W3D_ACTOR_X:                equ 0       ; int32 signed 16.16
W3D_ACTOR_Y:                equ 4       ; int32 signed 16.16
W3D_ACTOR_TILEX:            equ 8       ; uint8 cached/reserved destination
W3D_ACTOR_TILEY:            equ 9       ; uint8 cached/reserved destination
W3D_ACTOR_AREA:             equ 10      ; uint8
W3D_ACTOR_DIR:              equ 11      ; uint8 W3D_DIR_*
W3D_ACTOR_ACTIVE:           equ 12      ; W3D_ACTOR_ACTIVE_* / 0xff free
W3D_ACTOR_CLASS:            equ 13      ; uint8 original classtype
W3D_ACTOR_FLAGS:            equ 14      ; uint8 original FL_* bits
W3D_ACTOR_TICCOUNT:         equ 15      ; int16 original 70-Hz state tics
W3D_ACTOR_STATE:            equ 17      ; uint16 W3D_STATE_* id
W3D_ACTOR_DISTANCE:         equ 19      ; int32 16.16 / negative door wait
W3D_ACTOR_ANGLE:            equ 23      ; int16 continuous world degrees
W3D_ACTOR_HITPOINTS:        equ 25      ; int16
W3D_ACTOR_SPEED:            equ 27      ; int32 original units per 70-Hz tic
W3D_ACTOR_TEMP1:            equ 31      ; int16
W3D_ACTOR_TEMP2:            equ 33      ; int16
W3D_ACTOR_TEMP3:            equ 35      ; int16
W3D_ACTOR_NEXT:             equ 37      ; uint8 live slot / 0xff
W3D_ACTOR_PREV:             equ 38      ; uint8 live predecessor/free link
W3D_ACTOR_SIZE:             equ 39

W3D_SIGHT_ACTOR_X:          equ W3D_ACTOR_X
W3D_SIGHT_ACTOR_Y:          equ W3D_ACTOR_Y
W3D_SIGHT_ACTOR_TILEX:      equ W3D_ACTOR_TILEX
W3D_SIGHT_ACTOR_TILEY:      equ W3D_ACTOR_TILEY
W3D_SIGHT_ACTOR_AREA:       equ W3D_ACTOR_AREA
W3D_SIGHT_ACTOR_DIR:        equ W3D_ACTOR_DIR
W3D_SIGHT_ACTOR_SIZE:       equ 12

; Stable actor state ids. Zero is reserved as invalid/free; generated map
; seeds use the initial subset while the runner owns the complete path chains.
W3D_STATE_GRD_STAND:        equ 1
W3D_STATE_GRD_PATH1:        equ 2
W3D_STATE_DOG_PATH1:        equ 3
W3D_STATE_OFC_STAND:        equ 4
W3D_STATE_OFC_PATH1:        equ 5
W3D_STATE_MUT_STAND:        equ 6
W3D_STATE_MUT_PATH1:        equ 7
W3D_STATE_SS_STAND:         equ 8
W3D_STATE_SS_PATH1:         equ 9
W3D_STATE_GRD_DEAD:         equ 10
W3D_STATE_BLINKY_CHASE1:    equ 11
W3D_STATE_CLYDE_CHASE1:     equ 12
W3D_STATE_PINKY_CHASE1:     equ 13
W3D_STATE_INKY_CHASE1:      equ 14
W3D_STATE_BOSS_STAND:       equ 15
W3D_STATE_GRETEL_STAND:     equ 16
W3D_STATE_SCHABBS_STAND:    equ 17
W3D_STATE_GIFT_STAND:       equ 18
W3D_STATE_FAT_STAND:        equ 19
W3D_STATE_FAKE_STAND:       equ 20
W3D_STATE_MECHA_STAND:      equ 21
W3D_STATE_GRD_PATH1S:       equ 22
W3D_STATE_GRD_PATH2:        equ 23
W3D_STATE_GRD_PATH3:        equ 24
W3D_STATE_GRD_PATH3S:       equ 25
W3D_STATE_GRD_PATH4:        equ 26
W3D_STATE_DOG_PATH1S:       equ 27
W3D_STATE_DOG_PATH2:        equ 28
W3D_STATE_DOG_PATH3:        equ 29
W3D_STATE_DOG_PATH3S:       equ 30
W3D_STATE_DOG_PATH4:        equ 31
W3D_STATE_OFC_PATH1S:       equ 32
W3D_STATE_OFC_PATH2:        equ 33
W3D_STATE_OFC_PATH3:        equ 34
W3D_STATE_OFC_PATH3S:       equ 35
W3D_STATE_OFC_PATH4:        equ 36
W3D_STATE_MUT_PATH1S:       equ 37
W3D_STATE_MUT_PATH2:        equ 38
W3D_STATE_MUT_PATH3:        equ 39
W3D_STATE_MUT_PATH3S:       equ 40
W3D_STATE_MUT_PATH4:        equ 41
W3D_STATE_SS_PATH1S:        equ 42
W3D_STATE_SS_PATH2:         equ 43
W3D_STATE_SS_PATH3:         equ 44
W3D_STATE_SS_PATH3S:        equ 45
W3D_STATE_SS_PATH4:         equ 46
; First combat states retain their awareness-assigned stable ids. Remaining
; ordinary chase frames append after them so generated actor records and
; FirstSighting targets never need renumbering.
W3D_STATE_GRD_CHASE1:       equ 47
W3D_STATE_DOG_CHASE1:       equ 48
W3D_STATE_OFC_CHASE1:       equ 49
W3D_STATE_MUT_CHASE1:       equ 50
W3D_STATE_SS_CHASE1:        equ 51
W3D_STATE_GRD_CHASE1S:      equ 52
W3D_STATE_GRD_CHASE2:       equ 53
W3D_STATE_GRD_CHASE3:       equ 54
W3D_STATE_GRD_CHASE3S:      equ 55
W3D_STATE_GRD_CHASE4:       equ 56
W3D_STATE_DOG_CHASE1S:      equ 57
W3D_STATE_DOG_CHASE2:       equ 58
W3D_STATE_DOG_CHASE3:       equ 59
W3D_STATE_DOG_CHASE3S:      equ 60
W3D_STATE_DOG_CHASE4:       equ 61
W3D_STATE_OFC_CHASE1S:      equ 62
W3D_STATE_OFC_CHASE2:       equ 63
W3D_STATE_OFC_CHASE3:       equ 64
W3D_STATE_OFC_CHASE3S:      equ 65
W3D_STATE_OFC_CHASE4:       equ 66
W3D_STATE_MUT_CHASE1S:      equ 67
W3D_STATE_MUT_CHASE2:       equ 68
W3D_STATE_MUT_CHASE3:       equ 69
W3D_STATE_MUT_CHASE3S:      equ 70
W3D_STATE_MUT_CHASE4:       equ 71
W3D_STATE_SS_CHASE1S:       equ 72
W3D_STATE_SS_CHASE2:        equ 73
W3D_STATE_SS_CHASE3:        equ 74
W3D_STATE_SS_CHASE3S:       equ 75
W3D_STATE_SS_CHASE4:        equ 76
; Ordinary ranged/dog attack chains append after every stable awareness and
; chase id. NEXT remains a byte in this compact slice; ids through 100 are
; therefore safe, while the complete >255-state WL1 graph will require an ABI
; widening or per-level remap before bosses, projectiles, pain and death are
; all installed.
W3D_STATE_GRD_SHOOT1:       equ 77
W3D_STATE_GRD_SHOOT2:       equ 78
W3D_STATE_GRD_SHOOT3:       equ 79
W3D_STATE_DOG_JUMP1:        equ 80
W3D_STATE_DOG_JUMP2:        equ 81
W3D_STATE_DOG_JUMP3:        equ 82
W3D_STATE_DOG_JUMP4:        equ 83
W3D_STATE_DOG_JUMP5:        equ 84
W3D_STATE_OFC_SHOOT1:       equ 85
W3D_STATE_OFC_SHOOT2:       equ 86
W3D_STATE_OFC_SHOOT3:       equ 87
W3D_STATE_MUT_SHOOT1:       equ 88
W3D_STATE_MUT_SHOOT2:       equ 89
W3D_STATE_MUT_SHOOT3:       equ 90
W3D_STATE_MUT_SHOOT4:       equ 91
W3D_STATE_SS_SHOOT1:        equ 92
W3D_STATE_SS_SHOOT2:        equ 93
W3D_STATE_SS_SHOOT3:        equ 94
W3D_STATE_SS_SHOOT4:        equ 95
W3D_STATE_SS_SHOOT5:        equ 96
W3D_STATE_SS_SHOOT6:        equ 97
W3D_STATE_SS_SHOOT7:        equ 98
W3D_STATE_SS_SHOOT8:        equ 99
W3D_STATE_SS_SHOOT9:        equ 100
W3D_STATE_COUNT:            equ 101

W3D_STATE_THINK_NONE:       equ 0
W3D_STATE_THINK_PATH:       equ 1
W3D_STATE_THINK_STAND:      equ 2
W3D_STATE_THINK_CHASE:      equ 3
W3D_STATE_THINK_DOG_CHASE:  equ 4
W3D_STATE_ACTION_NONE:      equ 0
W3D_STATE_ACTION_SHOOT:     equ 1
W3D_STATE_ACTION_BITE:      equ 2

; Chase movement exposes attack transitions as small return values; the state
; runner consumes them immediately by installing the class-specific shooting
; or dog-jump chain. Keeping this seam explicit makes movement independently
; regressible without duplicating NewState/action behavior inside T_Chase.
W3D_CHASE_RESULT_NONE:      equ 0
W3D_CHASE_RESULT_RANGED:    equ 1
W3D_CHASE_RESULT_DOG_JUMP:  equ 2
W3D_CHASE_RESULT_CORRUPT:   equ 0ffh

; Compact state table. Function pointers remain local dispatch ids so table
; records and actor state survive code movement and generated fixtures.
W3D_STATE_SHAPENUM:         equ 0       ; int16 base shape; -1 uses temp1
W3D_STATE_ROTATIONS:        equ 2       ; uint8 0,2,8
W3D_STATE_TICTIME:          equ 3       ; uint16 original 70-Hz tics
W3D_STATE_THINK:            equ 5       ; uint8 W3D_STATE_THINK_*
W3D_STATE_ACTION:           equ 6       ; uint8 W3D_STATE_ACTION_*
W3D_STATE_NEXT:             equ 7       ; uint8 W3D_STATE_* / 0 removes
W3D_STATE_SIZE:             equ 8

; Durable set_actor render payload (including uint16 actorId). Gameplay-only
; tile/HP/flags never cross the write-only VDP boundary.
W3D_ACTOR_WIRE_ID:          equ 0       ; uint16
W3D_ACTOR_WIRE_SHAPENUM:    equ 2       ; int16 base shape
W3D_ACTOR_WIRE_X:           equ 4       ; int32
W3D_ACTOR_WIRE_Y:           equ 8       ; int32
W3D_ACTOR_WIRE_FACING:      equ 12      ; uint16 east=0, north=90
W3D_ACTOR_WIRE_ROTATIONS:   equ 14      ; uint8 0,2,8
W3D_ACTOR_WIRE_SIZE:        equ 15

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
