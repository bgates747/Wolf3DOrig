; WOLF-PERF-001. Task-only harness; production files are copied, never edited.
; PRT donor: Rally RALLY-28/custom-vdp/paced-road/control/source/prt.inc.
; 72*256 /18.432MHz = nominal 1ms. MOS vector borrowed/restored via API.
wp_prt_init:
    in0 a,(083h)
    ld (wp_old_ctl),a
    and 041h
    jp nz,wp_failed
    in0 a,(092h)
    ld (wp_old_iss),a
    and 0f3h
    out0 (092h),a
    ld hl,wp_irq
    ld e,00ch
    push ix
    push iy
    MOSCALL 14h
    pop iy
    pop ix
    ld (wp_old_vector),hl
    ld hl,0
    ld (wp_ticks),hl
    ld hl,72
    out0 (084h),l
    out0 (085h),h
    ld a,00eh
    out0 (083h),a
    ld a,05fh
    out0 (083h),a
    ld a,1
    ld (wp_owned),a
    ret
wp_prt_stop:
    ld a,(wp_owned)
    or a
    ret z
    xor a
    out0 (083h),a
    ld a,(wp_old_iss)
    out0 (092h),a
    ld hl,(wp_old_vector)
    ld e,00ch
    push ix
    push iy
    MOSCALL 14h
    pop iy
    pop ix
    ld de,wp_irq
    or a
    sbc hl,de
    jp nz,wp_failed
    ld a,1
    ld (wp_restored),a
    ld a,(wp_old_ctl)
    and 07eh
    out0 (083h),a
    xor a
    ld (wp_owned),a
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
wp_clock:
    MOSCALL mos_sysvars
    ld hl,(ix+sysvar_time)
    ret
wp_run:
    push ix
    push iy
    ld hl,0
    add hl,sp
    ld (wp_entry_sp),hl
    ld hl,wp_before_name
    call wp_dump_code
    xor a
    ld (w3d_audio_sfx_enabled),a
    ld (w3d_music_enabled),a
    ld a,(w3d_actor_count)
    or a
    jp nz,wp_failed
    call wp_prt_init
    ; Dedicated diagnostic log. No production ID is reused.
    ld bc,0f000h
    ld de,12056
    call w3d_vdplet_create_zero_buffer
    jp c,wp_failed
    ; Full initial snapshot and two page warm-ups, entirely outside timing.
    call w3d_mark_full_level_dirty
    call wp_warm_frame
    ld a,1
    ld (w3d_player_dirty),a
    call wp_warm_frame
    ; Reset native log after warm-up, retaining configured renderer.
    ld bc,100
    ld de,W3D_VDPLET_ARGUMENT_BUFFER
    call w3d_vdplet_send_run
    jp c,wp_failed
    call w3d_vdplet_wait_run
    jp c,wp_failed
    ; ez80asm DS emits 0xff padding: explicitly clear bounded unused slots.
    xor a
    ld hl,wp_rows
    ld (hl),a
    ld de,wp_rows+1
    ld bc,600*27-1
    ldir
    ld hl,wp_rows
    ld (wp_row_ptr),hl
    ld hl,0
    ld (wp_n),hl
    ld (wp_count),hl
    ; Empty 600-iteration control. No subtraction in reported timing.
    ld hl,(wp_ticks)
    ld (wp_empty_start),hl
    ld bc,600
@empty:
    dec bc
    ld a,b
    or c
    jr nz,@empty
    ld hl,(wp_ticks)
    ld de,(wp_empty_start)
    or a
    sbc hl,de
    ld (wp_empty_ticks),hl
    call wp_clock
    ld (wp_mos_start),hl
    ld hl,(wp_ticks)
    ld (wp_prt_start),hl
wp_next:
    .if WP_MODE=3
@pace:
    call wp_clock
    ld de,(wp_mos_start)
    or a
    sbc hl,de
    ; Bounded workload <65536 MOS ticks: zero HLU then exact u16 /4.
    ld a,0
    push hl
    pop de
    ld hl,0
    ld h,d
    ld l,e
    srl h
    rr l
    srl h
    rr l
    ld de,600
    push hl
    or a
    sbc hl,de
    pop hl
    jr c,@bounded
    ld hl,600
@bounded:
    ld de,(wp_n)
    push hl
    or a
    sbc hl,de
    pop hl
    jr z,@pace
    jr c,@pace
    ld (wp_n),hl
    .else
    ld hl,(wp_n)
    inc hl
    ld (wp_n),hl
    .endif
    ld ix,(wp_row_ptr)
    ld (ix+0),hl
    ld hl,(wp_ticks)
    ld (ix+6),hl
    ; Exact scripted pose: precomputed floor(720*n/600) mod360.
    ld hl,(wp_n)
    dec hl
    add hl,hl
    ld de,wp_angles
    add hl,de
    ld a,(hl)
    ld (w3d_player_pose+8),a
    inc hl
    ld a,(hl)
    ld (w3d_player_pose+9),a
    ld a,1
    ld (w3d_player_dirty),a
    ld (w3d_world_dirty),a
    call w3d_promote_render_visible_actors
    call w3d_load_player_angle
    ld ix,(wp_row_ptr)
    ld (ix+3),hl
    ld hl,(wp_ticks)
    ld (ix+9),hl
    call w3d_vdplet_batch_prepare
    jp c,wp_failed
    ld (wp_batch_address),hl
    ld (wp_batch_size),de
    ld ix,(wp_row_ptr)
    ld (ix+24),de
    ld hl,(wp_ticks)
    ld (ix+12),hl
    .if WP_MODE=1
    ; CPU-only serializer lifecycle; no upload/RUN, separate fresh process.
    call w3d_vdplet_batch_mark_submitted
    call w3d_vdplet_batch_accept_success
    jp c,wp_failed
    ld ix,(wp_row_ptr)
    ld hl,(wp_ticks)
    ld (ix+15),hl
    ld (ix+18),hl
    ld (ix+21),hl
    .else
    ld hl,(wp_batch_address)
    ld de,(wp_batch_size)
    ld bc,W3D_VDPLET_UPDATE_BUFFER
    call w3d_vdplet_upload_buffer
    jp c,wp_failed
    call w3d_mark_render_submitted
    jp c,wp_failed
    ld bc,W3P_ENTRY_APPLY_AND_RENDER
    ld de,W3D_VDPLET_ARGUMENT_BUFFER
    call w3d_vdplet_send_run
    jp c,wp_failed
    call w3d_vdplet_batch_mark_submitted
    ld ix,(wp_row_ptr)
    ld hl,(wp_ticks)
    ld (ix+15),hl
    call w3d_vdplet_wait_run
    jp c,wp_failed
    call w3d_vdplet_batch_accept_success
    jp c,wp_failed
    xor a
    ld (w3d_render_in_flight),a
    ld (w3d_async_owner),a
    ld ix,(wp_row_ptr)
    ld hl,(wp_ticks)
    ld (ix+18),hl
    .if WP_MODE=3
    call w3d_vdu_present
    ; Ordered INFO fence proves parser passed C3 (swap/vblank included).
    call w3d_vdplet_query_identity
    jp c,wp_failed
    .endif
    ld ix,(wp_row_ptr)
    ld hl,(wp_ticks)
    ld (ix+21),hl
    .endif
    ld hl,(wp_count)
    inc hl
    ld (wp_count),hl
    ld hl,(wp_row_ptr)
    ld de,27
    add hl,de
    ld (wp_row_ptr),hl
    ld hl,(wp_n)
    ld de,600
    or a
    sbc hl,de
    jp c,wp_next
    ld hl,(wp_ticks)
    ld (wp_prt_end),hl
    call wp_clock
    ld (wp_mos_end),hl
    call wp_prt_stop
    ; Presentation is outside unpaced hidden-frame capacity interval.
    .if WP_MODE=2
    call w3d_vdu_present
    call w3d_vdplet_query_identity
    jp c,wp_failed
    .endif
    ; Read the native diagnostic log only AFTER all timing has stopped.
    .if WP_MODE>1
    ld hl,(wp_count)
    add hl,hl
    add hl,hl
    push hl
    add hl,hl
    add hl,hl
    pop de
    add hl,de
    ld de,16
    add hl,de
    ld (wp_native_size),hl
    ld hl,0
    ld (wp_read_offset),hl
    ld hl,wp_native
    ld (wp_read_ptr),hl
@read:
    call wp_read16
    jp c,wp_failed
    ld de,(wp_read_ptr)
    ld a,l
    ld (de),a
    inc de
    ld a,h
    ld (de),a
    inc de
    ld (wp_read_ptr),de
    ld hl,(wp_read_offset)
    inc hl
    inc hl
    ld (wp_read_offset),hl
    ld de,(wp_native_size)
    or a
    sbc hl,de
    jr c,@read
    ld hl,wp_native_filename
    ld de,(wp_native_size)
    ld ix,wp_native
    call wp_write
    jp c,wp_failed
    .endif
    ld a,1
    ld (wp_status),a
    ; Fixed bounded output includes count and zero-filled unused row slots.
    ld hl,wp_filename
    ld de,wp_result_end-wp_result
    ld ix,wp_result
    call wp_write
    jp c,wp_failed
    ld hl,wp_clear_log
    ld bc,wp_clear_log_end-wp_clear_log
    rst.lil 18h
    call w3d_vdplet_query_identity
    jp c,wp_failed
    ld hl,0
    add hl,sp
    ld (wp_exit_sp),hl
    ld hl,wp_after_name
    call wp_dump_code
    ld hl,wp_stack_name
    ld de,256
    ld ix,0bfe00h
    call wp_write
    jp c,wp_failed
    ld hl,wp_done_msg
    call printString
    pop iy
    pop ix
    ret
wp_dump_code:
    ld de,wp_result_end-040000h
    ld ix,040000h
    call wp_write
    jp c,wp_failed
    ret
wp_warm_frame:
    call w3d_submit_dirty_world_render
    jp c,wp_failed
    call w3d_vdplet_wait_run
    jp c,wp_failed
    call w3d_vdplet_batch_accept_success
    jp c,wp_failed
    xor a
    ld (w3d_render_in_flight),a
    ld (w3d_async_owner),a
    call w3d_vdu_present
    call w3d_vdplet_query_identity
    jp c,wp_failed
    ret
wp_read16:
    ld hl,(wp_read_offset)
    ; ADL24 OK: four-byte offset storage; fourth byte is zero and untouched.
    ld (@offset),hl
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
    db 1,0
    dw 0f000h
@offset: db 0,0,0,0
@end:
wp_write:
    ld (wp_write_size),de
    ld (wp_write_pointer),ix
    ld c,6 ; write + create-new, never overwrite evidence
    MOSCALL mos_fopen
    or a
    jr z,@failed
    ld (wp_file_handle),a
    ld c,a
    ld hl,(wp_write_pointer)
    ld de,(wp_write_size)
    MOSCALL mos_fwrite
    push de
    ld a,(wp_file_handle)
    ld c,a
    MOSCALL mos_fclose
    pop hl
    ld de,(wp_write_size)
    or a
    sbc hl,de
    ret z
@failed:
    scf
    ret
wp_failed:
    ; Stop owned PRT and verify restoration even on a rejected transaction.
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
    ; A second idempotent exchange proves the table contains the old vector.
    ld hl,(wp_old_vector)
    ld e,00ch
    MOSCALL 14h
    ld de,(wp_old_vector)
    or a
    sbc hl,de
    jr nz,@not_restored
    ld a,1
    ld (wp_restored),a
@not_restored:
    ld a,(wp_old_ctl)
    and 07eh
    out0 (083h),a
    xor a
    ld (wp_owned),a
@report:
    ld a,(wp_restored)
    or a
    ld hl,wp_fail_msg
    jr z,@print
    ld hl,wp_fail_restored_msg
@print:
    call printString
@hold: jr @hold
wp_clear_log: db 23,0,0a0h,0,0f0h,2
wp_clear_log_end:
wp_old_ctl: db 0
wp_old_iss: db 0
wp_old_vector: dl 0
wp_owned: db 0
wp_ticks: dl 0
wp_empty_start: dl 0
wp_n: dl 0
wp_row_ptr: dl 0
wp_batch_address: dl 0
wp_batch_size: dl 0
wp_read_offset: dl 0
wp_read_ptr: dl 0
wp_write_size: dl 0
wp_write_pointer: dl 0
wp_file_handle: db 0
wp_entry_sp: dl 0
wp_exit_sp: dl 0
wp_before_name: asciz "before.bin"
wp_after_name: asciz "after.bin"
wp_stack_name: asciz "stack.bin"
wp_filename: asciz "timing.bin"
wp_native_filename: asciz "native.bin"
wp_done_msg: db "WOLF-PERF-001 COMPLETE",13,10,0
wp_fail_msg: db "WOLF-PERF-001 FAILED TIMER-UNRESTORED",13,10,0
wp_fail_restored_msg: db "WOLF-PERF-001 FAILED TIMER-RESTORED",13,10,0
wp_result:
    db "WPF1",1,WP_MODE
wp_status: db 0
wp_restored: db 0
wp_count: dl 0
wp_prt_start: dl 0
wp_prt_end: dl 0
wp_mos_start: dl 0
wp_mos_end: dl 0
wp_empty_ticks: dl 0
wp_native_size: dl 0
    db 34,36,0,0 ; tile x,y, enemy count, reserved
wp_rows: ds 600*27
wp_result_end:
wp_native: ds 12056
wp_angles:
    include "angles.inc"
