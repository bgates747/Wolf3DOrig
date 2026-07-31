; Directed real-eZ80 regression for production Wolf3D door-use resolution.
;
; The center-plane collision model permits the player's center to enter a
; door cell.  These cases call the real w3d_use_adjacent_door and
; w3d_handle_use_edge routines and prove that Space continues to resolve that
; current-cell door before falling back to the original cardinal neighbour.

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

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    include "wolf3d_sight.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_actors.inc"
    include "wolf3d_areas.inc"
    include "wolf3d_actor_sim.inc"
    include "wolf3d_motion.inc"

use_case_count:     equ 13

reason_index:       equ 1
reason_action:      equ 2
reason_target_dirty: equ 3
reason_dirty_sum:   equ 4
reason_world_dirty: equ 5
reason_timer_low:   equ 6
reason_timer_high:  equ 7
reason_latch:       equ 8

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
    ld (result_records),a
    ld (result_errors),a
    ld (result_first_reason),a
    ld (result_first_expected),a
    ld (result_first_actual),a
    dec a
    ld (result_first_case),a

    call case_current_near_well
    call case_current_far_well
    call case_adjacent_west
    call case_adjacent_east
    call case_adjacent_north
    call case_adjacent_south
    call case_floor_fallback
    call case_invalid_current_fails_closed
    call case_locked_refused
    call case_key_allows
    call case_opening_ignored
    call case_open_starts_closing
    call case_use_edge_latch

    call write_result
    call print_report
    ret

; Reset every authoritative field used by door operation. Door zero defaults
; to a closed vertical door at (10,10), with a nonzero timer so successful
; opening must visibly clear it. The tilemap starts entirely open.
begin_case:
    xor a
    ld (case_failed),a
    ld hl,test_tilemap
    ld (hl),a
    ld de,test_tilemap+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,test_tilemap
    ld (w3d_map_ptr),hl

    ld hl,test_static_bits
    ld (hl),a
    ld de,test_static_bits+1
    ld bc,511
    ldir
    ld hl,test_static_bits
    ld (w3d_static_blocking_ptr),hl

; Door close now consults the authoritative actor planes. This harness wants
; an intentionally empty world, so initialize both rather than relying on
; assembler-fill bytes in the actorat reservation storage.
    ld hl,w3d_actorat
    ld (hl),a
    ld de,w3d_actorat+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    dec a
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
    inc a

    ld hl,w3d_doors
    ld (hl),a
    ld de,w3d_doors+1
    ld bc,W3D_FIXTURE_DOOR_COUNT*W3D_DOOR_SIZE-1
    ldir
    ld hl,w3d_doors
    ld (w3d_doors_ptr),hl
    ld hl,w3d_door_dirty
    ld (hl),a
    ld de,w3d_door_dirty+1
    ld bc,W3D_FIXTURE_DOOR_COUNT-1
    ldir
    ld hl,w3d_door_timers
    ld (hl),a
    ld de,w3d_door_timers+1
    ld bc,W3D_FIXTURE_DOOR_COUNT*2-1
    ldir

    ld (w3d_world_dirty),a
    ld (w3d_use_was_down),a
    ld (w3d_controls),a
    ld (w3d_player_key_flags),a
    dec a
    ld (w3d_current_door_index),a

    ld a,10
    ld (w3d_doors+W3D_DOOR_TILEX),a
    ld (w3d_doors+W3D_DOOR_TILEY),a
    ld a,1
    ld (w3d_doors+W3D_DOOR_VERTICAL),a
    xor a
    ld (w3d_doors+W3D_DOOR_LOCK),a
    ld (w3d_doors+W3D_DOOR_ACTION),a
    ld (w3d_doors+W3D_DOOR_POSITION+0),a
    ld (w3d_doors+W3D_DOOR_POSITION+1),a
    ld a,034h
    ld (w3d_door_timers+0),a
    ld a,012h
    ld (w3d_door_timers+1),a
    ret

; Set player X/Y to tile 10.5,10.5 and angle zero.
pose_center:
    xor a
    ld (w3d_player_pose+0),a
    ld a,080h
    ld (w3d_player_pose+1),a
    ld a,10
    ld (w3d_player_pose+2),a
    xor a
    ld (w3d_player_pose+3),a
    ld (w3d_player_pose+4),a
    ld a,080h
    ld (w3d_player_pose+5),a
    ld a,10
    ld (w3d_player_pose+6),a
    xor a
    ld (w3d_player_pose+7),a
    ld (w3d_player_pose+8),a
    ld (w3d_player_pose+9),a
    ret

; Install door zero in its authoritative cell.
map_door_at_10_10:
    ld a,080h
    ld (test_tilemap+650),a       ; 10*64 + 10
    ret

; Common expectation for opening closed door zero.
expect_opening_zero:
    xor a
    ld (expected_index),a
    ld a,W3D_DOOR_ACTION_OPENING
    ld (expected_action),a
    ld a,1
    ld (expected_dirty),a
    ld (expected_world),a
    xor a
    ld (expected_timer+0),a
    ld (expected_timer+1),a
    jp validate_standard

expect_unchanged_unselected:
    ld a,0ffh
    ld (expected_index),a
    xor a
    ld (expected_action),a
    ld (expected_dirty),a
    ld (expected_world),a
    ld a,034h
    ld (expected_timer+0),a
    ld a,012h
    ld (expected_timer+1),a
    jp validate_standard

expect_unchanged_selected:
    xor a
    ld (expected_index),a
    ld (expected_action),a
    ld (expected_dirty),a
    ld (expected_world),a
    ld a,034h
    ld (expected_timer+0),a
    ld a,012h
    ld (expected_timer+1),a
    jp validate_standard

case_current_near_well:
    call begin_case
    call pose_center
    call map_door_at_10_10
    ld a,020h                    ; x = 10.125, reachable near-well step
    ld (w3d_player_pose+1),a
    call w3d_use_adjacent_door
    call expect_opening_zero
    jp finish_case

case_current_far_well:
    call begin_case
    call pose_center
    call map_door_at_10_10
    ld a,0e0h                    ; x = 10.875, reachable far-well step
    ld (w3d_player_pose+1),a
    ld a,180
    ld (w3d_player_pose+8),a
    call w3d_use_adjacent_door
    call expect_opening_zero
    jp finish_case

case_adjacent_west:
    call begin_case
    call pose_center
    call map_door_at_10_10
    ld a,0f0h                    ; x = 9.f000, face east
    ld (w3d_player_pose+1),a
    ld a,9
    ld (w3d_player_pose+2),a
    call w3d_use_adjacent_door
    call expect_opening_zero
    jp finish_case

case_adjacent_east:
    call begin_case
    call pose_center
    call map_door_at_10_10
    ld a,010h                    ; x = 11.1000, face west
    ld (w3d_player_pose+1),a
    ld a,11
    ld (w3d_player_pose+2),a
    ld a,180
    ld (w3d_player_pose+8),a
    call w3d_use_adjacent_door
    call expect_opening_zero
    jp finish_case

case_adjacent_north:
    call begin_case
    call pose_center
    call map_door_at_10_10
    xor a
    ld (w3d_doors+W3D_DOOR_VERTICAL),a
    ld a,0f0h                    ; y = 9.f000, face south
    ld (w3d_player_pose+5),a
    ld a,9
    ld (w3d_player_pose+6),a
    ld a,270 & 0ffh
    ld (w3d_player_pose+8),a
    ld a,270 >> 8
    ld (w3d_player_pose+9),a
    call w3d_use_adjacent_door
    call expect_opening_zero
    jp finish_case

case_adjacent_south:
    call begin_case
    call pose_center
    call map_door_at_10_10
    xor a
    ld (w3d_doors+W3D_DOOR_VERTICAL),a
    ld a,010h                    ; y = 11.1000, face north
    ld (w3d_player_pose+5),a
    ld a,11
    ld (w3d_player_pose+6),a
    ld a,90
    ld (w3d_player_pose+8),a
    call w3d_use_adjacent_door
    call expect_opening_zero
    jp finish_case

case_floor_fallback:
    call begin_case
    call pose_center
    call map_door_at_10_10
    ld a,9                       ; ordinary current floor tile, face east
    ld (w3d_player_pose+2),a
    call w3d_use_adjacent_door
    call expect_opening_zero
    jp finish_case

case_invalid_current_fails_closed:
    call begin_case
    call pose_center
    ; Current value is in the door range but index 22 is outside this fixture.
    ld a,096h
    ld (test_tilemap+650),a
    ld a,080h                    ; a tempting valid adjacent door at (11,10)
    ld (test_tilemap+651),a
    ld a,11
    ld (w3d_doors+W3D_DOOR_TILEX),a
    call w3d_use_adjacent_door
    call expect_unchanged_unselected
    jp finish_case

case_locked_refused:
    call begin_case
    call pose_center
    call map_door_at_10_10
    ld a,1
    ld (w3d_doors+W3D_DOOR_LOCK),a
    call w3d_use_adjacent_door
    call expect_unchanged_selected
    jp finish_case

case_key_allows:
    call begin_case
    call pose_center
    call map_door_at_10_10
    ld a,1
    ld (w3d_doors+W3D_DOOR_LOCK),a
    ld (w3d_player_key_flags),a
    call w3d_use_adjacent_door
    call expect_opening_zero
    jp finish_case

case_opening_ignored:
    call begin_case
    call pose_center
    call map_door_at_10_10
    ld a,W3D_DOOR_ACTION_OPENING
    ld (w3d_doors+W3D_DOOR_ACTION),a
    call w3d_use_adjacent_door
    xor a
    ld (expected_index),a
    ld a,W3D_DOOR_ACTION_OPENING
    ld (expected_action),a
    xor a
    ld (expected_dirty),a
    ld (expected_world),a
    ld a,034h
    ld (expected_timer+0),a
    ld a,012h
    ld (expected_timer+1),a
    call validate_standard
    jp finish_case

case_open_starts_closing:
    call begin_case
    call pose_center
    call map_door_at_10_10
    ; Stand outside the plane so close obstruction is clear.
    ld a,0f0h
    ld (w3d_player_pose+1),a
    ld a,9
    ld (w3d_player_pose+2),a
    ld a,W3D_DOOR_ACTION_OPEN
    ld (w3d_doors+W3D_DOOR_ACTION),a
    ld a,0ffh
    ld (w3d_doors+W3D_DOOR_POSITION+0),a
    ld (w3d_doors+W3D_DOOR_POSITION+1),a
    call w3d_use_adjacent_door
    xor a
    ld (expected_index),a
    ld a,W3D_DOOR_ACTION_CLOSING
    ld (expected_action),a
    ld a,1
    ld (expected_dirty),a
    ld (expected_world),a
    ld a,034h                    ; starting close does not reset open timer
    ld (expected_timer+0),a
    ld a,012h
    ld (expected_timer+1),a
    call validate_standard
    jp finish_case

case_use_edge_latch:
    call begin_case
    call pose_center
    call map_door_at_10_10
    ld a,020h                    ; inside the reachable current-door well
    ld (w3d_player_pose+1),a
    ld a,W3D_CONTROL_USE
    ld (w3d_controls),a
    call w3d_handle_use_edge
    call expect_opening_zero
    ld a,(w3d_use_was_down)
    ld b,1
    ld c,reason_latch
    call assert_equal

    ; Reset authoritative door state behind a still-held latch. A second
    ; sample must not operate it again.
    xor a
    ld (w3d_doors+W3D_DOOR_ACTION),a
    ld (w3d_door_dirty),a
    ld (w3d_world_dirty),a
    ld a,078h
    ld (w3d_door_timers+0),a
    ld a,056h
    ld (w3d_door_timers+1),a
    call w3d_handle_use_edge
    ld a,(w3d_doors+W3D_DOOR_ACTION)
    ld b,W3D_DOOR_ACTION_CLOSED
    ld c,reason_action
    call assert_equal
    ld a,(w3d_door_dirty)
    ld b,0
    ld c,reason_target_dirty
    call assert_equal
    ld a,(w3d_world_dirty)
    ld b,0
    ld c,reason_world_dirty
    call assert_equal
    ld a,(w3d_door_timers+0)
    ld b,078h
    ld c,reason_timer_low
    call assert_equal
    ld a,(w3d_door_timers+1)
    ld b,056h
    ld c,reason_timer_high
    call assert_equal

    ; A sampled release re-arms exactly one new press.
    xor a
    ld (w3d_controls),a
    call w3d_handle_use_edge
    ld a,(w3d_use_was_down)
    ld b,0
    ld c,reason_latch
    call assert_equal
    ld a,W3D_CONTROL_USE
    ld (w3d_controls),a
    call w3d_handle_use_edge
    ld a,(w3d_doors+W3D_DOOR_ACTION)
    ld b,W3D_DOOR_ACTION_OPENING
    ld c,reason_action
    call assert_equal
    ld a,(w3d_use_was_down)
    ld b,1
    ld c,reason_latch
    call assert_equal
    ld a,(w3d_door_timers+0)
    ld b,0
    ld c,reason_timer_low
    call assert_equal
    ld a,(w3d_door_timers+1)
    ld b,0
    ld c,reason_timer_high
    call assert_equal
    jp finish_case

validate_standard:
    ld a,(expected_index)
    ld b,a
    ld a,(w3d_current_door_index)
    ld c,reason_index
    call assert_equal
    ld a,(expected_action)
    ld b,a
    ld a,(w3d_doors+W3D_DOOR_ACTION)
    ld c,reason_action
    call assert_equal
    ld a,(expected_dirty)
    ld b,a
    ld a,(w3d_door_dirty)
    ld c,reason_target_dirty
    call assert_equal

    ld hl,w3d_door_dirty
    ld b,W3D_FIXTURE_DOOR_COUNT
    ld d,0
@dirty_sum:
    ld a,(hl)
    add a,d
    ld d,a
    inc hl
    djnz @dirty_sum
    ld a,(expected_dirty)
    ld b,a
    ld a,d
    ld c,reason_dirty_sum
    call assert_equal

    ld a,(expected_world)
    ld b,a
    ld a,(w3d_world_dirty)
    ld c,reason_world_dirty
    call assert_equal
    ld a,(expected_timer+0)
    ld b,a
    ld a,(w3d_door_timers+0)
    ld c,reason_timer_low
    call assert_equal
    ld a,(expected_timer+1)
    ld b,a
    ld a,(w3d_door_timers+1)
    ld c,reason_timer_high
    jp assert_equal

finish_case:
    ld a,(result_records)
    inc a
    ld (result_records),a
    ret

; A=actual, B=expected, C=reason. Record at most one error per case.
assert_equal:
    cp b
    ret z
    ld (assert_actual),a
    ld a,b
    ld (assert_expected),a
    ld a,(case_failed)
    or a
    ret nz
    ld a,1
    ld (case_failed),a
    ld a,(result_errors)
    or a
    jr nz,@count
    ld a,(result_records)
    ld (result_first_case),a
    ld a,c
    ld (result_first_reason),a
    ld a,(assert_expected)
    ld (result_first_expected),a
    ld a,(assert_actual)
    ld (result_first_actual),a
@count:
    ld a,(result_errors)
    inc a
    ld (result_errors),a
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
    ld a,(result_errors)
    or a
    ld hl,report_pass
    jr z,@emit
    ld hl,report_fail
@emit:
    call print_string
    ret

print_string:
    push bc
    ld bc,0
    ld a,0
    rst.lil 18h
    pop bc
    ret

; Required by the included interactive module but not exercised here.
w3d_mark_render_submitted:
    ret
w3d_elapsed_ticks:
    dl 0
w3d_exit_requested:
    db 0

result_filename:        asciz "use_result.bin"
report_banner:          asciz "\r\nWolf3D eZ80 door-use regression: "
report_pass:            asciz "PASS\r\n"
report_fail:            asciz "FAIL\r\n"

output_handle:          db 0
case_failed:            db 0
expected_index:         db 0
expected_action:        db 0
expected_dirty:         db 0
expected_world:         db 0
expected_timer:         dw 0
assert_expected:        db 0
assert_actual:          db 0

result_data:
    db "W3U1"
result_records:         db 0
result_errors:          db 0
result_first_case:      db 0ffh
result_first_reason:    db 0
result_first_expected:  db 0
result_first_actual:    db 0
                        db 0,0,0,0,0,0
result_end:

test_tilemap:
    ds W3D_MAP_BYTES
test_static_bits:
    ds 512
