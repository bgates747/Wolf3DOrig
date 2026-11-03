; Direct real-eZ80 regression for durable production preferences.

    assume adl=1
    org 040000h
    jp start
    align 64
    db "MOS",0,1

mos_fopen:        equ 0ah
mos_fclose:       equ 0bh
mos_fread:        equ 1ah
mos_fwrite:       equ 1bh
fa_read:          equ 01h
fa_write:         equ 02h
fa_create_always: equ 08h

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

w3d_audio_sfx_enabled: db 1
w3d_music_enabled: db 1

    include "wolf3d_config.inc"

REASON_RESULT:    equ 1
REASON_SFX:       equ 2
REASON_MUSIC:     equ 3
REASON_FLAGS:     equ 4
REASON_FILE_IO:   equ 5

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
    call test_missing_defaults
    call test_all_flag_combinations
    call test_corrupt_images
    call test_production_round_trip
    call test_exact_length
    call write_result
    ret

test_missing_defaults:
    ld a,1
    ld (test_case),a
    xor a
    ld (w3d_audio_sfx_enabled),a
    ld (w3d_music_enabled),a
    call w3d_config_initialize
    CHECK_MEM8 w3d_audio_sfx_enabled,1,REASON_SFX
    CHECK_MEM8 w3d_music_enabled,1,REASON_MUSIC
    ret

test_all_flag_combinations:
    ld a,2
    ld (test_case),a
    xor a
    ld (test_combo),a
@combo:
    ld a,(test_combo)
    and 1
    ld (w3d_audio_sfx_enabled),a
    ld a,(test_combo)
    and 2
    jr z,@music_set
    ld a,1
@music_set:
    ld (w3d_music_enabled),a
    call w3d_config_encode_file
    ld a,(test_combo)
    ld b,a
    ld c,REASON_FLAGS
    ld a,(w3d_config_file_buffer+W3D_CONFIG_FLAGS_OFFSET)
    call assert_a
    ld a,1
    ld (w3d_audio_sfx_enabled),a
    xor a
    ld (w3d_music_enabled),a
    call w3d_config_decode_file
    CHECK_A 0,REASON_RESULT
    ld a,(test_combo)
    and 1
    ld e,a
    ld a,(w3d_audio_sfx_enabled)
    ld b,e
    ld c,REASON_SFX
    call assert_a
    ld a,(test_combo)
    and 2
    jr z,@expect_music
    ld a,1
@expect_music:
    ld e,a
    ld a,(w3d_music_enabled)
    ld b,e
    ld c,REASON_MUSIC
    call assert_a
    ld a,(test_combo)
    inc a
    ld (test_combo),a
    cp 4
    jr c,@combo
    ret

test_corrupt_images:
    ld a,3
    ld (test_case),a
    ld a,1
    ld (w3d_audio_sfx_enabled),a
    ld (w3d_music_enabled),a
    call w3d_config_encode_file
    ld a,(w3d_config_file_buffer+W3D_CONFIG_CHECKSUM_1)
    xor 80h
    ld (w3d_config_file_buffer+W3D_CONFIG_CHECKSUM_1),a
    xor a
    ld (w3d_audio_sfx_enabled),a
    ld (w3d_music_enabled),a
    call w3d_config_decode_file
    CHECK_A 1,REASON_RESULT
    CHECK_MEM8 w3d_audio_sfx_enabled,1,REASON_SFX
    CHECK_MEM8 w3d_music_enabled,1,REASON_MUSIC

    call w3d_config_encode_file
    ld a,'!'
    ld (w3d_config_file_buffer+W3D_CONFIG_FOOTER_OFFSET),a
    call w3d_config_decode_file
    CHECK_A 1,REASON_RESULT

    call w3d_config_encode_file
    ld a,80h
    ld (w3d_config_file_buffer+W3D_CONFIG_FLAGS_OFFSET),a
    cpl
    ld (w3d_config_file_buffer+W3D_CONFIG_FLAGS_XOR),a
    ld hl,w3d_config_file_buffer
    ld bc,10
    call w3d_config_fletcher16
    ld a,(w3d_config_checksum_1)
    ld (w3d_config_file_buffer+W3D_CONFIG_CHECKSUM_1),a
    ld a,(w3d_config_checksum_2)
    ld (w3d_config_file_buffer+W3D_CONFIG_CHECKSUM_2),a
    call w3d_config_decode_file
    CHECK_A 1,REASON_RESULT
    ret

test_production_round_trip:
    ld a,4
    ld (test_case),a
    xor a
    ld (w3d_audio_sfx_enabled),a
    ld a,1
    ld (w3d_music_enabled),a
    call w3d_config_save
    ld a,0
    adc a,0
    CHECK_A 0,REASON_FILE_IO
    ld a,1
    ld (w3d_audio_sfx_enabled),a
    xor a
    ld (w3d_music_enabled),a
    call w3d_config_initialize
    CHECK_MEM8 w3d_audio_sfx_enabled,0,REASON_SFX
    CHECK_MEM8 w3d_music_enabled,1,REASON_MUSIC
    ret

test_exact_length:
    ld a,5
    ld (test_case),a
    call w3d_config_encode_file
    ld a,55h
    ld (w3d_config_file_buffer+W3D_CONFIG_FILE_SIZE),a
    ld de,W3D_CONFIG_READ_SIZE
    call write_config_prefix
    xor a
    ld (w3d_audio_sfx_enabled),a
    ld (w3d_music_enabled),a
    call w3d_config_initialize
    CHECK_MEM8 w3d_audio_sfx_enabled,1,REASON_SFX
    CHECK_MEM8 w3d_music_enabled,1,REASON_MUSIC

    ld de,8
    call write_config_prefix
    xor a
    ld (w3d_audio_sfx_enabled),a
    ld (w3d_music_enabled),a
    call w3d_config_initialize
    CHECK_MEM8 w3d_audio_sfx_enabled,1,REASON_SFX
    CHECK_MEM8 w3d_music_enabled,1,REASON_MUSIC
    ret

; DE=prefix length from the current in-memory image.
write_config_prefix:
    push de
    ld hl,w3d_config_filename
    ld c,fa_write|fa_create_always
    MOSCALL mos_fopen
    or a
    jr z,@open_failed
    ld (test_file_handle),a
    ld c,a
    ld hl,w3d_config_file_buffer
    pop de
    MOSCALL mos_fwrite
    push de
    ld a,(test_file_handle)
    ld c,a
    MOSCALL mos_fclose
    pop de
    ret
@open_failed:
    pop de
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
    ld (test_file_handle),a
    ld c,a
    ld hl,result_data
    ld de,result_end-result_data
    MOSCALL mos_fwrite
    ld a,(test_file_handle)
    ld c,a
    MOSCALL mos_fclose
    ret

result_filename: db "config_result.bin",0
test_file_handle: db 0
test_case: db 0
test_combo: db 0
result_data:
    db "W3C1"
result_checks: db 0
result_errors: db 0
result_first_case: db 0ffh
result_first_reason: db 0
result_first_expected: db 0
result_first_actual: db 0
    db 0,0,0,0,0,0
result_end:
