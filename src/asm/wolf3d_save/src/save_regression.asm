; Direct real-eZ80 regression for the transactional production save image.

    assume adl=1
    org 040000h
    jp start
    align 64
    db "MOS",0,1

mos_getkbmap:       equ 01eh
mos_fopen:          equ 00ah
mos_fclose:         equ 00bh
mos_fread:          equ 01ah
mos_fwrite:         equ 01bh
fa_read:            equ 01h
fa_write:           equ 02h
fa_create_always:   equ 08h
sysvar_time:         equ 00h

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    include "wolf3d_backend.inc"
    include "wolf3d_audio_assets.inc"
    include "wolf3d_sight.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_actors.inc"
    include "wolf3d_areas.inc"
    include "wolf3d_actor_sim.inc"
    include "wolf3d_victory.inc"
    include "wolf3d_motion.inc"
    include "wolf3d_player_combat.inc"

W3D_LEVEL_RATIO_SIZE:  equ 10
W3D_LEVEL_RATIO_COUNT: equ 8
    include "wolf3d_save.inc"
    include "wolf3d_save_slots.inc"

SAVE_CASE_COUNT: equ 10

REASON_RESULT:      equ 1
REASON_HEALTH:      equ 2
REASON_SCORE:       equ 3
REASON_TILEMAP:     equ 4
REASON_AREA:        equ 5
REASON_POINTER:     equ 6
REASON_ACTORAT:     equ 7
REASON_TRANSACTION: equ 8
REASON_SLOT_IO:     equ 9
REASON_SLOT_META:   equ 10
REASON_OLD_SCORE:   equ 11
REASON_FACE:        equ 12

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
    ld hl,result_cases
    ld (hl),a
    ld de,result_cases+1
    ld bc,result_end-result_cases-1
    ldir
    dec a
    ld (result_first_case),a
    call initialize_world
    call case_round_trip
    call case_header_rejected
    call case_checksum_rejected
    call case_scalar_rejected
    call case_tilemap_rejected
    call case_area_rejected
    call case_actor_rejected
    call case_door_rejected
    call case_static_and_pushwall_rejected
    call case_ten_slot_round_trip
    ld a,1
    ld (result_done),a
    call write_result
    ret

initialize_world:
    xor a
    ld (test_sysvars+sysvar_time),a
    ld a,2
    ld (w3d_requested_difficulty),a
    xor a
    ld (w3d_level_requested_index),a
    call w3d_initialize_motion_state
    xor a
    ld hl,w3d_level_ratios
    ld (hl),a
    ld de,w3d_level_ratios+1
    ld bc,W3D_LEVEL_RATIO_SIZE*W3D_LEVEL_RATIO_COUNT-1
    ldir
    ret

prepare_image:
    call prepare_state
    jp w3d_save_encode

prepare_state:
    ld a,73
    ld (w3d_player_health),a
    ld a,2
    ld (w3d_player_face_frame),a
    ld a,078h
    ld (w3d_player_score+0),a
    ld a,056h
    ld (w3d_player_score+1),a
    ld a,034h
    ld (w3d_player_score+2),a
    ld a,012h
    ld (w3d_player_score+3),a
    ld a,011h
    ld (w3d_death_oldscore+0),a
    ld a,022h
    ld (w3d_death_oldscore+1),a
    ld a,033h
    ld (w3d_death_oldscore+2),a
    ld a,044h
    ld (w3d_death_oldscore+3),a
    ld a,02ah
    ld (w3d_runtime_tilemap+97),a
    ld a,3
    ld (w3d_runtime_area_map+97),a
    ret

clear_round_trip_state:
    ld a,1
    ld (w3d_player_health),a
    xor a
    ld (w3d_player_face_frame),a
    ld (w3d_player_score+0),a
    ld (w3d_player_score+1),a
    ld (w3d_player_score+2),a
    ld (w3d_player_score+3),a
    ld (w3d_death_oldscore+0),a
    ld (w3d_death_oldscore+1),a
    ld (w3d_death_oldscore+2),a
    ld (w3d_death_oldscore+3),a
    ld (w3d_runtime_tilemap+97),a
    ld (w3d_runtime_area_map+97),a
    ret

refresh_checksum:
    ld hl,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE
    ld bc,W3D_SAVE_PAYLOAD_SIZE
    call w3d_save_fletcher16
    ld a,(w3d_save_checksum_1)
    ld (w3d_save_file_buffer+W3D_SAVE_H_CHECKSUM_1),a
    ld a,(w3d_save_checksum_2)
    ld (w3d_save_file_buffer+W3D_SAVE_H_CHECKSUM_2),a
    ret

set_transaction_sentinel:
    ld a,055h
    ld (w3d_player_health),a
    ret

assert_rejected_transactionally:
    ld (expected_result),a
    call w3d_save_decode
    push af
    ld a,(expected_result)
    ld b,a
    pop af
    ld c,REASON_RESULT
    call assert_a
    ld a,(w3d_player_health)
    ld b,055h
    ld c,REASON_TRANSACTION
    jp assert_a

finish_case:
    ld a,(result_cases)
    inc a
    ld (result_cases),a
    ret

case_round_trip:
    ld a,1
    ld (test_case),a
    call prepare_image
    call clear_round_trip_state
    call w3d_save_decode
    ld b,0
    ld c,REASON_RESULT
    call assert_a
    ld a,(w3d_player_health)
    ld b,73
    ld c,REASON_HEALTH
    call assert_a
    ld a,(w3d_player_score+3)
    ld b,012h
    ld c,REASON_SCORE
    call assert_a
    ld a,(w3d_death_oldscore+3)
    ld b,044h
    ld c,REASON_OLD_SCORE
    call assert_a
    ld a,(w3d_player_face_frame)
    ld b,2
    ld c,REASON_FACE
    call assert_a
    ld a,(w3d_runtime_tilemap+97)
    ld b,02ah
    ld c,REASON_TILEMAP
    call assert_a
    ld a,(w3d_runtime_area_map+97)
    ld b,3
    ld c,REASON_AREA
    call assert_a
    ld hl,(w3d_map_ptr)
    ld de,w3d_runtime_tilemap
    or a
    sbc hl,de
    ld a,l
    or h
    ld b,0
    ld c,REASON_POINTER
    call assert_a
    ld a,(w3d_actor_live_head)
    call w3d_actor_pointer_from_id
    push af
    call w3d_actorat_address_from_ix
    pop af
    cp (hl)
    jr z,@actorat_ok
    ld b,a
    ld a,(hl)
    ld c,REASON_ACTORAT
    call assert_a
@actorat_ok:
    jp finish_case

case_header_rejected:
    ld a,2
    ld (test_case),a
    call prepare_image
    ld a,'X'
    ld (w3d_save_file_buffer),a
    call set_transaction_sentinel
    ld a,1
    call assert_rejected_transactionally
    jp finish_case

case_checksum_rejected:
    ld a,3
    ld (test_case),a
    call prepare_image
    ld hl,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_SCORE
    inc (hl)
    call set_transaction_sentinel
    ld a,2
    call assert_rejected_transactionally
    jp finish_case

case_scalar_rejected:
    ld a,4
    ld (test_case),a
    call prepare_image
    ld a,101
    ld (w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_HEALTH),a
    call refresh_checksum
    call set_transaction_sentinel
    ld a,3
    call assert_rejected_transactionally
    jp finish_case

case_tilemap_rejected:
    ld a,5
    ld (test_case),a
    call prepare_image
    ld a,W3D_TILE_DOOR_MIN+W3D_MAX_DOORS-1
    ld (w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_TILEMAP),a
    call refresh_checksum
    call set_transaction_sentinel
    ld a,9
    call assert_rejected_transactionally
    jp finish_case

case_area_rejected:
    ld a,6
    ld (test_case),a
    call prepare_image
    ld a,W3D_NUM_AREAS
    ld (w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_AREA),a
    call refresh_checksum
    call set_transaction_sentinel
    ld a,4
    call assert_rejected_transactionally
    jp finish_case

case_actor_rejected:
    ld a,7
    ld (test_case),a
    call prepare_image
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_LIVE_HEAD)
    ld d,a
    ld e,W3D_ACTOR_SIZE
    mlt de
    inc de
    dec.s de
    ld hl,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_ACTORS+W3D_ACTOR_DIR
    add hl,de
    ld (hl),W3D_DIR_NODIR+1
    call refresh_checksum
    call set_transaction_sentinel
    ld a,5
    call assert_rejected_transactionally
    jp finish_case

case_door_rejected:
    ld a,8
    ld (test_case),a
    call prepare_image
    ld a,W3D_DOOR_ACTION_CLOSING+1
    ld (w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_DOORS+W3D_DOOR_ACTION),a
    call refresh_checksum
    call set_transaction_sentinel
    ld a,6
    call assert_rejected_transactionally
    jp finish_case

case_static_and_pushwall_rejected:
    ld a,9
    ld (test_case),a
    call prepare_image
    ld a,W3D_MAP_SIZE
    ld (w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_STATICS+W3D_STATIC_TILEX),a
    call refresh_checksum
    call set_transaction_sentinel
    ld a,7
    call assert_rejected_transactionally

    call prepare_image
    ld a,W3D_PUSHWALL_STATUS_COMPLETE+1
    ld (w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_PUSHWALL+W3D_PUSHWALL_RENDER_STATUS),a
    call refresh_checksum
    call set_transaction_sentinel
    ld a,8
    call assert_rejected_transactionally
    jp finish_case

case_ten_slot_round_trip:
    ld a,10
    ld (test_case),a
    xor a
    ld (test_slot),a
@save:
    ld a,(test_slot)
    add a,10
    ld (w3d_player_health),a
    ld a,(test_slot)
    add a,'0'
    ld (test_slot_name+5),a
    ld a,(test_slot)
    ld hl,test_slot_name
    call w3d_save_slot_store
    jr nc,@saved
    ld a,1
    ld b,0
    ld c,REASON_SLOT_IO
    call assert_a
@saved:
    ld a,(test_slot)
    inc a
    ld (test_slot),a
    cp W3D_SAVE_SLOT_COUNT
    jr c,@save

    call w3d_save_slots_initialize
    xor a
    ld (test_slot),a
@load:
    ld a,(test_slot)
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_save_slot_available
    add hl,de
    ld a,(hl)
    ld b,1
    ld c,REASON_SLOT_META
    call assert_a
    ld a,(test_slot)
    call w3d_save_slot_load
    jr nc,@loaded
    ld a,1
    ld b,0
    ld c,REASON_SLOT_IO
    call assert_a
    jr @next
@loaded:
    call w3d_save_slot_publish_pending
    jr nc,@published
    ld a,1
    ld b,0
    ld c,REASON_SLOT_IO
    call assert_a
    jr @next
@published:
    ld a,(test_slot)
    add a,10
    ld b,a
    ld a,(w3d_player_health)
    ld c,REASON_HEALTH
    call assert_a
@next:
    ld a,(test_slot)
    inc a
    ld (test_slot),a
    cp W3D_SAVE_SLOT_COUNT
    jr c,@load
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
    ld a,(test_case)
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

; Required by included modules but unreachable in this directed regression.
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
w3d_gameplay_panel_request: db 0
w3d_sysvars_pointer: dl test_sysvars
test_sysvars: ds 4
w3d_level_requested_index: db 0
w3d_death_oldscore: ds 4

result_filename: asciz "save_result.bin"
output_handle: db 0
test_case: db 0
case_failed: db 0
assert_expected: db 0
assert_actual: db 0
expected_result: db 0
test_slot: db 0
test_slot_name: db "slot 0",0
result_data:
    db "W3S1"
result_cases: db 0
result_errors: db 0
result_first_case: db 0ffh
result_first_reason: db 0
result_first_expected: db 0
result_first_actual: db 0
result_done: db 0
result_progress: db 0
    ds 4
result_end:

w3d_level_ratios:
    ds W3D_LEVEL_RATIO_SIZE*W3D_LEVEL_RATIO_COUNT
