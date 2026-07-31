; =============================================================================
; Wolf3D render-completion control-loop support.
;
; One render may be in flight. The interrupt callback only recognizes and
; copies the ten-byte W3DR completion payload; all VDU presentation work
; remains in the foreground. Non-W3DR records continue through normal MOS
; keyboard handling, with Escape latched as a clean shutdown request.
;
; This mirrors the proven earth-party-local ownership model while remaining
; Wolf3D-native: the eZ80 owns frame presentation and future simulation state;
; the VDP reports only that its submitted render has completed.
; =============================================================================

w3d_render_notify_token: equ 0573Dh

w3d_initialize_render_state:
    xor a
    ld (w3d_render_in_flight),a
    ld (w3d_completion_ready),a
    ld (w3d_sequence_initialized),a
    ld (w3d_exit_requested),a
    ld (w3d_callback_error),a
    ld (w3d_frame_presented),a
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

; Publish the in-flight state before any render byte reaches the VDP.
w3d_mark_render_submitted:
    xor a
    ld (w3d_completion_ready),a
    ld a,1
    ld (w3d_render_in_flight),a
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

    ld a,(w3d_completion_snapshot+4)
    cp 1
    jr nz,@reject
    ld a,(w3d_completion_snapshot+5)
    cp 1
    jr nz,@reject
    ld a,(w3d_completion_snapshot+6)
    cp w3d_render_notify_token & 0FFh
    jr nz,@reject
    ld a,(w3d_completion_snapshot+7)
    cp w3d_render_notify_token >> 8
    jr nz,@reject

    ld a,(w3d_sequence_initialized)
    or a
    jr z,@accept_first_sequence
    ld hl,w3d_completion_snapshot+8
    ld iy,w3d_expected_sequence
    ld a,(hl)
    cp (iy+0)
    jr nz,@reject
    inc hl
    ld a,(hl)
    cp (iy+1)
    jr nz,@reject
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
    call w3d_increment_expected_sequence
    di
    xor a
    ld (w3d_render_in_flight),a
    ei
; Mode 8+128 is double buffered: present exactly once, only after the VDP has
; completed the hidden surface associated with this validated sequence.
    call w3d_vdu_present
    ld a,1
    ld (w3d_frame_presented),a
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
    push ix
    push iy
    push de
    pop ix

    ld a,(ix+0)
    cp 'W'
    jr nz,@keyboard
    ld a,(ix+1)
    cp '3'
    jr nz,@keyboard
    ld a,(ix+2)
    cp 'D'
    jr nz,@keyboard
    ld a,(ix+3)
    cp 'R'
    jr nz,@keyboard

    ld iy,w3d_completion_record
    ld a,(ix+0)
    ld (iy+0),a
    ld a,(ix+1)
    ld (iy+1),a
    ld a,(ix+2)
    ld (iy+2),a
    ld a,(ix+3)
    ld (iy+3),a
    ld a,(ix+4)
    ld (iy+4),a
    ld a,(ix+5)
    ld (iy+5),a
    ld a,(ix+6)
    ld (iy+6),a
    ld a,(ix+7)
    ld (iy+7),a
    ld a,(ix+8)
    ld (iy+8),a
    ld a,(ix+9)
    ld (iy+9),a

; MOS resumes normal keyboard processing after this callback. Turn W3DR into
; a harmless null key-up record before returning.
    xor a
    ld (ix+0),a
    ld (ix+1),a
    ld (ix+2),a
    ld (ix+3),a
    ld a,1
    ld (w3d_completion_ready),a
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

w3d_sysvars_pointer:
    dl 0

w3d_timestamp_now:
    dl 0

w3d_elapsed_ticks:
    dl 0
