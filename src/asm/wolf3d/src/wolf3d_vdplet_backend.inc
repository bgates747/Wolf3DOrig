; =============================================================================
; Production Wolf3D VDPlet adapter for the application's one-frame-in-flight
; renderer lifecycle. Standalone remains the tracked/default backend.
; =============================================================================

; A transient native publication failure may be retried once with the exact
; frozen generation. A second rejection of those same bytes is deterministic
; for this client lifetime: continuing to retry would leave simulation and
; audio live behind a permanently frozen visible frame. Fail closed instead
; and preserve the native result in the ordinary post-MOS diagnostic.
W3D_VDPLET_RENDER_RETRY_LIMIT: equ 1
W3D_VDPLET_FIZZLE_OP_NONE:     equ 0
W3D_VDPLET_FIZZLE_OP_BEGIN:    equ 1
W3D_VDPLET_FIZZLE_OP_DISPLAY:  equ 2
W3D_VDPLET_FIZZLE_OP_SYNC:     equ 3

; Open the shared runtime/module, construct application-owned workspace and
; descriptor buffers, and CONFIG the module. The keyboard packet callback is
; already live, so every requested VDPL transaction has a valid reply path.
w3d_vdplet_backend_open:
    xor a
    ld (w3d_vdplet_render_retry_count),a
    call w3d_vdplet_open
    jr c,@failed
    ld a,W3D_VDPLET_STAGE_WORKSPACE
    ld (w3d_vdplet_stage),a
    ld bc,W3D_VDPLET_WORKSPACE_BUFFER
    ld de,W3P_DIRECT_TARGET_WORKSPACE_BYTES
    call w3d_vdplet_create_zero_buffer
    jr c,@cleanup
    call w3d_vdplet_batch_initialize
    ld a,W3D_VDPLET_STAGE_DESCRIPTOR
    ld (w3d_vdplet_stage),a
    call w3d_vdplet_upload_descriptor
    jr c,@cleanup
    ld a,W3D_VDPLET_STAGE_CONFIG
    ld (w3d_vdplet_stage),a
    call w3d_vdplet_configure_module
    ret nc
@cleanup:
    push af
    call w3d_vdplet_close
    pop af
    scf
@failed:
    call w3d_vdplet_select_failure_message
    scf
    ret

; Close while the callback still exists; UNLOAD's requested DONE must traverse
; the same mailbox as RUN completions.
w3d_vdplet_backend_close:
    jp w3d_vdplet_close

w3d_vdplet_upload_descriptor:
    ld bc,W3D_VDPLET_ARGUMENT_BUFFER
    ld hl,w3d_vdplet_descriptor
    ld de,W3P_ARGUMENT_BYTES
    jp w3d_vdplet_upload_buffer

w3d_vdplet_configure_module:
    ld bc,W3P_ENTRY_CONFIG
    ld de,W3D_VDPLET_ARGUMENT_BUFFER
    call w3d_vdplet_send_run
    ret c
    jp w3d_vdplet_wait_run

w3d_vdplet_reset_module:
    ld a,W3D_VDPLET_STAGE_RESET
    ld (w3d_vdplet_stage),a
    ld bc,W3P_ENTRY_RESET
    ld de,W3D_VDPLET_ARGUMENT_BUFFER
    call w3d_vdplet_send_run
    ret c
    call w3d_vdplet_wait_run
    ret c
    call w3d_vdplet_batch_initialize
    jp w3d_vdplet_configure_module

; Level replacement/respawn resets the VDP mirror and serializer generation,
; re-CONFIGs the same immutable resource descriptor, then submits one complete
; authoritative snapshot.
w3d_vdplet_submit_level_reset:
    call w3d_vdplet_reset_module
    ret c
    jp w3d_vdplet_submit_dirty_world_render

; Fizzle RUNs share the global one-producer owner but deliberately do not use
; the old standalone event-2 mailbox. Requested VDPL DONE is the only
; completion, and the app decides whether this operation needs one C3.
w3d_vdplet_submit_fizzle_begin:
    ld a,W3D_VDPLET_FIZZLE_OP_BEGIN
    ld bc,W3P_ENTRY_FIZZLE_BEGIN
    jr w3d_vdplet_submit_fizzle_run

w3d_vdplet_submit_fizzle_display:
    ld a,W3D_VDPLET_FIZZLE_OP_DISPLAY
    ld bc,W3P_ENTRY_FIZZLE_STEP
    jr w3d_vdplet_submit_fizzle_run

w3d_vdplet_submit_fizzle_sync:
    ld a,W3D_VDPLET_FIZZLE_OP_SYNC
    ld bc,W3P_ENTRY_FIZZLE_STEP

w3d_vdplet_submit_fizzle_run:
    ld (w3d_vdplet_fizzle_operation),a
    ld a,W3D_VDPLET_STAGE_FIZZLE
    ld (w3d_vdplet_stage),a
    push bc
    ld hl,0
    call w3d_mark_fizzle_submitted
    pop bc
    ret c
    ld de,W3D_VDPLET_ARGUMENT_BUFFER
    call w3d_vdplet_send_run
    ret nc
    push af
    call w3d_cancel_fizzle_submission
    xor a
    ld (w3d_vdplet_fizzle_operation),a
    pop af
    scf
    ret

; Consume exactly one begin/display/sync reply. A displayed slice gets one C3;
; the final sync writes the newly hidden surface and intentionally does not
; swap. The death state machine owns the semantic transition after success.
w3d_vdplet_consume_fizzle_completion:
    call w3d_vdplet_wait_run
    jr c,@fatal
    call w3d_cancel_fizzle_submission
    ld a,(w3d_vdplet_fizzle_operation)
    cp W3D_VDPLET_FIZZLE_OP_DISPLAY
    call z,w3d_vdu_present
    call w3d_death_accept_vdplet_fizzle_completion
    xor a
    ld (w3d_vdplet_fizzle_operation),a
    ret
@fatal:
    call w3d_vdplet_select_failure_message
    ld a,1
    ld (w3d_callback_error),a
    ld (w3d_exit_requested),a
    ret

; Freeze or recover the exact batch, upload it, then arm application ownership
; before emitting asynchronous APPLY_AND_RENDER. The first submission consumes
; only the serializer's captured dirty snapshot.
w3d_vdplet_submit_dirty_world_render:
    ld a,W3D_VDPLET_STAGE_RENDER
    ld (w3d_vdplet_stage),a
    call w3d_vdplet_batch_prepare
    ret c
    ld bc,W3D_VDPLET_UPDATE_BUFFER
    call w3d_vdplet_upload_buffer
    ret c
    call w3d_mark_render_submitted
    ret c
    ld bc,W3P_ENTRY_APPLY_AND_RENDER
    ld de,W3D_VDPLET_ARGUMENT_BUFFER
    call w3d_vdplet_send_run
    jr c,@cancel
    call w3d_vdplet_batch_mark_submitted
    W3D_PROFILE_CALL w3d_profile_submitted
    ret
@cancel:
    push af
    call w3d_cancel_render_submission
    pop af
    scf
    ret

; Called only after the interrupt callback publishes a VDPL record. DONE
; commits the frozen generation and uses the common one-C3 event tail. Native
; ERROR releases the render owner without presentation and schedules the exact
; same bytes/purpose for retry. Protocol ambiguity remains fatal and retains
; ownership, matching the standalone fail-closed rule.
w3d_vdplet_consume_render_completion:
    call w3d_vdplet_wait_run
    jr c,@failed
    call w3d_vdplet_batch_accept_success
    jr c,@fatal
    xor a
    ld (w3d_vdplet_render_retry_count),a
    jp w3d_publish_render_completion

@failed:
    ld a,(w3d_vdplet_status)
    cp W3D_VDPLET_STATUS_RUNTIME
    jr nz,@fatal
    ld a,(w3d_vdplet_render_retry_count)
    cp W3D_VDPLET_RENDER_RETRY_LIMIT
    jr nc,@fatal
    inc a
    ld (w3d_vdplet_render_retry_count),a
    call w3d_vdplet_batch_accept_failure
    jr c,@fatal
    ld a,(w3d_render_in_flight_purpose)
    ld (w3d_next_render_purpose),a
    di
    xor a
    ld (w3d_render_in_flight),a
    ld (w3d_async_owner),a
    ei
    inc a
    ld (w3d_world_dirty),a
    ret

@fatal:
    call w3d_vdplet_select_failure_message
    ld a,1
    ld (w3d_callback_error),a
    ld (w3d_exit_requested),a
    ret

; Preserve the exact already-recorded client failure in the text printed after
; the caller's MOS mode is restored. This is intentionally outside the wire
; protocol: it is safe on both stock MOS and the emulator and remains useful
; when the renderer cannot start far enough to draw an error screen.
w3d_vdplet_select_failure_message:
    ld a,(w3d_vdplet_stage)
    ld hl,w3d_vdplet_failure_stage
    call w3d_vdplet_write_hex_byte
    ld a,(w3d_vdplet_status)
    ld hl,w3d_vdplet_failure_status
    call w3d_vdplet_write_hex_byte
    ld a,(w3d_vdplet_last_value+1)
    ld hl,w3d_vdplet_failure_value
    call w3d_vdplet_write_hex_byte
    ld a,(w3d_vdplet_last_value+0)
    ld hl,w3d_vdplet_failure_value+2
    call w3d_vdplet_write_hex_byte
    ld a,(w3d_vdplet_callback_error)
    ld hl,w3d_vdplet_failure_callback
    call w3d_vdplet_write_hex_byte
    ld hl,w3d_vdplet_failure_msg
    ld (w3d_exit_message_ptr),hl
    ret

; A=byte, HL=two-character destination.
w3d_vdplet_write_hex_byte:
    push af
    rrca
    rrca
    rrca
    rrca
    and 0fh
    call w3d_vdplet_hex_nibble
    ld (hl),a
    inc hl
    pop af
    and 0fh
    call w3d_vdplet_hex_nibble
    ld (hl),a
    ret

w3d_vdplet_hex_nibble:
    add a,'0'
    cp '9'+1
    ret c
    add a,'A'-'9'-1
    ret

w3d_vdplet_failure_msg:
    db "VDPlet startup/render failure: stage="
w3d_vdplet_failure_stage:
    db "00 status="
w3d_vdplet_failure_status:
    db "00 value="
w3d_vdplet_failure_value:
    db "0000 callback="
w3d_vdplet_failure_callback:
    db "00",10,0

w3d_vdplet_render_retry_count:
    db 0
w3d_vdplet_fizzle_operation:
    db W3D_VDPLET_FIZZLE_OP_NONE
