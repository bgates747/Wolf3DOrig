; =============================================================================
; Non-blocking IMF-derived music sequencer.
;
; The generated streams retain every OPL2 register write and use cumulative
; 120-Hz delays derived from the original 700-Hz IMF clock.  Nine OPL voices
; map to VDP channels 3..11, leaving the accepted digitized-SFX pool on 0..2.
; OPL frequency, carrier level and waveform writes are translated to the VDP's
; oscillator API.  This deliberately preserves melody, rhythm, voice count,
; looping and source assignments while approximating the unavailable two-
; operator FM timbre with the VDP's four native waveforms.
;
; Public ABI:
;   w3d_music_initialize
;   w3d_music_start          A=music id
;   w3d_music_service        call freely; MOS 120-Hz clock owns cadence
;   w3d_music_pause          silence and freeze the current sequencer position
;   w3d_music_resume         resume a paused track without restarting it
;   w3d_music_stop
;   w3d_music_shutdown
;   w3d_music_start_current_floor
;
; All public entry points preserve IX/IY. Service preserves every GP register.
; =============================================================================

W3D_MUSIC_CHANNEL_BASE:      equ 3
W3D_MUSIC_VOICE_COUNT:       equ 9
W3D_MUSIC_MAX_VOLUME:        equ 48
W3D_MUSIC_INVALID_VOICE:     equ 0ffh

w3d_music_initialize:
    push ix
    ld a,1
    ld (w3d_music_enabled),a
    xor a
    ld (w3d_music_active),a
    ld (w3d_music_paused),a
    ld (w3d_music_initialized),a
    ld (w3d_music_capture_enabled),a
    ld (w3d_music_current_id),a
    ld hl,w3d_music_registers
    ld (hl),a
    ld de,w3d_music_registers+1
    ld bc,255
    ldir
    pop ix
    ret

; A=canonical music id. Carry set when unavailable/invalid.
w3d_music_start:
    push ix
    push iy
    ld (w3d_music_requested_id),a
    call w3d_music_stop_inner
    ld a,(w3d_music_requested_id)
    cp W3D_MUSIC_COUNT
    jr nc,@invalid
    ld de,0
    ld e,a
    ld hl,0
    ld l,a
    add hl,hl
    add hl,de                    ; id*3
    ld de,w3d_music_track_table
    add hl,de
    ld hl,(hl)
    ld de,0
    or a
    sbc hl,de
    jr z,@invalid
    ld (w3d_music_track_start),hl
    ld a,(w3d_music_requested_id)
    ld (w3d_music_current_id),a
    ld a,(w3d_music_enabled)
    or a
    jr z,@muted
    call w3d_music_enable_channels
    call w3d_music_restart_track
    ld a,1
    ld (w3d_music_active),a
    call w3d_music_service_inner
    pop iy
    pop ix
    or a
    ret
@muted:
    pop iy
    pop ix
    or a
    ret
@invalid:
    pop iy
    pop ix
    scf
    ret

; A=0 disables and silences music. Any nonzero value enables future starts;
; the shell caller deliberately chooses which context track should resume.
w3d_music_set_enabled:
    or a
    jr z,@disable
    ld a,1
    ld (w3d_music_enabled),a
    ret
@disable:
    ld (w3d_music_enabled),a
    jp w3d_music_stop

w3d_music_stop:
    push ix
    push iy
    call w3d_music_stop_inner
    pop iy
    pop ix
    ret

w3d_music_stop_inner:
    xor a
    ld (w3d_music_active),a
    ld (w3d_music_paused),a
    jp w3d_music_reset_voices

; Match SD_MusicOff/SD_MusicOn as used by CheckPause: process everything due
; at the pause boundary, silence live channels without discarding the IMF
; cursor/register shadow, then remove the wall-clock gap when resuming.
w3d_music_pause:
    push ix
    push iy
    ld a,(w3d_music_active)
    or a
    jr z,@done
    call w3d_music_service_inner
    ld ix,(w3d_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld (w3d_music_paused_at),hl
    xor a
    ld (w3d_music_active),a
    inc a
    ld (w3d_music_paused),a
    call w3d_music_reset_voices
; SD_MusicOff writes zero to every OPL B0 key-on register. Mirror that hardware
; state in the sequencer shadow so the next continuing IMF B0 write with bit 5
; set is classified as a fresh key edge and restarts the native oscillator.
    ld hl,w3d_music_registers+0b0h
    ld b,W3D_MUSIC_VOICE_COUNT
    xor a
@clear_key_on:
    ld (hl),a
    inc hl
    djnz @clear_key_on
@done:
    pop iy
    pop ix
    ret

w3d_music_resume:
    push ix
    push iy
    ld a,(w3d_music_paused)
    or a
    jr z,@done
    ld a,(w3d_music_enabled)
    or a
    jr z,@discard

; Shift the scheduler epoch by the paused duration.  IMF due times and cursor
; remain untouched, so the first post-resume service sees the same elapsed
; music time it saw at the pause boundary.
    ld ix,(w3d_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld de,(w3d_music_paused_at)
    or a
    sbc.s hl,de
    ld de,(w3d_music_started_at)
    add.s hl,de
    ld (w3d_music_started_at),hl
    call w3d_music_enable_channels

; ID_SD.C::SD_MusicOn only sets sqActive again. SD_MusicOff wrote zero to
; every OPL key-on register, so any note held across Pause remains silent until
; the continuing IMF stream reaches a later key edge. Preserve the cursor and
; non-key register shadow, but do not re-key native voices here.
    ld a,1
    ld (w3d_music_active),a
@discard:
    xor a
    ld (w3d_music_paused),a
@done:
    pop iy
    pop ix
    ret

w3d_music_shutdown:
    push ix
    push iy
    call w3d_music_stop_inner
    ld a,(w3d_music_initialized)
    or a
    jr z,@done
    ld a,W3D_MUSIC_CHANNEL_BASE
@disable:
    ld (w3d_music_channel_command_channel),a
    ld a,9
    ld (w3d_music_channel_command_action),a
    ld hl,w3d_music_channel_command
    ld bc,w3d_music_channel_command_end-w3d_music_channel_command
    call w3d_music_send_bytes
    ld a,(w3d_music_channel_command_channel)
    inc a
    cp W3D_MUSIC_CHANNEL_BASE+W3D_MUSIC_VOICE_COUNT
    jr c,@disable
    xor a
    ld (w3d_music_initialized),a
@done:
    pop iy
    pop ix
    ret

; Select the original Episode 1 GetLevelMusic[] assignment from the current
; zero-based floor.  The secret floor is entry 9, just as it is in the source
; table.  Invalid/injected levels stop music rather than indexing adjacent
; application data.
w3d_music_start_current_floor:
    ld a,(w3d_level_requested_index)
    cp 10
    jr nc,@invalid
    ld de,0
    ld e,a
    ld hl,w3d_music_episode1_floor_tracks
    add hl,de
    ld a,(hl)
    jp w3d_music_start
@invalid:
    call w3d_music_stop
    scf
    ret

w3d_music_enable_channels:
    ld a,(w3d_music_initialized)
    or a
    ret nz
    ld a,W3D_MUSIC_CHANNEL_BASE
@enable:
    ld (w3d_music_channel_command_channel),a
    ld a,8
    ld (w3d_music_channel_command_action),a
    ld hl,w3d_music_channel_command
    ld bc,w3d_music_channel_command_end-w3d_music_channel_command
    call w3d_music_send_bytes
    ld a,(w3d_music_channel_command_channel)
    inc a
    cp W3D_MUSIC_CHANNEL_BASE+W3D_MUSIC_VOICE_COUNT
    jr c,@enable
    ld a,1
    ld (w3d_music_initialized),a
    ret

; Preserve all caller-visible registers so this can be attached to shell input
; polls, asset callbacks and the gameplay foreground without hidden coupling.
w3d_music_service:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_music_service_inner
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

w3d_music_service_inner:
    ld a,(w3d_music_active)
    or a
    ret z
    ld ix,(w3d_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld de,(w3d_music_started_at)
    or a
    sbc.s hl,de
    ld (w3d_music_elapsed),hl
@event_loop:
    ld a,(w3d_music_events_remaining+0)
    ld b,a
    ld a,(w3d_music_events_remaining+1)
    or b
    jr nz,@have_event
    ld hl,(w3d_music_elapsed)
    ld de,(w3d_music_next_due)
    or a
    sbc.s hl,de
    ret c
    ld hl,(w3d_music_started_at)
    ld de,(w3d_music_loop_ticks)
    add.s hl,de
    ld (w3d_music_started_at),hl
    ld hl,(w3d_music_elapsed)
    or a
    sbc.s hl,de
    ld (w3d_music_elapsed),hl
    call w3d_music_reset_voices
    call w3d_music_restart_track_cursor
    jp @event_loop
@have_event:
    ld hl,(w3d_music_elapsed)
    ld de,(w3d_music_next_due)
    or a
    sbc.s hl,de
    ret c

    ld iy,(w3d_music_cursor)
    ld a,(iy+0)
    ld (w3d_music_event_register),a
    ld a,(iy+1)
    ld (w3d_music_event_value),a
    ld de,0
    ld e,(iy+2)
    ld d,(iy+3)
    lea iy,iy+4
    ld (w3d_music_cursor),iy
    ld hl,(w3d_music_next_due)
    add.s hl,de
    ld (w3d_music_next_due),hl
    ld hl,w3d_music_events_remaining
    ld a,(hl)
    sub 1
    ld (hl),a
    inc hl
    ld a,(hl)
    sbc a,0
    ld (hl),a
    call w3d_music_apply_event
    jp @event_loop

w3d_music_restart_track:
    ld ix,(w3d_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld (w3d_music_started_at),hl
    call w3d_music_reset_voices
w3d_music_restart_track_cursor:
    ld iy,(w3d_music_track_start)
    ld a,(iy+0)
    ld (w3d_music_events_remaining+0),a
    ld a,(iy+1)
    ld (w3d_music_events_remaining+1),a
    ld a,(iy+2)
    ld (w3d_music_loop_ticks+0),a
    ld a,(iy+3)
    ld (w3d_music_loop_ticks+1),a
    lea iy,iy+4
    ld (w3d_music_cursor),iy
    xor a
    ld (w3d_music_next_due+0),a
    ld (w3d_music_next_due+1),a
    ld hl,w3d_music_registers
    ld (hl),a
    ld de,w3d_music_registers+1
    ld bc,255
    ldir
    ret

; Store the OPL register first, then reflect the subset which affects a live
; oscillator. Setup-only operator writes remain in the shadow for key-on.
w3d_music_apply_event:
    ld a,(w3d_music_event_register)
    ld de,0
    ld e,a
    ld hl,w3d_music_registers
    add hl,de
    ld a,(hl)
    ld (w3d_music_old_value),a
    ld a,(w3d_music_event_value)
    ld (hl),a

    ld a,(w3d_music_event_register)
    cp 0a0h
    jr c,@carrier_level
    cp 0a9h
    jr c,@frequency_low
    cp 0b0h
    jr c,@carrier_level
    cp 0b9h
    jr c,@key_frequency
@carrier_level:
    ld a,(w3d_music_event_register)
    cp 040h
    jr c,@carrier_wave
    cp 056h
    jr nc,@carrier_wave
    sub 040h
    call w3d_music_operator_voice
    cp W3D_MUSIC_INVALID_VOICE
    ret z
    ld (w3d_music_voice),a
    call w3d_music_voice_is_on
    ret z
    jp w3d_music_set_voice_volume
@carrier_wave:
    ld a,(w3d_music_event_register)
    cp 0e0h
    ret c
    cp 0f6h
    ret nc
    sub 0e0h
    call w3d_music_operator_voice
    cp W3D_MUSIC_INVALID_VOICE
    ret z
    ld (w3d_music_voice),a
    call w3d_music_voice_is_on
    ret z
    jp w3d_music_set_voice_waveform

@frequency_low:
    sub 0a0h
    ld (w3d_music_voice),a
    call w3d_music_voice_is_on
    ret z
    jp w3d_music_set_voice_frequency

@key_frequency:
    sub 0b0h
    ld (w3d_music_voice),a
    ld a,(w3d_music_old_value)
    bit 5,a
    jr z,@old_off
    ld a,(w3d_music_event_value)
    bit 5,a
    jp z,w3d_music_reset_voice
    jp w3d_music_set_voice_frequency
@old_off:
    ld a,(w3d_music_event_value)
    bit 5,a
    ret z
    jp w3d_music_start_voice

; A=operator offset 0..21 -> A=carrier voice or FF.
w3d_music_operator_voice:
    cp 22
    jr nc,@invalid
    ld de,0
    ld e,a
    ld hl,w3d_music_carrier_voice_table
    add hl,de
    ld a,(hl)
    ret
@invalid:
    ld a,W3D_MUSIC_INVALID_VOICE
    ret

; Uses w3d_music_voice. Returns Z when off.
w3d_music_voice_is_on:
    ld a,(w3d_music_voice)
    ld de,0
    ld e,a
    ld hl,w3d_music_registers+0b0h
    add hl,de
    bit 5,(hl)
    ret

w3d_music_start_voice:
    call w3d_music_reset_voice
    call w3d_music_set_voice_waveform
    call w3d_music_calculate_frequency
    ld a,e
    ld (w3d_music_play_frequency+0),a
    ld a,d
    ld (w3d_music_play_frequency+1),a
    call w3d_music_calculate_volume
    ld (w3d_music_play_volume),a
    call w3d_music_publish_channel
    ld a,(w3d_music_channel)
    ld (w3d_music_play_channel),a
    ld hl,w3d_music_play_command
    ld bc,w3d_music_play_command_end-w3d_music_play_command
    jp w3d_music_send_bytes

w3d_music_reset_voices:
    xor a
    ld (w3d_music_voice),a
@loop:
    call w3d_music_reset_voice
    ld a,(w3d_music_voice)
    inc a
    ld (w3d_music_voice),a
    cp W3D_MUSIC_VOICE_COUNT
    jr c,@loop
    ret

w3d_music_reset_voice:
    call w3d_music_publish_channel
    ld a,(w3d_music_channel)
    ld (w3d_music_reset_channel),a
    ld hl,w3d_music_reset_command
    ld bc,w3d_music_reset_command_end-w3d_music_reset_command
    jp w3d_music_send_bytes

w3d_music_set_voice_frequency:
    call w3d_music_calculate_frequency
    ld a,e
    ld (w3d_music_frequency_value+0),a
    ld a,d
    ld (w3d_music_frequency_value+1),a
    call w3d_music_publish_channel
    ld a,(w3d_music_channel)
    ld (w3d_music_frequency_channel),a
    ld hl,w3d_music_frequency_command
    ld bc,w3d_music_frequency_command_end-w3d_music_frequency_command
    jp w3d_music_send_bytes

w3d_music_set_voice_volume:
    call w3d_music_calculate_volume
    ld (w3d_music_volume_value),a
    call w3d_music_publish_channel
    ld a,(w3d_music_channel)
    ld (w3d_music_volume_channel),a
    ld hl,w3d_music_volume_command
    ld bc,w3d_music_volume_command_end-w3d_music_volume_command
    jp w3d_music_send_bytes

w3d_music_set_voice_waveform:
    ld a,(w3d_music_voice)
    ld de,0
    ld e,a
    ld hl,w3d_music_carrier_offsets
    add hl,de
    ld a,(hl)
    ld de,0
    ld e,a
    ld hl,w3d_music_registers+0e0h
    add hl,de
    ld a,(hl)
    and 3
    ld de,0
    ld e,a
    ld hl,w3d_music_waveform_table
    add hl,de
    ld a,(hl)
    ld (w3d_music_waveform_value),a
    call w3d_music_publish_channel
    ld a,(w3d_music_channel)
    ld (w3d_music_waveform_channel),a
    ld hl,w3d_music_waveform_command
    ld bc,w3d_music_waveform_command_end-w3d_music_waveform_command
    jp w3d_music_send_bytes

; FNUM/block -> integer Hz using the documented OPL relation
; f = fnum*49716 / 2^(20-block). Returns DE, clamped to at least 1 Hz.
w3d_music_calculate_frequency:
    ld a,(w3d_music_voice)
    ld bc,0
    ld c,a
    ld hl,w3d_music_registers+0a0h
    add hl,bc
    ld e,(hl)
    ld hl,w3d_music_registers+0b0h
    add hl,bc
    ld a,(hl)
    ld d,a
    and 3
    ld h,a
    ld l,e
    ld de,49716
    call w3d_umul16x16_32
    ld a,(w3d_music_voice)
    ld bc,0
    ld c,a
    push hl
    ld hl,w3d_music_registers+0b0h
    add hl,bc
    ld a,(hl)
    pop hl
    srl a
    srl a
    and 7
    ld b,20
    sub b
    neg
    ld b,a
@shift:
    srl h
    rr l
    rr d
    rr e
    djnz @shift
    ld a,d
    or e
    ret nz
    ld de,1
    ret

w3d_music_calculate_volume:
    ld a,(w3d_music_voice)
    ld de,0
    ld e,a
    ld hl,w3d_music_carrier_offsets
    add hl,de
    ld a,(hl)
    ld de,0
    ld e,a
    ld hl,w3d_music_registers+040h
    add hl,de
    ld a,(hl)
    and 63
    ld de,0
    ld e,a
    ld hl,w3d_music_volume_table
    add hl,de
    ld a,(hl)
    ret

w3d_music_publish_channel:
    ld a,(w3d_music_voice)
    add a,W3D_MUSIC_CHANNEL_BASE
    ld (w3d_music_channel),a
    ret

; Regression seam -----------------------------------------------------------

w3d_music_capture_start:
    ld (w3d_music_capture_write),hl
    ld (w3d_music_capture_remaining),de
    xor a
    ld (w3d_music_capture_overflow),a
    ld a,1
    ld (w3d_music_capture_enabled),a
    ret

w3d_music_capture_stop:
    xor a
    ld (w3d_music_capture_enabled),a
    ret

w3d_music_send_bytes:
    ld a,(w3d_music_capture_enabled)
    or a
    jr nz,@capture
    rst.lil 018h
    ret
@capture:
    ld de,(w3d_music_capture_remaining)
    push hl
    push bc
    or a
    ex de,hl
    sbc.s hl,bc
    jr c,@overflow
    ld (w3d_music_capture_remaining),hl
    pop bc
    pop hl
    ld de,(w3d_music_capture_write)
    ldir
    ld (w3d_music_capture_write),de
    ret
@overflow:
    pop bc
    pop hl
    ld a,1
    ld (w3d_music_capture_overflow),a
    ret

; VDP commands ---------------------------------------------------------------

w3d_music_channel_command:
    db 23,0,085h
w3d_music_channel_command_channel:
    db 0
w3d_music_channel_command_action:
    db 8
w3d_music_channel_command_end:

w3d_music_reset_command:
    db 23,0,085h
w3d_music_reset_channel:
    db 0,10
w3d_music_reset_command_end:

w3d_music_waveform_command:
    db 23,0,085h
w3d_music_waveform_channel:
    db 0,4
w3d_music_waveform_value:
    db 3
w3d_music_waveform_command_end:

w3d_music_frequency_command:
    db 23,0,085h
w3d_music_frequency_channel:
    db 0,3
w3d_music_frequency_value:
    dw 1
w3d_music_frequency_command_end:

w3d_music_volume_command:
    db 23,0,085h
w3d_music_volume_channel:
    db 0,2
w3d_music_volume_value:
    db 0
w3d_music_volume_command_end:

w3d_music_play_command:
    db 23,0,085h
w3d_music_play_channel:
    db 0,0
w3d_music_play_volume:
    db 0
w3d_music_play_frequency:
    dw 1
    dw 0ffffh
w3d_music_play_command_end:

; OPL slot offsets: only carrier operators map to voices.
w3d_music_carrier_voice_table:
    db 0ffh,0ffh,0ffh,0,1,2,0ffh,0ffh
    db 0ffh,0ffh,0ffh,3,4,5,0ffh,0ffh
    db 0ffh,0ffh,0ffh,6,7,8
w3d_music_carrier_offsets:
    db 3,4,5,11,12,13,19,20,21
w3d_music_waveform_table:
    db 3,1,2,0                 ; sine, triangle, saw, square approximation
w3d_music_volume_table:
    db 48,47,46,46,45,44,43,43,42,41,40,40,39,38,37,37
    db 36,35,34,34,33,32,31,31,30,29,28,28,27,26,25,24
    db 24,23,22,21,21,20,19,18,18,17,16,15,15,14,13,12
    db 12,11,10,9,9,8,7,6,5,5,4,3,2,2,1,0

; Original wl_play.c Episode 1 floor music:
; GETTHEM, SEARCHN, POW, SUSPENSE, then repeat; WARMARCH on E1L9 and
; CORNER on the secret floor.
w3d_music_episode1_floor_tracks:
    db W3D_MUSIC_GETTHEM,W3D_MUSIC_SEARCHN,W3D_MUSIC_POW,W3D_MUSIC_SUSPENSE
    db W3D_MUSIC_GETTHEM,W3D_MUSIC_SEARCHN,W3D_MUSIC_POW,W3D_MUSIC_SUSPENSE
    db W3D_MUSIC_WARMARCH,W3D_MUSIC_CORNER

; State ----------------------------------------------------------------------

w3d_music_active:              db 0
w3d_music_paused:              db 0
w3d_music_enabled:             db 1
w3d_music_initialized:         db 0
w3d_music_current_id:          db 0
w3d_music_requested_id:        db 0
w3d_music_voice:               db 0
w3d_music_channel:             db 0
w3d_music_event_register:      db 0
w3d_music_event_value:         db 0
w3d_music_old_value:           db 0
w3d_music_track_start:         dl 0
w3d_music_cursor:              dl 0
w3d_music_started_at:          dl 0
w3d_music_paused_at:           dl 0
w3d_music_elapsed:             dl 0
; Three-byte backing is deliberate: native ADL register loads/stores are
; 24-bit, while the IMF format and comparisons use only the low word.  The
; padding byte remains zero and prevents a store from trampling its neighbor.
w3d_music_events_remaining:    dl 0
w3d_music_loop_ticks:          dl 0
w3d_music_next_due:            dl 0
w3d_music_registers:           ds 256
w3d_music_capture_enabled:     db 0
w3d_music_capture_overflow:    db 0
w3d_music_capture_write:       dl 0
w3d_music_capture_remaining:   dl 0
