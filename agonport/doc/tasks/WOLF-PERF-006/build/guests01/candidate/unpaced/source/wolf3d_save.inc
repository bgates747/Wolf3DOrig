; =============================================================================
; Versioned, transactional Wolf3DOrig save-game snapshot core.
;
; The original serializes every authoritative simulation object.  This Agon
; image does the same while deliberately omitting state which is derived here:
; actorat, the dense static-collision lookup, area reachability, dirty flags,
; asynchronous owners and renderer mirrors are rebuilt after publication.
;
; Decode never writes live state until the complete image has passed its
; exact-layout, Fletcher-16 and semantic validation.  The ten-slot menu and
; MOS file wrapper are kept outside this core so direct eZ80 tests can exercise
; the cold persistence boundary without a VDP or keyboard.
; =============================================================================

W3D_SAVE_VERSION_MAJOR:       equ 1
W3D_SAVE_VERSION_MINOR:       equ 0
W3D_SAVE_LAYOUT_ID:           equ 1
W3D_SAVE_HEADER_SIZE:         equ 64
W3D_SAVE_NAME_SIZE:           equ 32
W3D_SAVE_SCALAR_SIZE:         equ 64
W3D_SAVE_RATIO_SIZE:          equ W3D_LEVEL_RATIO_SIZE*W3D_LEVEL_RATIO_COUNT
W3D_SAVE_TILEMAP_SIZE:        equ W3D_MAP_BYTES
W3D_SAVE_AREA_SIZE:           equ W3D_MAP_BYTES
W3D_SAVE_ACTORS_SIZE:         equ W3D_MAX_ACTORS*W3D_ACTOR_SIZE
W3D_SAVE_DOORS_SIZE:          equ W3D_MAX_DOORS*W3D_DOOR_SIZE
W3D_SAVE_DOOR_TIMERS_SIZE:    equ W3D_MAX_DOORS*2
W3D_SAVE_STATICS_SIZE:        equ W3D_MAX_STATICS*W3D_STATIC_SIZE
W3D_SAVE_PUSHWALL_SIZE:       equ W3D_PUSHWALL_PAYLOAD_SIZE+6

W3D_SAVE_PAYLOAD_SCALAR:      equ 0
W3D_SAVE_PAYLOAD_RATIOS:      equ W3D_SAVE_PAYLOAD_SCALAR+W3D_SAVE_SCALAR_SIZE
W3D_SAVE_PAYLOAD_TILEMAP:     equ W3D_SAVE_PAYLOAD_RATIOS+W3D_SAVE_RATIO_SIZE
W3D_SAVE_PAYLOAD_AREA:        equ W3D_SAVE_PAYLOAD_TILEMAP+W3D_SAVE_TILEMAP_SIZE
W3D_SAVE_PAYLOAD_ACTORS:      equ W3D_SAVE_PAYLOAD_AREA+W3D_SAVE_AREA_SIZE
W3D_SAVE_PAYLOAD_DOORS:       equ W3D_SAVE_PAYLOAD_ACTORS+W3D_SAVE_ACTORS_SIZE
W3D_SAVE_PAYLOAD_DOOR_TIMERS: equ W3D_SAVE_PAYLOAD_DOORS+W3D_SAVE_DOORS_SIZE
W3D_SAVE_PAYLOAD_STATICS:     equ W3D_SAVE_PAYLOAD_DOOR_TIMERS+W3D_SAVE_DOOR_TIMERS_SIZE
W3D_SAVE_PAYLOAD_PUSHWALL:    equ W3D_SAVE_PAYLOAD_STATICS+W3D_SAVE_STATICS_SIZE
W3D_SAVE_PAYLOAD_SIZE:        equ W3D_SAVE_PAYLOAD_PUSHWALL+W3D_SAVE_PUSHWALL_SIZE
W3D_SAVE_FOOTER_OFFSET:       equ W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_SIZE
W3D_SAVE_FILE_SIZE:           equ W3D_SAVE_FOOTER_OFFSET+4

; Header offsets.
W3D_SAVE_H_LEVEL:             equ 18
W3D_SAVE_H_DIFFICULTY:        equ 19
W3D_SAVE_H_CHECKSUM_1:        equ 28
W3D_SAVE_H_CHECKSUM_2:        equ 29
W3D_SAVE_H_NAME:              equ 32

; Scalar payload offsets.  Unused tail bytes are zero and reserved for a
; compatible minor-version extension.
W3D_SAVE_S_PLAYER_POSE:       equ 0       ; 10
W3D_SAVE_S_KEY_FLAGS:         equ 10
W3D_SAVE_S_HEALTH:            equ 11
W3D_SAVE_S_AMMO:              equ 12
W3D_SAVE_S_WEAPON:            equ 13
W3D_SAVE_S_BEST_WEAPON:       equ 14
W3D_SAVE_S_CHOSEN_WEAPON:     equ 15
W3D_SAVE_S_LIVES:             equ 16
W3D_SAVE_S_SCORE:             equ 17      ; 4
W3D_SAVE_S_TREASURE_COUNT:    equ 21      ; 2
W3D_SAVE_S_NEXT_EXTRA:        equ 23      ; 4
W3D_SAVE_S_LEVEL:             equ 27
W3D_SAVE_S_DIFFICULTY:        equ 28
W3D_SAVE_S_RANDOM_INDEX:      equ 29
W3D_SAVE_S_ACTOR_TIC_PHASE:   equ 30
W3D_SAVE_S_LEVEL_SUBTICKS:    equ 31
W3D_SAVE_S_LEVEL_SECONDS:     equ 32
W3D_SAVE_S_LEVEL_MINUTES:     equ 33
W3D_SAVE_S_KILL_COUNT:        equ 34      ; 2
W3D_SAVE_S_STATIC_COUNT:      equ 36      ; 2
W3D_SAVE_S_ACTOR_COUNT:       equ 38
W3D_SAVE_S_ACTOR_FREE_HEAD:   equ 39
W3D_SAVE_S_ACTOR_LIVE_HEAD:   equ 40
W3D_SAVE_S_ACTOR_LIVE_TAIL:   equ 41
W3D_SAVE_S_DOOR_COUNT:        equ 42
W3D_SAVE_S_ATTACK_ACTIVE:     equ 43
W3D_SAVE_S_ATTACK_FRAME:      equ 44
W3D_SAVE_S_ATTACK_COUNT:      equ 45      ; 2
W3D_SAVE_S_ATTACK_TICS:       equ 47
W3D_SAVE_S_WEAPON_FRAME:      equ 48
W3D_SAVE_S_WEAPON_SHAPE:      equ 49      ; 2
W3D_SAVE_S_DOOR_PHASE:        equ 51
W3D_SAVE_S_OLD_SCORE:         equ 53      ; 4, level-entry death checkpoint
W3D_SAVE_S_FACE_FRAME:        equ 57      ; original gamestate.faceframe

W3D_SAVE_COPY_RECORD_SIZE:    equ 9
W3D_SAVE_ENCODE_COPY_COUNT:   equ 45
W3D_SAVE_DECODE_COPY_COUNT:   equ 45

; Return HL -> complete encoded image and BC=file size.  The staging buffer is
; stable until the next encode/decode operation.
w3d_save_encode:
    call w3d_save_encode_prepare_buffer
    call w3d_save_encode_copy_state
    call w3d_save_encode_finalize
    ld hl,w3d_save_file_buffer
    ld bc,W3D_SAVE_FILE_SIZE
    or a
    ret

; Cold-path stages are named separately so direct target regressions can
; localize a malformed descriptor or counter without duplicating production.
w3d_save_encode_prepare_buffer:
    call w3d_save_encode_copy_header
    call w3d_save_encode_zero_payload
    jp w3d_save_encode_finish_envelope

w3d_save_encode_copy_header:
    ld hl,w3d_save_header_template
    ld de,w3d_save_file_buffer
    ld b,W3D_SAVE_HEADER_SIZE
@byte:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    djnz @byte
    ret

w3d_save_encode_zero_payload:
    xor a
    ld hl,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE
    ld (hl),a
    ld de,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+1
    ld bc,W3D_SAVE_PAYLOAD_SIZE-1
    ldir
    ret

w3d_save_encode_finish_envelope:
    ld hl,w3d_save_footer
    ld de,w3d_save_file_buffer+W3D_SAVE_FOOTER_OFFSET
    ld bc,4
    ldir
    ld a,(w3d_level_requested_index)
    ld (w3d_save_file_buffer+W3D_SAVE_H_LEVEL),a
    ld a,(w3d_game_difficulty)
    ld (w3d_save_file_buffer+W3D_SAVE_H_DIFFICULTY),a
    ret

w3d_save_encode_copy_state:
    ld ix,w3d_save_encode_copies
    ld a,W3D_SAVE_ENCODE_COPY_COUNT
    jp w3d_save_run_copy_table

w3d_save_encode_finalize:
    ld hl,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE
    ld bc,W3D_SAVE_PAYLOAD_SIZE
    call w3d_save_fletcher16
    ld a,(w3d_save_checksum_1)
    ld (w3d_save_file_buffer+W3D_SAVE_H_CHECKSUM_1),a
    ld a,(w3d_save_checksum_2)
    ld (w3d_save_file_buffer+W3D_SAVE_H_CHECKSUM_2),a
    ret

; Validate and publish the staged image. Return carry clear/A=0 on success;
; carry set/A=one of the cold-path reason codes on failure.
w3d_save_decode:
    call w3d_save_validate_header
    ret c
    call w3d_save_validate_semantics
    ret c
    ld ix,w3d_save_decode_copies
    ld a,W3D_SAVE_DECODE_COPY_COUNT
    call w3d_save_run_copy_table
    call w3d_save_rebuild_derived_state
    xor a
    ret

; IX -> {source dl,destination dl,length dl}, A=record count.
w3d_save_run_copy_table:
    ld (w3d_save_copy_records_left),a
@next:
    ld hl,(ix+0)
    ld de,(ix+3)
    ld bc,(ix+6)
    ldir
    lea ix,ix+W3D_SAVE_COPY_RECORD_SIZE
    ld a,(w3d_save_copy_records_left)
    dec a
    ld (w3d_save_copy_records_left),a
    jr nz,@next
    ret

; HL=data, BC=length. Standard Fletcher-16 modulo-255 sums. This private copy
; keeps the snapshot core independent from high-score presentation code.
w3d_save_fletcher16:
    xor a
    ld (w3d_save_checksum_1),a
    ld (w3d_save_checksum_2),a
@byte:
    ld a,(w3d_save_checksum_1)
    add a,(hl)
    jr nc,@sum1_folded
    inc a
@sum1_folded:
    cp 0ffh
    jr nz,@sum1_ready
    xor a
@sum1_ready:
    ld (w3d_save_checksum_1),a
    ld d,a
    ld a,(w3d_save_checksum_2)
    add a,d
    jr nc,@sum2_folded
    inc a
@sum2_folded:
    cp 0ffh
    jr nz,@sum2_ready
    xor a
@sum2_ready:
    ld (w3d_save_checksum_2),a
    inc hl
    dec.s bc
    ld a,b
    or c
    jr nz,@byte
    ret

w3d_save_validate_header:
    ld hl,w3d_save_file_buffer
    ld de,w3d_save_header_template
    ld b,W3D_SAVE_H_LEVEL
@fixed_prefix:
    ld a,(de)
    cp (hl)
    jr nz,@layout
    inc hl
    inc de
    djnz @fixed_prefix
    ld hl,w3d_save_file_buffer+20
    ld de,w3d_save_header_template+20
    ld b,8
@fixed_suffix:
    ld a,(de)
    cp (hl)
    jr nz,@layout
    inc hl
    inc de
    djnz @fixed_suffix
    ld hl,w3d_save_file_buffer+30
    ld de,w3d_save_header_template+30
    ld b,2
@header_tail:
    ld a,(de)
    cp (hl)
    jr nz,@layout
    inc hl
    inc de
    djnz @header_tail
    ld hl,w3d_save_file_buffer+W3D_SAVE_FOOTER_OFFSET
    ld de,w3d_save_footer
    ld b,4
@footer:
    ld a,(de)
    cp (hl)
    jr nz,@layout
    inc hl
    inc de
    djnz @footer
    ld hl,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE
    ld bc,W3D_SAVE_PAYLOAD_SIZE
    call w3d_save_fletcher16
    ld a,(w3d_save_file_buffer+W3D_SAVE_H_CHECKSUM_1)
    ld b,a
    ld a,(w3d_save_checksum_1)
    cp b
    jr nz,@checksum
    ld a,(w3d_save_file_buffer+W3D_SAVE_H_CHECKSUM_2)
    ld b,a
    ld a,(w3d_save_checksum_2)
    cp b
    jr nz,@checksum
    or a
    ret
@layout:
    ld a,1
    scf
    ret
@checksum:
    ld a,2
    scf
    ret

w3d_save_validate_semantics:
    ld a,(w3d_save_file_buffer+W3D_SAVE_H_LEVEL)
    cp 10
    jp nc,@scalar
    ld b,a
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LEVEL)
    cp b
    jp nz,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_H_DIFFICULTY)
    cp 4
    jp nc,@scalar
    ld b,a
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_DIFFICULTY)
    cp b
    jp nz,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_HEALTH)
    cp 101
    jp nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_AMMO)
    cp 100
    jp nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_WEAPON)
    cp 4
    jp nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_BEST_WEAPON)
    cp 4
    jp nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_CHOSEN_WEAPON)
    cp 4
    jp nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_KEY_FLAGS)
    and 0f0h
    jp nz,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LEVEL_SUBTICKS)
    cp W3D_LEVEL_TIME_TICKS_PER_SECOND
    jp nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LEVEL_SECONDS)
    cp 60
    jp nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LEVEL_MINUTES)
    cp 100
    jp nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ATTACK_ACTIVE)
    cp 2
    jp nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ATTACK_FRAME)
    cp W3D_PLAYER_ATTACK_FRAME_COUNT
    jp nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_WEAPON_FRAME)
    cp W3D_PLAYER_ATTACK_FRAME_COUNT+1
    jp nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_DOOR_PHASE)
    cp 3
    jp nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_FACE_FRAME)
    cp 3
    jp nc,@scalar
    ld hl,0
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_STATIC_COUNT+0)
    ld l,a
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_STATIC_COUNT+1)
    ld h,a
    ld de,W3D_MAX_STATICS+1
    or a
    sbc.s hl,de
    jp nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_COUNT)
    cp W3D_MAX_ACTORS
    jr nc,@scalar
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_DOOR_COUNT)
    cp W3D_MAX_DOORS+1
    jr nc,@scalar
    call w3d_save_validate_player_pose
    jp c,@scalar
    call w3d_save_validate_tilemap
    jp c,@tilemap
    call w3d_save_validate_area_map
    jp c,@area
    call w3d_save_validate_actor_lists
    jp c,@actors
    call w3d_save_validate_doors
    jp c,@doors
    call w3d_save_validate_statics
    jp c,@statics
    call w3d_save_validate_pushwall
    jp c,@pushwall
    or a
    ret
@scalar:
    ld a,3
    scf
    ret
@area:
    ld a,4
    scf
    ret
@actors:
    ld a,5
    scf
    ret
@doors:
    ld a,6
    scf
    ret
@statics:
    ld a,7
    scf
    ret
@pushwall:
    ld a,8
    scf
    ret
@tilemap:
    ld a,9
    scf
    ret

w3d_save_validate_player_pose:
    ld ix,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_PLAYER_POSE
    ld a,(ix+3)
    or a
    jr nz,@bad
    ld a,(ix+7)
    or a
    jr nz,@bad
    ld a,(ix+2)
    cp W3D_MAP_SIZE
    jr nc,@bad
    ld a,(ix+6)
    cp W3D_MAP_SIZE
    jr nc,@bad
    ld hl,0
    ld l,(ix+8)
    ld h,(ix+9)
    ld de,360
    or a
    sbc.s hl,de
    jr nc,@bad
    or a
    ret
@bad:
    scf
    ret

; A staged map byte is either empty/a wall (00..7f) or a door reference
; (80..bf). Door references must name one of the staged records; accepting a
; larger low-seven-bit index would let later collision/area code walk beyond
; the door table even when a deliberately forged image has a valid checksum.
w3d_save_validate_tilemap:
    ld hl,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_TILEMAP
    ld bc,W3D_SAVE_TILEMAP_SIZE
@byte:
    ld a,(hl)
    cp W3D_TILE_DOOR_MIN
    jr c,@next
    cp W3D_TILE_DOOR_MAX+1
    jr nc,@bad
    and W3D_TILE_DOOR_MASK
    ld d,a
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_DOOR_COUNT)
    cp d
    jr z,@bad
    jr c,@bad
@next:
    inc hl
    dec.s bc
    ld a,b
    or c
    jr nz,@byte
    or a
    ret
@bad:
    scf
    ret

w3d_save_validate_area_map:
    ld hl,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_AREA
    ld bc,W3D_SAVE_AREA_SIZE
@byte:
    ld a,(hl)
    cp W3D_SLOT_NONE
    jr z,@next
    cp W3D_NUM_AREAS
    jr nc,@bad
@next:
    inc hl
    dec.s bc
    ld a,b
    or c
    jr nz,@byte
    or a
    ret
@bad:
    scf
    ret

; Validate the stable live/free partition, list links and every live record.
w3d_save_validate_actor_lists:
    xor a
    ld hl,w3d_save_actor_seen
    ld (hl),a
    ld de,w3d_save_actor_seen+1
    ld bc,W3D_MAX_ACTORS-1
    ldir
    ld a,1                         ; slot zero is player-reserved
    ld (w3d_save_actor_seen),a
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_COUNT)
    ld (w3d_save_actor_steps_left),a
    ld a,W3D_SLOT_NONE
    ld (w3d_save_actor_previous),a
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_LIVE_HEAD)
@live:
    ld b,a
    ld a,(w3d_save_actor_steps_left)
    or a
    jp z,@live_done
    ld a,b
    call w3d_save_validate_actor_id_unseen
    ret c
    call w3d_save_actor_pointer_from_staged_id
    ld a,(ix+W3D_ACTOR_ACTIVE)
    cp W3D_ACTOR_ACTIVE_FREE
    jp z,@bad
    cp W3D_ACTOR_ACTIVE_ALWAYS+1
    jp nc,@bad
    ld a,(ix+W3D_ACTOR_TILEX)
    cp W3D_MAP_SIZE
    jp nc,@bad
    ld a,(ix+W3D_ACTOR_TILEY)
    cp W3D_MAP_SIZE
    jp nc,@bad
    ld a,(ix+W3D_ACTOR_AREA)
    cp W3D_NUM_AREAS
    jp nc,@bad
    ld a,(ix+W3D_ACTOR_DIR)
    cp W3D_DIR_NODIR+1
    jp nc,@bad
    ld a,(ix+W3D_ACTOR_CLASS)
    cp W3D_CLASS_GHOST+1
    jp nc,@bad
    ld hl,0
    ld l,(ix+W3D_ACTOR_STATE+0)
    ld h,(ix+W3D_ACTOR_STATE+1)
    ld de,W3D_STATE_COUNT
    or a
    sbc.s hl,de
    jp nc,@bad
    ld a,(ix+W3D_ACTOR_PREV)
    ld b,a
    ld a,(w3d_save_actor_previous)
    cp b
    jp nz,@bad
    ld a,(w3d_save_actor_current)
    ld (w3d_save_actor_previous),a
    ld a,(ix+W3D_ACTOR_NEXT)
    ld b,a
    ld a,(w3d_save_actor_steps_left)
    dec a
    ld (w3d_save_actor_steps_left),a
    ld a,b
    jp @live
@live_done:
    ld a,b
    cp W3D_SLOT_NONE
    jp nz,@bad
    ld b,a
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_COUNT)
    or a
    jr z,@empty_tail
    ld a,(w3d_save_actor_previous)
    ld b,a
@empty_tail:
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_LIVE_TAIL)
    cp b
    jp nz,@bad

    ld a,W3D_MAX_ACTORS-1
    ld b,a
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_COUNT)
    ld c,a
    ld a,b
    sub c
    ld (w3d_save_actor_steps_left),a
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_FREE_HEAD)
@free:
    ld b,a
    ld a,(w3d_save_actor_steps_left)
    or a
    jr z,@free_done
    ld a,b
    call w3d_save_validate_actor_id_unseen
    ret c
    call w3d_save_actor_pointer_from_staged_id
    ld a,(ix+W3D_ACTOR_ACTIVE)
    cp W3D_ACTOR_ACTIVE_FREE
    jp nz,@bad
    ld a,(ix+W3D_ACTOR_PREV)       ; free-list link
    ld b,a
    ld a,(w3d_save_actor_steps_left)
    dec a
    ld (w3d_save_actor_steps_left),a
    ld a,b
    jp @free
@free_done:
    ld a,b
    cp W3D_SLOT_NONE
    jp nz,@bad
    or a
    ret
@bad:
    scf
    ret

; A=id. Reject zero, ff, >=150 or a duplicate. Publish current id.
w3d_save_validate_actor_id_unseen:
    or a
    jr z,@bad
    cp W3D_MAX_ACTORS
    jr nc,@bad
    ld (w3d_save_actor_current),a
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_save_actor_seen
    add hl,de                  ; full pointer add after explicitly zeroing DEU
    ld a,(hl)
    or a
    jr nz,@bad
    inc (hl)
    or a
    ret
@bad:
    scf
    ret

w3d_save_actor_pointer_from_staged_id:
    ld a,(w3d_save_actor_current)
    ld d,a
    ld e,W3D_ACTOR_SIZE
    mlt de
    inc de
    dec.s de
    ld ix,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_ACTORS
    add ix,de                  ; full pointer add after explicitly zeroing DEU
    ret

w3d_save_validate_doors:
    ld ix,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_DOORS
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_DOOR_COUNT)
    ld (w3d_save_records_left),a
@record:
    ld a,(w3d_save_records_left)
    or a
    ret z
    ld a,(ix+W3D_DOOR_TILEX)
    cp W3D_MAP_SIZE
    jr nc,@bad
    ld a,(ix+W3D_DOOR_TILEY)
    cp W3D_MAP_SIZE
    jr nc,@bad
    ld a,(ix+W3D_DOOR_VERTICAL)
    cp 2
    jr nc,@bad
    ld a,(ix+W3D_DOOR_ACTION)
    cp W3D_DOOR_ACTION_CLOSING+1
    jr nc,@bad
    ld a,(ix+W3D_DOOR_AREA1)
    cp W3D_NUM_AREAS
    jr nc,@bad
    ld a,(ix+W3D_DOOR_AREA2)
    cp W3D_NUM_AREAS
    jr nc,@bad
    lea ix,ix+W3D_DOOR_SIZE
    ld a,(w3d_save_records_left)
    dec a
    ld (w3d_save_records_left),a
    jr @record
@bad:
    scf
    ret

w3d_save_validate_statics:
    ld ix,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_STATICS
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_STATIC_COUNT+0)
    ld (w3d_save_records_left_16+0),a
    ld a,(w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_STATIC_COUNT+1)
    ld (w3d_save_records_left_16+1),a
@record:
    ld hl,0
    ld a,(w3d_save_records_left_16+0)
    ld l,a
    ld a,(w3d_save_records_left_16+1)
    ld h,a
    ld a,h
    or l
    ret z
    ld a,(ix+W3D_STATIC_TILEX)
    cp W3D_MAP_SIZE
    jr nc,@bad
    ld a,(ix+W3D_STATIC_TILEY)
    cp W3D_MAP_SIZE
    jr nc,@bad
    lea ix,ix+W3D_STATIC_SIZE
    ld hl,0
    ld a,(w3d_save_records_left_16+0)
    ld l,a
    ld a,(w3d_save_records_left_16+1)
    ld h,a
    dec.s hl
    ld a,l
    ld (w3d_save_records_left_16+0),a
    ld a,h
    ld (w3d_save_records_left_16+1),a
    jr @record
@bad:
    scf
    ret

w3d_save_validate_pushwall:
    ld ix,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_PUSHWALL
    ld a,(ix+W3D_PUSHWALL_RENDER_STATUS)
    cp W3D_PUSHWALL_STATUS_COMPLETE+1
    jr nc,@bad
    ld a,(ix+W3D_PUSHWALL_RENDER_ORIGIN_X)
    cp W3D_MAP_SIZE
    jr nc,@bad
    ld a,(ix+W3D_PUSHWALL_RENDER_ORIGIN_Y)
    cp W3D_MAP_SIZE
    jr nc,@bad
    ld a,(ix+W3D_PUSHWALL_RENDER_CURRENT_X)
    cp W3D_MAP_SIZE
    jr nc,@bad
    ld a,(ix+W3D_PUSHWALL_RENDER_CURRENT_Y)
    cp W3D_MAP_SIZE
    jr nc,@bad
    ld a,(ix+W3D_PUSHWALL_RENDER_DIR)
    cp 4
    jr nc,@bad
    ld a,(ix+W3D_PUSHWALL_RENDER_POS)
    cp 64
    jr nc,@bad
    ld a,(ix+W3D_PUSHWALL_RENDER_SIZE)
    cp W3D_PUSHWALL_HISTORY_MAX+1
    jr nc,@bad
    ld (w3d_save_records_left),a
    lea ix,ix+W3D_PUSHWALL_RENDER_SIZE+1
@history:
    ld a,(w3d_save_records_left)
    or a
    ret z
    ld a,(ix+0)
    cp W3D_MAP_SIZE
    jr nc,@bad
    ld a,(ix+1)
    cp W3D_MAP_SIZE
    jr nc,@bad
    ld a,(ix+2)
    cp W3D_MAP_SIZE
    jr nc,@bad
    ld a,(ix+3)
    cp W3D_MAP_SIZE
    jr nc,@bad
    lea ix,ix+W3D_PUSHWALL_HISTORY_ENTRY_SIZE
    ld a,(w3d_save_records_left)
    dec a
    ld (w3d_save_records_left),a
    jr @history
@bad:
    scf
    ret

; Rebuild everything intentionally excluded from the durable payload.
w3d_save_rebuild_derived_state:
    ld hl,w3d_runtime_tilemap
    ld (w3d_level_tilemap_ptr),hl
    ld (w3d_map_ptr),hl
    ld hl,w3d_runtime_area_map
    ld (w3d_level_area_ptr),hl
    ld (w3d_area_map_ptr),hl
    ld hl,w3d_doors
    ld (w3d_doors_ptr),hl

    xor a
    ld hl,w3d_actorat
    ld (hl),a
    ld de,w3d_actorat+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld a,(w3d_actor_live_head)
@claim:
    cp W3D_SLOT_NONE
    jr z,@actors_ready
    ld (w3d_save_actor_current),a
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_NONMARK|W3D_ACTOR_FLAG_NEVERMARK
    jr nz,@next_actor
    ld a,(w3d_save_actor_current)
    call w3d_actorat_claim
@next_actor:
    ld a,(ix+W3D_ACTOR_NEXT)
    jr @claim
@actors_ready:
    call w3d_build_static_collision_lookup
    call w3d_initialize_area_state
    call w3d_initialize_victory_state
    xor a
    ld (w3d_controls),a
    ld (w3d_use_was_down),a
    ld (w3d_player_thrustspeed+0),a
    ld (w3d_player_thrustspeed+1),a
    ld (w3d_player_dead),a
    ld (w3d_level_completion),a
    ld (w3d_player_attack_was_down),a
    ld (w3d_player_attack_repeat_down),a
    ld (w3d_player_attack_sound),a
    ld (w3d_player_attack_sound_count+0),a
    ld (w3d_player_attack_sound_count+1),a
    ld (w3d_player_last_attack_hit),a
    ld (w3d_player_last_attack_damage),a
    ld (w3d_player_last_damage_result),a
    ld (w3d_player_combat_fault),a
    ld (w3d_actor_tics_prepared),a
    ld (w3d_player_made_noise),a
    ld (w3d_simulation_accumulator+0),a
    ld (w3d_simulation_accumulator+1),a
    ld (w3d_simulation_accumulator+2),a
    ld a,W3D_SLOT_NONE
    ld (w3d_player_last_attacker),a
    ld (w3d_player_killer),a
    ld (w3d_player_last_attack_target),a
    call w3d_mark_full_level_dirty
    ld a,W3D_HUD_DIRTY_HEALTH|W3D_HUD_DIRTY_AMMO|W3D_HUD_DIRTY_KEYS|W3D_HUD_DIRTY_WEAPON|W3D_HUD_DIRTY_SCORE|W3D_HUD_DIRTY_LIVES
    ld (w3d_hud_dirty),a
    ld a,1
    ld (w3d_player_weapon_shape_dirty),a
    or a
    ret

; Descriptor tables ---------------------------------------------------------

w3d_save_encode_copies:
    dl w3d_player_pose,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_PLAYER_POSE,10
    dl w3d_player_key_flags,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_KEY_FLAGS,1
    dl w3d_player_health,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_HEALTH,1
    dl w3d_player_ammo,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_AMMO,1
    dl w3d_player_weapon,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_WEAPON,1
    dl w3d_player_best_weapon,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_BEST_WEAPON,1
    dl w3d_player_chosen_weapon,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_CHOSEN_WEAPON,1
    dl w3d_player_lives,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LIVES,1
    dl w3d_player_score,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_SCORE,4
    dl w3d_player_treasure_count,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_TREASURE_COUNT,2
    dl w3d_player_next_extra,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_NEXT_EXTRA,4
    dl w3d_level_requested_index,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LEVEL,1
    dl w3d_game_difficulty,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_DIFFICULTY,1
    dl w3d_random_index,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_RANDOM_INDEX,1
    dl w3d_actor_tic_phase,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_TIC_PHASE,1
    dl w3d_intermission_level_subticks,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LEVEL_SUBTICKS,1
    dl w3d_intermission_level_seconds,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LEVEL_SECONDS,1
    dl w3d_intermission_level_minutes,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LEVEL_MINUTES,1
    dl w3d_player_kill_count,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_KILL_COUNT,2
    dl w3d_static_count,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_STATIC_COUNT,2
    dl w3d_actor_count,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_COUNT,1
    dl w3d_actor_free_head,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_FREE_HEAD,1
    dl w3d_actor_live_head,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_LIVE_HEAD,1
    dl w3d_actor_live_tail,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_LIVE_TAIL,1
    dl w3d_level_door_count,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_DOOR_COUNT,1
    dl w3d_player_attack_active,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ATTACK_ACTIVE,1
    dl w3d_player_attack_frame,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ATTACK_FRAME,1
    dl w3d_player_attack_count,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ATTACK_COUNT,2
    dl w3d_player_attack_record_tics,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ATTACK_TICS,1
    dl w3d_player_weapon_frame,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_WEAPON_FRAME,1
    dl w3d_player_weapon_shape,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_WEAPON_SHAPE,2
    dl w3d_door_motion_phase,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_DOOR_PHASE,1
    dl w3d_death_oldscore,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_OLD_SCORE,4
    dl w3d_player_face_frame,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_FACE_FRAME,1
    dl w3d_level_ratios,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_RATIOS,W3D_SAVE_RATIO_SIZE
    dl w3d_runtime_tilemap,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_TILEMAP,W3D_SAVE_TILEMAP_SIZE
    dl w3d_runtime_area_map,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_AREA,W3D_SAVE_AREA_SIZE
    dl w3d_actors,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_ACTORS,W3D_SAVE_ACTORS_SIZE
    dl w3d_doors,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_DOORS,W3D_SAVE_DOORS_SIZE
    dl w3d_door_timers,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_DOOR_TIMERS,W3D_SAVE_DOOR_TIMERS_SIZE
    dl w3d_statics,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_STATICS,W3D_SAVE_STATICS_SIZE
    dl w3d_pushwall_payload,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_PUSHWALL,W3D_PUSHWALL_PAYLOAD_SIZE
    dl w3d_pushwall_state,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_PUSHWALL+W3D_PUSHWALL_PAYLOAD_SIZE,2
    dl w3d_player_secret_count,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_PUSHWALL+W3D_PUSHWALL_PAYLOAD_SIZE+2,2
    dl w3d_player_secret_total,w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_PUSHWALL+W3D_PUSHWALL_PAYLOAD_SIZE+4,2
w3d_save_encode_copies_end:

; The assembler has no metaprogramming primitive for swapping table columns;
; spell out the decode table so its direction remains reviewable.
w3d_save_decode_copies:
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_PLAYER_POSE,w3d_player_pose,10
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_KEY_FLAGS,w3d_player_key_flags,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_HEALTH,w3d_player_health,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_AMMO,w3d_player_ammo,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_WEAPON,w3d_player_weapon,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_BEST_WEAPON,w3d_player_best_weapon,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_CHOSEN_WEAPON,w3d_player_chosen_weapon,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LIVES,w3d_player_lives,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_SCORE,w3d_player_score,4
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_TREASURE_COUNT,w3d_player_treasure_count,2
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_NEXT_EXTRA,w3d_player_next_extra,4
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LEVEL,w3d_level_requested_index,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_DIFFICULTY,w3d_game_difficulty,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_RANDOM_INDEX,w3d_random_index,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_TIC_PHASE,w3d_actor_tic_phase,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LEVEL_SUBTICKS,w3d_intermission_level_subticks,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LEVEL_SECONDS,w3d_intermission_level_seconds,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_LEVEL_MINUTES,w3d_intermission_level_minutes,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_KILL_COUNT,w3d_player_kill_count,2
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_STATIC_COUNT,w3d_static_count,2
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_COUNT,w3d_actor_count,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_FREE_HEAD,w3d_actor_free_head,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_LIVE_HEAD,w3d_actor_live_head,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ACTOR_LIVE_TAIL,w3d_actor_live_tail,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_DOOR_COUNT,w3d_level_door_count,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ATTACK_ACTIVE,w3d_player_attack_active,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ATTACK_FRAME,w3d_player_attack_frame,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ATTACK_COUNT,w3d_player_attack_count,2
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_ATTACK_TICS,w3d_player_attack_record_tics,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_WEAPON_FRAME,w3d_player_weapon_frame,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_WEAPON_SHAPE,w3d_player_weapon_shape,2
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_DOOR_PHASE,w3d_door_motion_phase,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_OLD_SCORE,w3d_death_oldscore,4
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_S_FACE_FRAME,w3d_player_face_frame,1
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_RATIOS,w3d_level_ratios,W3D_SAVE_RATIO_SIZE
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_TILEMAP,w3d_runtime_tilemap,W3D_SAVE_TILEMAP_SIZE
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_AREA,w3d_runtime_area_map,W3D_SAVE_AREA_SIZE
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_ACTORS,w3d_actors,W3D_SAVE_ACTORS_SIZE
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_DOORS,w3d_doors,W3D_SAVE_DOORS_SIZE
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_DOOR_TIMERS,w3d_door_timers,W3D_SAVE_DOOR_TIMERS_SIZE
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_STATICS,w3d_statics,W3D_SAVE_STATICS_SIZE
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_PUSHWALL,w3d_pushwall_payload,W3D_PUSHWALL_PAYLOAD_SIZE
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_PUSHWALL+W3D_PUSHWALL_PAYLOAD_SIZE,w3d_pushwall_state,2
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_PUSHWALL+W3D_PUSHWALL_PAYLOAD_SIZE+2,w3d_player_secret_count,2
    dl w3d_save_file_buffer+W3D_SAVE_HEADER_SIZE+W3D_SAVE_PAYLOAD_PUSHWALL+W3D_PUSHWALL_PAYLOAD_SIZE+4,w3d_player_secret_total,2
w3d_save_decode_copies_end:

; Storage -------------------------------------------------------------------

w3d_save_header_template:
    db "W3SV"
    db W3D_SAVE_VERSION_MAJOR,W3D_SAVE_VERSION_MINOR
    dw W3D_SAVE_HEADER_SIZE
    dw W3D_SAVE_FILE_SIZE,0
    dw W3D_SAVE_PAYLOAD_SIZE,0
    dw W3D_SAVE_LAYOUT_ID
    db 0,0                         ; level/difficulty patched by encoder
    db W3D_ACTOR_SIZE,W3D_DOOR_SIZE,W3D_STATIC_SIZE,W3D_MAX_ACTORS,W3D_MAX_DOORS
    dw W3D_MAX_STATICS
    db 0
    dw 0                           ; Fletcher-16 patched by encoder
    db 05ah,0a5h
    ds W3D_SAVE_NAME_SIZE           ; original 32-byte slot description
w3d_save_footer:
    db "W3SE"

w3d_save_copy_records_left:
    db 0
w3d_save_checksum_1:
    db 0
w3d_save_checksum_2:
    db 0
w3d_save_records_left:
    db 0
w3d_save_records_left_16:
    dw 0
w3d_save_actor_steps_left:
    db 0
w3d_save_actor_previous:
    db W3D_SLOT_NONE
w3d_save_actor_current:
    db W3D_SLOT_NONE
w3d_save_actor_seen:
    ds W3D_MAX_ACTORS
w3d_save_file_buffer:
    ds W3D_SAVE_FILE_SIZE+1
