; Directed real-eZ80 regression for the production Wolf3D actor pool.
;
; This harness includes and calls wolf3d_actors.inc without copying any of its
; implementation.  It validates the generated E1L1 seed, list and occupancy
; invariants, pointer helpers, allocation/lifetime semantics, actor collision,
; and the exact durable subcommand-4/subcommand-5 buffers.  The latter are
; inspected immediately after the synchronous VDU send returns: the command
; buffers are the bytes passed to RST.LIL 18h, not a test-side reconstruction.

    assume adl=1
    org 0x040000
    jp start
    align 64
    db "MOS",0,1

mos_fopen:          equ 0x0a
mos_fclose:         equ 0x0b
mos_fwrite:         equ 0x1b
fa_write:           equ 0x02
fa_create_always:   equ 0x08

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    include "wolf3d_world.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_actors.inc"

phase_initialize:       equ 1
phase_pointer:          equ 2
phase_lifetime:         equ 3
phase_exhaustion:       equ 4
phase_collision:        equ 5
phase_wire:             equ 6

reason_scalar:          equ 1
reason_memory:          equ 2
reason_list:            equ 3
reason_free_record:     equ 4
reason_occupancy:       equ 5
reason_dirty:           equ 6
reason_pointer:         equ 7
reason_carry:           equ 8
reason_collision:       equ 9
reason_wire_prefix:     equ 10
reason_wire_payload:    equ 11
reason_wire_length:     equ 12

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
    ld (result_checks+0),a
    ld (result_checks+1),a
    ld (result_errors+0),a
    ld (result_errors+1),a
    ld (result_first_phase),a
    ld (result_first_reason),a
    ld (result_first_expected),a
    ld (result_first_actual),a
    ld (result_first_detail),a

    call test_initialize
    call test_pointer_helpers
    call test_lifetime
    call test_exhaustion
    call test_collision
    call test_wire_commands
    call write_result
    call print_report
    ret

; ---------------------------------------------------------------------------
; Generated E1L1 initialization -- validate every authoritative byte.
; ---------------------------------------------------------------------------

test_initialize:
    ld a,phase_initialize
    ld (test_phase),a
    xor a
    ld (w3d_world_dirty),a
    call w3d_initialize_actor_state

    ld a,(w3d_actor_count)
    ld b,W3D_FIXTURE_ACTOR_COUNT
    ld c,reason_scalar
    call assert_equal
    ld a,(w3d_actor_live_head)
    ld b,1
    ld c,reason_list
    call assert_equal
    ld a,(w3d_actor_live_tail)
    ld b,W3D_FIXTURE_ACTOR_COUNT
    ld c,reason_list
    call assert_equal
    ld a,(w3d_actor_free_head)
    ld b,W3D_FIXTURE_ACTOR_COUNT+1
    ld c,reason_list
    call assert_equal

; Slot zero must contain only the reserved-player ownership fields.
    xor a
    ld hl,expected_slot_zero
    ld (hl),a
    ld de,expected_slot_zero+1
    ld bc,W3D_ACTOR_SIZE-1
    ldir
    ld a,W3D_ACTOR_ACTIVE_ALWAYS
    ld (expected_slot_zero+W3D_ACTOR_ACTIVE),a
    ld a,W3D_SLOT_NONE
    ld (expected_slot_zero+W3D_ACTOR_NEXT),a
    ld (expected_slot_zero+W3D_ACTOR_PREV),a
    ld ix,w3d_actors
    ld iy,expected_slot_zero
    ld de,W3D_ACTOR_SIZE
    ld c,reason_memory
    call assert_memory

; Slots 1..count are an exact byte copy of the generated fixture, including
; stable forward/backward live links and patrol destination reservations.
    ld ix,w3d_actors+W3D_ACTOR_SIZE
    ld iy,w3d_fixture_initial_actors
    ld de,w3d_fixture_initial_actors_end-w3d_fixture_initial_actors
    ld c,reason_memory
    call assert_memory

; Every free record is otherwise zero, ACTIVE/NEXT are 0xff, and PREV is the
; next free slot (or 0xff at the end).  Validate all 39 bytes in all 128 slots.
    xor a
    ld hl,expected_free_record
    ld (hl),a
    ld de,expected_free_record+1
    ld bc,W3D_ACTOR_SIZE-1
    ldir
    ld a,W3D_ACTOR_ACTIVE_FREE
    ld (expected_free_record+W3D_ACTOR_ACTIVE),a
    ld a,W3D_SLOT_NONE
    ld (expected_free_record+W3D_ACTOR_NEXT),a
    ld a,W3D_FIXTURE_ACTOR_COUNT+1
    ld (test_slot),a
@free_slot:
    ld a,(test_slot)
    inc a
    cp W3D_MAX_ACTORS
    jr c,@free_successor
    ld a,W3D_SLOT_NONE
@free_successor:
    ld (expected_free_record+W3D_ACTOR_PREV),a
    ld a,(test_slot)
    ld (test_detail),a
    call w3d_actor_pointer_from_id
    ld iy,expected_free_record
    ld de,W3D_ACTOR_SIZE
    ld c,reason_free_record
    call assert_memory
    ld a,(test_slot)
    inc a
    ld (test_slot),a
    cp W3D_MAX_ACTORS
    jr c,@free_slot

; Build expected actorat independently from the generated fixture records,
; then compare all 4096 cells.  This detects missing, extra and stale claims.
    xor a
    ld hl,expected_actorat
    ld (hl),a
    ld de,expected_actorat+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld ix,w3d_fixture_initial_actors
    ld a,1
    ld (test_slot),a
@build_actorat:
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_NEVERMARK
    jr nz,@next_fixture_actor
    ld hl,0
    ld l,(ix+W3D_ACTOR_TILEY)
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    ld de,0
    ld e,(ix+W3D_ACTOR_TILEX)
    add.s hl,de
    ld de,expected_actorat
    add hl,de
    ld a,(test_slot)
    ld (hl),a
@next_fixture_actor:
    lea ix,ix+W3D_ACTOR_SIZE
    ld a,(test_slot)
    inc a
    ld (test_slot),a
    cp W3D_FIXTURE_ACTOR_COUNT+1
    jr c,@build_actorat
    ld ix,w3d_actorat
    ld iy,expected_actorat
    ld de,W3D_MAP_BYTES
    ld c,reason_occupancy
    call assert_memory

; No seed starts dirty, and actor initialization must not dirty the world.
    xor a
    ld hl,expected_zeroes
    ld (hl),a
    ld de,expected_zeroes+1
    ld bc,W3D_MAX_ACTORS-1
    ldir
    ld ix,w3d_actor_dirty
    ld iy,expected_zeroes
    ld de,W3D_MAX_ACTORS
    ld c,reason_dirty
    call assert_memory
    ld a,(w3d_world_dirty)
    ld b,0
    ld c,reason_dirty
    jp assert_equal

; ---------------------------------------------------------------------------
; Stable id -> record/state pointer helpers.
; ---------------------------------------------------------------------------

test_pointer_helpers:
    ld a,phase_pointer
    ld (test_phase),a

    xor a
    ld (test_detail),a
    call w3d_actor_pointer_from_id
    ld hl,w3d_actors
    call assert_ix_equals_hl
    ld a,1
    ld (test_detail),a
    call w3d_actor_pointer_from_id
    ld hl,w3d_actors+W3D_ACTOR_SIZE
    call assert_ix_equals_hl
    ld a,149
    ld (test_detail),a
    call w3d_actor_pointer_from_id
    ld hl,w3d_actors+5811       ; 149 * 39, kept literal for assembler precedence
    call assert_ix_equals_hl

    xor a
    ld (test_detail),a
    call w3d_actor_state_pointer_from_id
    ld hl,w3d_actor_states
    call assert_iy_equals_hl
    ld a,W3D_STATE_COUNT-1
    ld (test_detail),a
    call w3d_actor_state_pointer_from_id
    ld hl,w3d_actor_states+800  ; 100 * 8, literal avoids assembler precedence
    call assert_iy_equals_hl
    ld a,W3D_STATE_COUNT
    ld (test_detail),a
    call w3d_actor_state_pointer_from_id
    ld hl,w3d_actor_states
    call assert_iy_equals_hl
    ld a,0ffh
    ld (test_detail),a
    call w3d_actor_state_pointer_from_id
    ld hl,w3d_actor_states
    call assert_iy_equals_hl

; Also validate representative metadata at both ends of the table.
    ld a,1
    call w3d_actor_state_pointer_from_id
    ld a,(iy+W3D_STATE_SHAPENUM+0)
    ld b,50
    ld c,reason_pointer
    call assert_equal
    ld a,(iy+W3D_STATE_ROTATIONS)
    ld b,8
    ld c,reason_pointer
    call assert_equal
    ld a,W3D_STATE_COUNT-1
    call w3d_actor_state_pointer_from_id
    ld a,(iy+W3D_STATE_SHAPENUM+0)
    ld b,0bah                         ; SS shoot9 shape 186
    ld c,reason_pointer
    call assert_equal
    ld a,(iy+W3D_STATE_SHAPENUM+1)
    ld b,0
    ld c,reason_pointer
    jp assert_equal

; ---------------------------------------------------------------------------
; Allocate/publish/free and dirty lifecycle semantics.
; ---------------------------------------------------------------------------

test_lifetime:
    ld a,phase_lifetime
    ld (test_phase),a
    xor a
    ld (w3d_world_dirty),a
    call w3d_initialize_actor_state

; First free slot is 22; allocation detaches and zeroes it.
    call w3d_actor_alloc
    ld (test_actual),a
    ld a,0
    jr nc,@alloc_no_carry
    inc a
@alloc_no_carry:
    ld b,1
    ld c,reason_carry
    call assert_equal
    ld a,(test_actual)
    ld b,W3D_FIXTURE_ACTOR_COUNT+1
    ld c,reason_scalar
    call assert_equal
    xor a
    ld hl,expected_detached_record
    ld (hl),a
    ld de,expected_detached_record+1
    ld bc,W3D_ACTOR_SIZE-1
    ldir
    ld a,W3D_SLOT_NONE
    ld (expected_detached_record+W3D_ACTOR_NEXT),a
    ld (expected_detached_record+W3D_ACTOR_PREV),a
    ld a,W3D_FIXTURE_ACTOR_COUNT+1
    call w3d_actor_pointer_from_id
    ld iy,expected_detached_record
    ld de,W3D_ACTOR_SIZE
    ld c,reason_memory
    call assert_memory

; Publish slot 22 as a markable actor at (60,60).
    ld a,W3D_FIXTURE_ACTOR_COUNT+1
    call w3d_actor_pointer_from_id
    ld (ix+W3D_ACTOR_TILEX),60
    ld (ix+W3D_ACTOR_TILEY),60
    ld (ix+W3D_ACTOR_ACTIVE),W3D_ACTOR_ACTIVE_YES
    ld (ix+W3D_ACTOR_FLAGS),W3D_ACTOR_FLAG_SHOOTABLE
    ld (ix+W3D_ACTOR_STATE+0),W3D_STATE_GRD_STAND
    ld a,W3D_FIXTURE_ACTOR_COUNT+1
    call w3d_actor_publish
    ld a,(w3d_actor_count)
    ld b,W3D_FIXTURE_ACTOR_COUNT+1
    ld c,reason_list
    call assert_equal
    ld a,(w3d_actor_live_tail)
    ld b,W3D_FIXTURE_ACTOR_COUNT+1
    ld c,reason_list
    call assert_equal
    ld a,W3D_FIXTURE_ACTOR_COUNT
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_NEXT)
    ld b,W3D_FIXTURE_ACTOR_COUNT+1
    ld c,reason_list
    call assert_equal
    ld b,60
    ld c,60
    call w3d_actorat_get
    ld b,W3D_FIXTURE_ACTOR_COUNT+1
    ld c,reason_occupancy
    call assert_equal
    ld a,W3D_FIXTURE_ACTOR_COUNT+1
    call w3d_actor_dirty_address
    ld a,(hl)
    ld b,W3D_ACTOR_DIRTY_SET
    ld c,reason_dirty
    call assert_equal

; Slot 23 is NEVERMARK: it joins the live list but must not claim actorat.
    call w3d_actor_alloc
    ld (test_actual),a
    ld a,(test_actual)
    call w3d_actor_pointer_from_id
    ld (ix+W3D_ACTOR_TILEX),60
    ld (ix+W3D_ACTOR_TILEY),59
    ld (ix+W3D_ACTOR_ACTIVE),W3D_ACTOR_ACTIVE_YES
    ld (ix+W3D_ACTOR_FLAGS),W3D_ACTOR_FLAG_NEVERMARK
    ld a,(test_actual)
    call w3d_actor_publish
    ld b,60
    ld c,59
    call w3d_actorat_get
    ld b,0
    ld c,reason_occupancy
    call assert_equal

; Remove live middle slot 10. Return/retained NEXT=11 is the original loop's
; safe self-removal contract; neighbors must bypass it in both directions.
    ld a,10
    call w3d_actor_pointer_from_id
    ld a,10
    call w3d_actor_free
    ld b,11
    ld c,reason_list
    call assert_equal
    ld a,10
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_NEXT)
    ld b,11
    ld c,reason_list
    call assert_equal
    ld a,(ix+W3D_ACTOR_ACTIVE)
    ld b,W3D_ACTOR_ACTIVE_FREE
    ld c,reason_free_record
    call assert_equal
    ld a,9
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_NEXT)
    ld b,11
    ld c,reason_list
    call assert_equal
    ld a,11
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_PREV)
    ld b,9
    ld c,reason_list
    call assert_equal
    ld a,(w3d_actor_free_head)
    ld b,10
    ld c,reason_list
    call assert_equal
    ld a,10
    call w3d_actor_dirty_address
    ld a,(hl)
    ld b,W3D_ACTOR_DIRTY_REMOVE
    ld c,reason_dirty
    call assert_equal

; SET followed by free must collapse to REMOVE. Reallocating and publishing
; that same slot before submission must replace REMOVE with a full SET.
    ld a,1
    call w3d_actor_mark_dirty
    ld a,1
    call w3d_actor_pointer_from_id
    ld a,1
    call w3d_actor_free
    ld a,1
    call w3d_actor_dirty_address
    ld a,(hl)
    ld b,W3D_ACTOR_DIRTY_REMOVE
    ld c,reason_dirty
    call assert_equal
    call w3d_actor_alloc
    ld (test_actual),a
    ld b,1
    ld c,reason_scalar
    call assert_equal
    ld a,1
    call w3d_actor_pointer_from_id
    ld (ix+W3D_ACTOR_TILEX),60
    ld (ix+W3D_ACTOR_TILEY),58
    ld (ix+W3D_ACTOR_ACTIVE),W3D_ACTOR_ACTIVE_YES
    ld (ix+W3D_ACTOR_FLAGS),W3D_ACTOR_FLAG_SHOOTABLE
    ld a,1
    call w3d_actor_publish
    ld a,1
    call w3d_actor_dirty_address
    ld a,(hl)
    ld b,W3D_ACTOR_DIRTY_SET
    ld c,reason_dirty
    call assert_equal
    ld b,60
    ld c,58
    call w3d_actorat_get
    ld b,1
    ld c,reason_occupancy
    call assert_equal
    ld a,(w3d_world_dirty)
    ld b,1
    ld c,reason_dirty
    jp assert_equal

; ---------------------------------------------------------------------------
; Exhaust the free list, including carry behavior at the hard pool limit.
; ---------------------------------------------------------------------------

test_exhaustion:
    ld a,phase_exhaustion
    ld (test_phase),a
    call w3d_initialize_actor_state
    ld a,W3D_FIXTURE_ACTOR_COUNT+1
    ld (test_slot),a
@allocate_all:
    call w3d_actor_alloc
    ld (test_actual),a
    ld a,0
    jr nc,@missing_carry
    inc a
@missing_carry:
    ld b,1
    ld c,reason_carry
    call assert_equal
    ld a,(test_slot)
    ld b,a
    ld a,(test_actual)
    ld c,reason_scalar
    call assert_equal
    ld a,(test_slot)
    inc a
    ld (test_slot),a
    cp W3D_MAX_ACTORS
    jr c,@allocate_all
    ld a,(w3d_actor_free_head)
    ld b,W3D_SLOT_NONE
    ld c,reason_list
    call assert_equal
    call w3d_actor_alloc
    ld a,0
    jr nc,@full_carry_clear
    inc a
@full_carry_clear:
    ld b,0
    ld c,reason_carry
    jp assert_equal

; ---------------------------------------------------------------------------
; Original inclusive one-tile shootable-actor collision contract.
; ---------------------------------------------------------------------------

test_collision:
    ld a,phase_collision
    ld (test_phase),a
    call w3d_initialize_actor_state
    xor a
    ld hl,w3d_actorat
    ld (hl),a
    ld de,w3d_actorat+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld a,1
    call w3d_actor_pointer_from_id
    ld a,0
    ld (ix+W3D_ACTOR_X+0),a
    ld (ix+W3D_ACTOR_Y+0),a
    ld a,080h
    ld (ix+W3D_ACTOR_X+1),a
    ld (ix+W3D_ACTOR_Y+1),a
    ld a,10
    ld (ix+W3D_ACTOR_X+2),a
    ld (ix+W3D_ACTOR_Y+2),a
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld (ix+W3D_ACTOR_Y+3),a
    ld a,10
    ld (ix+W3D_ACTOR_TILEX),a
    ld (ix+W3D_ACTOR_TILEY),a

    ld iy,collision_cases
    ld a,collision_case_count
    ld (test_cases_left),a
    xor a
    ld (test_detail),a
@collision_case:
    push iy
    pop hl
    ld de,collision_candidate
    ld bc,8
    ldir
    ld a,1
    call w3d_actor_pointer_from_id
    ld a,(iy+8)
    ld (ix+W3D_ACTOR_FLAGS),a
    ld hl,w3d_actorat+650
    ld a,(iy+9)
    ld (hl),a
    ; Production receives the candidate AABB tile bounds from the motion
    ; clipper.  These directed centers are far from a tile-edge/radius
    ; crossover, so low==high is the exact pre-expansion bound.
    ld a,(iy+2)
    ld (w3d_clip_x_low),a
    ld (w3d_clip_x_high),a
    ld a,(iy+6)
    ld (w3d_clip_y_low),a
    ld (w3d_clip_y_high),a
    ld ix,collision_candidate
    call w3d_player_actors_clear
    ld b,(iy+10)
    ld c,reason_collision
    call assert_equal
    lea iy,iy+11
    ld a,(test_detail)
    inc a
    ld (test_detail),a
    ld a,(test_cases_left)
    dec a
    ld (test_cases_left),a
    jr nz,@collision_case

; Adversarial AABB crossovers.  The actor is exactly one tile from the player
; center but reserves a tile two cells from the player's center tile.  Only
; expanding the already-computed player AABB bounds (3x3 -> 4x4) finds it;
; the superseded center-tile scan misses these four symmetric cases.
    ld iy,collision_crossover_cases
    ld a,collision_crossover_case_count
    ld (test_cases_left),a
@crossover_case:
    xor a
    ld hl,w3d_actorat
    ld (hl),a
    ld de,w3d_actorat+1
    ld bc,W3D_MAP_BYTES-1
    ldir

    push iy
    pop hl
    ld de,collision_candidate
    ld bc,8
    ldir
    ld a,1
    call w3d_actor_pointer_from_id
    lea hl,iy+8
    push ix
    pop de
    ld bc,8
    ldir
    ld a,(iy+16)
    ld (ix+W3D_ACTOR_TILEX),a
    ld a,(iy+17)
    ld (ix+W3D_ACTOR_TILEY),a
    ld (ix+W3D_ACTOR_FLAGS),W3D_ACTOR_FLAG_SHOOTABLE
    ld a,1
    call w3d_actorat_claim

    ld a,(iy+18)
    ld (w3d_clip_x_low),a
    ld a,(iy+19)
    ld (w3d_clip_x_high),a
    ld a,(iy+20)
    ld (w3d_clip_y_low),a
    ld a,(iy+21)
    ld (w3d_clip_y_high),a
    ld ix,collision_candidate
    call w3d_player_actors_clear
    ld b,(iy+22)
    ld c,reason_collision
    call assert_equal
    lea iy,iy+23
    ld a,(test_detail)
    inc a
    ld (test_detail),a
    ld a,(test_cases_left)
    dec a
    ld (test_cases_left),a
    jp nz,@crossover_case
    ret

; ---------------------------------------------------------------------------
; Exact subcommand 4/5 command memory consumed by the production sender.
; ---------------------------------------------------------------------------

test_wire_commands:
    ld a,phase_wire
    ld (test_phase),a
    call w3d_initialize_actor_state
    ld a,1
    call w3d_actor_pointer_from_id
    ld (ix+W3D_ACTOR_X+0),011h
    ld (ix+W3D_ACTOR_X+1),022h
    ld (ix+W3D_ACTOR_X+2),033h
    ld (ix+W3D_ACTOR_X+3),044h
    ld (ix+W3D_ACTOR_Y+0),055h
    ld (ix+W3D_ACTOR_Y+1),066h
    ld (ix+W3D_ACTOR_Y+2),077h
    ld (ix+W3D_ACTOR_Y+3),088h
    ld (ix+W3D_ACTOR_STATE+0),W3D_STATE_GRD_STAND
    ld (ix+W3D_ACTOR_STATE+1),0
    ld (ix+W3D_ACTOR_DIR),W3D_DIR_SOUTHWEST
    ld a,1
    call w3d_actor_mark_dirty
    call w3d_submit_dirty_actors

    ld a,w3d_actor_set_end-w3d_actor_set_command
    ld b,7+W3D_ACTOR_WIRE_SIZE
    ld c,reason_wire_length
    call assert_equal
    ld ix,w3d_actor_set_command
    ld iy,expected_set_command_prefix
    ld de,7
    ld c,reason_wire_prefix
    call assert_memory
    ld ix,w3d_actor_wire_record
    ld iy,expected_wire_cardinal
    ld de,W3D_ACTOR_WIRE_SIZE
    ld c,reason_wire_payload
    call assert_memory
    ld a,1
    call w3d_actor_dirty_address
    ld a,(hl)
    ld b,W3D_ACTOR_DIRTY_NONE
    ld c,reason_dirty
    call assert_equal

; State zero's -1 base shape uses TEMP1, and NODIR uses continuous ANGLE.
    ld a,1
    call w3d_actor_pointer_from_id
    xor a
    ld (ix+W3D_ACTOR_STATE+0),a
    ld (ix+W3D_ACTOR_STATE+1),a
    ld (ix+W3D_ACTOR_DIR),W3D_DIR_NODIR
    ld (ix+W3D_ACTOR_TEMP1+0),034h
    ld (ix+W3D_ACTOR_TEMP1+1),012h
    ld (ix+W3D_ACTOR_ANGLE+0),067h
    ld (ix+W3D_ACTOR_ANGLE+1),001h
    ld a,1
    call w3d_actor_mark_dirty
    call w3d_submit_dirty_actors
    ld ix,w3d_actor_wire_record
    ld iy,expected_wire_continuous
    ld de,W3D_ACTOR_WIRE_SIZE
    ld c,reason_wire_payload
    call assert_memory

; Removal emits only the stable uint16 slot id via subcommand 5.
    ld a,1
    call w3d_actor_dirty_address
    ld (hl),W3D_ACTOR_DIRTY_REMOVE
    call w3d_submit_dirty_actors
    ld a,w3d_actor_remove_end-w3d_actor_remove_command
    ld b,9
    ld c,reason_wire_length
    call assert_equal
    ld ix,w3d_actor_remove_command
    ld iy,expected_remove_command
    ld de,9
    ld c,reason_wire_prefix
    call assert_memory
    ld a,1
    call w3d_actor_dirty_address
    ld a,(hl)
    ld b,W3D_ACTOR_DIRTY_NONE
    ld c,reason_dirty
    jp assert_equal

; ---------------------------------------------------------------------------
; Assertion/report support.
; ---------------------------------------------------------------------------

; IX=actual, IY=expected, DE=16-bit length, C=reason. IX/IY advance.
assert_memory:
@loop:
    ld a,(ix)
    ld b,(iy)
    call assert_equal
    lea ix,ix+1
    lea iy,iy+1
    dec.s de
    ld a,d
    or e
    jr nz,@loop
    ret

assert_ix_equals_hl:
    push ix
    pop de
    or a
    sbc hl,de
    ld a,0
    jr nz,@different
    inc a
@different:
    ld b,1
    ld c,reason_pointer
    jp assert_equal

assert_iy_equals_hl:
    push iy
    pop de
    or a
    sbc hl,de
    ld a,0
    jr nz,@different
    inc a
@different:
    ld b,1
    ld c,reason_pointer
    jp assert_equal

; A=actual, B=expected, C=reason. Records every check and mismatch, retaining
; a compact diagnostic for the first failure only.
assert_equal:
    ld (assert_actual),a
    ld a,b
    ld (assert_expected),a
    push hl
    ld hl,result_checks
    inc (hl)
    jr nz,@check_value
    inc hl
    inc (hl)
@check_value:
    ld a,(assert_actual)
    cp b
    jr z,@return
    ld hl,result_errors
    ld a,(hl)
    inc (hl)
    jr nz,@consider_first
    inc hl
    inc (hl)
@consider_first:
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

; The production include references this motion-owned flag.
w3d_world_dirty:
    db 0
w3d_clip_x_low:
    db 0
w3d_clip_x_high:
    db 0
w3d_clip_y_low:
    db 0
w3d_clip_y_high:
    db 0

result_filename:            asciz "actor_result.bin"
report_banner:              asciz "\r\nWolf3D eZ80 actor regression: "
report_pass:                asciz "PASS\r\n"
report_fail:                asciz "FAIL\r\n"

output_handle:              db 0
test_phase:                 db 0
test_detail:                db 0
test_slot:                  db 0
test_actual:                db 0
test_cases_left:            db 0
assert_expected:            db 0
assert_actual:              db 0

result_data:
    db "W3A1"
result_checks:              dw 0
result_errors:              dw 0
result_first_phase:         db 0
result_first_reason:        db 0
result_first_expected:      db 0
result_first_actual:        db 0
result_first_detail:        db 0
                            db 0,0,0
result_end:

expected_set_command_prefix:
    db 23,0,0a0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 04ah,4
expected_remove_command:
    db 23,0,0a0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 04ah,5
    dw 1

expected_wire_cardinal:
    dw 1                  ; actorId
    dw 50                 ; s_grdstand base shape
    db 011h,022h,033h,044h
    db 055h,066h,077h,088h
    dw 225                ; southwest
    db 8
expected_wire_continuous:
    dw 1
    dw 01234h             ; state-zero -1 shape -> TEMP1 override
    db 011h,022h,033h,044h
    db 055h,066h,077h,088h
    dw 359                ; NODIR -> continuous actor angle
    db 0

; x,y, actor flags, actorat cell value, expected clear result.
collision_cases:
    db 000h,080h,010,0, 000h,080h,010,0, W3D_ACTOR_FLAG_SHOOTABLE,0,1
    db 000h,080h,010,0, 000h,080h,010,0, W3D_ACTOR_FLAG_SHOOTABLE,1,0
    db 000h,080h,011,0, 000h,080h,010,0, W3D_ACTOR_FLAG_SHOOTABLE,1,0
    db 001h,080h,011,0, 000h,080h,010,0, W3D_ACTOR_FLAG_SHOOTABLE,1,1
    db 000h,080h,009,0, 000h,080h,010,0, W3D_ACTOR_FLAG_SHOOTABLE,1,0
    db 0ffh,07fh,009,0, 000h,080h,010,0, W3D_ACTOR_FLAG_SHOOTABLE,1,1
    db 000h,080h,010,0, 000h,080h,011,0, W3D_ACTOR_FLAG_SHOOTABLE,1,0
    db 000h,080h,010,0, 001h,080h,011,0, W3D_ACTOR_FLAG_SHOOTABLE,1,1
    db 000h,080h,010,0, 000h,080h,010,0, 0,1,1
    db 000h,080h,010,0, 000h,080h,010,0, W3D_ACTOR_FLAG_SHOOTABLE,150,0
    db 000h,080h,020,0, 000h,080h,020,0, W3D_ACTOR_FLAG_SHOOTABLE,1,1
collision_cases_end:
collision_case_count:       equ 11

; candidate x/y, actor x/y, cached x/y, clip xlo/xhi/ylo/yhi, expected.
; Radius 0x5800 makes .E000 cross the high tile boundary and .2000 cross the
; low boundary before w3d_player_actors_clear expands each side by one cell.
collision_crossover_cases:
    ; X high: candidate 10.E, actor 11.E, actor reserves x=12.
    db 000h,0e0h,10,0, 000h,080h,10,0
    db 000h,0e0h,11,0, 000h,080h,10,0
    db 12,10, 10,11,10,10, 0
    ; X low: candidate 10.2, actor 9.2, actor reserves x=8.
    db 000h,020h,10,0, 000h,080h,10,0
    db 000h,020h,9,0, 000h,080h,10,0
    db 8,10, 9,10,10,10, 0
    ; Y high: candidate 10.E, actor 11.E, actor reserves y=12.
    db 000h,080h,10,0, 000h,0e0h,10,0
    db 000h,080h,10,0, 000h,0e0h,11,0
    db 10,12, 10,10,10,11, 0
    ; Y low: candidate 10.2, actor 9.2, actor reserves y=8.
    db 000h,080h,10,0, 000h,020h,10,0
    db 000h,080h,10,0, 000h,020h,9,0
    db 10,8, 10,10,9,10, 0
collision_crossover_cases_end:
collision_crossover_case_count: equ 4

collision_candidate:        ds 8
expected_slot_zero:         ds W3D_ACTOR_SIZE
expected_free_record:       ds W3D_ACTOR_SIZE
expected_detached_record:   ds W3D_ACTOR_SIZE
expected_zeroes:            ds W3D_MAX_ACTORS
expected_actorat:           ds W3D_MAP_BYTES
