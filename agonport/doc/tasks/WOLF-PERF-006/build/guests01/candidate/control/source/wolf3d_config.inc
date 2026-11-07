; =============================================================================
; Durable Agon-facing Wolf3D preferences.
;
; WL_MAIN.C::ReadConfig/WriteConfig persists the original sound, music,
; device, control, view-size, and mouse-sensitivity selections. Agon exposes
; only two mutable equivalents: sound effects and music. Keep those across
; MOS launches without pretending that fixed viewport/controls or absent DOS
; devices are configurable.
;
; The 16-byte image is versioned, exact-length, guarded by a Fletcher-16 over
; the first ten bytes, and terminated by a second magic. Decode publishes
; preferences only after every check succeeds; missing/truncated/corrupt or
; future-version files therefore select the documented on/on defaults.
; =============================================================================

W3D_CONFIG_FILE_SIZE:       equ 16
W3D_CONFIG_READ_SIZE:       equ W3D_CONFIG_FILE_SIZE+1
W3D_CONFIG_FLAGS_OFFSET:    equ 6
W3D_CONFIG_FLAGS_XOR:       equ 7
W3D_CONFIG_CHECKSUM_1:      equ 10
W3D_CONFIG_CHECKSUM_2:      equ 11
W3D_CONFIG_FOOTER_OFFSET:   equ 12
W3D_CONFIG_FLAG_SFX:        equ 00000001b
W3D_CONFIG_FLAG_MUSIC:      equ 00000010b
W3D_CONFIG_FLAGS_VALID:     equ W3D_CONFIG_FLAG_SFX|W3D_CONFIG_FLAG_MUSIC

w3d_config_initialize:
    call w3d_config_reset_defaults
    ld hl,w3d_config_filename
    ld c,fa_read
    MOSCALL mos_fopen
    or a
    ret z
    ld (w3d_config_file_handle),a
    ld c,a
    ld hl,w3d_config_file_buffer
    ld de,W3D_CONFIG_READ_SIZE
    MOSCALL mos_fread
    push de
    ld a,(w3d_config_file_handle)
    ld c,a
    MOSCALL mos_fclose
    pop hl
    ld de,W3D_CONFIG_FILE_SIZE
    or a
    sbc hl,de
    jr nz,@invalid
    jp w3d_config_decode_file
@invalid:
    jp w3d_config_reset_defaults

; Return carry clear only after the complete preference image is written.
w3d_config_save:
    call w3d_config_encode_file
    ld hl,w3d_config_filename
    ld c,fa_write|fa_create_always
    MOSCALL mos_fopen
    or a
    jr z,@failed
    ld (w3d_config_file_handle),a
    ld c,a
    ld hl,w3d_config_file_buffer
    ld de,W3D_CONFIG_FILE_SIZE
    MOSCALL mos_fwrite
    push de
    ld a,(w3d_config_file_handle)
    ld c,a
    MOSCALL mos_fclose
    pop hl
    ld de,W3D_CONFIG_FILE_SIZE
    or a
    sbc hl,de
    jr nz,@failed
    or a
    ret
@failed:
    scf
    ret

w3d_config_reset_defaults:
    ld a,1
    ld (w3d_audio_sfx_enabled),a
    ld (w3d_music_enabled),a
    xor a
    ret

w3d_config_encode_file:
    ld hl,w3d_config_file_template
    ld de,w3d_config_file_buffer
    ld bc,W3D_CONFIG_FILE_SIZE
    ldir
    ld b,0
    ld a,(w3d_audio_sfx_enabled)
    or a
    jr z,@music
    set 0,b
@music:
    ld a,(w3d_music_enabled)
    or a
    jr z,@flags_ready
    set 1,b
@flags_ready:
    ld a,b
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
    ret

; A=0/Z on success. Any failure republishes on/on defaults and returns NZ.
w3d_config_decode_file:
    ld hl,w3d_config_file_buffer
    ld de,w3d_config_file_template
    ld b,6
@header:
    ld a,(de)
    cp (hl)
    jr nz,@invalid
    inc de
    inc hl
    djnz @header
    ld a,(w3d_config_file_buffer+W3D_CONFIG_FLAGS_OFFSET)
    ld b,a
    and ~W3D_CONFIG_FLAGS_VALID
    jr nz,@invalid
    ld a,(w3d_config_file_buffer+W3D_CONFIG_FLAGS_XOR)
    cpl
    cp b
    jr nz,@invalid
    ld a,(w3d_config_file_buffer+8)
    or a
    jr nz,@invalid
    ld a,(w3d_config_file_buffer+9)
    or a
    jr nz,@invalid
    ld hl,w3d_config_file_buffer+W3D_CONFIG_FOOTER_OFFSET
    ld de,w3d_config_file_template+W3D_CONFIG_FOOTER_OFFSET
    ld b,4
@footer:
    ld a,(de)
    cp (hl)
    jr nz,@invalid
    inc de
    inc hl
    djnz @footer
    ld hl,w3d_config_file_buffer
    ld bc,10
    call w3d_config_fletcher16
    ld a,(w3d_config_file_buffer+W3D_CONFIG_CHECKSUM_1)
    ld b,a
    ld a,(w3d_config_checksum_1)
    cp b
    jr nz,@invalid
    ld a,(w3d_config_file_buffer+W3D_CONFIG_CHECKSUM_2)
    ld b,a
    ld a,(w3d_config_checksum_2)
    cp b
    jr nz,@invalid
    ld a,(w3d_config_file_buffer+W3D_CONFIG_FLAGS_OFFSET)
    ld b,a
    and W3D_CONFIG_FLAG_SFX
    ld (w3d_audio_sfx_enabled),a
    ld a,b
    and W3D_CONFIG_FLAG_MUSIC
    jr z,@music_ready
    ld a,1
@music_ready:
    ld (w3d_music_enabled),a
    xor a
    ret
@invalid:
    call w3d_config_reset_defaults
    ld a,1
    or a
    ret

; HL=data, BC=length. Standard Fletcher-16 modulo-255 sums.
w3d_config_fletcher16:
    xor a
    ld (w3d_config_checksum_1),a
    ld (w3d_config_checksum_2),a
@byte:
    ld a,(w3d_config_checksum_1)
    add a,(hl)
    jr nc,@sum1_folded
    inc a
@sum1_folded:
    cp 0ffh
    jr nz,@sum1_ready
    xor a
@sum1_ready:
    ld (w3d_config_checksum_1),a
    ld d,a
    ld a,(w3d_config_checksum_2)
    add a,d
    jr nc,@sum2_folded
    inc a
@sum2_folded:
    cp 0ffh
    jr nz,@sum2_ready
    xor a
@sum2_ready:
    ld (w3d_config_checksum_2),a
    inc hl
    dec.s bc
    ld a,b
    or c
    jr nz,@byte
    ret

w3d_config_filename:
    db "wolf3d.cfg",0
w3d_config_file_template:
    db "W3CF",1,W3D_CONFIG_FILE_SIZE
    db W3D_CONFIG_FLAGS_VALID,0ffh-W3D_CONFIG_FLAGS_VALID
    db 0,0,0,0
    db "FC3W"
w3d_config_file_buffer:
    ds W3D_CONFIG_READ_SIZE
w3d_config_file_handle:
    db 0
w3d_config_checksum_1:
    db 0
w3d_config_checksum_2:
    db 0
