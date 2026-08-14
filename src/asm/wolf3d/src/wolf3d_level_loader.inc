; =============================================================================
; W3L1 runtime level package loader.
;
; Package generation and structural validation live in
; build_level_packages.py / formats/level_package.py. The eZ80 retains one
; package in RAM and publishes its section pointers through the mutable level
; bindings used by gameplay.
; =============================================================================

W3D_LEVEL_PACKAGE_MAX:          equ 24576
W3L_MAGIC:                      equ 0
W3L_VERSION_MAJOR:              equ 4
W3L_VERSION_MINOR:              equ 5
W3L_LEVEL:                      equ 6
W3L_DIFFICULTY:                 equ 7
W3L_DOOR_COUNT:                 equ 8
W3L_ACTOR_COUNT:                equ 9
W3L_STATIC_COUNT:               equ 10
W3L_RANDOM_INDEX:               equ 12
W3L_TOTAL_SIZE:                 equ 14
W3L_PLAYER_POSE:                equ 16
W3L_DOORS_OFFSET:               equ 26
W3L_STATICS_OFFSET:             equ 28
W3L_ACTORS_OFFSET:              equ 30
W3L_BLOCKING_OFFSET:            equ 32
W3L_AREAS_OFFSET:               equ 34
W3L_PATHS_OFFSET:               equ 36
W3L_TILEMAP_OFFSET:             equ 38
W3L_HEADER_SIZE:                equ 64

W3D_LEVEL_LOAD_OK:              equ 0
W3D_LEVEL_LOAD_FILE_ERROR:      equ 1
W3D_LEVEL_LOAD_MAGIC_ERROR:     equ 2
W3D_LEVEL_LOAD_VERSION_ERROR:   equ 3
W3D_LEVEL_LOAD_ID_ERROR:        equ 4
W3D_LEVEL_LOAD_COUNT_ERROR:     equ 5
W3D_LEVEL_LOAD_BOUNDS_ERROR:    equ 6

; HL is the canonical cursor. Reject any section offset that does not exactly
; match it, restoring HL when equal. This forbids gaps, overlaps, reordering,
; and one-past-end bindings before any runtime pointer is published.
    MACRO VALIDATE_W3L_OFFSET field
        ld de,0
        ld a,(w3d_level_package+field+0)
        ld e,a
        ld a,(w3d_level_package+field+1)
        ld d,a
        or a
        sbc hl,de
        jp nz,w3d_level_load_bounds_error
        add hl,de
    ENDMACRO

; Publish base+uint16 offset only after the complete canonical layout passed.
    MACRO PUBLISH_W3L_POINTER field,target
        ld hl,0
        ld a,(w3d_level_package+field+0)
        ld l,a
        ld a,(w3d_level_package+field+1)
        ld h,a
        ld de,w3d_level_package
        add hl,de
        ld (target),hl
    ENDMACRO

; A=level 0..9, B=difficulty 0..3. Returns A=0/Z on success; otherwise a
; W3D_LEVEL_LOAD_* error with NZ. A successful call also patches the matching
; per-level image-container filenames.
w3d_load_level_package:
    ld (w3d_level_requested_index),a
    ld a,b
    ld (w3d_level_requested_difficulty),a
    cp 4
    jp nc,@id_error
    ld a,(w3d_level_requested_index)
    cp 10
    jp nc,@id_error
    call w3d_level_select_state_filename
    call w3d_level_patch_asset_filenames

; Clear the whole receive arena first: a truncated load can never inherit a
; valid header or section tail from the previous level.
    xor a
    ld hl,w3d_level_package
    ld (hl),a
    ld de,w3d_level_package+1
    ld bc,W3D_LEVEL_PACKAGE_MAX-1
    ldir
    ld hl,(w3d_level_selected_filename)
    ld de,w3d_level_package
    ld bc,W3D_LEVEL_PACKAGE_MAX
    MOSCALL mos_load
    or a
    jp nz,@file_error

    ld hl,w3d_level_package
    ld de,@magic
    ld b,4
@magic_loop:
    ld a,(de)
    cp (hl)
    jp nz,@magic_error
    inc de
    inc hl
    djnz @magic_loop
    ld a,(w3d_level_package+W3L_VERSION_MAJOR)
    cp 1
    jp nz,@version_error
    ld a,(w3d_level_package+W3L_VERSION_MINOR)
    or a
    jp nz,@version_error
    ld a,(w3d_level_requested_index)
    ld b,a
    ld a,(w3d_level_package+W3L_LEVEL)
    cp b
    jp nz,@id_error
    ld a,(w3d_level_requested_difficulty)
    ld b,a
    ld a,(w3d_level_package+W3L_DIFFICULTY)
    cp b
    jp nz,@id_error

    ld a,(w3d_level_package+W3L_DOOR_COUNT)
    cp W3D_MAX_DOORS+1
    jp nc,@count_error
    ld a,(w3d_level_package+W3L_ACTOR_COUNT)
    cp W3D_MAX_ACTORS
    jp nc,@count_error
    ld hl,0
    ld a,(w3d_level_package+W3L_STATIC_COUNT+0)
    ld l,a
    ld a,(w3d_level_package+W3L_STATIC_COUNT+1)
    ld h,a
    ld de,W3D_MAX_STATICS+1
    or a
    sbc hl,de
    jp nc,@count_error

; Reserved bytes are part of the canonical v1.0 contract. Reject packages
; whose producer tries to smuggle future fields into a version we understand.
    ld a,(w3d_level_package+13)
    or a
    jp nz,w3d_level_load_bounds_error
    ld hl,w3d_level_package+40
    ld b,W3L_HEADER_SIZE-40
@reserved_loop:
    ld a,(hl)
    or a
    jp nz,w3d_level_load_bounds_error
    inc hl
    djnz @reserved_loop

    ld hl,0
    ld a,(w3d_level_package+W3L_TOTAL_SIZE+0)
    ld l,a
    ld a,(w3d_level_package+W3L_TOTAL_SIZE+1)
    ld h,a
    ld de,W3L_HEADER_SIZE
    or a
    sbc hl,de
    jp c,w3d_level_load_bounds_error
    add hl,de
    ld de,W3D_LEVEL_PACKAGE_MAX+1
    or a
    sbc hl,de
    jp nc,w3d_level_load_bounds_error

; Validate the exact section layout and computed package end. Keep the cursor
; in HL; all arithmetic is bounded below 24 KiB.
    ld hl,W3L_HEADER_SIZE
    VALIDATE_W3L_OFFSET W3L_DOORS_OFFSET
    ld de,0
    ld a,(w3d_level_package+W3L_DOOR_COUNT)
    ld d,a
    ld e,W3D_DOOR_SIZE
    mlt de
    add hl,de

    VALIDATE_W3L_OFFSET W3L_STATICS_OFFSET
    ld de,0
    ld a,(w3d_level_package+W3L_STATIC_COUNT+0)
    ld e,a
    ld a,(w3d_level_package+W3L_STATIC_COUNT+1)
    ld d,a
    add hl,de
    add hl,de
    add hl,de
    add hl,de
    add hl,de
    add hl,de

    VALIDATE_W3L_OFFSET W3L_ACTORS_OFFSET
    ld de,0
    ld a,(w3d_level_package+W3L_ACTOR_COUNT)
    ld d,a
    ld e,W3D_ACTOR_SIZE
    mlt de
    add hl,de

    VALIDATE_W3L_OFFSET W3L_BLOCKING_OFFSET
    ld de,W3D_MAP_BYTES/8
    add hl,de
    VALIDATE_W3L_OFFSET W3L_AREAS_OFFSET
    ld de,W3D_MAP_BYTES
    add hl,de
    VALIDATE_W3L_OFFSET W3L_PATHS_OFFSET
    ld de,W3D_MAP_BYTES
    add hl,de
    VALIDATE_W3L_OFFSET W3L_TILEMAP_OFFSET
    ld de,W3D_MAP_BYTES
    add hl,de

; MOS LOAD reports success for any file up to the supplied maximum rather than
; returning its exact byte count. A nonzero footer at the canonical end makes
; a truncated package fail after the receive arena was cleared to zero.
    ld de,w3d_level_package
    add hl,de
    ld de,@footer
    ld b,4
@footer_loop:
    ld a,(de)
    cp (hl)
    jp nz,w3d_level_load_bounds_error
    inc de
    inc hl
    djnz @footer_loop

; Return the canonical cursor to a package-relative total-size value.
    ld de,w3d_level_package
    or a
    sbc hl,de
    ld de,0
    ld a,(w3d_level_package+W3L_TOTAL_SIZE+0)
    ld e,a
    ld a,(w3d_level_package+W3L_TOTAL_SIZE+1)
    ld d,a
    or a
    sbc hl,de
    jp nz,w3d_level_load_bounds_error

; Publish counts and pointers only after every structural check succeeds.
    ld a,(w3d_level_package+W3L_DOOR_COUNT)
    ld (w3d_level_door_count),a
    ld a,(w3d_level_package+W3L_ACTOR_COUNT)
    ld (w3d_level_actor_count),a
; This binding is deliberately uint16. A native-ADL `ld (nn),hl` stores HLU
; as a third byte and would overwrite the adjacent actor count.
    ld a,(w3d_level_package+W3L_STATIC_COUNT+0)
    ld (w3d_level_static_count+0),a
    ld a,(w3d_level_package+W3L_STATIC_COUNT+1)
    ld (w3d_level_static_count+1),a
    ld a,(w3d_level_package+W3L_RANDOM_INDEX)
    ld (w3d_level_random_index),a
    ld hl,w3d_level_package+W3L_PLAYER_POSE
    ld (w3d_level_player_seed_ptr),hl
    PUBLISH_W3L_POINTER W3L_DOORS_OFFSET,w3d_level_door_seed_ptr
    PUBLISH_W3L_POINTER W3L_STATICS_OFFSET,w3d_level_static_seed_ptr
    PUBLISH_W3L_POINTER W3L_ACTORS_OFFSET,w3d_level_actor_seed_ptr
    PUBLISH_W3L_POINTER W3L_BLOCKING_OFFSET,w3d_level_blocking_ptr
    PUBLISH_W3L_POINTER W3L_AREAS_OFFSET,w3d_level_area_ptr
    PUBLISH_W3L_POINTER W3L_PATHS_OFFSET,w3d_level_path_ptr
    PUBLISH_W3L_POINTER W3L_TILEMAP_OFFSET,w3d_level_tilemap_ptr
    xor a
    ret

@file_error:
    ld a,W3D_LEVEL_LOAD_FILE_ERROR
    or a
    ret
@magic_error:
    ld a,W3D_LEVEL_LOAD_MAGIC_ERROR
    or a
    ret
@version_error:
    ld a,W3D_LEVEL_LOAD_VERSION_ERROR
    or a
    ret
@id_error:
    ld a,W3D_LEVEL_LOAD_ID_ERROR
    or a
    ret
@count_error:
    ld a,W3D_LEVEL_LOAD_COUNT_ERROR
    or a
    ret
@magic:
    db "W3L1"
@footer:
    db "E3L1"

w3d_level_load_bounds_error:
    ld a,W3D_LEVEL_LOAD_BOUNDS_ERROR
    or a
    ret

w3d_level_select_state_filename:
    ld a,(w3d_level_requested_difficulty)
    ld b,a
    add a,a
    add a,b
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_level_state_filename_table
    add hl,de
    ld hl,(hl)
    ld (w3d_level_selected_filename),hl
    jp w3d_level_patch_index_in_hl

w3d_level_patch_asset_filenames:
    ld hl,w3d_level_tiles_filename
    call w3d_level_patch_index_in_hl
    ld hl,w3d_level_sprites_filename
    ; fall through
w3d_level_patch_index_in_hl:
    push hl
    ld de,6
    add hl,de
    ld a,(w3d_level_requested_index)
    ld b,'0'
@tens:
    cp 10
    jr c,@digits
    sub 10
    inc b
    jr @tens
@digits:
    ld (hl),b
    inc hl
    add a,'0'
    ld (hl),a
    pop hl
    ret

; Route and load one completed Episode 1 floor. The caller has already frozen
; simulation and established W3D_ASYNC_OWNER_NONE. Asset transfer remains
; synchronous; the next render is acquired only after every package pointer,
; bitmap, tilemap byte, and mutable-world seed is ready.
;
; Carry clear: the new level's reset/render is in flight.
; Carry set:   state or AGNB loading failed; no partial world was submitted.
w3d_transition_to_next_level:
; Victory is a terminal gameplay result, never a load target. Also classify a
; legacy/forced normal completion on zero-based floor 8 as victory so no call
; path can accidentally advance the boss floor into secret floor 9.
    call w3d_level_completion_is_victory
    jr nz,@ordinary_transition
    ld a,W3D_LEVEL_COMPLETION_VICTORY
    ld (w3d_level_completion),a
    scf
    ret

@ordinary_transition:
    ld hl,level_transition_msg
    call printString
    call printNewLine

    ld a,(w3d_level_completion)
    cp W3D_LEVEL_COMPLETION_SECRET
    jr z,@secret_floor
    ld a,(w3d_level_requested_index)
    cp 9
    jr z,@return_from_secret
    inc a
    jr @target_ready
@secret_floor:
    ld a,9
    jr @target_ready
@return_from_secret:
; Original shareware ElevatorBackTo[0] returns the secret floor to E1L2.
    ld a,1
@target_ready:
    ld (w3d_level_transition_target),a
    ld a,(w3d_game_difficulty)
    ld b,a
    ld a,(w3d_level_transition_target)
    call w3d_load_level_package
    jr nz,@package_failed

    ld de,w3d_level_tiles_filename
    ld hl,printImageDot
    call agnb_load_images_with_callback
    jr nz,@asset_failed
    ld de,w3d_level_sprites_filename
    ld hl,printImageDot
    call agnb_load_images_with_callback
    jr nz,@asset_failed

    call w3d_replace_level_tilemap_buffer
    call w3d_seed_level_transition_state
; Loading may take seconds. Re-prime the fixed-step clock so disk/VDU transfer
; time never appears as a simulation backlog on the new floor.
    call w3d_initialize_control_clock
    call w3d_death_prepare_next_render
    call w3d_submit_level_reset
    ret

@package_failed:
    call w3d_set_level_load_error
    scf
    ret

@asset_failed:
    ld hl,assets_error_msg
    ld (w3d_exit_message_ptr),hl
    scf
    ret

; Z means the current completion belongs to Episode 1 victory. The explicit
; result is authoritative; normal completion on E1L9 is accepted defensively
; for regression injection and older callers. Every other completion is NZ.
w3d_level_completion_is_victory:
    ld a,(w3d_level_completion)
    cp W3D_LEVEL_COMPLETION_VICTORY
    ret z
    cp W3D_LEVEL_COMPLETION_NORMAL
    ret nz
    ld a,(w3d_level_requested_index)
    cp 8
    ret

; Production transition wrapper. Keep this out of wolf3d_motion.inc so its
; standalone gameplay regressions remain independent of the death subsystem.
; Game-persistent inventory is already live; only world/per-level and transient
; combat state are rebuilt before the new score checkpoint and full replay.
w3d_seed_level_transition_state:
    call w3d_seed_level_world_state
    call w3d_initialize_player_combat
    call w3d_death_checkpoint_level_score
    jp w3d_mark_full_level_dirty

; Replace, never append, the renderer's 4096-byte tilemap buffer. Stock
; BUFFERED_WRITE intentionally adds a new stream to an existing buffer ID,
; while Wolf3D GetTile reads stream zero. Without the clear, a floor transition
; binds the destination player pose to the previous floor's map: E1L2's real
; spawn (16,61) is solid wall in E1L1, producing the observed gray enclosure.
; The caller has established that no asynchronous render owner is active, so
; removing the old map before the synchronous replacement is safe.
w3d_replace_level_tilemap_buffer:
    ld hl,W3D_FIXTURE_TILEMAP_BUFFER_ID
    call vdu_clear_buffer
    ld hl,W3D_FIXTURE_TILEMAP_BUFFER_ID
    ld bc,W3D_MAP_BYTES
    ld de,(w3d_level_tilemap_ptr)
    jp vdu_load_buffer

w3d_level_state_filename_table:
    dl w3d_level_state_baby_filename
    dl w3d_level_state_easy_filename
    dl w3d_level_state_medium_filename
    dl w3d_level_state_hard_filename
w3d_level_state_baby_filename:   db "level_00/state_baby.w3l",0
w3d_level_state_easy_filename:   db "level_00/state_easy.w3l",0
w3d_level_state_medium_filename: db "level_00/state_medium.w3l",0
w3d_level_state_hard_filename:   db "level_00/state_hard.w3l",0
w3d_level_tiles_filename:        db "level_00/tiles.agnb",0
w3d_level_sprites_filename:      db "level_00/sprites.agnb",0

w3d_level_requested_index:       db 0
w3d_level_requested_difficulty:  db 2
w3d_level_transition_target:     db 0
w3d_level_selected_filename:     dl w3d_level_state_medium_filename
w3d_level_package:
    ds W3D_LEVEL_PACKAGE_MAX
