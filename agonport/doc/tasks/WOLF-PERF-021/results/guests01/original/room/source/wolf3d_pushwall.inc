; =============================================================================
; Original Episode 1 pushwall / secret simulation.
;
; The immutable W3L path map preserves plane-1 PUSHABLETILE as 0xfd.  The
; mutable runtime tilemap and area map are rebuilt from their retained seeds
; on each level/attempt entry, so completed secrets cannot poison a respawn.
;
; Only one wall moves at once, matching WL_ACT1.C.  `state` counts original
; 70-Hz tics from one; the shared actor 2,2,3 cadence advances it exactly at
; the client's 30-Hz fixed step.  The eight-byte renderer snapshot is
; sufficient even when render lag skips a boundary: status, origin/current
; cells, direction, fractional position, and texture reconstruct the exact
; authoritative result.
; =============================================================================

W3D_PUSHWALL_STATUS_RESET:       equ 0
W3D_PUSHWALL_STATUS_ACTIVE:      equ 1
W3D_PUSHWALL_STATUS_COMPLETE:    equ 2
W3D_PUSHWALL_RENDER_SIZE:        equ 8
W3D_PUSHWALL_HISTORY_MAX:        equ 16
W3D_PUSHWALL_HISTORY_ENTRY_SIZE: equ 5
W3D_PUSHWALL_PAYLOAD_SIZE:       equ 89

W3D_PUSHWALL_RENDER_STATUS:      equ 0
W3D_PUSHWALL_RENDER_ORIGIN_X:    equ 1
W3D_PUSHWALL_RENDER_ORIGIN_Y:    equ 2
W3D_PUSHWALL_RENDER_CURRENT_X:   equ 3
W3D_PUSHWALL_RENDER_CURRENT_Y:   equ 4
W3D_PUSHWALL_RENDER_DIR:         equ 5
W3D_PUSHWALL_RENDER_POS:         equ 6
W3D_PUSHWALL_RENDER_TEXTURE:     equ 7

; Reset all mutable pushwall state and derive the original secrettotal from
; the immutable path/trigger map.  The reset renderer record is deliberately
; dirty so a complete world replay clears any prior level's private state.
w3d_initialize_pushwall_state:
    xor a
    ld hl,w3d_pushwall_payload
    ld (hl),a
    ld de,w3d_pushwall_payload+1
    ld bc,W3D_PUSHWALL_PAYLOAD_SIZE-1
    ldir
    ld (w3d_pushwall_state+0),a
    ld (w3d_pushwall_state+1),a
    ld (w3d_player_secret_count+0),a
    ld (w3d_player_secret_count+1),a
    ld (w3d_player_secret_total+0),a
    ld (w3d_player_secret_total+1),a
    ld a,1
    ld (w3d_pushwall_dirty),a

    ld hl,(w3d_level_path_ptr)
    ld bc,W3D_MAP_BYTES
@count_loop:
    ld a,(hl)
    cp W3D_PATH_PUSHWALL
    jr nz,@count_next
    ld de,(w3d_player_secret_total)
    inc.s de
    ld a,e
    ld (w3d_player_secret_total+0),a
    ld a,d
    ld (w3d_player_secret_total+1),a
@count_next:
    inc hl
    dec bc
    ld a,b
    or c
    jr nz,@count_loop
    ret

; Advance one active pushwall by this fixed quantum's exact original tic count.
w3d_simulate_pushwall:
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_STATUS)
    cp W3D_PUSHWALL_STATUS_ACTIVE
    ret nz
    call w3d_prepare_actor_frame_tics

    ld hl,0
    ld a,(w3d_pushwall_state+0)
    ld l,a
    ld a,(w3d_pushwall_state+1)
    ld h,a
    ld a,h
    rra
    ld a,l
    rra
    and 0c0h
    ld (w3d_pushwall_old_block),a

    ld de,0
    ld a,(w3d_actor_frame_tics)
    ld e,a
    add.s hl,de
    ld a,l
    ld (w3d_pushwall_state+0),a
    ld a,h
    ld (w3d_pushwall_state+1),a

; pwallpos=(pwallstate/2)&63. Keep it current even when no cell boundary was
; crossed so a slow renderer receives only the newest fractional position.
    srl h
    rr l
    ld a,l
    and 03fh
    ld (w3d_pushwall_render+W3D_PUSHWALL_RENDER_POS),a

; Compare state/128 using the two high bits of the low byte plus high byte.
    ld hl,0
    ld a,(w3d_pushwall_state+0)
    ld l,a
    ld a,(w3d_pushwall_state+1)
    ld h,a
    ld a,h
    rra
    ld a,l
    rra
    and 0c0h
    ld b,a
    ld a,(w3d_pushwall_old_block)
    cp b
    call nz,w3d_pushwall_cross_cell

    ld a,1
    ld (w3d_pushwall_dirty),a
    ld (w3d_world_dirty),a
    ret

; The current marked cell has just been vacated.  Preserve the original area
; ownership, then either stop after two cells / a newly blocked continuation,
; or reserve the next cell and mark the new moving cell with 0xc0.
w3d_pushwall_cross_cell:
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_X)
    ld b,a
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_Y)
    ld c,a
    xor a
    call w3d_map_write
    ld a,(w3d_player_area)
    call w3d_area_write

    call w3d_pushwall_advance_current

    ld hl,0
    ld a,(w3d_pushwall_state+0)
    ld l,a
    ld a,(w3d_pushwall_state+1)
    ld h,a
    ld de,256
    or a
    sbc.s hl,de
    jr nc,@complete

    call w3d_pushwall_load_next_coords
    push bc
    call w3d_pushwall_destination_clear
    pop bc
    or a
    jr z,@complete

; Reserve the next cell with the ordinary texture. The current cell keeps the
; original 0xc0 moving-wall marker for CPU sight and standalone compatibility.
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_TEXTURE)
    call w3d_map_write
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_X)
    ld b,a
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_Y)
    ld c,a
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_TEXTURE)
    or 0c0h
    call w3d_map_write
    ret

@complete:
    call w3d_pushwall_record_completion
    ld a,W3D_PUSHWALL_STATUS_COMPLETE
    ld (w3d_pushwall_render+W3D_PUSHWALL_RENDER_STATUS),a
    xor a
    ld (w3d_pushwall_state+0),a
    ld (w3d_pushwall_state+1),a
    ld (w3d_pushwall_render+W3D_PUSHWALL_RENDER_POS),a
    ret

; Append the just-completed origin/current/texture overlay. Episode 1's
; largest level contains fifteen secrets, so the sixteenth slot is deliberate
; headroom and is also the renderer wire ceiling. A completion is recorded
; exactly once because COMPLETE stops subsequent simulation calls.
w3d_pushwall_record_completion:
    ld a,(w3d_pushwall_history_count)
    cp W3D_PUSHWALL_HISTORY_MAX
    ret nc
    push af
    ld d,a
    ld e,W3D_PUSHWALL_HISTORY_ENTRY_SIZE
    mlt de
    ld hl,w3d_pushwall_history
    add hl,de
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_ORIGIN_X)
    ld (hl),a
    inc hl
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_ORIGIN_Y)
    ld (hl),a
    inc hl
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_X)
    ld (hl),a
    inc hl
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_Y)
    ld (hl),a
    inc hl
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_TEXTURE)
    ld (hl),a
    pop af
    inc a
    ld (w3d_pushwall_history_count),a
    ret

; B/C are the facing-adjacent cell and A is a cardinal W3D_DIR_* value.
; The path marker owns the Use action even when the wall has already moved.
w3d_try_pushwall:
    ld (w3d_pushwall_requested_dir),a
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_STATUS)
    cp W3D_PUSHWALL_STATUS_ACTIVE
    ret z
    call w3d_map_read
    or a
    ret z
    cp W3D_TILE_DOOR_MIN
    ret nc
    ld (w3d_pushwall_requested_texture),a

    push bc
    call w3d_pushwall_load_requested_destination
    call w3d_pushwall_destination_clear
    pop bc
    or a
    jr z,@blocked

    ld a,W3D_PUSHWALL_STATUS_ACTIVE
    ld (w3d_pushwall_render+W3D_PUSHWALL_RENDER_STATUS),a
    ld a,b
    ld (w3d_pushwall_render+W3D_PUSHWALL_RENDER_ORIGIN_X),a
    ld (w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_X),a
    ld a,c
    ld (w3d_pushwall_render+W3D_PUSHWALL_RENDER_ORIGIN_Y),a
    ld (w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_Y),a
    ld a,(w3d_pushwall_requested_dir)
    ld (w3d_pushwall_render+W3D_PUSHWALL_RENDER_DIR),a
    xor a
    ld (w3d_pushwall_render+W3D_PUSHWALL_RENDER_POS),a
    ld a,(w3d_pushwall_requested_texture)
    ld (w3d_pushwall_render+W3D_PUSHWALL_RENDER_TEXTURE),a
    ld a,1
    ld (w3d_pushwall_state+0),a
    xor a
    ld (w3d_pushwall_state+1),a

; Source is the moving wall, destination is reserved immediately just like
; actorat/tilemap in the original PushWall.
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_TEXTURE)
    or 0c0h
    call w3d_map_write
    call w3d_pushwall_load_next_coords
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_TEXTURE)
    call w3d_map_write

    ld hl,(w3d_player_secret_count)
    inc.s hl
    ld a,l
    ld (w3d_player_secret_count+0),a
    ld a,h
    ld (w3d_player_secret_count+1),a
    ld a,1
    ld (w3d_pushwall_dirty),a
    ld (w3d_world_dirty),a
    ld a,W3D_AUDIO_SOUND_PUSHWALL
    ld b,127
    ld c,0
    jp w3d_audio_request

@blocked:
    ld a,W3D_AUDIO_SOUND_NOWAY
    ld b,127
    ld c,0
    jp w3d_audio_request

; Advance the persistent current cell by one cardinal step.
w3d_pushwall_advance_current:
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_X)
    ld b,a
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_Y)
    ld c,a
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_DIR)
    call w3d_pushwall_step_coords
    ld a,b
    ld (w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_X),a
    ld a,c
    ld (w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_Y),a
    ret

; Produce the cell after the current persistent cell in B/C.
w3d_pushwall_load_next_coords:
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_X)
    ld b,a
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_CURRENT_Y)
    ld c,a
    ld a,(w3d_pushwall_render+W3D_PUSHWALL_RENDER_DIR)
    jp w3d_pushwall_step_coords

; Produce the cell after caller-supplied B/C using the requested direction.
w3d_pushwall_load_requested_destination:
    ld a,(w3d_pushwall_requested_dir)
    ; fall through

; A=cardinal direction, B/C coordinate. Invalid values deliberately leave an
; out-of-range coordinate which the conservative destination check rejects.
w3d_pushwall_step_coords:
    cp W3D_DIR_EAST
    jr z,@east
    cp W3D_DIR_NORTH
    jr z,@north
    cp W3D_DIR_WEST
    jr z,@west
    cp W3D_DIR_SOUTH
    jr z,@south
    ld b,W3D_MAP_SIZE
    ret
@east:
    inc b
    ret
@north:
    dec c
    ret
@west:
    dec b
    ret
@south:
    inc c
    ret

; B/C destination. Return A=1 only for an open in-range map cell without an
; actor reservation or original blocking static.
w3d_pushwall_destination_clear:
    ld a,b
    cp W3D_MAP_SIZE
    jr nc,@blocked
    ld a,c
    cp W3D_MAP_SIZE
    jr nc,@blocked
    call w3d_map_read
    or a
    jr nz,@blocked
    call w3d_actorat_get
    or a
    jr nz,@blocked
    call w3d_static_tile_blocked
    or a
    jr nz,@blocked
    ld a,1
    ret
@blocked:
    xor a
    ret

; B=x,C=y -> A path/trigger metadata.
w3d_path_read:
    push bc
    ld hl,0
    ld l,c
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    ld de,0
    ld e,b
    add.s hl,de
    ld de,(w3d_level_path_ptr)
    add hl,de
    ld a,(hl)
    pop bc
    ret

; B=x,C=y,A=value. Runtime tilemap only.
w3d_map_write:
    push af
    call w3d_runtime_map_address
    pop af
    ld (hl),a
    ret

; B=x,C=y,A=area. Runtime area map only.
w3d_area_write:
    push af
    call w3d_runtime_area_address
    pop af
    ld (hl),a
    ret

w3d_runtime_map_address:
    ld hl,w3d_runtime_tilemap
    jr w3d_runtime_grid_address
w3d_runtime_area_address:
    ld hl,w3d_runtime_area_map
w3d_runtime_grid_address:
    push bc
    ld de,0
    ld e,c
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    ld a,e
    add a,b
    ld e,a
    jr nc,@ready
    inc d
@ready:
    add hl,de
    pop bc
    ret

; Renderer-facing authoritative payload and CPU-only timing/state. The first
; 89 bytes match schema 2's PUSHWALL_STATE record exactly.
w3d_pushwall_payload:
w3d_pushwall_render:
    ds W3D_PUSHWALL_RENDER_SIZE
w3d_pushwall_history_count:
    db 0
w3d_pushwall_history:
    ds W3D_PUSHWALL_HISTORY_MAX*W3D_PUSHWALL_HISTORY_ENTRY_SIZE
w3d_pushwall_state:
    dw 0
w3d_pushwall_dirty:
    db 0
w3d_player_secret_count:
    dw 0
w3d_player_secret_total:
    dw 0
w3d_pushwall_requested_dir:
    db 0
w3d_pushwall_requested_texture:
    db 0
w3d_pushwall_old_block:
    db 0
