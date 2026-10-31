; =============================================================================
; Wolf3D production VDPlet descriptor and immutable update-batch serializer.
;
; This layer reads the same authoritative world and dirty tables as the
; standalone renderer bridge. A prepared batch remains byte-for-byte frozen,
; with the same nonzero generation, until the runtime accepts it. Simulation
; may accumulate fresh dirt while RUN owns that batch; a failed RUN retries
; the frozen bytes and never restores old flags over newer state.
;
; Lifecycle:
;   initialize -> prepare -> upload/send RUN -> mark_submitted
;   successful reply: accept_success
;   failed reply:     accept_failure -> prepare returns exact same bytes
;
; mark_submitted must immediately follow a successfully armed RUN. Its first
; invocation clears only the snapshot used to construct the batch. Retry
; submissions never clear dirty state a second time.
; =============================================================================

W3D_VDPLET_BATCH_STATUS_OK:          equ 0
W3D_VDPLET_BATCH_STATUS_EMPTY:       equ 1
W3D_VDPLET_BATCH_STATUS_GENERATION:  equ 2
W3D_VDPLET_BATCH_STATUS_LIFECYCLE:   equ 3

; Reset serializer ownership and materialize the exact 24-byte descriptor.
; The initial generation seed is zero, so the first full batch is generation 1.
w3d_vdplet_batch_initialize:
    ld hl,w3d_vdplet_descriptor_template
    ld de,w3d_vdplet_descriptor
    ld bc,W3P_ARGUMENT_BYTES
    ldir
    xor a
    ld (w3d_vdplet_batch_status),a
    ld (w3d_vdplet_batch_ready),a
    ld (w3d_vdplet_batch_submitted),a
    ld (w3d_vdplet_batch_snapshot_cleared),a
    ld (w3d_vdplet_batch_last_generation+0),a
    ld (w3d_vdplet_batch_last_generation+1),a
    ld (w3d_vdplet_batch_last_generation+2),a
    ld (w3d_vdplet_batch_candidate_generation+0),a
    ld (w3d_vdplet_batch_candidate_generation+1),a
    ld (w3d_vdplet_batch_candidate_generation+2),a
    inc a
    ld (w3d_vdplet_batch_full_required),a
    ret

; Require the next newly constructed batch to be a complete level snapshot.
; A currently prepared batch retains ownership and rejects this lifecycle
; change; level transitions request full only after the prior owner completes.
w3d_vdplet_batch_require_full:
    ld a,(w3d_vdplet_batch_ready)
    or a
    jr nz,@bad_lifecycle
    ld a,1
    ld (w3d_vdplet_batch_full_required),a
    or a
    ret
@bad_lifecycle:
    ld a,W3D_VDPLET_BATCH_STATUS_LIFECYCLE
    ld (w3d_vdplet_batch_status),a
    scf
    ret

; Return a frozen prepared batch or construct one from authoritative state.
; Carry clear: HL=batch address, DE=exact nonzero byte count.
; Carry set:   no dirty records or generation/lifecycle failure.
w3d_vdplet_batch_prepare:
    ld a,(w3d_vdplet_batch_ready)
    or a
    jr z,@new_batch
    ld a,(w3d_vdplet_batch_submitted)
    or a
    jp z,w3d_vdplet_batch_return_prepared
    ld a,W3D_VDPLET_BATCH_STATUS_LIFECYCLE
    ld (w3d_vdplet_batch_status),a
    scf
    ret

@new_batch:

    call w3d_vdplet_batch_snapshot_dirty
    ld hl,(w3d_vdplet_batch_last_generation)
    inc hl
; Low-word zero can only be the forbidden 0xffff -> 0 wrap because the saved
; generation's upper byte is always deliberately zero.
    ld a,h
    or l
    jr nz,@generation_ready
    ld a,W3D_VDPLET_BATCH_STATUS_GENERATION
    ld (w3d_vdplet_batch_status),a
    scf
    ret
@generation_ready:
    ld a,l
    ld (w3d_vdplet_batch_candidate_generation+0),a
    ld a,h
    ld (w3d_vdplet_batch_candidate_generation+1),a
    xor a
    ld (w3d_vdplet_batch_candidate_generation+2),a

    ld hl,w3d_vdplet_batch_header_template
    ld de,w3d_vdplet_batch_buffer
    ld bc,W3P_BATCH_HEADER_BYTES
    ldir
    ld de,w3d_vdplet_batch_buffer+W3P_BATCH_HEADER_BYTES
    ld (w3d_vdplet_batch_cursor),de
    xor a
    ld (w3d_vdplet_batch_records+0),a
    ld (w3d_vdplet_batch_records+1),a
    ld (w3d_vdplet_batch_records+2),a
    ld (w3d_vdplet_batch_snapshot_cleared),a
    ld (w3d_vdplet_batch_submitted),a

    ld a,(w3d_vdplet_batch_candidate_generation+0)
    ld (w3d_vdplet_batch_buffer+W3P_BATCH_GENERATION_OFFSET+0),a
    ld a,(w3d_vdplet_batch_candidate_generation+1)
    ld (w3d_vdplet_batch_buffer+W3P_BATCH_GENERATION_OFFSET+1),a

    ld a,(w3d_vdplet_batch_full_required)
    or a
    jr z,@dirty
    ld a,W3P_BATCH_FLAG_FULL
    ld (w3d_vdplet_batch_buffer+W3P_BATCH_FLAGS_OFFSET+0),a
    call w3d_vdplet_batch_append_level
    call w3d_vdplet_batch_append_player
    call w3d_vdplet_batch_append_all_doors
    call w3d_vdplet_batch_append_all_actors
    call w3d_vdplet_batch_append_all_statics
    call w3d_vdplet_batch_append_hud
    call w3d_vdplet_batch_append_view_weapon
    jr @finalize

@dirty:
    call w3d_vdplet_batch_append_dirty_player
    call w3d_vdplet_batch_append_dirty_doors
    call w3d_vdplet_batch_append_dirty_actors
    call w3d_vdplet_batch_append_dirty_statics
    call w3d_vdplet_batch_append_dirty_hud
    call w3d_vdplet_batch_append_dirty_view_weapon
    ld hl,(w3d_vdplet_batch_records)
    ld a,h
    or l
    jr nz,@finalize
    ld a,W3D_VDPLET_BATCH_STATUS_EMPTY
    ld (w3d_vdplet_batch_status),a
    scf
    ret

@finalize:
    ld hl,(w3d_vdplet_batch_cursor)
    ld de,w3d_vdplet_batch_buffer
    or a
    sbc hl,de
    ld a,l
    ld (w3d_vdplet_batch_bytes+0),a
    ld (w3d_vdplet_batch_buffer+W3P_BATCH_TOTAL_OFFSET+0),a
    ld a,h
    ld (w3d_vdplet_batch_bytes+1),a
    ld (w3d_vdplet_batch_buffer+W3P_BATCH_TOTAL_OFFSET+1),a
    xor a
    ld (w3d_vdplet_batch_bytes+2),a
    ld hl,(w3d_vdplet_batch_records)
    ld a,l
    ld (w3d_vdplet_batch_buffer+W3P_BATCH_RECORDS_OFFSET+0),a
    ld a,h
    ld (w3d_vdplet_batch_buffer+W3P_BATCH_RECORDS_OFFSET+1),a
    xor a
    ld (w3d_vdplet_batch_status),a
    inc a
    ld (w3d_vdplet_batch_ready),a
    jp w3d_vdplet_batch_return_prepared

w3d_vdplet_batch_return_prepared:
    ld hl,w3d_vdplet_batch_buffer
    ld de,(w3d_vdplet_batch_bytes)
    or a
    ret

; Call only after RUN has been armed and emitted successfully. The first send
; consumes the captured dirty snapshot; exact retries merely reacquire RUN
; ownership and preserve all dirt accumulated after the original send.
w3d_vdplet_batch_mark_submitted:
    ld a,(w3d_vdplet_batch_ready)
    or a
    jr z,@bad_lifecycle
    ld a,(w3d_vdplet_batch_submitted)
    or a
    jr nz,@bad_lifecycle
    ld a,(w3d_vdplet_batch_snapshot_cleared)
    or a
    jr nz,@mark
    call w3d_vdplet_batch_clear_snapshot
    ld a,1
    ld (w3d_vdplet_batch_snapshot_cleared),a
@mark:
    ld a,1
    ld (w3d_vdplet_batch_submitted),a
    xor a
    ld (w3d_vdplet_batch_status),a
    ret
@bad_lifecycle:
    ld a,W3D_VDPLET_BATCH_STATUS_LIFECYCLE
    ld (w3d_vdplet_batch_status),a
    scf
    ret

; A rejected/publication-failed RUN leaves the frozen batch ready for an exact
; retry. Never restore its old flags: newer simulation dirt is authoritative.
w3d_vdplet_batch_accept_failure:
    ld a,(w3d_vdplet_batch_ready)
    or a
    jr z,@bad_lifecycle
    ld a,(w3d_vdplet_batch_submitted)
    or a
    jr z,@bad_lifecycle
    xor a
    ld (w3d_vdplet_batch_submitted),a
    ld (w3d_vdplet_batch_status),a
    ret
@bad_lifecycle:
    ld a,W3D_VDPLET_BATCH_STATUS_LIFECYCLE
    ld (w3d_vdplet_batch_status),a
    scf
    ret

; Commit the accepted generation and release the immutable staging batch.
w3d_vdplet_batch_accept_success:
    ld a,(w3d_vdplet_batch_ready)
    or a
    jr z,@bad_lifecycle
    ld a,(w3d_vdplet_batch_submitted)
    or a
    jr z,@bad_lifecycle
    ld a,(w3d_vdplet_batch_candidate_generation+0)
    ld (w3d_vdplet_batch_last_generation+0),a
    ld a,(w3d_vdplet_batch_candidate_generation+1)
    ld (w3d_vdplet_batch_last_generation+1),a
    xor a
    ld (w3d_vdplet_batch_last_generation+2),a
    ld (w3d_vdplet_batch_ready),a
    ld (w3d_vdplet_batch_submitted),a
    ld (w3d_vdplet_batch_snapshot_cleared),a
    ld (w3d_vdplet_batch_full_required),a
    ld (w3d_vdplet_batch_status),a
    ret
@bad_lifecycle:
    ld a,W3D_VDPLET_BATCH_STATUS_LIFECYCLE
    ld (w3d_vdplet_batch_status),a
    scf
    ret

; ---------------------------------------------------------------------------
; Record construction
; ---------------------------------------------------------------------------

; A=record type, B=payload bytes.
w3d_vdplet_batch_begin_record:
    ld de,(w3d_vdplet_batch_cursor)
    ld (de),a
    inc de
    ld a,b
    ld (de),a
    inc de
    ld (w3d_vdplet_batch_cursor),de
    ld hl,(w3d_vdplet_batch_records)
    inc hl
    ld (w3d_vdplet_batch_records),hl
    ret

; HL=source, BC=byte count.
w3d_vdplet_batch_append_bytes:
    ld de,(w3d_vdplet_batch_cursor)
    ldir
    ld (w3d_vdplet_batch_cursor),de
    ret

w3d_vdplet_batch_append_level:
    ld a,W3D_FIXTURE_TILEMAP_BUFFER_ID
    ld (w3d_vdplet_level_payload+0),a
    xor a
    ld (w3d_vdplet_level_payload+1),a
    ld a,(w3d_level_door_count)
    ld (w3d_vdplet_level_payload+2),a
    ld a,(w3d_static_count+0)
    ld (w3d_vdplet_level_payload+3),a
    ld a,(w3d_static_count+1)
    ld (w3d_vdplet_level_payload+4),a
    xor a
    ld (w3d_vdplet_level_payload+5),a
    ld a,W3P_RECORD_LEVEL
    ld b,W3P_LEVEL_BYTES
    call w3d_vdplet_batch_begin_record
    ld hl,w3d_vdplet_level_payload
    ld bc,W3P_LEVEL_BYTES
    jp w3d_vdplet_batch_append_bytes

w3d_vdplet_batch_append_player:
    ld a,W3P_RECORD_PLAYER
    ld b,W3P_PLAYER_BYTES
    call w3d_vdplet_batch_begin_record
    ld hl,w3d_player_pose
    ld bc,W3P_PLAYER_BYTES
    jp w3d_vdplet_batch_append_bytes

w3d_vdplet_batch_append_dirty_player:
    ld a,(w3d_vdplet_player_dirty_snapshot)
    or a
    ret z
    jp w3d_vdplet_batch_append_player

w3d_vdplet_batch_append_all_doors:
    xor a
    ld (w3d_vdplet_batch_door_index),a
@loop:
    ld a,(w3d_vdplet_batch_door_index)
    call w3d_compare_door_index
    ret nc
    call w3d_vdplet_batch_append_current_door
    ld a,(w3d_vdplet_batch_door_index)
    inc a
    ld (w3d_vdplet_batch_door_index),a
    jr @loop

w3d_vdplet_batch_append_dirty_doors:
    xor a
    ld (w3d_vdplet_batch_door_index),a
@loop:
    ld a,(w3d_vdplet_batch_door_index)
    call w3d_compare_door_index
    ret nc
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_vdplet_door_dirty_snapshot
    add hl,de
    ld a,(hl)
    or a
    call nz,w3d_vdplet_batch_append_current_door
    ld a,(w3d_vdplet_batch_door_index)
    inc a
    ld (w3d_vdplet_batch_door_index),a
    jr @loop

w3d_vdplet_batch_append_current_door:
    ld a,(w3d_vdplet_batch_door_index)
    ld (w3d_vdplet_door_payload+0),a
    call w3d_door_pointer_from_index
    push ix
    pop hl
    ld de,w3d_vdplet_door_payload+1
    ld bc,W3D_DOOR_WIRE_SIZE
    ldir
    ld a,W3P_RECORD_DOOR
    ld b,W3P_DOOR_BYTES
    call w3d_vdplet_batch_begin_record
    ld hl,w3d_vdplet_door_payload
    ld bc,W3P_DOOR_BYTES
    jp w3d_vdplet_batch_append_bytes

w3d_vdplet_batch_append_all_actors:
    ld a,1
    ld (w3d_vdplet_batch_actor_index),a
@loop:
    ld a,(w3d_vdplet_batch_actor_index)
    cp W3D_MAX_ACTORS
    ret nc
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_ACTIVE)
    cp W3D_ACTOR_ACTIVE_FREE
    jr z,@next
    ld a,(w3d_vdplet_batch_actor_index)
    call w3d_vdplet_batch_append_actor_set
@next:
    ld a,(w3d_vdplet_batch_actor_index)
    inc a
    ld (w3d_vdplet_batch_actor_index),a
    jr @loop

w3d_vdplet_batch_append_dirty_actors:
    ld a,1
    ld (w3d_vdplet_batch_actor_index),a
@loop:
    ld a,(w3d_vdplet_batch_actor_index)
    cp W3D_MAX_ACTORS
    ret nc
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_vdplet_actor_dirty_snapshot
    add hl,de
    ld a,(hl)
    cp W3D_ACTOR_DIRTY_SET
    jr z,@set
    cp W3D_ACTOR_DIRTY_REMOVE
    jr z,@remove
@next:
    ld a,(w3d_vdplet_batch_actor_index)
    inc a
    ld (w3d_vdplet_batch_actor_index),a
    jr @loop
@set:
    ld a,(w3d_vdplet_batch_actor_index)
    call w3d_vdplet_batch_append_actor_set
    jr @next
@remove:
    ld a,(w3d_vdplet_batch_actor_index)
    ld (w3d_vdplet_actor_remove_payload+0),a
    xor a
    ld (w3d_vdplet_actor_remove_payload+1),a
    ld a,W3P_RECORD_ACTOR_REMOVE
    ld b,W3P_ACTOR_REMOVE_BYTES
    call w3d_vdplet_batch_begin_record
    ld hl,w3d_vdplet_actor_remove_payload
    ld bc,W3P_ACTOR_REMOVE_BYTES
    call w3d_vdplet_batch_append_bytes
    jr @next

; A=actor id.
w3d_vdplet_batch_append_actor_set:
    call w3d_build_actor_wire_record
    ld a,W3P_RECORD_ACTOR_SET
    ld b,W3P_ACTOR_SET_BYTES
    call w3d_vdplet_batch_begin_record
    ld hl,w3d_actor_wire_record
    ld bc,W3P_ACTOR_SET_BYTES
    jp w3d_vdplet_batch_append_bytes

w3d_vdplet_batch_append_all_statics:
    ld hl,0
    ld (w3d_vdplet_batch_static_index),hl
@loop:
    call w3d_vdplet_batch_static_in_range
    ret nc
    call w3d_vdplet_batch_append_current_static
    ld hl,(w3d_vdplet_batch_static_index)
    inc hl
    ld (w3d_vdplet_batch_static_index),hl
    jr @loop

w3d_vdplet_batch_append_dirty_statics:
    ld hl,0
    ld (w3d_vdplet_batch_static_index),hl
@loop:
    call w3d_vdplet_batch_static_in_range
    ret nc
    ld hl,(w3d_vdplet_batch_static_index)
    ld de,w3d_vdplet_static_dirty_snapshot
    add hl,de
    ld a,(hl)
    or a
    call nz,w3d_vdplet_batch_append_current_static
    ld hl,(w3d_vdplet_batch_static_index)
    inc hl
    ld (w3d_vdplet_batch_static_index),hl
    jr @loop

; Carry set iff the uint16 serializer index is below the runtime static count.
w3d_vdplet_batch_static_in_range:
    ld hl,(w3d_vdplet_batch_static_index)
    ld de,0
    ld a,(w3d_static_count+0)
    ld e,a
    ld a,(w3d_static_count+1)
    ld d,a
    or a
    sbc hl,de
    ret

w3d_vdplet_batch_append_current_static:
    ld hl,(w3d_vdplet_batch_static_index)
    ld a,l
    ld (w3d_vdplet_static_payload+0),a
    ld a,h
    ld (w3d_vdplet_static_payload+1),a
    ld de,0
    ld e,l
    ld d,h
    add hl,hl
    add hl,de
    add hl,hl
    ld de,w3d_statics
    add hl,de
    ld de,w3d_vdplet_static_payload+2
    ld bc,W3D_STATIC_WIRE_SIZE
    ldir
    ld a,W3P_RECORD_STATIC
    ld b,W3P_STATIC_BYTES
    call w3d_vdplet_batch_begin_record
    ld hl,w3d_vdplet_static_payload
    ld bc,W3P_STATIC_BYTES
    jp w3d_vdplet_batch_append_bytes

w3d_vdplet_batch_append_hud:
    ld a,(w3d_player_health)
    ld (w3d_vdplet_hud_payload+0),a
    ld a,(w3d_player_ammo)
    ld (w3d_vdplet_hud_payload+1),a
    ld a,(w3d_player_key_flags)
    ld (w3d_vdplet_hud_payload+2),a
    ld a,(w3d_player_weapon)
    ld (w3d_vdplet_hud_payload+3),a
    ld hl,w3d_player_score
    ld de,w3d_vdplet_hud_payload+4
    ld bc,4
    ldir
    ld a,(w3d_level_requested_index)
    inc a
    ld (w3d_vdplet_hud_payload+8),a
    xor a
    ld (w3d_vdplet_hud_payload+9),a
    ld a,(w3d_player_lives)
    ld (w3d_vdplet_hud_payload+10),a
    xor a
    ld (w3d_vdplet_hud_payload+11),a
    ld a,W3P_RECORD_HUD
    ld b,W3P_HUD_BYTES
    call w3d_vdplet_batch_begin_record
    ld hl,w3d_vdplet_hud_payload
    ld bc,W3P_HUD_BYTES
    jp w3d_vdplet_batch_append_bytes

w3d_vdplet_batch_append_dirty_hud:
    ld a,(w3d_vdplet_hud_dirty_snapshot)
    or a
    ret z
    jp w3d_vdplet_batch_append_hud

w3d_vdplet_batch_append_view_weapon:
    ld a,W3P_RECORD_VIEW_WEAPON
    ld b,W3P_VIEW_WEAPON_BYTES
    call w3d_vdplet_batch_begin_record
    ld hl,w3d_player_weapon_shape
    ld bc,W3P_VIEW_WEAPON_BYTES
    jp w3d_vdplet_batch_append_bytes

w3d_vdplet_batch_append_dirty_view_weapon:
    ld a,(w3d_vdplet_view_dirty_snapshot)
    or a
    ret z
    jp w3d_vdplet_batch_append_view_weapon

; ---------------------------------------------------------------------------
; Dirty snapshot and first-submission consumption
; ---------------------------------------------------------------------------

w3d_vdplet_batch_snapshot_dirty:
    ld hl,w3d_door_dirty
    ld de,w3d_vdplet_door_dirty_snapshot
    ld bc,W3D_MAX_DOORS
    ldir
    ld hl,w3d_actor_dirty
    ld de,w3d_vdplet_actor_dirty_snapshot
    ld bc,W3D_MAX_ACTORS
    ldir
    ld hl,w3d_static_dirty
    ld de,w3d_vdplet_static_dirty_snapshot
    ld bc,W3D_MAX_STATICS
    ldir
    ld a,(w3d_player_dirty)
    ld (w3d_vdplet_player_dirty_snapshot),a
    ld a,(w3d_hud_dirty)
    ld (w3d_vdplet_hud_dirty_snapshot),a
    ld a,(w3d_player_weapon_shape_dirty)
    ld (w3d_vdplet_view_dirty_snapshot),a
    ret

w3d_vdplet_batch_clear_snapshot:
    ld hl,w3d_vdplet_door_dirty_snapshot
    ld de,w3d_door_dirty
    ld bc,W3D_MAX_DOORS
    call w3d_vdplet_batch_clear_matching_bytes
    ld hl,w3d_vdplet_actor_dirty_snapshot
    ld de,w3d_actor_dirty
    ld bc,W3D_MAX_ACTORS
    call w3d_vdplet_batch_clear_matching_bytes
    ld hl,w3d_vdplet_static_dirty_snapshot
    ld de,w3d_static_dirty
    ld bc,W3D_MAX_STATICS
    call w3d_vdplet_batch_clear_matching_bytes

    ld a,(w3d_vdplet_player_dirty_snapshot)
    ld b,a
    or a
    jr z,@hud
    ld a,(w3d_player_dirty)
    cp b
    jr nz,@hud
    xor a
    ld (w3d_player_dirty),a
@hud:
    ld a,(w3d_vdplet_hud_dirty_snapshot)
    ld b,a
    or a
    jr z,@view
    ld a,(w3d_hud_dirty)
    cp b
    jr nz,@view
    xor a
    ld (w3d_hud_dirty),a
@view:
    ld a,(w3d_vdplet_view_dirty_snapshot)
    ld b,a
    or a
    jr z,@refresh
    ld a,(w3d_player_weapon_shape_dirty)
    cp b
    jr nz,@refresh
    xor a
    ld (w3d_player_weapon_shape_dirty),a
@refresh:
    jp w3d_vdplet_batch_refresh_world_dirty

; HL=snapshot, DE=live, BC=count. Clear a live byte only when the nonzero
; captured value still matches it.
w3d_vdplet_batch_clear_matching_bytes:
@loop:
    ld a,(hl)
    or a
    jr z,@next
    push bc
    ld b,a
    ld a,(de)
    cp b
    pop bc
    jr nz,@next
    xor a
    ld (de),a
@next:
    inc hl
    inc de
    dec.s bc
    ld a,b
    or c
    jr nz,@loop
    ret

w3d_vdplet_batch_refresh_world_dirty:
    ld hl,w3d_door_dirty
    ld bc,W3D_MAX_DOORS
    call w3d_vdplet_batch_any_nonzero
    jr nz,@dirty
    ld hl,w3d_actor_dirty
    ld bc,W3D_MAX_ACTORS
    call w3d_vdplet_batch_any_nonzero
    jr nz,@dirty
    ld hl,w3d_static_dirty
    ld bc,W3D_MAX_STATICS
    call w3d_vdplet_batch_any_nonzero
    jr nz,@dirty
    ld a,(w3d_player_dirty)
    ld b,a
    ld a,(w3d_hud_dirty)
    or b
    ld b,a
    ld a,(w3d_player_weapon_shape_dirty)
    or b
    jr nz,@dirty
    xor a
    ld (w3d_world_dirty),a
    ret
@dirty:
    ld a,1
    ld (w3d_world_dirty),a
    ret

; HL=bytes, BC=count; NZ when any byte is nonzero.
w3d_vdplet_batch_any_nonzero:
@loop:
    ld a,(hl)
    or a
    ret nz
    inc hl
    dec.s bc
    ld a,b
    or c
    jr nz,@loop
    ret

; ---------------------------------------------------------------------------
; Durable serializer storage
; ---------------------------------------------------------------------------

w3d_vdplet_descriptor_template:
    db 'W','3','P','A'
    db W3P_SCHEMA_VERSION,W3P_ARGUMENT_BYTES
    dw W3P_ARG_FLAG_COPIED_PIXELS
    dw W3D_VDPLET_WORKSPACE_BUFFER
    dw W3D_VDPLET_UPDATE_BUFFER
    dw W3D_FIXTURE_TILEMAP_BUFFER_ID
    dw W3P_DEFAULT_WALL_BASE
    dw W3P_DEFAULT_SPRITE_BASE
    dw W3P_DEFAULT_HUD_BASE
    dw 0
    dw 0

w3d_vdplet_batch_header_template:
    db 'W','3','D','U'
    db W3P_SCHEMA_VERSION,W3P_BATCH_HEADER_BYTES
    dw 0
    dw 0
    dw 0
    dw 0
    dw 0

w3d_vdplet_descriptor:
    ds W3P_ARGUMENT_BYTES
w3d_vdplet_batch_buffer:
    ds W3P_BATCH_MAX_BYTES
w3d_vdplet_batch_cursor:
    dl 0
w3d_vdplet_batch_bytes:
    dl 0
w3d_vdplet_batch_records:
    dl 0
w3d_vdplet_batch_last_generation:
    dl 0
w3d_vdplet_batch_candidate_generation:
    dl 0
w3d_vdplet_batch_status:
    db W3D_VDPLET_BATCH_STATUS_OK
w3d_vdplet_batch_ready:
    db 0
w3d_vdplet_batch_submitted:
    db 0
w3d_vdplet_batch_snapshot_cleared:
    db 0
w3d_vdplet_batch_full_required:
    db 1

w3d_vdplet_batch_door_index:
    db 0
w3d_vdplet_batch_actor_index:
    db 0
w3d_vdplet_batch_static_index:
    dl 0

w3d_vdplet_level_payload:
    ds W3P_LEVEL_BYTES
w3d_vdplet_door_payload:
    ds W3P_DOOR_BYTES
w3d_vdplet_actor_remove_payload:
    ds W3P_ACTOR_REMOVE_BYTES
w3d_vdplet_static_payload:
    ds W3P_STATIC_BYTES
w3d_vdplet_hud_payload:
    ds W3P_HUD_BYTES

w3d_vdplet_door_dirty_snapshot:
    ds W3D_MAX_DOORS
w3d_vdplet_actor_dirty_snapshot:
    ds W3D_MAX_ACTORS
w3d_vdplet_static_dirty_snapshot:
    ds W3D_MAX_STATICS
w3d_vdplet_player_dirty_snapshot:
    db 0
w3d_vdplet_hud_dirty_snapshot:
    db 0
w3d_vdplet_view_dirty_snapshot:
    db 0
