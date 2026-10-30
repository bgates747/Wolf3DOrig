; Direct real-eZ80 regression for abortable callbacks in production
; wolf3d/src/agnb_api.inc. Tiny three-record image and audio containers are
; supplied by the host runner. FatFS is real; only VDP calls are counters.

    assume adl=1
    org 040000h
    jp start
    align 64
    db "MOS",0,1

mos_fopen:          equ 00ah
mos_fclose:         equ 00bh
mos_fwrite:         equ 01bh
fa_write:           equ 002h
fa_create_always:   equ 008h

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    macro FFSCALL function
        push iy
        ld a,function
        rst.lil 08h
        pop iy
    endmacro

ffs_fopen:             equ 080h
ffs_fclose:            equ 081h
ffs_fread:             equ 082h
fa_read:               equ 001h
ffobjid_objsize:       equ 11
fil_obj:               equ 0
fil_dir_ptr:           equ 33

    macro CHECK_A expected,reason
        ld b,expected
        ld c,reason
        call assert_a
    endmacro

    macro CHECK_MEM8 address,expected,reason
        ld a,(address)
        CHECK_A expected,reason
    endmacro

; Exact production dependency for image-size validation.
umul24:
    push de
    push bc
    push af
    push hl
    pop bc
    ld a,24
    ld hl,0
@loop:
    add hl,hl
    ex de,hl
    add hl,hl
    ex de,hl
    jr nc,@no_add
    add hl,bc
@no_add:
    dec a
    jr nz,@loop
    pop af
    pop bc
    pop de
    ret

vdu_clear_buffer:
vdu_load_buffer:
vdu_consolidate_buffer:
vdu_buff_select:
    ret

vdu_bmp_create:
    ld hl,test_image_finalize_count
    inc (hl)
    ret

vdu_buffer_to_sound:
    ld hl,test_audio_finalize_count
    inc (hl)
    ret

    include "agnb_api.inc"

REASON_RESULT:       equ 1
REASON_CALLBACKS:    equ 2
REASON_FINALIZED:    equ 3
REASON_FILE_OPEN:    equ 4
REASON_LAST_ERROR:   equ 5
REASON_EARLY_OFFSET: equ 6

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
    call test_image_legacy_ignores_result
    call test_image_abortable_continues
    call test_image_abortable_stops_at_two
    call test_audio_legacy_ignores_result
    call test_audio_abortable_continues
    call test_audio_abortable_stops_at_two
    call write_result
    ret

test_image_legacy_ignores_result:
    ld a,1
    ld (test_case),a
    call reset_counts
    ld a,1
    ld (test_abort_at),a
    ld de,image_filename
    ld hl,test_record_callback
    call agnb_load_images_with_callback
    CHECK_A agnb_error_ok,REASON_RESULT
    CHECK_MEM8 test_callback_count,3,REASON_CALLBACKS
    CHECK_MEM8 test_image_finalize_count,3,REASON_FINALIZED
    CHECK_MEM8 agnb_file_is_open,0,REASON_FILE_OPEN
    CHECK_MEM8 agnb_last_error,agnb_error_ok,REASON_LAST_ERROR
    ret

test_image_abortable_continues:
    ld a,2
    ld (test_case),a
    call reset_counts
    xor a
    ld (test_abort_at),a
    ld de,image_filename
    ld hl,test_record_callback
    call agnb_load_images_with_abortable_callback
    CHECK_A agnb_error_ok,REASON_RESULT
    CHECK_MEM8 test_callback_count,3,REASON_CALLBACKS
    CHECK_MEM8 test_image_finalize_count,3,REASON_FINALIZED
    CHECK_MEM8 agnb_file_is_open,0,REASON_FILE_OPEN
    CHECK_MEM8 agnb_last_error,agnb_error_ok,REASON_LAST_ERROR
    ret

test_image_abortable_stops_at_two:
    ld a,3
    ld (test_case),a
    call reset_counts
    ld a,2
    ld (test_abort_at),a
    ld de,image_filename
    ld hl,test_record_callback
    call agnb_load_images_with_abortable_callback
    CHECK_A agnb_error_callback_abort,REASON_RESULT
    CHECK_MEM8 test_callback_count,2,REASON_CALLBACKS
    CHECK_MEM8 test_image_finalize_count,2,REASON_FINALIZED
    CHECK_MEM8 agnb_file_is_open,0,REASON_FILE_OPEN
    CHECK_MEM8 agnb_last_error,agnb_error_callback_abort,REASON_LAST_ERROR
    call check_reader_stopped_before_riff_end
    ret

test_audio_legacy_ignores_result:
    ld a,4
    ld (test_case),a
    call reset_counts
    ld a,1
    ld (test_abort_at),a
    ld de,audio_filename
    ld hl,test_record_callback
    call agnb_load_audio_with_callback
    CHECK_A agnb_error_ok,REASON_RESULT
    CHECK_MEM8 test_callback_count,3,REASON_CALLBACKS
    CHECK_MEM8 test_audio_finalize_count,3,REASON_FINALIZED
    CHECK_MEM8 agnb_file_is_open,0,REASON_FILE_OPEN
    CHECK_MEM8 agnb_last_error,agnb_error_ok,REASON_LAST_ERROR
    ret

test_audio_abortable_continues:
    ld a,5
    ld (test_case),a
    call reset_counts
    xor a
    ld (test_abort_at),a
    ld de,audio_filename
    ld hl,test_record_callback
    call agnb_load_audio_with_abortable_callback
    CHECK_A agnb_error_ok,REASON_RESULT
    CHECK_MEM8 test_callback_count,3,REASON_CALLBACKS
    CHECK_MEM8 test_audio_finalize_count,3,REASON_FINALIZED
    CHECK_MEM8 agnb_file_is_open,0,REASON_FILE_OPEN
    CHECK_MEM8 agnb_last_error,agnb_error_ok,REASON_LAST_ERROR
    ret

test_audio_abortable_stops_at_two:
    ld a,6
    ld (test_case),a
    call reset_counts
    ld a,2
    ld (test_abort_at),a
    ld de,audio_filename
    ld hl,test_record_callback
    call agnb_load_audio_with_abortable_callback
    CHECK_A agnb_error_callback_abort,REASON_RESULT
    CHECK_MEM8 test_callback_count,2,REASON_CALLBACKS
    CHECK_MEM8 test_audio_finalize_count,2,REASON_FINALIZED
    CHECK_MEM8 agnb_file_is_open,0,REASON_FILE_OPEN
    CHECK_MEM8 agnb_last_error,agnb_error_callback_abort,REASON_LAST_ERROR
    call check_reader_stopped_before_riff_end
    ret

; Return A=0 until the selected finalized-record boundary, then arbitrary NZ.
test_record_callback:
    ld hl,test_callback_count
    inc (hl)
    ld a,(test_abort_at)
    or a
    ret z
    ld b,a
    ld a,(test_callback_count)
    cp b
    jr c,@continue
    ld a,07fh
    ret
@continue:
    xor a
    ret

reset_counts:
    xor a
    ld (test_callback_count),a
    ld (test_image_finalize_count),a
    ld (test_audio_finalize_count),a
    ret

check_reader_stopped_before_riff_end:
    ld hl,(agnb_state+agnb_state_file_offset)
    ld de,(agnb_state+agnb_state_riff_end)
    or a
    sbc hl,de
    ld a,1
    jr c,@checked
    xor a
@checked:
    CHECK_A 1,REASON_EARLY_OFFSET
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

image_filename: db "image.agnb",0
audio_filename: db "audio.agnb",0
result_filename: db "agnb_abort_result.bin",0
output_handle: db 0
test_case: db 0
test_abort_at: db 0
test_callback_count: db 0
test_image_finalize_count: db 0
test_audio_finalize_count: db 0

result_data:
    db "AGA1"
result_checks: db 0
result_errors: db 0
result_first_case: db 0ffh
result_first_reason: db 0
result_first_expected: db 0
result_first_actual: db 0
    db 0,0,0,0,0,0
result_end:
