; Direct real-eZ80 regression for the production high-score ordering core.

    assume adl=1
    org 040000h
    jp start
    align 64
    db "MOS",0,1

mos_getkey:         equ 00h
mos_fopen:          equ 0ah
mos_fclose:         equ 0bh
mos_fread:          equ 1ah
mos_fwrite:         equ 1bh
fa_read:            equ 01h
fa_write:           equ 02h
fa_create_always:   equ 08h
sysvar_time:        equ 00h
W3D_SHELL_HIGH_SCORES_BASE_BUFFER: equ 04304h

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

    include "wolf3d_highscores.inc"

; Presentation and production-state seams are inert in this core regression.
w3d_vdu_present:
w3d_shell_clear:
w3d_shell_plot_full_screen:
printString:
w3d_shell_wait_any_press:
w3d_shell_wait_all_released:
    ret
w3d_shell_request_exit:
    ld a,1
    ld (test_exit_requested),a
    or a
    ret
w3d_shell_query_exit_request:
    ld a,(test_exit_requested)
    or a
    ret
w3d_shell_read_keyboard:
    ld a,(test_read_count)
    inc a
    ld (test_read_count),a
    ld a,(test_time_step)
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,(test_sysvars+sysvar_time)
    add hl,de
    ld (test_sysvars+sysvar_time),hl
    xor a
    ld hl,test_keymap
    ld (hl),a
    ld de,test_keymap+1
    ld bc,15
    ldir
    ld a,(test_key_kind)
    or a
    jr z,@done
    ld b,a
    ld a,(test_read_count)
    ld c,a
    ld a,(test_key_after)
    cp c
    jr nc,@not_yet
    jr @emit
@not_yet:
    jr nz,@done
@emit:
    ld a,b
    cp 2
    jr z,@escape
    ld a,1
    ld (test_keymap),a
    jr @done
@escape:
    ld a,1
    ld (test_keymap+14),a
@done:
    ld ix,test_keymap
    ret
w3d_sysvars_pointer:
    dl test_sysvars
test_sysvars:
    ds 4
test_keymap:
    ds 16
w3d_player_score:
    ds 4
w3d_level_requested_index:
    db 0

REASON_SLOT:       equ 1
REASON_NAME:       equ 2
REASON_SCORE:      equ 3
REASON_COMPLETED:  equ 4
REASON_EPISODE:    equ 5
REASON_SHIFT:      equ 6
REASON_TERMINATOR: equ 7
REASON_FILE_RESULT: equ 8
REASON_CURSOR:      equ 9
REASON_WAIT:        equ 10

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
    call test_defaults
    call test_equal_does_not_qualify
    call test_completed_tiebreak_and_shift
    call test_unsigned_u32_score
    call test_bottom_slot
    call test_name_copy
    call test_name_truncation
    call test_file_round_trip
    call test_file_checksum_recovery
    call test_file_structure_recovery
    call test_decimal_formatting
    call test_production_file_round_trip
    call test_name_editor
    call test_cursor_contract
    call test_timed_nonqualifying_wait
    call write_result
    ret

test_defaults:
    ld a,1
    ld (test_case),a
    call w3d_highscores_reset_defaults
    CHECK_MEM8 w3d_highscores+0,'i',REASON_NAME
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_RECORD_SIZE+0,'A',REASON_NAME
    CHECK_MEM8 w3d_highscores+396,'J',REASON_NAME
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_SCORE+0,10000&0ffh,REASON_SCORE
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_SCORE+1,10000>>8,REASON_SCORE
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_SCORE+2,0,REASON_SCORE
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_SCORE+3,0,REASON_SCORE
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_COMPLETED,1,REASON_COMPLETED
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_EPISODE,0,REASON_EPISODE
    ret

test_cursor_contract:
    ld a,14
    ld (test_case),a
    ld bc,0a509h
    ld a,4
    call w3d_highscores_set_cursor
    ld a,b
    ld (test_cursor_bc+0),a
    ld a,c
    ld (test_cursor_bc+1),a
    CHECK_MEM8 test_cursor_bc+0,0a5h,REASON_CURSOR
    CHECK_MEM8 test_cursor_bc+1,09h,REASON_CURSOR
    CHECK_MEM8 w3d_highscores_cursor_command+1,4,REASON_CURSOR
    CHECK_MEM8 w3d_highscores_cursor_command+2,9,REASON_CURSOR
    ret

test_timed_nonqualifying_wait:
    ld a,15
    ld (test_case),a
    call reset_wait_test
    ld a,100
    ld (test_time_step),a
    call w3d_highscores_wait_nonqualifying
    CHECK_MEM8 test_read_count,9,REASON_WAIT
    CHECK_MEM8 test_exit_requested,0,REASON_WAIT

    call reset_wait_test
    ld a,1
    ld (test_key_kind),a
    ld a,3
    ld (test_key_after),a
    call w3d_highscores_wait_nonqualifying
    CHECK_MEM8 test_read_count,3,REASON_WAIT
    CHECK_MEM8 test_exit_requested,0,REASON_WAIT

    call reset_wait_test
    ld a,2
    ld (test_key_kind),a
    ld a,1
    ld (test_key_after),a
    call w3d_highscores_wait_nonqualifying
    CHECK_MEM8 test_read_count,1,REASON_WAIT
    CHECK_MEM8 test_exit_requested,1,REASON_WAIT
    ret

reset_wait_test:
    xor a
    ld (test_read_count),a
    ld (test_time_step),a
    ld (test_key_kind),a
    ld (test_exit_requested),a
    ld hl,test_sysvars
    ld (hl),a
    ld de,test_sysvars+1
    ld bc,3
    ldir
    ret

test_equal_does_not_qualify:
    ld a,2
    ld (test_case),a
    call w3d_highscores_reset_defaults
    call candidate_default_score
    call w3d_highscores_consider
    CHECK_A W3D_HIGHSCORE_NO_SLOT,REASON_SLOT
    CHECK_MEM8 w3d_highscores+0,'i',REASON_NAME
    ret

test_completed_tiebreak_and_shift:
    ld a,3
    ld (test_case),a
    call w3d_highscores_reset_defaults
    call candidate_default_score
    ld a,2
    ld (w3d_highscores_candidate_completed),a
    call w3d_highscores_consider
    CHECK_A 0,REASON_SLOT
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_NAME,0,REASON_NAME
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_COMPLETED,2,REASON_COMPLETED
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_EPISODE,0,REASON_EPISODE
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_RECORD_SIZE+0,'i',REASON_SHIFT
    ret

test_unsigned_u32_score:
    ld a,4
    ld (test_case),a
    call w3d_highscores_reset_defaults
    call candidate_default_score
    xor a
    ld (w3d_highscores_candidate_score+0),a
    ld (w3d_highscores_candidate_score+1),a
    ld (w3d_highscores_candidate_score+2),a
    inc a
    ld (w3d_highscores_candidate_score+3),a
    call w3d_highscores_consider
    CHECK_A 0,REASON_SLOT
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_SCORE+3,1,REASON_SCORE
    ret

test_bottom_slot:
    ld a,5
    ld (test_case),a
    call w3d_highscores_reset_defaults
    ld ix,w3d_highscores
    ld b,6
@raise:
    ld (ix+W3D_HIGHSCORE_SCORE+0),10001&0ffh
    ld (ix+W3D_HIGHSCORE_SCORE+1),10001>>8
    lea ix,ix+W3D_HIGHSCORE_RECORD_SIZE
    djnz @raise
    call candidate_default_score
    ld a,2
    ld (w3d_highscores_candidate_completed),a
    call w3d_highscores_consider
    CHECK_A 6,REASON_SLOT
    CHECK_MEM8 w3d_highscores+458,2,REASON_COMPLETED
    ret

test_name_copy:
    ld a,6
    ld (test_case),a
    call w3d_highscores_reset_defaults
    call candidate_default_score
    ld a,2
    ld (w3d_highscores_candidate_completed),a
    call w3d_highscores_consider
    ld hl,test_short_name
    call w3d_highscores_set_inserted_name
    CHECK_MEM8 w3d_highscores+0,'B',REASON_NAME
    CHECK_MEM8 w3d_highscores+3,'.',REASON_NAME
    CHECK_MEM8 w3d_highscores+4,0,REASON_TERMINATOR
    ret

test_name_truncation:
    ld a,7
    ld (test_case),a
    call w3d_highscores_reset_defaults
    call candidate_default_score
    ld a,2
    ld (w3d_highscores_candidate_completed),a
    call w3d_highscores_consider
    ld hl,test_long_name
    call w3d_highscores_set_inserted_name
    CHECK_MEM8 w3d_highscores+56,'A',REASON_NAME
    CHECK_MEM8 w3d_highscores+57,0,REASON_TERMINATOR
    ret

test_file_round_trip:
    ld a,8
    ld (test_case),a
    call w3d_highscores_reset_defaults
    call candidate_default_score
    ld a,2
    ld (w3d_highscores_candidate_completed),a
    call w3d_highscores_consider
    ld hl,test_short_name
    call w3d_highscores_set_inserted_name
    call w3d_highscores_encode_file
    xor a
    ld hl,w3d_highscores
    ld (hl),a
    ld de,w3d_highscores+1
    ld bc,W3D_HIGHSCORE_FILE_PAYLOAD_SIZE-1
    ldir
    call w3d_highscores_decode_file
    CHECK_A 0,REASON_FILE_RESULT
    CHECK_MEM8 w3d_highscores+0,'B',REASON_NAME
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_COMPLETED,2,REASON_COMPLETED
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_RECORD_SIZE+0,'i',REASON_SHIFT
    ret

test_file_checksum_recovery:
    ld a,9
    ld (test_case),a
    call w3d_highscores_reset_defaults
    call w3d_highscores_encode_file
    ld hl,w3d_highscores_file_buffer+W3D_HIGHSCORE_FILE_HEADER_SIZE+7
    ld a,(hl)
    xor 055h
    ld (hl),a
    call w3d_highscores_decode_file
    CHECK_A 1,REASON_FILE_RESULT
    CHECK_MEM8 w3d_highscores+0,'i',REASON_NAME
    call w3d_highscores_encode_file
    ld hl,w3d_highscores_file_buffer+W3D_HIGHSCORE_FILE_HEADER_SIZE
    ld (hl),'A'
    push hl
    pop de
    inc de
    ld bc,W3D_HIGHSCORE_NAME_SIZE-1
    ldir
    ld hl,w3d_highscores_file_buffer+W3D_HIGHSCORE_FILE_HEADER_SIZE
    ld bc,W3D_HIGHSCORE_FILE_PAYLOAD_SIZE
    call w3d_highscores_fletcher16
    ld a,(w3d_highscores_checksum_1)
    ld (w3d_highscores_file_buffer+12),a
    ld a,(w3d_highscores_checksum_2)
    ld (w3d_highscores_file_buffer+13),a
    call w3d_highscores_decode_file
    CHECK_A 1,REASON_FILE_RESULT
    CHECK_MEM8 w3d_highscores+0,'i',REASON_NAME
    ret

test_file_structure_recovery:
    ld a,10
    ld (test_case),a
    call w3d_highscores_reset_defaults
    call w3d_highscores_encode_file
    xor a
    ld (w3d_highscores_file_buffer+W3D_HIGHSCORE_FILE_FOOTER+3),a
    call w3d_highscores_decode_file
    CHECK_A 1,REASON_FILE_RESULT
    CHECK_MEM8 w3d_highscores+0,'i',REASON_NAME
    call w3d_highscores_encode_file
    xor a
    ld (w3d_highscores_file_buffer),a
    call w3d_highscores_decode_file
    CHECK_A 1,REASON_FILE_RESULT
    CHECK_MEM8 w3d_highscores+0,'i',REASON_NAME
    ret

test_decimal_formatting:
    ld a,11
    ld (test_case),a
    ld hl,test_zero_u32
    call w3d_highscores_format_u32
    push hl
    pop ix
    ld a,(ix+0)
    CHECK_A '0',REASON_SCORE
    ld a,(ix+1)
    CHECK_A 0,REASON_TERMINATOR
    ld hl,test_max_u32
    call w3d_highscores_format_u32
    push hl
    pop ix
    ld a,(ix+0)
    CHECK_A '4',REASON_SCORE
    ld a,(ix+9)
    CHECK_A '5',REASON_SCORE
    ld a,(ix+10)
    CHECK_A 0,REASON_TERMINATOR
    ld hl,test_max_u16
    call w3d_highscores_format_u16
    push hl
    pop ix
    ld a,(ix+0)
    CHECK_A '6',REASON_COMPLETED
    ld a,(ix+4)
    CHECK_A '5',REASON_COMPLETED
    ld a,(ix+5)
    CHECK_A 0,REASON_TERMINATOR
    ret

test_production_file_round_trip:
    ld a,12
    ld (test_case),a
    call w3d_highscores_reset_defaults
    call candidate_default_score
    ld a,2
    ld (w3d_highscores_candidate_completed),a
    call w3d_highscores_consider
    ld hl,test_short_name
    call w3d_highscores_set_inserted_name
    call w3d_highscores_save
    ld a,0
    jr nc,@saved
    inc a
@saved:
    CHECK_A 0,REASON_FILE_RESULT
    call w3d_highscores_reset_defaults
    call w3d_highscores_initialize
    CHECK_MEM8 w3d_highscores+0,'B',REASON_NAME
    CHECK_MEM8 w3d_highscores+W3D_HIGHSCORE_COMPLETED,2,REASON_COMPLETED
    ret

test_name_editor:
    ld a,13
    ld (test_case),a
    call w3d_highscores_reset_defaults
    call candidate_default_score
    ld a,2
    ld (w3d_highscores_candidate_completed),a
    call w3d_highscores_consider
    ld hl,test_name_keys
    ld (test_name_key_pointer),hl
    ld hl,test_name_key_hook
    call w3d_highscores_set_key_hook
    call w3d_highscores_read_key
    CHECK_A 'B',REASON_NAME
    ld hl,test_name_keys
    ld (test_name_key_pointer),hl
    call w3d_highscores_edit_inserted_name
    call w3d_highscores_reset_key_hook
    CHECK_MEM8 w3d_highscores+0,'B',REASON_NAME
    CHECK_MEM8 w3d_highscores+1,'!',REASON_NAME
    CHECK_MEM8 w3d_highscores+2,0,REASON_TERMINATOR
    ret

test_name_key_hook:
    ld hl,(test_name_key_pointer)
    ld a,(hl)
    inc hl
    ld (test_name_key_pointer),hl
    ret

candidate_default_score:
    ld hl,10000
    ld (w3d_highscores_candidate_score),hl
    xor a
    ld (w3d_highscores_candidate_score+3),a
    inc a
    ld (w3d_highscores_candidate_completed),a
    xor a
    ld (w3d_highscores_candidate_completed+1),a
    ld (w3d_highscores_candidate_episode+0),a
    ld (w3d_highscores_candidate_episode+1),a
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

test_short_name: db "B.J.",0
test_long_name:
    db "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",0
test_zero_u32: db 0,0,0,0
test_max_u32: db 0ffh,0ffh,0ffh,0ffh
test_max_u16: dw 0ffffh
test_name_keys: db 'B','J',8,'!',13
test_name_key_pointer: dl test_name_keys
result_filename: db "highscores_result.bin",0
output_handle: db 0
test_case: db 0
test_cursor_bc: ds 2
test_read_count: db 0
test_time_step: db 0
test_key_kind: db 0
test_key_after: db 0
test_exit_requested: db 0

result_data:
    db "W3H1"
result_checks: db 0
result_errors: db 0
result_first_case: db 0ffh
result_first_reason: db 0
result_first_expected: db 0
result_first_actual: db 0
    db 0,0,0,0,0,0
result_end:
