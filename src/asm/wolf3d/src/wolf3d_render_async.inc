; =============================================================================
; Wolf3D render-completion control-loop support.
;
; One presentation producer may be in flight. The interrupt callback only
; recognizes and routes the ten-byte W3DR payload; all validation and VDU
; presentation work remains in the foreground. Event 1 completes a render;
; event 2 completes a VDP-owned fizzle. Non-W3DR records continue through
; normal MOS keyboard handling, with Escape latched as a shutdown request.
;
; This mirrors the proven earth-party-local ownership model while remaining
; Wolf3D-native: the eZ80 owns frame presentation and future simulation state;
; the VDP reports only that its submitted render has completed.
; =============================================================================

w3d_render_notify_token: equ 0573Dh

W3D_RENDER_EVENT_COMPLETE:        equ 1
W3D_RENDER_EVENT_FIZZLE_COMPLETE: equ 2

W3D_ASYNC_OWNER_NONE:             equ 0
W3D_ASYNC_OWNER_RENDER:           equ 1
W3D_ASYNC_OWNER_FIZZLE:           equ 2

; A purpose is latched at submission rather than inferred at completion.
; This keeps a slow callback from advancing a newer death phase by mistake.
W3D_RENDER_PURPOSE_NORMAL:        equ 0
W3D_RENDER_PURPOSE_DEAD_FACE:     equ 1
W3D_RENDER_PURPOSE_DEATH_TURN:    equ 2
W3D_RENDER_PURPOSE_DEATH_TARGET:  equ 3
W3D_RENDER_PURPOSE_DEATH_TARGET_SYNC: equ 4
W3D_RENDER_PURPOSE_RESPAWN:       equ 5

w3d_initialize_render_state:
; TODO: if the scratch area is contiguous we can use ldir to clear the whole block.
    xor a
    ld (w3d_render_in_flight),a
    ld (w3d_completion_ready),a
    ld (w3d_sequence_initialized),a
    ld (w3d_exit_requested),a
    ld (w3d_callback_error),a
    ld (w3d_frame_presented),a
    ld (w3d_async_owner),a
    ld (w3d_next_render_purpose),a
    ld (w3d_render_in_flight_purpose),a
    ld (w3d_completed_render_purpose),a
    ld (w3d_render_event_ready),a
    ld (w3d_fizzle_in_flight),a
    ld (w3d_fizzle_completion_ready),a
    ld (w3d_fizzle_sequence_initialized),a
    ld (w3d_fizzle_event_ready),a
    ld (w3d_fizzle_outstanding_token+0),a
    ld (w3d_fizzle_outstanding_token+1),a
    ld (w3d_completed_fizzle_token+0),a
    ld (w3d_completed_fizzle_token+1),a
    ld (w3d_fizzle_expected_sequence+0),a
    ld (w3d_fizzle_expected_sequence+1),a
    ld (w3d_expected_sequence+0),a
    ld (w3d_expected_sequence+1),a
    ret

; Prime the 24-bit 120 Hz MOS clock so the first control-loop delta is zero
; rather than the machine's full uptime. Future fixed-step simulation can
; consume w3d_elapsed_ticks without changing the render-completion lifecycle.
w3d_initialize_control_clock:
    MOSCALL mos_sysvars
    ld (w3d_sysvars_pointer),ix
    ld hl,(ix+sysvar_time)
    ld (w3d_timestamp_now),hl
    ld hl,0
    ld (w3d_elapsed_ticks),hl
    ret

w3d_tick_control_clock:
    ld ix,(w3d_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld de,(w3d_timestamp_now)
    ld (w3d_timestamp_now),hl
    or a
    sbc hl,de
    ld (w3d_elapsed_ticks),hl
    ret

; A=purpose for the next render submission. Unknown purposes are permitted so
; future presentation phases can be added without revising this mailbox ABI.
w3d_set_next_render_purpose:
    ld (w3d_next_render_purpose),a
    ret

; Publish the in-flight state before any render byte reaches the VDP. Carry is
; clear on success. Carry is set and the callback fault latch is raised if a
; caller attempts to overlap render and fizzle ownership.
w3d_mark_render_submitted:
    ld a,(w3d_async_owner)
    or a
    jr nz,@owner_conflict
    ld a,(w3d_render_in_flight)
    or a
    jr nz,@owner_conflict
    xor a
    ld (w3d_completion_ready),a
    ld (w3d_render_event_ready),a
    ld a,(w3d_next_render_purpose)
    ld (w3d_render_in_flight_purpose),a
    xor a
    ld (w3d_next_render_purpose),a
    ld a,1
    ld (w3d_render_in_flight),a
    ld a,W3D_ASYNC_OWNER_RENDER
    ld (w3d_async_owner),a
    or a
    ret

@owner_conflict:
    ld a,1
    ld (w3d_callback_error),a
    ld (w3d_exit_requested),a
    scf
    ret

; HL=uint16 token to be echoed by event 2. Only L/H are significant. Carry is
; clear on success. The command producer must call this before sending
; fizzle_to_red, exactly as a render producer calls mark_render_submitted.
w3d_mark_fizzle_submitted:
    ld a,(w3d_async_owner)
    or a
    jr nz,@owner_conflict
    ld a,(w3d_fizzle_in_flight)
    or a
    jr nz,@owner_conflict
    ld a,l
    ld (w3d_fizzle_outstanding_token+0),a
    ld a,h
    ld (w3d_fizzle_outstanding_token+1),a
    xor a
    ld (w3d_fizzle_completion_ready),a
    ld (w3d_fizzle_event_ready),a
    ld a,1
    ld (w3d_fizzle_in_flight),a
    ld a,W3D_ASYNC_OWNER_FIZZLE
    ld (w3d_async_owner),a
    or a
    ret

@owner_conflict:
    ld a,1
    ld (w3d_callback_error),a
    ld (w3d_exit_requested),a
    scf
    ret

; Undo a successfully marked fizzle when its synchronous command hook reports
; failure before any byte was accepted by the VDP.
w3d_cancel_fizzle_submission:
    xor a
    ld (w3d_fizzle_in_flight),a
    ld (w3d_fizzle_completion_ready),a
    ld a,(w3d_async_owner)
    cp W3D_ASYNC_OWNER_FIZZLE
    ret nz
    xor a
    ld (w3d_async_owner),a
    ret

; Atomically snapshot and validate the completion mailbox. A valid completed
; frame is presented exactly once from foreground code.
w3d_consume_render_completion:
    di
    ld hl,w3d_completion_record
    ld de,w3d_completion_snapshot
    ld bc,10
    ldir
    xor a
    ld (w3d_completion_ready),a
    ei

    ld a,(w3d_completion_snapshot+0)
    cp 'W'
    jp nz,@reject
    ld a,(w3d_completion_snapshot+1)
    cp '3'
    jp nz,@reject
    ld a,(w3d_completion_snapshot+2)
    cp 'D'
    jp nz,@reject
    ld a,(w3d_completion_snapshot+3)
    cp 'R'
    jp nz,@reject
    ld a,(w3d_completion_snapshot+4)
    cp 1
    jp nz,@reject
    ld a,(w3d_completion_snapshot+5)
    cp W3D_RENDER_EVENT_COMPLETE
    jp nz,@reject
    ld a,(w3d_completion_snapshot+6)
    cp w3d_render_notify_token & 0FFh
    jp nz,@reject
    ld a,(w3d_completion_snapshot+7)
    cp w3d_render_notify_token >> 8
    jp nz,@reject

    ld a,(w3d_sequence_initialized)
    or a
    jr z,@accept_first_sequence
    ld hl,w3d_completion_snapshot+8
    ld iy,w3d_expected_sequence
    ld a,(hl)
    cp (iy+0)
    jp nz,@reject
    inc hl
    ld a,(hl)
    cp (iy+1)
    jp nz,@reject
    jr @sequence_valid

@accept_first_sequence:
    ld hl,w3d_completion_snapshot+8
    ld iy,w3d_expected_sequence
    ld a,(hl)
    ld (iy+0),a
    inc hl
    ld a,(hl)
    ld (iy+1),a
    ld a,1
    ld (w3d_sequence_initialized),a

@sequence_valid:
    ld a,(w3d_async_owner)
    cp W3D_ASYNC_OWNER_RENDER
    jp nz,@reject
    call w3d_increment_expected_sequence
    di
    xor a
    ld (w3d_render_in_flight),a
    ld (w3d_async_owner),a
    ei
; Mode 8+128 is double buffered: present exactly once, only after the VDP has
; completed the hidden surface associated with this validated sequence.
    call w3d_vdu_present
    ld a,(w3d_render_in_flight_purpose)
    ld (w3d_completed_render_purpose),a
    ld a,1
    ld (w3d_frame_presented),a
    ld (w3d_render_event_ready),a
    ret

@reject:
; Keep render_in_flight asserted. Remaining resident is safer than returning
; while a completion producer might still target the callback.
    ld a,1
    ld (w3d_callback_error),a
    ld (w3d_exit_requested),a
    ret

w3d_increment_expected_sequence:
    ld hl,w3d_expected_sequence
    inc (hl)
    ret nz
    inc hl
    inc (hl)
    ret

; Carry set returns A=the purpose of one newly presented render and consumes
; that one-shot foreground event. Carry clear means there is no new event.
w3d_take_render_event:
    di
    ld a,(w3d_render_event_ready)
    or a
    jr z,@none
    ld a,(w3d_completed_render_purpose)
    ld b,a
    xor a
    ld (w3d_render_event_ready),a
    ld a,b
    ei
    scf
    ret
@none:
    ei
    or a
    ret

; Atomically snapshot and validate event 2. Unlike event 1, a fizzle has
; already updated both display surfaces and must never trigger VDU C3.
w3d_consume_fizzle_completion:
    di
    ld hl,w3d_fizzle_completion_record
    ld de,w3d_fizzle_completion_snapshot
    ld bc,10
    ldir
    xor a
    ld (w3d_fizzle_completion_ready),a
    ei

    ld a,(w3d_fizzle_completion_snapshot+0)
    cp 'W'
    jp nz,@reject
    ld a,(w3d_fizzle_completion_snapshot+1)
    cp '3'
    jp nz,@reject
    ld a,(w3d_fizzle_completion_snapshot+2)
    cp 'D'
    jp nz,@reject
    ld a,(w3d_fizzle_completion_snapshot+3)
    cp 'R'
    jp nz,@reject
    ld a,(w3d_fizzle_completion_snapshot+4)
    cp 1
    jp nz,@reject
    ld a,(w3d_fizzle_completion_snapshot+5)
    cp W3D_RENDER_EVENT_FIZZLE_COMPLETE
    jp nz,@reject
    ld a,(w3d_fizzle_completion_snapshot+6)
    ld b,a
    ld a,(w3d_fizzle_outstanding_token+0)
    cp b
    jp nz,@reject
    ld a,(w3d_fizzle_completion_snapshot+7)
    ld b,a
    ld a,(w3d_fizzle_outstanding_token+1)
    cp b
    jp nz,@reject

    ld a,(w3d_fizzle_sequence_initialized)
    or a
    jr z,@accept_first_sequence
    ld hl,w3d_fizzle_completion_snapshot+8
    ld iy,w3d_fizzle_expected_sequence
    ld a,(hl)
    cp (iy+0)
    jp nz,@reject
    inc hl
    ld a,(hl)
    cp (iy+1)
    jp nz,@reject
    jr @sequence_valid

@accept_first_sequence:
    ld hl,w3d_fizzle_completion_snapshot+8
    ld iy,w3d_fizzle_expected_sequence
    ld a,(hl)
    ld (iy+0),a
    inc hl
    ld a,(hl)
    ld (iy+1),a
    ld a,1
    ld (w3d_fizzle_sequence_initialized),a

@sequence_valid:
    ld a,(w3d_async_owner)
    cp W3D_ASYNC_OWNER_FIZZLE
    jp nz,@reject
    call w3d_increment_fizzle_expected_sequence
    ld a,(w3d_fizzle_outstanding_token+0)
    ld (w3d_completed_fizzle_token+0),a
    ld a,(w3d_fizzle_outstanding_token+1)
    ld (w3d_completed_fizzle_token+1),a
    di
    xor a
    ld (w3d_fizzle_in_flight),a
    ld (w3d_async_owner),a
    ei
    ld a,1
    ld (w3d_fizzle_event_ready),a
    ret

@reject:
; Retain fizzle ownership after a malformed or stale completion. Shutdown can
; then drain nothing further without accidentally permitting a render race.
    ld a,1
    ld (w3d_callback_error),a
    ld (w3d_exit_requested),a
    ret

w3d_increment_fizzle_expected_sequence:
    ld hl,w3d_fizzle_expected_sequence
    inc (hl)
    ret nz
    inc hl
    inc (hl)
    ret

; Carry set consumes one validated fizzle event and returns its uint16 token
; in HL (HLU is explicitly zero). Carry clear means no event is pending.
w3d_take_fizzle_event:
    di
    ld a,(w3d_fizzle_event_ready)
    or a
    jr z,@none
    xor a
    ld (w3d_fizzle_event_ready),a
    ld hl,0
    ld a,(w3d_completed_fizzle_token+0)
    ld l,a
    ld a,(w3d_completed_fizzle_token+1)
    ld h,a
    ei
    scf
    ret
@none:
    ei
    or a
    ret

w3d_install_render_callback:
    ld hl,w3d_render_packet_callback
    ld c,0
    MOSCALL mos_setkbvector
    ret

w3d_remove_render_callback:
    ld hl,0
    ld c,0
    MOSCALL mos_setkbvector
    ret

w3d_enable_render_notifications:
    ld hl,@command
    ld bc,@end-@command
    rst.lil 18h
    ret
@command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,41,1
    dw w3d_render_notify_token
@end:

w3d_disable_render_notifications:
    ld hl,@command
    ld bc,@end-@command
    rst.lil 18h
    ret
@command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,41,0
    dw 0
@end:

w3d_vdu_present:
    ld hl,@command
    ld bc,@end-@command
    rst.lil 18h
    ret
@command:
    db 23,0,0C3h
@end:

; MOS invokes this from its UART interrupt path with DEU pointing at the
; payload. It must not make MOS/VDU calls or perform foreground work.
w3d_render_packet_callback:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    push de
    pop ix

; W3DV is a startup compatibility reply, not a render event or keyboard
; record. The helper consumes cookie-matched and malformed replies atomically.
    call w3d_try_capture_version_packet
    jr c,@done

    ld a,(ix+0)
    cp 'W'
    jp nz,@keyboard
    ld a,(ix+1)
    cp '3'
    jp nz,@keyboard
    ld a,(ix+2)
    cp 'D'
    jp nz,@keyboard
    ld a,(ix+3)
    cp 'R'
    jp nz,@keyboard

; The shared magic has two independently sequenced foreground mailboxes.
; Unknown event values deliberately enter the render mailbox so validation
; turns protocol drift into a visible callback fault rather than a key event.
    ld a,(ix+5)
    cp W3D_RENDER_EVENT_FIZZLE_COMPLETE
    jr z,@fizzle_record
    ld iy,w3d_completion_record
    jr @copy_record
@fizzle_record:
    ld iy,w3d_fizzle_completion_record
@copy_record:
    push ix
    pop hl
    push iy
    pop de
    ld bc,10
    ldir

; MOS resumes normal keyboard processing after this callback. Turn W3DR into
; a harmless null key-up record before returning.
    xor a
    ld (ix+0),a
    ld (ix+1),a
    ld (ix+2),a
    ld (ix+3),a
    ld a,(ix+5)
    cp W3D_RENDER_EVENT_FIZZLE_COMPLETE
    ld a,1
    jr z,@fizzle_ready
    ld (w3d_completion_ready),a
    jr @done
@fizzle_ready:
    ld (w3d_fizzle_completion_ready),a
    jr @done

@keyboard:
; Escape key-down requests shutdown. The foreground waits for any outstanding
; render completion before removing this callback.
    ld a,(ix+3)
    cp 1
    jr nz,@done
    ld a,(ix+0)
    cp 27
    jr nz,@done
    ld a,1
    ld (w3d_exit_requested),a

@done:
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

w3d_render_in_flight:
    db 0

w3d_completion_ready:
    db 0

w3d_completion_record:
    ds 10

w3d_completion_snapshot:
    ds 10

w3d_expected_sequence:
    ds 2

w3d_sequence_initialized:
    db 0

w3d_exit_requested:
    db 0

w3d_callback_error:
    db 0

w3d_frame_presented:
    db 0

w3d_async_owner:
    db W3D_ASYNC_OWNER_NONE

w3d_next_render_purpose:
    db W3D_RENDER_PURPOSE_NORMAL

w3d_render_in_flight_purpose:
    db W3D_RENDER_PURPOSE_NORMAL

w3d_completed_render_purpose:
    db W3D_RENDER_PURPOSE_NORMAL

w3d_render_event_ready:
    db 0

w3d_fizzle_in_flight:
    db 0

w3d_fizzle_completion_ready:
    db 0

w3d_fizzle_completion_record:
    ds 10

w3d_fizzle_completion_snapshot:
    ds 10

w3d_fizzle_outstanding_token:
    ds 2

w3d_completed_fizzle_token:
    ds 2

w3d_fizzle_expected_sequence:
    ds 2

w3d_fizzle_sequence_initialized:
    db 0

w3d_fizzle_event_ready:
    db 0

w3d_sysvars_pointer:
    dl 0

w3d_timestamp_now:
    dl 0

w3d_elapsed_ticks:
    dl 0
