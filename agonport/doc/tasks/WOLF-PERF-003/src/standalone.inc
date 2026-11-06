; Task-only transport adapter. Native control packets use W3DT, schema 1,
; success byte, monotonically incremented u16 cookie and u16 result.
; The MOS interrupt callback only captures; foreground owns all validation.
wp_a_prepare:
    xor a
    ld (wp_a_packets),a
    ld hl,0
    ld (wp_a_used),hl
    ld a,1
    ld (wp_a_capture),a
    call w3d_submit_dirty_world_render
    push af
    xor a
    ld (wp_a_capture),a
    pop af
    ret c
    ld a,(wp_a_packets)
    cp 2
    jp nz,wp_failed
    ld de,(wp_a_used)
    ld hl,24 ; pose command 17 + render command 7
    or a
    sbc hl,de
    jp nz,wp_failed
    ld hl,wp_a_wire
    or a
    ret
wp_a_capture_wire:
    ld a,(wp_a_capture)
    or a
    jr nz,@capture
    rst.lil 18h
    ret
@capture:
    push af
    push bc
    push de
    push hl
    ld a,b
    or a
    jp nz,wp_failed
    ld a,(wp_a_packets)
    cp 2
    jp nc,wp_failed
    ld a,c
    cp 18
    jp nc,wp_failed
    ld a,(wp_a_packets)
    or a
    jr nz,@second
    ld a,c
    ld (wp_a_len1),a
    jr @copy
@second:
    ld a,c
    ld (wp_a_len2),a
@copy:
    ld de,0
    ld a,(wp_a_used)
    ld e,a
    add a,c
    ld (wp_a_used),a
    push hl
    ld hl,wp_a_wire
    add hl,de
    ex de,hl
    pop hl
    ldir
    ld a,(wp_a_packets)
    inc a
    ld (wp_a_packets),a
    pop hl
    pop de
    pop bc
    pop af
    ret
wp_a_submit:
    ld hl,wp_a_wire
    ld bc,17
    rst.lil 18h
    ld hl,wp_a_wire+17
    ld bc,7
    rst.lil 18h
    or a
    ret
wp_a_retire:
    xor a
    ld (w3d_render_in_flight),a
    ld (w3d_async_owner),a
    ld (w3d_completion_ready),a
    ret
wp_a_wait:
    call wp_clock
    ld (wp_a_wait_start),hl
@wait:
    ld a,(w3d_callback_error)
    or a
    scf
    ret nz
    ld a,(w3d_completion_ready)
    or a
    jr nz,@done
    call wp_clock
    ld de,(wp_a_wait_start)
    or a
    sbc hl,de
    ld de,240
    or a
    sbc hl,de
    jr c,@wait
    scf
    ret
@done:
    call w3d_consume_render_completion
    ld a,(w3d_callback_error)
    or a
    ret z
    scf
    ret
wp_a_create_log:
    ld hl,@packet
    ld bc,@end-@packet
    rst.lil 18h
    jp w3d_audio_wait_for_vdp_ingress
@packet:
    db 23,0,0a0h
    dw 0f000h
    db 2
    db 23,0,0a0h
    dw 0f000h
    db 3
    dw 12056
@end:
wp_a_reset:
    ld a,240
    ld hl,0
    jp wp_a_control
wp_a_fence:
    ; Both backends use the SAME stock mode-info ordered parser fence.
    jp w3d_audio_wait_for_vdp_ingress
wp_a_read16:
    ld a,241
    ld hl,(wp_read_offset)
    jp wp_a_control
wp_a_control:
    ld (@op),a
    ld a,l
    ld (@offset),a
    ld a,h
    ld (@offset+1),a
    ld hl,(wp_a_cookie)
    inc hl
    ld (wp_a_cookie),hl
    ld a,l
    ld (@cookie),a
    ld a,h
    ld (@cookie+1),a
    xor a
    ld (wp_a_ready),a
    ld hl,@packet
    ld bc,@end-@packet
    rst.lil 18h
    call wp_clock
    ld (wp_a_wait_start),hl
@wait:
    ld a,(wp_a_ready)
    or a
    jr nz,@reply
    call wp_clock
    ld de,(wp_a_wait_start)
    or a
    sbc hl,de
    ld de,240
    or a
    sbc hl,de
    jr c,@wait
    scf
    ret
@reply:
    ld a,(wp_a_reply+4)
    cp 1
    scf
    ret nz
    ld a,(wp_a_reply+5)
    cp 1
    scf
    ret nz
    ld a,(wp_a_cookie)
    ld hl,wp_a_reply+6
    cp (hl)
    scf
    ret nz
    inc hl
    ld a,(wp_a_cookie+1)
    cp (hl)
    scf
    ret nz
    ld hl,0
    ld a,(wp_a_reply+8)
    ld l,a
    ld a,(wp_a_reply+9)
    ld h,a
    or a
    ret
@packet:
    db 23,0,0a0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4ah
@op: db 240
@cookie: dw 0
@offset: dw 0
@end:
wp_a_try_capture:
    ld a,(ix+0)
    cp 'W'
    jr nz,@other
    ld a,(ix+1)
    cp '3'
    jr nz,@other
    ld a,(ix+2)
    cp 'D'
    jr nz,@other
    ld a,(ix+3)
    cp 'T'
    jr nz,@other
    push ix
    pop hl
    ld de,wp_a_reply
    ld bc,10
    ldir
    ld a,1
    ld (wp_a_ready),a
    scf
    ret
@other:
    or a
    ret
wp_a_capture: db 0
wp_a_packets: db 0
wp_a_len1: db 0
wp_a_len2: db 0
wp_a_used: dl 0
wp_a_wire: ds 34
wp_a_wait_start: dl 0
wp_a_cookie: dl 0
wp_a_ready: db 0
wp_a_reply: ds 10
