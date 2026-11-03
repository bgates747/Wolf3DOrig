; Direct real-eZ80 regression for the production IMF-derived music sequencer.
    assume adl=1
    org 040000h
    jp start
    align 64
    db "MOS",0,1

mos_fopen:          equ 00ah
mos_fclose:         equ 00bh
mos_fwrite:         equ 01bh
sysvar_time:        equ 00h
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

w3d_sysvars_pointer: dl test_sysvars
w3d_level_requested_index: db 0
test_sysvars: ds 32

    include "wolf3d_math.inc"
    include "wolf3d_music_assets.inc"
    include "wolf3d_music.inc"

REASON_SCALAR:      equ 1
REASON_FREQUENCY:   equ 2
REASON_VOLUME:      equ 3
REASON_WAVEFORM:    equ 4
REASON_WIRE:        equ 5
REASON_SCHEDULER:   equ 6
REASON_LIFECYCLE:   equ 7

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
    call w3d_music_initialize

    ld a,1
    ld (result_stage),a
    call write_result
    call case_frequency_volume_wave
    ld a,2
    ld (result_stage),a
    call write_result
    call case_wire_start
    ld a,3
    ld (result_stage),a
    call write_result
    call case_scheduler_loop
    ld a,4
    ld (result_stage),a
    call write_result
    call case_canonical_lifecycle
    ld a,1
    ld (result_done),a
    call write_result
    ret

case_frequency_volume_wave:
    ld a,1
    ld (test_case),a
    xor a
    ld (w3d_music_voice),a
    ld a,044h
    ld (w3d_music_registers+0a0h),a
    ld a,032h
    ld (w3d_music_registers+0b0h),a
    call w3d_music_calculate_frequency
    push de
    ld a,e
    CHECK_A 0b7h,REASON_FREQUENCY
    pop de
    ld a,d
    CHECK_A 01h,REASON_FREQUENCY

    ld a,2
    ld (test_case),a
    xor a
    ld (w3d_music_registers+043h),a
    call w3d_music_calculate_volume
    CHECK_A 48,REASON_VOLUME
    ld a,63
    ld (w3d_music_registers+043h),a
    call w3d_music_calculate_volume
    CHECK_A 0,REASON_VOLUME

    ld a,3
    ld (test_case),a
    ld a,2
    ld (w3d_music_registers+0e3h),a
    call w3d_music_set_voice_waveform
    CHECK_MEM8 w3d_music_waveform_value,2,REASON_WAVEFORM
    ret

case_wire_start:
    ld a,4
    ld (test_case),a
    ld hl,test_capture
    ld de,64
    call w3d_music_capture_start
    xor a
    ld (w3d_music_voice),a
    ld a,044h
    ld (w3d_music_registers+0a0h),a
    ld a,032h
    ld (w3d_music_registers+0b0h),a
    xor a
    ld (w3d_music_registers+043h),a
    ld (w3d_music_registers+0e3h),a
    call w3d_music_start_voice
    call w3d_music_capture_stop
    CHECK_MEM8 w3d_music_capture_overflow,0,REASON_WIRE
    CHECK_MEM8 test_capture+0,23,REASON_WIRE
    CHECK_MEM8 test_capture+3,3,REASON_WIRE
    CHECK_MEM8 test_capture+4,10,REASON_WIRE
    CHECK_MEM8 test_capture+8,3,REASON_WIRE
    CHECK_MEM8 test_capture+9,4,REASON_WIRE
    CHECK_MEM8 test_capture+10,3,REASON_WAVEFORM
    CHECK_MEM8 test_capture+14,3,REASON_WIRE
    CHECK_MEM8 test_capture+15,0,REASON_WIRE
    CHECK_MEM8 test_capture+16,48,REASON_VOLUME
    CHECK_MEM8 test_capture+17,0b7h,REASON_FREQUENCY
    CHECK_MEM8 test_capture+18,01h,REASON_FREQUENCY
    CHECK_MEM8 test_capture+19,0ffh,REASON_WIRE
    CHECK_MEM8 test_capture+20,0ffh,REASON_WIRE
    CHECK_MEM8 w3d_music_capture_remaining+0,43,REASON_WIRE
    ret

case_scheduler_loop:
    ld a,5
    ld (test_case),a
    ld hl,test_track
    ld (w3d_music_track_start),hl
    xor a
    ld (test_sysvars+sysvar_time),a
    ld (test_sysvars+sysvar_time+1),a
    call w3d_music_restart_track
    ld a,1
    ld (w3d_music_active),a
    call w3d_music_service
    CHECK_MEM8 w3d_music_events_remaining+0,1,REASON_SCHEDULER
    CHECK_MEM8 w3d_music_next_due+0,1,REASON_SCHEDULER

    ld a,6
    ld (test_case),a
    ld a,1
    ld (test_sysvars+sysvar_time),a
    call w3d_music_service
    CHECK_MEM8 w3d_music_events_remaining+0,0,REASON_SCHEDULER
    CHECK_MEM8 w3d_music_next_due+0,2,REASON_SCHEDULER

    ld a,7
    ld (test_case),a
    ld a,2
    ld (test_sysvars+sysvar_time),a
    call w3d_music_service
    CHECK_MEM8 w3d_music_events_remaining+0,1,REASON_SCHEDULER
    CHECK_MEM8 w3d_music_started_at+0,2,REASON_SCHEDULER
    CHECK_MEM8 w3d_music_next_due+0,1,REASON_SCHEDULER
    ret

case_canonical_lifecycle:
    ld a,8
    ld (test_case),a
    call w3d_music_stop
    ld a,0ffh
    call w3d_music_start
    jr c,@invalid_ok
    xor a
    CHECK_A 1,REASON_LIFECYCLE
@invalid_ok:
    ld a,1
    CHECK_A 1,REASON_LIFECYCLE

    ld a,9
    ld (test_case),a
    xor a
    ld (test_sysvars+sysvar_time),a
    ld (test_sysvars+sysvar_time+1),a
    ld a,W3D_MUSIC_NAZI_NOR
    call w3d_music_start
    jr nc,@started
    xor a
    CHECK_A 1,REASON_LIFECYCLE
@started:
    CHECK_MEM8 w3d_music_active,1,REASON_LIFECYCLE
    CHECK_MEM8 w3d_music_current_id,W3D_MUSIC_NAZI_NOR,REASON_LIFECYCLE
    ld a,(w3d_music_events_remaining+0)
    ld b,a
    ld a,(w3d_music_events_remaining+1)
    or b
    jr nz,@remaining_ok
    xor a
    CHECK_A 1,REASON_LIFECYCLE
@remaining_ok:
    ld a,1
    CHECK_A 1,REASON_LIFECYCLE

    ld a,10
    ld (test_case),a
    call w3d_music_shutdown
    CHECK_MEM8 w3d_music_active,0,REASON_LIFECYCLE
    CHECK_MEM8 w3d_music_initialized,0,REASON_LIFECYCLE

    ld a,11
    ld (test_case),a
    call w3d_music_initialize
    xor a
    call w3d_music_set_enabled
    CHECK_MEM8 w3d_music_enabled,0,REASON_LIFECYCLE
    CHECK_MEM8 w3d_music_active,0,REASON_LIFECYCLE
    ld ix,test_floor_tracks
    xor a
@floor_loop:
    ld (w3d_level_requested_index),a
    push af
    call w3d_music_start_current_floor
    ld a,(w3d_music_current_id)
    ld b,(ix)
    ld c,REASON_LIFECYCLE
    call assert_a
    lea ix,ix+1
    pop af
    inc a
    cp 10
    jr c,@floor_loop
    CHECK_MEM8 w3d_music_active,0,REASON_LIFECYCLE
    ld a,1
    call w3d_music_set_enabled
    CHECK_MEM8 w3d_music_enabled,1,REASON_LIFECYCLE
    xor a
    ld (w3d_level_requested_index),a
    call w3d_music_start_current_floor
    CHECK_MEM8 w3d_music_active,1,REASON_LIFECYCLE
    call w3d_music_shutdown
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

test_track:
    dw 2,2
    db 0,0
    dw 1
    db 0,0
    dw 1
test_floor_tracks:
    db W3D_MUSIC_GETTHEM,W3D_MUSIC_SEARCHN,W3D_MUSIC_POW,W3D_MUSIC_SUSPENSE
    db W3D_MUSIC_GETTHEM,W3D_MUSIC_SEARCHN,W3D_MUSIC_POW,W3D_MUSIC_SUSPENSE
    db W3D_MUSIC_WARMARCH,W3D_MUSIC_CORNER
test_capture: ds 64

result_filename: db "music_result.bin",0
output_handle: db 0
test_case: db 0
result_data:
    db "W3MU"
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
