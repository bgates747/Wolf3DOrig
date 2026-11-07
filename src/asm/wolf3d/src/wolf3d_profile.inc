; Small call sites retain branch reach; each hook preserves registers/flags.
w3d_profile_initialize:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_profile_initialize_impl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

w3d_profile_game_open:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_profile_game_open_impl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

w3d_profile_input_begin:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_profile_input_begin_impl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

w3d_profile_input_end:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_profile_input_end_impl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

w3d_profile_prepare:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_profile_prepare_impl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

w3d_profile_submitted:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_profile_submitted_impl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

w3d_profile_callback:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_profile_callback_impl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

w3d_profile_before_present:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_profile_before_present_impl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

w3d_profile_after_present:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_profile_after_present_impl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

w3d_profile_game_close:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_profile_game_close_impl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

w3d_profile_finish:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_profile_finish_impl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

; Optional full-game profiler. Entire file is excluded by W3D_PROFILE=0.
; WOLF-PROFILE-001/PRE-CODE.md owns the boundaries and clock limitations.
WP_RECORD_BYTES: equ 64
WP_CAPACITY: equ 128
WP_FLUSH_FRAMES: equ 120
WP_ICON_BUFFER: equ 0ef00h
WP_NATIVE_BUFFER: equ 0f000h

w3d_profile_initialize_impl:
    xor a
    ld hl,wp_state
    ld (hl),a
    ld de,wp_state+1
    ld bc,wp_state_end-wp_state-1
    ldir
    ld hl,wp_header+12
    ld b,20
@header_zero:
    ld (hl),a
    inc hl
    djnz @header_zero
    in0 a,(083h)
    ld (wp_old_ctl),a
    and 041h
    jr z,@available
    ld a,1
    ld (wp_status),a                 ; busy timer: never take it
    ret
@available:
    in0 a,(092h)
    ld (wp_old_iss),a
    and 0f3h
    out0 (092h),a
    ld hl,wp_irq
    ld e,00ch
    MOSCALL 14h
    ld (wp_old_vector),hl
    ld hl,72
    out0 (084h),l
    out0 (085h),h
    ld a,00eh
    out0 (083h),a
    ld a,05fh
    out0 (083h),a
    ld a,1
    ld (wp_owned),a
    ld (wp_active),a
    ret

wp_irq:
    push af
    push hl
    in0 a,(083h)
    ld hl,(wp_ticks)
    inc hl
    ld (wp_ticks),hl
    pop hl
    pop af
    ei
    reti.l

w3d_profile_game_open_impl:
    ld a,(wp_active)
    or a
    jr nz,@active
    .if W3D_PROFILE_NATIVE
    jp wp_protocol_failed          ; finite native logger requires its buffer
    .else
    ret
    .endif
@active:
    ld hl,wp_records
    ld (wp_next),hl
    xor a
    ld (wp_count),a
    ld (wp_pending),a
    ld (wp_due),a
    ld (wp_input_valid),a
    ld a,1
    ld (wp_new_session),a
    ld hl,(wp_ticks)
    ld (wp_last_flush),hl
    ld hl,wp_icon_upload
    ld bc,wp_icon_upload_end-wp_icon_upload
    rst.lil 18h
    ld hl,wp_icon_pixels
    ld bc,24*32
    rst.lil 18h
    ld hl,wp_icon_create
    ld bc,wp_icon_create_end-wp_icon_create
    rst.lil 18h
    call w3d_audio_wait_for_vdp_ingress
    jp c,wp_protocol_failed
    ld a,1
    ld (wp_game_open),a
    .if W3D_PROFILE_NATIVE
    ld hl,wp_native_create
    ld bc,wp_native_create_end-wp_native_create
    rst.lil 18h
    call w3d_audio_wait_for_vdp_ingress
    jp c,wp_protocol_failed
    call wp_native_reset
    jp c,wp_protocol_failed
    .endif
    ret

; Input service gaps and inclusive input/physics foreground costs are
; aggregated, not logged once per idle poll. No simulation clock is altered.
w3d_profile_input_begin_impl:
    ld a,(wp_active)
    or a
    ret z
    ld hl,(wp_ticks)
    ld (wp_input_start),hl
    ld a,(wp_input_valid)
    or a
    jr z,@first
    ld de,(wp_input_last)
    or a
    sbc hl,de
    ld de,(wp_input_gap)
    push hl
    or a
    sbc hl,de
    pop hl
    jr c,@first
    ld (wp_input_gap),hl
@first:
    ld hl,(wp_input_start)
    ld (wp_input_last),hl
    ld a,1
    ld (wp_input_valid),a
    ret
w3d_profile_input_end_impl:
    ld a,(wp_active)
    or a
    ret z
    ld hl,(wp_ticks)
    ld de,(wp_input_start)
    or a
    sbc hl,de
    ld de,(wp_sim_cost)
    add hl,de
    ld (wp_sim_cost),hl
    ret

w3d_profile_prepare_impl:
    ld a,(wp_active)
    or a
    ret z
    ld a,(wp_game_open)
    or a
    ret z
    ld a,(wp_pending)
    or a
    jr z,@new
    ld hl,(wp_dropped)
    inc hl
    ld (wp_dropped),hl            ; failed/uncompleted attempt, not a frame
@new:
    ld a,(wp_count)
    cp WP_CAPACITY
    jr c,@room
    ld a,2
    ld (wp_status),a
    jp wp_protocol_failed         ; never overrun or let native602 fill
@room:
    ld hl,(wp_next)
    ld (wp_current),hl
    push hl
    xor a
    ld b,WP_RECORD_BYTES
@clear:
    ld (hl),a
    inc hl
    djnz @clear
    pop ix
    ld a,(wp_new_session)
    or a
    jr z,@session_flagged
    set 5,(ix+42)
@session_flagged:
    ld hl,(wp_sequence)
    inc hl
    ld (wp_sequence),hl
    ld (ix+0),hl
    ld hl,(wp_ticks)
    ld (ix+3),hl
    ld hl,(wp_input_gap)
    ld (ix+21),hl
    ld hl,(wp_sim_cost)
    ld (ix+24),hl
    ld hl,(w3d_simulation_accumulator)
    ld (ix+27),hl
    ld hl,(wp_dropped)
    ld (ix+56),hl
    ld a,(w3d_next_render_purpose)
    ld (ix+45),a
    ld a,W3D_RENDER_BACKEND
    ld (ix+44),a
    call w3d_load_player_angle
    ld (ix+46),l
    ld (ix+47),h
    push ix
    pop de
    ld hl,48
    add hl,de
    ex de,hl
    ld hl,w3d_player_pose
    ld bc,8
    ldir
    xor a
    ld (wp_input_gap),a
    ld (wp_input_gap+1),a
    ld (wp_input_gap+2),a
    ld a,1
    ld (wp_pending),a
    ret
w3d_profile_submitted_impl:
    ld a,(wp_pending)
    or a
    ret z
    ld ix,(wp_current)
    ld hl,(wp_ticks)
    ld (ix+6),hl
    set 3,(ix+42)
    ret

; IRQ safe: only snapshot a single instruction's atomic 24-bit tick read.
w3d_profile_callback_impl:
    ld a,(wp_pending)
    or a
    ret z
    ld a,(w3d_async_owner)
    cp W3D_ASYNC_OWNER_RENDER
    ret nz
    ld ix,(wp_current)
    ld hl,(wp_ticks)
    ld (ix+9),hl
    set 2,(ix+42)
    ret

w3d_profile_before_present_impl:
    ld a,(wp_pending)
    or a
    ret z
    ld ix,(wp_current)
    ld hl,(wp_ticks)
    ld (ix+12),hl
    xor a
    ld (wp_due),a
    ld a,(w3d_render_in_flight_purpose)
    cp W3D_RENDER_PURPOSE_NORMAL
    ret nz                         ; don't disturb death/fizzle sequencing
    ld a,(wp_count)
    cp WP_FLUSH_FRAMES-1
    jr nc,@due
    ld de,(wp_last_flush)
    or a
    sbc hl,de
    ld de,5000
    or a
    sbc hl,de
    ret c
@due:
    ld a,1
    ld (wp_due),a
    set 0,(ix+42)                  ; presentation bucket includes log cue
    ld hl,(wp_ticks)
    ld (wp_gap_start),hl
    jp wp_draw_icon

w3d_profile_after_present_impl:
    ld a,(wp_pending)
    or a
    ret z
    ld ix,(wp_current)
    ld hl,(wp_ticks)
    ld (ix+15),hl                  ; return from synchronous serial send
    call w3d_audio_wait_for_vdp_ingress
    jp c,wp_protocol_failed
    ld ix,(wp_current)
    ld hl,(wp_ticks)
    ld (ix+18),hl                  ; ordered swap/fence, NOT optical scanout
    set 4,(ix+42)
    ld a,(wp_count)
    ld (ix+59),a
    inc a
    ld (wp_count),a
    ld de,WP_RECORD_BYTES
    ld hl,(wp_next)
    add hl,de
    ld (wp_next),hl
    xor a
    ld (wp_pending),a
    ld (wp_new_session),a
    ld a,(wp_due)
    or a
    ret z
    call wp_flush
    ; Both pages are redrawn by ordinary completed frames, from live state.
    ; No writes to the scanned-out page, no stale saved expression.
    ld a,1
    ld (w3d_hud_dirty),a
    ld (w3d_world_dirty),a
    ret

wp_draw_icon:
    ; VDU23,27,3 uses physical pixels and ignores graphics viewport/origin.
    ; A 3D renderer's retained clip must not hide the HUD write cue.
    ld hl,@command
    ld bc,@end-@command
    rst.lil 18h
    ret
@command:
    db 23,27,020h
    dw WP_ICON_BUFFER
    db 23,27,3
    dw 136,204
@end:

; Write the previous flush's end times in the next block. It is impossible
; for a write to contain its own eventual close-completion timestamp. The
; last logging gap is explicitly open-ended if no subsequent block exists.
wp_flush:
    ld a,(wp_count)
    or a
    ret z
    ld hl,wp_previous_gap
    ld de,wp_header+16
    ld bc,16
    ldir
    .if W3D_PROFILE_NATIVE
    call wp_collect_native
    jp c,wp_protocol_failed
    .endif
    ld a,(wp_count)
    ld (wp_header+8),a
    ld a,(wp_status)
    add a,a
    add a,a
    add a,a
    add a,a
    or W3D_PROFILE_NATIVE
    ld (wp_header+7),a
    ld hl,(wp_block)
    ld (wp_header+12),hl
    inc hl
    ld (wp_block),hl
    ld hl,(wp_gap_start)
    ld (wp_previous_gap+0),hl
    ld hl,(wp_ticks)
    ld (wp_previous_gap+8),hl
    ld hl,wp_filename
    ld a,(wp_file_created)
    or a
    ld c,fa_write|fa_create_always
    jr z,@open
    ld c,032h                       ; FA_WRITE | FA_OPEN_APPEND
@open:
    MOSCALL mos_fopen
    or a
    jp z,wp_disk_failed
    ld (wp_file),a
    ld c,a
    ld hl,wp_header
    ld de,32
    MOSCALL mos_fwrite
    ld hl,32
    or a
    sbc hl,de
    jr nz,@short
    ld a,(wp_count)
    ld hl,0
    ld l,a
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ld (wp_write_bytes),hl
    ex de,hl
    ld hl,wp_records
    ld a,(wp_file)
    ld c,a
    MOSCALL mos_fwrite
    ld hl,(wp_write_bytes)
    or a
    sbc hl,de
    jr nz,@short
    ld a,(wp_file)
    ld c,a
    MOSCALL mos_fclose
    ld hl,(wp_ticks)
    ld (wp_previous_gap+12),hl
    ld (wp_previous_gap+4),hl
    ld (wp_last_flush),hl
    ld a,1
    ld (wp_file_created),a
    xor a
    ld (wp_file),a
    ld (wp_count),a
    ld (wp_due),a
    ld (wp_input_valid),a          ; separate logging gap from input latency
    ld hl,wp_records
    ld (wp_next),hl
    ret
@short:
    ld a,(wp_file)
    ld c,a
    MOSCALL mos_fclose
    jp wp_disk_failed

wp_disk_failed:
    ld a,3
    ld (wp_status),a
    xor a
    ld (wp_file),a
    ld (wp_active),a
    ld (wp_pending),a
    ; A profiled module cannot be left filling its finite native log forever.
    ; Stop this game through the existing drained error path, without retry.
    .if W3D_PROFILE_NATIVE
    ld a,1
    ld (w3d_callback_error),a
    ld (w3d_exit_requested),a
    .endif
    ret
wp_protocol_failed:
    ld a,(wp_status)
    or a
    jr nz,@status_set
    ld a,4
    ld (wp_status),a
@status_set:
    xor a
    ld (wp_active),a
    ld (wp_pending),a
    ld a,1
    ld (w3d_callback_error),a
    ld (w3d_exit_requested),a
    scf
    ret

w3d_profile_game_close_impl:
    ld a,(wp_game_open)
    or a
    ret z
    ld a,(wp_active)
    or a
    jr nz,@active
    ld a,(wp_status)
    cp 3
    ret nz                         ; retain uncertain protocol ownership
    ld a,(w3d_async_owner)
    or a
    ret nz
    jp @release                    ; drained disk error still frees own buffers
@active:
    ld a,(w3d_async_owner)
    or a
    jr nz,@unsafe
    ld a,(wp_pending)
    or a
    jr nz,@unsafe
    ld a,(wp_count)
    or a
    jr z,@release
    ; Terminal flush isn't a new measured game frame. Use a visible cue only
    ; after all owners have drained; its swap is excluded from frame counts.
    ld hl,(wp_ticks)
    ld (wp_gap_start),hl
    call wp_draw_icon
    call w3d_vdu_present
    call w3d_audio_wait_for_vdp_ingress
    jp c,wp_protocol_failed
    call wp_flush
@release:
    ld hl,wp_clear_buffers
    ld bc,wp_clear_buffers_end-wp_clear_buffers
    rst.lil 18h
    call w3d_audio_wait_for_vdp_ingress
    jp c,wp_protocol_failed
    xor a
    ld (wp_game_open),a
    ret
@unsafe:
    ld a,4
    ld (wp_status),a
    ret                            ; no queries/LOAD/reset on uncertain owner

w3d_profile_finish_impl:
    ld a,(wp_owned)
    or a
    jr z,@report
    xor a
    out0 (083h),a
    ld a,(wp_old_iss)
    out0 (092h),a
    ld hl,(wp_old_vector)
    ld e,00ch
    MOSCALL 14h
    ld de,wp_irq
    or a
    sbc hl,de
    jr z,@restored
    ld a,5
    ld (wp_status),a
@restored:
    ld a,(wp_old_ctl)
    and 07eh
    out0 (083h),a
    xor a
    ld (wp_owned),a
@report:
    ld a,(wp_status)
    or a
    ld hl,wp_ok_message
    jp z,printString
    ld hl,wp_error_message
    call printString
    ld a,(wp_status)
    add a,'0'
    rst.lil 10h
    jp printNewLine

    .if W3D_PROFILE_NATIVE
wp_native_reset:
    ld bc,100
    ld de,W3D_VDPLET_ARGUMENT_BUFFER
    call w3d_vdplet_send_run
    ret c
    jp w3d_vdplet_wait_run
wp_native_read16:
    ld hl,(wp_native_offset)
    ld (@offset),hl
    ld a,(w3d_vdplet_handle+0)
    ld (@handle+0),a
    ld a,(w3d_vdplet_handle+1)
    ld (@handle+1),a
    ld a,W3D_VDPL_REPLY_VALUE
    ld hl,@token
    call w3d_vdplet_arm_request
    ret c
    ld hl,@packet
    ld bc,@end-@packet
    rst.lil 18h
    jp w3d_vdplet_wait_reply
@packet:
    db 23,0,W3D_VDPL_SELECTOR
    dw 12
    db 1,5
@token: dw 0
@handle: dw 0
    dw WP_NATIVE_BUFFER
@offset: db 0,0,0,0
@end:
; BC bytes, DE destination. All replies validated by existing request logic.
wp_native_read:
    ld (wp_native_left),bc
    ld (wp_native_dest),de
@word:
    call wp_native_read16
    ret c
    ld de,(wp_native_dest)
    ld a,l
    ld (de),a
    inc de
    ld a,h
    ld (de),a
    inc de
    ld (wp_native_dest),de
    ld hl,(wp_native_offset)
    inc hl
    inc hl
    ld (wp_native_offset),hl
    ld hl,(wp_native_left)
    dec hl
    dec hl
    ld (wp_native_left),hl
    ld a,h
    or l
    jr nz,@word
    or a
    ret
wp_collect_native:
    ld hl,0
    ld (wp_native_offset),hl
    ld de,wp_native_header
    ld bc,16
    call wp_native_read
    ret c
    ld hl,(wp_native_header)
    ld de,04e5057h                 ; "WPN"; fourth byte checked separately
    or a
    sbc hl,de
    jp nz,@bad
    ld a,(wp_native_header+3)
    cp '1'
    jp nz,@bad
    ld hl,(wp_native_header+4)
    ld de,1
    or a
    sbc hl,de
    jp nz,@bad
    ld a,(wp_native_header+7)
    or a
    jp nz,@bad
    ld a,(wp_count)
    ld hl,(wp_native_header+8)
    ld de,0
    ld e,a
    or a
    sbc hl,de
    jp nz,@bad
    ld a,(wp_native_header+11)
    or a
    jp nz,@bad
    ld hl,wp_records
    ld (wp_native_record),hl
    xor a
    ld (wp_native_index),a
@record:
    ld de,wp_native_sample
    ld bc,20
    call wp_native_read
    ret c
    ld hl,(wp_native_sample)
    ld de,0
    ld a,(wp_native_index)
    ld e,a
    or a
    sbc hl,de
    jr nz,@bad
    ld a,(wp_native_sample+3)
    or a
    jr nz,@bad
    ld ix,(wp_native_record)
    ld a,(wp_native_sample+4)
    cp (ix+46)
    jr nz,@bad
    ld a,(wp_native_sample+5)
    cp (ix+47)
    jr nz,@bad
    ld a,(wp_native_sample+6)
    ld b,a
    ld a,(wp_native_sample+7)
    or b
    jr nz,@bad
    push ix
    pop hl
    ld de,30
    add hl,de
    ex de,hl
    ld hl,wp_native_sample+8
    ld bc,12
    ldir
    set 1,(ix+42)
    push ix
    pop hl
    ld de,60
    add hl,de
    ex de,hl
    ld hl,wp_native_header+12
    ld bc,4
    ldir
    ld de,WP_RECORD_BYTES
    ld hl,(wp_native_record)
    add hl,de
    ld (wp_native_record),hl
    ld a,(wp_native_index)
    inc a
    ld (wp_native_index),a
    ld b,a
    ld a,(wp_count)
    cp b
    jp nz,@record
    jp wp_native_reset
@bad:
    scf
    ret
    .endif

wp_icon_upload:
    db 23,0,0a0h
    dw WP_ICON_BUFFER
    db 2
    db 23,0,0a0h
    dw WP_ICON_BUFFER
    db 0
    dw 24*32
wp_icon_upload_end:
wp_icon_create:
    db 23,0,0a0h
    dw WP_ICON_BUFFER
    db 14
    db 23,27,020h
    dw WP_ICON_BUFFER
    db 23,27,021h
    dw 24,32
    db 1
wp_icon_create_end:
wp_clear_buffers:
    db 23,0,0a0h
    dw WP_ICON_BUFFER
    db 2
    .if W3D_PROFILE_NATIVE
    db 23,0,0a0h
    dw WP_NATIVE_BUFFER
    db 2
    .endif
wp_clear_buffers_end:
    .if W3D_PROFILE_NATIVE
wp_native_create:
    db 23,0,0a0h
    dw WP_NATIVE_BUFFER
    db 2
    db 23,0,0a0h
    dw WP_NATIVE_BUFFER
    db 3
    dw 12056
wp_native_create_end:
    .endif
wp_icon_pixels:
    include "wolf3d_profile_icon.inc"
wp_filename: db "WOLFPROF.BIN",0
wp_ok_message: db "PROFILE: WOLFPROF.BIN; nominal 1ms clock, logging gaps excluded by decoder.",13,10,0
wp_error_message: db "PROFILE stopped/status (1 timer busy, 2 full, 3 disk, 4 protocol/unsafe, 5 timer restore): ",0
wp_header:
    db "WPF1",1,W3D_RENDER_BACKEND,1,W3D_PROFILE_NATIVE
    dw 0,WP_RECORD_BYTES
    ds 20                         ; filled before first write

; Only this range is cleared on entry. Padding bytes in records/header are
; initialized explicitly: ez80asm DS defaults to FF, not zero.
wp_state:
wp_active: db 0
wp_owned: db 0
wp_status: db 0
wp_game_open: db 0
wp_pending: db 0
wp_count: db 0
wp_due: db 0
wp_input_valid: db 0
wp_new_session: db 0
wp_file_created: db 0
wp_file: db 0
wp_old_ctl: db 0
wp_old_iss: db 0
wp_old_vector: dl 0
wp_ticks: dl 0
wp_sequence: dl 0
wp_block: dl 0
wp_dropped: dl 0
wp_next: dl 0
wp_current: dl 0
wp_input_start: dl 0
wp_input_last: dl 0
wp_input_gap: dl 0
wp_sim_cost: dl 0
wp_gap_start: dl 0
wp_last_flush: dl 0
wp_write_bytes: dl 0
wp_previous_gap: ds 16
    .if W3D_PROFILE_NATIVE
wp_native_offset: dl 0
wp_native_left: dl 0
wp_native_dest: dl 0
wp_native_record: dl 0
wp_native_index: db 0
wp_native_header: ds 16
wp_native_sample: ds 20
    .endif
wp_records: ds WP_CAPACITY*WP_RECORD_BYTES
wp_state_end:
