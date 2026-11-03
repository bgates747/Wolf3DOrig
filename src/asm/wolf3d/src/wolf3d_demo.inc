; =============================================================================
; Original Episode 1 recorded-demo playback.
;
; Generated assets retain the exact WL1 button/control records.  A record
; owns four original 70-Hz tics.  The 30-Hz simulation advances them with the
; exact rational cadence: add 70 after each fixed step and consume a record
; whenever the accumulator reaches 4*30=120.  Physical input aborts a demo
; back to the control panel and never becomes an application Escape request.
; =============================================================================

W3D_DEMO_CADENCE_ADD:       equ 70
W3D_DEMO_CADENCE_LIMIT:     equ 120
W3D_DEMO_DIFFICULTY_HARD:   equ 3

; Select the next stream for the attract loop and publish its map/difficulty.
w3d_demo_prepare_next:
    ld a,(w3d_demo_next_index)
    cp W3D_DEMO_COUNT
    jr c,@index_ready
    xor a
@index_ready:
    ld (w3d_demo_selected_index),a
    inc a
    cp W3D_DEMO_COUNT
    jr c,@store_next
    xor a
@store_next:
    ld (w3d_demo_next_index),a

    ld a,(w3d_demo_selected_index)
    ld de,0
    ld e,a
    ld hl,0
    ld l,a
    add hl,hl                    ; 2*index
    add hl,de                    ; 3*index
    add hl,hl                    ; 6*index
    ld de,w3d_demo_stream_table
    add hl,de
    ld de,(hl)
    ld (w3d_demo_stream_start),de
    inc hl
    inc hl
    inc hl
    ld de,(hl)
    ld (w3d_demo_stream_end),de
    ld hl,(w3d_demo_stream_start)
    ld a,(hl)
    ld (w3d_demo_level),a
    ld a,W3D_DEMO_DIFFICULTY_HARD
    ld (w3d_requested_difficulty),a
    ld a,1
    ld (w3d_demo_active),a
    xor a
    ld (w3d_demo_finished),a
    ret

; Called after ordinary level-state initialization. The prepared stream must
; match the level selected by the gameplay loader.
w3d_demo_begin_session:
    ld a,(w3d_demo_active)
    or a
    ret z
    ld hl,(w3d_demo_stream_start)
    ld de,W3D_DEMO_HEADER_SIZE
    add hl,de
    ld (w3d_demo_cursor),hl
    xor a
    ld (w3d_demo_cadence),a
    ld (w3d_demo_finished),a
    ld (w3d_demo_turn_fraction+0),a
    ld (w3d_demo_turn_fraction+1),a
    ld (w3d_demo_back_fraction),a
    ret

w3d_demo_cancel:
    xor a
    ld (w3d_demo_active),a
    ld (w3d_demo_finished),a
    ret

; Convert the signed original per-tic controls to this port's 30-Hz distance
; requests. Original forward/strafe Thrust used 150 units at 70 Hz, hence
; magnitude*350 per 30-Hz quantum. Backward used 100, hence magnitude*700/3;
; retain its modulo-three remainder so long runs have no systematic drift.
w3d_demo_prepare_motion_step:
    xor a
    ld (w3d_demo_forward_distance+0),a
    ld (w3d_demo_forward_distance+1),a
    ld (w3d_demo_strafe_distance+0),a
    ld (w3d_demo_strafe_distance+1),a
    ld (w3d_player_thrustspeed+0),a
    ld (w3d_player_thrustspeed+1),a

    ld a,(w3d_demo_control_y)
    or a
    jr z,@strafe
    jp p,@backward
    neg
    call w3d_demo_magnitude_350
    xor a
    ld (w3d_demo_forward_offset+0),a
    ld (w3d_demo_forward_offset+1),a
    jr @store_forward
@backward:
    call w3d_demo_magnitude_back
    ld a,180
    ld (w3d_demo_forward_offset+0),a
    xor a
    ld (w3d_demo_forward_offset+1),a
@store_forward:
    ld a,l
    ld (w3d_demo_forward_distance+0),a
    ld (w3d_player_thrustspeed+0),a
    ld a,h
    ld (w3d_demo_forward_distance+1),a
    ld (w3d_player_thrustspeed+1),a

@strafe:
    ld a,(w3d_demo_buttons)
    bit 1,a
    ret z
    ld a,(w3d_demo_control_x)
    or a
    ret z
    jp p,@strafe_left
    neg
    ld de,270
    jr @strafe_magnitude
@strafe_left:
    ld de,90
@strafe_magnitude:
    push af
    ld a,e
    ld (w3d_demo_strafe_offset+0),a
    ld a,d
    ld (w3d_demo_strafe_offset+1),a
    pop af
    call w3d_demo_magnitude_350
    ld a,l
    ld (w3d_demo_strafe_distance+0),a
    ld a,h
    ld (w3d_demo_strafe_distance+1),a
    ld de,0
    ld a,(w3d_player_thrustspeed+0)
    ld e,a
    ld a,(w3d_player_thrustspeed+1)
    ld d,a
    add.s hl,de
    ld a,l
    ld (w3d_player_thrustspeed+0),a
    ld a,h
    ld (w3d_player_thrustspeed+1),a
    ret

; A=unsigned magnitude -> HL=A*350.
w3d_demo_magnitude_350:
    ld c,a
    ld b,94
    mlt bc
    ld l,0
    ld h,a
    add.s hl,bc
    ret

; A=unsigned magnitude -> HL=floor((A*700+remainder)/3).
w3d_demo_magnitude_back:
    ld d,a
    ld c,a
    ld b,23
    mlt bc
    ld l,0
    ld h,a
    or a
    sbc.s hl,bc                   ; A*(256-23) = A*233
    ld a,d
    ld d,0
    ld e,a
    ld a,(w3d_demo_back_fraction)
    add a,e
    ld e,0
@divide_three:
    cp 3
    jr c,@fraction_ready
    sub 3
    inc e
    jr @divide_three
@fraction_ready:
    ld (w3d_demo_back_fraction),a
    ld d,0
    add.s hl,de
    ret

; Apply original anglefrac semantics at 30 Hz. One signed control unit equals
; 70/(20*30)=7/60 degree per port quantum. The signed remainder survives
; record boundaries, matching the source's persistent anglefrac accumulator.
w3d_demo_apply_turn_step:
    ld a,(w3d_demo_buttons)
    bit 1,a
    ret nz
    ld a,(w3d_demo_control_x)
    or a
    ret z
    ld de,0
    ld e,a
    bit 7,a
    jr z,@signed_x_ready
    dec d
@signed_x_ready:
    push de
    pop hl
    add.s hl,hl                   ; 2x
    add.s hl,hl                   ; 4x
    add.s hl,de                   ; 5x
    add.s hl,de                   ; 6x
    add.s hl,de                   ; 7x
    ld de,0
    ld a,(w3d_demo_turn_fraction+0)
    ld e,a
    ld a,(w3d_demo_turn_fraction+1)
    ld d,a
    add.s hl,de
    bit 7,h
    jr nz,@negative

    ld b,0
@positive_divide:
    ld de,60
    or a
    sbc.s hl,de
    jr c,@positive_remainder
    inc b
    jr @positive_divide
@positive_remainder:
    add.s hl,de
    call w3d_demo_store_turn_fraction
    ld a,b
    or a
    ret z
    ld e,a
    ld d,0
    xor a
    sub e
    ld e,a
    ld a,0
    sbc a,d
    ld d,a
    jp w3d_rotate_player

@negative:
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
    ld b,0
@negative_divide:
    ld de,60
    or a
    sbc.s hl,de
    jr c,@negative_remainder
    inc b
    jr @negative_divide
@negative_remainder:
    add.s hl,de
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
    call w3d_demo_store_turn_fraction
    ld a,b
    or a
    ret z
    ld e,a
    ld d,0
    jp w3d_rotate_player

w3d_demo_store_turn_fraction:
    ld a,l
    ld (w3d_demo_turn_fraction+0),a
    ld a,h
    ld (w3d_demo_turn_fraction+1),a
    ret

w3d_demo_apply_forward_step:
    ld bc,0
    ld a,(w3d_demo_forward_distance+0)
    ld c,a
    ld a,(w3d_demo_forward_distance+1)
    ld b,a
    or c
    ret z
    ld de,0
    ld a,(w3d_demo_forward_offset+0)
    ld e,a
    ld a,(w3d_demo_forward_offset+1)
    ld d,a
    jp w3d_move_at_heading_offset_scaled

w3d_demo_apply_strafe_step:
    ld bc,0
    ld a,(w3d_demo_strafe_distance+0)
    ld c,a
    ld a,(w3d_demo_strafe_distance+1)
    ld b,a
    or c
    ret z
    ld de,0
    ld a,(w3d_demo_strafe_offset+0)
    ld e,a
    ld a,(w3d_demo_strafe_offset+1)
    ld d,a
    jp w3d_move_at_heading_offset_scaled

; Any physical key aborts playback. In particular, Escape is local to the
; demo and must not survive in the application's global shutdown latch.
w3d_demo_latch_input_abort:
    ld hl,w3d_keyboard_masks
    ld b,16
@scan:
    ld a,(hl)
    or a
    jr nz,@abort
    inc hl
    djnz @scan
    ret
@abort:
    ld a,1
    ld (w3d_demo_finished),a
    xor a
    ld (w3d_exit_requested),a
    ret

; Convert the current original record to the port's compact digital controls.
; The compact mask feeds use/combat/observability, while the retained signed
; analog bytes feed the magnitude-preserving motion path.
w3d_demo_sample_controls:
    ld a,(w3d_demo_finished)
    or a
    jr z,@record
    xor a
    ld (w3d_controls),a
    ret
@record:
    ld hl,(w3d_demo_cursor)
    ld a,(hl)
    ld (w3d_demo_buttons),a
    inc hl
    ld a,(hl)
    ld (w3d_demo_control_x),a
    inc hl
    ld a,(hl)
    ld (w3d_demo_control_y),a

    xor a
    ld b,a
    ld a,(w3d_demo_buttons)
    bit 0,a                       ; bt_attack
    jr z,@no_attack
    ld b,W3D_CONTROL_ATTACK
@no_attack:
    bit 3,a                       ; bt_use
    jr z,@movement
    ld a,b
    or W3D_CONTROL_USE
    ld b,a

@movement:
    ld a,(w3d_demo_control_y)
    or a
    jr z,@horizontal
    jp p,@backward
    ld a,b
    or W3D_CONTROL_W
    ld b,a
    jr @horizontal
@backward:
    ld a,b
    or W3D_CONTROL_S
    ld b,a

@horizontal:
    ld a,(w3d_demo_control_x)
    or a
    jr z,@publish
    ld c,a
    ld a,(w3d_demo_buttons)
    bit 1,a                       ; bt_strafe
    jr nz,@strafe
    ld a,c
    or a
    jp p,@turn_right
    ld a,b
    or W3D_CONTROL_LEFT
    ld b,a
    jr @publish
@turn_right:
    ld a,b
    or W3D_CONTROL_RIGHT
    ld b,a
    jr @publish
@strafe:
; Original positive controlx thrusts left; negative thrusts right.
    ld a,c
    or a
    jp p,@strafe_left
    ld a,b
    or W3D_CONTROL_D
    ld b,a
    jr @publish
@strafe_left:
    ld a,b
    or W3D_CONTROL_A
    ld b,a
@publish:
    ld a,b
    ld (w3d_controls),a
    ret

; Advance the rational record clock after one completed 30-Hz simulation step.
w3d_demo_advance_step:
    ld a,(w3d_demo_active)
    or a
    ret z
    ld a,(w3d_demo_finished)
    or a
    ret nz
    ld a,(w3d_demo_cadence)
    add a,W3D_DEMO_CADENCE_ADD
    cp W3D_DEMO_CADENCE_LIMIT
    jr c,@store
    sub W3D_DEMO_CADENCE_LIMIT
    ld hl,(w3d_demo_cursor)
    ld de,W3D_DEMO_RECORD_SIZE
    add hl,de
    ld (w3d_demo_cursor),hl
    ld de,(w3d_demo_stream_end)
    or a
    sbc hl,de
    jr c,@store
    ld a,1
    ld (w3d_demo_finished),a
    xor a
@store:
    ld (w3d_demo_cadence),a
    ret

w3d_demo_active:
    db 0
w3d_demo_finished:
    db 0
w3d_demo_next_index:
    db 0
w3d_demo_selected_index:
    db 0
w3d_demo_level:
    db 0
w3d_demo_cadence:
    db 0
w3d_demo_buttons:
    db 0
w3d_demo_control_x:
    db 0
w3d_demo_control_y:
    db 0
w3d_demo_turn_fraction:
    dw 0
w3d_demo_back_fraction:
    db 0
w3d_demo_forward_distance:
    dw 0
w3d_demo_forward_offset:
    dw 0
w3d_demo_strafe_distance:
    dw 0
w3d_demo_strafe_offset:
    dw 0
w3d_demo_stream_start:
    dl 0
w3d_demo_stream_end:
    dl 0
w3d_demo_cursor:
    dl 0
