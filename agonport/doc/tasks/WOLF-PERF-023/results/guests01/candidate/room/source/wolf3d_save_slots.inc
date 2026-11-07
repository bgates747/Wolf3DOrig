; =============================================================================
; Original ten-slot save/load persistence wrapper.
;
; SAVEGAM0..9.W3S mirror the source game's stable slot identity. Each file is
; an exact versioned save image with a 32-byte description in its header.
; Scanning and loading fail closed on missing, truncated, overlong, corrupt,
; incompatible, or semantically invalid data. A successful load remains
; staged until the application has loaded the matching canonical level assets;
; only then does w3d_save_decode transactionally publish the simulation.
; =============================================================================

W3D_SAVE_SLOT_COUNT:        equ 10
W3D_SAVE_SLOT_NAME_MAX:     equ W3D_SAVE_NAME_SIZE-1
W3D_SAVE_SLOT_DIGIT_OFFSET: equ 7

; Scan all ten filenames and cache only validated descriptions. Missing and
; damaged slots are ordinary empty rows, not startup failures.
w3d_save_slots_initialize:
    xor a
    ld (w3d_save_pending_load),a
    ld (w3d_save_slot_index),a
    ld hl,w3d_save_slot_available
    ld (hl),a
    ld de,w3d_save_slot_available+1
    ld bc,W3D_SAVE_SLOT_COUNT-1
    ldir
    ld hl,w3d_save_slot_names
    ld (hl),a
    ld de,w3d_save_slot_names+1
    ld bc,W3D_SAVE_SLOT_COUNT*W3D_SAVE_NAME_SIZE-1
    ldir
@slot:
    ld a,(w3d_save_slot_index)
    call w3d_save_slot_read_image
    jr c,@next
    call w3d_save_validate_header
    jr c,@next
    call w3d_save_validate_semantics
    jr c,@next
    call w3d_save_slot_validate_name
    jr c,@next
    call w3d_save_slot_publish_metadata
@next:
    ld a,(w3d_save_slot_index)
    inc a
    ld (w3d_save_slot_index),a
    cp W3D_SAVE_SLOT_COUNT
    jr c,@slot
    or a
    ret

; A=slot. Read and validate an exact image. On success, leave it staged,
; select its canonical level/difficulty, and latch a deferred load request.
w3d_save_slot_load:
    cp W3D_SAVE_SLOT_COUNT
    jr nc,@failed
    ld (w3d_save_slot_index),a
    call w3d_save_slot_read_image
    jr c,@failed
    call w3d_save_validate_header
    jr c,@failed
    call w3d_save_validate_semantics
    jr c,@failed
    call w3d_save_slot_validate_name
    jr c,@failed
    call w3d_save_slot_publish_metadata
    ld a,(w3d_save_file_buffer+W3D_SAVE_H_LEVEL)
    ld (w3d_level_requested_index),a
    ld a,(w3d_save_file_buffer+W3D_SAVE_H_DIFFICULTY)
    ld (w3d_requested_difficulty),a
    ld a,1
    ld (w3d_save_pending_load),a
    or a
    ret
@failed:
    xor a
    ld (w3d_save_pending_load),a
    scf
    ret

; A=slot, HL=zero-terminated description. Encode and replace the complete
; file. Return carry clear only when MOS reports the exact byte count.
w3d_save_slot_store:
    cp W3D_SAVE_SLOT_COUNT
    jr nc,@failed
    ld (w3d_save_slot_index),a
    push hl
    call w3d_save_encode
    pop hl
    ld de,w3d_save_file_buffer+W3D_SAVE_H_NAME
    ld b,W3D_SAVE_SLOT_NAME_MAX
@name:
    ld a,(hl)
    or a
    jr z,@name_done
    ld (de),a
    inc hl
    inc de
    djnz @name
@name_done:
    xor a
    ld (de),a
    call w3d_save_slot_prepare_filename
    ld hl,w3d_save_slot_filename
    ld c,fa_write|fa_create_always
    MOSCALL mos_fopen
    or a
    jr z,@failed
    ld (w3d_save_slot_handle),a
    ld c,a
    ld hl,w3d_save_file_buffer
    ld de,W3D_SAVE_FILE_SIZE
    MOSCALL mos_fwrite
    push de
    ld a,(w3d_save_slot_handle)
    ld c,a
    MOSCALL mos_fclose
    pop hl
    ld de,W3D_SAVE_FILE_SIZE
    or a
    sbc.s hl,de
    jr nz,@failed
    call w3d_save_slot_publish_metadata
    or a
    ret
@failed:
    scf
    ret

; Publish a previously staged valid image after its canonical package and
; assets are active. Clear the pending latch only on success.
w3d_save_slot_publish_pending:
    ld a,(w3d_save_pending_load)
    or a
    ret z
    call w3d_save_decode
    ret c
    xor a
    ld (w3d_save_pending_load),a
    ret

; A=slot. Carry clear iff exactly W3D_SAVE_FILE_SIZE bytes were read and no
; extra byte exists. The buffer intentionally owns one guard byte for this.
w3d_save_slot_read_image:
    ld (w3d_save_slot_index),a
    call w3d_save_slot_prepare_filename
    ld hl,w3d_save_slot_filename
    ld c,fa_read
    MOSCALL mos_fopen
    or a
    jr z,@failed
    ld (w3d_save_slot_handle),a
    ld c,a
    ld hl,w3d_save_file_buffer
    ld de,W3D_SAVE_FILE_SIZE+1
    MOSCALL mos_fread
    push de
    ld a,(w3d_save_slot_handle)
    ld c,a
    MOSCALL mos_fclose
    pop hl
    ld de,W3D_SAVE_FILE_SIZE
    or a
    sbc.s hl,de
    jr nz,@failed
    or a
    ret
@failed:
    scf
    ret

w3d_save_slot_prepare_filename:
    ld a,(w3d_save_slot_index)
    add a,'0'
    ld (w3d_save_slot_filename+W3D_SAVE_SLOT_DIGIT_OFFSET),a
    ret

; Require a terminator in the complete original 32-byte name field.
w3d_save_slot_validate_name:
    ld hl,w3d_save_file_buffer+W3D_SAVE_H_NAME
    ld b,W3D_SAVE_NAME_SIZE
@byte:
    ld a,(hl)
    or a
    ret z
    inc hl
    djnz @byte
    scf
    ret

; Cache availability and description for the currently selected slot.
w3d_save_slot_publish_metadata:
    ld a,(w3d_save_slot_index)
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_save_slot_available
    add hl,de
    ld (hl),1
    ld a,(w3d_save_slot_index)
    ld d,a
    ld e,W3D_SAVE_NAME_SIZE
    mlt de
    inc de
    dec.s de
    ld hl,w3d_save_slot_names
    add hl,de
    ex de,hl
    ld hl,w3d_save_file_buffer+W3D_SAVE_H_NAME
    ld bc,W3D_SAVE_NAME_SIZE
    ldir
    ret

w3d_save_pending_load:
    db 0
w3d_save_slot_index:
    db 0
w3d_save_slot_handle:
    db 0
w3d_save_slot_available:
    ds W3D_SAVE_SLOT_COUNT
w3d_save_slot_names:
    ds W3D_SAVE_SLOT_COUNT*W3D_SAVE_NAME_SIZE
w3d_save_slot_filename:
    db "savegam0.w3s",0
