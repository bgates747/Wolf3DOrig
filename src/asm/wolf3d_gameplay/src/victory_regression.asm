; Directed real-eZ80 regression for EXITTILE movement and completion freeze.

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

    include "wolf3d_audio_assets.inc"
    include "wolf3d_sight.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_actors.inc"
    include "wolf3d_areas.inc"
    include "wolf3d_actor_sim.inc"
    include "wolf3d_motion.inc"
    include "wolf3d_player_combat.inc"

victory_case_count: equ 4

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
    ld hl,result_records
    ld (hl),a
    ld de,result_records+1
    ld bc,result_end-result_records-1
    ldir
    call initialize_world
    call case_adjacent_none
    call case_victory_latch
    call case_victory_stops_quantum
    call case_completion_freezes_catchup
    call write_result
    ret

initialize_world:
    xor a
    ld hl,test_tilemap
    ld (hl),a
    ld de,test_tilemap+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,test_tilemap
    ld (w3d_map_ptr),hl
    ld hl,test_paths
    ld (hl),W3D_PATH_NONE
    ld de,test_paths+1
    ld bc,W3D_MAP_BYTES-1
    ldir
; Previous LDIR leaves HL at test_paths+4095; bind the actual base explicitly.
    ld hl,test_paths
    ld (w3d_path_directions_ptr),hl
    ld hl,test_areas
    ld (w3d_area_map_ptr),hl
    ld hl,test_static_bits
    xor a
    ld (hl),a
    ld de,test_static_bits+1
    ld bc,W3D_MAP_BYTES/8-1
    ldir
    ld hl,test_static_bits
    ld (w3d_static_blocking_ptr),hl
    ld hl,w3d_actorat
    ld (hl),a
    ld de,w3d_actorat+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,w3d_doors
    ld (w3d_doors_ptr),hl
    xor a
    ld (w3d_level_actor_count),a
    ld (w3d_actor_live_head),a
    dec a
    ld (w3d_actor_live_head),a
    ret

reset_case:
    xor a
    ld (case_failed),a
    ld (w3d_level_completion),a
    ld (w3d_player_dead),a
    ld (w3d_player_dirty),a
    ld (w3d_world_dirty),a
    ld (w3d_pickup_scan_needed),a
    ld (w3d_player_weapon_shape_dirty),a
    ld (w3d_actor_tics_prepared),a
    ld (w3d_actor_tic_phase),a
    ld (w3d_area_topology_dirty),a
    ld (w3d_controls),a
    ld (w3d_use_was_down),a
    ld hl,w3d_keyboard_masks
    ld (hl),a
    ld de,w3d_keyboard_masks+1
    ld bc,15
    ldir
    ld a,1
    ld (w3d_player_weapon),a
    xor a
    ld (w3d_player_weapon_frame),a
    call w3d_player_combat_refresh_shape
    ld hl,0x000af000
    ld (w3d_player_pose+0),hl
    xor a
    ld (w3d_player_pose+3),a
    ld hl,0x000a8000
    ld (w3d_player_pose+4),hl
    ld (w3d_player_pose+7),a
    ld (w3d_player_pose+8),a
    ld (w3d_player_pose+9),a
; ez80asm evaluates mixed addition/multiplication left-to-right; use literal
; row-major offset 10*64+11 rather than a misleading symbolic expression.
    ld hl,test_paths+651
    ld (hl),W3D_PATH_NONE
    ret

finish_case:
    ld a,(result_records)
    inc a
    ld (result_records),a
    ret

; Moving east into an ordinary 0xff cell is a normal successful translation.
case_adjacent_none:
    call reset_case
    ld hl,test_delta_east
    call w3d_clip_move_delta24
    ld b,1
    ld c,1
    call assert_a
    ld a,(w3d_level_completion)
    ld b,W3D_LEVEL_COMPLETION_NONE
    ld c,2
    call assert_a
    ld a,(w3d_player_weapon_shape+0)
    ld b,421 & 0ffh
    ld c,3
    call assert_a
    jp finish_case

; The same accepted move onto 0xfe latches victory and hides the view weapon.
case_victory_latch:
    call reset_case
    ld hl,test_paths+651
    ld (hl),W3D_PATH_VICTORY
    ld hl,test_delta_east
    call w3d_clip_move_delta24
    ld b,1
    ld c,4
    call assert_a
    ld a,(w3d_level_completion)
    ld b,W3D_LEVEL_COMPLETION_VICTORY
    ld c,5
    call assert_a
    ld a,(w3d_player_weapon_shape+0)
    ld b,0ffh
    ld c,6
    call assert_a
    ld a,(w3d_player_weapon_shape+1)
    ld b,0ffh
    ld c,7
    call assert_a
    jp finish_case

; A W+D quantum reaches victory via forward movement. The D-axis request and
; every later subsystem must be skipped; Y therefore remains unchanged.
case_victory_stops_quantum:
    call reset_case
    ld hl,test_paths+651
    ld (hl),W3D_PATH_VICTORY
    ld a,W3D_CONTROL_W|W3D_CONTROL_D
    ld (w3d_controls),a
    ld a,2
    ld (w3d_keyboard_masks+4),a
    ld a,4
    ld (w3d_keyboard_masks+6),a
    call w3d_simulate_player_step
    ld a,(w3d_level_completion)
    ld b,W3D_LEVEL_COMPLETION_VICTORY
    ld c,8
    call assert_a
    ld a,(w3d_player_pose+6)
    ld b,10
    ld c,9
    call assert_a
    ld a,(w3d_pickup_scan_needed)
    ld b,1
    ld c,10
    call assert_a
    ld a,(w3d_actor_tics_prepared)
    ld b,0
    ld c,11
    call assert_a
    ld a,(w3d_actor_tic_phase)
    ld b,0
    ld c,12
    call assert_a
    jp finish_case

; A later catch-up fixed step sees the completion latch at entry and performs
; no door/input/world work at all.
case_completion_freezes_catchup:
    call reset_case
    ld a,W3D_LEVEL_COMPLETION_NORMAL
    ld (w3d_level_completion),a
    ld a,0a5h
    ld (w3d_controls),a
    call w3d_simulate_player_step
    ld a,(w3d_controls)
    ld b,0a5h
    ld c,13
    call assert_a
    ld a,(w3d_pickup_scan_needed)
    ld b,0
    ld c,14
    call assert_a
    jp finish_case

assert_a:
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

; Required by included modules but not reached in these directed cases.
w3d_mark_render_submitted: ret
w3d_death_fixed_step: or a
    ret
w3d_death_promote_lethal_latch: or a
    ret
w3d_audio_begin_quantum: ret
w3d_audio_request: xor a
    ret
w3d_audio_request_actor: xor a
    ret
w3d_audio_request_tile: xor a
    ret
w3d_elapsed_ticks: dl 0
w3d_exit_requested: db 0

test_delta_east: db 0,16,0, 0,0,0
result_filename: asciz "victory_result.bin"
output_handle: db 0
case_failed: db 0
assert_expected: db 0
assert_actual: db 0
result_data:
    db "W3V1"
result_records: db 0
result_errors: db 0
result_first_case: db 0ffh
result_first_reason: db 0
result_first_expected: db 0
result_first_actual: db 0
    ds 6
result_end:

test_tilemap: ds W3D_MAP_BYTES
test_paths: ds W3D_MAP_BYTES
test_areas: ds W3D_MAP_BYTES
test_static_bits: ds W3D_MAP_BYTES/8
