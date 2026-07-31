; Direct real-eZ80 regression for production Wolf3D ordinary chase movement.
;
; This fixture supplies synthetic actor/world inputs and literal expected
; outputs. Every decision calls production labels in wolf3d_actor_sim.inc;
; no selector, attack, door, or movement algorithm is copied here.

    assume adl=1
    org 0x040000
    jp start
    align 64
    db "MOS",0,1

mos_fopen:          equ 0x0a
mos_fclose:         equ 0x0b
mos_fwrite:         equ 0x1b
mos_getkbmap:       equ 0x1e
fa_write:           equ 0x02
fa_create_always:   equ 0x08

; PRT1: 18.432 MHz / 256 / 72 = 1 kHz, hardware-compatible.
prt_reload_1ms:     equ 72
TMR1_CTL:           equ 083h
TMR_REG_CTL:        equ 0
TMR_RES_LOW:        equ 1
TMR_RES_HIGH:       equ 2
PRT_OFF:            equ %00001110
PRT_ON:             equ %01011111
timing_iterations:  equ 10000

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    macro CHECK_A expected, why
        ld b,expected
        ld c,why
        call assert_equal
    endmacro

    macro CHECK_IX8 offset, expected, why
        ld a,(ix+offset)
        ld b,expected
        ld c,why
        call assert_equal
    endmacro

    macro CHECK_MEM8 address, expected, why
        ld a,(address)
        ld b,expected
        ld c,why
        call assert_equal
    endmacro

    macro CHECK_IX32 offset, b0, b1, b2, b3, why
        CHECK_IX8 offset+0,b0,why
        CHECK_IX8 offset+1,b1,why
        CHECK_IX8 offset+2,b2,why
        CHECK_IX8 offset+3,b3,why
    endmacro

    include "wolf3d_sight.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_actors.inc"
    include "wolf3d_areas.inc"
    include "wolf3d_actor_sim.inc"
    include "wolf3d_motion.inc"
    include "wolf3d_player_combat.inc"

phase_chase_select:     equ 1
phase_dodge_select:     equ 2
phase_ranged:           equ 3
phase_motion:           equ 4
phase_doors_occupancy:  equ 5
phase_dog:              equ 6
phase_containment:      equ 7
phase_scheduler_states: equ 8
phase_timing:           equ 9
phase_count:            equ 9

reason_scalar:          equ 1
reason_direction_tile:  equ 2
reason_rng:             equ 3
reason_flags:           equ 4
reason_pose:            equ 5
reason_distance:        equ 6
reason_door:            equ 7
reason_occupancy:       equ 8
reason_area_player:     equ 9
reason_containment:     equ 10
reason_clock:           equ 11
reason_actor_record:    equ 12

cell_center:    equ 20*64+20
cell_east:      equ 20*64+21
cell_northeast:equ 19*64+21
cell_north:     equ 19*64+20
cell_northwest:equ 19*64+19
cell_west:      equ 20*64+19
cell_southwest:equ 21*64+19
cell_south:     equ 21*64+20
cell_southeast:equ 21*64+21

start:
    push af
    push bc
    push de
    push ix
    push iy
    call run_tests
    pop iy
    pop ix
    pop de
    pop bc
    pop af
    ld hl,0
    ret

run_tests:
    xor a
    ld hl,result_checks
    ld (hl),a
    ld de,result_checks+1
    ld bc,result_end-result_checks-1
    ldir
    ld a,1
    ld (result_schema),a
    call prt_irq_install
    call test_select_chase
    call test_select_dodge
    call test_ranged_requests
    call test_motion_and_residual
    call test_doors_and_occupancy
    call test_dog_chase
    call test_corrupt_containment
    call test_state_table_and_scheduler
    call time_chase_paths
    call prt_irq_restore
    call write_result
    call print_report
    ret

; ---------------------------------------------------------------------------
; Case 1: SelectChaseDir direct, old, reversal, fallback threshold, trapped.
; ---------------------------------------------------------------------------

test_select_chase:
    ld a,phase_chase_select
    ld (test_phase),a

; Larger X delta wins directly and consumes no RNG.
    ld a,1
    ld (test_detail),a
    call prepare_center_guard
    ld hl,0188000h                   ; player (24.5,22.5)
    ld de,0168000h
    call set_player_xy
    ld a,42
    ld (w3d_random_index),a
    call w3d_actor_select_chase_dir
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_EAST,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEX,21,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEY,20,reason_direction_tile
    CHECK_IX32 W3D_ACTOR_DISTANCE,0,0,1,0,reason_distance
    CHECK_MEM8 w3d_random_index,42,reason_rng

; If the direct direction is blocked, the old direction precedes fallback.
    ld a,2
    ld (test_detail),a
    call prepare_center_guard
    ld a,W3D_DIR_NORTH
    ld (ix+W3D_ACTOR_DIR),a
    ld a,1
    ld (test_tilemap+cell_east),a
    ld a,42
    ld (w3d_random_index),a
    call w3d_actor_select_chase_dir
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_NORTH,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEX,20,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEY,19,reason_direction_tile
    CHECK_MEM8 w3d_random_index,42,reason_rng

; 128 selects W first; 129 selects N first. E is the blocked direct path.
    ld a,3
    ld (test_detail),a
    call prepare_center_guard
    ld a,1
    ld (test_tilemap+cell_east),a
    ld a,22                            ; next byte table[23] = 128
    ld (w3d_random_index),a
    call w3d_actor_select_chase_dir
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_WEST,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEX,19,reason_direction_tile
    CHECK_MEM8 w3d_random_index,23,reason_rng

    ld a,4
    ld (test_detail),a
    call prepare_center_guard
    ld a,1
    ld (test_tilemap+cell_east),a
    ld a,159                           ; next byte table[160] = 129
    ld (w3d_random_index),a
    call w3d_actor_select_chase_dir
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_NORTH,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEY,19,reason_direction_tile
    CHECK_MEM8 w3d_random_index,160,reason_rng

; Reversal is suppressed until every other candidate fails.
    ld a,5
    ld (test_detail),a
    call prepare_center_guard
    call block_all_neighbors
    xor a
    ld (test_tilemap+cell_east),a
    ld a,W3D_DIR_WEST
    ld (ix+W3D_ACTOR_DIR),a
    ld a,37                            ; next byte = 200
    ld (w3d_random_index),a
    call w3d_actor_select_chase_dir
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_EAST,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEX,21,reason_direction_tile
    CHECK_MEM8 w3d_random_index,38,reason_rng

; A surrounded actor returns zero/nodir after exactly one fallback byte.
    ld a,6
    ld (test_detail),a
    call prepare_center_guard
    call block_all_neighbors
    ld a,37
    ld (w3d_random_index),a
    call w3d_actor_select_chase_dir
    CHECK_A 0,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_NODIR,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEX,20,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEY,20,reason_direction_tile
    CHECK_MEM8 w3d_random_index,38,reason_rng
    ret

; ---------------------------------------------------------------------------
; Case 2: SelectDodgeDir symmetric diagonal, random boundary, FIRSTATTACK.
; ---------------------------------------------------------------------------

test_select_dodge:
    ld a,phase_dodge_select
    ld (test_phase),a

; abs(dx)>abs(dy) places vertical first; symmetric table must still yield NE.
    ld a,1
    ld (test_detail),a
    call prepare_center_guard
    ld hl,0188000h                   ; (24.5,18.5)
    ld de,0128000h
    call set_player_xy
    ld a,37                            ; 200, no random swap
    ld (w3d_random_index),a
    call w3d_actor_select_dodge_dir
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_NORTHEAST,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEX,21,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEY,19,reason_direction_tile
    CHECK_MEM8 w3d_random_index,38,reason_rng

; With NE blocked, native below-boundary 123 chooses N; 128 chooses E.
    ld a,2
    ld (test_detail),a
    call prepare_center_guard
    ld hl,0168000h                   ; (22.5,18.5), equal deltas
    ld de,0128000h
    call set_player_xy
    ld a,1
    ld (test_tilemap+cell_northeast),a
    ld a,197                           ; next byte table[198] = 123
    ld (w3d_random_index),a
    call w3d_actor_select_dodge_dir
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_NORTH,reason_direction_tile
    CHECK_MEM8 w3d_random_index,198,reason_rng

    ld a,3
    ld (test_detail),a
    call prepare_center_guard
    ld hl,0168000h
    ld de,0128000h
    call set_player_xy
    ld a,1
    ld (test_tilemap+cell_northeast),a
    ld a,22                            ; next 128: no swap
    ld (w3d_random_index),a
    call w3d_actor_select_dodge_dir
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_EAST,reason_direction_tile
    CHECK_MEM8 w3d_random_index,23,reason_rng

; Without FIRSTATTACK, east is reversal and south wins. With it, east wins.
    ld a,4
    ld (test_detail),a
    call prepare_firstattack_geometry
    ld a,W3D_ACTOR_FLAG_SHOOTABLE
    ld (ix+W3D_ACTOR_FLAGS),a
    ld a,37
    ld (w3d_random_index),a
    call w3d_actor_select_dodge_dir
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_SOUTH,reason_direction_tile
    CHECK_MEM8 w3d_random_index,38,reason_rng

    ld a,5
    ld (test_detail),a
    call prepare_firstattack_geometry
    ld a,W3D_ACTOR_FLAG_SHOOTABLE|W3D_ACTOR_FLAG_FIRSTATTACK
    ld (ix+W3D_ACTOR_FLAGS),a
    ld a,37
    ld (w3d_random_index),a
    call w3d_actor_select_dodge_dir
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_EAST,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_FLAGS,W3D_ACTOR_FLAG_SHOOTABLE,reason_flags
    CHECK_MEM8 w3d_random_index,38,reason_rng

; Same-tile deltas preserve the source's west/north bias -> NW.
    ld a,6
    ld (test_detail),a
    call prepare_center_guard
    ld hl,0148000h
    ld de,0148000h
    call set_player_xy
    ld a,37
    ld (w3d_random_index),a
    call w3d_actor_select_dodge_dir
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_NORTHWEST,reason_direction_tile
    CHECK_MEM8 w3d_random_index,38,reason_rng
    ret

; ---------------------------------------------------------------------------
; Case 3: CheckLine/ranged chance and exact RNG/request seam behavior.
; ---------------------------------------------------------------------------

test_ranged_requests:
    ld a,phase_ranged
    ld (test_phase),a

; Dist=4,tics=2 => chance 8. Roll 7 requests and preserves all 39 bytes.
    ld a,1
    ld (test_detail),a
    call prepare_center_guard
    ld a,W3D_DIR_EAST
    ld (ix+W3D_ACTOR_DIR),a
    call save_actor_record
    ld a,156                           ; next byte table[157] = 7
    ld (w3d_random_index),a
    call w3d_actor_think_chase
    CHECK_A W3D_CHASE_RESULT_RANGED,reason_scalar
    CHECK_MEM8 w3d_random_index,157,reason_rng
    call assert_actor_record_unchanged

; Roll exactly 8 fails the strict comparison; speed zero isolates the seam.
    ld a,2
    ld (test_detail),a
    call prepare_center_guard
    ld a,W3D_DIR_EAST
    ld (ix+W3D_ACTOR_DIR),a
    xor a
    ld (ix+W3D_ACTOR_SPEED+0),a
    ld (ix+W3D_ACTOR_SPEED+1),a
    ld a,0                             ; next byte table[1] = 8
    ld (w3d_random_index),a
    call w3d_actor_think_chase
    CHECK_A W3D_CHASE_RESULT_NONE,reason_scalar
    CHECK_MEM8 w3d_actor_chase_dodge,1,reason_scalar
    CHECK_MEM8 w3d_random_index,1,reason_rng

; Adjacent signed distance below 0x4000 uses chance 300 but consumes byte 255.
    ld a,3
    ld (test_detail),a
    call prepare_center_guard
    ld hl,0158000h                   ; player (21.5,20.5)
    ld de,0148000h
    call set_player_xy
    ld a,W3D_DIR_EAST
    ld (ix+W3D_ACTOR_DIR),a
    ld (ix+W3D_ACTOR_DISTANCE+0),0ffh
    ld (ix+W3D_ACTOR_DISTANCE+1),03fh
    xor a
    ld (ix+W3D_ACTOR_DISTANCE+2),a
    ld (ix+W3D_ACTOR_DISTANCE+3),a
    ld a,157                           ; next byte table[158] = 255
    ld (w3d_random_index),a
    call w3d_actor_think_chase
    CHECK_A W3D_CHASE_RESULT_RANGED,reason_scalar
    CHECK_MEM8 w3d_random_index,158,reason_rng

; A blocked CheckLine consumes no attack byte.
    ld a,4
    ld (test_detail),a
    call prepare_center_guard
    ld a,W3D_DIR_EAST
    ld (ix+W3D_ACTOR_DIR),a
    xor a
    ld (ix+W3D_ACTOR_SPEED+0),a
    ld (ix+W3D_ACTOR_SPEED+1),a
    ld a,1
    ld (test_tilemap+1302),a
    ld a,37
    ld (w3d_random_index),a
    call w3d_actor_think_chase
    CHECK_A W3D_CHASE_RESULT_NONE,reason_scalar
    CHECK_MEM8 w3d_random_index,37,reason_rng

; Failed shot with NODIR consumes a second byte in SelectDodgeDir and clears
; FIRSTATTACK. Native bytes are 205 then 128 from start index 21.
    ld a,5
    ld (test_detail),a
    call prepare_center_guard
    xor a
    ld (ix+W3D_ACTOR_SPEED+0),a
    ld (ix+W3D_ACTOR_SPEED+1),a
    ld a,W3D_ACTOR_FLAG_SHOOTABLE|W3D_ACTOR_FLAG_FIRSTATTACK
    ld (ix+W3D_ACTOR_FLAGS),a
    ld a,21
    ld (w3d_random_index),a
    call w3d_actor_think_chase
    CHECK_A W3D_CHASE_RESULT_NONE,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_NORTHEAST,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEX,21,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEY,19,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_FLAGS,W3D_ACTOR_FLAG_SHOOTABLE,reason_flags
    CHECK_MEM8 w3d_random_index,23,reason_rng
    ret

; ---------------------------------------------------------------------------
; Case 4: exact budgets, equality, residual crossing, persistent dodge mode.
; ---------------------------------------------------------------------------

test_motion_and_residual:
    ld a,phase_motion
    ld (test_phase),a

; Three direct thinks using caller-supplied 2,2,3 advance 512*7 units.
    ld a,1
    ld (test_detail),a
    call prepare_east_leg_guard
    ld hl,01e8000h                   ; player (30.5,20.5)
    ld de,0148000h
    call set_player_xy
    ld a,1
    ld (test_tilemap+1302),a           ; line blocked, destination 21 clear
    ld a,42
    ld (w3d_random_index),a
    ld a,2
    ld (w3d_actor_frame_tics),a
    call w3d_actor_think_chase
    call w3d_actor_think_chase
    ld a,3
    ld (w3d_actor_frame_tics),a
    call w3d_actor_think_chase
    CHECK_IX32 W3D_ACTOR_X,0,08eh,014h,0,reason_pose
    CHECK_IX32 W3D_ACTOR_Y,0,080h,014h,0,reason_pose
    CHECK_IX32 W3D_ACTOR_DISTANCE,0,0f2h,0,0,reason_distance
    CHECK_MEM8 w3d_random_index,42,reason_rng

; Budget 3000 reaches a center after 512, then continues 2488 north.
    ld a,2
    ld (test_detail),a
    call prepare_east_leg_guard
    ld hl,0158000h                   ; player (21.5,15.5)
    ld de,00f8000h
    call set_player_xy
    ld a,1
    ld (test_tilemap+1109),a           ; block line without blocking north step
    ld hl,0157e00h
    ld (ix+W3D_ACTOR_X),hl
    ld (ix+W3D_ACTOR_X+3),0
    ld (ix+W3D_ACTOR_DISTANCE+0),0
    ld (ix+W3D_ACTOR_DISTANCE+1),2
    ld (ix+W3D_ACTOR_DISTANCE+2),0
    ld (ix+W3D_ACTOR_DISTANCE+3),0
    ld hl,1500
    ld (ix+W3D_ACTOR_SPEED),hl
    ld (ix+W3D_ACTOR_SPEED+3),0
    ld a,2
    ld (w3d_actor_frame_tics),a
    call w3d_actor_think_chase
    CHECK_A W3D_CHASE_RESULT_NONE,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_NORTH,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEX,21,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEY,19,reason_direction_tile
    CHECK_IX32 W3D_ACTOR_X,0,080h,015h,0,reason_pose
    CHECK_IX32 W3D_ACTOR_Y,048h,076h,014h,0,reason_pose
    CHECK_IX32 W3D_ACTOR_DISTANCE,048h,0f6h,0,0,reason_distance

; move == distance still snaps and reserves the next leg with zero residual.
    ld a,3
    ld (test_detail),a
    call prepare_exact_center_crossing
    call w3d_actor_think_chase
    CHECK_A W3D_CHASE_RESULT_NONE,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_NORTH,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEX,21,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEY,19,reason_direction_tile
    CHECK_IX32 W3D_ACTOR_X,0,080h,015h,0,reason_pose
    CHECK_IX32 W3D_ACTOR_Y,0,080h,014h,0,reason_pose
    CHECK_IX32 W3D_ACTOR_DISTANCE,0,0,1,0,reason_distance

; A failed ranged roll keeps dodge=true through the equality crossing and the
; selector consumes the second native byte (205,128).
    ld a,4
    ld (test_detail),a
    call prepare_east_leg_guard
    ld hl,0198000h                   ; player (25.5,20.5), cached delta four
    ld de,0148000h
    call set_player_xy
    ld hl,0157c00h
    ld (ix+W3D_ACTOR_X),hl
    ld (ix+W3D_ACTOR_X+3),0
    ld (ix+W3D_ACTOR_DISTANCE+0),0
    ld (ix+W3D_ACTOR_DISTANCE+1),4
    ld (ix+W3D_ACTOR_DISTANCE+2),0
    ld (ix+W3D_ACTOR_DISTANCE+3),0
    ld a,21
    ld (w3d_random_index),a
    ld a,2
    ld (w3d_actor_frame_tics),a
    call w3d_actor_think_chase
    CHECK_A W3D_CHASE_RESULT_NONE,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_NORTHEAST,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEX,22,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEY,19,reason_direction_tile
    CHECK_IX32 W3D_ACTOR_X,0,080h,015h,0,reason_pose
    CHECK_IX32 W3D_ACTOR_Y,0,080h,014h,0,reason_pose
    CHECK_MEM8 w3d_random_index,23,reason_rng
    ret

; ---------------------------------------------------------------------------
; Case 5: closed/open door lifecycle plus shootable occupancy behavior.
; ---------------------------------------------------------------------------

test_doors_and_occupancy:
    ld a,phase_doors_occupancy
    ld (test_phase),a

; Cardinal guard commits a closed door, requests OPENING, and waits.
    ld a,1
    ld (test_detail),a
    call prepare_center_guard
    ld a,W3D_DOOR_ACTION_CLOSED
    call install_east_door3
    CHECK_MEM8 test_tilemap+cell_east,W3D_TILE_DOOR_MIN+3,reason_door
    CHECK_MEM8 w3d_doors+30+W3D_DOOR_TILEX,21,reason_door
    CHECK_MEM8 w3d_doors+30+W3D_DOOR_TILEY,20,reason_door
    CHECK_MEM8 w3d_doors+30+W3D_DOOR_ACTION,W3D_DOOR_ACTION_CLOSED,reason_door
    ld b,21
    ld c,20
    call w3d_actor_check_side_cell
    CHECK_A 1,reason_door
    CHECK_MEM8 w3d_actor_pending_door,3,reason_door
    ld a,42
    ld (w3d_random_index),a
    call w3d_actor_think_chase
    CHECK_A W3D_CHASE_RESULT_NONE,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_EAST,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEX,21,reason_direction_tile
    CHECK_IX32 W3D_ACTOR_DISTANCE,0fch,0ffh,0ffh,0ffh,reason_door
    CHECK_MEM8 w3d_doors+34,W3D_DOOR_ACTION_OPENING,reason_door
    CHECK_MEM8 w3d_door_dirty+3,1,reason_door
    CHECK_MEM8 w3d_random_index,42,reason_rng

; Once externally fully open, the pending wait proceeds with the same budget.
    ld a,W3D_DOOR_ACTION_OPEN
    ld (w3d_doors+34),a
    ld a,1
    ld (test_tilemap+1302),a           ; keep attack line blocked
    ld a,2
    ld (w3d_actor_frame_tics),a
    call w3d_actor_think_chase
    CHECK_A W3D_CHASE_RESULT_NONE,reason_scalar
    CHECK_IX32 W3D_ACTOR_X,0,084h,014h,0,reason_pose
    CHECK_IX32 W3D_ACTOR_DISTANCE,0,0fch,0,0,reason_distance

; Fully OPEN is floor for ordinary and dog CHECKSIDE/CHECKDIAG semantics.
    ld a,2
    ld (test_detail),a
    call prepare_center_guard
    ld a,W3D_DOOR_ACTION_OPEN
    call install_east_door3
    ld a,W3D_DIR_EAST
    ld (ix+W3D_ACTOR_DIR),a
    call w3d_actor_try_walk
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_TILEX,21,reason_direction_tile
    CHECK_IX32 W3D_ACTOR_DISTANCE,0,0,1,0,reason_distance
    CHECK_MEM8 w3d_door_dirty+3,0,reason_door

    ld a,3
    ld (test_detail),a
    call prepare_center_dog
    ld a,W3D_DOOR_ACTION_OPEN
    call install_east_door3
    ld a,W3D_DIR_EAST
    ld (ix+W3D_ACTOR_DIR),a
    call w3d_actor_try_walk
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_TILEX,21,reason_direction_tile

; Non-open door remains solid to dog cardinal movement.
    ld a,4
    ld (test_detail),a
    call prepare_center_dog
    ld a,W3D_DOOR_ACTION_OPENING
    call install_east_door3
    ld a,W3D_DIR_EAST
    ld (ix+W3D_ACTOR_DIR),a
    call w3d_actor_try_walk
    CHECK_A 0,reason_scalar
    CHECK_IX8 W3D_ACTOR_TILEX,20,reason_direction_tile

; Shootable actor blocks; clearing SHOOTABLE makes the live occupant passable.
    ld a,5
    ld (test_detail),a
    call prepare_center_guard
    call install_east_occupant
    ld a,W3D_DIR_EAST
    ld (ix+W3D_ACTOR_DIR),a
    call w3d_actor_try_walk
    CHECK_A 0,reason_scalar
    CHECK_IX8 W3D_ACTOR_TILEX,20,reason_direction_tile

    ld a,6
    ld (test_detail),a
    call prepare_center_guard
    call install_east_occupant
    push ix
    ld a,2
    call w3d_actor_pointer_from_id
    xor a
    ld (ix+W3D_ACTOR_FLAGS),a
    pop ix
    ld a,W3D_DIR_EAST
    ld (ix+W3D_ACTOR_DIR),a
    call w3d_actor_try_walk
    CHECK_A 1,reason_scalar
    CHECK_IX8 W3D_ACTOR_TILEX,21,reason_direction_tile
    ret

; ---------------------------------------------------------------------------
; Case 6: T_DogChase projected jump request, both axes, diagonal movement.
; ---------------------------------------------------------------------------

test_dog_chase:
    ld a,phase_dog
    ld (test_phase),a

; Exact projected X boundary and near Y requests s_dogjump1, no RNG/mutation.
    ld a,1
    ld (test_detail),a
    call prepare_east_leg_dog
    ld hl,0158400h
    ld de,0148000h
    call set_player_xy
    call save_actor_record
    ld a,42
    ld (w3d_random_index),a
    call w3d_actor_think_dog_chase
    CHECK_A W3D_CHASE_RESULT_DOG_JUMP,reason_scalar
    CHECK_MEM8 w3d_random_index,42,reason_rng
    call assert_actor_record_unchanged

; X exact but Y one LSB beyond its projected threshold must not jump.
    ld a,2
    ld (test_detail),a
    call prepare_east_leg_dog
    ld hl,0158400h
    ld de,0158401h
    call set_player_xy
    call w3d_actor_think_dog_chase
    CHECK_A W3D_CHASE_RESULT_NONE,reason_scalar
    CHECK_IX32 W3D_ACTOR_X,0,084h,014h,0,reason_pose
    CHECK_IX32 W3D_ACTOR_DISTANCE,0,0fch,0,0,reason_distance

; NODIR dog consumes one dodge byte and moves both axes by the full budget.
    ld a,3
    ld (test_detail),a
    call prepare_center_dog
    ld hl,01e8000h
    ld de,0148000h
    call set_player_xy
    ld a,37
    ld (w3d_random_index),a
    call w3d_actor_think_dog_chase
    CHECK_A W3D_CHASE_RESULT_NONE,reason_scalar
    CHECK_IX8 W3D_ACTOR_DIR,W3D_DIR_NORTHEAST,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEX,21,reason_direction_tile
    CHECK_IX8 W3D_ACTOR_TILEY,19,reason_direction_tile
    CHECK_IX32 W3D_ACTOR_X,0,084h,014h,0,reason_pose
    CHECK_IX32 W3D_ACTOR_Y,0,07ch,014h,0,reason_pose
    CHECK_IX32 W3D_ACTOR_DISTANCE,0,0fch,0,0,reason_distance
    CHECK_MEM8 w3d_random_index,38,reason_rng

; Repeating the unlatched jump seam leaves pose and RNG unchanged both times.
    ld a,4
    ld (test_detail),a
    call prepare_east_leg_dog
    ld hl,0158400h
    ld de,0148000h
    call set_player_xy
    call save_actor_record
    ld a,42
    ld (w3d_random_index),a
    call w3d_actor_think_dog_chase
    CHECK_A W3D_CHASE_RESULT_DOG_JUMP,reason_scalar
    call w3d_actor_think_dog_chase
    CHECK_A W3D_CHASE_RESULT_DOG_JUMP,reason_scalar
    CHECK_MEM8 w3d_random_index,42,reason_rng
    call assert_actor_record_unchanged
    ret

; ---------------------------------------------------------------------------
; Case 7: invalid class/direction and malformed waits return FF before work.
; ---------------------------------------------------------------------------

test_corrupt_containment:
    ld a,phase_containment
    ld (test_phase),a

    ld a,1
    ld (test_detail),a
    call prepare_center_dog
    call save_actor_record
    ld a,42
    ld (w3d_random_index),a
    call w3d_actor_think_chase
    CHECK_A W3D_CHASE_RESULT_CORRUPT,reason_containment
    CHECK_MEM8 w3d_random_index,42,reason_rng
    call assert_actor_record_unchanged

    ld a,2
    ld (test_detail),a
    call prepare_center_guard
    ld a,9
    ld (ix+W3D_ACTOR_DIR),a
    call save_actor_record
    ld a,42
    ld (w3d_random_index),a
    call w3d_actor_think_chase
    CHECK_A W3D_CHASE_RESULT_CORRUPT,reason_containment
    CHECK_MEM8 w3d_random_index,42,reason_rng
    call assert_actor_record_unchanged

; Valid sign but malformed extension bytes fail before complemented indexing.
    ld a,3
    ld (test_detail),a
    call prepare_east_leg_guard
    ld a,1
    ld (test_tilemap+1302),a
    ld (ix+W3D_ACTOR_DISTANCE+0),0fch
    ld (ix+W3D_ACTOR_DISTANCE+1),0feh
    ld (ix+W3D_ACTOR_DISTANCE+2),0ffh
    ld (ix+W3D_ACTOR_DISTANCE+3),0ffh
    call w3d_actor_think_chase
    CHECK_A W3D_CHASE_RESULT_CORRUPT,reason_containment

; Dog rejects any injected negative wait before projected jump range.
    ld a,4
    ld (test_detail),a
    call prepare_east_leg_dog
    ld (ix+W3D_ACTOR_DISTANCE+0),0ffh
    ld (ix+W3D_ACTOR_DISTANCE+1),0ffh
    ld (ix+W3D_ACTOR_DISTANCE+2),0ffh
    ld (ix+W3D_ACTOR_DISTANCE+3),0ffh
    ld hl,0148000h
    ld de,0148000h
    call set_player_xy
    call save_actor_record
    ld a,42
    ld (w3d_random_index),a
    call w3d_actor_think_dog_chase
    CHECK_A W3D_CHASE_RESULT_CORRUPT,reason_containment
    CHECK_MEM8 w3d_random_index,42,reason_rng
    call assert_actor_record_unchanged
    ret

; ---------------------------------------------------------------------------
; Case 8: all 30 chase-state records plus one complete scheduler composition.
; ---------------------------------------------------------------------------

test_state_table_and_scheduler:
    ld a,phase_scheduler_states
    ld (test_phase),a
    ld a,1
    ld (test_detail),a

; Stable FirstSighting/chase ids and the complete post-combat table length.
    ld a,W3D_STATE_GRD_CHASE1
    CHECK_A 47,reason_scalar
    ld a,W3D_STATE_DOG_CHASE1
    CHECK_A 48,reason_scalar
    ld a,W3D_STATE_OFC_CHASE1
    CHECK_A 49,reason_scalar
    ld a,W3D_STATE_MUT_CHASE1
    CHECK_A 50,reason_scalar
    ld a,W3D_STATE_SS_CHASE1
    CHECK_A 51,reason_scalar
    ld a,W3D_STATE_SS_CHASE4
    CHECK_A 76,reason_scalar
    ld hl,w3d_actor_states_end-w3d_actor_states
    ld a,l
    CHECK_A 010h,reason_scalar          ; 130 * 8 = 0x0410
    ld a,h
    CHECK_A 4,reason_scalar

    ld ix,w3d_actor_states+376         ; 47 * 8, literal avoids precedence
    ld iy,expected_chase_states
    ld de,expected_chase_states_end-expected_chase_states
    ld c,reason_actor_record
    call assert_memory

; Full live-list pass supplies 2,2,3, releases/reclaims the cached target, and
; marks a moving chase actor dirty without faults or hidden RNG.
    ld a,2
    ld (test_detail),a
    call prepare_east_leg_guard
    ld a,W3D_STATE_GRD_CHASE1
    ld (ix+W3D_ACTOR_STATE+0),a
    xor a
    ld (ix+W3D_ACTOR_STATE+1),a
    ld (ix+W3D_ACTOR_TICCOUNT+0),a
    ld (ix+W3D_ACTOR_TICCOUNT+1),a
    ld hl,01e8000h
    ld de,0148000h
    call set_player_xy
    ld a,1
    ld (test_tilemap+1302),a
    ld a,42
    ld (w3d_random_index),a
    call w3d_simulate_actors
    call w3d_simulate_actors
    call w3d_simulate_actors
    ld a,1
    call w3d_actor_pointer_from_id
    CHECK_IX32 W3D_ACTOR_X,0,08eh,014h,0,reason_pose
    CHECK_IX32 W3D_ACTOR_DISTANCE,0,0f2h,0,0,reason_distance
    CHECK_MEM8 w3d_actor_tic_phase,0,reason_clock
    CHECK_MEM8 w3d_actor_frame_tics,3,reason_clock
    CHECK_MEM8 w3d_actorat+cell_east,1,reason_occupancy
    CHECK_MEM8 w3d_actorat+cell_center,0,reason_occupancy
    CHECK_MEM8 w3d_actor_dirty+1,W3D_ACTOR_DIRTY_SET,reason_occupancy
    CHECK_MEM8 w3d_actor_fault_count+0,0,reason_containment
    CHECK_MEM8 w3d_actor_fault_count+1,0,reason_containment
    CHECK_MEM8 w3d_random_index,42,reason_rng
    ret

; ---------------------------------------------------------------------------
; Case 9: hardware-compatible PRT budgets; assertions/file I/O are outside.
; ---------------------------------------------------------------------------

time_chase_paths:
    ld a,phase_timing
    ld (test_phase),a

; Stable close-range ranged requests include CheckLine and RNG, no reset work.
    ld a,1
    ld (test_detail),a
    call prepare_center_guard
    ld hl,0158000h
    ld de,0148000h
    call set_player_xy
    ld a,W3D_DIR_EAST
    ld (ix+W3D_ACTOR_DIR),a
    ld (ix+W3D_ACTOR_DISTANCE+0),0ffh
    ld (ix+W3D_ACTOR_DISTANCE+1),03fh
    xor a
    ld (ix+W3D_ACTOR_DISTANCE+2),a
    ld (ix+W3D_ACTOR_DISTANCE+3),a
    ld hl,timing_iterations
    ld (timing_left),hl
    call prt_start
@ordinary_loop:
    call w3d_actor_think_chase
    ld (last_return),a
    ld hl,(timing_left)
    dec hl
    ld (timing_left),hl
    ld a,h
    or l
    jr nz,@ordinary_loop
    call prt_stop_ordinary
    ld a,(last_return)
    CHECK_A W3D_CHASE_RESULT_RANGED,reason_scalar

; Stable exact-range dog jump is the lower-bound chase path, with no mutation.
    ld a,2
    ld (test_detail),a
    call prepare_east_leg_dog
    ld hl,0158400h
    ld de,0148000h
    call set_player_xy
    ld hl,timing_iterations
    ld (timing_left),hl
    call prt_start
@dog_loop:
    call w3d_actor_think_dog_chase
    ld (last_return),a
    ld hl,(timing_left)
    dec hl
    ld (timing_left),hl
    ld a,h
    or l
    jr nz,@dog_loop
    call prt_stop_dog
    ld a,(last_return)
    CHECK_A W3D_CHASE_RESULT_DOG_JUMP,reason_scalar
    ret

; ---------------------------------------------------------------------------
; Synthetic actor/world setup.
; ---------------------------------------------------------------------------

reset_chase_world:
    xor a
    ld hl,w3d_actors
    ld (hl),a
    ld de,w3d_actors+1
    ld bc,W3D_MAX_ACTORS*W3D_ACTOR_SIZE-1
    ldir
    ld hl,w3d_actorat
    ld (hl),a
    ld de,w3d_actorat+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,w3d_actor_dirty
    ld (hl),a
    ld de,w3d_actor_dirty+1
    ld bc,W3D_MAX_ACTORS-1
    ldir
    ld hl,test_tilemap
    ld (hl),a
    ld de,test_tilemap+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,test_area_map
    ld (hl),a
    ld de,test_area_map+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,test_static_bits
    ld (hl),a
    ld de,test_static_bits+1
    ld bc,511
    ldir
    ld hl,w3d_doors
    ld (hl),a
    ld de,w3d_doors+1
    ld bc,W3D_FIXTURE_DOOR_COUNT*W3D_DOOR_SIZE-1
    ldir
    ld hl,w3d_door_timers
    ld (hl),a
    ld de,w3d_door_timers+1
    ld bc,W3D_FIXTURE_DOOR_COUNT*2-1
    ldir
    ld hl,w3d_door_dirty
    ld (hl),a
    ld de,w3d_door_dirty+1
    ld bc,W3D_FIXTURE_DOOR_COUNT-1
    ldir
    ld hl,w3d_area_by_player
    ld (hl),a
    ld de,w3d_area_by_player+1
    ld bc,W3D_NUM_AREAS-1
    ldir
    ld hl,w3d_player_pose
    ld (hl),a
    ld de,w3d_player_pose+1
    ld bc,9
    ldir

    ld a,0ffh
    ld hl,test_path_directions
    ld (hl),a
    ld de,test_path_directions+1
    ld bc,W3D_MAP_BYTES-1
    ldir

; Conservative solid outer ring.
    xor a
    ld hl,test_tilemap
    ld iy,test_tilemap+4032
    ld b,64
@horizontal:
    ld (hl),1
    ld (iy+0),1
    inc hl
    inc iy
    djnz @horizontal
    ld iy,test_tilemap+64
    ld b,62
@vertical:
    ld (iy+0),1
    ld (iy+63),1
    lea iy,iy+64
    djnz @vertical

    call w3d_initialize_actor_simulation
    ld hl,test_tilemap
    ld (w3d_map_ptr),hl
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_TILEMAP),hl
    ld hl,w3d_doors
    ld (w3d_doors_ptr),hl
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_DOORS),hl
    ld hl,w3d_area_by_player
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_AREAS),hl
    ld hl,test_area_map
    ld (w3d_area_map_ptr),hl
    ld hl,test_path_directions
    ld (w3d_path_directions_ptr),hl
    ld hl,test_static_bits
    ld (w3d_static_blocking_ptr),hl

    ld a,W3D_SLOT_NONE
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
    ld a,1
    ld (w3d_actor_free_head),a
    xor a
    ld (w3d_actor_count),a
    ld (w3d_world_dirty),a
    ld (w3d_player_dirty),a
    ld (w3d_area_fault_count+0),a
    ld (w3d_area_fault_count+1),a
    ret

prepare_center_guard:
    call reset_chase_world
    ld a,1
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
    ld (w3d_actor_count),a
    ld a,2
    ld (w3d_actor_free_head),a
    ld a,1
    call w3d_actor_pointer_from_id
    ld hl,0148000h                   ; physical center (20.5,20.5)
    ld (ix+W3D_ACTOR_X),hl
    ld (ix+W3D_ACTOR_Y),hl
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld (ix+W3D_ACTOR_Y+3),a
    ld a,20
    ld (ix+W3D_ACTOR_TILEX),a
    ld (ix+W3D_ACTOR_TILEY),a
    ld a,2
    ld (ix+W3D_ACTOR_AREA),a
    ld a,1
    ld (w3d_area_by_player+2),a
    ld a,W3D_DIR_NODIR
    ld (ix+W3D_ACTOR_DIR),a
    ld a,W3D_ACTOR_ACTIVE_YES
    ld (ix+W3D_ACTOR_ACTIVE),a
    ld a,W3D_CLASS_GUARD
    ld (ix+W3D_ACTOR_CLASS),a
    ld a,W3D_ACTOR_FLAG_SHOOTABLE
    ld (ix+W3D_ACTOR_FLAGS),a
    ld a,W3D_STATE_GRD_CHASE1
    ld (ix+W3D_ACTOR_STATE+0),a
    xor a
    ld (ix+W3D_ACTOR_STATE+1),a
    ld (ix+W3D_ACTOR_TICCOUNT+0),a
    ld (ix+W3D_ACTOR_TICCOUNT+1),a
    ld (ix+W3D_ACTOR_DISTANCE+0),a
    ld (ix+W3D_ACTOR_DISTANCE+1),a
    inc a
    ld (ix+W3D_ACTOR_DISTANCE+2),a
    xor a
    ld (ix+W3D_ACTOR_DISTANCE+3),a
    ld (ix+W3D_ACTOR_SPEED+0),a
    ld a,2
    ld (ix+W3D_ACTOR_SPEED+1),a
    xor a
    ld (ix+W3D_ACTOR_SPEED+2),a
    ld (ix+W3D_ACTOR_SPEED+3),a
    ld a,W3D_SLOT_NONE
    ld (ix+W3D_ACTOR_NEXT),a
    ld (ix+W3D_ACTOR_PREV),a
    ld a,1
    ld (w3d_current_actor_index),a
    call w3d_actorat_claim
    ld hl,0188000h                   ; default player (24.5,20.5)
    ld de,0148000h
    call set_player_xy
    ld a,2
    ld (w3d_actor_frame_tics),a
    ld a,1
    call w3d_actor_pointer_from_id
    ret

prepare_center_dog:
    call prepare_center_guard
    ld a,W3D_CLASS_DOG
    ld (ix+W3D_ACTOR_CLASS),a
    ld a,W3D_STATE_DOG_CHASE1
    ld (ix+W3D_ACTOR_STATE+0),a
    ret

prepare_east_leg_guard:
    call prepare_center_guard
    jp make_actor_east_leg

prepare_east_leg_dog:
    call prepare_center_dog
    jp make_actor_east_leg

make_actor_east_leg:
    ld a,1
    call w3d_actorat_release
    ld a,21
    ld (ix+W3D_ACTOR_TILEX),a
    ld a,20
    ld (ix+W3D_ACTOR_TILEY),a
    ld a,W3D_DIR_EAST
    ld (ix+W3D_ACTOR_DIR),a
    call w3d_actor_set_tile_distance
    ld a,1
    jp w3d_actorat_claim

prepare_exact_center_crossing:
    call prepare_east_leg_guard
    ld hl,0158000h
    ld de,00f8000h
    call set_player_xy
    ld a,1
    ld (test_tilemap+1109),a
    ld hl,0157c00h
    ld (ix+W3D_ACTOR_X),hl
    ld (ix+W3D_ACTOR_X+3),0
    ld (ix+W3D_ACTOR_DISTANCE+0),0
    ld (ix+W3D_ACTOR_DISTANCE+1),4
    ld (ix+W3D_ACTOR_DISTANCE+2),0
    ld (ix+W3D_ACTOR_DISTANCE+3),0
    ld a,2
    ld (w3d_actor_frame_tics),a
    ret

prepare_firstattack_geometry:
    call prepare_center_guard
    ld a,W3D_DIR_WEST
    ld (ix+W3D_ACTOR_DIR),a
    ld a,1
    ld (test_tilemap+cell_northeast),a
    ld (test_tilemap+cell_north),a
    ret

; HL=x low 24 bits, DE=y low 24 bits; fixture coordinates use byte3=zero.
set_player_xy:
    ld (w3d_player_pose+0),hl
    ld (w3d_player_pose+4),de
    xor a
    ld (w3d_player_pose+3),a
    ld (w3d_player_pose+7),a
    jp w3d_prepare_actor_sight_context

block_all_neighbors:
    ld a,1
    ld (test_tilemap+cell_east),a
    ld (test_tilemap+cell_northeast),a
    ld (test_tilemap+cell_north),a
    ld (test_tilemap+cell_northwest),a
    ld (test_tilemap+cell_west),a
    ld (test_tilemap+cell_southwest),a
    ld (test_tilemap+cell_south),a
    ld (test_tilemap+cell_southeast),a
    ret

; Input A=door action. Install valid door index 3 at east neighbor.
install_east_door3:
    ld (door_action_input),a
    ld a,W3D_TILE_DOOR_MIN+3
    ld (test_tilemap+cell_east),a
    ld ix,w3d_doors+30                 ; 3 * W3D_DOOR_SIZE
    ld (ix+W3D_DOOR_TILEX),21
    ld (ix+W3D_DOOR_TILEY),20
    ld (ix+W3D_DOOR_VERTICAL),1
    ld a,(door_action_input)
    ld (ix+W3D_DOOR_ACTION),a
    cp W3D_DOOR_ACTION_OPEN
    jr nz,@done
    ld (ix+W3D_DOOR_POSITION+0),0ffh
    ld (ix+W3D_DOOR_POSITION+1),0ffh
@done:
    ld a,1
    call w3d_actor_pointer_from_id
    ret

install_east_occupant:
    push ix
    ld a,2
    call w3d_actor_pointer_from_id
    ld a,W3D_ACTOR_ACTIVE_YES
    ld (ix+W3D_ACTOR_ACTIVE),a
    ld a,W3D_ACTOR_FLAG_SHOOTABLE
    ld (ix+W3D_ACTOR_FLAGS),a
    ld a,21
    ld (ix+W3D_ACTOR_TILEX),a
    ld a,20
    ld (ix+W3D_ACTOR_TILEY),a
    ld a,2
    call w3d_actorat_claim
    pop ix
    ret

save_actor_record:
    push ix
    pop hl
    ld de,actor_before
    ld bc,W3D_ACTOR_SIZE
    ldir
    ret

assert_actor_record_unchanged:
    ld a,1
    call w3d_actor_pointer_from_id
    ld iy,actor_before
    ld de,W3D_ACTOR_SIZE
    ld c,reason_actor_record
    call assert_memory
    ld a,1
    jp w3d_actor_pointer_from_id

; ---------------------------------------------------------------------------
; PRT1 stopwatch.
; ---------------------------------------------------------------------------

prt_start:
    di
    ld hl,0
    ld (prt_irq_counter),hl
    ld hl,prt_reload_1ms
    out0 (TMR1_CTL+TMR_RES_LOW),l
    out0 (TMR1_CTL+TMR_RES_HIGH),h
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld a,PRT_ON
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ei
    ret

prt_stop_ordinary:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_irq_counter)
    ld (result_timing_ordinary),hl
    ei
    ret

prt_stop_dog:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_irq_counter)
    ld (result_timing_dog),hl
    ei
    ret

prt_irq_install:
    di
    ld hl,0
    ld a,($10c)
    ld l,a
    ld a,($10d)
    ld h,a
    inc hl
    ld hl,(hl)
    ld (prt_vector),hl
    ld a,(hl)
    ld (prt_saved_vector+0),a
    inc hl
    ld a,(hl)
    ld (prt_saved_vector+1),a
    inc hl
    ld a,(hl)
    ld (prt_saved_vector+2),a
    inc hl
    ld a,(hl)
    ld (prt_saved_vector+3),a
    ld hl,(prt_vector)
    ld (hl),0c3h
    inc hl
    ld de,prt_irq_handler
    ld (hl),de
    ei
    ret

prt_irq_restore:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_vector)
    ld a,(prt_saved_vector+0)
    ld (hl),a
    inc hl
    ld a,(prt_saved_vector+1)
    ld (hl),a
    inc hl
    ld a,(prt_saved_vector+2)
    ld (hl),a
    inc hl
    ld a,(prt_saved_vector+3)
    ld (hl),a
    ei
    ret

prt_irq_handler:
    di
    push af
    push hl
    in0 a,(TMR1_CTL+TMR_REG_CTL)
    ld hl,(prt_irq_counter)
    inc hl
    ld (prt_irq_counter),hl
    pop hl
    pop af
    ei
    reti.l

; ---------------------------------------------------------------------------
; Comparators and mailbox.
; ---------------------------------------------------------------------------

; IX=actual, IY=expected, DE=count, C=reason.
assert_memory:
@loop:
    ld a,d
    or e
    ret z
    ld a,(ix+0)
    ld b,(iy+0)
    push de
    call assert_equal
    pop de
    inc ix
    inc iy
    dec.s de
    jr @loop

; A=actual, B=expected, C=reason.
assert_equal:
    ld (assert_actual),a
    ld a,b
    ld (assert_expected),a
    push hl
    ld hl,result_checks
    inc (hl)
    jr nz,@compare
    inc hl
    inc (hl)
@compare:
    ld a,(assert_actual)
    cp b
    jr z,@index
    ld hl,result_errors
    inc (hl)
    jr nz,@bucket
    inc hl
    inc (hl)
@bucket:
    ld a,(test_phase)
    or a
    jr z,@first
    dec a
    cp phase_count
    jr nc,@first
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,result_phase_errors
    add hl,de
    inc (hl)
@first:
    ld a,(result_first_reason)
    or a
    jr nz,@index
    ld a,(test_phase)
    ld (result_first_phase),a
    ld a,c
    ld (result_first_reason),a
    ld a,(assert_expected)
    ld (result_first_expected),a
    ld a,(assert_actual)
    ld (result_first_actual),a
    ld a,(test_detail)
    ld (result_first_detail),a
    ld a,(test_index+0)
    ld (result_first_index+0),a
    ld a,(test_index+1)
    ld (result_first_index+1),a
@index:
    ld hl,test_index
    inc (hl)
    jr nz,@return
    inc hl
    inc (hl)
@return:
    pop hl
    ret

write_result:
    ld hl,result_filename
    ld c,fa_write | fa_create_always
    MOSCALL mos_fopen
    or a
    ret z
    ld (output_handle),a
    ld c,a
    ld hl,result_data
    ld de,result_end-result_data
    MOSCALL mos_fwrite
    ld a,(output_handle)
    ld c,a
    MOSCALL mos_fclose
    ret

print_report:
    ld hl,report_banner
    call print_string
    ld a,(result_errors+0)
    ld b,a
    ld a,(result_errors+1)
    or b
    ld hl,report_pass
    jr z,@emit
    ld hl,report_fail
@emit:
    jp print_string

print_string:
    push bc
    ld bc,0
    ld a,0
    rst.lil 18h
    pop bc
    ret

; Normal-world fixture: death presentation is deliberately inactive.
w3d_death_fixed_step:
    or a
    ret
w3d_death_promote_lethal_latch:
    or a
    ret

; Required by wolf3d_motion.inc but not exercised by this mailbox fixture.
w3d_mark_render_submitted:
    ret
w3d_elapsed_ticks:
    dl 0
w3d_exit_requested:
    db 0

; Literal source-derived records for IDs 47..76 are inserted below.
expected_chase_states:
    ; IDs 47..51: stable chase1 entry points.
    dw 58
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE1S
    dw 99
    db 8
    dw 10
    db W3D_STATE_THINK_DOG_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_CHASE1S
    dw 246
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE1S
    dw 195
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE1S
    dw 146
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE1S

    ; Guard W1s/W2/W3/W3s/W4.
    dw 58
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE2
    dw 66
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE3
    dw 74
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE3S
    dw 74
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE4
    dw 82
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE1

    ; Dog W1s/W2/W3/W3s/W4.
    dw 99
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_CHASE2
    dw 107
    db 8
    dw 8
    db W3D_STATE_THINK_DOG_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_CHASE3
    dw 115
    db 8
    dw 10
    db W3D_STATE_THINK_DOG_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_CHASE3S
    dw 115
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_CHASE4
    dw 123
    db 8
    dw 8
    db W3D_STATE_THINK_DOG_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_CHASE1

    ; Officer W1s/W2/W3/W3s/W4.
    dw 246
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE2
    dw 254
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE3
    dw 262
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE3S
    dw 262
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE4
    dw 270
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE1

    ; Mutant W1s/W2/W3/W3s/W4.
    dw 195
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE2
    dw 203
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE3
    dw 211
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE3S
    dw 211
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE4
    dw 219
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE1

    ; SS W1s/W2/W3/W3s/W4.
    dw 146
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE2
    dw 154
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE3
    dw 162
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE3S
    dw 162
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE4
    dw 170
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE1
expected_chase_states_end:

result_filename:            asciz "chase_result.bin"
report_banner:              asciz "\r\nWolf3D eZ80 chase regression: "
report_pass:                asciz "PASS\r\n"
report_fail:                asciz "FAIL\r\n"

output_handle:              db 0
test_phase:                 db 0
test_detail:                db 0
test_index:                 dw 0
assert_expected:            db 0
assert_actual:              db 0
door_action_input:          db 0
last_return:                db 0
timing_left:                dl 0
prt_vector:                 dl 0
prt_saved_vector:           db 0,0,0,0
prt_irq_counter:            dl 0
actor_before:               ds W3D_ACTOR_SIZE

result_data:
    db "W3CH"
result_checks:              dw 0
result_errors:              dw 0
result_first_phase:         db 0
result_first_reason:        db 0
result_first_expected:      db 0
result_first_actual:        db 0
result_first_detail:        db 0
result_first_index:         dw 0
                            db 0
result_phase_errors:        ds phase_count
result_timing_ordinary:     dl 0
result_timing_dog:          dl 0
result_schema:              db 1
result_end:

test_tilemap:
    ds W3D_MAP_BYTES
test_path_directions:
    ds W3D_MAP_BYTES
test_area_map:
    ds W3D_MAP_BYTES
test_static_bits:
    ds 512
