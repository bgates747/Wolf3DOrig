; =============================================================================
; Wolf3D logical sound batching and VDP playback transport.
;
; Gameplay calls begin/request/discard-or-flush once per 30 Hz simulation
; quantum.  Only the newest catch-up quantum is flushed.  The queue retains
; the three highest-priority loaded effects; equal priorities retain request
; order.  Playback uses the three default VDP channels in deterministic
; round-robin order and never waits for completion.
;
; Public producer ABI:
;   w3d_audio_begin_quantum
;   w3d_audio_request
;       A = AUDIOWL1 logical sound id (0..68)
;       B = mono gain (0..127; zero is a silent no-op)
;       C = metadata flags (bit 0 positioned; other bits reserved)
;       Carry clear when processed; carry set when inactive/invalid/missing.
;   w3d_audio_discard_quantum
;   w3d_audio_flush_quantum
;
; Loader/lifecycle ABI:
;   w3d_audio_initialize
;   w3d_audio_mark_sample_loaded         A = logical sound id
;   w3d_audio_mark_sample_buffer_loaded  HL = exact 0x5000+logical buffer id
;   w3d_audio_select_transport           A = BUFFERED or DIRECT
;   w3d_audio_install_available_command_buffers
;   w3d_audio_shutdown
;
; IX and IY are preserved by producer/lifecycle entry points.  Other general
; registers are volatile.  The standard buffered playback procedure is:
; reset channel, select sample waveform, play whole sample at full volume.
; Runtime calls that procedure, then sets the requested mono gain while the
; new note is pending.  Direct diagnostic playback sends the same reset,
; waveform and play commands with gain embedded in the play command.
;
; Dependency: generated wolf3d_audio_assets.inc must be included first.  It
; owns the authoritative logical IDs, active AdLib SoundCommon priorities,
; stable buffer ranges, and manifest-derived sample/command table.
; =============================================================================

W3D_AUDIO_FLAG_POSITIONED:     equ 00000001b
W3D_AUDIO_TRANSPORT_BUFFERED:  equ 0
W3D_AUDIO_TRANSPORT_DIRECT:    equ 1

W3D_AUDIO_PENDING_SOUND:       equ 0
W3D_AUDIO_PENDING_GAIN:        equ 1
W3D_AUDIO_PENDING_PRIORITY:    equ 2
W3D_AUDIO_PENDING_ORDER:       equ 3
W3D_AUDIO_PENDING_FLAGS:       equ 4
W3D_AUDIO_PENDING_SIZE:        equ 5

; -----------------------------------------------------------------------------
; Lifecycle and loaded-sample state
; -----------------------------------------------------------------------------

w3d_audio_initialize:
    push ix
    ld hl,w3d_audio_state_begin
    xor a
    ld (hl),a
    ld de,w3d_audio_state_begin+1
    ld bc,w3d_audio_state_end-w3d_audio_state_begin-1
    ldir
    ld a,W3D_AUDIO_TRANSPORT_BUFFERED
    ld (w3d_audio_transport),a
    pop ix
    ret

; A=logical id.  Carry set for an invalid id.
w3d_audio_mark_sample_loaded:
    cp W3D_AUDIO_LOGICAL_COUNT
    jr nc,@invalid
    ld de,0
    ld e,a
    ld hl,w3d_audio_sample_loaded
    add hl,de
    ld (hl),1
    or a
    ret
@invalid:
    scf
    ret

; A=logical id.  Carry set for an invalid id.
w3d_audio_mark_sample_unavailable:
    cp W3D_AUDIO_LOGICAL_COUNT
    jr nc,@invalid
    ld de,0
    ld e,a
    ld hl,w3d_audio_sample_loaded
    add hl,de
    ld (hl),0
    or a
    ret
@invalid:
    scf
    ret

; HL=AGNB buffer id.  Exact stable range is 0x5000..0x5044.
w3d_audio_mark_sample_buffer_loaded:
    ld a,h
    cp W3D_AUDIO_SAMPLE_BUFFER_BASE/256
    jr nz,@invalid
    ld a,l
    cp W3D_AUDIO_LOGICAL_COUNT
    jr nc,@invalid
    jp w3d_audio_mark_sample_loaded
@invalid:
    scf
    ret

; A=logical id -> HL=stable sample buffer id, carry set when invalid.
w3d_audio_get_sample_buffer_id:
    cp W3D_AUDIO_LOGICAL_COUNT
    jr nc,@invalid
    ld de,0
    ld e,a
    ld hl,W3D_AUDIO_SAMPLE_BUFFER_BASE
    add hl,de
    or a
    ret
@invalid:
    ld hl,0ffffh
    scf
    ret

; A=logical id, C=channel -> HL=stable command buffer id.
; Mapping is 0x6000 + logical*3 + channel.
w3d_audio_get_command_buffer_id:
    cp W3D_AUDIO_LOGICAL_COUNT
    jr nc,@invalid
    ld b,a
    ld a,c
    cp W3D_AUDIO_CHANNEL_COUNT
    jr nc,@invalid
    ld de,0
    ld e,b
    ld hl,0
    add hl,de
    add hl,de
    add hl,de
    ld e,c
    ld d,0
    add hl,de
    ld de,W3D_AUDIO_COMMAND_BUFFER_BASE
    add hl,de
    or a
    ret
@invalid:
    ld hl,0ffffh
    scf
    ret

; A=W3D_AUDIO_TRANSPORT_BUFFERED or W3D_AUDIO_TRANSPORT_DIRECT.
w3d_audio_select_transport:
    cp W3D_AUDIO_TRANSPORT_DIRECT+1
    jr nc,@invalid
    ld (w3d_audio_transport),a
    or a
    ret
@invalid:
    scf
    ret

; -----------------------------------------------------------------------------
; Per-quantum request batching
; -----------------------------------------------------------------------------

w3d_audio_begin_quantum:
    push ix
    ld a,(w3d_audio_quantum_active)
    or a
    call nz,w3d_audio_discard_quantum_inner
    ld a,1
    ld (w3d_audio_quantum_active),a
    xor a
    ld (w3d_audio_pending_count),a
    ld (w3d_audio_request_order),a
    ld hl,w3d_audio_begun_quanta
    call w3d_audio_inc_u16
    pop ix
    ret

w3d_audio_request:
    push ix
    call w3d_audio_request_inner
    pop ix
    ret

w3d_audio_request_inner:
    ld (w3d_audio_new_sound),a
    ld a,b
    ld (w3d_audio_new_gain),a
    ld a,c
    ld (w3d_audio_new_flags),a

    ld a,(w3d_audio_quantum_active)
    or a
    jr z,@inactive
    ld a,(w3d_audio_new_sound)
    cp W3D_AUDIO_LOGICAL_COUNT
    jr nc,@invalid
    ld a,(w3d_audio_new_gain)
    or a
    jr z,@silent
    cp 128
    jr c,@gain_ready
    ld a,127
    ld (w3d_audio_new_gain),a
@gain_ready:
    ld a,(w3d_audio_new_sound)
    call w3d_audio_loaded_pointer
    ld a,(hl)
    or a
    jr z,@missing

    ld a,(w3d_audio_new_sound)
    call w3d_audio_asset_pointer
    ld de,W3D_AUDIO_ENTRY_PRIORITY
    add hl,de
    ld a,(hl)
    ld (w3d_audio_new_priority),a
    ld a,(w3d_audio_request_order)
    ld (w3d_audio_new_order),a
    inc a
    ld (w3d_audio_request_order),a
    ld hl,w3d_audio_requested_events
    call w3d_audio_inc_u16
    call w3d_audio_insert_request
    or a
    ret

@inactive:
    ld hl,w3d_audio_inactive_requests
    call w3d_audio_inc_u16
    scf
    ret
@invalid:
    ld hl,w3d_audio_invalid_requests
    call w3d_audio_inc_u16
    scf
    ret
@missing:
    ld hl,w3d_audio_missing_requests
    call w3d_audio_inc_u16
    scf
    ret
@silent:
    ld hl,w3d_audio_silent_requests
    call w3d_audio_inc_u16
    scf
    ret

; A=valid logical id -> HL=&loaded[id].
w3d_audio_loaded_pointer:
    ld de,0
    ld e,a
    ld hl,w3d_audio_sample_loaded
    add hl,de
    ret

; A=valid logical id -> HL=&generated asset table entry.
w3d_audio_asset_pointer:
    ld hl,0
    ld l,a
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    ld de,w3d_audio_asset_table
    add hl,de
    ret

; Retain a descending-priority, stable-tie list of at most three requests.
w3d_audio_insert_request:
    ld a,(w3d_audio_pending_count)
    or a
    jp z,@empty
    cp 1
    jp z,@one
    cp 2
    jp z,@two

; Full queue: every new request displaces one old event or is itself dropped.
    ld hl,w3d_audio_dropped_requests
    call w3d_audio_inc_u16
    ld ix,w3d_audio_pending+0
    ld a,(w3d_audio_new_priority)
    cp (ix+W3D_AUDIO_PENDING_PRIORITY)
    jr z,@full_check_one
    jr c,@full_check_one
    call w3d_audio_copy_entry_1_to_2
    call w3d_audio_copy_entry_0_to_1
    ld ix,w3d_audio_pending+0
    jp w3d_audio_store_new_entry
@full_check_one:
    ld ix,w3d_audio_pending+5
    ld a,(w3d_audio_new_priority)
    cp (ix+W3D_AUDIO_PENDING_PRIORITY)
    jr z,@full_check_two
    jr c,@full_check_two
    call w3d_audio_copy_entry_1_to_2
    ld ix,w3d_audio_pending+5
    jp w3d_audio_store_new_entry
@full_check_two:
    ld ix,w3d_audio_pending+10
    ld a,(w3d_audio_new_priority)
    cp (ix+W3D_AUDIO_PENDING_PRIORITY)
    ret z
    ret c
    jp w3d_audio_store_new_entry

@two:
    ld ix,w3d_audio_pending+0
    ld a,(w3d_audio_new_priority)
    cp (ix+W3D_AUDIO_PENDING_PRIORITY)
    jr z,@two_check_one
    jr c,@two_check_one
    call w3d_audio_copy_entry_1_to_2
    call w3d_audio_copy_entry_0_to_1
    ld ix,w3d_audio_pending+0
    jr @grow_to_three
@two_check_one:
    ld ix,w3d_audio_pending+5
    ld a,(w3d_audio_new_priority)
    cp (ix+W3D_AUDIO_PENDING_PRIORITY)
    jr z,@two_append
    jr c,@two_append
    call w3d_audio_copy_entry_1_to_2
    ld ix,w3d_audio_pending+5
    jr @grow_to_three
@two_append:
    ld ix,w3d_audio_pending+10
@grow_to_three:
    call w3d_audio_store_new_entry
    ld a,3
    ld (w3d_audio_pending_count),a
    ret

@one:
    ld ix,w3d_audio_pending+0
    ld a,(w3d_audio_new_priority)
    cp (ix+W3D_AUDIO_PENDING_PRIORITY)
    jr z,@one_append
    jr c,@one_append
    call w3d_audio_copy_entry_0_to_1
    ld ix,w3d_audio_pending+0
    jr @grow_to_two
@one_append:
    ld ix,w3d_audio_pending+5
@grow_to_two:
    call w3d_audio_store_new_entry
    ld a,2
    ld (w3d_audio_pending_count),a
    ret

@empty:
    ld ix,w3d_audio_pending
    call w3d_audio_store_new_entry
    ld a,1
    ld (w3d_audio_pending_count),a
    ret

w3d_audio_store_new_entry:
    ld a,(w3d_audio_new_sound)
    ld (ix+W3D_AUDIO_PENDING_SOUND),a
    ld a,(w3d_audio_new_gain)
    ld (ix+W3D_AUDIO_PENDING_GAIN),a
    ld a,(w3d_audio_new_priority)
    ld (ix+W3D_AUDIO_PENDING_PRIORITY),a
    ld a,(w3d_audio_new_order)
    ld (ix+W3D_AUDIO_PENDING_ORDER),a
    ld a,(w3d_audio_new_flags)
    ld (ix+W3D_AUDIO_PENDING_FLAGS),a
    ret

w3d_audio_copy_entry_0_to_1:
    ld hl,w3d_audio_pending+0
    ld de,w3d_audio_pending+5
    ld bc,W3D_AUDIO_PENDING_SIZE
    ldir
    ret

w3d_audio_copy_entry_1_to_2:
    ld hl,w3d_audio_pending+5
    ld de,w3d_audio_pending+10
    ld bc,W3D_AUDIO_PENDING_SIZE
    ldir
    ret

w3d_audio_discard_quantum:
    push ix
    call w3d_audio_discard_quantum_inner
    pop ix
    ret

w3d_audio_discard_quantum_inner:
    ld a,(w3d_audio_quantum_active)
    or a
    ret z
    ld a,(w3d_audio_pending_count)
    ld hl,w3d_audio_discarded_events
    call w3d_audio_add_u16_a
    ld hl,w3d_audio_discarded_quanta
    call w3d_audio_inc_u16
    xor a
    ld (w3d_audio_pending_count),a
    ld (w3d_audio_quantum_active),a
    ret

w3d_audio_flush_quantum:
    push ix
    ld a,(w3d_audio_quantum_active)
    or a
    jr z,@done
    ld a,(w3d_audio_pending_count)
    ld (w3d_audio_last_flush_count),a
    or a
    jr z,@close
    ld b,a
    ld ix,w3d_audio_pending
@loop:
    push bc
    ld b,(ix+W3D_AUDIO_PENDING_GAIN)
    ld a,(w3d_audio_next_channel)
    ld c,a
    ld a,(ix+W3D_AUDIO_PENDING_SOUND)
    call w3d_audio_emit_event
    pop bc
    lea ix,ix+W3D_AUDIO_PENDING_SIZE
    djnz @loop
@close:
    ld hl,w3d_audio_flushed_quanta
    call w3d_audio_inc_u16
    xor a
    ld (w3d_audio_pending_count),a
    ld (w3d_audio_quantum_active),a
@done:
    pop ix
    ret

; -----------------------------------------------------------------------------
; Playback transport
; -----------------------------------------------------------------------------

; A=logical id, B=gain, C=channel.  Rechecks loaded state before wire output.
w3d_audio_emit_event:
    ld (w3d_audio_emit_sound),a
    ld a,b
    ld (w3d_audio_emit_gain),a
    ld a,c
    ld (w3d_audio_emit_channel),a
    ld a,(w3d_audio_emit_sound)
    call w3d_audio_loaded_pointer
    ld a,(hl)
    or a
    jr z,@missing
    ld a,(w3d_audio_transport)
    cp W3D_AUDIO_TRANSPORT_DIRECT
    jr z,@direct
    call w3d_audio_emit_buffered
    jr @emitted
@direct:
    call w3d_audio_emit_direct
@emitted:
    ld hl,w3d_audio_emitted_events
    call w3d_audio_inc_u16
    ld a,(w3d_audio_next_channel)
    inc a
    cp W3D_AUDIO_CHANNEL_COUNT
    jr c,@store_channel
    xor a
@store_channel:
    ld (w3d_audio_next_channel),a
    or a
    ret
@missing:
    ld hl,w3d_audio_missing_dispatches
    call w3d_audio_inc_u16
    scf
    ret

; Buffered runtime path: six-byte call followed by six-byte volume adjustment.
w3d_audio_emit_buffered:
    ld a,(w3d_audio_emit_channel)
    ld c,a
    ld a,(w3d_audio_emit_sound)
    call w3d_audio_get_command_buffer_id
    ld a,l
    ld (w3d_audio_buffered_call_id+0),a
    ld a,h
    ld (w3d_audio_buffered_call_id+1),a
    ld a,(w3d_audio_emit_channel)
    ld (w3d_audio_buffered_volume_channel),a
    ld a,(w3d_audio_emit_gain)
    ld (w3d_audio_buffered_volume_gain),a
    ld hl,w3d_audio_buffered_call
    ld bc,w3d_audio_buffered_call_end-w3d_audio_buffered_call
    call w3d_audio_send_bytes
    ld hl,w3d_audio_buffered_volume
    ld bc,w3d_audio_buffered_volume_end-w3d_audio_buffered_volume
    call w3d_audio_send_bytes
    ld a,12
    ld hl,w3d_audio_runtime_uart_bytes
    jp w3d_audio_add_u32_a

w3d_audio_buffered_call:
    db 23,0,0a0h
w3d_audio_buffered_call_id:
    dw 0
    db 1
w3d_audio_buffered_call_end:
w3d_audio_buffered_volume:
    db 23,0,085h
w3d_audio_buffered_volume_channel:
    db 0
    db 2
w3d_audio_buffered_volume_gain:
    db 0
w3d_audio_buffered_volume_end:

; Direct diagnostic path: reset, set sample waveform, play complete sample.
w3d_audio_emit_direct:
    ld a,(w3d_audio_emit_channel)
    ld (w3d_audio_direct_reset_channel),a
    ld (w3d_audio_direct_wave_channel),a
    ld (w3d_audio_direct_play_channel),a
    ld a,(w3d_audio_emit_sound)
    call w3d_audio_get_sample_buffer_id
    ld a,l
    ld (w3d_audio_direct_sample_id+0),a
    ld a,h
    ld (w3d_audio_direct_sample_id+1),a
    ld a,(w3d_audio_emit_gain)
    ld (w3d_audio_direct_gain),a
    ld hl,w3d_audio_direct_commands
    ld bc,w3d_audio_direct_commands_end-w3d_audio_direct_commands
    call w3d_audio_send_bytes
    ld a,23
    ld hl,w3d_audio_runtime_uart_bytes
    jp w3d_audio_add_u32_a

w3d_audio_direct_commands:
    db 23,0,085h
w3d_audio_direct_reset_channel:
    db 0
    db 10
    db 23,0,085h
w3d_audio_direct_wave_channel:
    db 0
    db 4,8
w3d_audio_direct_sample_id:
    dw 0
    db 23,0,085h
w3d_audio_direct_play_channel:
    db 0
    db 0
w3d_audio_direct_gain:
    db 0
    dw 0,0
w3d_audio_direct_commands_end:

; Upload reset/waveform/play procedures for every loaded logical sample and
; each of the three default channels.  Zero/partial loaded sets are valid.
; Buffered op 0 appends, so every target is cleared first; rerunning setup is
; idempotent instead of concatenating another playback procedure.
w3d_audio_install_available_command_buffers:
    push ix
    xor a
    ld (w3d_audio_install_sound),a
@sound_loop:
    ld a,(w3d_audio_install_sound)
    call w3d_audio_loaded_pointer
    ld a,(hl)
    or a
    jr z,@next_sound
    xor a
    ld (w3d_audio_install_channel),a
@channel_loop:
    ld a,(w3d_audio_install_sound)
    ld a,(w3d_audio_install_channel)
    ld c,a
    ld a,(w3d_audio_install_sound)
    call w3d_audio_install_command_buffer
    ld a,(w3d_audio_install_channel)
    inc a
    ld (w3d_audio_install_channel),a
    cp W3D_AUDIO_CHANNEL_COUNT
    jr c,@channel_loop
@next_sound:
    ld a,(w3d_audio_install_sound)
    inc a
    ld (w3d_audio_install_sound),a
    cp W3D_AUDIO_LOGICAL_COUNT
    jr c,@sound_loop
    pop ix
    ret

; A=logical id, C=channel; uploads one 23-byte command procedure.
w3d_audio_install_command_buffer:
    ld (w3d_audio_install_sound),a
    ld a,c
    ld (w3d_audio_install_channel),a
    ld a,(w3d_audio_install_sound)
    ld a,(w3d_audio_install_channel)
    ld c,a
    ld a,(w3d_audio_install_sound)
    call w3d_audio_get_command_buffer_id
    ret c
    ld a,l
    ld (w3d_audio_clear_command_id+0),a
    ld (w3d_audio_upload_command_id+0),a
    ld a,h
    ld (w3d_audio_clear_command_id+1),a
    ld (w3d_audio_upload_command_id+1),a
    ld a,(w3d_audio_install_sound)
    call w3d_audio_get_sample_buffer_id
    ret c
    ld a,l
    ld (w3d_audio_procedure_sample_id+0),a
    ld a,h
    ld (w3d_audio_procedure_sample_id+1),a
    ld a,(w3d_audio_install_channel)
    ld (w3d_audio_procedure_reset_channel),a
    ld (w3d_audio_procedure_wave_channel),a
    ld (w3d_audio_procedure_play_channel),a
    ld hl,w3d_audio_clear_command
    ld bc,w3d_audio_clear_command_end-w3d_audio_clear_command
    call w3d_audio_send_bytes
    ld hl,w3d_audio_upload_header
    ld bc,w3d_audio_upload_header_end-w3d_audio_upload_header
    call w3d_audio_send_bytes
    ld hl,w3d_audio_procedure
    ld bc,w3d_audio_procedure_end-w3d_audio_procedure
    call w3d_audio_send_bytes
    ld a,37
    ld hl,w3d_audio_setup_uart_bytes
    call w3d_audio_add_u32_a
    ld hl,w3d_audio_installed_commands
    call w3d_audio_inc_u16
    or a
    ret

w3d_audio_clear_command:
    db 23,0,0a0h
w3d_audio_clear_command_id:
    dw 0
    db 2
w3d_audio_clear_command_end:

w3d_audio_upload_header:
    db 23,0,0a0h
w3d_audio_upload_command_id:
    dw 0
    db 0
    dw w3d_audio_procedure_end-w3d_audio_procedure
w3d_audio_upload_header_end:

w3d_audio_procedure:
    db 23,0,085h
w3d_audio_procedure_reset_channel:
    db 0
    db 10
    db 23,0,085h
w3d_audio_procedure_wave_channel:
    db 0
    db 4,8
w3d_audio_procedure_sample_id:
    dw 0
    db 23,0,085h
w3d_audio_procedure_play_channel:
    db 0
    db 0,127
    dw 0,0
w3d_audio_procedure_end:

; Stop current effects without disabling the VDP's three default channels.
; Diagnostics remain readable; loaded state is cleared after the wire reset.
w3d_audio_shutdown:
    push ix
    call w3d_audio_discard_quantum_inner
    xor a
    ld (w3d_audio_shutdown_channel),a
@loop:
    ld a,(w3d_audio_shutdown_channel)
    ld (w3d_audio_shutdown_command_channel),a
    ld hl,w3d_audio_shutdown_command
    ld bc,w3d_audio_shutdown_command_end-w3d_audio_shutdown_command
    call w3d_audio_send_bytes
    ld a,5
    ld hl,w3d_audio_shutdown_uart_bytes
    call w3d_audio_add_u32_a
    ld a,(w3d_audio_shutdown_channel)
    inc a
    ld (w3d_audio_shutdown_channel),a
    cp W3D_AUDIO_CHANNEL_COUNT
    jr c,@loop
    xor a
    ld hl,w3d_audio_sample_loaded
    ld (hl),a
    ld de,w3d_audio_sample_loaded+1
    ld bc,W3D_AUDIO_LOGICAL_COUNT-1
    ldir
    pop ix
    ret

w3d_audio_shutdown_command:
    db 23,0,085h
w3d_audio_shutdown_command_channel:
    db 0
    db 10
w3d_audio_shutdown_command_end:

; -----------------------------------------------------------------------------
; Output seam and diagnostic helpers
; -----------------------------------------------------------------------------

; Normal mode sends HL/BC directly to MOS.  A regression may call
; w3d_audio_capture_start with HL=destination and DE=u16 capacity; capture then
; replaces physical VDU output without changing generated command bytes.
w3d_audio_send_bytes:
    ld a,(w3d_audio_capture_enabled)
    or a
    jr nz,w3d_audio_capture_bytes
    rst.lil 018h
    ret

w3d_audio_capture_start:
    ld (w3d_audio_capture_write),hl
    ld a,e
    ld (w3d_audio_capture_remaining+0),a
    ld a,d
    ld (w3d_audio_capture_remaining+1),a
    xor a
    ld (w3d_audio_capture_length+0),a
    ld (w3d_audio_capture_length+1),a
    ld (w3d_audio_capture_overflow),a
    inc a
    ld (w3d_audio_capture_enabled),a
    ret

w3d_audio_capture_stop:
    xor a
    ld (w3d_audio_capture_enabled),a
    ret

w3d_audio_capture_bytes:
    push ix
    ld ix,(w3d_audio_capture_write)
@loop:
    ld a,b
    or c
    jr z,@done
    ld a,(w3d_audio_capture_remaining+0)
    ld e,a
    ld a,(w3d_audio_capture_remaining+1)
    or e
    jr z,@overflow
    ld a,(hl)
    ld (ix+0),a
    inc hl
    inc ix
    ld a,(w3d_audio_capture_remaining+0)
    sub 1
    ld (w3d_audio_capture_remaining+0),a
    ld a,(w3d_audio_capture_remaining+1)
    sbc a,0
    ld (w3d_audio_capture_remaining+1),a
    ld a,(w3d_audio_capture_length+0)
    inc a
    ld (w3d_audio_capture_length+0),a
    jr nz,@next
    ld a,(w3d_audio_capture_length+1)
    inc a
    ld (w3d_audio_capture_length+1),a
@next:
    dec.s bc
    jr @loop
@overflow:
    ld a,1
    ld (w3d_audio_capture_overflow),a
@done:
    ld (w3d_audio_capture_write),ix
    pop ix
    ret

; HL=u16 counter.
w3d_audio_inc_u16:
    inc (hl)
    ret nz
    inc hl
    inc (hl)
    ret

; HL=u16 counter, A=small addend.
w3d_audio_add_u16_a:
    ld e,a
    ld a,(hl)
    add a,e
    ld (hl),a
    ret nc
    inc hl
    inc (hl)
    ret

; HL=u32 counter, A=small addend.
w3d_audio_add_u32_a:
    ld e,a
    ld a,(hl)
    add a,e
    ld (hl),a
    ret nc
    inc hl
    inc (hl)
    ret nz
    inc hl
    inc (hl)
    ret nz
    inc hl
    inc (hl)
    ret

; -----------------------------------------------------------------------------
; Mutable service state and diagnostics
; -----------------------------------------------------------------------------

w3d_audio_state_begin:
w3d_audio_sample_loaded:
    ds W3D_AUDIO_LOGICAL_COUNT
w3d_audio_pending:
    ds W3D_AUDIO_CHANNEL_COUNT*W3D_AUDIO_PENDING_SIZE
w3d_audio_pending_count:
    db 0
w3d_audio_quantum_active:
    db 0
w3d_audio_request_order:
    db 0
w3d_audio_next_channel:
    db 0
w3d_audio_transport:
    db W3D_AUDIO_TRANSPORT_BUFFERED
w3d_audio_last_flush_count:
    db 0

; Request/emit scratch.
w3d_audio_new_sound:          db 0
w3d_audio_new_gain:           db 0
w3d_audio_new_priority:       db 0
w3d_audio_new_order:          db 0
w3d_audio_new_flags:          db 0
w3d_audio_emit_sound:         db 0
w3d_audio_emit_gain:          db 0
w3d_audio_emit_channel:       db 0
w3d_audio_install_sound:      db 0
w3d_audio_install_channel:    db 0
w3d_audio_shutdown_channel:   db 0

; Counts are intentionally writable/readable diagnostics for tests and HUD
; profiling.  UART totals count eZ80-to-VDP bytes, not VDP internal calls.
w3d_audio_begun_quanta:       dw 0
w3d_audio_flushed_quanta:     dw 0
w3d_audio_discarded_quanta:   dw 0
w3d_audio_requested_events:   dw 0
w3d_audio_emitted_events:     dw 0
w3d_audio_dropped_requests:   dw 0
w3d_audio_discarded_events:   dw 0
w3d_audio_missing_requests:   dw 0
w3d_audio_missing_dispatches: dw 0
w3d_audio_invalid_requests:   dw 0
w3d_audio_inactive_requests:  dw 0
w3d_audio_silent_requests:    dw 0
w3d_audio_installed_commands: dw 0
w3d_audio_runtime_uart_bytes: ds 4
w3d_audio_setup_uart_bytes:   ds 4
w3d_audio_shutdown_uart_bytes: ds 4

; Optional test capture sink.  Production leaves enabled=0.
w3d_audio_capture_enabled:    db 0
w3d_audio_capture_write:      dl 0
w3d_audio_capture_remaining:  dw 0
                              db 0
w3d_audio_capture_length:     dw 0
w3d_audio_capture_overflow:   db 0
w3d_audio_state_end:
