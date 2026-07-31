; =============================================================================
; Interactive player motion for the Wolf3D render fixture.
;
; Simulation advances in exact four-tick quanta from MOS's 120 Hz clock:
; 30 fixed updates per second. Rendering is capped by those same quanta and
; remains callback-gated to one frame in flight. If rendering falls behind,
; simulation catches up before the next pose snapshot is submitted.
;
; Controls:
;   W/S         forward/backward
;   A/D         strafe left/right
;   Left/Right  turn left/right
;   Escape      clean exit
;
; This inspection fixture intentionally performs no collision detection.
; =============================================================================

W3D_SIMULATION_STEP_TICKS:      equ 4
W3D_SIMULATION_MAX_STEPS:       equ 4
W3D_SIMULATION_MAX_BACKLOG:     equ 32
W3D_PLAYER_TURN_STEP_DEGREES:   equ 3

W3D_CONTROL_W:                  equ 00000001b
W3D_CONTROL_S:                  equ 00000010b
W3D_CONTROL_A:                  equ 00000100b
W3D_CONTROL_D:                  equ 00001000b
W3D_CONTROL_LEFT:               equ 00010000b
W3D_CONTROL_RIGHT:              equ 00100000b

; Seed the mutable pose from the generated level fixture and start with no
; pending simulation time or unsent change. The fixture command stream has
; already submitted this exact pose for the unconditional first render.
w3d_initialize_motion_state:
    ld hl,w3d_fixture_initial_player_pose
    ld de,w3d_player_pose
    ld bc,w3d_fixture_initial_player_pose_end-w3d_fixture_initial_player_pose
    ldir
    xor a
    ld (w3d_player_dirty),a
    ld (w3d_controls),a
    ld hl,0
    ld (w3d_simulation_accumulator),hl
    call w3d_reset_keys
    ret

; OR MOS's current held-key map into a local latch. Sampling on every
; foreground pass catches short taps; resetting and immediately resampling
; after each fixed quantum makes held keys active during every catch-up step.
w3d_poll_keys:
    MOSCALL mos_getkbmap
    ld iy,w3d_keyboard_masks
    ld b,16
@loop:
    ld a,(ix)
    or (iy)
    ld (iy),a
    inc ix
    inc iy
    djnz @loop
    ret

w3d_reset_keys:
    ld iy,w3d_keyboard_masks
    xor a
    ld b,16
@loop:
    ld (iy),a
    inc iy
    djnz @loop
    ret

; Add the latest full 24-bit MOS-clock delta and clamp exceptional stalls.
w3d_accumulate_simulation_time:
    ld hl,(w3d_elapsed_ticks)
    ld de,(w3d_simulation_accumulator)
    add hl,de
    ld de,W3D_SIMULATION_MAX_BACKLOG+1
    or a
    sbc hl,de
    jr c,@below_limit
    ld hl,W3D_SIMULATION_MAX_BACKLOG
    ld (w3d_simulation_accumulator),hl
    ret
@below_limit:
    add hl,de
    ld (w3d_simulation_accumulator),hl
    ret

; Advance at most four 30 Hz quanta per foreground pass. Mainloop refuses to
; submit a new render until any remaining complete quantum is also consumed.
w3d_run_simulation_batch:
    ld a,W3D_SIMULATION_MAX_STEPS
    ld (w3d_simulation_steps_remaining),a
@next:
    ld a,(w3d_exit_requested)
    or a
    ret nz
    call w3d_take_simulation_step
    ret c
    call w3d_simulate_player_step
    call w3d_reset_keys
    call w3d_poll_keys
    ld hl,w3d_simulation_steps_remaining
    dec (hl)
    jr nz,@next
    ret

; Carry means fewer than four 120 Hz ticks remain.
w3d_take_simulation_step:
    ld hl,(w3d_simulation_accumulator)
    ld de,W3D_SIMULATION_STEP_TICKS
    or a
    sbc hl,de
    ret c
    ld (w3d_simulation_accumulator),hl
    or a
    ret

; Convert the latched FabGL virtual-key map into a compact control mask.
w3d_sample_controls:
    ld ix,w3d_keyboard_masks
    xor a
    bit 1,(ix+4)                 ; W
    jr z,@not_w
    or W3D_CONTROL_W
@not_w:
    bit 1,(ix+10)                ; S
    jr z,@not_s
    or W3D_CONTROL_S
@not_s:
    bit 1,(ix+8)                 ; A
    jr z,@not_a
    or W3D_CONTROL_A
@not_a:
    bit 2,(ix+6)                 ; D
    jr z,@not_d
    or W3D_CONTROL_D
@not_d:
    bit 1,(ix+3)                 ; Left arrow
    jr z,@not_left
    or W3D_CONTROL_LEFT
@not_left:
    bit 1,(ix+15)                ; Right arrow
    jr z,@done
    or W3D_CONTROL_RIGHT
@done:
    ld (w3d_controls),a
    ret

; One fixed 30 Hz input/integration quantum. Rotation precedes translation,
; matching the established local-transform fixtures' responsive convention.
w3d_simulate_player_step:
    call w3d_sample_controls

    ld a,(w3d_controls)
    and W3D_CONTROL_LEFT|W3D_CONTROL_RIGHT
    cp W3D_CONTROL_LEFT
    jr nz,@check_right
    ld de,W3D_PLAYER_TURN_STEP_DEGREES
    call w3d_rotate_player
    jr @translation
@check_right:
    cp W3D_CONTROL_RIGHT
    jr nz,@translation
    ld de,-W3D_PLAYER_TURN_STEP_DEGREES
    call w3d_rotate_player

@translation:
    ld a,(w3d_controls)
    bit 0,a                        ; W: current heading
    jr z,@not_w
    ld de,0
    call w3d_move_at_heading_offset
@not_w:
    ld a,(w3d_controls)
    bit 1,a                        ; S: opposite heading
    jr z,@not_s
    ld de,180
    call w3d_move_at_heading_offset
@not_s:
    ld a,(w3d_controls)
    bit 2,a                        ; A: 90 degrees left
    jr z,@not_a
    ld de,90
    call w3d_move_at_heading_offset
@not_a:
    ld a,(w3d_controls)
    bit 3,a                        ; D: 90 degrees right
    ret z
    ld de,270
    jp w3d_move_at_heading_offset

; DE is a signed turn delta; the persistent wire angle remains 0..359.
w3d_rotate_player:
    call w3d_load_player_angle
    add hl,de
    bit 7,h
    jr z,@not_negative
    ld de,360
    add hl,de
    jr @store
@not_negative:
    ld de,360
    or a
    sbc hl,de
    jr nc,@store
    add hl,de
@store:
    ld a,l
    ld (w3d_player_pose+8),a
    ld a,h
    ld (w3d_player_pose+9),a
    ld a,1
    ld (w3d_player_dirty),a
    ret

w3d_load_player_angle:
    ld hl,0
    ld a,(w3d_player_pose+8)
    ld l,a
    ld a,(w3d_player_pose+9)
    ld h,a
    ret

; Move one fixed distance along playerAngle+DE. Offsets used here are
; non-negative and below 360; one subtraction therefore normalizes them.
w3d_move_at_heading_offset:
    call w3d_load_player_angle
    add hl,de
    ld de,360
    or a
    sbc hl,de
    jr nc,@normalized
    add hl,de
@normalized:
    jp w3d_apply_heading_delta

; HL is a normalized integer-degree heading. Each table entry contains a
; signed 24-bit dx followed by signed 24-bit dy. Computing angle*6 uses only
; register adds; translation uses bytewise 32-bit addition with sign extension.
w3d_apply_heading_delta:
    ld de,0
    ld e,l
    ld d,h
    add hl,hl                    ; 2 * angle
    add hl,de                    ; 3 * angle
    add hl,hl                    ; 6 * angle
    ld de,w3d_motion_delta_table
    add hl,de

    ld ix,w3d_player_pose
    call w3d_add_signed_delta24
    inc hl
    ld ix,w3d_player_pose+4
    call w3d_add_signed_delta24

    ld a,1
    ld (w3d_player_dirty),a
    ret

; Add the signed 24-bit little-endian value at HL to the 32-bit value at IX.
; Returns with HL pointing at the delta's sign byte.
w3d_add_signed_delta24:
    ld a,(ix+0)
    add a,(hl)
    ld (ix+0),a
    inc hl
    ld a,(ix+1)
    adc a,(hl)
    ld (ix+1),a
    inc hl
    ld a,(ix+2)
    adc a,(hl)
    ld (ix+2),a
    ld a,0
    bit 7,(hl)
    jr z,@positive
    dec a
@positive:
    adc a,(ix+3)
    ld (ix+3),a
    ret

; Send only the mutable player pose and render request. Map, doors, and assets
; remain resident in VDP world state. Dirty is cleared for this exact snapshot;
; later simulation steps during the in-flight render set it again.
w3d_submit_dirty_player_render:
    call w3d_mark_render_submitted
    ld hl,w3d_player_pose
    ld de,@player_pose
    ld bc,10
    ldir
    xor a
    ld (w3d_player_dirty),a
    ld hl,@command
    ld bc,@end-@command
    rst.lil 18h
    ret
@command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,2
@player_pose:
    ds 10
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,7
@end:

w3d_keyboard_masks:
    ds 16

w3d_player_pose:
    ds 10                         ; int32 x, int32 y, uint16 degrees

w3d_player_dirty:
    db 0

w3d_controls:
    db 0

w3d_simulation_accumulator:
    dl 0

w3d_simulation_steps_remaining:
    db 0

    include "wolf3d_motion_table.inc"
