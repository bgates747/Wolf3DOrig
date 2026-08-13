; Direct real-eZ80 regression for the production Wolf3D actor patrol runner.
;
; The independent Python oracle emits fixed W3PV records.  This fixture only
; applies those complete actor/door snapshots and sparse world cells, advances
; the production door and actor routines, and compares authoritative memory.
; It deliberately contains no second implementation of DoActor/T_Path.

    assume adl=1
    org 0x040000
    jp start
    align 64
    db "MOS",0,1

mos_getkbmap:       equ 0x1e
mos_fopen:          equ 0x0a
mos_fclose:         equ 0x0b
mos_fwrite:         equ 0x1b
fa_write:           equ 0x02
fa_create_always:   equ 0x08

; PRT1 runs at 18.432 MHz / 256, so a reload of 72 gives a hardware-compatible
; 1 ms stopwatch tick. Interrupt ownership follows the established DDA harness.
prt_reload_1ms:     equ 72
TMR1_CTL:           equ 083h
TMR_REG_CTL:        equ 0
TMR_RES_LOW:        equ 1
TMR_RES_HIGH:       equ 2
PRT_OFF:            equ %00001110
PRT_ON:             equ %01011111

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    include "wolf3d_audio_assets.inc"
    include "wolf3d_sight.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_actors.inc"
    include "wolf3d_areas.inc"
    include "wolf3d_actor_sim.inc"
    include "wolf3d_motion.inc"
    include "wolf3d_player_combat.inc"
    include "patrol_vectors.inc"

phase_vector:               equ 1
phase_cadence:              equ 2
phase_trywalk:              equ 3
phase_player:               equ 4
phase_obstruction:          equ 5
phase_invalid:              equ 6

reason_header:              equ 1
reason_actor_present:       equ 2
reason_actor_record:        equ 3
reason_door_record:         equ 4
reason_actor_dirty:         equ 5
reason_door_dirty:          equ 6
reason_actor_phase:         equ 7
reason_door_phase:          equ 8
reason_actorat:             equ 9
reason_timer:               equ 10
reason_scalar:              equ 11
reason_tile:                equ 12
reason_distance:            equ 13
reason_pose:                equ 14
reason_door_action:         equ 15
reason_fault:               equ 16

; Remaining fixed W3PV-v1 offsets.  The generated include owns the record
; size/count and the four large-record offsets used by both implementations.
pv_case_id:                 equ 0
pv_steps:                   equ 2
pv_actor_phase:             equ 4
pv_door_phase:              equ 5
pv_actor_id:                equ 6
pv_door_index:              equ 7
pv_player_x:                equ 8
pv_player_y:                equ 12
pv_initial_door_timer:      equ 114
pv_expected_door_timer:     equ 116
pv_expected_actor_dirty:    equ 118
pv_expected_door_dirty:     equ 119
pv_final_actor_phase:       equ 120
pv_final_door_phase:        equ 121
pv_expected_actor_present: equ 122
pv_patch_count:             equ 123
pv_patch_size:              equ 8
pv_patch_x:                 equ 0
pv_patch_y:                 equ 1
pv_patch_tile:              equ 2
pv_patch_path:              equ 3
pv_patch_area:              equ 4
pv_patch_static:            equ 5
pv_patch_actorat_in:        equ 6
pv_patch_actorat_out:       equ 7

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
    call prt_irq_install
    call test_vector_corpus
    call test_direct_cadence
    call test_trywalk_edges
    call test_player_rollback
    call test_actor_door_obstruction
    call test_adjacent_actor_close_threshold
    call test_invalid_state_safety
    call prt_irq_restore
    call write_result
    call print_report
    ret

; ---------------------------------------------------------------------------
; All eleven independent W3PV oracle cases
; ---------------------------------------------------------------------------

test_vector_corpus:
    ld a,phase_vector
    ld (test_phase),a

; Validate the durable header before trusting the generated record stream.
    ld ix,w3d_patrol_vector_blob
    ld iy,expected_vector_header
    ld de,8
    ld c,reason_header
    call assert_memory

    ld hl,w3d_patrol_vector_blob+W3D_PATROL_VECTOR_HEADER_SIZE
    ld (vector_ptr),hl
    ld a,W3D_PATROL_VECTOR_COUNT
    ld (vectors_left),a
@next:
    ld hl,(vector_ptr)
    push hl
    pop iy
    ld a,(iy+pv_case_id)
    ld (test_detail),a
    call prepare_vector_case
    call run_vector_steps
    call validate_vector_case

    ld hl,(vector_ptr)
    ld de,W3D_PATROL_VECTOR_RECORD_SIZE
    add hl,de
    ld (vector_ptr),hl
    ld hl,vectors_left
    dec (hl)
    jr nz,@next
    ret

prepare_vector_case:
    call reset_empty_world
    ld hl,(vector_ptr)
    push hl
    pop iy

; Install the complete actor record at its stable slot and expose a one-entry
; live list.  Sparse actorat cells below carry the source/destination claim.
    ld a,(iy+pv_actor_id)
    ld (test_actor_id),a
    call w3d_actor_pointer_from_id
    lea hl,iy+W3D_PV_INITIAL_ACTOR
    push ix
    pop de
    ld bc,W3D_ACTOR_SIZE
    ldir
    ld a,(test_actor_id)
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
    ld a,1
    ld (w3d_actor_count),a

; Player coordinates are part of the oracle record because MoveObj's
; inclusive one-tile rejection is observable actor behavior.
    ld hl,(vector_ptr)
    push hl
    pop iy
    lea hl,iy+pv_player_x
    ld de,w3d_player_pose
    ld bc,8
    ldir

; Apply only the cells named by the oracle.  Everything else is open area
; zero, no path arrow, no static, and no actor (apart from border walls).
    ld hl,(vector_ptr)
    push hl
    pop iy
    ld a,(iy+pv_patch_count)
    ld (patches_left),a
    push iy
    pop hl
    ld de,W3D_PV_PATCHES
    add hl,de                         ; LEA's signed displacement stops at +127
    ld (patch_ptr),hl
@patch_loop:
    ld a,(patches_left)
    or a
    jr z,@door
    ld hl,(patch_ptr)
    push hl
    pop ix
    ld b,(ix+pv_patch_x)
    ld c,(ix+pv_patch_y)
    call test_cell_offset
    push hl
    ld de,test_tilemap
    add hl,de
    ld a,(ix+pv_patch_tile)
    ld (hl),a
    pop hl
    push hl
    ld de,test_path_directions
    add hl,de
    ld a,(ix+pv_patch_path)
    ld (hl),a
    pop hl
    push hl
    ld de,test_area_map
    add hl,de
    ld a,(ix+pv_patch_area)
    ld (hl),a
    pop hl
    ld de,w3d_actorat
    add hl,de
    ld a,(ix+pv_patch_actorat_in)
    ld (hl),a
    ld a,(ix+pv_patch_static)
    or a
    jr z,@patch_done
    ld b,(ix+pv_patch_x)
    ld c,(ix+pv_patch_y)
    call set_test_static_cell
@patch_done:
    ld hl,(patch_ptr)
    ld de,pv_patch_size
    add hl,de
    ld (patch_ptr),hl
    ld hl,patches_left
    dec (hl)
    jr @patch_loop

@door:
    ld hl,(vector_ptr)
    push hl
    pop iy
    ld a,(iy+pv_door_index)
    ld (test_door_index),a
    cp W3D_SLOT_NONE
    jr z,@phases
    call w3d_door_pointer_from_index
    lea hl,iy+W3D_PV_INITIAL_DOOR
    push ix
    pop de
    ld bc,W3D_DOOR_SIZE
    ldir
    ld a,(test_door_index)
    call test_door_timer_pointer
    ld hl,(vector_ptr)
    push hl
    pop iy
    ld a,(iy+pv_initial_door_timer+0)
    ld (ix+0),a
    ld a,(iy+pv_initial_door_timer+1)
    ld (ix+1),a

@phases:
    ld hl,(vector_ptr)
    push hl
    pop iy
    ld a,(iy+pv_actor_phase)
    ld (w3d_actor_tic_phase),a
    ld a,(iy+pv_door_phase)
    ld (w3d_door_motion_phase),a
    ret

run_vector_steps:
    ld hl,(vector_ptr)
    push hl
    pop iy
    ld l,(iy+pv_steps+0)
    ld h,(iy+pv_steps+1)
    inc hl
    dec.s hl
    ld (test_steps),hl
    ld a,(test_detail)
    cp 10                            ; time the real 92-frame E1L1 acceptance
    call z,prt_start
@loop:
    ld hl,(test_steps)
    ld a,h
    or l
    jr z,@complete
    call w3d_simulate_doors
    call w3d_simulate_actors
    ld hl,(test_steps)
    dec.s hl
    ld (test_steps),hl
    jr @loop
@complete:
    ld a,(test_detail)
    cp 10
    ret nz
    jp prt_stop

validate_vector_case:
    ld hl,(vector_ptr)
    push hl
    pop iy

; Presence is checked separately so a safe removal cannot masquerade as a
; zero-filled expected record.
    ld a,(test_actor_id)
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_ACTIVE)
    cp W3D_ACTOR_ACTIVE_FREE
    ld a,0
    jr z,@presence_ready
    inc a
@presence_ready:
    ld b,(iy+pv_expected_actor_present)
    ld c,reason_actor_present
    call assert_equal
    ld a,b
    or a
    jr z,@door

    ld a,(test_actor_id)
    call w3d_actor_pointer_from_id
    ld hl,(vector_ptr)
    ld de,W3D_PV_EXPECTED_ACTOR
    add hl,de
    push hl
    pop iy
    ld de,W3D_ACTOR_SIZE
    ld c,reason_actor_record
    call assert_memory

@door:
    ld hl,(vector_ptr)
    push hl
    pop iy
    ld a,(test_door_index)
    cp W3D_SLOT_NONE
    jr z,@dirty
    call w3d_door_pointer_from_index
    ld hl,(vector_ptr)
    ld de,W3D_PV_EXPECTED_DOOR
    add hl,de
    push hl
    pop iy
    ld de,W3D_DOOR_SIZE
    ld c,reason_door_record
    call assert_memory

    ld a,(test_door_index)
    call test_door_timer_pointer
    push ix
    pop hl
    push hl
    pop ix
    ld hl,(vector_ptr)
    ld de,pv_expected_door_timer
    add hl,de
    push hl
    pop iy
    ld de,2
    ld c,reason_timer
    call assert_memory

@dirty:
    ld hl,(vector_ptr)
    push hl
    pop iy
    ld a,(test_actor_id)
    call w3d_actor_dirty_address
    ld a,(hl)
    or a
    ld a,0
    jr z,@actor_dirty_ready
    inc a
@actor_dirty_ready:
    ld b,(iy+pv_expected_actor_dirty)
    ld c,reason_actor_dirty
    call assert_equal

    ld a,(test_door_index)
    cp W3D_SLOT_NONE
    ld a,0
    jr z,@door_dirty_ready
    ld a,(test_door_index)
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_door_dirty
    add hl,de
    ld a,(hl)
    or a
    ld a,0
    jr z,@door_dirty_ready
    inc a
@door_dirty_ready:
    ld b,(iy+pv_expected_door_dirty)
    ld c,reason_door_dirty
    call assert_equal

    ld a,(w3d_actor_tic_phase)
    ld b,(iy+pv_final_actor_phase)
    ld c,reason_actor_phase
    call assert_equal
    ld a,(w3d_door_motion_phase)
    ld b,(iy+pv_final_door_phase)
    ld c,reason_door_phase
    call assert_equal

; Every sparse cell pins final destination occupancy, including release and
; reclaim across residual multi-leg movement.
    ld a,(iy+pv_patch_count)
    ld (patches_left),a
    push iy
    pop hl
    ld de,W3D_PV_PATCHES
    add hl,de
    ld (patch_ptr),hl
@occupancy_loop:
    ld a,(patches_left)
    or a
    ret z
    ld hl,(patch_ptr)
    push hl
    pop ix
    ld b,(ix+pv_patch_x)
    ld c,(ix+pv_patch_y)
    call w3d_actorat_get
    ld b,(ix+pv_patch_actorat_out)
    ld c,reason_actorat
    call assert_equal
    ld hl,(patch_ptr)
    ld de,pv_patch_size
    add hl,de
    ld (patch_ptr),hl
    ld hl,patches_left
    dec (hl)
    jr @occupancy_loop

; ---------------------------------------------------------------------------
; Small directed checks not naturally represented by the corpus
; ---------------------------------------------------------------------------

test_direct_cadence:
    ld a,phase_cadence
    ld (test_phase),a
    ld (test_detail),a
    call w3d_initialize_actor_simulation
    ld iy,expected_cadence
    ld d,0
    ld e,6
@loop:
    push de
    call w3d_actor_advance_frame_tics
    ld a,(w3d_actor_frame_tics)
    ld b,(iy+0)
    ld c,reason_scalar
    call assert_equal
    inc iy
    pop de
    dec.s de
    ld a,d
    or e
    jr nz,@loop
    ret

test_trywalk_edges:
    ld a,phase_trywalk
    ld (test_phase),a

; A wall in the cardinal target cell blocks an ordinary guard.
    ld a,1
    ld (test_detail),a
    call prepare_direct_actor
    ld a,1
    ld (test_tilemap+651),a          ; (11,10)
    call w3d_actor_try_walk
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TILEX)
    ld b,10
    ld c,reason_tile
    call assert_equal

; An immutable blocking static in the same otherwise-open cell also blocks.
    ld a,2
    ld (test_detail),a
    call prepare_direct_actor
    ld b,11
    ld c,10
    call set_test_static_cell
    call w3d_actor_try_walk
    ld b,0
    ld c,reason_scalar
    call assert_equal

; Shootable actor reservations block; nonshootable reservations do not.
    ld a,3
    ld (test_detail),a
    call prepare_direct_actor
    ld a,2
    ld (w3d_actorat+651),a          ; target (11,10) reservation
    ld a,W3D_ACTOR_FLAG_SHOOTABLE
    ld (w3d_actors+78+W3D_ACTOR_FLAGS),a ; slot 2; avoid ez80asm L-to-R precedence
    call w3d_actor_try_walk
    ld b,0
    ld c,reason_scalar
    call assert_equal

    ld a,4
    ld (test_detail),a
    call prepare_direct_actor
    ld a,2
    ld (w3d_actorat+651),a
    xor a
    ld (w3d_actors+78+W3D_ACTOR_FLAGS),a
    call w3d_actor_try_walk
    ld b,1
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TILEX)
    ld b,11
    ld c,reason_tile
    call assert_equal

; Underflow at the west map edge fails closed without corrupting cached tile.
    ld a,5
    ld (test_detail),a
    call prepare_direct_actor
    xor a
    ld (ix+W3D_ACTOR_TILEX),a
    ld a,W3D_DIR_WEST
    ld (ix+W3D_ACTOR_DIR),a
    call w3d_actor_try_walk
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TILEX)
    ld b,0
    ld c,reason_tile
    call assert_equal

; Diagonal movement also checks the two orthogonal corner cells.
    ld a,6
    ld (test_detail),a
    call prepare_direct_actor
    ld a,W3D_DIR_NORTHEAST
    ld (ix+W3D_ACTOR_DIR),a
    ld a,1
    ld (test_tilemap+651),a          ; east corner (11,10)
    call w3d_actor_try_walk
    ld b,0
    ld c,reason_scalar
    call assert_equal

; A fully open door is ordinary floor for both CHECKDIAG dogs and CHECKSIDE
; guards. The two closed-door counterparts are corpus cases 6 and 7.
    ld a,7
    ld (test_detail),a
    call prepare_direct_actor
    ld a,W3D_CLASS_DOG
    ld (ix+W3D_ACTOR_CLASS),a
    call install_direct_open_door
    call w3d_actor_try_walk
    ld b,1
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TILEX)
    ld b,11
    ld c,reason_tile
    call assert_equal
    ld a,(ix+W3D_ACTOR_DISTANCE+2)
    ld b,1
    ld c,reason_distance
    call assert_equal

    ld a,8
    ld (test_detail),a
    call prepare_direct_actor
    call install_direct_open_door
    call w3d_actor_try_walk
    ld b,1
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TILEX)
    ld b,11
    ld c,reason_tile
    call assert_equal
    ld a,(w3d_doors+W3D_DOOR_ACTION)
    ld b,W3D_DOOR_ACTION_OPEN
    ld c,reason_door_action
    call assert_equal

; A stale reservation naming a slot already returned to the free list fails
; closed instead of becoming a pass-through cell.
    ld a,9
    ld (test_detail),a
    call prepare_direct_actor
    ld a,2
    ld (w3d_actorat+651),a
    ld a,W3D_ACTOR_ACTIVE_FREE
    ld (w3d_actors+78+W3D_ACTOR_ACTIVE),a
    call w3d_actor_try_walk
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ret

test_player_rollback:
    ld a,phase_player
    ld (test_phase),a
    ld a,1
    ld (test_detail),a
    call prepare_direct_actor
    ld hl,0000400h
    ld (w3d_actor_move_amount),hl
    ld hl,00acc00h                   ; exactly 0x4800 east of moved actor
    ld (w3d_player_pose+0),hl
    xor a
    ld (w3d_player_pose+3),a
    ld hl,00a8000h
    ld (w3d_player_pose+4),hl
    ld (w3d_player_pose+7),a
    call w3d_actor_move_obj
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_X+0)
    ld b,0
    ld c,reason_pose
    call assert_equal
    ld a,(ix+W3D_ACTOR_X+1)
    ld b,080h
    ld c,reason_pose
    call assert_equal
    ld a,(ix+W3D_ACTOR_X+2)
    ld b,10
    ld c,reason_pose
    call assert_equal
    ld a,(ix+W3D_ACTOR_DISTANCE+0)
    ld b,0
    ld c,reason_distance
    call assert_equal
    ld a,(ix+W3D_ACTOR_DISTANCE+2)
    ld b,1
    ld c,reason_distance
    call assert_equal
    ret

test_actor_door_obstruction:
    ld a,phase_obstruction
    ld (test_phase),a
    ld a,1
    ld (test_detail),a
    call prepare_direct_actor
    ld a,10
    ld (w3d_doors+W3D_DOOR_TILEX),a
    ld (w3d_doors+W3D_DOOR_TILEY),a
    ld a,1
    ld (w3d_doors+W3D_DOOR_VERTICAL),a
    ld a,080h
    ld (w3d_doors+W3D_DOOR_POSITION+1),a
    xor a
    ld (w3d_doors+W3D_DOOR_POSITION+0),a

; Original CloseDoor parity first honors the cached actorat reservation even
; when the actor's physical center has not reached the recessed well.
    ld a,1
    ld (w3d_actorat+650),a
    ld hl,0208000h
    ld (w3d_actors+W3D_ACTOR_SIZE+W3D_ACTOR_X),hl
    ld (w3d_actors+W3D_ACTOR_SIZE+W3D_ACTOR_Y),hl
    xor a
    call w3d_door_pointer_from_index
    call w3d_door_actor_obstructs
    ld b,1
    ld c,reason_scalar
    call assert_equal

; Clearing the reservation still leaves the finite slab/AABB fallback.
    xor a
    ld (w3d_actorat+650),a
    ld hl,00a8000h
    ld (w3d_actors+W3D_ACTOR_SIZE+W3D_ACTOR_X),hl
    ld (w3d_actors+W3D_ACTOR_SIZE+W3D_ACTOR_Y),hl
    call w3d_door_pointer_from_index
    call w3d_door_actor_obstructs
    ld b,1
    ld c,reason_scalar
    call assert_equal

; NONMARK entities are deliberately absent from occupancy/door obstruction.
    ld a,1
    call w3d_actor_pointer_from_id
    ld a,W3D_ACTOR_FLAG_NONMARK
    ld (ix+W3D_ACTOR_FLAGS),a
    xor a
    call w3d_door_pointer_from_index
    call w3d_door_actor_obstructs
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ret

; Original CloseDoor does not only inspect actorat[door]. For a vertical door
; it also inspects the actors reserving the west/east adjacent cells, blocking
; while the far-side actor's x-MINDIST still lies in the door tile. This pair
; pins the exact one-LSB boundary even when the door is fully open and its
; renderer slab has disappeared.
test_adjacent_actor_close_threshold:
    ld a,phase_obstruction
    ld (test_phase),a
    ld a,2
    ld (test_detail),a
    call prepare_direct_actor

    ld a,10
    ld (w3d_doors+W3D_DOOR_TILEX),a
    ld (w3d_doors+W3D_DOOR_TILEY),a
    ld a,1
    ld (w3d_doors+W3D_DOOR_VERTICAL),a
    ld a,W3D_DOOR_ACTION_OPEN
    ld (w3d_doors+W3D_DOOR_ACTION),a
    ld a,0ffh
    ld (w3d_doors+W3D_DOOR_POSITION+0),a
    ld (w3d_doors+W3D_DOOR_POSITION+1),a

; The actor has reserved east-adjacent (11,10), but at x=11:57ff its
; x-MINDIST is still 10:ffff. Closing must remain suppressed.
    ld a,11
    ld (ix+W3D_ACTOR_TILEX),a
    ld a,10
    ld (ix+W3D_ACTOR_TILEY),a
    ld a,1
    ld (w3d_actorat+651),a
    ld hl,00b57ffh
    ld (ix+W3D_ACTOR_X),hl
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld (w3d_current_door_index),a
    call w3d_door_pointer_from_index
    call w3d_try_close_current_door
    ld a,(w3d_doors+W3D_DOOR_ACTION)
    ld b,W3D_DOOR_ACTION_OPEN
    ld c,reason_door_action
    call assert_equal
    ld a,(w3d_door_dirty+0)
    ld b,0
    ld c,reason_door_dirty
    call assert_equal

; At x=11:5800, x-MINDIST is exactly 11:0000: the body has cleared the
; door tile and the same far-side reservation must no longer suppress close.
    ld a,3
    ld (test_detail),a
    ld hl,00b5800h
    ld (w3d_actors+W3D_ACTOR_SIZE+W3D_ACTOR_X),hl
    ld a,W3D_DOOR_ACTION_OPEN
    ld (w3d_doors+W3D_DOOR_ACTION),a
    xor a
    ld (w3d_door_dirty+0),a
    ld (w3d_world_dirty),a
    ld (w3d_current_door_index),a
    call w3d_door_pointer_from_index
    call w3d_try_close_current_door
    ld a,(w3d_doors+W3D_DOOR_ACTION)
    ld b,W3D_DOOR_ACTION_CLOSING
    ld c,reason_door_action
    call assert_equal
    ld a,(w3d_door_dirty+0)
    ld b,1
    ld c,reason_door_dirty
    call assert_equal
    ret

test_invalid_state_safety:
    ld a,phase_invalid
    ld (test_phase),a
    ld a,1
    ld (test_detail),a
    call prepare_direct_actor
    ld a,1
    ld (w3d_actorat+650),a          ; actor's cached (10,10) reservation
    ld (ix+W3D_ACTOR_STATE+1),a      ; invalid uint16 state, must fail closed
    call w3d_simulate_actors
    ld a,(w3d_actor_fault_count+0)
    ld b,1
    ld c,reason_fault
    call assert_equal
    ld a,(w3d_actor_count)
    ld b,0
    ld c,reason_actor_present
    call assert_equal
    ld a,(w3d_actor_live_head)
    ld b,W3D_SLOT_NONE
    ld c,reason_actor_present
    call assert_equal
    ld a,(w3d_actorat+650)
    ld b,0
    ld c,reason_actorat
    call assert_equal
    ld a,(w3d_actor_dirty+1)
    ld b,W3D_ACTOR_DIRTY_REMOVE
    ld c,reason_actor_dirty
    call assert_equal
    ret

; ---------------------------------------------------------------------------
; World/setup helpers
; ---------------------------------------------------------------------------

prepare_direct_actor:
    call reset_empty_world
    ld a,1
    ld (test_actor_id),a
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
    ld (w3d_actor_count),a
    call w3d_actor_pointer_from_id
    ld hl,00a8000h
    ld (ix+W3D_ACTOR_X),hl
    ld (ix+W3D_ACTOR_Y),hl
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld (ix+W3D_ACTOR_Y+3),a
    ld a,10
    ld (ix+W3D_ACTOR_TILEX),a
    ld (ix+W3D_ACTOR_TILEY),a
    ld a,W3D_DIR_EAST
    ld (ix+W3D_ACTOR_DIR),a
    ld a,W3D_ACTOR_ACTIVE_YES
    ld (ix+W3D_ACTOR_ACTIVE),a
    ld a,W3D_CLASS_GUARD
    ld (ix+W3D_ACTOR_CLASS),a
    ld a,W3D_ACTOR_FLAG_SHOOTABLE
    ld (ix+W3D_ACTOR_FLAGS),a
    ld a,W3D_STATE_GRD_PATH1
    ld (ix+W3D_ACTOR_STATE+0),a
    xor a
    ld (ix+W3D_ACTOR_STATE+1),a
    ld hl,010000h
    ld (ix+W3D_ACTOR_DISTANCE),hl
    ld (ix+W3D_ACTOR_DISTANCE+3),a
    ld hl,512
    ld (ix+W3D_ACTOR_SPEED),hl
    xor a
    ld (ix+W3D_ACTOR_SPEED+3),a
    ld a,W3D_SLOT_NONE
    ld (ix+W3D_ACTOR_NEXT),a
    ld (ix+W3D_ACTOR_PREV),a
    ld a,1
    ld (w3d_current_actor_index),a
    ret

; Install door zero at the direct actor's east target and leave it fully open.
install_direct_open_door:
    ld a,W3D_TILE_DOOR_MIN
    ld (test_tilemap+651),a
    ld a,11
    ld (w3d_doors+W3D_DOOR_TILEX),a
    ld a,10
    ld (w3d_doors+W3D_DOOR_TILEY),a
    ld a,1
    ld (w3d_doors+W3D_DOOR_VERTICAL),a
    ld a,W3D_DOOR_ACTION_OPEN
    ld (w3d_doors+W3D_DOOR_ACTION),a
    ld a,0ffh
    ld (w3d_doors+W3D_DOOR_POSITION+0),a
    ld (w3d_doors+W3D_DOOR_POSITION+1),a
    ret

reset_empty_world:
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

; No-arrow is FF, not zero (zero is a valid east arrow).
    ld a,0ffh
    ld hl,test_path_directions
    ld (hl),a
    ld de,test_path_directions+1
    ld bc,W3D_MAP_BYTES-1
    ldir

; Match the oracle's ordinary bordered empty map.
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
    ld ix,test_tilemap+64
    ld b,62
@vertical:
    ld (ix+0),1
    ld (ix+63),1
    lea ix,ix+64
    djnz @vertical

    ld hl,test_tilemap
    ld (w3d_map_ptr),hl
    ld hl,test_static_bits
    ld (w3d_static_blocking_ptr),hl
    ld hl,test_area_map
    ld (w3d_area_map_ptr),hl
    ld hl,test_path_directions
    ld (w3d_path_directions_ptr),hl
    ld hl,w3d_doors
    ld (w3d_doors_ptr),hl

; Patrol vectors predate the connectivity milestone and model their synthetic
; area zero as connected. Seed that explicit graph state so MoveObj's new
; source-faithful area gate preserves the independent vector contract.
    ld a,1
    ld hl,w3d_area_by_player
    ld (hl),a
    ld de,w3d_area_by_player+1
    ld bc,W3D_NUM_AREAS-1
    ldir
    xor a
    ld (w3d_player_area),a
    ld (w3d_area_last_player_sample),a
    inc a
    ld (w3d_area_player_sample_seen),a
    dec a
    ld (w3d_area_topology_dirty),a
    ld (w3d_area_fault_count+0),a
    ld (w3d_area_fault_count+1),a

    ld ix,w3d_actors
    ld a,W3D_ACTOR_ACTIVE_ALWAYS
    ld (ix+W3D_ACTOR_ACTIVE),a
    ld a,W3D_SLOT_NONE
    ld (ix+W3D_ACTOR_NEXT),a
    ld (ix+W3D_ACTOR_PREV),a
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
    ld a,1
    ld (w3d_actor_free_head),a
    xor a
    ld (w3d_actor_count),a
    ld (w3d_world_dirty),a
    ld (w3d_player_dirty),a
    ld (w3d_door_motion_phase),a
    call w3d_initialize_actor_simulation
    xor a
    ld (w3d_awareness_enabled),a

    ld hl,03c8000h                   ; keep default player far from test actor
    ld (w3d_player_pose+0),hl
    ld (w3d_player_pose+4),hl
    xor a
    ld (w3d_player_pose+3),a
    ld (w3d_player_pose+7),a
    ret

; B=x,C=y -> HL=y*64+x. B/C preserved.
test_cell_offset:
    push bc
    ld hl,0
    ld l,c
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    ld de,0
    ld e,b
    add.s hl,de
    pop bc
    ret

; Set the immutable bit for B=x,C=y. Test arrays are zeroed before patches.
set_test_static_cell:
    push bc
    ld a,b
    and 7
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,static_masks
    add hl,de
    ld a,(hl)
    ld (test_static_mask),a
    ld hl,0
    ld l,c
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    ld a,b
    srl a
    srl a
    srl a
    ld e,a
    ld d,0
    inc de
    dec.s de
    add.s hl,de
    ld de,test_static_bits
    add hl,de
    ld a,(test_static_mask)
    or (hl)
    ld (hl),a
    pop bc
    ret

; A=door index -> IX=&timer[door].
test_door_timer_pointer:
    ld l,a
    ld h,0
    inc hl
    dec.s hl
    add.s hl,hl
    ld de,w3d_door_timers
    add hl,de
    push hl
    pop ix
    ret

; ---------------------------------------------------------------------------
; PRT1 1-ms stopwatch (same vector discipline as wolf3d_ai regression)
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

prt_stop:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_irq_counter)
    ld (result_e1l1_milliseconds),hl
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

; IX actual, IY expected, DE byte count, C reason. One check per byte.
assert_memory:
@loop:
    ld a,d
    or e
    ret z
    ld a,(ix+0)
    ld b,(iy+0)
    call assert_equal
    inc ix
    inc iy
    dec.s de
    jr @loop

; A=actual, B=expected, C=reason. Preserve the first compact diagnostic.
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
    jr z,@return
    ld hl,result_errors
    inc (hl)
    jr nz,@first
    inc hl
    inc (hl)
@first:
    ld a,(test_phase)
    or a
    jr z,@vector_bucket
    dec a
    cp 6
    jr nc,@vector_bucket
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,result_phase_errors
    add hl,de
    inc (hl)
@vector_bucket:
    ld a,(test_phase)
    cp phase_vector
    jr nz,@first_diagnostic
    ld a,(test_detail)
    or a
    jr z,@first_diagnostic
    dec a
    cp W3D_PATROL_VECTOR_COUNT
    jr nc,@first_diagnostic
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,result_vector_errors
    add hl,de
    inc (hl)
@first_diagnostic:
    ld a,(result_first_reason)
    or a
    jr nz,@return
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

; Required by the interactive motion include, not exercised by this fixture.
w3d_mark_render_submitted:
    ret
w3d_audio_begin_quantum:
    ret
w3d_audio_request:
w3d_audio_request_actor:
w3d_audio_request_tile:
    or a
    ret
w3d_elapsed_ticks:
    dl 0
w3d_exit_requested:
    db 0

expected_vector_header:
    db "W3PV"
    dw 1
    dw 192
expected_cadence:
    db 2,2,3,2,2,3
static_masks:
    db 1,2,4,8,16,32,64,128

result_filename:            asciz "patrol_result.bin"
report_banner:              asciz "\r\nWolf3D eZ80 patrol regression: "
report_pass:                asciz "PASS\r\n"
report_fail:                asciz "FAIL\r\n"

output_handle:              db 0
test_phase:                 db 0
test_detail:                db 0
test_actor_id:              db 0
test_door_index:            db W3D_SLOT_NONE
vectors_left:               db 0
patches_left:               db 0
vector_ptr:                 dl 0
patch_ptr:                  dl 0
test_steps:                 dl 0
test_static_mask:           db 0
assert_expected:            db 0
assert_actual:              db 0
prt_vector:                 dl 0
prt_saved_vector:           db 0,0,0,0
prt_irq_counter:            dl 0

result_data:
    db "W3P1"
result_checks:              dw 0
result_errors:              dw 0
result_first_phase:         db 0
result_first_reason:        db 0
result_first_expected:      db 0
result_first_actual:        db 0
result_first_detail:        db 0
                            db 0,0,0
result_vector_errors:       ds W3D_PATROL_VECTOR_COUNT
result_phase_errors:        ds 6
result_e1l1_milliseconds:   dl 0
                            db 0
result_end:

test_tilemap:
    ds W3D_MAP_BYTES
test_path_directions:
    ds W3D_MAP_BYTES
test_area_map:
    ds W3D_MAP_BYTES
test_static_bits:
    ds 512
