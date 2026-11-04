; Direct real-eZ80 semantic regression for production recorded-demo playback.
    assume adl=1
    org 040000h
    jp start
    align 64
    db "MOS",0,1

mos_fopen:          equ 00ah
mos_fclose:         equ 00bh
mos_fwrite:         equ 01bh
fa_write:           equ 02h
fa_create_always:   equ 08h

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    macro CHECK_A expected,reason
        ld b,expected
        ld c,reason
        call assert_a
    endmacro

    macro CHECK_MEM8 address,expected,reason
        ld a,(address)
        CHECK_A expected,reason
    endmacro

W3D_CONTROL_W:      equ 00000001b
W3D_CONTROL_S:      equ 00000010b
W3D_CONTROL_A:      equ 00000100b
W3D_CONTROL_D:      equ 00001000b
W3D_CONTROL_LEFT:   equ 00010000b
W3D_CONTROL_RIGHT:  equ 00100000b
W3D_CONTROL_USE:    equ 01000000b
W3D_CONTROL_ATTACK: equ 10000000b

w3d_requested_difficulty: db 0
w3d_controls: db 0
w3d_keyboard_masks: ds 16
w3d_exit_requested: db 0
w3d_player_thrustspeed: dw 0

; Analog integration is checked independently of collision/table scaling.
; These seams record the exact signed turn and unsigned-distance requests
; published by the production demo state machine.
w3d_rotate_player:
    ld a,e
    ld (test_turn_delta+0),a
    ld a,d
    ld (test_turn_delta+1),a
    ret

w3d_move_at_heading_offset_scaled:
    ld a,e
    ld (test_move_offset+0),a
    ld a,d
    ld (test_move_offset+1),a
    ld a,c
    ld (test_move_distance+0),a
    ld a,b
    ld (test_move_distance+1),a
    ld hl,test_move_count
    inc (hl)
    ret

    include "wolf3d_demo_assets.inc"
    include "wolf3d_demo.inc"

REASON_SELECTION:  equ 1
REASON_LEVEL:      equ 2
REASON_DIFFICULTY: equ 3
REASON_ACTIVE:     equ 4
REASON_CONTROLS:   equ 5
REASON_CADENCE:    equ 6
REASON_CURSOR:     equ 7
REASON_FINISHED:   equ 8
REASON_EXIT_LATCH: equ 9
REASON_ABORTED:    equ 10

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
    dec a
    ld (result_first_case),a
    ld a,1
    ld (result_stage),a
    call write_result
    call case_stream_selection
    ld a,2
    ld (result_stage),a
    call write_result
    call case_control_decode
    ld a,3
    ld (result_stage),a
    call write_result
    call case_analog_motion
    ld a,4
    ld (result_stage),a
    call write_result
    call case_cadence
    ld a,5
    ld (result_stage),a
    call write_result
    call case_terminal_and_abort
    ld a,1
    ld (result_done),a
    call write_result
    ret

case_stream_selection:
    ld a,1
    ld (test_case),a
    xor a
    ld (w3d_demo_next_index),a
    call w3d_demo_prepare_next
    CHECK_MEM8 w3d_demo_selected_index,0,REASON_SELECTION
    CHECK_MEM8 w3d_demo_level,0,REASON_LEVEL
    CHECK_MEM8 w3d_requested_difficulty,3,REASON_DIFFICULTY
    CHECK_MEM8 w3d_demo_active,1,REASON_ACTIVE

    ld a,2
    ld (test_case),a
    call w3d_demo_prepare_next
    CHECK_MEM8 w3d_demo_selected_index,1,REASON_SELECTION
    CHECK_MEM8 w3d_demo_level,2,REASON_LEVEL

    ld a,3
    ld (test_case),a
    ld a,W3D_DEMO_COUNT
    ld (w3d_demo_next_index),a
    call w3d_demo_prepare_next
    CHECK_MEM8 w3d_demo_selected_index,0,REASON_SELECTION
    CHECK_MEM8 w3d_demo_level,0,REASON_LEVEL
    ret

case_control_decode:
    ld a,4
    ld (test_case),a
    ld hl,test_record_attack_forward_left
    ld (w3d_demo_cursor),hl
    xor a
    ld (w3d_demo_finished),a
    ld (w3d_demo_aborted),a
    call w3d_demo_sample_controls
    CHECK_MEM8 w3d_controls,0d1h,REASON_CONTROLS

    ld a,5
    ld (test_case),a
    ld hl,test_record_strafe_left_back
    ld (w3d_demo_cursor),hl
    call w3d_demo_sample_controls
    CHECK_MEM8 w3d_controls,006h,REASON_CONTROLS

    ld a,6
    ld (test_case),a
    ld hl,test_record_strafe_right
    ld (w3d_demo_cursor),hl
    call w3d_demo_sample_controls
    CHECK_MEM8 w3d_controls,008h,REASON_CONTROLS
    ret

case_analog_motion:
    ld a,12
    ld (test_case),a
    ld a,002h                    ; bt_strafe
    ld (w3d_demo_buttons),a
    ld a,20
    ld (w3d_demo_control_x),a
    ld a,-35
    ld (w3d_demo_control_y),a
    call w3d_demo_prepare_motion_step
    CHECK_MEM8 w3d_demo_forward_distance+0,0dah,REASON_CONTROLS
    CHECK_MEM8 w3d_demo_forward_distance+1,02fh,REASON_CONTROLS
    CHECK_MEM8 w3d_demo_strafe_distance+0,058h,REASON_CONTROLS
    CHECK_MEM8 w3d_demo_strafe_distance+1,01bh,REASON_CONTROLS
    CHECK_MEM8 w3d_player_thrustspeed+0,032h,REASON_CONTROLS
    CHECK_MEM8 w3d_player_thrustspeed+1,04bh,REASON_CONTROLS
    xor a
    ld (test_move_count),a
    call w3d_demo_apply_forward_step
    CHECK_MEM8 test_move_offset+0,0,REASON_CONTROLS
    CHECK_MEM8 test_move_distance+0,0dah,REASON_CONTROLS
    CHECK_MEM8 test_move_distance+1,02fh,REASON_CONTROLS
    call w3d_demo_apply_strafe_step
    CHECK_MEM8 test_move_offset+0,90,REASON_CONTROLS
    CHECK_MEM8 test_move_distance+0,058h,REASON_CONTROLS
    CHECK_MEM8 test_move_distance+1,01bh,REASON_CONTROLS
    CHECK_MEM8 test_move_count,2,REASON_CONTROLS

    ld a,13
    ld (test_case),a
    xor a
    ld (w3d_demo_buttons),a
    ld (w3d_demo_turn_fraction+0),a
    ld (w3d_demo_turn_fraction+1),a
    ld a,-100
    ld (w3d_demo_control_x),a
    call w3d_demo_apply_turn_step
    CHECK_MEM8 test_turn_delta+0,11,REASON_CONTROLS
    CHECK_MEM8 test_turn_delta+1,0,REASON_CONTROLS
    CHECK_MEM8 w3d_demo_turn_fraction+0,0d8h,REASON_CONTROLS
    CHECK_MEM8 w3d_demo_turn_fraction+1,0ffh,REASON_CONTROLS

    ld a,14
    ld (test_case),a
    xor a
    ld (w3d_demo_turn_fraction+0),a
    ld (w3d_demo_turn_fraction+1),a
    ld a,100
    ld (w3d_demo_control_x),a
    call w3d_demo_apply_turn_step
    CHECK_MEM8 test_turn_delta+0,0f5h,REASON_CONTROLS
    CHECK_MEM8 test_turn_delta+1,0ffh,REASON_CONTROLS
    CHECK_MEM8 w3d_demo_turn_fraction+0,40,REASON_CONTROLS
    CHECK_MEM8 w3d_demo_turn_fraction+1,0,REASON_CONTROLS

    ld a,15
    ld (test_case),a
    xor a
    ld (w3d_demo_control_x),a
    ld (w3d_demo_back_fraction),a
    ld a,35
    ld (w3d_demo_control_y),a
    call w3d_demo_prepare_motion_step
    CHECK_MEM8 w3d_demo_forward_distance+0,0e6h,REASON_CONTROLS
    CHECK_MEM8 w3d_demo_forward_distance+1,01fh,REASON_CONTROLS
    CHECK_MEM8 w3d_demo_back_fraction,2,REASON_CONTROLS
    call w3d_demo_prepare_motion_step
    CHECK_MEM8 w3d_demo_forward_distance+0,0e7h,REASON_CONTROLS
    CHECK_MEM8 w3d_demo_forward_distance+1,01fh,REASON_CONTROLS
    CHECK_MEM8 w3d_demo_back_fraction,1,REASON_CONTROLS
    ret

case_cadence:
    ld a,7
    ld (test_case),a
    ld a,1
    ld (w3d_demo_active),a
    xor a
    ld (w3d_demo_finished),a
    ld (w3d_demo_cadence),a
    ld hl,test_cadence_records
    ld (w3d_demo_cursor),hl
    ld hl,test_cadence_records_end
    ld (w3d_demo_stream_end),hl
    call w3d_demo_advance_step
    CHECK_MEM8 w3d_demo_cadence,70,REASON_CADENCE
    ld hl,(w3d_demo_cursor)
    ld a,l
    CHECK_A test_cadence_records&0ffh,REASON_CURSOR

    ld a,8
    ld (test_case),a
    call w3d_demo_advance_step
    CHECK_MEM8 w3d_demo_cadence,20,REASON_CADENCE
    ld hl,(w3d_demo_cursor)
    ld a,l
    CHECK_A test_cadence_records+3&0ffh,REASON_CURSOR

    ld a,9
    ld (test_case),a
    call w3d_demo_advance_step
    CHECK_MEM8 w3d_demo_cadence,90,REASON_CADENCE
    ld hl,(w3d_demo_cursor)
    ld a,l
    CHECK_A test_cadence_records+3&0ffh,REASON_CURSOR
    ret

case_terminal_and_abort:
    ld a,10
    ld (test_case),a
    ld a,1
    ld (w3d_demo_active),a
    xor a
    ld (w3d_demo_finished),a
    ld (w3d_demo_aborted),a
    ld a,70
    ld (w3d_demo_cadence),a
    ld hl,test_terminal_record
    ld (w3d_demo_cursor),hl
    ld hl,test_terminal_record_end
    ld (w3d_demo_stream_end),hl
    call w3d_demo_advance_step
    CHECK_MEM8 w3d_demo_finished,1,REASON_FINISHED
    CHECK_MEM8 w3d_demo_aborted,0,REASON_ABORTED
    ld a,0ffh
    ld (w3d_controls),a
    call w3d_demo_sample_controls
    CHECK_MEM8 w3d_controls,0,REASON_CONTROLS

    ld a,11
    ld (test_case),a
    xor a
    ld hl,w3d_keyboard_masks
    ld (hl),a
    ld de,w3d_keyboard_masks+1
    ld bc,15
    ldir
    ld a,1
    ld (w3d_keyboard_masks+5),a
    ld (w3d_exit_requested),a
    xor a
    ld (w3d_demo_finished),a
    ld (w3d_demo_aborted),a
    call w3d_demo_latch_input_abort
    CHECK_MEM8 w3d_demo_finished,1,REASON_FINISHED
    CHECK_MEM8 w3d_demo_aborted,1,REASON_ABORTED
    CHECK_MEM8 w3d_exit_requested,0,REASON_EXIT_LATCH
    call w3d_demo_cancel
    CHECK_MEM8 w3d_demo_aborted,0,REASON_ABORTED
    ret

assert_a:
    ld d,a
    ld hl,result_checks
    inc (hl)
    cp b
    ret z
    ld hl,result_errors
    ld a,(hl)
    inc (hl)
    or a
    ret nz
    ld a,(test_case)
    ld (result_first_case),a
    ld a,c
    ld (result_first_reason),a
    ld a,b
    ld (result_first_expected),a
    ld a,d
    ld (result_first_actual),a
    ret

write_result:
    ld hl,result_filename
    ld c,fa_write|fa_create_always
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

test_record_attack_forward_left: db 009h,0fbh,0f7h
test_record_strafe_left_back:    db 002h,004h,006h
test_record_strafe_right:        db 002h,0fch,000h
test_cadence_records:            db 0,0,0,0,0,0
test_cadence_records_end:
test_terminal_record:            db 0,0,0
test_terminal_record_end:
test_turn_delta: dw 0
test_move_offset: dw 0
test_move_distance: dw 0
test_move_count: db 0

result_filename: db "demo_result.bin",0
output_handle: db 0
test_case: db 0
result_data:
    db "W3D2"
result_checks: db 0
result_errors: db 0
result_first_case: db 0ffh
result_first_reason: db 0
result_first_expected: db 0
result_first_actual: db 0
result_stage: db 0
result_done: db 0
    db 0,0,0,0
result_end:
