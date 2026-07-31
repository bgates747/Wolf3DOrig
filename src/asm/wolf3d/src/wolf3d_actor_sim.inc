; =============================================================================
; Original-style actor state runner and path-patrol movement.
;
; The foreground simulation runs at an exact 30 Hz while the original game
; expresses state durations and speeds in 70-Hz tics. One shared 2,2,3 tic
; cadence is exact over three fixed frames. This deliberately retains the
; DOS scheduler's variable-tics semantics, including SpawnNewObj's unusual
; zero-ticcount latch: a timed state seeded with zero thinks forever without
; advancing its animation state.
;
; Physical x/y and cached tilex/tiley are intentionally different. As in the
; original, actorat reserves the actor's destination tile while x/y may still
; be one tile behind it. T_Path releases that claim around the actor turn,
; moves toward the cached center, follows plane-1 arrows, and then reclaims
; the newest destination.
; =============================================================================

W3D_ACTOR_TRANSITION_LIMIT: equ 16

; CPU-owned gameplay projection hooks. They mirror the current VDP defaults
; in reduced 8.8 coordinates and deliberately avoid asynchronous visibility
; feedback: AI/RNG therefore remains tied to simulation time, not render rate.
W3D_ACTOR_VIEW_SCALE:                 equ 87
W3D_ACTOR_VIEW_FOCAL_MINUS_SIZE_Q8:   equ 017h
W3D_ACTOR_VIEW_MINDIST_Q8:            equ 058h
W3D_ACTOR_VIEW_LEFT_QUOTIENT_LIMIT:   equ 128
W3D_ACTOR_VIEW_RIGHT_QUOTIENT_LIMIT:  equ 129
W3D_PLAYER_RUN_SPEED:                 equ 01770h

; Reset only the scheduling/diagnostic state owned by this include. The pool
; and generated actors are initialized independently by wolf3d_actors.inc.
w3d_initialize_actor_simulation:
    xor a
    ld (w3d_actor_tic_phase),a
    ld (w3d_actor_frame_tics),a
    ld (w3d_player_made_noise),a
    ld (w3d_actor_fault_count+0),a
    ld (w3d_actor_fault_count+1),a
    ld a,W3D_FIXTURE_RND_INDEX_AFTER_SPAWN
    ld (w3d_random_index),a
    ld a,1
    ld (w3d_awareness_enabled),a
    ld hl,w3d_fixture_tilemap
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_TILEMAP),hl
    ld hl,w3d_doors
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_DOORS),hl
    ld hl,w3d_area_by_player
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_AREAS),hl
    xor a
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_MADENOISE),a
    ret

; Publish one fixed-step noise event.  The current control layer has no weapon
; input yet, but this is the stable producer API for weapon fire and successful
; player damage to an actor.
; Every scheduled actor sees the same byte; w3d_simulate_actors clears it only
; after the complete live-list pass.
w3d_mark_player_noise:
    ld a,1
    ld (w3d_player_made_noise),a
    ret

; Advance every scheduled actor once after doors and player movement. The
; saved NEXT byte makes removal during the current turn traversal-safe.
w3d_simulate_actors:
    call w3d_actor_advance_frame_tics
    call w3d_prepare_actor_sight_context
    ld a,(w3d_actor_live_head)
@loop:
    cp W3D_SLOT_NONE
    jr z,@done
    ld (w3d_current_actor_index),a
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_NEXT)
    ld (w3d_actor_iteration_next),a

; Match DoActor's scheduling gate without conflating connectivity with the
; persistent active byte. ACTIVE_YES/ALWAYS run globally; ACTIVE_NO runs only
; while its validated area is connected to the player; FREE never runs.
    ld a,(ix+W3D_ACTOR_ACTIVE)
    cp W3D_ACTOR_ACTIVE_FREE
    jr z,@next
    cp W3D_ACTOR_ACTIVE_YES
    jr z,@scheduled
    cp W3D_ACTOR_ACTIVE_ALWAYS
    jr z,@scheduled
    or a
    jr nz,@next                       ; malformed active values fail closed
    ld a,(ix+W3D_ACTOR_AREA)
    cp W3D_NUM_AREAS
    jr nc,@next
    ld de,0
    ld e,a
    ld hl,w3d_area_by_player
    add hl,de
    ld a,(hl)
    or a
    jr z,@next
@scheduled:

; Markable actors release their cached destination for the duration of their
; own turn, allowing TryWalk to inspect other reservations without seeing self.
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_NONMARK|W3D_ACTOR_FLAG_NEVERMARK
    jr nz,@run
    ld a,(w3d_current_actor_index)
    call w3d_actorat_release
@run:
    call w3d_actor_run_current
    jr c,@next                       ; actor removed/faulted

; Restore IX because later AI/action dispatch is allowed to borrow it. This
; first patrol slice treats both NONMARK and NEVERMARK as unreserved actors,
; matching pool initialization and avoiding stale claims from render-only
; entities.
    ld a,(w3d_current_actor_index)
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_NONMARK|W3D_ACTOR_FLAG_NEVERMARK
    jr nz,@next
    ld a,(w3d_current_actor_index)
    call w3d_actorat_claim
@next:
    ld a,(w3d_actor_iteration_next)
    jr @loop
@done:
    xor a
    ld (w3d_player_made_noise),a
    ret

; CheckSight consumes one stable context while actor records remain in IX.
; The visual predicate always receives made-noise=false: SightPlayer handles
; non-ambush noise before the line trace, exactly like the original wrapper.
w3d_prepare_actor_sight_context:
    ld hl,w3d_player_pose
    ld de,w3d_actor_sight_context+W3D_SIGHT_CTX_PLAYER_X
    ld bc,8
    ldir
    xor a
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_MADENOISE),a
    ret

; Produce 2,2,3 original tics on successive 30-Hz fixed updates.
w3d_actor_advance_frame_tics:
    ld a,(w3d_actor_tic_phase)
    cp 2
    jr z,@three
    inc a
    ld (w3d_actor_tic_phase),a
    ld a,2
    ld (w3d_actor_frame_tics),a
    ret
@three:
    xor a
    ld (w3d_actor_tic_phase),a
    ld a,3
    ld (w3d_actor_frame_tics),a
    ret

; IX=current actor. Carry set means the actor was removed. Timed states carry
; signed overshoot into their successors; only the final state's think runs.
w3d_actor_run_current:
    call w3d_actor_resolve_current_state
    jp c,w3d_actor_fault_current
    call w3d_actor_capture_render_signature

    ld hl,0
    ld l,(ix+W3D_ACTOR_TICCOUNT+0)
    ld h,(ix+W3D_ACTOR_TICCOUNT+1)
    ld a,h
    or l
    jp z,@think                      ; original zero-ticcount latch

    ld de,0
    ld a,(w3d_actor_frame_tics)
    ld e,a
    or a
    sbc.s hl,de
    ld (ix+W3D_ACTOR_TICCOUNT+0),l
    ld (ix+W3D_ACTOR_TICCOUNT+1),h
    bit 7,h
    jr nz,@transition_setup
    ld a,h
    or l
    jp nz,@think

@transition_setup:
    ld a,W3D_ACTOR_TRANSITION_LIMIT
    ld (w3d_actor_transitions_left),a
@transition:
    ld a,(w3d_actor_transitions_left)
    or a
    jp z,w3d_actor_fault_current
    dec a
    ld (w3d_actor_transitions_left),a

; End-state actions run before NEXT, matching DoActor. Dispatch may borrow
; index registers, so reacquire both the actor and its (possibly replaced)
; current state before following the successor byte.
    ld a,(iy+W3D_STATE_ACTION)
    call w3d_actor_dispatch_action
    jp c,w3d_actor_fault_current
    ld a,(w3d_current_actor_index)
    call w3d_actor_pointer_from_id
    call w3d_actor_resolve_current_state
    jp c,w3d_actor_fault_current
    ld a,(iy+W3D_STATE_NEXT)
    or a
    jp z,w3d_actor_remove_current
    cp W3D_STATE_COUNT
    jp nc,w3d_actor_fault_current
    ld (ix+W3D_ACTOR_STATE+0),a
    xor a
    ld (ix+W3D_ACTOR_STATE+1),a
    ld a,(ix+W3D_ACTOR_STATE+0)
    call w3d_actor_state_pointer_from_id

    ld e,(iy+W3D_STATE_TICTIME+0)
    ld d,(iy+W3D_STATE_TICTIME+1)
    ld a,d
    or e
    jr nz,@add_duration
    xor a
    ld (ix+W3D_ACTOR_TICCOUNT+0),a
    ld (ix+W3D_ACTOR_TICCOUNT+1),a
    jp @think
@add_duration:
    ld hl,0
    ld l,(ix+W3D_ACTOR_TICCOUNT+0)
    ld h,(ix+W3D_ACTOR_TICCOUNT+1)
    add.s hl,de
    ld (ix+W3D_ACTOR_TICCOUNT+0),l
    ld (ix+W3D_ACTOR_TICCOUNT+1),h
    bit 7,h
    jr nz,@transition
    ld a,h
    or l
    jr z,@transition

@think:
    call w3d_actor_resolve_current_state
    jp c,w3d_actor_fault_current
    ld a,(iy+W3D_STATE_THINK)
    or a
    jr z,@thought
    cp W3D_STATE_THINK_PATH
    jr z,@path
    cp W3D_STATE_THINK_STAND
    jr z,@stand
    cp W3D_STATE_THINK_CHASE
    jr z,@chase
    cp W3D_STATE_THINK_DOG_CHASE
    jp nz,w3d_actor_fault_current
    call w3d_actor_think_dog_chase
    cp W3D_CHASE_RESULT_CORRUPT
    jp z,w3d_actor_fault_current
    cp W3D_CHASE_RESULT_DOG_JUMP
    jr nz,@thought
    ld a,W3D_STATE_DOG_JUMP1
    call w3d_actor_new_state
    jp c,w3d_actor_fault_current
    jr @thought
@chase:
    call w3d_actor_think_chase
    cp W3D_CHASE_RESULT_CORRUPT
    jp z,w3d_actor_fault_current
    cp W3D_CHASE_RESULT_RANGED
    jr nz,@thought
    call w3d_actor_begin_ranged_attack
    jp c,w3d_actor_fault_current
    jr @thought
@stand:
    call w3d_actor_sight_player
    cp 0ffh
    jp z,w3d_actor_fault_current
    jr @thought
@path:
    call w3d_actor_think_path
    cp 0ffh
    jp z,w3d_actor_fault_current
@thought:
    call w3d_actor_compare_render_signature
    ret c                             ; comparison may fault/free current actor
    or a                              ; clear carry: actor remains live
    ret

; A=state id. Exact NewState semantics: replace the state and reset ticcount
; to that state's full duration without changing pose, direction or distance.
; Carry reports an invalid id.
w3d_actor_new_state:
    or a
    jr z,@invalid
    cp W3D_STATE_COUNT
    jr nc,@invalid
    ld (ix+W3D_ACTOR_STATE+0),a
    xor a
    ld (ix+W3D_ACTOR_STATE+1),a
    ld a,(ix+W3D_ACTOR_STATE+0)
    call w3d_actor_state_pointer_from_id
    ld a,(iy+W3D_STATE_TICTIME+0)
    ld (ix+W3D_ACTOR_TICCOUNT+0),a
    ld a,(iy+W3D_STATE_TICTIME+1)
    ld (ix+W3D_ACTOR_TICCOUNT+1),a
    or a
    ret
@invalid:
    scf
    ret

; IX=current ordinary ranged actor. Map the exact T_Chase class switch to the
; first record of its original shooting chain.
w3d_actor_begin_ranged_attack:
    ld a,(ix+W3D_ACTOR_CLASS)
    cp W3D_CLASS_GUARD
    jr z,@guard
    cp W3D_CLASS_OFFICER
    jr z,@officer
    cp W3D_CLASS_MUTANT
    jr z,@mutant
    cp W3D_CLASS_SS
    jr nz,@invalid
    ld a,W3D_STATE_SS_SHOOT1
    jp w3d_actor_new_state
@guard:
    ld a,W3D_STATE_GRD_SHOOT1
    jp w3d_actor_new_state
@officer:
    ld a,W3D_STATE_OFC_SHOOT1
    jp w3d_actor_new_state
@mutant:
    ld a,W3D_STATE_MUT_SHOOT1
    jp w3d_actor_new_state
@invalid:
    scf
    ret

; A=W3D_STATE_ACTION_*. Unknown ids fail closed. Implementations preserve no
; index-register contract; the transition loop reacquires its actor/state.
w3d_actor_dispatch_action:
    or a
    ret z
    cp W3D_STATE_ACTION_SHOOT
    jp z,w3d_actor_action_shoot
    cp W3D_STATE_ACTION_BITE
    jp z,w3d_actor_action_bite
    scf
    ret

; ---------------------------------------------------------------------------
; Ordinary attack end actions
; ---------------------------------------------------------------------------

; IX=current guard/officer/mutant/SS. Port T_Shoot's observable gameplay
; order exactly: connected area, line trace, action-time distance, deterministic
; CPU visibility/running hitchance, one hit draw, and a second draw only on a
; hit. Sound and damage flash are intentionally deferred; health/HUD state is
; authoritative here.
w3d_actor_action_shoot:
    xor a
    ld (w3d_actor_combat_is_ss),a
    ld a,(ix+W3D_ACTOR_CLASS)
    cp W3D_CLASS_GUARD
    jr z,@class_ok
    cp W3D_CLASS_OFFICER
    jr z,@class_ok
    cp W3D_CLASS_MUTANT
    jr z,@class_ok
    cp W3D_CLASS_SS
    jp nz,@corrupt
    ld a,1
    ld (w3d_actor_combat_is_ss),a
@class_ok:
    ld a,(ix+W3D_ACTOR_AREA)
    cp W3D_NUM_AREAS
    jp nc,@corrupt
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_area_by_player
    add hl,de
    ld a,(hl)
    or a
    jp z,@no_shot

    ld iy,w3d_actor_sight_context
    call w3d_CheckLine
    or a
    jp z,@no_shot

    call w3d_actor_tile_deltas_abs
    ld a,(w3d_actor_chase_abs_x)
    ld b,a
    ld a,(w3d_actor_chase_abs_y)
    cp b
    jr c,@distance_ready
    ld b,a
@distance_ready:
    ld a,(w3d_actor_combat_is_ss)
    or a
    jr z,@store_distance
    ld a,b
    add a,a
    ld b,3
    call w3d_actor_u8_div_b          ; floor(2*dist/3)
    ld b,a
@store_distance:
    ld a,b
    ld (w3d_actor_combat_distance),a

    call w3d_actor_cpu_visible
    ld (w3d_actor_combat_visible),a

; Choose the source base chance from the current fixed-step requested speed.
; Load the uint16 bytewise: its following byte is unrelated gameplay state.
    ld hl,0
    ld a,(w3d_player_thrustspeed+0)
    ld l,a
    ld a,(w3d_player_thrustspeed+1)
    ld h,a
    ld de,W3D_PLAYER_RUN_SPEED
    or a
    sbc.s hl,de
    jr nc,@running
    ld hl,0100h                     ; walking base 256
    jr @chance_base_ready
@running:
    ld hl,00a0h                     ; running base 160
@chance_base_ready:
    ld a,(w3d_actor_combat_distance)
    ld e,a
    ld d,0
    ld a,(w3d_actor_combat_visible)
    or a
    jr z,@distance_times_eight
    sla e
    rl d                            ; *2
@distance_times_eight:
    sla e
    rl d                            ; *2 / total visible *4
    sla e
    rl d                            ; *4 / total visible *8
    sla e
    rl d                            ; *8 / total visible *16
    or a
    sbc.s hl,de
    ld a,l
    ld (w3d_actor_combat_hitchance+0),a
    ld a,h
    ld (w3d_actor_combat_hitchance+1),a

; US_RndT is consumed even for chances <=0 or >=256.
    call w3d_random_byte
    ld b,a
    ld a,(w3d_actor_combat_hitchance+1)
    bit 7,a
    jp nz,@no_shot
    or a
    jr nz,@hit
    ld a,b
    ld b,a
    ld a,(w3d_actor_combat_hitchance+0)
    ld c,a
    ld a,b
    cp c
    jp nc,@no_shot                    ; strict random < hitchance
@hit:
    call w3d_random_byte
    ld b,a
    ld a,(w3d_actor_combat_distance)
    cp 2
    jr c,@damage_shift_two
    cp 4
    jr c,@damage_shift_three
    srl b
@damage_shift_three:
    srl b
@damage_shift_two:
    srl b
    srl b
    ld a,b
    call w3d_take_player_damage
@no_shot:
    or a
    ret
@corrupt:
    scf
    ret

; IX=current dog. T_Bite checks the physical position at action time, allowing
; the player to escape during the 20-tic jump wind-up. Each inclusive axis
; bound is TILEGLOBAL+MINACTORDIST = 0x20000. Only an in-range attempt draws
; RNG; only a hit draws damage.
w3d_actor_action_bite:
    ld a,(ix+W3D_ACTOR_CLASS)
    cp W3D_CLASS_DOG
    jr nz,@corrupt
    call w3d_actor_bite_in_range
    or a
    jr z,@no_bite
    call w3d_random_byte
    cp 180
    jr nc,@no_bite
    call w3d_random_byte
    srl a
    srl a
    srl a
    srl a
    call w3d_take_player_damage
@no_bite:
    or a
    ret
@corrupt:
    scf
    ret

; Return A=1 iff both absolute physical-axis deltas are <=0x20000.
w3d_actor_bite_in_range:
    ld hl,(w3d_player_pose+0)
    ld de,(ix+W3D_ACTOR_X)
    or a
    sbc hl,de
    jr nc,@x_abs
    ld hl,(ix+W3D_ACTOR_X)
    ld de,(w3d_player_pose+0)
    or a
    sbc hl,de
@x_abs:
    ld de,020001h
    or a
    sbc hl,de
    jr nc,@far

    ld hl,(w3d_player_pose+4)
    ld de,(ix+W3D_ACTOR_Y)
    or a
    sbc hl,de
    jr nc,@y_abs
    ld hl,(ix+W3D_ACTOR_Y)
    ld de,(w3d_player_pose+4)
    or a
    sbc hl,de
@y_abs:
    ld de,020001h
    or a
    sbc hl,de
    jr nc,@far
    ld a,1
    ret
@far:
    xor a
    ret

; A=raw damage; w3d_current_actor_index is the attacker. Medium is the
; generated fixture default; baby quarters damage. Health saturates at zero,
; the HUD is dirtied only on a real change, and death freezes future fixed
; steps without aborting the current actor pass.
w3d_take_player_damage:
    ld b,a
    ld a,(w3d_current_actor_index)
    ld (w3d_player_last_attacker),a
    ld a,(w3d_game_difficulty)
    or a
    ld a,b
    jr nz,@difficulty_ready
    srl a
    srl a
@difficulty_ready:
    ld b,a
    ld a,(w3d_player_health)
    or a
    jr nz,@alive
    ld a,(w3d_current_actor_index)
    ld (w3d_player_killer),a
    ld a,1
    ld (w3d_player_dead),a
    or a
    ret
@alive:
    ld c,a
    ld a,b
    or a
    ret z
    ld a,c
    sub b
    jr nc,@store_health
    xor a
@store_health:
    ld (w3d_player_health),a
    or a
    jr nz,@changed
    ld a,(w3d_current_actor_index)
    ld (w3d_player_killer),a
    ld a,1
    ld (w3d_player_dead),a
@changed:
    ld a,1
    ld (w3d_pickup_scan_needed),a
    ld a,W3D_HUD_DIRTY_HEALTH
    call w3d_mark_hud_dirty
    or a
    ret

; Deterministic replacement for renderer-owned FL_VISABLE. It uses the same
; current projection constants but only authoritative CPU state. The reduced
; actor-relative vector is rotated by the generated 360-degree Q12 motion
; table. Integer cross-products reproduce truncation-toward-zero screen-edge
; inclusion without performing a division.
w3d_actor_cpu_visible:
    call w3d_actor_load_relative_q8
    call w3d_actor_load_heading_q12

; forward = relx*cos + rely*forwardY
    ld hl,0
    ld a,(w3d_actor_projection_rel_x+0)
    ld l,a
    ld a,(w3d_actor_projection_rel_x+1)
    ld h,a
    ld de,0
    ld a,(w3d_actor_projection_cos+0)
    ld e,a
    ld a,(w3d_actor_projection_cos+1)
    ld d,a
    call w3d_actor_mul_q8_q12
    ld a,l
    ld (w3d_actor_projection_term+0),a
    ld a,h
    ld (w3d_actor_projection_term+1),a

    ld hl,0
    ld a,(w3d_actor_projection_rel_y+0)
    ld l,a
    ld a,(w3d_actor_projection_rel_y+1)
    ld h,a
    ld de,0
    ld a,(w3d_actor_projection_forward_y+0)
    ld e,a
    ld a,(w3d_actor_projection_forward_y+1)
    ld d,a
    call w3d_actor_mul_q8_q12
    ld de,0
    ld a,(w3d_actor_projection_term+0)
    ld e,a
    ld a,(w3d_actor_projection_term+1)
    ld d,a
    add.s hl,de
    ld de,W3D_ACTOR_VIEW_FOCAL_MINUS_SIZE_Q8
    add.s hl,de
    bit 7,h
    jp nz,@not_visible
    ld de,W3D_ACTOR_VIEW_MINDIST_Q8
    or a
    sbc.s hl,de
    jp c,@not_visible
    add.s hl,de
    ld a,l
    ld (w3d_actor_projection_nx+0),a
    ld a,h
    ld (w3d_actor_projection_nx+1),a

; lateral = rely*cos - relx*forwardY
    ld hl,0
    ld a,(w3d_actor_projection_rel_y+0)
    ld l,a
    ld a,(w3d_actor_projection_rel_y+1)
    ld h,a
    ld de,0
    ld a,(w3d_actor_projection_cos+0)
    ld e,a
    ld a,(w3d_actor_projection_cos+1)
    ld d,a
    call w3d_actor_mul_q8_q12
    ld a,l
    ld (w3d_actor_projection_term+0),a
    ld a,h
    ld (w3d_actor_projection_term+1),a

    ld hl,0
    ld a,(w3d_actor_projection_rel_x+0)
    ld l,a
    ld a,(w3d_actor_projection_rel_x+1)
    ld h,a
    ld de,0
    ld a,(w3d_actor_projection_forward_y+0)
    ld e,a
    ld a,(w3d_actor_projection_forward_y+1)
    ld d,a
    call w3d_actor_mul_q8_q12
    ex de,hl
    ld hl,0
    ld a,(w3d_actor_projection_term+0)
    ld l,a
    ld a,(w3d_actor_projection_term+1)
    ld h,a
    or a
    sbc.s hl,de

; For negative lateral, screen x>=0 iff abs(ny)*87 < nx*128.
; For nonnegative lateral, x<=255 iff ny*87 < nx*129.
    ld c,W3D_ACTOR_VIEW_RIGHT_QUOTIENT_LIMIT
    bit 7,h
    jr z,@lateral_abs_ready
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
    ld c,W3D_ACTOR_VIEW_LEFT_QUOTIENT_LIMIT
@lateral_abs_ready:
    ld de,W3D_ACTOR_VIEW_SCALE
    push bc                           ; preserve screen-edge quotient limit
    call w3d_umul16x16_32
    pop bc
    ld a,e
    ld (w3d_actor_projection_left_product+0),a
    ld a,d
    ld (w3d_actor_projection_left_product+1),a
    ld a,l
    ld (w3d_actor_projection_left_product+2),a
    ld a,h
    ld (w3d_actor_projection_left_product+3),a

    ld hl,0
    ld a,(w3d_actor_projection_nx+0)
    ld l,a
    ld a,(w3d_actor_projection_nx+1)
    ld h,a
    ld d,0
    ld e,c
    call w3d_umul16x16_32
    ld b,h
    ld a,(w3d_actor_projection_left_product+3)
    ld c,a
    ld a,b
    cp c
    jr c,@not_visible
    jr nz,@visible
    ld b,l
    ld a,(w3d_actor_projection_left_product+2)
    ld c,a
    ld a,b
    cp c
    jr c,@not_visible
    jr nz,@visible
    ld b,d
    ld a,(w3d_actor_projection_left_product+1)
    ld c,a
    ld a,b
    cp c
    jr c,@not_visible
    jr nz,@visible
    ld b,e
    ld a,(w3d_actor_projection_left_product+0)
    ld c,a
    ld a,b
    cp c
    jr c,@not_visible
    jr z,@not_visible                  ; strict left product < right product
@visible:
    ld a,1
    ret
@not_visible:
    xor a
    ret

; Store signed (actor-player)>>8 for X/Y. Bytewise subtraction preserves the
; carry across the discarded fractional byte without ever reading HLU.
w3d_actor_load_relative_q8:
    ld a,(w3d_player_pose+0)
    ld b,a
    ld a,(ix+W3D_ACTOR_X+0)
    sub b
    ld a,(w3d_player_pose+1)
    ld b,a
    ld a,(ix+W3D_ACTOR_X+1)
    sbc a,b
    ld (w3d_actor_projection_rel_x+0),a
    ld a,(w3d_player_pose+2)
    ld b,a
    ld a,(ix+W3D_ACTOR_X+2)
    sbc a,b
    ld (w3d_actor_projection_rel_x+1),a

    ld a,(w3d_player_pose+4)
    ld b,a
    ld a,(ix+W3D_ACTOR_Y+0)
    sub b
    ld a,(w3d_player_pose+5)
    ld b,a
    ld a,(ix+W3D_ACTOR_Y+1)
    sbc a,b
    ld (w3d_actor_projection_rel_y+0),a
    ld a,(w3d_player_pose+6)
    ld b,a
    ld a,(ix+W3D_ACTOR_Y+2)
    sbc a,b
    ld (w3d_actor_projection_rel_y+1),a
    ret

; Load current 0..359 heading's signed Q12 forward vector from the same table
; used by player movement. The table's Y value already carries map-Y-down's
; `-sin` sign.
w3d_actor_load_heading_q12:
    ld hl,0
    ld a,(w3d_player_pose+8)
    ld l,a
    ld a,(w3d_player_pose+9)
    ld h,a
    ld de,0
    ld e,l
    ld d,h
    add hl,hl
    add hl,de
    add hl,hl
    ld de,w3d_motion_delta_table
    add hl,de
    ld a,(hl)
    ld (w3d_actor_projection_cos+0),a
    inc hl
    ld a,(hl)
    ld (w3d_actor_projection_cos+1),a
    inc hl
    inc hl
    ld a,(hl)
    ld (w3d_actor_projection_forward_y+0),a
    inc hl
    ld a,(hl)
    ld (w3d_actor_projection_forward_y+1),a
    ret

; Signed Q8 value HL times signed Q12 DE -> signed Q8 HL. WL_DRAW.C's
; FixedByFrac multiplies magnitudes and applies the sign afterward, so negative
; products truncate toward zero rather than floor. Bias a negative product by
; 0xfff before the arithmetic twelve-bit extraction to preserve that detail.
; Only low 16-bit GP bytes are significant throughout this contract.
w3d_actor_mul_q8_q12:
    call w3d_smul16x16_32
    bit 7,h
    jr z,@extract
    ld a,d
    and 00fh
    ld b,a
    ld a,e
    or b
    jr z,@extract                     ; exact multiple needs no bias
    ld a,e
    add a,0ffh
    ld e,a
    ld a,d
    adc a,00fh
    ld d,a
    ld a,l
    adc a,0
    ld l,a
    ld a,h
    adc a,0
    ld h,a
@extract:
    ld a,d
    srl a
    srl a
    srl a
    srl a
    ld b,a
    ld a,l
    and 00fh
    rlca
    rlca
    rlca
    rlca
    or b
    ld c,a
    ld a,l
    and 0f0h
    rrca
    rrca
    rrca
    rrca
    ld b,a
    ld a,h
    and 00fh
    rlca
    rlca
    rlca
    rlca
    or b
    ld h,a
    ld l,c
    ret

; Resolve IX's uint16 state id. Carry marks zero, high-byte, or range faults.
w3d_actor_resolve_current_state:
    ld a,(ix+W3D_ACTOR_STATE+1)
    or a
    jr nz,@invalid
    ld a,(ix+W3D_ACTOR_STATE+0)
    or a
    jr z,@invalid
    cp W3D_STATE_COUNT
    jr nc,@invalid
    call w3d_actor_state_pointer_from_id
    or a
    ret
@invalid:
    scf
    ret

; Capture the complete effective VDP signature: shape (including the original
; shape=-1/temp1 override), rotations, full x/y, and resolved facing. Comparing
; wire-visible values rather than internal direction/state ids prevents false
; dirtiness such as NODIR angle 0 selecting cardinal EAST.
w3d_actor_capture_render_signature:
    ld a,(iy+W3D_STATE_SHAPENUM+0)
    ld (w3d_actor_old_shape+0),a
    ld b,a
    ld a,(iy+W3D_STATE_SHAPENUM+1)
    ld (w3d_actor_old_shape+1),a
    and b
    inc a
    jr nz,@rotations
    ld a,(ix+W3D_ACTOR_TEMP1+0)
    ld (w3d_actor_old_shape+0),a
    ld a,(ix+W3D_ACTOR_TEMP1+1)
    ld (w3d_actor_old_shape+1),a
@rotations:
    ld a,(iy+W3D_STATE_ROTATIONS)
    ld (w3d_actor_old_rotations),a
    push ix
    pop hl
    ld de,w3d_actor_old_pose
    ld bc,8
    ldir
    ld a,(ix+W3D_ACTOR_DIR)
    cp W3D_DIR_NODIR
    jr nc,@continuous_facing
    add a,a
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_actor_direction_degrees
    add hl,de
    ld a,(hl)
    ld (w3d_actor_old_facing+0),a
    inc hl
    ld a,(hl)
    ld (w3d_actor_old_facing+1),a
    ret
@continuous_facing:
    ld a,(ix+W3D_ACTOR_ANGLE+0)
    ld (w3d_actor_old_facing+0),a
    ld a,(ix+W3D_ACTOR_ANGLE+1)
    ld (w3d_actor_old_facing+1),a
    ret

w3d_actor_compare_render_signature:
    call w3d_actor_resolve_current_state
    jp c,w3d_actor_fault_current
    ld a,(iy+W3D_STATE_SHAPENUM+0)
    ld b,a
    ld a,(iy+W3D_STATE_SHAPENUM+1)
    ld c,a
    and b
    inc a
    jr nz,@compare
    ld b,(ix+W3D_ACTOR_TEMP1+0)
    ld c,(ix+W3D_ACTOR_TEMP1+1)
@compare:
    ld a,(w3d_actor_old_shape+0)
    cp b
    jp nz,w3d_actor_mark_current_dirty
    ld a,(w3d_actor_old_shape+1)
    cp c
    jp nz,w3d_actor_mark_current_dirty
    ld a,(w3d_actor_old_rotations)
    cp (iy+W3D_STATE_ROTATIONS)
    jp nz,w3d_actor_mark_current_dirty

; Compare the complete int32 x/y prefix bytewise. ADL pointer increments are
; safe here; no general-purpose register's inaccessible upper byte is data.
    push ix
    pop hl
    ld de,w3d_actor_old_pose
    ld b,8
@pose_loop:
    ld a,(de)
    cp (hl)
    jp nz,w3d_actor_mark_current_dirty
    inc de
    inc hl
    djnz @pose_loop

; Resolve current facing with the same cardinal table used by the sender.
    ld a,(ix+W3D_ACTOR_DIR)
    cp W3D_DIR_NODIR
    jr nc,@continuous_facing
    add a,a
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_actor_direction_degrees
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    jr @facing_ready
@continuous_facing:
    ld e,(ix+W3D_ACTOR_ANGLE+0)
    ld d,(ix+W3D_ACTOR_ANGLE+1)
@facing_ready:
    ld a,(w3d_actor_old_facing+0)
    cp e
    jp nz,w3d_actor_mark_current_dirty
    ld a,(w3d_actor_old_facing+1)
    cp d
    jp nz,w3d_actor_mark_current_dirty
    ret

w3d_actor_mark_current_dirty:
    ld a,(w3d_current_actor_index)
    jp w3d_actor_mark_dirty

; ---------------------------------------------------------------------------
; SightPlayer / FirstSighting (ordinary-enemy awareness)
; ---------------------------------------------------------------------------

; IX=current non-chasing actor. Return A=1 only on the fixed step that enters
; combat, A=0 while unaware/delaying, or 0xff for a corrupt state/class pairing.
; A pending temp2 is consumed before any area or sight revalidation. Initial
; acquisition seeds the delay and returns zero without spending this frame's
; tics, so a path actor continues its current patrol step exactly once.
w3d_actor_sight_player:
    ld a,(w3d_awareness_enabled)
    or a
    jp z,@unaware
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_ATTACKMODE
    jp nz,@invalid

    ld hl,0
    ld l,(ix+W3D_ACTOR_TEMP2+0)
    ld h,(ix+W3D_ACTOR_TEMP2+1)
    ld a,h
    or l
    jr z,@acquire

    ld de,0
    ld a,(w3d_actor_frame_tics)
    ld e,a
    or a
    sbc.s hl,de
    bit 7,h
    jr nz,@react
    ld a,h
    or l
    jr z,@react
    ld (ix+W3D_ACTOR_TEMP2+0),l
    ld (ix+W3D_ACTOR_TEMP2+1),h
    xor a
    ret

@react:
    xor a
    ld (ix+W3D_ACTOR_TEMP2+0),a
    ld (ix+W3D_ACTOR_TEMP2+1),a
    jp w3d_actor_first_sighting

@acquire:
; Area validation precedes both noise and visual acquisition.  A pending
; reaction above intentionally bypasses this gate, matching SightPlayer.
    ld a,(ix+W3D_ACTOR_AREA)
    cp W3D_NUM_AREAS
    jr nc,@unaware
    ld de,0
    ld e,a
    ld hl,w3d_area_by_player
    add hl,de
    ld a,(hl)
    or a
    jr z,@unaware

    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_AMBUSH
    jr nz,@visual
    ld a,(w3d_player_made_noise)
    or a
    jr nz,@detected                  ; noise bypasses facing and line trace

@visual:
    push iy
    ld iy,w3d_actor_sight_context
    call w3d_CheckSight
    pop iy
    or a
    jr z,@unaware
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_AMBUSH
    jr z,@detected
    ld a,(ix+W3D_ACTOR_FLAGS)
    and 0bfh                         ; clear FL_AMBUSH on acquisition
    ld (ix+W3D_ACTOR_FLAGS),a

@detected:
    call w3d_actor_reaction_delay
    or a
    jr z,@invalid
    ld (ix+W3D_ACTOR_TEMP2+0),a
    xor a
    ld (ix+W3D_ACTOR_TEMP2+1),a
@unaware:
    xor a
    ret
@invalid:
    ld a,0ffh
    ret

; Return the original class-specific reaction delay in A. Zero means that a
; path/stand state was paired with an unsupported class and must fail closed.
w3d_actor_reaction_delay:
    ld a,(ix+W3D_ACTOR_CLASS)
    cp W3D_CLASS_GUARD
    jr z,@guard
    cp W3D_CLASS_OFFICER
    jr z,@officer
    cp W3D_CLASS_MUTANT
    jr z,@sixth
    cp W3D_CLASS_SS
    jr z,@sixth
    cp W3D_CLASS_DOG
    jr z,@dog
    xor a
    ret
@guard:
    call w3d_random_byte
    srl a
    srl a
    inc a
    ret
@officer:
    ld a,2                          ; officer consumes no random byte
    ret
@sixth:
    call w3d_random_byte
    call w3d_actor_u8_div6
    inc a
    ret
@dog:
    call w3d_random_byte
    srl a
    srl a
    srl a
    inc a
    ret

; Rare cold-path division used once per mutant/SS acquisition. Input A is
; uint8; output A=floor(input/6). The bounded 42-subtraction worst case is
; preferable to carrying a second 256-byte quotient table.
w3d_actor_u8_div6:
    ld b,0
@loop:
    cp 6
    jr c,@done
    sub 6
    inc b
    jr @loop
@done:
    ld a,b
    ret

; Exact US_RndT table/index convention: increment the uint8 index first, then
; return the corresponding table byte. Initialization resumes after the build-
; time SpawnNewObj calls already embodied in the generated actor ticcounts.
w3d_random_byte:
    ld a,(w3d_random_index)
    inc a
    ld (w3d_random_index),a
    ld de,0
    ld e,a
    ld hl,w3d_random_table
    add hl,de
    ld a,(hl)
    ret

; Apply ordinary FirstSighting without chase movement or sound dispatch.
; Active is intentionally unchanged: the original renderer promoted visible
; actors, while this write-only VDP cannot feed visibility back to the eZ80.
; Existing ACTIVE_NO actors therefore retain the settled area scheduler rule.
w3d_actor_first_sighting:
    ld a,(ix+W3D_ACTOR_CLASS)
    cp W3D_CLASS_GUARD
    jr z,@guard
    cp W3D_CLASS_OFFICER
    jr z,@officer
    cp W3D_CLASS_MUTANT
    jr z,@mutant
    cp W3D_CLASS_SS
    jr z,@ss
    cp W3D_CLASS_DOG
    jr z,@dog
    ld a,0ffh
    ret
@guard:
    ld b,W3D_STATE_GRD_CHASE1
    ld c,3
    jr @apply
@officer:
    ld b,W3D_STATE_OFC_CHASE1
    ld c,5
    jr @apply
@mutant:
    ld b,W3D_STATE_MUT_CHASE1
    ld c,3
    jr @apply
@ss:
    ld b,W3D_STATE_SS_CHASE1
    ld c,4
    jr @apply
@dog:
    ld b,W3D_STATE_DOG_CHASE1
    ld c,2

@apply:
    ld a,b
    ld (ix+W3D_ACTOR_STATE+0),a
    xor a
    ld (ix+W3D_ACTOR_STATE+1),a
    ld a,b
    call w3d_actor_state_pointer_from_id
    ld a,(iy+W3D_STATE_TICTIME+0)
    ld (ix+W3D_ACTOR_TICCOUNT+0),a
    ld a,(iy+W3D_STATE_TICTIME+1)
    ld (ix+W3D_ACTOR_TICCOUNT+1),a

; All ordinary patrol speeds are unsigned 16-bit quantities even though the
; durable field is int32.  Keep the wider bytes intentionally zero and avoid
; using inaccessible HLU/DEU as data.
    ld hl,0
    ld l,(ix+W3D_ACTOR_SPEED+0)
    ld h,(ix+W3D_ACTOR_SPEED+1)
    push hl
    pop de
    ld a,c
    dec a
@multiply:
    jr z,@speed_ready
    add.s hl,de
    dec a
    jr @multiply
@speed_ready:
    ld (ix+W3D_ACTOR_SPEED+0),l
    ld (ix+W3D_ACTOR_SPEED+1),h
    xor a
    ld (ix+W3D_ACTOR_SPEED+2),a
    ld (ix+W3D_ACTOR_SPEED+3),a

    bit 7,(ix+W3D_ACTOR_DISTANCE+3)
    jr z,@distance_ready
    ld (ix+W3D_ACTOR_DISTANCE+0),a
    ld (ix+W3D_ACTOR_DISTANCE+1),a
    ld (ix+W3D_ACTOR_DISTANCE+2),a
    ld (ix+W3D_ACTOR_DISTANCE+3),a
@distance_ready:
    ld a,(ix+W3D_ACTOR_FLAGS)
    or W3D_ACTOR_FLAG_ATTACKMODE|W3D_ACTOR_FLAG_FIRSTATTACK
    ld (ix+W3D_ACTOR_FLAGS),a
    ld a,1
    ret

w3d_actor_remove_current:
    ld a,(w3d_current_actor_index)
    call w3d_actor_free
    scf
    ret

w3d_actor_fault_current:
    ld hl,w3d_actor_fault_count
    inc (hl)
    jr nz,@remove
    inc hl
    inc (hl)
@remove:
    jp w3d_actor_remove_current

; ---------------------------------------------------------------------------
; Ordinary chase movement and explicit attack-request seams
; ---------------------------------------------------------------------------

; IX=current guard/officer/mutant/SS actor. Preserve the complete original
; one-think ordering through the shooting-state decision. Return NONE after
; movement/blocking, RANGED when the original strict random attack roll
; succeeds, or CORRUPT for a bad class/dir; the runner maps RANGED to NewState.
w3d_actor_think_chase:
    ld a,(ix+W3D_ACTOR_CLASS)
    cp W3D_CLASS_GUARD
    jr z,@class_ok
    cp W3D_CLASS_OFFICER
    jr z,@class_ok
    cp W3D_CLASS_MUTANT
    jr z,@class_ok
    cp W3D_CLASS_SS
    jp nz,@corrupt
@class_ok:
    ld a,(ix+W3D_ACTOR_DIR)
    cp W3D_DIR_NODIR+1
    jp nc,@corrupt

    call w3d_actor_probe_ranged_attack
    cp W3D_CHASE_RESULT_RANGED
    ret z

    ld a,(ix+W3D_ACTOR_DIR)
    cp W3D_DIR_NODIR
    jr nz,@have_direction
    call w3d_actor_select_chase_mode
    cp W3D_CHASE_RESULT_CORRUPT
    ret z
    or a
    jr z,@none
@have_direction:
    call w3d_actor_set_move_budget

@movement_loop:
    ld hl,(w3d_actor_move_remaining)
    ld a,h
    or l
    jr z,@none

    bit 7,(ix+W3D_ACTOR_DISTANCE+3)
    jr z,@positive_distance
; Legal -(door+1) waits for the <=64-door fixture are sign-extended from the
; low byte. Reject noncanonical 32-bit negatives before complementing it.
    ld a,(ix+W3D_ACTOR_DISTANCE+1)
    cp 0ffh
    jr nz,@bad_wait
    ld a,(ix+W3D_ACTOR_DISTANCE+2)
    cp 0ffh
    jr nz,@bad_wait
    ld a,(ix+W3D_ACTOR_DISTANCE+3)
    cp 0ffh
    jr nz,@bad_wait
    ld a,(ix+W3D_ACTOR_DISTANCE+0)
    cpl                               ; -distance-1 -> door index
    cp W3D_FIXTURE_DOOR_COUNT
    jr nc,@bad_wait
    call w3d_request_open_door
    cp W3D_DOOR_ACTION_OPEN
    jr nz,@none
    call w3d_actor_set_tile_distance
    jr @movement_loop
@bad_wait:
    jp @corrupt

@positive_distance:
    ld de,(ix+W3D_ACTOR_DISTANCE)
    or a
    sbc hl,de                         ; remaining - distance
    jr nc,@reach_center
    ld hl,(w3d_actor_move_remaining)
    ld (w3d_actor_move_amount),hl
    call w3d_actor_move_obj
    ld hl,0
    ld (w3d_actor_move_remaining),hl
    jr @none

@reach_center:
    ld (w3d_actor_move_remaining),hl
    call w3d_actor_snap_to_cached_center
    call w3d_actor_select_chase_mode
    cp W3D_CHASE_RESULT_CORRUPT
    ret z
    or a
    jr z,@none
    jr @movement_loop

@none:
    ld a,W3D_CHASE_RESULT_NONE
    ret
@corrupt:
    ld a,W3D_CHASE_RESULT_CORRUPT
    ret

; IX=current dog. T_DogChase requests s_dogjump1 before movement when the
; complete remaining budget can enter the inclusive one-tile square. The
; runner installs the jump chain; its jump2 end action performs T_Bite.
w3d_actor_think_dog_chase:
    ld a,(ix+W3D_ACTOR_CLASS)
    cp W3D_CLASS_DOG
    jr nz,@corrupt
    ld a,(ix+W3D_ACTOR_DIR)
    cp W3D_DIR_NODIR+1
    jr nc,@corrupt
    cp W3D_DIR_NODIR
    jr nz,@have_direction
    call w3d_actor_select_dodge_dir
    cp W3D_CHASE_RESULT_CORRUPT
    ret z
    or a
    jr z,@none
@have_direction:
    call w3d_actor_set_move_budget

@movement_loop:
    ld hl,(w3d_actor_move_remaining)
    ld a,h
    or l
    jr z,@none

; A dog can never obtain a door wait through TryWalk. A malformed injected
; wait fails closed instead of reaching either the jump seam or movement.
    bit 7,(ix+W3D_ACTOR_DISTANCE+3)
    jr nz,@bad_wait
    call w3d_actor_dog_jump_in_range
    or a
    jr nz,@jump

    ld hl,(w3d_actor_move_remaining)
    ld de,(ix+W3D_ACTOR_DISTANCE)
    or a
    sbc hl,de
    jr nc,@reach_center
    ld hl,(w3d_actor_move_remaining)
    ld (w3d_actor_move_amount),hl
    call w3d_actor_move_obj
    ld hl,0
    ld (w3d_actor_move_remaining),hl
    jr @none

@reach_center:
    ld (w3d_actor_move_remaining),hl
    call w3d_actor_snap_to_cached_center
    call w3d_actor_select_dodge_dir
    cp W3D_CHASE_RESULT_CORRUPT
    ret z
    or a
    jr z,@none
    jr @movement_loop
@bad_wait:
    jp @corrupt
@none:
    ld a,W3D_CHASE_RESULT_NONE
    ret
@jump:
    ld a,W3D_CHASE_RESULT_DOG_JUMP
    ret
@corrupt:
    ld a,W3D_CHASE_RESULT_CORRUPT
    ret

; CheckLine and the original attack chance precede all direction/door/motion
; work. A successful roll is exposed without actor mutation so the independently
; tested runner seam can install the correct class-specific shooting state.
w3d_actor_probe_ranged_attack:
    xor a
    ld (w3d_actor_chase_dodge),a
    push iy
    ld iy,w3d_actor_sight_context
    call w3d_CheckLine
    pop iy
    or a
    ret z                             ; blocked line: no attack RNG draw

    call w3d_actor_tile_deltas_abs
    ld a,(w3d_actor_chase_abs_x)
    ld b,a
    ld a,(w3d_actor_chase_abs_y)
    cp b
    jr c,@x_is_max
    ld b,a
@x_is_max:
    ld a,b
    or a
    jr z,@always
    cp 1
    jr nz,@scaled
    call w3d_actor_distance_lt_quarter
    or a
    jr nz,@always

@scaled:
    ld a,(w3d_actor_frame_tics)
    add a,a
    add a,a
    add a,a
    add a,a                          ; tics << 4
    call w3d_actor_u8_div_b
    ld b,a
    call w3d_random_byte
    cp b                              ; strict US_RndT() < chance
    jr c,@requested
    ld a,1
    ld (w3d_actor_chase_dodge),a
    ld a,W3D_CHASE_RESULT_NONE
    ret
@always:
    call w3d_random_byte             ; chance=300 still consumes one byte
@requested:
    ld a,W3D_CHASE_RESULT_RANGED
    ret

; Signed actor distance < 0x00004000. Negative waits are therefore true,
; matching the C comparison, although FirstSighting normally clears one.
w3d_actor_distance_lt_quarter:
    bit 7,(ix+W3D_ACTOR_DISTANCE+3)
    jr nz,@true
    ld a,(ix+W3D_ACTOR_DISTANCE+3)
    or a
    jr nz,@false
    ld a,(ix+W3D_ACTOR_DISTANCE+2)
    or a
    jr nz,@false
    ld hl,0
    ld l,(ix+W3D_ACTOR_DISTANCE+0)
    ld h,(ix+W3D_ACTOR_DISTANCE+1)
    ld de,04000h
    or a
    sbc.s hl,de
    jr c,@true
@false:
    xor a
    ret
@true:
    ld a,1
    ret

; Input A=uint8 numerator, B=nonzero uint8 divisor; output floor(A/B) in A.
w3d_actor_u8_div_b:
    ld c,0
@loop:
    cp b
    jr c,@done
    sub b
    inc c
    jr @loop
@done:
    ld a,c
    ret

; Original speed*tics motion budget. Valid ordinary chase speeds keep the
; product below 64 KiB, while distance/coordinates continue to use 24 bits.
w3d_actor_set_move_budget:
    ld hl,(ix+W3D_ACTOR_SPEED)
    ld de,(ix+W3D_ACTOR_SPEED)
    add hl,de
    ld a,(w3d_actor_frame_tics)
    cp 3
    jr nz,@ready
    add hl,de
@ready:
    ld (w3d_actor_move_remaining),hl
    ret

; Dispatch the selector fixed for this complete T_Chase call.
w3d_actor_select_chase_mode:
    ld a,(w3d_actor_chase_dodge)
    or a
    jp nz,w3d_actor_select_dodge_dir
    jp w3d_actor_select_chase_dir

; SelectDodgeDir. Returns 1 after a successful TryWalk, 0 when trapped, or FF
; for an invalid incoming direction. It always consumes exactly one RNG byte.
w3d_actor_select_dodge_dir:
    ld a,(ix+W3D_ACTOR_DIR)
    cp W3D_DIR_NODIR+1
    jp nc,@corrupt
    ld (w3d_actor_chase_old_dir),a
    ld b,a
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_FIRSTATTACK
    jr z,@ordinary_turnaround
    ld a,(ix+W3D_ACTOR_FLAGS)
    and 0dfh                         ; clear FIRSTATTACK before all attempts
    ld (ix+W3D_ACTOR_FLAGS),a
    ld a,W3D_DIR_NODIR
    jr @turnaround_ready
@ordinary_turnaround:
    ld a,b
    call w3d_actor_opposite_direction
@turnaround_ready:
    ld (w3d_actor_chase_turnaround),a

; Zero deltas deliberately retain the source's west/north bias.
    ld a,(w3d_player_pose+2)
    ld b,(ix+W3D_ACTOR_TILEX)
    cp b
    jr z,@x_nonpositive
    jr c,@x_nonpositive
    ld a,W3D_DIR_EAST
    ld (w3d_actor_chase_dirs+1),a
    ld a,W3D_DIR_WEST
    ld (w3d_actor_chase_dirs+3),a
    jr @x_ready
@x_nonpositive:
    ld a,W3D_DIR_WEST
    ld (w3d_actor_chase_dirs+1),a
    ld a,W3D_DIR_EAST
    ld (w3d_actor_chase_dirs+3),a
@x_ready:
    ld a,(w3d_player_pose+6)
    ld b,(ix+W3D_ACTOR_TILEY)
    cp b
    jr z,@y_nonpositive
    jr c,@y_nonpositive
    ld a,W3D_DIR_SOUTH
    ld (w3d_actor_chase_dirs+2),a
    ld a,W3D_DIR_NORTH
    ld (w3d_actor_chase_dirs+4),a
    jr @preferences
@y_nonpositive:
    ld a,W3D_DIR_NORTH
    ld (w3d_actor_chase_dirs+2),a
    ld a,W3D_DIR_SOUTH
    ld (w3d_actor_chase_dirs+4),a

@preferences:
    call w3d_actor_tile_deltas_abs
    ld a,(w3d_actor_chase_abs_y)
    ld b,a
    ld a,(w3d_actor_chase_abs_x)
    cp b
    jr c,@randomize
    jr z,@randomize
    call w3d_actor_swap_dodge_pairs  ; absdx > absdy
@randomize:
    call w3d_random_byte
    cp 128
    jr nc,@diagonal
    call w3d_actor_swap_dodge_pairs
@diagonal:
    ld a,(w3d_actor_chase_dirs+1)
    ld b,a
    ld a,(w3d_actor_chase_dirs+2)
    ld c,a
    call w3d_actor_diagonal_direction
    ld (w3d_actor_chase_dirs+0),a

    xor a
    ld (w3d_actor_chase_try_index),a
@try_loop:
    ld a,(w3d_actor_chase_try_index)
    cp 5
    jr nc,@turnaround
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_actor_chase_dirs
    add hl,de
    ld a,(hl)
    call w3d_actor_try_except_turnaround
    or a
    ret nz
    ld a,(w3d_actor_chase_try_index)
    inc a
    ld (w3d_actor_chase_try_index),a
    jr @try_loop
@turnaround:
    ld a,(w3d_actor_chase_turnaround)
    call w3d_actor_try_direction
    or a
    ret nz
    ld a,W3D_DIR_NODIR
    ld (ix+W3D_ACTOR_DIR),a
    ld a,W3D_CHASE_RESULT_NONE
    ret
@corrupt:
    ld a,W3D_CHASE_RESULT_CORRUPT
    ret

; SelectChaseDir, including the original enum-order fallback quirk: the search
; is N,NW,W or W,NW,N, not a normalized four-cardinal sweep.
w3d_actor_select_chase_dir:
    ld a,(ix+W3D_ACTOR_DIR)
    cp W3D_DIR_NODIR+1
    jp nc,@corrupt
    ld (w3d_actor_chase_old_dir),a
    call w3d_actor_opposite_direction
    ld (w3d_actor_chase_turnaround),a
    ld a,W3D_DIR_NODIR
    ld (w3d_actor_chase_dirs+1),a
    ld (w3d_actor_chase_dirs+2),a

    ld a,(w3d_player_pose+2)
    ld b,(ix+W3D_ACTOR_TILEX)
    cp b
    jr z,@x_done
    jr c,@x_west
    ld a,W3D_DIR_EAST
    jr @x_store
@x_west:
    ld a,W3D_DIR_WEST
@x_store:
    ld (w3d_actor_chase_dirs+1),a
@x_done:
    ld a,(w3d_player_pose+6)
    ld b,(ix+W3D_ACTOR_TILEY)
    cp b
    jr z,@order
    jr c,@y_north
    ld a,W3D_DIR_SOUTH
    jr @y_store
@y_north:
    ld a,W3D_DIR_NORTH
@y_store:
    ld (w3d_actor_chase_dirs+2),a

@order:
    call w3d_actor_tile_deltas_abs
    ld a,(w3d_actor_chase_abs_x)
    ld b,a
    ld a,(w3d_actor_chase_abs_y)
    cp b
    jr c,@suppress_turnaround
    jr z,@suppress_turnaround
    ld a,(w3d_actor_chase_dirs+1)
    ld b,a
    ld a,(w3d_actor_chase_dirs+2)
    ld (w3d_actor_chase_dirs+1),a
    ld a,b
    ld (w3d_actor_chase_dirs+2),a

@suppress_turnaround:
    ld a,(w3d_actor_chase_turnaround)
    ld b,a
    ld a,(w3d_actor_chase_dirs+1)
    cp b
    jr nz,@second
    ld a,W3D_DIR_NODIR
    ld (w3d_actor_chase_dirs+1),a
@second:
    ld a,(w3d_actor_chase_dirs+2)
    cp b
    jr nz,@try_direct
    ld a,W3D_DIR_NODIR
    ld (w3d_actor_chase_dirs+2),a

@try_direct:
    ld a,(w3d_actor_chase_dirs+1)
    call w3d_actor_try_direction
    or a
    ret nz
    ld a,(w3d_actor_chase_dirs+2)
    call w3d_actor_try_direction
    or a
    ret nz
    ld a,(w3d_actor_chase_old_dir)
    call w3d_actor_try_direction
    or a
    ret nz

    call w3d_random_byte
    cp 129                            ; >128 chooses ascending source loop
    jr nc,@ascending
    ld a,W3D_DIR_WEST
    call w3d_actor_try_except_turnaround
    or a
    ret nz
    ld a,W3D_DIR_NORTHWEST
    call w3d_actor_try_except_turnaround
    or a
    ret nz
    ld a,W3D_DIR_NORTH
    call w3d_actor_try_except_turnaround
    or a
    ret nz
    jr @turnaround
@ascending:
    ld a,W3D_DIR_NORTH
    call w3d_actor_try_except_turnaround
    or a
    ret nz
    ld a,W3D_DIR_NORTHWEST
    call w3d_actor_try_except_turnaround
    or a
    ret nz
    ld a,W3D_DIR_WEST
    call w3d_actor_try_except_turnaround
    or a
    ret nz
@turnaround:
    ld a,(w3d_actor_chase_turnaround)
    call w3d_actor_try_direction
    or a
    ret nz
    ld a,W3D_DIR_NODIR
    ld (ix+W3D_ACTOR_DIR),a
    ld a,W3D_CHASE_RESULT_NONE
    ret
@corrupt:
    ld a,W3D_CHASE_RESULT_CORRUPT
    ret

; A=candidate. TryWalk is transactional on failure. The enclosing scheduler
; has released the current actor's cached reservation before selector entry.
w3d_actor_try_direction:
    cp W3D_DIR_NODIR
    jr z,@blocked
    cp W3D_DIR_NODIR+1
    jr nc,@blocked
    ld (ix+W3D_ACTOR_DIR),a
    jp w3d_actor_try_walk
@blocked:
    xor a
    ret

w3d_actor_try_except_turnaround:
    cp W3D_DIR_NODIR
    jr z,@blocked
    ld b,a
    ld a,(w3d_actor_chase_turnaround)
    cp b
    jr z,@blocked
    ld a,b
    jp w3d_actor_try_direction
@blocked:
    xor a
    ret

w3d_actor_opposite_direction:
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_actor_opposite_dirs
    add hl,de
    ld a,(hl)
    ret

; B/C are the two cardinal toward directions in either axis order.
w3d_actor_diagonal_direction:
    ld d,b
    ld e,9
    mlt de
    ld a,e
    add a,c
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_actor_diagonal_dirs
    add hl,de
    ld a,(hl)
    ret

w3d_actor_swap_dodge_pairs:
    ld a,(w3d_actor_chase_dirs+1)
    ld b,a
    ld a,(w3d_actor_chase_dirs+2)
    ld (w3d_actor_chase_dirs+1),a
    ld a,b
    ld (w3d_actor_chase_dirs+2),a
    ld a,(w3d_actor_chase_dirs+3)
    ld b,a
    ld a,(w3d_actor_chase_dirs+4)
    ld (w3d_actor_chase_dirs+3),a
    ld a,b
    ld (w3d_actor_chase_dirs+4),a
    ret

; Cache absolute player-tile deltas from the actor's reserved destination.
w3d_actor_tile_deltas_abs:
    ld a,(w3d_player_pose+2)
    sub (ix+W3D_ACTOR_TILEX)
    jr nc,@x_ready
    neg
@x_ready:
    ld (w3d_actor_chase_abs_x),a
    ld a,(w3d_player_pose+6)
    sub (ix+W3D_ACTOR_TILEY)
    jr nc,@y_ready
    neg
@y_ready:
    ld (w3d_actor_chase_abs_y),a
    ret

; Return A=1 when the dog's current remaining movement budget projects both
; absolute coordinate deltas to <= MINACTORDIST, including exact contact.
w3d_actor_dog_jump_in_range:
    ld hl,(w3d_actor_move_remaining)
    ld de,W3D_MIN_ACTOR_DISTANCE
    add hl,de
    ld (w3d_actor_dog_jump_threshold),hl

    ld hl,(w3d_player_pose+0)
    ld de,(ix+W3D_ACTOR_X)
    or a
    sbc hl,de
    jr nc,@x_abs
    ld hl,(ix+W3D_ACTOR_X)
    ld de,(w3d_player_pose+0)
    or a
    sbc hl,de
@x_abs:
    ld de,(w3d_actor_dog_jump_threshold)
    or a
    sbc hl,de
    jr c,@check_y
    jr nz,@far
@check_y:
    ld hl,(w3d_player_pose+4)
    ld de,(ix+W3D_ACTOR_Y)
    or a
    sbc hl,de
    jr nc,@y_abs
    ld hl,(ix+W3D_ACTOR_Y)
    ld de,(w3d_player_pose+4)
    or a
    sbc hl,de
@y_abs:
    ld de,(w3d_actor_dog_jump_threshold)
    or a
    sbc hl,de
    jr c,@near
    jr nz,@far
@near:
    ld a,1
    ret
@far:
    xor a
    ret

; ---------------------------------------------------------------------------
; T_Path / SelectPathDir / TryWalk
; ---------------------------------------------------------------------------

; IX=current actor. Movement budget is speed times this frame's original tic
; count. Door waits consume the whole budget, exactly like the C routine.
w3d_actor_think_path:
    call w3d_actor_sight_player
    cp 0ffh
    ret z
    or a
    ret nz
    ld a,(ix+W3D_ACTOR_DIR)
    cp W3D_DIR_NODIR
    jr c,@have_direction
    call w3d_actor_select_path_dir
    or a
    ret z
@have_direction:
    ld hl,(ix+W3D_ACTOR_SPEED)
    ld de,(ix+W3D_ACTOR_SPEED)
    add hl,de                         ; speed * 2
    ld a,(w3d_actor_frame_tics)
    cp 3
    jr nz,@budget_ready
    add hl,de                         ; speed * 3
@budget_ready:
    ld (w3d_actor_move_remaining),hl

@movement_loop:
    ld hl,(w3d_actor_move_remaining)
    ld a,h
    or l
    ret z

    bit 7,(ix+W3D_ACTOR_DISTANCE+3)
    jr z,@positive_distance
; Decode only a canonical sign-extended -(door+1), never a low-byte alias.
    ld a,(ix+W3D_ACTOR_DISTANCE+1)
    cp 0ffh
    jr nz,@bad_wait
    ld a,(ix+W3D_ACTOR_DISTANCE+2)
    cp 0ffh
    jr nz,@bad_wait
    ld a,(ix+W3D_ACTOR_DISTANCE+3)
    cp 0ffh
    jr nz,@bad_wait
    ld a,(ix+W3D_ACTOR_DISTANCE+0)
    cpl                               ; -distance-1 -> door index
    cp W3D_FIXTURE_DOOR_COUNT
    jr nc,@bad_wait
    call w3d_request_open_door
    cp W3D_DOOR_ACTION_OPEN
    ret nz
    call w3d_actor_set_tile_distance
    jr @movement_loop
@bad_wait:
    ld a,W3D_DIR_NODIR
    ld (ix+W3D_ACTOR_DIR),a
    ret

@positive_distance:
    ld de,(ix+W3D_ACTOR_DISTANCE)
    or a
    sbc hl,de                         ; remaining - distance
    jr nc,@reach_center

; Budget is strictly less than the remaining leg. MoveObj consumes it once.
    ld hl,(w3d_actor_move_remaining)
    ld (w3d_actor_move_amount),hl
    call w3d_actor_move_obj
    ld hl,0
    ld (w3d_actor_move_remaining),hl
    ret

@reach_center:
    ld (w3d_actor_move_remaining),hl
    call w3d_actor_snap_to_cached_center
    call w3d_actor_select_path_dir
    or a
    ret z
    jr @movement_loop

; Read an arrow at the current cached tile, retain direction on no-arrow,
; then reserve/prepare the next leg with TryWalk. A facing change is render
; dirtiness even if the new direction is immediately blocked.
w3d_actor_select_path_dir:
    ld hl,0
    ld l,(ix+W3D_ACTOR_TILEY)
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    ld de,0
    ld e,(ix+W3D_ACTOR_TILEX)
    add.s hl,de
    ld de,(w3d_path_directions_ptr)
    add hl,de
    ld a,(hl)
    cp 8
    jr nc,@direction_ready
    ld (ix+W3D_ACTOR_DIR),a
@direction_ready:
    call w3d_actor_set_tile_distance
    call w3d_actor_try_walk
    or a
    ret nz
    ld a,W3D_DIR_NODIR
    ld (ix+W3D_ACTOR_DIR),a
    xor a
    ret

w3d_actor_set_tile_distance:
    xor a
    ld (ix+W3D_ACTOR_DISTANCE+0),a
    ld (ix+W3D_ACTOR_DISTANCE+1),a
    inc a
    ld (ix+W3D_ACTOR_DISTANCE+2),a
    xor a
    ld (ix+W3D_ACTOR_DISTANCE+3),a
    ret

; Validate the directional destination with original CHECKSIDE/CHECKDIAG
; semantics. Cardinal dogs/fake actors and every diagonal treat a non-open
; door as solid; ordinary cardinal walkers may request and wait on that door.
w3d_actor_try_walk:
    ld a,W3D_SLOT_NONE
    ld (w3d_actor_pending_door),a
    ld a,(ix+W3D_ACTOR_DIR)
    cp 8
    jp nc,@blocked
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_actor_direction_dx
    add hl,de
    ld a,(hl)
    add a,(ix+W3D_ACTOR_TILEX)
    ld (w3d_actor_target_x),a
    ld hl,w3d_actor_direction_dy
    add hl,de
    ld a,(hl)
    add a,(ix+W3D_ACTOR_TILEY)
    ld (w3d_actor_target_y),a

; Inert movement is unchecked in the original. No current patrol is inert,
; but retaining the branch keeps this primitive ready for scripted actors.
    ld a,(ix+W3D_ACTOR_CLASS)
    cp W3D_CLASS_INERT
    jr z,@commit

    ld a,(ix+W3D_ACTOR_DIR)
    bit 0,a
    jr nz,@diagonal
    ld a,(ix+W3D_ACTOR_CLASS)
    cp W3D_CLASS_DOG
    jr z,@cardinal_diag
    cp W3D_CLASS_FAKE
    jr z,@cardinal_diag
    ld a,(w3d_actor_target_x)
    ld b,a
    ld a,(w3d_actor_target_y)
    ld c,a
    call w3d_actor_check_side_cell
    or a
    jp z,@blocked
    jr @commit
@cardinal_diag:
    ld a,(w3d_actor_target_x)
    ld b,a
    ld a,(w3d_actor_target_y)
    ld c,a
    call w3d_actor_check_diag_cell
    or a
    jp z,@blocked
    jr @commit

@diagonal:
; Destination, then the horizontal and vertical orthogonal corner cells.
    ld a,(w3d_actor_target_x)
    ld b,a
    ld a,(w3d_actor_target_y)
    ld c,a
    call w3d_actor_check_diag_cell
    or a
    jp z,@blocked
    ld a,(w3d_actor_target_x)
    ld b,a
    ld c,(ix+W3D_ACTOR_TILEY)
    call w3d_actor_check_diag_cell
    or a
    jp z,@blocked
    ld b,(ix+W3D_ACTOR_TILEX)
    ld a,(w3d_actor_target_y)
    ld c,a
    call w3d_actor_check_diag_cell
    or a
    jp z,@blocked

@commit:
    ld a,(w3d_actor_target_x)
    ld (ix+W3D_ACTOR_TILEX),a
    ld a,(w3d_actor_target_y)
    ld (ix+W3D_ACTOR_TILEY),a
    ld a,(w3d_actor_pending_door)
    cp W3D_SLOT_NONE
    jr z,@ordinary_floor
    push af
    call w3d_request_open_door
    pop af
    cpl                               ; door index -> -(index+1)
    ld (ix+W3D_ACTOR_DISTANCE+0),a
    ld a,0ffh
    ld (ix+W3D_ACTOR_DISTANCE+1),a
    ld (ix+W3D_ACTOR_DISTANCE+2),a
    ld (ix+W3D_ACTOR_DISTANCE+3),a
    ld a,1
    ret
@ordinary_floor:
    call w3d_actor_area_at_cached_tile
    cp W3D_NUM_AREAS
    jr nc,@area_retained
    ld (ix+W3D_ACTOR_AREA),a
@area_retained:
    call w3d_actor_set_tile_distance
    ld a,1
    ret
@blocked:
    xor a
    ret

; CHECKDIAG: walls/statics/non-open doors and shootable actors block. The DOS
; DoorOpening path clears its actorat sentinel at fully OPEN, represented here
; by allowing exactly that action through the otherwise persistent map byte.
w3d_actor_check_diag_cell:
    ld a,b
    cp W3D_MAP_SIZE
    jr nc,@blocked
    ld a,c
    cp W3D_MAP_SIZE
    jr nc,@blocked
    call w3d_map_read
    or a
    jr z,@floor
    cp W3D_TILE_DOOR_MIN
    jr c,@blocked
    cp W3D_TILE_DOOR_MAX+1
    jr nc,@blocked
    and W3D_TILE_DOOR_MASK
    call w3d_actor_door_action_at_bc
    cp W3D_DOOR_ACTION_OPEN
    jr nz,@blocked
@floor:
    push bc
    call w3d_static_tile_blocked
    pop bc
    or a
    jr nz,@blocked
    jp w3d_actor_cell_occupant_clear
@blocked:
    xor a
    ret

; CHECKSIDE: a valid non-open door is traversable only as a pending wait. At
; fully OPEN the DOS actorat sentinel is absent, so it is ordinary floor and
; does not reset the door's hold timer.
w3d_actor_check_side_cell:
    ld a,b
    cp W3D_MAP_SIZE
    jr nc,@blocked
    ld a,c
    cp W3D_MAP_SIZE
    jr nc,@blocked
    call w3d_map_read
    or a
    jr z,@floor
    cp W3D_TILE_DOOR_MIN
    jr c,@blocked
    cp W3D_TILE_DOOR_MAX+1
    jr nc,@blocked
    and W3D_TILE_DOOR_MASK
    call w3d_actor_door_action_at_bc
    cp 0ffh
    jr z,@blocked
    cp W3D_DOOR_ACTION_OPEN
    jr z,@floor
    ld a,(w3d_actor_checked_door)
    ld (w3d_actor_pending_door),a
@floor:
    push bc
    call w3d_static_tile_blocked
    pop bc
    or a
    jr nz,@blocked
    jp w3d_actor_cell_occupant_clear
@blocked:
    xor a
    ret

; A=door index, B/C=map coordinate. Return action or FF for malformed name.
; Actor IX is preserved across the door-record lookup.
w3d_actor_door_action_at_bc:
    cp W3D_FIXTURE_DOOR_COUNT
    jr nc,@invalid
    ld (w3d_actor_checked_door),a
    push ix
    call w3d_door_pointer_from_index
    ld a,(ix+W3D_DOOR_TILEX)
    cp b
    jr nz,@pop_invalid
    ld a,(ix+W3D_DOOR_TILEY)
    cp c
    jr nz,@pop_invalid
    ld a,(ix+W3D_DOOR_ACTION)
    pop ix
    ret
@pop_invalid:
    pop ix
@invalid:
    ld a,0ffh
    ret

; B/C cell occupancy: zero/nonshootable is passable; malformed slots fail
; closed. Restore current IX after inspecting another actor's flags.
w3d_actor_cell_occupant_clear:
    call w3d_actorat_get
    or a
    jr z,@clear
    cp W3D_MAX_ACTORS
    jr nc,@blocked
    push ix
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_ACTIVE)
    cp W3D_ACTOR_ACTIVE_FREE
    jr z,@pop_blocked
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_SHOOTABLE
    ld b,a
    pop ix
    ld a,b
    or a
    jr nz,@blocked
@clear:
    ld a,1
    ret
@pop_blocked:
    pop ix
@blocked:
    xor a
    ret

w3d_actor_area_at_cached_tile:
    ld hl,0
    ld l,(ix+W3D_ACTOR_TILEY)
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    ld de,0
    ld e,(ix+W3D_ACTOR_TILEX)
    add.s hl,de
    ld de,(w3d_area_map_ptr)
    add hl,de
    ld a,(hl)
    ret

; ---------------------------------------------------------------------------
; Physical actor movement
; ---------------------------------------------------------------------------

; Tentatively move by w3d_actor_move_amount in the actor's octant. Reject and
; restore when both center deltas to the player are <= MINACTORDIST. On an
; accepted move subtract the amount from the positive leg distance.
w3d_actor_move_obj:
    ld a,(ix+W3D_ACTOR_DIR)
    cp 8
    jp nc,@blocked
    ld hl,(ix+W3D_ACTOR_X)
    ld (w3d_actor_saved_x),hl
    ld hl,(ix+W3D_ACTOR_Y)
    ld (w3d_actor_saved_y),hl

    ld a,(ix+W3D_ACTOR_DIR)
    cp W3D_DIR_NORTH
    jr z,@north
    cp W3D_DIR_SOUTH
    jr z,@south
    cp W3D_DIR_EAST
    jr z,@east
    cp W3D_DIR_WEST
    jr z,@west
    cp W3D_DIR_NORTHEAST
    jr z,@northeast
    cp W3D_DIR_NORTHWEST
    jr z,@northwest
    cp W3D_DIR_SOUTHEAST
    jr z,@southeast
; southwest
    call w3d_actor_sub_x
    call w3d_actor_add_y
    jr @player_check
@north:
    call w3d_actor_sub_y
    jr @player_check
@south:
    call w3d_actor_add_y
    jr @player_check
@east:
    call w3d_actor_add_x
    jr @player_check
@west:
    call w3d_actor_sub_x
    jr @player_check
@northeast:
    call w3d_actor_add_x
    call w3d_actor_sub_y
    jr @player_check
@northwest:
    call w3d_actor_sub_x
    call w3d_actor_sub_y
    jr @player_check
@southeast:
    call w3d_actor_add_x
    call w3d_actor_add_y

@player_check:
; The original tests player overlap only when this actor's area is connected.
; Invalid areas fail disconnected rather than indexing beyond the 37-byte
; table. This permits legitimate motion on the far side of a closed door.
    ld a,(ix+W3D_ACTOR_AREA)
    cp W3D_NUM_AREAS
    jr nc,@accepted
    ld de,0
    ld e,a
    ld hl,w3d_area_by_player
    add hl,de
    ld a,(hl)
    or a
    jr z,@accepted
    call w3d_actor_clear_of_player
    or a
    jr nz,@accepted
    ld hl,(w3d_actor_saved_x)
    ld (ix+W3D_ACTOR_X),hl
    ld hl,(w3d_actor_saved_y)
    ld (ix+W3D_ACTOR_Y),hl
@blocked:
    xor a
    ret
@accepted:
    ld hl,(ix+W3D_ACTOR_DISTANCE)
    ld de,(w3d_actor_move_amount)
    or a
    sbc hl,de
    ld (ix+W3D_ACTOR_DISTANCE),hl
    ld a,1
    ret

w3d_actor_add_x:
    ld hl,(ix+W3D_ACTOR_X)
    ld de,(w3d_actor_move_amount)
    add hl,de
    ld (ix+W3D_ACTOR_X),hl
    ret
w3d_actor_sub_x:
    ld hl,(ix+W3D_ACTOR_X)
    ld de,(w3d_actor_move_amount)
    or a
    sbc hl,de
    ld (ix+W3D_ACTOR_X),hl
    ret
w3d_actor_add_y:
    ld hl,(ix+W3D_ACTOR_Y)
    ld de,(w3d_actor_move_amount)
    add hl,de
    ld (ix+W3D_ACTOR_Y),hl
    ret
w3d_actor_sub_y:
    ld hl,(ix+W3D_ACTOR_Y)
    ld de,(w3d_actor_move_amount)
    or a
    sbc hl,de
    ld (ix+W3D_ACTOR_Y),hl
    ret

; Return A=1 if either absolute player delta is strictly greater than one
; tile; A=0 when both are within the original inclusive square threshold.
w3d_actor_clear_of_player:
    ld hl,(ix+W3D_ACTOR_X)
    ld de,(w3d_player_pose+0)
    or a
    sbc hl,de
    jr nc,@x_abs
    ld hl,(w3d_player_pose+0)
    ld de,(ix+W3D_ACTOR_X)
    or a
    sbc hl,de
@x_abs:
    ld de,W3D_MIN_ACTOR_DISTANCE+1
    or a
    sbc hl,de
    jr nc,@clear

    ld hl,(ix+W3D_ACTOR_Y)
    ld de,(w3d_player_pose+4)
    or a
    sbc hl,de
    jr nc,@y_abs
    ld hl,(w3d_player_pose+4)
    ld de,(ix+W3D_ACTOR_Y)
    or a
    sbc hl,de
@y_abs:
    ld de,W3D_MIN_ACTOR_DISTANCE+1
    or a
    sbc hl,de
    jr nc,@clear
    xor a
    ret
@clear:
    ld a,1
    ret

w3d_actor_snap_to_cached_center:
    xor a
    ld (ix+W3D_ACTOR_X+0),a
    ld (ix+W3D_ACTOR_Y+0),a
    ld a,080h
    ld (ix+W3D_ACTOR_X+1),a
    ld (ix+W3D_ACTOR_Y+1),a
    ld a,(ix+W3D_ACTOR_TILEX)
    ld (ix+W3D_ACTOR_X+2),a
    ld a,(ix+W3D_ACTOR_TILEY)
    ld (ix+W3D_ACTOR_Y+2),a
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld (ix+W3D_ACTOR_Y+3),a
    ret

w3d_actor_direction_dx:
    db 1,1,0,0ffh,0ffh,0ffh,0,1
w3d_actor_direction_dy:
    db 0,0ffh,0ffh,0ffh,0,1,1,1
w3d_actor_opposite_dirs:
    db W3D_DIR_WEST,W3D_DIR_SOUTHWEST,W3D_DIR_SOUTH,W3D_DIR_SOUTHEAST
    db W3D_DIR_EAST,W3D_DIR_NORTHEAST,W3D_DIR_NORTH,W3D_DIR_NORTHWEST
    db W3D_DIR_NODIR
w3d_actor_diagonal_dirs:
    db 8,8,1,8,8,8,7,8,8
    db 8,8,8,8,8,8,8,8,8
    db 1,8,8,8,3,8,8,8,8
    db 8,8,8,8,8,8,8,8,8
    db 8,8,3,8,8,8,5,8,8
    db 8,8,8,8,8,8,8,8,8
    db 7,8,8,8,5,8,8,8,8
    db 8,8,8,8,8,8,8,8,8
    db 8,8,8,8,8,8,8,8,8

; John Carmack's fixed 256-byte US_RndT table. The runtime index below is
; level state; the immutable table is shared by awareness and future combat.
w3d_random_table:
    db 0,8,109,220,222,241,149,107,75,248,254,140,16,66,74,21
    db 211,47,80,242,154,27,205,128,161,89,77,36,95,110,85,48
    db 212,140,211,249,22,79,200,50,28,188,52,140,202,120,68,145
    db 62,70,184,190,91,197,152,224,149,104,25,178,252,182,202,182
    db 141,197,4,81,181,242,145,42,39,227,156,198,225,193,219,93
    db 122,175,249,0,175,143,70,239,46,246,163,53,163,109,168,135
    db 2,235,25,92,20,145,138,77,69,166,78,176,173,212,166,113
    db 94,161,41,50,239,49,111,164,70,60,2,37,171,75,136,156
    db 11,56,42,146,138,229,73,146,77,61,98,196,135,106,63,197
    db 195,86,96,203,113,101,170,247,181,113,80,250,108,7,255,237
    db 129,226,79,107,112,166,103,241,24,223,239,120,198,58,60,82
    db 128,3,184,66,143,224,145,224,81,206,163,45,63,90,168,114
    db 59,33,159,95,28,139,123,98,125,196,15,70,194,253,54,14
    db 109,226,71,17,161,93,186,87,244,138,20,52,123,251,26,36
    db 17,46,52,231,232,76,31,221,84,37,216,165,212,106,197,242
    db 98,43,39,175,254,145,190,84,118,222,187,136,120,163,236,249
w3d_random_table_end:

; ---------------------------------------------------------------------------
; Scratch/state
; ---------------------------------------------------------------------------

w3d_actor_tic_phase:
    db 0
w3d_actor_frame_tics:
    db 0
w3d_player_made_noise:
    db 0
w3d_awareness_enabled:
    db 0
w3d_random_index:
    db 0
w3d_actor_sight_context:
    ds W3D_SIGHT_CTX_SIZE
w3d_actor_chase_dodge:
    db 0
w3d_actor_chase_old_dir:
    db W3D_DIR_NODIR
w3d_actor_chase_turnaround:
    db W3D_DIR_NODIR
w3d_actor_chase_dirs:
    ds 5
w3d_actor_chase_abs_x:
    db 0
w3d_actor_chase_abs_y:
    db 0
w3d_actor_chase_try_index:
    db 0
w3d_actor_dog_jump_threshold:
    dl 0
w3d_actor_combat_is_ss:
    db 0
w3d_actor_combat_distance:
    db 0
w3d_actor_combat_visible:
    db 0
w3d_actor_combat_hitchance:
    dw 0
w3d_actor_projection_rel_x:
    dw 0
w3d_actor_projection_rel_y:
    dw 0
w3d_actor_projection_cos:
    dw 0
w3d_actor_projection_forward_y:
    dw 0
w3d_actor_projection_term:
    dw 0
w3d_actor_projection_nx:
    dw 0
w3d_actor_projection_left_product:
    ds 4
w3d_actor_iteration_next:
    db W3D_SLOT_NONE
w3d_actor_transitions_left:
    db 0
w3d_actor_old_shape:
    dw 0
w3d_actor_old_rotations:
    db 0
w3d_actor_old_pose:
    ds 8
w3d_actor_old_facing:
    dw 0
w3d_actor_target_x:
    db 0
w3d_actor_target_y:
    db 0
w3d_actor_pending_door:
    db W3D_SLOT_NONE
w3d_actor_checked_door:
    db W3D_SLOT_NONE
w3d_actor_move_remaining:
    dl 0
w3d_actor_move_amount:
    dl 0
w3d_actor_saved_x:
    dl 0
w3d_actor_saved_y:
    dl 0
w3d_actor_fault_count:
    dw 0
