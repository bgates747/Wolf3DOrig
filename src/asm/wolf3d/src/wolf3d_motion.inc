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
;   Up Arrow    operate the adjacent door (rising edge)
;   Space       attack/fire
;   1/2/3/4     knife/pistol/submachine gun/gatling gun
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
W3D_PLAYER_POSE_SIZE:           equ 10
; Experimental feel tuning: the original 0x5800 player radius proved too
; conservative around walls and the renderer-matched door slab.
W3D_PLAYER_COLLISION_RADIUS:     equ 04800h
; Original CloseDoor's MINDIST body margin is an actor-only close-start rule.
; It must not inherit the independently tuned player wall/door radius.
W3D_DOOR_ACTOR_CLEARANCE:        equ 05800h
W3D_ELEVATOR_SWITCH_TILE:        equ 21
W3D_LEVEL_COMPLETION_NONE:       equ 0
W3D_LEVEL_COMPLETION_NORMAL:     equ 1
W3D_LEVEL_COMPLETION_SECRET:     equ 2

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

; Initialize persistent new-game state, then build the first authoritative
; attempt.  Respawns call w3d_reseed_level_attempt instead: lives, score,
; difficulty, and the extra-life threshold survive that world rebuild and are
; reconciled by wolf3d_death.inc after the hook returns.
w3d_initialize_motion_state:
    ld a,(w3d_requested_difficulty)
    ld (w3d_game_difficulty),a
    ld a,3
    ld (w3d_player_lives),a
    xor a
    ld (w3d_player_score+0),a
    ld (w3d_player_score+1),a
    ld (w3d_player_score+2),a
    ld (w3d_player_score+3),a
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
    jp w3d_seed_level_attempt_state

; Rebuild every mutable world/per-level field from the active level bindings
; without touching game-persistent health, ammo, weapons, lives, difficulty,
; score, or extra-life threshold. This is the common SetupGameLevel core for
; a fresh game, death reseed, and successful level transition.
w3d_seed_level_world_state:
    ld hl,(w3d_level_player_seed_ptr)
    ld de,w3d_player_pose
    ld bc,W3D_PLAYER_POSE_SIZE
    ldir

; Clear the complete runtime-door capacity before copying the active prefix.
; Level transitions may shrink the active count, so no stale record survives
; as an accidental future seed.
    xor a
    ld hl,w3d_doors
    ld (hl),a
    ld de,w3d_doors+1
    ld bc,W3D_MAX_DOORS*W3D_DOOR_SIZE-1
    ldir
    ld a,(w3d_level_door_count)
    or a
    jr z,@doors_seeded
    ld hl,(w3d_level_door_seed_ptr)
    ld de,w3d_doors
@copy_door_seed:
    ld bc,W3D_DOOR_SIZE
    ldir
    dec a
    jr nz,@copy_door_seed
@doors_seeded:
; Clear the complete runtime-static capacity before copying the active level's
; active prefix. Drops may extend that prefix to the original MAXSTATS=400,
; so no byte may depend on MOS loader/BSS behavior.
    xor a
    ld hl,w3d_statics
    ld (hl),a
    ld de,w3d_statics+1
    ld bc,W3D_MAX_STATICS*W3D_STATIC_SIZE-1
    ldir
    ld hl,w3d_static_dirty
    ld (hl),a
    ld de,w3d_static_dirty+1
    ld bc,W3D_MAX_STATICS-1
    ldir
    ld bc,0
    ld a,(w3d_level_static_count+0)
    ld c,a
    ld a,(w3d_level_static_count+1)
    ld b,a
    or c
    jr z,@statics_seeded
    ld hl,(w3d_level_static_seed_ptr)
    ld de,w3d_statics
@copy_static_seed:
    push bc
    ld bc,W3D_STATIC_SIZE
    ldir
    pop bc
    dec bc
    ld a,b
    or c
    jr nz,@copy_static_seed
@statics_seeded:
    ld a,(w3d_level_static_count+0)
    ld (w3d_static_count+0),a
    ld a,(w3d_level_static_count+1)
    ld (w3d_static_count+1),a
    xor a
    ld (w3d_player_dirty),a
    ld (w3d_world_dirty),a
    ld (w3d_controls),a
    ld (w3d_use_was_down),a
    ld (w3d_player_key_flags),a
    ld (w3d_player_thrustspeed+0),a
    ld (w3d_player_thrustspeed+1),a
    ld (w3d_player_dead),a
    ld (w3d_level_completion),a
    ld a,W3D_SLOT_NONE
    ld (w3d_player_last_attacker),a
    ld (w3d_player_killer),a
    xor a
    ld (w3d_door_motion_phase),a
    ld hl,w3d_door_timers
    ld (hl),a
    ld de,w3d_door_timers+1
    ld bc,W3D_MAX_DOORS*2-1
    ldir
    ld hl,w3d_door_dirty
    ld (hl),a
    ld de,w3d_door_dirty+1
    ld bc,W3D_MAX_DOORS-1
    ldir
    xor a
    ld (w3d_hud_dirty),a
    ld (w3d_pickup_scan_needed),a
    ld (w3d_player_treasure_count+0),a
    ld (w3d_player_treasure_count+1),a
    xor a
    ld hl,(w3d_level_tilemap_ptr)
    ld (w3d_map_ptr),hl
    ld hl,(w3d_level_blocking_ptr)
    ld (w3d_static_blocking_ptr),hl
    ld hl,w3d_doors
    ld (w3d_doors_ptr),hl
    call w3d_build_static_collision_lookup
    ld hl,0
    ld (w3d_simulation_accumulator),hl
    call w3d_initialize_actor_state
    call w3d_initialize_actor_simulation
    call w3d_initialize_area_state
    call w3d_reset_keys
    ret

; Attempt entry resets transient weapon/attack machinery around whichever
; inventory policy the caller established. New-game startup sets canonical
; pistol inventory above; death code reapplies it after this hook; a level
; transition deliberately retains the player's current inventory.
w3d_seed_level_attempt_state:
    call w3d_seed_level_world_state
    jp w3d_initialize_player_combat

; Death-restart hook. Rebuild authoritative state, then mark exactly the
; level's active doors/statics/actors plus all player/HUD state for replay.
; Carry is clear only after the full reset is ready; no render is submitted.
w3d_reseed_level_attempt:
    call w3d_seed_level_attempt_state
    call w3d_mark_full_level_dirty
    or a
    ret

w3d_mark_full_level_dirty:
    ld a,(w3d_level_door_count)
    or a
    jr z,@statics
    ld b,a
    ld hl,w3d_door_dirty
@door_loop:
    ld (hl),1
    inc hl
    djnz @door_loop

@statics:
    ld bc,0
    ld a,(w3d_level_static_count+0)
    ld c,a
    ld a,(w3d_level_static_count+1)
    ld b,a
    ld hl,w3d_static_dirty
@static_loop:
    ld a,b
    or c
    jr z,@actors
    ld (hl),1
    inc hl
    dec bc
    jr @static_loop

@actors:
    ld a,(w3d_level_actor_count)
    or a
    jr z,@player
    ld b,a
    ld hl,w3d_actor_dirty+1
@actor_loop:
    ld (hl),W3D_ACTOR_DIRTY_SET
    inc hl
    djnz @actor_loop

@player:
    ld a,W3D_HUD_DIRTY_HEALTH|W3D_HUD_DIRTY_AMMO|W3D_HUD_DIRTY_KEYS|W3D_HUD_DIRTY_WEAPON|W3D_HUD_DIRTY_SCORE|W3D_HUD_DIRTY_LIVES
    ld (w3d_hud_dirty),a
    ld a,1
    ld (w3d_player_dirty),a
    ld (w3d_player_weapon_shape_dirty),a
    ld (w3d_world_dirty),a
    ret

; OR MOS's current held-key map into a local latch. Sampling on every
; foreground pass catches short taps; resetting and immediately resampling
; after each fixed quantum makes held keys active during every catch-up step.
; Every sample also promotes Escape directly from byte 14 bit 0 into the
; shutdown latch. The keyboard callback remains a low-latency backup, but the
; hot loop is authoritative and cannot depend on receiving an ASCII record.
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
    ; fall through

w3d_latch_exit_request:
    ld a,(w3d_keyboard_masks+14)
    and 00000001b                  ; Escape
    ret z
    ld a,1
    ld (w3d_exit_requested),a
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
; Every fixed quantum owns a fresh same-tick arbitration batch. Beginning a
; newer catch-up step discards the older step's unplayed requests, so sound
; never lags behind authoritative simulation time.
    call w3d_audio_begin_quantum
    call w3d_death_fixed_step
    jr c,@step_complete
    call w3d_simulate_player_step
    call w3d_death_promote_lethal_latch
@step_complete:
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
    bit 1,(ix+7)                 ; Up arrow / use
    jr z,@not_use
    or W3D_CONTROL_USE
@not_use:
    bit 2,(ix+12)                ; Space / attack
    jr z,@done
    or W3D_CONTROL_ATTACK
@done:
    ld (w3d_controls),a
    ret

; One fixed 30 Hz input/integration quantum. Door simulation precedes player
; input, matching the original update order; a newly operated door therefore
; begins moving on the next quantum. Rotation precedes translation.
w3d_simulate_player_step:
; Death is a stable gameplay latch until a future restart/respawn slice. The
; foreground loop still drains fixed time, polls Escape and submits the final
; health/dead-face snapshot; only world simulation freezes.
    ld a,(w3d_player_dead)
    or a
    ret nz
    call w3d_simulate_doors
    call w3d_sample_controls
    call w3d_update_player_thrustspeed
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
    and W3D_CONTROL_W|W3D_CONTROL_S
    cp W3D_CONTROL_W               ; exactly W: current heading
    jr nz,@check_s
    ld de,0
    call w3d_move_at_heading_offset
    jr @strafe_translation
@check_s:
    cp W3D_CONTROL_S               ; exactly S: opposite heading
    jr nz,@strafe_translation
    ld de,180
    call w3d_move_at_heading_offset

@strafe_translation:
    ld a,(w3d_controls)
    and W3D_CONTROL_A|W3D_CONTROL_D
    cp W3D_CONTROL_A               ; exactly A: 90 degrees left
    jr nz,@check_d
    ld de,90
    call w3d_move_at_heading_offset
    jr @pickups
@check_d:
    cp W3D_CONTROL_D               ; exactly D: 90 degrees right
    jr nz,@pickups
    ld de,270
    call w3d_move_at_heading_offset
@pickups:
    call w3d_refresh_player_area
    call w3d_collect_pending_pickups
    call w3d_simulate_player_combat
    jp w3d_simulate_actors

; Reconstruct the original per-frame `thrustspeed` gameplay signal from this
; port's fixed 0x1000 movement requests. Opposite keys cancel before they can
; contribute; collision does not, matching Thrust() adding speed before
; ClipMove(). A cardinal request is 4096 and a forward+strafe diagonal is
; 8192, so the original RUNSPEED=6000 test remains meaningful.
w3d_update_player_thrustspeed:
    ld hl,0
    ld a,(w3d_controls)
    and W3D_CONTROL_W|W3D_CONTROL_S
    cp W3D_CONTROL_W
    jr z,@forward_axis
    cp W3D_CONTROL_S
    jr nz,@strafe_axis
@forward_axis:
    ld de,01000h
    add.s hl,de
@strafe_axis:
    ld a,(w3d_controls)
    and W3D_CONTROL_A|W3D_CONTROL_D
    cp W3D_CONTROL_A
    jr z,@strafe
    cp W3D_CONTROL_D
    jr nz,@store
@strafe:
    ld de,01000h
    add.s hl,de
@store:
; The value is deliberately uint16. An unsuffixed ADL store would write HLU
; across the following health byte, so publish only the two significant bytes.
    ld a,l
    ld (w3d_player_thrustspeed+0),a
    ld a,h
    ld (w3d_player_thrustspeed+1),a
    ret

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
    jp z,@blocked
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
    call w3d_player_actors_clear
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
    ld de,W3D_PLAYER_COLLISION_RADIUS
    jr w3d_compute_square_bounds

; CloseDoor's adjacent-reservation guard uses the original actor MINDIST,
; independently of both the player wall radius and actor/player clearance.
w3d_compute_door_actor_bounds:
    ld de,W3D_DOOR_ACTOR_CLEARANCE

; IX -> int32 x/y; DE -> 16-bit radius. Populate the shared clip-bound
; scratch. The caller-selected radius remains live through all four bounds.
w3d_compute_square_bounds:
    ld hl,0
    ld l,(ix+0)
    ld h,(ix+1)
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
    call w3d_static_blocks_candidate
    or a
    jr nz,@blocked
    jr @clear
@map_occupied:
    cp W3D_TILE_DOOR_MIN
    jr c,@blocked
    cp W3D_TILE_DOOR_MAX+1
    jr nc,@blocked
    and W3D_TILE_DOOR_MASK
    call w3d_compare_door_index
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
    ld d,a
    ld e,W3D_DOOR_SIZE
    mlt de
    inc de
    dec.s de
    ld hl,w3d_doors
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

; Build an 8 KiB dense broad-phase resolution table once per level/attempt.
; Each uint16 entry is static slot+1; zero means that tile has no blocking
; static. The immutable bitset remains authoritative for broad-phase hits,
; while this table makes the rare narrow phase constant-time.
w3d_build_static_collision_lookup:
    xor a
    ld hl,w3d_static_collision_lookup
    ld (hl),a
    ld de,w3d_static_collision_lookup+1
    ld bc,W3D_MAP_BYTES*2-1
    ldir
    ld hl,0
    ld (w3d_current_static_index),hl
@loop:
    ld hl,(w3d_current_static_index)
    call w3d_load_static_count_de
    or a
    sbc.s hl,de
    ret nc
    call w3d_static_pointer_from_current
    ld a,(ix+W3D_STATIC_TILEX)
    ld b,a
    ld a,(ix+W3D_STATIC_TILEY)
    ld c,a
    push bc
    call w3d_static_tile_blocked
    pop bc
    or a
    jr z,@next
    call w3d_static_collision_lookup_address
    ld de,(w3d_current_static_index)
    inc.s de
    ld (hl),e
    inc hl
    ld (hl),d
@next:
    ld hl,(w3d_current_static_index)
    inc.s hl
    ld (w3d_current_static_index),hl
    jr @loop

; B=x,C=y -> HL=&uint16 lookup[y*64+x]. Preserves BC; DE is scratch.
w3d_static_collision_lookup_address:
    ld e,c
    ld d,0
    inc de
    dec.s de
    sla e                           ; y * 128
    rl d
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    ld a,b
    add a,a                        ; x * 2
    add a,e
    ld e,a
    jr nc,@ready
    inc d
@ready:
    ld hl,w3d_static_collision_lookup
    add hl,de
    ret

; B=x,C=y, IX -> candidate player pose. Return A=1 only when the occupancy
; broad phase hits and the candidate center is inside the resolved static's
; inclusive W3D_PHYSICAL_OBJECT_CLEARANCE square. A bit/table or table/record
; disagreement fails
; closed, preventing corrupt level state from silently becoming traversable.
w3d_static_blocks_candidate:
    push bc
    call w3d_static_tile_blocked
    pop bc
    or a
    ret z
    call w3d_static_collision_lookup_address
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    or e
    jp z,@blocked
    dec.s de                       ; stored slot+1 -> zero-based slot
    ld hl,W3D_MAX_STATICS
    or a
    sbc.s hl,de
    jp c,@blocked
    jp z,@blocked
    push iy
    call w3d_static_pointer_iy_from_de
    ld a,(iy+W3D_STATIC_TILEX)
    cp b
    jr nz,@corrupt
    ld a,(iy+W3D_STATIC_TILEY)
    cp c
    jr nz,@corrupt
    ld a,(iy+W3D_STATIC_SHAPENUM+0)
    inc a
    jr nz,@x
    ld a,(iy+W3D_STATIC_SHAPENUM+1)
    inc a
    jr z,@corrupt
@x:
    ld a,(ix+2)
    cp b
    jr nz,@clear
    ld hl,0
    ld l,(ix+0)
    ld h,(ix+1)
    ld de,08000h-W3D_PHYSICAL_OBJECT_CLEARANCE
    or a
    sbc.s hl,de
    jr c,@clear
    ld hl,0
    ld l,(ix+0)
    ld h,(ix+1)
    ld de,08000h+W3D_PHYSICAL_OBJECT_CLEARANCE+1
    or a
    sbc.s hl,de
    jr nc,@clear
@y:
    ld a,(ix+6)
    cp c
    jr nz,@clear
    ld hl,0
    ld l,(ix+4)
    ld h,(ix+5)
    ld de,08000h-W3D_PHYSICAL_OBJECT_CLEARANCE
    or a
    sbc.s hl,de
    jr c,@clear
    ld hl,0
    ld l,(ix+4)
    ld h,(ix+5)
    ld de,08000h+W3D_PHYSICAL_OBJECT_CLEARANCE+1
    or a
    sbc.s hl,de
    jr nc,@clear
    pop iy
@blocked:
    ld a,1
    ret
@corrupt:
    pop iy
    jr @blocked
@clear:
    pop iy
    xor a
    ret

; DE=zero-based uint16 stable static slot -> IY=runtime static record.
w3d_static_pointer_iy_from_de:
    push de
    pop hl
    add hl,hl                       ; 2 * slot
    add hl,de                       ; 3 * slot
    add hl,hl                       ; 6 * slot
    ld de,w3d_statics
    add hl,de
    push hl
    pop iy
    ret

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
    call w3d_load_static_count_de
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
; current HUD/gameplay subset. Refused health/ammo/gibs pickups remain active
; and silent exactly as in the original; every successful consumption queues
; one full-gain unpositioned logical pickup sound before removing its static.
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
    call w3d_request_current_pickup_sound
    ld a,0ffh
    ld (ix+W3D_STATIC_SHAPENUM+0),a
    ld (ix+W3D_STATIC_SHAPENUM+1),a
    call w3d_mark_current_static_dirty
    ld a,1
    ret

; IX=current successfully consumed static. w3d_audio_request consumes A/B/C
; and may destroy AF/BC/DE/HL; its fixed ABI preserves IX/IY. The explicit IX
; save keeps this producer correct for a future backend with weaker internals.
w3d_request_current_pickup_sound:
    ld a,(ix+W3D_STATIC_ITEMNUMBER)
    cp W3D_ITEM_GIBS
    jp z,@gibs
    cp W3D_ITEM_ALPO
    jp z,@food
    cp W3D_ITEM_FIRSTAID
    jp z,@firstaid
    cp W3D_ITEM_KEY1
    jp c,@none
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
    jp z,@ammo
    cp W3D_ITEM_CLIP2
    jp z,@ammo
    cp W3D_ITEM_MACHINEGUN
    jp z,@machinegun
    cp W3D_ITEM_CHAINGUN
    jp z,@chaingun
    cp W3D_ITEM_FOOD
    jp z,@food
    cp W3D_ITEM_FULLHEAL
    jp nz,@none
    ld a,W3D_AUDIO_SOUND_BONUS1UP
    jr @request
@gibs:
    ld a,W3D_AUDIO_SOUND_SLURPIE
    jr @request
@food:
    ld a,W3D_AUDIO_SOUND_HEALTH1
    jr @request
@firstaid:
    ld a,W3D_AUDIO_SOUND_HEALTH2
    jr @request
@key:
    ld a,W3D_AUDIO_SOUND_GETKEY
    jr @request
@cross:
    ld a,W3D_AUDIO_SOUND_BONUS1
    jr @request
@chalice:
    ld a,W3D_AUDIO_SOUND_BONUS2
    jr @request
@bible:
    ld a,W3D_AUDIO_SOUND_BONUS3
    jr @request
@crown:
    ld a,W3D_AUDIO_SOUND_BONUS4
    jr @request
@ammo:
    ld a,W3D_AUDIO_SOUND_GETAMMO
    jr @request
@machinegun:
    ld a,W3D_AUDIO_SOUND_GETMACHINE
    jr @request
@chaingun:
    ld a,W3D_AUDIO_SOUND_GETGATLING
@request:
    ld b,127
    ld c,0                          ; unpositioned
    push ix
    call w3d_audio_request
    pop ix
@none:
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
; GiveAmmo restores the chosen weapon from an empty magazine only while the
; source attack frame is zero.  A pickup during another attack frame must not
; switch attackinfo rows underneath the active animation.
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
    ld a,(w3d_player_attack_frame)
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
    call w3d_mark_hud_dirty
    jp w3d_player_combat_refresh_shape

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
    call w3d_mark_hud_dirty
    jp w3d_player_combat_refresh_shape

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

; Return the uint16 runtime high-water count in DE with DEU deliberately zero.
; A native ADL load from the two-byte field would consume the following byte.
w3d_load_static_count_de:
    ld de,0
    ld a,(w3d_static_count+0)
    ld e,a
    ld a,(w3d_static_count+1)
    ld d,a
    ret

w3d_mark_current_static_dirty:
    ld hl,(w3d_current_static_index)
    ld de,w3d_static_dirty
    add hl,de
    ld a,1
    ld (hl),a
    ld (w3d_world_dirty),a
    ret

; ---------------------------------------------------------------------------
; Runtime item drops
; ---------------------------------------------------------------------------

; PlaceItemType's ordinary-combat subset. A=itemnumber, B=tilex, C=tiley.
; Reuse the first collected/removed slot (shapenum=-1), otherwise append one
; stable VDP identity up to the original MAXSTATS=400 capacity. Carry is set
; on success and clear if the item is unsupported or the pool is full.
w3d_place_item_type:
    cp W3D_ITEM_CLIP2
    jr z,@clip2
    cp W3D_ITEM_MACHINEGUN
    jr z,@machinegun
    or a
    ret
@clip2:
    ld d,28                         ; SPR_STAT_26
    jr @shape_ready
@machinegun:
    ld d,29                         ; SPR_STAT_27
@shape_ready:
    ld (w3d_drop_itemnumber),a
    ld a,b
    ld (w3d_drop_tilex),a
    ld a,c
    ld (w3d_drop_tiley),a
    ld a,d
    ld (w3d_drop_shapenum),a

    ld hl,0
    ld (w3d_current_static_index),hl
@find_reusable:
    ld hl,(w3d_current_static_index)
    call w3d_load_static_count_de
    or a
    sbc.s hl,de
    jr nc,@append
    call w3d_static_pointer_from_current
    ld a,(ix+W3D_STATIC_SHAPENUM+0)
    inc a
    jr nz,@next
    ld a,(ix+W3D_STATIC_SHAPENUM+1)
    inc a
    jr z,@write_record
@next:
    ld hl,(w3d_current_static_index)
    inc.s hl
    ld (w3d_current_static_index),hl
    jr @find_reusable

@append:
    call w3d_load_static_count_de
    ex de,hl
    ld de,W3D_MAX_STATICS
    or a
    sbc.s hl,de
    jr nc,@full
    add.s hl,de                     ; restore old count/index
    ld (w3d_current_static_index),hl
    inc.s hl
; Count is uint16; publish only its two significant bytes in ADL mode.
    ld a,l
    ld (w3d_static_count+0),a
    ld a,h
    ld (w3d_static_count+1),a
    call w3d_static_pointer_from_current

@write_record:
    ld a,(w3d_drop_tilex)
    ld (ix+W3D_STATIC_TILEX),a
    ld a,(w3d_drop_tiley)
    ld (ix+W3D_STATIC_TILEY),a
    ld a,(w3d_drop_shapenum)
    ld (ix+W3D_STATIC_SHAPENUM+0),a
    xor a
    ld (ix+W3D_STATIC_SHAPENUM+1),a
    ld a,W3D_STATIC_FLAG_BONUS
    ld (ix+W3D_STATIC_FLAGS),a
    ld a,(w3d_drop_itemnumber)
    ld (ix+W3D_STATIC_ITEMNUMBER),a
    call w3d_mark_current_static_dirty
    scf
    ret
@full:
    or a
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

; Turn the latched Up-arrow state into one operation per physical key press.
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

; Operate the door whose cell currently contains the player, otherwise exactly
; one adjacent tile in the nearest cardinal direction.  Center-plane collision
; deliberately permits the player to enter a door well, so current-cell
; priority keeps Up Arrow useful throughout that recess. A malformed current
; door byte fails closed instead of accidentally operating a neighboring door.
; Adjacent angle sectors preserve the original boundary behavior: 315 remains
; south; 316 begins the east sector. The original elevator switch is operable
; only from its east/west faces; area zero selects the secret exit.
w3d_use_adjacent_door:
    xor a
    ld (w3d_use_elevator_ok),a
    ld a,(w3d_player_pose+2)
    ld b,a
    ld a,(w3d_player_pose+6)
    ld c,a
    call w3d_map_read
    cp W3D_TILE_DOOR_MIN
    jr c,@select_adjacent
    cp W3D_TILE_DOOR_MAX+1
    jr nc,@select_adjacent
    jp @resolve_door_tile

@select_adjacent:
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
    ld a,1
    ld (w3d_use_elevator_ok),a
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
    ld a,1
    ld (w3d_use_elevator_ok),a
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
    cp W3D_ELEVATOR_SWITCH_TILE
    jr nz,@check_door_tile
    ld a,(w3d_use_elevator_ok)
    or a
    ret z
    ld a,(w3d_player_area)
    or a
    ld a,W3D_LEVEL_COMPLETION_NORMAL
    jr nz,@complete_level
    ld a,W3D_LEVEL_COMPLETION_SECRET
@complete_level:
    ld (w3d_level_completion),a
    ld a,W3D_AUDIO_SOUND_LEVELDONE
    ld b,127
    ld c,0
    jp w3d_audio_request
@check_door_tile:
    cp W3D_TILE_DOOR_MIN
    ret c
    cp W3D_TILE_DOOR_MAX+1
    ret nc
@resolve_door_tile:
    and W3D_TILE_DOOR_MASK
    call w3d_compare_door_index
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
    jr z,@locked
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

@locked:
    ld a,W3D_AUDIO_SOUND_NOWAY
    ld b,127
    ld c,0                          ; unpositioned
    call w3d_audio_request
    ret

; Actor-side OpenDoor. A=door index, return A=current action. Unlike the
; player's use command this deliberately ignores locks. OPEN resets its hold
; timer; CLOSED/CLOSING reverses toward OPENING; OPENING is unchanged. IX is
; preserved because T_Path owns it as the current actor record.
w3d_request_open_door:
    call w3d_compare_door_index
    jr c,@valid
    ld a,0ffh
    ret
@valid:
    ld (w3d_current_door_index),a
    push ix
    call w3d_door_pointer_from_index
    ld a,(ix+W3D_DOOR_ACTION)
    cp W3D_DOOR_ACTION_OPEN
    jr z,@already_open
    cp W3D_DOOR_ACTION_OPENING
    jr z,@return
    ld a,W3D_DOOR_ACTION_OPENING
    ld (ix+W3D_DOOR_ACTION),a
    call w3d_zero_current_door_timer
    call w3d_mark_current_door_dirty
    ld a,W3D_DOOR_ACTION_OPENING
    jr @return
@already_open:
    call w3d_zero_current_door_timer
    ld a,W3D_DOOR_ACTION_OPEN
@return:
    pop ix
    ret

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
    call w3d_compare_door_index
    jp nc,w3d_refresh_areas_if_dirty
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
    ld a,h
    or l
    jr nz,@advance
    call w3d_mark_area_topology_dirty ; edge becomes live after this step
    ld a,W3D_AUDIO_SOUND_OPENDOOR
    push hl                           ; spatial gating uses HL as scratch
    call w3d_audio_request_current_door
    pop hl                            ; restore the zero position accumulator
@advance:
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
    call w3d_door_anything_obstructs
    or a
    ret nz                           ; remain open and retry next update
    call w3d_door_adjacent_actor_obstructs
    or a
    ret nz                           ; crossing body has not cleared the well
    ld a,W3D_DOOR_ACTION_CLOSING
    ld (ix+W3D_DOOR_ACTION),a
    ld a,W3D_AUDIO_SOUND_CLOSEDOOR
    call w3d_audio_request_current_door
    jp w3d_mark_current_door_dirty

; Root-provided tile-helper ABI: A=logical id, B=tilex, C=tiley. It may
; destroy AF/BC/DE/HL. Preserve IX because every caller still owns the current
; authoritative door record after the enqueue. WL_ACT1 emits door motion only
; when at least one valid endpoint area is currently connected to the player;
; first-open calls this before the pending topology rebuild, so the listener
; side's old reachability is exactly the intended gate.
w3d_audio_request_current_door:
    push af
    ld a,(ix+W3D_DOOR_AREA1)
    call w3d_audio_door_area_reachable
    or a
    jr nz,@request
    ld a,(ix+W3D_DOOR_AREA2)
    call w3d_audio_door_area_reachable
    or a
    jr z,@silent
@request:
    pop af
    ld b,(ix+W3D_DOOR_TILEX)
    ld c,(ix+W3D_DOOR_TILEY)
    push ix
    call w3d_audio_request_tile
    pop ix
    ret
@silent:
    pop af
    or a
    ret

; A=area endpoint. Return A=1 iff it is in range and player-reachable.
w3d_audio_door_area_reachable:
    cp W3D_NUM_AREAS
    jr nc,@no
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_area_by_player
    add hl,de
    ld a,(hl)
    or a
    ret z
    ld a,1
    ret
@no:
    xor a
    ret

w3d_advance_closing_door:
    call w3d_door_anything_obstructs
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
    ld a,(ix+W3D_DOOR_POSITION+0)
    ld b,a
    ld a,(ix+W3D_DOOR_POSITION+1)
    or b
    call nz,w3d_mark_area_topology_dirty ; edge dies with the zero position
    xor a
    ld (ix+W3D_DOOR_POSITION+0),a
    ld (ix+W3D_DOOR_POSITION+1),a
    ld (ix+W3D_DOOR_ACTION),a         ; W3D_DOOR_ACTION_CLOSED
    call w3d_zero_current_door_timer
    jp w3d_mark_current_door_dirty

; Test the player first, then every markable live actor against exactly the
; same finite slab/AABB geometry. Thus occupants in either recessed door well
; reverse a closing panel instead of being clipped by it. IX remains the
; current authoritative door for the caller.
w3d_door_anything_obstructs:
    call w3d_door_player_obstructs
    or a
    ret nz
    jp w3d_door_actor_obstructs

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

w3d_door_actor_obstructs:
    push iy
    push ix
    push ix
    pop iy                            ; IY=current authoritative door

; Preserve the original CloseDoor invariant first: an actor reserving the
; door cell holds a fully open door even though its rendered slab is empty at
; position FFFF. This closes the gap between our separate tilemap/actorat
; planes and the DOS actorat door sentinel lifecycle.
    ld b,(iy+W3D_DOOR_TILEX)
    ld c,(iy+W3D_DOOR_TILEY)
    call w3d_actorat_get
    or a
    jr nz,@blocked

; Adjacent physical actors then use the renderer-matching finite slab test.
    ld a,(w3d_actor_live_head)
@loop:
    cp W3D_SLOT_NONE
    jr z,@clear
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_NONMARK|W3D_ACTOR_FLAG_NEVERMARK
    jr nz,@next
    call w3d_compute_player_bounds   ; generic square bounds from actor x/y
    call w3d_clip_bounds_overlap_door
    or a
    jr nz,@blocked
@next:
    ld a,(ix+W3D_ACTOR_NEXT)
    jr @loop
@blocked:
    ld a,1
    jr @return
@clear:
    xor a
@return:
    pop ix
    pop iy
    ret

; Close-start guard matching the original CloseDoor neighbour checks. A path
; actor reserves its destination tile before its physical center arrives, so
; after crossing the door center its reservation may already be on the far
; side while its body still occupies the well. A fully-open finite slab is
; empty and cannot detect that case. Inspect only the two axis-adjacent
; reservations and require the actor's MINDIST-radius body to clear the door
; tile before CLOSING begins. This is intentionally actor-only: the accepted
; player well/slab behavior is unchanged.
;
; IX -> authoritative door. Return A=1 obstructed, A=0 clear; preserve IX/IY.
w3d_door_adjacent_actor_obstructs:
    push iy
    push ix
    push ix
    pop iy
    ld a,(iy+W3D_DOOR_VERTICAL)
    or a
    jr z,@horizontal

; Vertical door: check the reservations immediately west/east and the
; corresponding high/low X bounds.
    ld a,(iy+W3D_DOOR_TILEX)
    or a
    jp z,@blocked
    dec a
    ld b,a
    ld c,(iy+W3D_DOOR_TILEY)
    call w3d_door_reserved_actor_pointer
    jp c,@blocked
    or a
    jr z,@vertical_east
    call w3d_compute_door_actor_bounds
    ld a,(w3d_clip_x_high)
    cp (iy+W3D_DOOR_TILEX)
    jp z,@blocked
@vertical_east:
    ld a,(iy+W3D_DOOR_TILEX)
    inc a
    cp W3D_MAP_SIZE
    jp nc,@blocked
    ld b,a
    ld c,(iy+W3D_DOOR_TILEY)
    call w3d_door_reserved_actor_pointer
    jp c,@blocked
    or a
    jr z,@clear
    call w3d_compute_door_actor_bounds
    ld a,(w3d_clip_x_low)
    cp (iy+W3D_DOOR_TILEX)
    jp z,@blocked
    jr @clear

; Horizontal door: axis-swapped north/south checks.
@horizontal:
    ld a,(iy+W3D_DOOR_TILEY)
    or a
    jp z,@blocked
    dec a
    ld c,a
    ld b,(iy+W3D_DOOR_TILEX)
    call w3d_door_reserved_actor_pointer
    jp c,@blocked
    or a
    jr z,@horizontal_south
    call w3d_compute_door_actor_bounds
    ld a,(w3d_clip_y_high)
    cp (iy+W3D_DOOR_TILEY)
    jp z,@blocked
@horizontal_south:
    ld a,(iy+W3D_DOOR_TILEY)
    inc a
    cp W3D_MAP_SIZE
    jp nc,@blocked
    ld c,a
    ld b,(iy+W3D_DOOR_TILEX)
    call w3d_door_reserved_actor_pointer
    jp c,@blocked
    or a
    jr z,@clear
    call w3d_compute_door_actor_bounds
    ld a,(w3d_clip_y_low)
    cp (iy+W3D_DOOR_TILEY)
    jp z,@blocked
@clear:
    xor a
    jr @return
@blocked:
    ld a,1
@return:
    pop ix
    pop iy
    ret

; B/C=reservation cell. Empty returns A=0/carry clear; a valid live actor
; returns IX -> record and A=1/carry clear. Corrupt or stale free slots fail
; closed with carry set.
w3d_door_reserved_actor_pointer:
    call w3d_actorat_get
    or a
    ret z
    cp W3D_MAX_ACTORS
    jr nc,@invalid
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_ACTIVE)
    cp W3D_ACTOR_ACTIVE_FREE
    jr z,@invalid
    ld a,1
    or a
    ret
@invalid:
    scf
    ret

; A=door index; returns IX -> authoritative W3D_DOOR_SIZE record.
w3d_door_pointer_from_index:
    ld d,a
    ld e,W3D_DOOR_SIZE
    mlt de
    inc de
    dec.s de
    ld hl,w3d_doors
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

; Respawn presentation entry. init_level clears every VDP-side door, actor,
; static, and map reference while leaving resident bitmap assets intact. The
; reseed hook has already marked the complete authoritative fixture prefix;
; replay it and submit exactly one purpose-tagged render through the ordinary
; dirty bridge. The caller must have established RESPawn purpose and verified
; that no asynchronous owner is active. Ownership is nevertheless acquired
; here before destructive init_level bytes are allowed onto the wire.
w3d_submit_level_reset:
    call w3d_mark_render_submitted
    ret c
    ld hl,@init_level_command
    ld bc,@init_level_end-@init_level_command
    rst.lil 18h
    jp w3d_submit_dirty_world_render_marked
@init_level_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,1
    dw W3D_FIXTURE_TILEMAP_BUFFER_ID
@init_level_end:

; Send every changed door/static/HUD field, then the changed player pose,
; followed by one render request. Assets/map remain resident. Each dirty flag
; is cleared only after its complete command crosses the synchronous VDU
; boundary. Mark ownership first: a rejected overlapping submission must emit
; no state bytes and must leave every dirty flag intact for diagnosis/retry.
w3d_submit_dirty_world_render:
    call w3d_mark_render_submitted
    ret c

w3d_submit_dirty_world_render_marked:
    xor a
    ld (w3d_current_door_index),a
@door_loop:
    ld a,(w3d_current_door_index)
    call w3d_compare_door_index
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
    ld bc,W3D_DOOR_WIRE_SIZE
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
    call w3d_submit_dirty_actors
    ld hl,0
    ld (w3d_current_static_index),hl
@static_loop:
    ld hl,(w3d_current_static_index)
    call w3d_load_static_count_de
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

@view_weapon:
    ld a,(w3d_player_weapon_shape_dirty)
    or a
    jr z,@player
    ld a,(w3d_player_weapon_shape+0)
    ld (@view_weapon_shape+0),a
    ld a,(w3d_player_weapon_shape+1)
    ld (@view_weapon_shape+1),a
    ld hl,@view_weapon_command
    ld bc,@view_weapon_end-@view_weapon_command
    rst.lil 18h
    xor a
    ld (w3d_player_weapon_shape_dirty),a

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
    ld hl,@render_command
    ld bc,@render_end-@render_command
    rst.lil 18h
    or a
    ret
@door_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,3
@door_number:
    db 0
@door_record:
    ds W3D_DOOR_WIRE_SIZE
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
@view_weapon_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,8
@view_weapon_shape:
    dw -1
@view_weapon_end:
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

; Sum of requested movement magnitudes for the current 30-Hz quantum. This
; is the eZ80 counterpart of WL_AGENT.C's `thrustspeed`.
w3d_player_thrustspeed:
    dw 0

w3d_player_dead:
    db 0

w3d_player_last_attacker:
    db W3D_SLOT_NONE

w3d_player_killer:
    db W3D_SLOT_NONE

w3d_game_difficulty:
    db W3D_FIXTURE_DIFFICULTY

w3d_requested_difficulty:
    db W3D_FIXTURE_DIFFICULTY

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
    ds W3D_MAX_DOORS*W3D_DOOR_SIZE

w3d_door_timers:
    ds W3D_MAX_DOORS*2

w3d_door_dirty:
    ds W3D_MAX_DOORS

w3d_statics:
    ds W3D_MAX_STATICS*W3D_STATIC_SIZE

w3d_static_dirty:
    ds W3D_MAX_STATICS

; uint16 slot+1 per map cell; 0 means no blocking static.
w3d_static_collision_lookup:
    ds W3D_MAP_BYTES*2

w3d_static_count:
    dw W3D_FIXTURE_STATIC_COUNT

w3d_current_static_index:
    dl 0

w3d_drop_tilex:
    db 0
w3d_drop_tiley:
    db 0
w3d_drop_shapenum:
    db 0
w3d_drop_itemnumber:
    db 0

w3d_current_door_index:
    db 0

w3d_use_elevator_ok:
    db 0

w3d_level_completion:
    db W3D_LEVEL_COMPLETION_NONE

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
