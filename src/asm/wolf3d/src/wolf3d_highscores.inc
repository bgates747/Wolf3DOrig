; =============================================================================
; Original Wolf3D shareware high-score ordering core.
;
; ID_US.H defines seven records containing a 58-byte name, unsigned 32-bit
; score, completed-floor word, and episode word.  CheckHighScore orders first
; by descending score, then by descending completed floor; episode is display
; metadata and does not participate in qualification.  Presentation, name
; editing, and durable file I/O are separate shell-facing layers so this core
; can be exercised directly on a real eZ80.
; =============================================================================

W3D_HIGHSCORE_COUNT:             equ 7
W3D_HIGHSCORE_NAME_MAX:          equ 57
W3D_HIGHSCORE_NAME_SIZE:         equ 58
W3D_HIGHSCORE_NAME:              equ 0
W3D_HIGHSCORE_SCORE:             equ 58
W3D_HIGHSCORE_COMPLETED:         equ 62
W3D_HIGHSCORE_EPISODE:           equ 64
W3D_HIGHSCORE_RECORD_SIZE:       equ 66
W3D_HIGHSCORE_NO_SLOT:           equ 0ffh
W3D_HIGHSCORE_FILE_HEADER_SIZE:   equ 16
W3D_HIGHSCORE_FILE_PAYLOAD_SIZE:  equ 462
W3D_HIGHSCORE_FILE_FOOTER:        equ 478
W3D_HIGHSCORE_FILE_SIZE:          equ 482
W3D_HIGHSCORE_VISIBLE_NAME_MAX:   equ 12
W3D_HIGHSCORE_ROW_FIRST:          equ 9
W3D_HIGHSCORE_ROW_STEP:           equ 2
W3D_HIGHSCORE_NAME_COLUMN:        equ 4
W3D_HIGHSCORE_LEVEL_END_COLUMN:   equ 22
W3D_HIGHSCORE_SCORE_END_COLUMN:   equ 33
; IN_UserInput(500) at the original 70 Hz, rounded to MOS's 120 Hz clock.
W3D_HIGHSCORE_DISPLAY_TICKS:       equ 857

; ---------------------------------------------------------------------------
; Production persistence and original-facing presentation
; ---------------------------------------------------------------------------

; Missing, truncated, corrupt, or incompatible files are all ordinary first-
; run conditions.  Defaults are published before opening and decode is
; transactional, so no failure can expose a partial table.
w3d_highscores_initialize:
    call w3d_highscores_reset_defaults
    call w3d_highscores_reset_key_hook
    ld hl,w3d_highscores_filename
    ld c,fa_read
    MOSCALL mos_fopen
    or a
    ret z
    ld (w3d_highscores_file_handle),a
    ld c,a
    ld hl,w3d_highscores_file_buffer
    ld de,W3D_HIGHSCORE_FILE_SIZE
    MOSCALL mos_fread
    push de
    ld a,(w3d_highscores_file_handle)
    ld c,a
    MOSCALL mos_fclose
    pop hl
    ld de,W3D_HIGHSCORE_FILE_SIZE
    or a
    sbc.s hl,de
    jr nz,@invalid
    jp w3d_highscores_decode_file
@invalid:
    jp w3d_highscores_reset_defaults

; Return carry clear only when the complete versioned image was written.
w3d_highscores_save:
    call w3d_highscores_encode_file
    ld hl,w3d_highscores_filename
    ld c,fa_write|fa_create_always
    MOSCALL mos_fopen
    or a
    jr z,@failed
    ld (w3d_highscores_file_handle),a
    ld c,a
    ld hl,w3d_highscores_file_buffer
    ld de,W3D_HIGHSCORE_FILE_SIZE
    MOSCALL mos_fwrite
    push de
    ld a,(w3d_highscores_file_handle)
    ld c,a
    MOSCALL mos_fclose
    pop hl
    ld de,W3D_HIGHSCORE_FILE_SIZE
    or a
    sbc.s hl,de
    jr nz,@failed
    or a
    ret
@failed:
    scf
    ret

; Original CheckHighScore(score,mapon+1) lifecycle.  The shareware episode is
; zero, and the source passes the one-based current floor even on game over.
; Escape remains application-global during both line entry and acknowledgment.
w3d_highscores_handle_game_end:
    ld hl,w3d_player_score
    ld de,w3d_highscores_candidate_score
    ld bc,4
    ldir
    xor a
    ld (w3d_highscores_candidate_completed+1),a
    ld (w3d_highscores_candidate_episode+0),a
    ld (w3d_highscores_candidate_episode+1),a
    ld a,(w3d_level_requested_index)
    inc a
    ld (w3d_highscores_candidate_completed+0),a
    call w3d_highscores_consider
    cp W3D_HIGHSCORE_NO_SLOT
    jr z,@not_inserted
    call w3d_highscores_edit_inserted_name
    call w3d_highscores_save
    ret
@not_inserted:
    call w3d_highscores_draw
    jp w3d_highscores_wait_nonqualifying

w3d_highscores_view:
    call w3d_highscores_draw
    jp w3d_shell_wait_any_press

; CheckHighScore's non-qualifying path is not an indefinite acknowledgment:
; the source calls IN_UserInput(500), returning on any key or after 500
; original 70-Hz ticks. Escape still owns the common application-exit latch.
w3d_highscores_wait_nonqualifying:
    call w3d_shell_wait_all_released
    call w3d_shell_query_exit_request
    ret nz
    ld ix,(w3d_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld (w3d_highscores_wait_started),hl
@wait:
    call w3d_shell_read_keyboard
    bit 0,(ix+14)
    jr nz,@escape
    ld b,16
@scan:
    ld a,(ix)
    or a
    jr nz,@pressed
    inc ix
    djnz @scan
    ld ix,(w3d_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld de,(w3d_highscores_wait_started)
    or a
    sbc hl,de
    ld de,W3D_HIGHSCORE_DISPLAY_TICKS
    or a
    sbc hl,de
    jr c,@wait
    ret
@escape:
    call w3d_shell_request_exit
@pressed:
    jp w3d_shell_wait_all_released

; Draw the invariant original backdrop plus the seven mutable records. Mode
; 136 retains mode 8's native 8-pixel text grid, matching the source column
; anchors; every row is separated by 16 pixels exactly as DrawHighScores does.
w3d_highscores_draw:
    call @frame
    call w3d_vdu_present
@frame:
    call w3d_shell_clear
    ld hl,W3D_SHELL_HIGH_SCORES_BASE_BUFFER
    call w3d_shell_plot_full_screen
    ld hl,w3d_highscores_text_colours
    ld bc,w3d_highscores_text_colours_end-w3d_highscores_text_colours
    rst.lil 18h
    ld ix,w3d_highscores
    ld b,W3D_HIGHSCORE_COUNT
    ld c,W3D_HIGHSCORE_ROW_FIRST
@row:
    push bc
    push ix
    push ix
    pop hl
    push hl
    ld a,W3D_HIGHSCORE_NAME_COLUMN
    call w3d_highscores_set_cursor
    pop hl
    call printString
    pop ix

    push ix
    lea hl,ix+W3D_HIGHSCORE_COMPLETED
    call w3d_highscores_format_u16
    call w3d_highscores_string_length
    ld a,W3D_HIGHSCORE_LEVEL_END_COLUMN
    sub e
    pop ix
    push ix
    push hl
    call w3d_highscores_set_cursor
    pop hl
    call printString
    pop ix

    push ix
    lea hl,ix+W3D_HIGHSCORE_SCORE
    call w3d_highscores_format_u32
    call w3d_highscores_string_length
    ld a,W3D_HIGHSCORE_SCORE_END_COLUMN
    sub e
    pop ix
    push ix
    push hl
    call w3d_highscores_set_cursor
    pop hl
    call printString
    pop ix
    pop bc
    ld a,c
    add a,W3D_HIGHSCORE_ROW_STEP
    ld c,a
    lea ix,ix+W3D_HIGHSCORE_RECORD_SIZE
    djnz @row
    ret

; Edit at most the 100-pixel original input width (twelve native characters).
; The stored format retains the original 57-character capacity for forward
; compatibility. Escape requests the common clean application exit.
w3d_highscores_edit_inserted_name:
    xor a
    ld (w3d_highscores_name_length),a
    ld (w3d_highscores_name_edit),a
@redraw:
    call w3d_highscores_draw
    call @draw_cursor
    call w3d_vdu_present
    call @draw_cursor
    jr @key
@draw_cursor:
    ld a,(w3d_highscores_inserted_slot)
    add a,a
    add a,W3D_HIGHSCORE_ROW_FIRST
    ld c,a
    ld a,(w3d_highscores_name_length)
    add a,W3D_HIGHSCORE_NAME_COLUMN
    call w3d_highscores_set_cursor
    ld a,'_'
    rst.lil 10h
    ret
@key:
    call w3d_highscores_read_key
    cp 27
    jr z,@escape
    cp 13
    jr z,@accept
    cp 10
    jr z,@accept
    cp 8
    jr z,@backspace
    cp 127
    jr z,@backspace
    cp 32
    jr c,@key
    cp 127
    jr nc,@key
    ld b,a
    ld a,(w3d_highscores_name_length)
    cp W3D_HIGHSCORE_VISIBLE_NAME_MAX
    jr nc,@key
    ld e,a
    ld d,0
    inc de
    dec.s de                 ; undocumented eZ80 idiom: DEU=0
    ld a,b
    ld hl,w3d_highscores_name_edit
    add hl,de
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    ld a,e
    inc a
    ld (w3d_highscores_name_length),a
    jp @redraw
@backspace:
    ld a,(w3d_highscores_name_length)
    or a
    jr z,@key
    dec a
    ld (w3d_highscores_name_length),a
    ld e,a
    ld d,0
    inc de
    dec.s de                 ; undocumented eZ80 idiom: DEU=0
    ld hl,w3d_highscores_name_edit
    add hl,de
    xor a
    ld (hl),a
    jp @redraw
@escape:
    call w3d_shell_request_exit
@accept:
    ld hl,w3d_highscores_name_edit
    jp w3d_highscores_set_inserted_name

w3d_highscores_set_key_hook:
    ld (w3d_highscores_key_hook),hl
    ret

w3d_highscores_reset_key_hook:
    ld hl,w3d_highscores_getkey_default
    ld (w3d_highscores_key_hook),hl
    ret

w3d_highscores_read_key:
    ld hl,(w3d_highscores_key_hook)
    jp (hl)

w3d_highscores_getkey_default:
    MOSCALL mos_getkey
    ret

; A=column, C=row.  The command is patched bytewise to avoid native-ADL stores
; where only the two one-byte VDU parameters are meaningful.
w3d_highscores_set_cursor:
    push bc
    ld (w3d_highscores_cursor_command+1),a
    ld a,c
    ld (w3d_highscores_cursor_command+2),a
    ld hl,w3d_highscores_cursor_command
    ld bc,3
    rst.lil 18h
    pop bc
    ret

; HL -> u16 / u32 little-endian. Return HL -> zero-terminated decimal text.
w3d_highscores_format_u16:
    ld de,w3d_highscores_number_work
    ld bc,2
    ldir
    xor a
    ld (de),a
    inc de
    ld (de),a
    jr w3d_highscores_format_work

w3d_highscores_format_u32:
    ld de,w3d_highscores_number_work
    ld bc,4
    ldir

w3d_highscores_format_work:
    xor a
    ld (w3d_highscores_number_text+10),a
    ld ix,w3d_highscores_number_text
    lea ix,ix+10
@digit:
    call w3d_highscores_divide_work_by_10
    add a,'0'
    dec ix
    ld (ix),a
    ld hl,w3d_highscores_number_work
    ld b,4
    xor a
@nonzero:
    or (hl)
    inc hl
    djnz @nonzero
    jr nz,@digit
    push ix
    pop hl
    ret

; Divide the four-byte work value by ten in place and return remainder in A.
w3d_highscores_divide_work_by_10:
    ld iy,w3d_highscores_number_work+3
    xor a
    ld e,4
@byte:
    ld c,(iy)
    ld d,0
    ld b,8
@bit:
    sla c
    adc a,a
    cp 10
    jr c,@quotient_zero
    sub 10
    scf
    jr @shift_quotient
@quotient_zero:
    or a
@shift_quotient:
    rl d
    djnz @bit
    ld (iy),d
    dec iy
    dec e
    jr nz,@byte
    ret

; HL -> text. Return E=length while preserving HL.
w3d_highscores_string_length:
    push hl
    ld e,0
@scan:
    ld a,(hl)
    or a
    jr z,@done
    inc hl
    inc e
    jr @scan
@done:
    pop hl
    ret

; Restore the exact ID_US_1.C default roster.  Initializers omit episode, so
; the C static-storage rule supplies zero for every default record.
w3d_highscores_reset_defaults:
    ld hl,w3d_highscores_defaults
    ld de,w3d_highscores
    ld bc,W3D_HIGHSCORE_COUNT*W3D_HIGHSCORE_RECORD_SIZE
    ldir
    ld a,W3D_HIGHSCORE_NO_SLOT
    ld (w3d_highscores_inserted_slot),a
    ret

; Compare the public candidate fields with the live table and insert it at the
; first qualifying row.  Return A=0..6 for the inserted row, or $ff when the
; candidate does not qualify.  A score tie qualifies only when completed is
; strictly greater, matching CheckHighScore exactly.
w3d_highscores_consider:
    ld ix,w3d_highscores
    ld c,0
    ld b,W3D_HIGHSCORE_COUNT
@row:
    ld a,(w3d_highscores_candidate_score+3)
    cp (ix+W3D_HIGHSCORE_SCORE+3)
    jr c,@next
    jr nz,@qualifies
    ld a,(w3d_highscores_candidate_score+2)
    cp (ix+W3D_HIGHSCORE_SCORE+2)
    jr c,@next
    jr nz,@qualifies
    ld a,(w3d_highscores_candidate_score+1)
    cp (ix+W3D_HIGHSCORE_SCORE+1)
    jr c,@next
    jr nz,@qualifies
    ld a,(w3d_highscores_candidate_score+0)
    cp (ix+W3D_HIGHSCORE_SCORE+0)
    jr c,@next
    jr nz,@qualifies
    ld a,(w3d_highscores_candidate_completed+1)
    cp (ix+W3D_HIGHSCORE_COMPLETED+1)
    jr c,@next
    jr nz,@qualifies
    ld a,(w3d_highscores_candidate_completed+0)
    cp (ix+W3D_HIGHSCORE_COMPLETED+0)
    jr c,@next
    jr z,@next
@qualifies:
    ld a,c
    jp w3d_highscores_insert_at
@next:
    lea ix,ix+W3D_HIGHSCORE_RECORD_SIZE
    inc c
    djnz @row
    ld a,W3D_HIGHSCORE_NO_SLOT
    ld (w3d_highscores_inserted_slot),a
    ret

; A=slot 0..6. Shift the suffix down one row with a single overlap-safe LDDR,
; clear the destination record, and install the candidate with an empty name.
w3d_highscores_insert_at:
    ld (w3d_highscores_inserted_slot),a
    cp W3D_HIGHSCORE_COUNT-1
    jr z,@write
    ld c,a
    ld a,W3D_HIGHSCORE_COUNT-1
    sub c
    ld de,0
    ld d,a
    ld e,W3D_HIGHSCORE_RECORD_SIZE
    mlt de
    push de
    pop bc
    ld hl,w3d_highscores+395
    ld de,w3d_highscores+W3D_HIGHSCORE_FILE_PAYLOAD_SIZE-1
    lddr
@write:
    ld a,(w3d_highscores_inserted_slot)
    ld de,0
    ld d,a
    ld e,W3D_HIGHSCORE_RECORD_SIZE
    mlt de
    ld hl,w3d_highscores
    add hl,de
    push hl
    xor a
    ld (hl),a
    push hl
    pop de
    inc de
    ld bc,W3D_HIGHSCORE_RECORD_SIZE-1
    ldir
    pop ix
    ld hl,w3d_highscores_candidate_score
    lea de,ix+W3D_HIGHSCORE_SCORE
    ld bc,4
    ldir
    ld hl,w3d_highscores_candidate_completed
    lea de,ix+W3D_HIGHSCORE_COMPLETED
    ld bc,2
    ldir
    ld hl,w3d_highscores_candidate_episode
    lea de,ix+W3D_HIGHSCORE_EPISODE
    ld bc,2
    ldir
    ld a,(w3d_highscores_inserted_slot)
    ret

; HL -> zero-terminated candidate name. Copy at most the original 57-byte
; limit into the most recently inserted row and always terminate.  A no-slot
; call is harmless, which simplifies cancellation and non-qualification paths.
w3d_highscores_set_inserted_name:
    ld a,(w3d_highscores_inserted_slot)
    cp W3D_HIGHSCORE_COUNT
    ret nc
    push hl
    ld de,0
    ld d,a
    ld e,W3D_HIGHSCORE_RECORD_SIZE
    mlt de
    ld ix,w3d_highscores
    add ix,de
    pop hl
    lea de,ix+W3D_HIGHSCORE_NAME
    ld b,W3D_HIGHSCORE_NAME_MAX
@copy:
    ld a,(hl)
    or a
    jr z,@terminate
    ld (de),a
    inc hl
    inc de
    djnz @copy
@terminate:
    xor a
    ld (de),a
    ret

; Build the complete versioned persistence image.  The payload is the exact
; seven-record table; a Fletcher-16 checksum and trailing magic make cleared,
; truncated, corrupt, and incompatible loads fail closed.
w3d_highscores_encode_file:
    ld hl,w3d_highscores_file_header
    ld de,w3d_highscores_file_buffer
    ld bc,W3D_HIGHSCORE_FILE_HEADER_SIZE
    ldir
    ld hl,w3d_highscores
    ld de,w3d_highscores_file_buffer+W3D_HIGHSCORE_FILE_HEADER_SIZE
    ld bc,W3D_HIGHSCORE_FILE_PAYLOAD_SIZE
    ldir
    ld hl,w3d_highscores_file_footer
    ld de,w3d_highscores_file_buffer+W3D_HIGHSCORE_FILE_FOOTER
    ld bc,4
    ldir
    ld hl,w3d_highscores_file_buffer+W3D_HIGHSCORE_FILE_HEADER_SIZE
    ld bc,W3D_HIGHSCORE_FILE_PAYLOAD_SIZE
    call w3d_highscores_fletcher16
    ld a,(w3d_highscores_checksum_1)
    ld (w3d_highscores_file_buffer+12),a
    ld a,(w3d_highscores_checksum_2)
    ld (w3d_highscores_file_buffer+13),a
    ret

; Validate the in-memory file image and publish its table only after every
; field succeeds. Return A=0/Z on success. Any failure restores the original
; default roster and returns A=1/NZ.
w3d_highscores_decode_file:
    ld hl,w3d_highscores_file_buffer
    ld de,w3d_highscores_file_header
    ld b,12
@header:
    ld a,(de)
    cp (hl)
    jr nz,@invalid
    inc de
    inc hl
    djnz @header
    ld hl,w3d_highscores_file_buffer+14
    ld de,w3d_highscores_file_header+14
    ld b,2
@header_tail:
    ld a,(de)
    cp (hl)
    jr nz,@invalid
    inc de
    inc hl
    djnz @header_tail
    ld hl,w3d_highscores_file_buffer+W3D_HIGHSCORE_FILE_FOOTER
    ld de,w3d_highscores_file_footer
    ld b,4
@footer:
    ld a,(de)
    cp (hl)
    jr nz,@invalid
    inc de
    inc hl
    djnz @footer
    ld hl,w3d_highscores_file_buffer+W3D_HIGHSCORE_FILE_HEADER_SIZE
    ld bc,W3D_HIGHSCORE_FILE_PAYLOAD_SIZE
    call w3d_highscores_fletcher16
    ld a,(w3d_highscores_file_buffer+12)
    ld b,a
    ld a,(w3d_highscores_checksum_1)
    cp b
    jr nz,@invalid
    ld a,(w3d_highscores_file_buffer+13)
    ld b,a
    ld a,(w3d_highscores_checksum_2)
    cp b
    jr nz,@invalid
; A checksum-valid record is still structurally invalid when its fixed 58-byte
; name field has no terminator. Reject it before publishing so printString can
; never escape one record into score metadata or the next row.
    ld ix,w3d_highscores_file_buffer+W3D_HIGHSCORE_FILE_HEADER_SIZE
    ld b,W3D_HIGHSCORE_COUNT
@name_record:
    push bc
    push ix
    pop hl
    ld b,W3D_HIGHSCORE_NAME_SIZE
@name_byte:
    ld a,(hl)
    or a
    jr z,@name_valid
    inc hl
    djnz @name_byte
    pop bc
    jr @invalid
@name_valid:
    pop bc
    lea ix,ix+W3D_HIGHSCORE_RECORD_SIZE
    djnz @name_record
    ld hl,w3d_highscores_file_buffer+W3D_HIGHSCORE_FILE_HEADER_SIZE
    ld de,w3d_highscores
    ld bc,W3D_HIGHSCORE_FILE_PAYLOAD_SIZE
    ldir
    ld a,W3D_HIGHSCORE_NO_SLOT
    ld (w3d_highscores_inserted_slot),a
    xor a
    ret
@invalid:
    call w3d_highscores_reset_defaults
    ld a,1
    or a
    ret

; HL=data, BC=length.  Publish the standard Fletcher-16 modulo-255 sums in
; the two checksum bytes.  The end-around carry is equivalent to reducing an
; 8-bit addition modulo 255, avoiding division in this cold path.
w3d_highscores_fletcher16:
    xor a
    ld (w3d_highscores_checksum_1),a
    ld (w3d_highscores_checksum_2),a
@byte:
    ld a,(w3d_highscores_checksum_1)
    add a,(hl)
    jr nc,@sum1_folded
    inc a
@sum1_folded:
    cp 0ffh
    jr nz,@sum1_ready
    xor a
@sum1_ready:
    ld (w3d_highscores_checksum_1),a
    ld d,a
    ld a,(w3d_highscores_checksum_2)
    add a,d
    jr nc,@sum2_folded
    inc a
@sum2_folded:
    cp 0ffh
    jr nz,@sum2_ready
    xor a
@sum2_ready:
    ld (w3d_highscores_checksum_2),a
    inc hl
    dec.s bc
    ld a,b
    or c
    jr nz,@byte
    ret

; Public candidate. Production copies the current player score, Episode 1
; zero-based episode, and completed-floor value here before considering it.
w3d_highscores_candidate_score:
    ds 4
w3d_highscores_candidate_completed:
    dw 0
w3d_highscores_candidate_episode:
    dw 0
w3d_highscores_inserted_slot:
    db W3D_HIGHSCORE_NO_SLOT

w3d_highscores:
    ds W3D_HIGHSCORE_COUNT*W3D_HIGHSCORE_RECORD_SIZE

w3d_highscores_checksum_1:
    db 0
w3d_highscores_checksum_2:
    db 0

w3d_highscores_file_buffer:
    ds W3D_HIGHSCORE_FILE_SIZE

w3d_highscores_filename:
    db "scores.w3h",0
w3d_highscores_file_handle:
    db 0
w3d_highscores_key_hook:
    dl w3d_highscores_getkey_default
w3d_highscores_cursor_command:
    db 31,0,0
w3d_highscores_text_colours:
    db 17,15                 ; white foreground
    db 17,128+1              ; dark-red shell background
w3d_highscores_text_colours_end:
w3d_highscores_name_length:
    db 0
w3d_highscores_name_edit:
    ds W3D_HIGHSCORE_VISIBLE_NAME_MAX+1
w3d_highscores_number_work:
    ds 4
w3d_highscores_number_text:
    ds 11
w3d_highscores_wait_started:
    dl 0

w3d_highscores_file_header:
    db "W3HS"
    db 1,0
    db W3D_HIGHSCORE_COUNT,W3D_HIGHSCORE_RECORD_SIZE
    dw W3D_HIGHSCORE_FILE_PAYLOAD_SIZE
    dw 0
    dw 0                         ; Fletcher-16, patched in encoded image
    dw W3D_HIGHSCORE_FILE_HEADER_SIZE
w3d_highscores_file_footer:
    db "W3HE"

    macro W3D_DEFAULT_SCORE text,length
        db text,0
        ds W3D_HIGHSCORE_NAME_MAX-length
        dw 10000,0
        dw 1
        dw 0
    endmacro

w3d_highscores_defaults:
    W3D_DEFAULT_SCORE "id software-'92",15
    W3D_DEFAULT_SCORE "Adrian Carmack",14
    W3D_DEFAULT_SCORE "John Carmack",12
    W3D_DEFAULT_SCORE "Kevin Cloud",11
    W3D_DEFAULT_SCORE "Tom Hall",8
    W3D_DEFAULT_SCORE "John Romero",11
    W3D_DEFAULT_SCORE "Jay Wilbur",10
