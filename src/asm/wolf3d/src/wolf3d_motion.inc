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
;   Space       operate the adjacent door (rising edge)
;   Escape      clean exit
;
; Player collision follows Wolf3D's square PLAYERSIZE AABB and ClipMove
; ordering: combined X/Y, then X only, then Y only. Unlike the DOS tile-wide
; door test, doors collide with the same moving center-plane slab rendered by
; this port's VDP; this lets the player enter either door well. The original
; statinfo[] blocking decorations are represented by a separate 64x64 bitset.
; The eZ80 owns doors, mutable static and pickup state, player inventory, and
; every dirty snapshot sent to the VDP.
; =============================================================================

W3D_SIMULATION_STEP_TICKS:      equ 4
W3D_SIMULATION_MAX_STEPS:       equ 4
W3D_SIMULATION_MAX_BACKLOG:     equ 32
W3D_PLAYER_TURN_STEP_DEGREES:   equ 3
W3D_PLAYER_COLLISION_RADIUS:     equ 05800h

; Original doors traverse 0xffff in 64 ticks at 70 Hz and wait 300 ticks.
; At 30 Hz, 2389,2389,2390 repeating is the exact average travel rate;
; open timers use thirds of an original tick (7 per update, 900 total).
W3D_DOOR_STEP_LO:                equ 0955h
W3D_DOOR_STEP_HI:                equ 0956h
W3D_DOOR_OPEN_TIMER_STEP:        equ 7
W3D_DOOR_OPEN_TIMER_LIMIT:       equ 900

W3D_CONTROL_W:                  equ 00000001b
W3D_CONTROL_S:                  equ 00000010b
W3D_CONTROL_A:                  equ 00000100b
W3D_CONTROL_D:                  equ 00001000b
W3D_CONTROL_LEFT:               equ 00010000b
W3D_CONTROL_RIGHT:              equ 00100000b
W3D_CONTROL_USE:                equ 01000000b

W3D_HUD_DIRTY_HEALTH:           equ 00000001b
W3D_HUD_DIRTY_AMMO:             equ 00000010b
W3D_HUD_DIRTY_KEYS:             equ 00000100b
W3D_HUD_DIRTY_WEAPON:           equ 00001000b
W3D_HUD_DIRTY_SCORE:            equ 00010000b
W3D_HUD_DIRTY_LIVES:            equ 00100000b

; Seed the mutable pose from the generated level fixture and start with no
; pending simulation time or unsent change. The fixture command stream has
; already submitted this exact pose for the unconditional first render.
w3d_initialize_motion_state:
    ld hl,w3d_fixture_initial_player_pose
    ld de,w3d_player_pose
    ld bc,w3d_fixture_initial_player_pose_end-w3d_fixture_initial_player_pose
    ldir
    ld hl,w3d_fixture_initial_doors
    ld de,w3d_doors
    ld bc,w3d_fixture_initial_doors_end-w3d_fixture_initial_doors
    ldir
    ld hl,w3d_fixture_initial_statics
    ld de,w3d_statics
    ld bc,w3d_fixture_initial_statics_end-w3d_fixture_initial_statics
    ldir
    xor a
    ld (w3d_player_dirty),a
    ld (w3d_world_dirty),a
    ld (w3d_controls),a
    ld (w3d_use_was_down),a
    ld (w3d_player_key_flags),a
    ld (w3d_door_motion_phase),a
    ld hl,w3d_door_timers
    ld (hl),a
    ld de,w3d_door_timers+1
    ld bc,W3D_FIXTURE_DOOR_COUNT*2-1
    ldir
    ld hl,w3d_door_dirty
    ld (hl),a
    ld de,w3d_door_dirty+1
    ld bc,W3D_FIXTURE_DOOR_COUNT-1
    ldir
    ld hl,w3d_static_dirty
    ld (hl),a
    ld de,w3d_static_dirty+1
    ld bc,W3D_FIXTURE_STATIC_COUNT-1
    ldir
    ld (w3d_hud_dirty),a
    ld (w3d_pickup_scan_needed),a
    ld (w3d_player_score+0),a
    ld (w3d_player_score+1),a
    ld (w3d_player_score+2),a
    ld (w3d_player_score+3),a
    ld (w3d_player_treasure_count+0),a
    ld (w3d_player_treasure_count+1),a
    ld a,040h
    ld (w3d_player_next_extra+0),a
    ld a,09ch
    ld (w3d_player_next_extra+1),a
    xor a
    ld (w3d_player_next_extra+2),a
    ld (w3d_player_next_extra+3),a
    ld a,100
    ld (w3d_player_health),a
    ld a,8
    ld (w3d_player_ammo),a
    ld a,1
    ld (w3d_player_weapon),a
    ld (w3d_player_best_weapon),a
    ld (w3d_player_chosen_weapon),a
    ld a,3
    ld (w3d_player_lives),a
    xor a
    ld hl,w3d_fixture_tilemap
    ld (w3d_map_ptr),hl
    ld hl,w3d_fixture_static_blocking_bits
    ld (w3d_static_blocking_ptr),hl
    ld hl,w3d_doors
    ld (w3d_doors_ptr),hl
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
    jr z,@not_right
    or W3D_CONTROL_RIGHT
@not_right:
    bit 2,(ix+12)                ; Space / use
    jr z,@done
    or W3D_CONTROL_USE
@done:
    ld (w3d_controls),a
    ret

; One fixed 30 Hz input/integration quantum. Door simulation precedes player
; input, matching the original update order; a newly operated door therefore
; begins moving on the next quantum. Rotation precedes translation.
w3d_simulate_player_step:
    call w3d_simulate_doors
    call w3d_sample_controls
    call w3d_handle_use_edge

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
    jr z,@pickups
    ld de,270
    call w3d_move_at_heading_offset
@pickups:
    jp w3d_collect_pending_pickups

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
    ld (w3d_world_dirty),a
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
; register adds; ClipMove applies the pair through the collision predicate.
w3d_apply_heading_delta:
    ld de,0
    ld e,l
    ld d,h
    add hl,hl                    ; 2 * angle
    add hl,de                    ; 3 * angle
    add hl,hl                    ; 6 * angle
    ld de,w3d_motion_delta_table
    add hl,de
    jp w3d_clip_move_delta24

; Apply the dx/dy pair at HL using Wolf3D's ClipMove ordering: full X/Y,
; then X only, then Y only. A=1 when either coordinate changes, otherwise 0.
w3d_clip_move_delta24:
    ld (w3d_move_delta_ptr),hl

; A zero delta is not movement and must not dirty the world. This also keeps
; future sub-pixel/quantized callers honest even though the current heading
; table always supplies a nonzero vector.
    ld a,(hl)
    inc hl
    or (hl)
    inc hl
    or (hl)
    inc hl
    or (hl)
    inc hl
    or (hl)
    inc hl
    or (hl)
    jp z,@blocked

; First attempt the complete vector.
    call w3d_copy_pose_to_candidate
    ld hl,(w3d_move_delta_ptr)
    ld ix,w3d_move_candidate
    call w3d_add_signed_delta24
    inc hl
    ld ix,w3d_move_candidate+4
    call w3d_add_signed_delta24
    ld ix,w3d_move_candidate
    call w3d_player_position_clear
    or a
    jr z,@x_only
    ld hl,w3d_move_candidate
    ld de,w3d_player_pose
    ld bc,8
    ldir
    jr @moved

; If blocked, retain only X and try again.
@x_only:
    ld hl,(w3d_move_delta_ptr)
    ld a,(hl)
    inc hl
    or (hl)
    inc hl
    or (hl)
    jr z,@y_only
    call w3d_copy_pose_to_candidate
    ld hl,(w3d_move_delta_ptr)
    ld ix,w3d_move_candidate
    call w3d_add_signed_delta24
    ld ix,w3d_move_candidate
    call w3d_player_position_clear
    or a
    jr z,@y_only
    ld hl,w3d_move_candidate
    ld de,w3d_player_pose
    ld bc,4
    ldir
    jr @moved

; X was blocked too; retain only Y for the final slide attempt.
@y_only:
    ld hl,(w3d_move_delta_ptr)
    inc hl
    inc hl
    inc hl
    ld a,(hl)
    inc hl
    or (hl)
    inc hl
    or (hl)
    jr z,@blocked
    call w3d_copy_pose_to_candidate
    ld hl,(w3d_move_delta_ptr)
    inc hl
    inc hl
    inc hl
    ld ix,w3d_move_candidate+4
    call w3d_add_signed_delta24
    ld ix,w3d_move_candidate
    call w3d_player_position_clear
    or a
    jr z,@blocked
    ld hl,w3d_move_candidate+4
    ld de,w3d_player_pose+4
    ld bc,4
    ldir
@moved:
    ld a,1
    ld (w3d_player_dirty),a
    ld (w3d_world_dirty),a
    ld (w3d_pickup_scan_needed),a
    ret
@blocked:
    xor a
    ret

w3d_copy_pose_to_candidate:
    ld hl,w3d_player_pose
    ld de,w3d_move_candidate
    ld bc,8
    ldir
    ret

; IX points to candidate int32 X/Y. Derive the four corner tiles of the
; square 0x5800-radius player AABB and require every corner to be clear. A
; named door corner is resolved to its renderer-matching center-plane slab by
; w3d_collision_tile_clear. IX is preserved so ClipMove can still copy the
; accepted candidate afterward.
w3d_player_position_clear:
    call w3d_compute_player_bounds
    ld a,(w3d_clip_x_low)
    cp W3D_MAP_SIZE
    jr nc,@blocked
    ld a,(w3d_clip_x_high)
    cp W3D_MAP_SIZE
    jr nc,@blocked
    ld a,(w3d_clip_y_low)
    cp W3D_MAP_SIZE
    jr nc,@blocked
    ld a,(w3d_clip_y_high)
    cp W3D_MAP_SIZE
    jr nc,@blocked

    ld a,(w3d_clip_x_low)
    ld b,a
    ld a,(w3d_clip_y_low)
    ld c,a
    call w3d_collision_tile_clear
    or a
    jr z,@blocked
    ld a,(w3d_clip_x_high)
    ld b,a
    ld a,(w3d_clip_y_low)
    ld c,a
    call w3d_collision_tile_clear
    or a
    jr z,@blocked
    ld a,(w3d_clip_x_low)
    ld b,a
    ld a,(w3d_clip_y_high)
    ld c,a
    call w3d_collision_tile_clear
    or a
    jr z,@blocked
    ld a,(w3d_clip_x_high)
    ld b,a
    ld a,(w3d_clip_y_high)
    ld c,a
    call w3d_collision_tile_clear
    or a
    jr z,@blocked
    ld a,1
    ret
@blocked:
    xor a
    ret

; Compute low/high tile bounds for the square player at IX without touching
; any 24-bit register upper byte. The fractional words use forced 16-bit ops.
w3d_compute_player_bounds:
    ld hl,0
    ld l,(ix+0)
    ld h,(ix+1)
    ld de,W3D_PLAYER_COLLISION_RADIUS
    or a
    sbc.s hl,de
    ld a,l
    ld (w3d_clip_x_low_fraction+0),a
    ld a,h
    ld (w3d_clip_x_low_fraction+1),a
    ld a,(ix+2)
    sbc a,0
    ld (w3d_clip_x_low),a

    ld hl,0
    ld l,(ix+0)
    ld h,(ix+1)
    ld de,W3D_PLAYER_COLLISION_RADIUS
    add.s hl,de
    ld a,l
    ld (w3d_clip_x_high_fraction+0),a
    ld a,h
    ld (w3d_clip_x_high_fraction+1),a
    ld a,(ix+2)
    adc a,0
    ld (w3d_clip_x_high),a

    ld hl,0
    ld l,(ix+4)
    ld h,(ix+5)
    ld de,W3D_PLAYER_COLLISION_RADIUS
    or a
    sbc.s hl,de
    ld a,l
    ld (w3d_clip_y_low_fraction+0),a
    ld a,h
    ld (w3d_clip_y_low_fraction+1),a
    ld a,(ix+6)
    sbc a,0
    ld (w3d_clip_y_low),a

    ld hl,0
    ld l,(ix+4)
    ld h,(ix+5)
    ld de,W3D_PLAYER_COLLISION_RADIUS
    add.s hl,de
    ld a,l
    ld (w3d_clip_y_high_fraction+0),a
    ld a,h
    ld (w3d_clip_y_high_fraction+1),a
    ld a,(ix+6)
    adc a,0
    ld (w3d_clip_y_high),a
    ret

; B=x, C=y. Ordinary walls, reserved bytes, and original block-type statics
; stop the tile-wide square-player test. A valid named door cell resolves to
; its finite center-plane slab. Since the AABB is less than one tile wide, any
; slab it can touch necessarily lies in one of these four probed corner tiles;
; this avoids scanning all doors on every movement attempt. Invalid/reserved
; door bytes remain conservatively solid. Candidate IX is never repurposed.
w3d_collision_tile_clear:
    call w3d_map_read
    or a
    jr nz,@map_occupied
    call w3d_static_tile_blocked
    or a
    jr nz,@blocked
    jr @clear
@map_occupied:
    cp W3D_TILE_DOOR_MIN
    jr c,@blocked
    cp W3D_TILE_DOOR_MAX+1
    jr nc,@blocked
    and W3D_TILE_DOOR_MASK
    cp W3D_FIXTURE_DOOR_COUNT
    jr nc,@blocked
    push iy
    call w3d_door_pointer_iy_from_index
    ld a,(iy+W3D_DOOR_TILEX)
    cp b
    jr nz,@invalid_named_door
    ld a,(iy+W3D_DOOR_TILEY)
    cp c
    jr nz,@invalid_named_door
    call w3d_clip_bounds_overlap_door
    pop iy
    or a
    jr nz,@blocked
    jr @clear
@invalid_named_door:
    pop iy
@blocked:
    xor a
    ret
@clear:
    ld a,1
    ret

; IY -> authoritative door; clip-bound bytes/words describe the square AABB.
; Return A=1 iff it touches the finite moving slab, otherwise zero. The VDP
; admits ray fractions [0,position] and draws the panel at
; [position+1,0xffff]. AABB contact with the perpendicular center plane counts
; as collision. At position 0xffff there is no panel at all.
;
; Vertical door:   x == tileX:8000, panel extends along +Y.
; Horizontal door: y == tileY:8000, panel extends along +X.
;
; Only L,H,D,E hold multi-byte operands; their 24-bit upper bytes are ignored
; by forced 16-bit subtraction. IX, IY, B, and C are preserved.
w3d_clip_bounds_overlap_door:
    ld a,(iy+W3D_DOOR_POSITION+0)
    inc a
    jr nz,@not_fully_open
    ld a,(iy+W3D_DOOR_POSITION+1)
    inc a
    jp z,@clear
@not_fully_open:
    ld a,(iy+W3D_DOOR_VERTICAL)
    or a
    jp z,@horizontal

; Low X must be <= the vertical center plane.
@vertical:
    ld a,(w3d_clip_x_low)
    cp (iy+W3D_DOOR_TILEX)
    jr c,@vertical_low_ok
    jp nz,@clear
    ld hl,0
    ld a,(w3d_clip_x_low_fraction+0)
    ld l,a
    ld a,(w3d_clip_x_low_fraction+1)
    ld h,a
    ld de,08000h
    or a
    sbc.s hl,de
    jr c,@vertical_low_ok
    jp nz,@clear
@vertical_low_ok:

; High X must be >= the vertical center plane.
    ld a,(w3d_clip_x_high)
    cp (iy+W3D_DOOR_TILEX)
    jp c,@clear
    jr nz,@vertical_plane_crossed
    ld hl,0
    ld a,(w3d_clip_x_high_fraction+0)
    ld l,a
    ld a,(w3d_clip_x_high_fraction+1)
    ld h,a
    ld de,08000h
    or a
    sbc.s hl,de
    jp c,@clear
@vertical_plane_crossed:

; The highest occupied Y must lie strictly beyond tileY:position, because the
; position fraction itself belongs to the passable gap.
    ld a,(w3d_clip_y_high)
    cp (iy+W3D_DOOR_TILEY)
    jp c,@clear
    jr nz,@vertical_panel_start_ok
    ld hl,0
    ld a,(w3d_clip_y_high_fraction+0)
    ld l,a
    ld a,(w3d_clip_y_high_fraction+1)
    ld h,a
    ld de,0
    ld e,(iy+W3D_DOOR_POSITION+0)
    ld d,(iy+W3D_DOOR_POSITION+1)
    or a
    sbc.s hl,de
    jp c,@clear
    jp z,@clear
@vertical_panel_start_ok:

; The lowest occupied Y must not have passed tileY:ffff, the finite panel end.
    ld a,(w3d_clip_y_low)
    cp (iy+W3D_DOOR_TILEY)
    jp c,@blocked
    jp z,@blocked
    jp @clear

; Horizontal is the exact axis-swapped test.
@horizontal:
    ld a,(w3d_clip_y_low)
    cp (iy+W3D_DOOR_TILEY)
    jr c,@horizontal_low_ok
    jp nz,@clear
    ld hl,0
    ld a,(w3d_clip_y_low_fraction+0)
    ld l,a
    ld a,(w3d_clip_y_low_fraction+1)
    ld h,a
    ld de,08000h
    or a
    sbc.s hl,de
    jr c,@horizontal_low_ok
    jp nz,@clear
@horizontal_low_ok:
    ld a,(w3d_clip_y_high)
    cp (iy+W3D_DOOR_TILEY)
    jp c,@clear
    jr nz,@horizontal_plane_crossed
    ld hl,0
    ld a,(w3d_clip_y_high_fraction+0)
    ld l,a
    ld a,(w3d_clip_y_high_fraction+1)
    ld h,a
    ld de,08000h
    or a
    sbc.s hl,de
    jp c,@clear
@horizontal_plane_crossed:
    ld a,(w3d_clip_x_high)
    cp (iy+W3D_DOOR_TILEX)
    jp c,@clear
    jr nz,@horizontal_panel_start_ok
    ld hl,0
    ld a,(w3d_clip_x_high_fraction+0)
    ld l,a
    ld a,(w3d_clip_x_high_fraction+1)
    ld h,a
    ld de,0
    ld e,(iy+W3D_DOOR_POSITION+0)
    ld d,(iy+W3D_DOOR_POSITION+1)
    or a
    sbc.s hl,de
    jp c,@clear
    jp z,@clear
@horizontal_panel_start_ok:
    ld a,(w3d_clip_x_low)
    cp (iy+W3D_DOOR_TILEX)
    jp c,@blocked
    jp z,@blocked
    jp @clear

@blocked:
    ld a,1
    ret
@clear:
    xor a
    ret

; A=door index; returns IY -> authoritative W3D_DOOR_SIZE record without
; borrowing IX from the movement candidate.
w3d_door_pointer_iy_from_index:
    ld hl,0
    ld l,a
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    ld de,w3d_doors
    add hl,de
    push hl
    pop iy
    ret

; B=x, C=y -> A nonzero iff the fixture's immutable LSB-first 64x64 static
; occupancy bit is set.  This stays separate from the render/sight tilemap:
; blocking decorations are sprites, not opaque walls, and must not poison DDA.
; Destroys AF, C, DE, HL; preserves B.
w3d_static_tile_blocked:
    ld e,c
    ld d,0
    inc de
    dec.s de                        ; zero DEU without stack/scratch traffic
    sla e                           ; y * 8 gives the bitset row byte
    rl d
    sla e
    rl d
    sla e
    rl d
    ld a,b
    srl a
    srl a
    srl a
    add a,e
    ld e,a
    jr nc,@byte_offset_ready
    inc d
@byte_offset_ready:
    ld hl,(w3d_static_blocking_ptr)
    add hl,de
    ld c,(hl)
    ld a,b
    and 7
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_static_bit_masks
    add hl,de
    ld a,(hl)
    and c
    ret

w3d_static_bit_masks:
    db 1,2,4,8,16,32,64,128

; ---------------------------------------------------------------------------
; Mutable statics and pickups
; ---------------------------------------------------------------------------

; A successful translation requests one scan.  Pickup contact uses the same
; square player bounds already established for movement: a bonus is eligible
; as soon as its tile overlaps the player's PLAYERSIZE AABB.  Unlike the DOS
; renderer's visibility-triggered GetBonus call, this simulation-side test is
; deterministic and independent of VDP/render cadence.
w3d_collect_pending_pickups:
    ld a,(w3d_pickup_scan_needed)
    or a
    ret z
    xor a
    ld (w3d_pickup_scan_needed),a
    push ix
    ld ix,w3d_player_pose
    call w3d_compute_player_bounds
    ld hl,0
    ld (w3d_current_static_index),hl
@loop:
    ld hl,(w3d_current_static_index)
    ld de,W3D_FIXTURE_STATIC_COUNT
    or a
    sbc hl,de
    jr nc,@done
    call w3d_static_pointer_from_current

    ld a,(ix+W3D_STATIC_SHAPENUM+0)
    inc a
    jr nz,@active
    ld a,(ix+W3D_STATIC_SHAPENUM+1)
    inc a
    jr z,@next                       ; shapenum == -1: already collected
@active:
    ld a,(ix+W3D_STATIC_FLAGS)
    and W3D_STATIC_FLAG_BONUS
    jr z,@next

    ld a,(ix+W3D_STATIC_TILEX)
    ld b,a
    ld hl,w3d_clip_x_low
    cp (hl)
    jr c,@next
    ld a,(w3d_clip_x_high)
    cp b
    jr c,@next
    ld a,(ix+W3D_STATIC_TILEY)
    ld b,a
    ld hl,w3d_clip_y_low
    cp (hl)
    jr c,@next
    ld a,(w3d_clip_y_high)
    cp b
    jr c,@next
    call w3d_apply_current_pickup
@next:
    ld hl,(w3d_current_static_index)
    inc hl
    ld (w3d_current_static_index),hl
    jr @loop
@done:
    pop ix
    ret

; Apply the original non-SPEAR GetBonus state rules represented by this port's
; current HUD/gameplay subset.  Sound/flash side effects are deliberately not
; part of authoritative object state.  Refused health/ammo/gibs pickups remain
; active exactly as in the original.
w3d_apply_current_pickup:
    ld a,(ix+W3D_STATIC_ITEMNUMBER)
    cp W3D_ITEM_GIBS
    jp z,@gibs
    cp W3D_ITEM_ALPO
    jp z,@alpo
    cp W3D_ITEM_FIRSTAID
    jp z,@firstaid
    cp W3D_ITEM_KEY1
    jp c,@not_consumed
    cp W3D_ITEM_KEY4+1
    jp c,@key
    cp W3D_ITEM_CROSS
    jp z,@cross
    cp W3D_ITEM_CHALICE
    jp z,@chalice
    cp W3D_ITEM_BIBLE
    jp z,@bible
    cp W3D_ITEM_CROWN
    jp z,@crown
    cp W3D_ITEM_CLIP
    jp z,@clip
    cp W3D_ITEM_CLIP2
    jp z,@clip2
    cp W3D_ITEM_MACHINEGUN
    jp z,@machinegun
    cp W3D_ITEM_CHAINGUN
    jp z,@chaingun
    cp W3D_ITEM_FOOD
    jp z,@food
    cp W3D_ITEM_FULLHEAL
    jp z,@fullheal
@not_consumed:
    xor a
    ret

@alpo:
    ld a,(w3d_player_health)
    cp 100
    jp nc,@not_consumed
    ld a,4
    call w3d_add_player_health
    jp @consume
@firstaid:
    ld a,(w3d_player_health)
    cp 100
    jp nc,@not_consumed
    ld a,25
    call w3d_add_player_health
    jp @consume
@food:
    ld a,(w3d_player_health)
    cp 100
    jp nc,@not_consumed
    ld a,10
    call w3d_add_player_health
    jp @consume
@gibs:
    ld a,(w3d_player_health)
    cp 11
    jp nc,@not_consumed
    ld a,1
    call w3d_add_player_health
    jp @consume

@key:
    sub W3D_ITEM_KEY1
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_key_masks
    add hl,de
    ld b,(hl)
    ld a,(w3d_player_key_flags)
    ld c,a
    or b
    ld (w3d_player_key_flags),a
    cp c
    jp z,@consume
    ld a,W3D_HUD_DIRTY_KEYS
    call w3d_mark_hud_dirty
    jp @consume

@cross:
    ld hl,100
    call w3d_add_player_score
    call w3d_increment_treasure_count
    jp @consume
@chalice:
    ld hl,500
    call w3d_add_player_score
    call w3d_increment_treasure_count
    jp @consume
@bible:
    ld hl,1000
    call w3d_add_player_score
    call w3d_increment_treasure_count
    jp @consume
@crown:
    ld hl,5000
    call w3d_add_player_score
    call w3d_increment_treasure_count
    jp @consume

@clip:
    ld a,(w3d_player_ammo)
    cp 99
    jp nc,@not_consumed
    ld a,8
    call w3d_add_player_ammo
    jp @consume
@clip2:
    ld a,(w3d_player_ammo)
    cp 99
    jp nc,@not_consumed
    ld a,4
    call w3d_add_player_ammo
    jp @consume

@machinegun:
    ld a,6
    call w3d_add_player_ammo
    ld a,(w3d_player_best_weapon)
    cp 2
    jp nc,@consume
    ld a,2
    call w3d_set_player_weapon
    jp @consume
@chaingun:
    ld a,6
    call w3d_add_player_ammo
    ld a,(w3d_player_best_weapon)
    cp 3
    jp nc,@consume
    ld a,3
    call w3d_set_player_weapon
    jp @consume

@fullheal:
    ld a,(w3d_player_health)
    cp 100
    jr z,@fullheal_ammo
    ld a,100
    ld (w3d_player_health),a
    ld a,W3D_HUD_DIRTY_HEALTH
    call w3d_mark_hud_dirty
@fullheal_ammo:
    ld a,25
    call w3d_add_player_ammo
    call w3d_give_extra_life
    call w3d_increment_treasure_count

@consume:
    ld a,0ffh
    ld (ix+W3D_STATIC_SHAPENUM+0),a
    ld (ix+W3D_STATIC_SHAPENUM+1),a
    call w3d_mark_current_static_dirty
    ld a,1
    ret

; A=health increment. Saturates at 100 and marks only an actual HUD change.
w3d_add_player_health:
    ld b,a
    ld a,(w3d_player_health)
    ld c,a
    add a,b
    cp 101
    jr c,@ready
    ld a,100
@ready:
    cp c
    ret z
    ld (w3d_player_health),a
    ld a,W3D_HUD_DIRTY_HEALTH
    jp w3d_mark_hud_dirty

; A=ammo increment. Saturates at 99 and marks only an actual HUD change.
; With no attack animation modeled yet, an empty-ammo player is necessarily
; idle, so match GiveAmmo's restore of the chosen weapon when ammunition
; becomes available again.
w3d_add_player_ammo:
    ld b,a
    ld a,(w3d_player_ammo)
    ld c,a
    add a,b
    cp 100
    jr c,@ready
    ld a,99
@ready:
    cp c
    ret z
    ld (w3d_player_ammo),a
    ld a,W3D_HUD_DIRTY_AMMO
    call w3d_mark_hud_dirty
    ld a,c
    or a
    ret nz
    ld a,(w3d_player_chosen_weapon)
    ld b,a
    ld a,(w3d_player_weapon)
    cp b
    ret z
    ld a,b
    ld (w3d_player_weapon),a
    ld a,W3D_HUD_DIRTY_WEAPON
    jp w3d_mark_hud_dirty

; HL=unsigned point increment (the current treasures all fit in 16 bits).
w3d_add_player_score:
    ld a,(w3d_player_score+0)
    add a,l
    ld (w3d_player_score+0),a
    ld a,(w3d_player_score+1)
    adc a,h
    ld (w3d_player_score+1),a
    ld a,(w3d_player_score+2)
    adc a,0
    ld (w3d_player_score+2),a
    ld a,(w3d_player_score+3)
    adc a,0
    ld (w3d_player_score+3),a
    ld a,W3D_HUD_DIRTY_SCORE
    call w3d_mark_hud_dirty

; Original GivePoints awards another life at each 40,000-point threshold.
@extra_life_check:
    ld a,(w3d_player_next_extra+3)
    ld b,a
    ld a,(w3d_player_score+3)
    cp b
    jr c,@no_extra_life
    jr nz,@award
    ld a,(w3d_player_next_extra+2)
    ld b,a
    ld a,(w3d_player_score+2)
    cp b
    jr c,@no_extra_life
    jr nz,@award
    ld a,(w3d_player_next_extra+1)
    ld b,a
    ld a,(w3d_player_score+1)
    cp b
    jr c,@no_extra_life
    jr nz,@award
    ld a,(w3d_player_next_extra+0)
    ld b,a
    ld a,(w3d_player_score+0)
    cp b
    jr c,@no_extra_life
@award:
    ld a,(w3d_player_next_extra+0)
    add a,040h
    ld (w3d_player_next_extra+0),a
    ld a,(w3d_player_next_extra+1)
    adc a,09ch
    ld (w3d_player_next_extra+1),a
    ld a,(w3d_player_next_extra+2)
    adc a,0
    ld (w3d_player_next_extra+2),a
    ld a,(w3d_player_next_extra+3)
    adc a,0
    ld (w3d_player_next_extra+3),a
    call w3d_give_extra_life
    jr @extra_life_check
@no_extra_life:
    ret

; Match GiveExtraMan: lives never exceed nine.  The threshold still advances
; when already capped, but no redundant HUD command is emitted.
w3d_give_extra_life:
    ld a,(w3d_player_lives)
    cp 9
    ret nc
    inc a
    ld (w3d_player_lives),a
    ld a,W3D_HUD_DIRTY_LIVES
    jp w3d_mark_hud_dirty

; Original treasurecount is a 16-bit per-level statistic.  It is persistent
; eZ80 state even though this first HUD does not display it.
w3d_increment_treasure_count:
    ld hl,w3d_player_treasure_count
    inc (hl)
    ret nz
    inc hl
    inc (hl)
    ret

; A=new best/current/chosen weapon (0 knife .. 3 chaingun).
w3d_set_player_weapon:
    ld (w3d_player_best_weapon),a
    ld (w3d_player_weapon),a
    ld (w3d_player_chosen_weapon),a
    ld a,W3D_HUD_DIRTY_WEAPON
    jp w3d_mark_hud_dirty

; A=one or more W3D_HUD_DIRTY_* bits.
w3d_mark_hud_dirty:
    ld b,a
    ld a,(w3d_hud_dirty)
    or b
    ld (w3d_hud_dirty),a
    ld a,1
    ld (w3d_world_dirty),a
    ret

; Current static index is a 24-bit loop value but the public slot is uint16.
; Returns IX -> compact W3D_STATIC_SIZE authoritative record.
w3d_static_pointer_from_current:
    ld hl,(w3d_current_static_index)
    ld de,0
    ld e,l
    ld d,h
    add hl,hl                       ; 2 * index
    add hl,de                       ; 3 * index
    add hl,hl                       ; 6 * index
    ld de,w3d_statics
    add hl,de
    push hl
    pop ix
    ret

w3d_mark_current_static_dirty:
    ld hl,(w3d_current_static_index)
    ld de,w3d_static_dirty
    add hl,de
    ld a,1
    ld (hl),a
    ld (w3d_world_dirty),a
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

; ---------------------------------------------------------------------------
; Door operation and fixed-step simulation
; ---------------------------------------------------------------------------

; Turn the latched Space state into one operation per physical key press.
w3d_handle_use_edge:
    ld a,(w3d_controls)
    and W3D_CONTROL_USE
    jr z,@released
    ld a,(w3d_use_was_down)
    or a
    ret nz
    ld a,1
    ld (w3d_use_was_down),a
    jp w3d_use_adjacent_door
@released:
    xor a
    ld (w3d_use_was_down),a
    ret

; Operate exactly one adjacent tile in the nearest cardinal direction.
; Angle sectors preserve the original boundary behavior: 315 remains south;
; 316 begins the east sector. Pushwalls/elevator switches are future layers.
w3d_use_adjacent_door:
    call w3d_load_player_angle
    ld de,45
    or a
    sbc.s hl,de
    jr c,@east
    call w3d_load_player_angle
    ld de,135
    or a
    sbc.s hl,de
    jr c,@north
    call w3d_load_player_angle
    ld de,225
    or a
    sbc.s hl,de
    jr c,@west
    call w3d_load_player_angle
    ld de,316
    or a
    sbc.s hl,de
    jr nc,@east
@south:
    ld a,(w3d_player_pose+2)
    ld b,a
    ld a,(w3d_player_pose+6)
    inc a
    ld c,a
    jr @tile_ready
@east:
    ld a,(w3d_player_pose+2)
    inc a
    ld b,a
    ld a,(w3d_player_pose+6)
    ld c,a
    jr @tile_ready
@north:
    ld a,(w3d_player_pose+2)
    ld b,a
    ld a,(w3d_player_pose+6)
    dec a
    ld c,a
    jr @tile_ready
@west:
    ld a,(w3d_player_pose+2)
    dec a
    ld b,a
    ld a,(w3d_player_pose+6)
    ld c,a
@tile_ready:
    ld a,b
    cp W3D_MAP_SIZE
    ret nc
    ld a,c
    cp W3D_MAP_SIZE
    ret nc
    call w3d_map_read
    cp W3D_TILE_DOOR_MIN
    ret c
    cp W3D_TILE_DOOR_MAX+1
    ret nc
    and W3D_TILE_DOOR_MASK
    cp W3D_FIXTURE_DOOR_COUNT
    ret nc
    ld (w3d_current_door_index),a
    call w3d_door_pointer_from_index

; Locks 1..4 consume future inventory bits 0..3. Normal and elevator-art
; doors operate now; other values fail conservatively.
    ld a,(ix+W3D_DOOR_LOCK)
    or a
    jr z,@unlocked
    cp 5
    jr z,@unlocked
    cp 5
    ret nc
    dec a
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_key_masks
    add hl,de
    ld a,(hl)
    ld b,a
    ld a,(w3d_player_key_flags)
    and b
    ret z
@unlocked:
    ld a,(ix+W3D_DOOR_ACTION)
    cp W3D_DOOR_ACTION_OPENING
    ret z                           ; original opening-door close request is ignored
    cp W3D_DOOR_ACTION_OPEN
    jp z,w3d_try_close_current_door
    ; Closed or closing reverses/starts toward open from its current position.
    ld a,W3D_DOOR_ACTION_OPENING
    ld (ix+W3D_DOOR_ACTION),a
    call w3d_zero_current_door_timer
    jp w3d_mark_current_door_dirty

; Advance every authoritative door once. The phase sequence preserves the
; original 70 Hz travel time without a runtime multiply.
w3d_simulate_doors:
    ld a,(w3d_door_motion_phase)
    cp 2
    jr z,@large_step
    ld de,W3D_DOOR_STEP_LO
    inc a
    ld (w3d_door_motion_phase),a
    jr @step_ready
@large_step:
    ld de,W3D_DOOR_STEP_HI
    xor a
    ld (w3d_door_motion_phase),a
@step_ready:
    ld (w3d_door_step_delta),de
    xor a
    ld (w3d_current_door_index),a
@loop:
    ld a,(w3d_current_door_index)
    cp W3D_FIXTURE_DOOR_COUNT
    ret nc
    call w3d_door_pointer_from_index
    ld a,(ix+W3D_DOOR_ACTION)
    cp W3D_DOOR_ACTION_OPENING
    jr z,@opening
    cp W3D_DOOR_ACTION_OPEN
    jr z,@open
    cp W3D_DOOR_ACTION_CLOSING
    jr z,@closing
    jr @next
@opening:
    call w3d_advance_opening_door
    jr @next
@open:
    call w3d_advance_open_door
    jr @next
@closing:
    call w3d_advance_closing_door
@next:
    ld a,(w3d_current_door_index)
    inc a
    ld (w3d_current_door_index),a
    jr @loop

w3d_advance_opening_door:
    ld hl,0
    ld l,(ix+W3D_DOOR_POSITION+0)
    ld h,(ix+W3D_DOOR_POSITION+1)
    ld de,(w3d_door_step_delta)
    add.s hl,de
    jr c,@fully_open
    ld a,h
    and l
    inc a
    jr z,@fully_open                 ; an exact FFFF sum is saturated too
    ld (ix+W3D_DOOR_POSITION+0),l
    ld (ix+W3D_DOOR_POSITION+1),h
    jp w3d_mark_current_door_dirty
@fully_open:
    ld a,0ffh
    ld (ix+W3D_DOOR_POSITION+0),a
    ld (ix+W3D_DOOR_POSITION+1),a
    ld a,W3D_DOOR_ACTION_OPEN
    ld (ix+W3D_DOOR_ACTION),a
    call w3d_zero_current_door_timer
    jp w3d_mark_current_door_dirty

w3d_advance_open_door:
    call w3d_current_door_timer_pointer
    ld hl,0
    ld l,(iy+0)
    ld h,(iy+1)
    ld de,W3D_DOOR_OPEN_TIMER_STEP
    add.s hl,de
    ld (iy+0),l
    ld (iy+1),h
    ld de,W3D_DOOR_OPEN_TIMER_LIMIT
    or a
    sbc.s hl,de
    ret c
    ld hl,W3D_DOOR_OPEN_TIMER_LIMIT
    ld (iy+0),l
    ld (iy+1),h                    ; retry every tick without timer wraparound
    jp w3d_try_close_current_door

w3d_try_close_current_door:
    call w3d_door_player_obstructs
    or a
    ret nz                           ; remain open and retry next update
    ld a,W3D_DOOR_ACTION_CLOSING
    ld (ix+W3D_DOOR_ACTION),a
    jp w3d_mark_current_door_dirty

w3d_advance_closing_door:
    call w3d_door_player_obstructs
    or a
    jr z,@unobstructed
    ld a,W3D_DOOR_ACTION_OPENING
    ld (ix+W3D_DOOR_ACTION),a
    call w3d_zero_current_door_timer
    jp w3d_mark_current_door_dirty
@unobstructed:
    ld hl,0
    ld l,(ix+W3D_DOOR_POSITION+0)
    ld h,(ix+W3D_DOOR_POSITION+1)
    ld de,(w3d_door_step_delta)
    or a
    sbc.s hl,de
    jr c,@fully_closed
    jr z,@fully_closed
    ld (ix+W3D_DOOR_POSITION+0),l
    ld (ix+W3D_DOOR_POSITION+1),h
    jp w3d_mark_current_door_dirty
@fully_closed:
    xor a
    ld (ix+W3D_DOOR_POSITION+0),a
    ld (ix+W3D_DOOR_POSITION+1),a
    ld (ix+W3D_DOOR_ACTION),a         ; W3D_DOOR_ACTION_CLOSED
    call w3d_zero_current_door_timer
    jp w3d_mark_current_door_dirty

; Actor-free obstruction hook using exactly the same finite slab/AABB geometry
; as movement. Thus a player safely inside the passable part of either well
; does not hold the door, while contact with the currently visible panel does.
; IX remains the current authoritative door for the caller.
w3d_door_player_obstructs:
    push iy
    push ix
    ld ix,w3d_player_pose
    call w3d_compute_player_bounds
    pop ix
    push ix
    pop iy
    call w3d_clip_bounds_overlap_door
    pop iy
    ret

; A=door index; returns IX -> authoritative W3D_DOOR_SIZE record.
w3d_door_pointer_from_index:
    ld hl,0
    ld l,a
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    ld de,w3d_doors
    add hl,de
    push hl
    pop ix
    ret

w3d_current_door_timer_pointer:
    ld a,(w3d_current_door_index)
    ld hl,0
    ld l,a
    add.s hl,hl
    ld de,w3d_door_timers
    add hl,de
    push hl
    pop iy
    ret

w3d_zero_current_door_timer:
    push iy
    call w3d_current_door_timer_pointer
    xor a
    ld (iy+0),a
    ld (iy+1),a
    pop iy
    ret

w3d_mark_current_door_dirty:
    ld a,(w3d_current_door_index)
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_door_dirty
    add hl,de
    ld a,1
    ld (hl),a
    ld (w3d_world_dirty),a
    ret

; Send every changed door/static/HUD field, then the changed player pose,
; followed by one render request. Assets/map remain resident. Each dirty flag
; is cleared only after its complete command crosses the synchronous VDU
; boundary.
w3d_submit_dirty_world_render:
    xor a
    ld (w3d_current_door_index),a
@door_loop:
    ld a,(w3d_current_door_index)
    cp W3D_FIXTURE_DOOR_COUNT
    jr nc,@statics
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_door_dirty
    add hl,de
    ld a,(hl)
    or a
    jr z,@next_door

    ld a,(w3d_current_door_index)
    ld (@door_number),a
    call w3d_door_pointer_from_index
    push ix
    pop hl
    ld de,@door_record
    ld bc,W3D_DOOR_SIZE
    ldir
    ld hl,@door_command
    ld bc,@door_end-@door_command
    rst.lil 18h

    ld a,(w3d_current_door_index)
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_door_dirty
    add hl,de
    xor a
    ld (hl),a
@next_door:
    ld a,(w3d_current_door_index)
    inc a
    ld (w3d_current_door_index),a
    jr @door_loop

@statics:
    ld hl,0
    ld (w3d_current_static_index),hl
@static_loop:
    ld hl,(w3d_current_static_index)
    ld de,W3D_FIXTURE_STATIC_COUNT
    or a
    sbc hl,de
    jr nc,@hud
    ld hl,(w3d_current_static_index)
    ld de,w3d_static_dirty
    add hl,de
    ld a,(hl)
    or a
    jr z,@next_static

    ld hl,(w3d_current_static_index)
    ld a,l
    ld (@static_number+0),a
    ld a,h
    ld (@static_number+1),a
    call w3d_static_pointer_from_current
    push ix
    pop hl
    ld de,@static_record
    ld bc,W3D_STATIC_WIRE_SIZE
    ldir
    ld hl,@static_command
    ld bc,@static_end-@static_command
    rst.lil 18h

    ld hl,(w3d_current_static_index)
    ld de,w3d_static_dirty
    add hl,de
    xor a
    ld (hl),a
@next_static:
    ld hl,(w3d_current_static_index)
    inc hl
    ld (w3d_current_static_index),hl
    jr @static_loop

@hud:
    call w3d_submit_dirty_hud

@player:
    ld a,(w3d_player_dirty)
    or a
    jr z,@render
    ld hl,w3d_player_pose
    ld de,@player_pose
    ld bc,10
    ldir
    xor a
    ld (w3d_player_dirty),a
    ld hl,@player_command
    ld bc,@player_end-@player_command
    rst.lil 18h

@render:
    xor a
    ld (w3d_world_dirty),a
    call w3d_mark_render_submitted
    ld hl,@render_command
    ld bc,@render_end-@render_command
    rst.lil 18h
    ret
@door_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,3
@door_number:
    db 0
@door_record:
    ds W3D_DOOR_SIZE
@door_end:
@static_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,6
@static_number:
    dw 0
@static_record:
    ds W3D_STATIC_WIRE_SIZE
@static_end:
@player_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,2
@player_pose:
    ds 10
@player_end:
@render_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,7
@render_end:

; Submit only changed status fields. The VDP persists these values and draws
; the complete panel into each hidden buffer during render_frame.
w3d_submit_dirty_hud:
    ld a,(w3d_hud_dirty)
    bit 0,a
    jr z,@ammo
    ld a,(w3d_player_health)
    ld (@health_value),a
    ld hl,@health_command
    ld bc,@health_end-@health_command
    rst.lil 18h
@ammo:
    ld a,(w3d_hud_dirty)
    bit 1,a
    jr z,@keys
    ld a,(w3d_player_ammo)
    ld (@ammo_value),a
    ld hl,@ammo_command
    ld bc,@ammo_end-@ammo_command
    rst.lil 18h
@keys:
    ld a,(w3d_hud_dirty)
    bit 2,a
    jr z,@weapon
    ld a,(w3d_player_key_flags)
    ld (@keys_value),a
    ld hl,@keys_command
    ld bc,@keys_end-@keys_command
    rst.lil 18h
@weapon:
    ld a,(w3d_hud_dirty)
    bit 3,a
    jr z,@score
    ld a,(w3d_player_weapon)
    ld (@weapon_value),a
    ld hl,@weapon_command
    ld bc,@weapon_end-@weapon_command
    rst.lil 18h
@score:
    ld a,(w3d_hud_dirty)
    bit 4,a
    jr z,@lives
    ld hl,w3d_player_score
    ld de,@score_value
    ld bc,4
    ldir
    ld hl,@score_command
    ld bc,@score_end-@score_command
    rst.lil 18h
@lives:
    ld a,(w3d_hud_dirty)
    bit 5,a
    jr z,@done
    ld a,(w3d_player_lives)
    ld (@lives_value),a
    ld hl,@lives_command
    ld bc,@lives_end-@lives_command
    rst.lil 18h
@done:
    xor a
    ld (w3d_hud_dirty),a
    ret

@health_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,10
@health_value:
    db 100
@health_end:
@ammo_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,11
@ammo_value:
    db 8
@ammo_end:
@keys_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,12
@keys_value:
    db 0
@keys_end:
@weapon_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,13
@weapon_value:
    db 1
@weapon_end:
@score_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,14
@score_value:
    dl 0
    db 0
@score_end:
@lives_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,17
@lives_value:
    db 3
@lives_end:

w3d_keyboard_masks:
    ds 16

w3d_player_pose:
    ds 10                         ; int32 x, int32 y, uint16 degrees

w3d_player_dirty:
    db 0

w3d_world_dirty:
    db 0

w3d_controls:
    db 0

w3d_use_was_down:
    db 0

w3d_player_key_flags:
    db 0

w3d_player_health:
    db 100

w3d_player_ammo:
    db 8

w3d_player_weapon:
    db 1

w3d_player_best_weapon:
    db 1

w3d_player_chosen_weapon:
    db 1

w3d_player_lives:
    db 3

w3d_player_score:
    dl 0
    db 0

w3d_player_treasure_count:
    dw 0

w3d_player_next_extra:
    db 040h,09ch,0,0

w3d_hud_dirty:
    db 0

w3d_pickup_scan_needed:
    db 0

w3d_static_blocking_ptr:
    dl 0

w3d_key_masks:
    db 1,2,4,8

w3d_doors:
    ds W3D_FIXTURE_DOOR_COUNT*W3D_DOOR_SIZE

w3d_door_timers:
    ds W3D_FIXTURE_DOOR_COUNT*2

w3d_door_dirty:
    ds W3D_FIXTURE_DOOR_COUNT

w3d_statics:
    ds W3D_FIXTURE_STATIC_COUNT*W3D_STATIC_SIZE

w3d_static_dirty:
    ds W3D_FIXTURE_STATIC_COUNT

w3d_current_static_index:
    dl 0

w3d_current_door_index:
    db 0

w3d_door_motion_phase:
    db 0

w3d_door_step_delta:
    dl 0

w3d_move_delta_ptr:
    dl 0

w3d_move_candidate:
    ds 8

w3d_clip_x_low:
    db 0
w3d_clip_x_low_fraction:
    dw 0
w3d_clip_x_high:
    db 0
w3d_clip_x_high_fraction:
    dw 0
w3d_clip_y_low:
    db 0
w3d_clip_y_low_fraction:
    dw 0
w3d_clip_y_high:
    db 0
w3d_clip_y_high_fraction:
    dw 0

w3d_simulation_accumulator:
    dl 0

w3d_simulation_steps_remaining:
    db 0

    include "wolf3d_motion_table.inc"
