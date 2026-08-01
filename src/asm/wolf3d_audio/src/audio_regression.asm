; Direct real-eZ80 regression for the production Wolf3D audio service.

    assume adl=1
    org 040000h
    jp start
    align 64
    db "MOS",0,1

mos_fopen:          equ 00ah
mos_fclose:         equ 00bh
mos_fwrite:         equ 01bh
fa_write:           equ 002h
fa_create_always:   equ 008h

; PRT1: 18.432 MHz / 256 / 72 = 1 kHz, matching the established hardware
; regression stopwatch.  The ISR accumulates elapsed milliseconds in 24 bits;
; setup, assertions and mailbox I/O remain outside the measured regions.
prt_reload_1ms:     equ 72
TMR1_CTL:           equ 083h
TMR_REG_CTL:        equ 0
TMR_RES_LOW:        equ 1
TMR_RES_HIGH:       equ 2
PRT_OFF:            equ %00001110
PRT_ON:             equ %01011111
timing_iterations:  equ 10000

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    macro CHECK_A expected, why
        ld b,expected
        ld c,why
        call assert_equal
    endmacro

    macro CHECK_MEM8 address, expected, why
        ld a,(address)
        CHECK_A expected,why
    endmacro

    macro CHECK_HL expectedLow, expectedHigh, why
        ld a,l
        CHECK_A expectedLow,why
        ld a,h
        CHECK_A expectedHigh,why
    endmacro

    macro REQUEST sound, gain, flags
        ld a,sound
        ld b,gain
        ld c,flags
        call w3d_audio_request
    endmacro

    include "wolf3d_audio_assets.inc"
    include "wolf3d_audio.inc"

phase_ids:          equ 1
phase_batch:        equ 2
phase_catchup:      equ 3
phase_buffered:     equ 4
phase_direct:       equ 5
phase_install:      equ 6
phase_shutdown:     equ 7
phase_timing:       equ 8
phase_count:        equ 8

reason_scalar:      equ 1
reason_mapping:     equ 2
reason_queue:       equ 3
reason_counter:     equ 4
reason_wire:        equ 5
reason_carry:       equ 6
reason_loaded:      equ 7

start:
    push af
    push bc
    push de
    push ix
    push iy
    call run_tests
    pop iy
    pop ix
    pop de
    pop bc
    pop af
    ld hl,0
    ret

run_tests:
    xor a
    ld hl,result_checks
    ld (hl),a
    ld de,result_checks+1
    ld bc,result_end-result_checks-1
    ldir
    ld a,2
    ld (result_schema),a
    ld hl,timing_iterations
    ld a,l
    ld (result_timing_iterations+0),a
    ld a,h
    ld (result_timing_iterations+1),a
    ld hl,1000
    ld a,l
    ld (result_timing_hz+0),a
    ld a,h
    ld (result_timing_hz+1),a
    ld a,1
    ld (result_timing_flags),a
    call test_ids_and_loaded_state
    call test_priority_batch
    call test_catchup_suppression
    call test_buffered_wire
    call test_direct_wire
    call test_command_install
    call test_shutdown
    call prt_irq_install
    call benchmark_loaded_request
    call benchmark_buffered_flush
    call prt_irq_restore
    call write_result
    call print_report
    ret

; -----------------------------------------------------------------------------
; 1. Stable IDs, original priorities and loaded-state validation.
; -----------------------------------------------------------------------------

test_ids_and_loaded_state:
    ld a,phase_ids
    ld (test_phase),a
    call w3d_audio_initialize
    ld a,W3D_AUDIO_LOGICAL_COUNT
    CHECK_A 69,reason_scalar
    ld hl,w3d_audio_asset_table_end-w3d_audio_asset_table
    CHECK_HL 050h,4,reason_scalar       ; 69 * 16 = 1104 = 0x0450
    CHECK_MEM8 w3d_audio_asset_table+368+W3D_AUDIO_ENTRY_PRIORITY,1,reason_scalar
    CHECK_MEM8 w3d_audio_asset_table+384+W3D_AUDIO_ENTRY_PRIORITY,1,reason_scalar
    CHECK_MEM8 w3d_audio_asset_table+480+W3D_AUDIO_ENTRY_PRIORITY,90,reason_scalar

    xor a
    call w3d_audio_get_sample_buffer_id
    CHECK_HL 0,050h,reason_mapping
    ld a,68
    call w3d_audio_get_sample_buffer_id
    CHECK_HL 044h,050h,reason_mapping
    ld a,69
    call w3d_audio_get_sample_buffer_id
    call carry_to_a
    CHECK_A 1,reason_carry

    xor a
    ld c,a
    call w3d_audio_get_command_buffer_id
    CHECK_HL 0,060h,reason_mapping
    ld a,68
    ld c,2
    call w3d_audio_get_command_buffer_id
    CHECK_HL 0ceh,060h,reason_mapping
    ld a,68
    ld c,3
    call w3d_audio_get_command_buffer_id
    call carry_to_a
    CHECK_A 1,reason_carry

    ld hl,05018h
    call w3d_audio_mark_sample_buffer_loaded
    call carry_to_a
    CHECK_A 0,reason_carry
    CHECK_MEM8 w3d_audio_sample_loaded+24,1,reason_loaded
    ld hl,05045h
    call w3d_audio_mark_sample_buffer_loaded
    call carry_to_a
    CHECK_A 1,reason_carry
    ld hl,04018h
    call w3d_audio_mark_sample_buffer_loaded
    call carry_to_a
    CHECK_A 1,reason_carry
    ret

; -----------------------------------------------------------------------------
; 2. Highest three priorities survive; equal priorities remain stable.
; -----------------------------------------------------------------------------

test_priority_batch:
    ld a,phase_batch
    ld (test_phase),a
    call w3d_audio_initialize
    ld hl,batch_loaded_ids
    ld b,batch_loaded_ids_end-batch_loaded_ids
@load:
    ld a,(hl)
    push hl
    push bc
    call w3d_audio_mark_sample_loaded
    pop bc
    pop hl
    inc hl
    djnz @load

; Producer ABI must preserve both index registers across a request.
    call w3d_audio_begin_quantum
    ld ix,0123456h
    ld iy,0654321h
    REQUEST W3D_AUDIO_SOUND_ATKPISTOL,100,0
    ld (test_index_actual+0),ix
    ld (test_index_actual+3),iy
    ld hl,test_index_actual
    ld de,test_index_expected
    ld bc,6
    call assert_memory
    call w3d_audio_discard_quantum

    call w3d_audio_begin_quantum
    REQUEST W3D_AUDIO_SOUND_ATKKNIFE,91,W3D_AUDIO_FLAG_POSITIONED
    REQUEST W3D_AUDIO_SOUND_ATKPISTOL,92,0
    REQUEST W3D_AUDIO_SOUND_NOWAY,93,0
    REQUEST W3D_AUDIO_SOUND_OPENDOOR,94,W3D_AUDIO_FLAG_POSITIONED
    REQUEST W3D_AUDIO_SOUND_GETMACHINE,200,0
    CHECK_MEM8 w3d_audio_pending_count,3,reason_queue
    CHECK_MEM8 w3d_audio_pending+W3D_AUDIO_PENDING_SOUND,W3D_AUDIO_SOUND_GETMACHINE,reason_queue
    CHECK_MEM8 w3d_audio_pending+W3D_AUDIO_PENDING_GAIN,127,reason_queue
    CHECK_MEM8 w3d_audio_pending+5+W3D_AUDIO_PENDING_SOUND,W3D_AUDIO_SOUND_NOWAY,reason_queue
    CHECK_MEM8 w3d_audio_pending+10+W3D_AUDIO_PENDING_SOUND,W3D_AUDIO_SOUND_ATKKNIFE,reason_queue
    CHECK_MEM8 w3d_audio_pending+10+W3D_AUDIO_PENDING_FLAGS,W3D_AUDIO_FLAG_POSITIONED,reason_queue
    CHECK_MEM8 w3d_audio_requested_events+0,6,reason_counter
    CHECK_MEM8 w3d_audio_dropped_requests+0,2,reason_counter
    call w3d_audio_discard_quantum

; Three priority-50 requests must retain source order exactly.
    call w3d_audio_begin_quantum
    REQUEST W3D_AUDIO_SOUND_NAZIHITPLAYER,70,0
    REQUEST W3D_AUDIO_SOUND_NAZIMISS,71,0
    REQUEST W3D_AUDIO_SOUND_PLAYERDEATH,72,0
    CHECK_MEM8 w3d_audio_pending+W3D_AUDIO_PENDING_SOUND,W3D_AUDIO_SOUND_NAZIHITPLAYER,reason_queue
    CHECK_MEM8 w3d_audio_pending+5+W3D_AUDIO_PENDING_SOUND,W3D_AUDIO_SOUND_NAZIMISS,reason_queue
    CHECK_MEM8 w3d_audio_pending+10+W3D_AUDIO_PENDING_SOUND,W3D_AUDIO_SOUND_PLAYERDEATH,reason_queue
    call w3d_audio_discard_quantum

; Invalid, missing, silent and out-of-quantum calls are fail-quiet diagnostics.
    REQUEST W3D_AUDIO_SOUND_ATKPISTOL,100,0
    call carry_to_a
    CHECK_A 1,reason_carry
    CHECK_MEM8 w3d_audio_inactive_requests+0,1,reason_counter
    call w3d_audio_begin_quantum
    REQUEST 69,100,0
    call carry_to_a
    CHECK_A 1,reason_carry
    REQUEST W3D_AUDIO_SOUND_GAMEOVER,100,0
    call carry_to_a
    CHECK_A 1,reason_carry
    REQUEST W3D_AUDIO_SOUND_ATKPISTOL,0,0
    call carry_to_a
    CHECK_A 1,reason_carry
    CHECK_MEM8 w3d_audio_invalid_requests+0,1,reason_counter
    CHECK_MEM8 w3d_audio_missing_requests+0,1,reason_counter
    CHECK_MEM8 w3d_audio_silent_requests+0,1,reason_counter
    jp w3d_audio_discard_quantum

batch_loaded_ids:
    db W3D_AUDIO_SOUND_ATKKNIFE,W3D_AUDIO_SOUND_ATKPISTOL,W3D_AUDIO_SOUND_NOWAY
    db W3D_AUDIO_SOUND_OPENDOOR,W3D_AUDIO_SOUND_GETMACHINE
    db W3D_AUDIO_SOUND_NAZIHITPLAYER,W3D_AUDIO_SOUND_NAZIMISS
    db W3D_AUDIO_SOUND_PLAYERDEATH
batch_loaded_ids_end:

; -----------------------------------------------------------------------------
; 3. Explicit and implicit catch-up discards never emit stale events.
; -----------------------------------------------------------------------------

test_catchup_suppression:
    ld a,phase_catchup
    ld (test_phase),a
    call w3d_audio_initialize
    ld a,W3D_AUDIO_SOUND_PLAYERDEATH
    call w3d_audio_mark_sample_loaded
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    call w3d_audio_mark_sample_loaded
    call start_capture

    call w3d_audio_begin_quantum
    REQUEST W3D_AUDIO_SOUND_PLAYERDEATH,127,0
    call w3d_audio_discard_quantum
    call w3d_audio_begin_quantum
    REQUEST W3D_AUDIO_SOUND_ATKPISTOL,91,0
    call w3d_audio_flush_quantum
    CHECK_MEM8 w3d_audio_capture_length+0,12,reason_wire
    CHECK_MEM8 w3d_audio_discarded_quanta+0,1,reason_counter
    CHECK_MEM8 w3d_audio_discarded_events+0,1,reason_counter
    ld hl,test_capture
    ld de,expected_buffered_pistol_ch0
    ld bc,12
    call assert_memory

; Beginning over a still-active batch performs the same safe discard.
    call w3d_audio_initialize
    call start_capture
    ld a,W3D_AUDIO_SOUND_PLAYERDEATH
    call w3d_audio_mark_sample_loaded
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    call w3d_audio_mark_sample_loaded
    call w3d_audio_begin_quantum
    REQUEST W3D_AUDIO_SOUND_PLAYERDEATH,127,0
    call w3d_audio_begin_quantum
    REQUEST W3D_AUDIO_SOUND_ATKPISTOL,91,0
    call w3d_audio_flush_quantum
    CHECK_MEM8 w3d_audio_capture_length+0,12,reason_wire
    CHECK_MEM8 w3d_audio_discarded_quanta+0,1,reason_counter
    CHECK_MEM8 w3d_audio_discarded_events+0,1,reason_counter
    ret

; -----------------------------------------------------------------------------
; 4. Buffered wire, sorted emission order, round robin and byte accounting.
; -----------------------------------------------------------------------------

test_buffered_wire:
    ld a,phase_buffered
    ld (test_phase),a
    call w3d_audio_initialize
    call start_capture
    ld a,W3D_AUDIO_SOUND_ATKKNIFE
    call w3d_audio_mark_sample_loaded
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    call w3d_audio_mark_sample_loaded
    ld a,W3D_AUDIO_SOUND_GETMACHINE
    call w3d_audio_mark_sample_loaded
    call w3d_audio_begin_quantum
    REQUEST W3D_AUDIO_SOUND_ATKKNIFE,49,0
    REQUEST W3D_AUDIO_SOUND_ATKPISTOL,50,0
    REQUEST W3D_AUDIO_SOUND_GETMACHINE,80,0
    call w3d_audio_flush_quantum
    CHECK_MEM8 w3d_audio_capture_length+0,36,reason_wire
    CHECK_MEM8 w3d_audio_runtime_uart_bytes+0,36,reason_counter
    CHECK_MEM8 w3d_audio_emitted_events+0,3,reason_counter
    CHECK_MEM8 w3d_audio_next_channel,0,reason_counter
    ld hl,test_capture
    ld de,expected_buffered_sorted
    ld bc,36
    call assert_memory

; Next event wraps to channel zero and contributes exactly twelve bytes.
    call w3d_audio_begin_quantum
    REQUEST W3D_AUDIO_SOUND_ATKPISTOL,33,0
    call w3d_audio_flush_quantum
    CHECK_MEM8 w3d_audio_capture_length+0,48,reason_wire
    CHECK_MEM8 w3d_audio_runtime_uart_bytes+0,48,reason_counter
    CHECK_MEM8 w3d_audio_next_channel,1,reason_counter

; A sample withdrawn after arbitration must emit nothing or consume a channel.
    call w3d_audio_initialize
    call start_capture
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    call w3d_audio_mark_sample_loaded
    call w3d_audio_begin_quantum
    REQUEST W3D_AUDIO_SOUND_ATKPISTOL,127,0
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    call w3d_audio_mark_sample_unavailable
    call w3d_audio_flush_quantum
    CHECK_MEM8 w3d_audio_capture_length+0,0,reason_wire
    CHECK_MEM8 w3d_audio_missing_dispatches+0,1,reason_counter
    CHECK_MEM8 w3d_audio_next_channel,0,reason_counter
    ret

; -----------------------------------------------------------------------------
; 5. Direct fallback sends reset+waveform+play and embeds mono gain.
; -----------------------------------------------------------------------------

test_direct_wire:
    ld a,phase_direct
    ld (test_phase),a
    call w3d_audio_initialize
    ld a,W3D_AUDIO_TRANSPORT_DIRECT
    call w3d_audio_select_transport
    call carry_to_a
    CHECK_A 0,reason_carry
    call start_capture
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    call w3d_audio_mark_sample_loaded
    call w3d_audio_begin_quantum
    REQUEST W3D_AUDIO_SOUND_ATKPISTOL,73,W3D_AUDIO_FLAG_POSITIONED
    call w3d_audio_flush_quantum
    CHECK_MEM8 w3d_audio_capture_length+0,23,reason_wire
    CHECK_MEM8 w3d_audio_runtime_uart_bytes+0,23,reason_counter
    ld hl,test_capture
    ld de,expected_direct_pistol_ch0
    ld bc,23
    call assert_memory
    ld a,2
    call w3d_audio_select_transport
    call carry_to_a
    CHECK_A 1,reason_carry
    CHECK_MEM8 w3d_audio_transport,W3D_AUDIO_TRANSPORT_DIRECT,reason_scalar
    ret

; -----------------------------------------------------------------------------
; 6. Only loaded samples get three stable command procedures.
; -----------------------------------------------------------------------------

test_command_install:
    ld a,phase_install
    ld (test_phase),a
    call w3d_audio_initialize
    call start_capture
    call w3d_audio_install_available_command_buffers
    CHECK_MEM8 w3d_audio_capture_length+0,0,reason_wire
    CHECK_MEM8 w3d_audio_installed_commands+0,0,reason_counter

    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    call w3d_audio_mark_sample_loaded
    call w3d_audio_install_available_command_buffers
    CHECK_MEM8 w3d_audio_capture_length+0,111,reason_wire
    CHECK_MEM8 w3d_audio_installed_commands+0,3,reason_counter
    CHECK_MEM8 w3d_audio_setup_uart_bytes+0,111,reason_counter
    CHECK_MEM8 w3d_audio_capture_overflow,0,reason_wire
    ld hl,test_capture
    ld de,expected_install_pistol
    ld bc,111
    jp assert_memory

; -----------------------------------------------------------------------------
; 7. Shutdown resets exactly the three default channels and clears availability.
; -----------------------------------------------------------------------------

test_shutdown:
    ld a,phase_shutdown
    ld (test_phase),a
    call w3d_audio_initialize
    call start_capture
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    call w3d_audio_mark_sample_loaded
    call w3d_audio_shutdown
    CHECK_MEM8 w3d_audio_capture_length+0,15,reason_wire
    CHECK_MEM8 w3d_audio_shutdown_uart_bytes+0,15,reason_counter
    CHECK_MEM8 w3d_audio_sample_loaded+W3D_AUDIO_SOUND_ATKPISTOL,0,reason_loaded
    ld hl,test_capture
    ld de,expected_shutdown
    ld bc,15
    jp assert_memory

; -----------------------------------------------------------------------------
; 8. Hardware-compatible PRT timings.  The matched baselines contain the exact
; fixture re-arm, argument loads and loop bookkeeping but omit the production
; call.  Subtracting them in the host runner isolates backend CPU dispatch from
; both harness overhead and physical UART/VDP time.
; -----------------------------------------------------------------------------

benchmark_loaded_request:
    ld a,phase_timing
    ld (test_phase),a
    call w3d_audio_initialize
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    call w3d_audio_mark_sample_loaded
    call w3d_audio_begin_quantum
    ld hl,timing_iterations
    ld (timing_left),hl
    call prt_start
@request_loop:
    xor a
    ld (w3d_audio_pending_count),a
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    ld b,127
    ld c,0
    call w3d_audio_request
    ld hl,(timing_left)
    dec hl
    ld (timing_left),hl
    ld a,h
    or l
    jr nz,@request_loop
    call prt_stop_request_total
    call w3d_audio_discard_quantum

; Same active/loaded state, argument setup, queue re-arm and loop bookkeeping.
    call w3d_audio_initialize
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    call w3d_audio_mark_sample_loaded
    call w3d_audio_begin_quantum
    ld hl,timing_iterations
    ld (timing_left),hl
    call prt_start
@request_baseline_loop:
    xor a
    ld (w3d_audio_pending_count),a
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    ld b,127
    ld c,0
    ld hl,(timing_left)
    dec hl
    ld (timing_left),hl
    ld a,h
    or l
    jr nz,@request_baseline_loop
    call prt_stop_request_baseline
    jp w3d_audio_discard_quantum

benchmark_buffered_flush:
    call prepare_flush_benchmark
    ld hl,timing_iterations
    ld (timing_left),hl
    call prt_start
@flush_loop:
    call rearm_one_event_capture
    call w3d_audio_flush_quantum
    ld hl,(timing_left)
    dec hl
    ld (timing_left),hl
    ld a,h
    or l
    jr nz,@flush_loop
    call prt_stop_flush_total

; The final iteration must still be the exact twelve-byte buffered path.
    CHECK_MEM8 w3d_audio_capture_length+0,12,reason_wire
    CHECK_MEM8 w3d_audio_capture_length+1,0,reason_wire
    CHECK_MEM8 w3d_audio_capture_overflow,0,reason_wire
    ld hl,timing_capture
    ld de,expected_buffered_pistol_full_gain_ch0
    ld bc,12
    call assert_memory

; Repeat only the identical fixture re-arm and loop bookkeeping.  The runner
; reports (flush total - this baseline) / 10,000 as the backend-only cost.
    call prepare_flush_benchmark
    ld hl,timing_iterations
    ld (timing_left),hl
    call prt_start
@flush_baseline_loop:
    call rearm_one_event_capture
    ld hl,(timing_left)
    dec hl
    ld (timing_left),hl
    ld a,h
    or l
    jr nz,@flush_baseline_loop
    call prt_stop_flush_baseline
    jp w3d_audio_initialize

prepare_flush_benchmark:
    call w3d_audio_initialize
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    call w3d_audio_mark_sample_loaded
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    ld (w3d_audio_pending+W3D_AUDIO_PENDING_SOUND),a
    ld a,127
    ld (w3d_audio_pending+W3D_AUDIO_PENDING_GAIN),a
    ld hl,timing_capture
    ld de,12
    jp w3d_audio_capture_start

; Re-arm exactly the mutable state consumed by a one-event buffered flush.
; Keeping this helper in both measured loops makes its call and stores cancel.
rearm_one_event_capture:
    ld a,1
    ld (w3d_audio_quantum_active),a
    ld (w3d_audio_pending_count),a
    ld hl,timing_capture
    ld (w3d_audio_capture_write),hl
    ld a,12
    ld (w3d_audio_capture_remaining+0),a
    xor a
    ld (w3d_audio_capture_remaining+1),a
    ld (w3d_audio_capture_length+0),a
    ld (w3d_audio_capture_length+1),a
    ld (w3d_audio_capture_overflow),a
    ret

; -----------------------------------------------------------------------------
; PRT1 stopwatch.  DI/EI protects vector replacement and every critical
; counter snapshot; the ISR itself preserves the registers it touches.
; -----------------------------------------------------------------------------

prt_start:
    di
    ld hl,0
    ld (prt_irq_counter),hl
    ld hl,prt_reload_1ms
    out0 (TMR1_CTL+TMR_RES_LOW),l
    out0 (TMR1_CTL+TMR_RES_HIGH),h
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld a,PRT_ON
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ei
    ret

prt_stop_request_total:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_irq_counter)
    ld (result_timing_request_total),hl
    ei
    ret

prt_stop_request_baseline:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_irq_counter)
    ld (result_timing_request_baseline),hl
    ei
    ret

prt_stop_flush_total:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_irq_counter)
    ld (result_timing_flush_total),hl
    ei
    ret

prt_stop_flush_baseline:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_irq_counter)
    ld (result_timing_flush_baseline),hl
    ei
    ret

prt_irq_install:
    di
    ld hl,0
    ld a,($10c)
    ld l,a
    ld a,($10d)
    ld h,a
    inc hl
    ld hl,(hl)
    ld (prt_vector),hl
    ld a,(hl)
    ld (prt_saved_vector+0),a
    inc hl
    ld a,(hl)
    ld (prt_saved_vector+1),a
    inc hl
    ld a,(hl)
    ld (prt_saved_vector+2),a
    inc hl
    ld a,(hl)
    ld (prt_saved_vector+3),a
    ld hl,(prt_vector)
    ld (hl),0c3h
    inc hl
    ld de,prt_irq_handler
    ld (hl),de
    ei
    ret

prt_irq_restore:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_vector)
    ld a,(prt_saved_vector+0)
    ld (hl),a
    inc hl
    ld a,(prt_saved_vector+1)
    ld (hl),a
    inc hl
    ld a,(prt_saved_vector+2)
    ld (hl),a
    inc hl
    ld a,(prt_saved_vector+3)
    ld (hl),a
    ei
    ret

prt_irq_handler:
    di
    push af
    push hl
    in0 a,(TMR1_CTL+TMR_REG_CTL)
    ld hl,(prt_irq_counter)
    inc hl
    ld (prt_irq_counter),hl
    pop hl
    pop af
    ei
    reti.l

; -----------------------------------------------------------------------------
; Test helpers, assertions and result mailbox.
; -----------------------------------------------------------------------------

start_capture:
    ld hl,test_capture
    ld de,test_capture_end-test_capture
    jp w3d_audio_capture_start

carry_to_a:
    ld a,0
    adc a,0
    ret

; HL=actual, DE=expected, BC=u16 length.
assert_memory:
@loop:
    ld a,b
    or c
    ret z
    push hl
    push de
    push bc
    ld a,(de)
    ld b,a
    ld a,(hl)
    ld c,reason_wire
    call assert_equal
    pop bc
    pop de
    pop hl
    inc hl
    inc de
    dec.s bc
    jr @loop

; A=actual, B=expected, C=reason.
assert_equal:
    ld (assert_actual),a
    ld a,b
    ld (assert_expected),a
    push hl
    ld hl,result_checks
    inc (hl)
    jr nz,@compare
    inc hl
    inc (hl)
@compare:
    ld a,(assert_actual)
    cp b
    jr z,@return
    ld hl,result_errors
    inc (hl)
    jr nz,@first
    inc hl
    inc (hl)
@first:
    ld a,(result_first_reason)
    or a
    jr nz,@return
    ld a,(test_phase)
    ld (result_first_phase),a
    ld a,c
    ld (result_first_reason),a
    ld a,(assert_expected)
    ld (result_first_expected),a
    ld a,(assert_actual)
    ld (result_first_actual),a
@return:
    pop hl
    ret

write_result:
    ld hl,result_filename
    ld c,fa_write|fa_create_always
    MOSCALL mos_fopen
    or a
    ret z
    ld (output_handle),a
    ld c,a
    ld hl,result_data
    ld de,result_end-result_data
    MOSCALL mos_fwrite
    ld a,(output_handle)
    ld c,a
    MOSCALL mos_fclose
    ret

print_report:
    ld hl,report_banner
    call print_string
    ld a,(result_errors+0)
    ld b,a
    ld a,(result_errors+1)
    or b
    ld hl,report_pass
    jr z,@emit
    ld hl,report_fail
@emit:
    jp print_string

print_string:
    push bc
    ld bc,0
    ld a,0
    rst.lil 018h
    pop bc
    ret

expected_buffered_pistol_ch0:
    db 23,0,0a0h,048h,060h,1, 23,0,085h,0,2,91

expected_buffered_pistol_full_gain_ch0:
    db 23,0,0a0h,048h,060h,1, 23,0,085h,0,2,127

; Emission order: GETMACHINE/ch0, knife/ch1, pistol/ch2.
expected_buffered_sorted:
    db 23,0,0a0h,05ah,060h,1, 23,0,085h,0,2,80
    db 23,0,0a0h,046h,060h,1, 23,0,085h,1,2,49
    db 23,0,0a0h,04ah,060h,1, 23,0,085h,2,2,50

expected_direct_pistol_ch0:
    db 23,0,085h,0,10
    db 23,0,085h,0,4,8,018h,050h
    db 23,0,085h,0,0,73,0,0,0,0

expected_install_pistol:
    db 23,0,0a0h,048h,060h,2
    db 23,0,0a0h,048h,060h,0,23,0
    db 23,0,085h,0,10
    db 23,0,085h,0,4,8,018h,050h
    db 23,0,085h,0,0,127,0,0,0,0
    db 23,0,0a0h,049h,060h,2
    db 23,0,0a0h,049h,060h,0,23,0
    db 23,0,085h,1,10
    db 23,0,085h,1,4,8,018h,050h
    db 23,0,085h,1,0,127,0,0,0,0
    db 23,0,0a0h,04ah,060h,2
    db 23,0,0a0h,04ah,060h,0,23,0
    db 23,0,085h,2,10
    db 23,0,085h,2,4,8,018h,050h
    db 23,0,085h,2,0,127,0,0,0,0

expected_shutdown:
    db 23,0,085h,0,10
    db 23,0,085h,1,10
    db 23,0,085h,2,10

report_banner:      asciz "Wolf3D audio direct regression\r\n"
report_pass:        asciz "PASS\r\n"
report_fail:        asciz "FAIL\r\n"
result_filename:    asciz "audio_result.bin"
test_phase:         db 0
output_handle:      db 0
assert_expected:    db 0
assert_actual:      db 0
timing_left:        dl 0
prt_vector:         dl 0
prt_saved_vector:   db 0,0,0,0
prt_irq_counter:    dl 0

result_data:
    db "W3AU"
result_checks:              dw 0
result_errors:              dw 0
result_first_phase:         db 0
result_first_reason:        db 0
result_first_expected:      db 0
result_first_actual:        db 0
result_schema:              db 2
result_timing_request_total:    dl 0
result_timing_request_baseline: dl 0
result_timing_flush_total:      dl 0
result_timing_flush_baseline:   dl 0
result_timing_iterations:       dw 0
result_timing_hz:               dw 0
result_timing_flags:            db 1    ; bit 0: matched baselines present
    ds 2
result_end:

test_capture:
    ds 256
test_capture_end:
timing_capture:
    ds 12
test_index_actual:
    ds 6
test_index_expected:
    db 056h,034h,012h,021h,043h,065h
