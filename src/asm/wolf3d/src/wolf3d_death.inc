; =============================================================================
; Ordinary player-death state machine.
;
; The eZ80 owns every durable transition. The VDP receives only render state
; and the asynchronous viewport-only fizzle command. Normal world simulation
; must call w3d_death_promote_lethal_latch after a complete actor pass, call
; w3d_death_fixed_step instead of ordinary simulation while it returns carry,
; pump w3d_death_foreground_update, and classify each submission with
; w3d_death_prepare_next_render.
;
; Hook ABIs:
;   bearing: A=killer slot -> carry clear and HL=0..359, or carry set invalid
;   fizzle:  DE=uint16 token -> carry clear once command bytes were accepted
;   reseed:  no arguments -> carry clear after the authoritative level world
;            has been rebuilt, without submitting a render
;
; Hook setters take a 24-bit code pointer in HL. The defaults provide a real
; actor bearing and the frozen fizzle_to_red wire command. Reseed deliberately
; fails closed until the level-reset owner supplies a complete implementation.
; =============================================================================

W3D_DEATH_PHASE_ALIVE:                equ 0
W3D_DEATH_PHASE_WAIT_DEAD_FRAME:      equ 1
W3D_DEATH_PHASE_TURN:                 equ 2
W3D_DEATH_PHASE_WAIT_TARGET_FRAME:    equ 3
W3D_DEATH_PHASE_WAIT_TARGET_SYNC_FRAME: equ 4
W3D_DEATH_PHASE_WAIT_FIZZLE:          equ 5
W3D_DEATH_PHASE_HOLD:                 equ 6
W3D_DEATH_PHASE_RESEED:               equ 7
W3D_DEATH_PHASE_WAIT_RESPAWN_FRAME:   equ 8
W3D_DEATH_PHASE_GAME_OVER:            equ 9

; DEATHROTATE=2 at the original 70 Hz is exactly 140 degrees/second. At this
; client's 30 Hz fixed step, 4,4,6 repeats to the same rate without fractions.
W3D_DEATH_TURN_STEP_A:                equ 4
W3D_DEATH_TURN_STEP_B:                equ 6
W3D_DEATH_HOLD_STEPS:                 equ 43
W3D_DEATH_FIZZLE_TOKEN_SEED:          equ 0D100h

; ---------------------------------------------------------------------------
; Public lifecycle and hook installation
; ---------------------------------------------------------------------------

w3d_initialize_death_state:
; Clear every compact field deterministically; do not depend on MOS loader BSS
; behavior. The hook pointers are installed immediately afterward.
    xor a
    ld hl,w3d_death_state_begin
    ld (hl),a
    ld de,w3d_death_state_begin+1
    ld bc,w3d_death_state_end-w3d_death_state_begin-1
    ldir

    ld a,W3D_SLOT_NONE
    ld (w3d_death_killer_slot),a

    ld hl,w3d_death_default_bearing
    ld (w3d_death_bearing_hook),hl
    ld hl,w3d_death_default_fizzle_start
    ld (w3d_death_fizzle_hook),hl
    ld hl,w3d_death_default_reseed
    ld (w3d_death_reseed_hook),hl

    ld a,W3D_DEATH_FIZZLE_TOKEN_SEED & 0ffh
    ld (w3d_death_fizzle_token+0),a
    ld a,W3D_DEATH_FIZZLE_TOKEN_SEED >> 8
    ld (w3d_death_fizzle_token+1),a
    jp w3d_death_checkpoint_level_score

w3d_death_set_bearing_hook:
    ld (w3d_death_bearing_hook),hl
    ret

w3d_death_set_fizzle_hook:
    ld (w3d_death_fizzle_hook),hl
    ret

w3d_death_set_reseed_hook:
    ld (w3d_death_reseed_hook),hl
    ret

; Capture the score at level entry/completion. Death restores this checkpoint
; only when another attempt is actually available.
w3d_death_checkpoint_level_score:
    ld a,(w3d_player_score+0)
    ld (w3d_death_oldscore+0),a
    ld a,(w3d_player_score+1)
    ld (w3d_death_oldscore+1),a
    ld a,(w3d_player_score+2)
    ld (w3d_death_oldscore+2),a
    ld a,(w3d_player_score+3)
    ld (w3d_death_oldscore+3),a
    ret

; Promote the stable lethal latch only after the current actor pass is fully
; resolved. Carry set means this call began death presentation; carry clear
; means the player was alive or a death sequence was already active.
w3d_death_promote_lethal_latch:
    ld a,(w3d_death_phase)
    cp W3D_DEATH_PHASE_ALIVE
    jr nz,@not_promoted
    ld a,(w3d_player_dead)
    or a
    jr z,@not_promoted

; Combat for this fixed quantum has already run. Hide the overlay here so the
; first purpose-tagged dead-face snapshot cannot expose one stale gun frame.
    call w3d_hide_player_weapon
    ld a,(w3d_player_killer)
    ld (w3d_death_killer_slot),a
    call w3d_death_call_bearing_hook
    jr c,@bearing_invalid
; Force the undocumented upper byte to zero before validating the 16-bit hook
; result. This is the established eZ80 inc/dec.s idiom.
    inc hl
    dec.s hl
    ld de,360
    or a
    sbc.s hl,de
    jr nc,@bearing_invalid
    add.s hl,de
    ld a,l
    ld (w3d_death_target_angle+0),a
    ld a,h
    ld (w3d_death_target_angle+1),a
    ld a,1
    ld (w3d_death_killer_valid),a
    jr @bearing_ready

@bearing_invalid:
; Missing/corrupt/coincident killers are not fatal. Preserve the current view,
; still show the dead face, and continue to the red fizzle.
    call w3d_load_player_angle
    ld a,l
    ld (w3d_death_target_angle+0),a
    ld a,h
    ld (w3d_death_target_angle+1),a
    xor a
    ld (w3d_death_killer_valid),a

@bearing_ready:
    call w3d_death_choose_turn_route
    xor a
    ld (w3d_death_turn_rate_phase),a
    ld (w3d_death_ack_armed),a
    ld a,W3D_DEATH_PHASE_WAIT_DEAD_FRAME
    ld (w3d_death_phase),a
; Damage normally dirties health already, but the state boundary must be safe
; when tests or future hazards latch death directly.
    xor a
    ld (w3d_player_health),a
    ld a,(w3d_hud_dirty)
    or W3D_HUD_DIRTY_HEALTH
    ld (w3d_hud_dirty),a
    ld a,1
    ld (w3d_world_dirty),a
    scf
    ret

@not_promoted:
    or a
    ret

; Select and latch the semantic purpose for the next render. Call this
; immediately before w3d_mark_render_submitted (or a helper that calls it).
; A returns the selected purpose.
w3d_death_prepare_next_render:
    ld a,(w3d_death_phase)
    cp W3D_DEATH_PHASE_WAIT_DEAD_FRAME
    jr z,@dead_face
    cp W3D_DEATH_PHASE_TURN
    jr z,@turn
    cp W3D_DEATH_PHASE_WAIT_TARGET_FRAME
    jr z,@target
    cp W3D_DEATH_PHASE_WAIT_TARGET_SYNC_FRAME
    jr z,@target_sync
    cp W3D_DEATH_PHASE_WAIT_RESPAWN_FRAME
    jr z,@respawn
    ld a,W3D_RENDER_PURPOSE_NORMAL
    jr @set
@dead_face:
    ld a,W3D_RENDER_PURPOSE_DEAD_FACE
    jr @set
@turn:
    ld a,W3D_RENDER_PURPOSE_DEATH_TURN
    jr @set
@target:
    ld a,W3D_RENDER_PURPOSE_DEATH_TARGET
    jr @set
@target_sync:
    ld a,W3D_RENDER_PURPOSE_DEATH_TARGET_SYNC
    jr @set
@respawn:
    ld a,W3D_RENDER_PURPOSE_RESPAWN
@set:
    call w3d_set_next_render_purpose
    ret

; Return A=1 when an ordinary render submission is legal. Fizzle, hold,
; reseed, and game-over phases retain exclusive ownership of the red surface.
w3d_death_render_permitted:
    ld a,(w3d_async_owner)
    or a
    jr nz,@no
    ld a,(w3d_death_phase)
    cp W3D_DEATH_PHASE_WAIT_FIZZLE
    jr z,@no
    cp W3D_DEATH_PHASE_HOLD
    jr z,@no
    cp W3D_DEATH_PHASE_RESEED
    jr z,@no
    cp W3D_DEATH_PHASE_GAME_OVER
    jr z,@no
    ld a,1
    or a
    ret
@no:
    xor a
    ret

; ---------------------------------------------------------------------------
; Foreground asynchronous event pump
; ---------------------------------------------------------------------------

; Safe whether the caller has already consumed the raw render mailbox or not.
; This routine never presents fizzle event 2; render_async validates it and
; publishes only the one-shot completion token.
w3d_death_foreground_update:
    ld a,(w3d_completion_ready)
    or a
    call nz,w3d_consume_render_completion

    call w3d_take_render_event
    jr nc,@no_render_event
    call w3d_death_accept_render_purpose
@no_render_event:
    ld a,(w3d_fizzle_completion_ready)
    or a
    call nz,w3d_consume_fizzle_completion

    call w3d_take_fizzle_event
    jr nc,@done
    call w3d_death_accept_fizzle_completion
@done:
    ld a,(w3d_death_phase)
    ret

; A=latched purpose from the render that was actually presented.
w3d_death_accept_render_purpose:
    cp W3D_RENDER_PURPOSE_DEAD_FACE
    jr z,@dead_face
    cp W3D_RENDER_PURPOSE_DEATH_TARGET
    jr z,@target
    cp W3D_RENDER_PURPOSE_DEATH_TARGET_SYNC
    jr z,@target_sync
    cp W3D_RENDER_PURPOSE_RESPAWN
    jr z,@respawn
; Normal and intermediate-turn completions only release the next snapshot.
    ret

@dead_face:
    ld a,(w3d_death_phase)
    cp W3D_DEATH_PHASE_WAIT_DEAD_FRAME
    ret nz
    call w3d_death_load_turn_remaining
    ld a,h
    or l
    jr z,@target_frame_needed
    ld a,W3D_DEATH_PHASE_TURN
    ld (w3d_death_phase),a
    ret
@target_frame_needed:
; Submit one purpose-tagged target frame even when no rotation was needed. It
; gives the fizzle an unambiguous, fully presented source surface.
    ld a,W3D_DEATH_PHASE_WAIT_TARGET_FRAME
    ld (w3d_death_phase),a
    ld a,1
    ld (w3d_player_dirty),a
    ld (w3d_world_dirty),a
    ret

@target:
    ld a,(w3d_death_phase)
    cp W3D_DEATH_PHASE_WAIT_TARGET_FRAME
    ret nz
; Mode 8 alternates two physical surfaces. The first final-target render makes
; only one surface current; force the exact same pose through the other
; surface before granting the fizzle exclusive ownership of both.
    ld a,W3D_DEATH_PHASE_WAIT_TARGET_SYNC_FRAME
    ld (w3d_death_phase),a
    ld a,1
    ld (w3d_player_dirty),a
    ld (w3d_world_dirty),a
    ret

@target_sync:
    ld a,(w3d_death_phase)
    cp W3D_DEATH_PHASE_WAIT_TARGET_SYNC_FRAME
    ret nz
; Escape owns shutdown once the last render completion releases its owner.
; Do not create a brand-new asynchronous fizzle that main would then have to
; await after the user has already requested exit.
    ld a,(w3d_exit_requested)
    or a
    ret nz
    jp w3d_death_begin_fizzle

@respawn:
    ld a,(w3d_death_phase)
    cp W3D_DEATH_PHASE_WAIT_RESPAWN_FRAME
    ret nz
    xor a
    ld (w3d_player_dead),a
    ld (w3d_death_phase),a       ; ALIVE == 0
    ret

; HL is the already-validated event-2 token. render_async compared it against
; the outstanding token and sequence before publishing this event.
w3d_death_accept_fizzle_completion:
    ld a,(w3d_death_phase)
    cp W3D_DEATH_PHASE_WAIT_FIZZLE
    ret nz
    ld a,W3D_DEATH_HOLD_STEPS
    ld (w3d_death_hold_remaining),a
    xor a
    ld (w3d_death_ack_armed),a
    ld a,W3D_DEATH_PHASE_HOLD
    ld (w3d_death_phase),a
    ret

; ---------------------------------------------------------------------------
; Fixed-step phase runner
; ---------------------------------------------------------------------------

; Carry clear means ALIVE and the caller should run one ordinary world step.
; Carry set means death owns this quantum; input polling and Escape remain the
; caller's responsibility. Render cadence never changes this phase timing.
w3d_death_fixed_step:
    ld a,(w3d_death_phase)
    cp W3D_DEATH_PHASE_ALIVE
    jr z,@alive
    cp W3D_DEATH_PHASE_TURN
    jr z,@turn
    cp W3D_DEATH_PHASE_HOLD
    jr z,@hold
    cp W3D_DEATH_PHASE_RESEED
    jr z,@reseed
    scf
    ret
@turn:
    call w3d_death_advance_turn
    scf
    ret
@hold:
    call w3d_death_advance_hold
    scf
    ret
@reseed:
    call w3d_death_attempt_reseed
    scf
    ret
@alive:
    or a
    ret

w3d_death_advance_turn:
    call w3d_death_load_turn_remaining
    ld a,h
    or l
    jr z,@finished

; Exact 4,4,6 cadence. DE is the positive clamped magnitude for accounting;
; the negative route negates its low word for the explicit .s turn helper.
    ld a,(w3d_death_turn_rate_phase)
    cp 2
    jr z,@step_six
    inc a
    ld (w3d_death_turn_rate_phase),a
    ld de,W3D_DEATH_TURN_STEP_A
    jr @clamp
@step_six:
    xor a
    ld (w3d_death_turn_rate_phase),a
    ld de,W3D_DEATH_TURN_STEP_B

@clamp:
    push hl
    or a
    sbc.s hl,de
    pop hl
    jr nc,@step_ready
    ld d,h
    ld e,l
@step_ready:
    ld a,e
    ld (w3d_death_step_magnitude),a
    ld a,(w3d_death_turn_direction)
    bit 7,a
    jr z,@rotate
    xor a
    sub e
    ld e,a
    ld a,0
    sbc a,d
    ld d,a
@rotate:
    call w3d_death_apply_signed_turn

    call w3d_death_load_turn_remaining
    ld a,(w3d_death_step_magnitude)
    ld e,a
    ld d,0
    or a
    sbc.s hl,de
    call w3d_death_store_turn_remaining
    ld a,h
    or l
    ret nz
@finished:
    ld a,W3D_DEATH_PHASE_WAIT_TARGET_FRAME
    ld (w3d_death_phase),a
; The final exact target angle is dirty even if a slower turn frame remains in
; flight; its latched purpose cannot be mistaken for this target snapshot.
    ld a,1
    ld (w3d_player_dirty),a
    ld (w3d_world_dirty),a
    ret

; DE is a signed low-16-bit turn delta. The .s suffix is intentional: the
; dynamically negated DEU byte is irrelevant and must never enter the sum.
w3d_death_apply_signed_turn:
    call w3d_load_player_angle
    add.s hl,de
    bit 7,h
    jr z,@not_negative
    ld de,360
    add.s hl,de
    jr @store
@not_negative:
    ld de,360
    or a
    sbc.s hl,de
    jr nc,@store
    add.s hl,de
@store:
    ld a,l
    ld (w3d_player_pose+8),a
    ld a,h
    ld (w3d_player_pose+9),a
    ld a,1
    ld (w3d_player_dirty),a
    ld (w3d_world_dirty),a
    ret

w3d_death_advance_hold:
    ld a,(w3d_death_hold_remaining)
    or a
    jr z,@finish
    dec a
    ld (w3d_death_hold_remaining),a
    jr z,@finish

    call w3d_death_any_key_down
    ld b,a
    ld a,(w3d_death_ack_armed)
    or a
    jr nz,@armed
; A held combat key cannot dismiss the red screen. Arm only after a complete
; fixed quantum observes every key released.
    ld a,b
    or a
    ret nz
    ld a,1
    ld (w3d_death_ack_armed),a
    ret
@armed:
    ld a,b
    or a
    ret z
@finish:
    jp w3d_death_finish_hold

w3d_death_any_key_down:
    ld hl,w3d_keyboard_masks
    ld b,16
    xor a
@loop:
    or (hl)
    inc hl
    djnz @loop
    ret

; ---------------------------------------------------------------------------
; Turn route, fizzle submission, and attempt restart
; ---------------------------------------------------------------------------

; Choose target-current modulo 360. Exact 180-degree ties take the original
; counterclockwise/negative branch because the C source tests clockwise <
; counter rather than <=.
w3d_death_choose_turn_route:
    call w3d_load_player_angle
    ld a,l
    ld (w3d_death_current_angle+0),a
    ld a,h
    ld (w3d_death_current_angle+1),a

    call w3d_death_load_target_angle
    ld de,0
    ld a,(w3d_death_current_angle+0)
    ld e,a
    ld a,(w3d_death_current_angle+1)
    ld d,a
    or a
    sbc.s hl,de
    jr nc,@positive_delta
    ld de,360
    add.s hl,de
@positive_delta:
    ld a,l
    ld (w3d_death_positive_delta+0),a
    ld a,h
    ld (w3d_death_positive_delta+1),a
    or l
    jr z,@no_turn

    ld de,180
    or a
    sbc.s hl,de
    jr c,@positive_route
; Negative route, including the exact tie: remaining = 360-positive_delta.
    ld hl,360
    ld de,0
    ld a,(w3d_death_positive_delta+0)
    ld e,a
    ld a,(w3d_death_positive_delta+1)
    ld d,a
    or a
    sbc.s hl,de
    call w3d_death_store_turn_remaining
    ld a,0ffh
    ld (w3d_death_turn_direction),a
    ret

@positive_route:
    call w3d_death_load_positive_delta
    call w3d_death_store_turn_remaining
    ld a,1
    ld (w3d_death_turn_direction),a
    ret

@no_turn:
    xor a
    ld (w3d_death_turn_remaining+0),a
    ld (w3d_death_turn_remaining+1),a
    ld (w3d_death_turn_direction),a
    ret

w3d_death_begin_fizzle:
; A new token on every attempt makes a delayed event from a previous death
; fail validation even if its independent sequence were somehow replayed.
    ld hl,w3d_death_fizzle_token
    inc (hl)
    jr nz,@token_ready
    inc hl
    inc (hl)
@token_ready:
    call w3d_death_load_fizzle_token
    call w3d_mark_fizzle_submitted
    jr c,@fault
    ld a,W3D_DEATH_PHASE_WAIT_FIZZLE
    ld (w3d_death_phase),a
    call w3d_death_load_fizzle_token
    ld d,h
    ld e,l
    call w3d_death_call_fizzle_hook
    ret nc
    call w3d_cancel_fizzle_submission
@fault:
    ld a,1
    ld (w3d_death_fault),a
    ld a,W3D_DEATH_PHASE_GAME_OVER
    ld (w3d_death_phase),a
    scf
    ret

w3d_death_finish_hold:
; Original lives are signed: displayed zero is one final playable attempt.
; Decrement first, and only -1 (0xff) enters game over.
    ld a,(w3d_player_lives)
    dec a
    ld (w3d_player_lives),a
    cp 0ffh
    jr z,@game_over
    ld (w3d_death_respawn_lives),a

; SetupGameLevel-like hooks may reinitialize these persistent fields. Preserve
; them here and reapply canonical attempt inventory after the hook succeeds.
    ld a,(w3d_player_next_extra+0)
    ld (w3d_death_saved_next_extra+0),a
    ld a,(w3d_player_next_extra+1)
    ld (w3d_death_saved_next_extra+1),a
    ld a,(w3d_player_next_extra+2)
    ld (w3d_death_saved_next_extra+2),a
    ld a,(w3d_player_next_extra+3)
    ld (w3d_death_saved_next_extra+3),a
    ld a,(w3d_game_difficulty)
    ld (w3d_death_saved_difficulty),a

    ld a,W3D_DEATH_PHASE_RESEED
    ld (w3d_death_phase),a
    jp w3d_death_attempt_reseed

@game_over:
    ld a,W3D_DEATH_PHASE_GAME_OVER
    ld (w3d_death_phase),a
    ret

w3d_death_attempt_reseed:
    call w3d_death_call_reseed_hook
    jr c,@fault
    call w3d_death_reset_player_attempt
    ld a,W3D_DEATH_PHASE_WAIT_RESPAWN_FRAME
    ld (w3d_death_phase),a
    ret
@fault:
    ld a,1
    ld (w3d_death_fault),a
    ld a,W3D_DEATH_PHASE_GAME_OVER
    ld (w3d_death_phase),a
    ret

w3d_death_reset_player_attempt:
    ld a,(w3d_death_respawn_lives)
    ld (w3d_player_lives),a
    ld a,(w3d_death_saved_difficulty)
    ld (w3d_game_difficulty),a

    ld a,(w3d_death_oldscore+0)
    ld (w3d_player_score+0),a
    ld a,(w3d_death_oldscore+1)
    ld (w3d_player_score+1),a
    ld a,(w3d_death_oldscore+2)
    ld (w3d_player_score+2),a
    ld a,(w3d_death_oldscore+3)
    ld (w3d_player_score+3),a
    ld a,(w3d_death_saved_next_extra+0)
    ld (w3d_player_next_extra+0),a
    ld a,(w3d_death_saved_next_extra+1)
    ld (w3d_player_next_extra+1),a
    ld a,(w3d_death_saved_next_extra+2)
    ld (w3d_player_next_extra+2),a
    ld a,(w3d_death_saved_next_extra+3)
    ld (w3d_player_next_extra+3),a

    ld a,100
    ld (w3d_player_health),a
    ld a,8
    ld (w3d_player_ammo),a
    ld a,1
    ld (w3d_player_weapon),a
    ld (w3d_player_best_weapon),a
    ld (w3d_player_chosen_weapon),a
    call w3d_initialize_player_combat
    xor a
    ld (w3d_player_key_flags),a
    ld (w3d_controls),a
    ld (w3d_use_was_down),a
    ld (w3d_player_thrustspeed+0),a
    ld (w3d_player_thrustspeed+1),a
    ld (w3d_player_treasure_count+0),a
    ld (w3d_player_treasure_count+1),a
    ld (w3d_pickup_scan_needed),a
    ld a,W3D_SLOT_NONE
    ld (w3d_player_last_attacker),a
    ld (w3d_player_killer),a
; Keep w3d_player_dead latched until the normal respawn surface is presented.
    ld a,W3D_HUD_DIRTY_HEALTH|W3D_HUD_DIRTY_AMMO|W3D_HUD_DIRTY_KEYS|W3D_HUD_DIRTY_WEAPON|W3D_HUD_DIRTY_SCORE|W3D_HUD_DIRTY_LIVES
    ld (w3d_hud_dirty),a
    ld a,1
    ld (w3d_player_dead),a
    ld (w3d_player_dirty),a
    ld (w3d_world_dirty),a
    ret

; ---------------------------------------------------------------------------
; Default hooks and indirect-call trampolines
; ---------------------------------------------------------------------------

w3d_death_call_bearing_hook:
    ld hl,(w3d_death_bearing_hook)
    jp (hl)

w3d_death_call_fizzle_hook:
    ld hl,(w3d_death_fizzle_hook)
    jp (hl)

w3d_death_call_reseed_hook:
    ld hl,(w3d_death_reseed_hook)
    jp (hl)

; A=killer slot -> carry clear, HL=0..359. The reduced 8.8 actor vector is
; precise over a 64x64 level. A 257-byte atan table limits quantization to
; about one degree while avoiding sqrt and division beyond the existing
; restoring slope primitive.
w3d_death_default_bearing:
    or a
    jp z,@invalid
    cp W3D_MAX_ACTORS
    jp nc,@invalid
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_ACTIVE)
    cp W3D_ACTOR_ACTIVE_ALWAYS+1
    jp nc,@invalid
    call w3d_actor_load_relative_q8

    xor a
    ld (w3d_death_bearing_signs),a
    ld a,(w3d_actor_projection_rel_x+1)
    bit 7,a
    jr z,@x_sign_ready
    ld a,1
    ld (w3d_death_bearing_signs),a
@x_sign_ready:
; desired north-positive Y is -relative-map-Y, so positive relative Y means a
; negative angular Y. Zero must remain unsigned in either direction.
    ld a,(w3d_actor_projection_rel_y+0)
    ld b,a
    ld a,(w3d_actor_projection_rel_y+1)
    ld c,a
    or b
    jr z,@y_sign_ready
    bit 7,c
    jr nz,@y_sign_ready
    ld a,(w3d_death_bearing_signs)
    or 2
    ld (w3d_death_bearing_signs),a
@y_sign_ready:
    call w3d_death_capture_absolute_vector
    ld a,(w3d_death_abs_x+0)
    ld b,a
    ld a,(w3d_death_abs_x+1)
    or b
    ld b,a
    ld a,(w3d_death_abs_y+0)
    ld c,a
    ld a,(w3d_death_abs_y+1)
    or c
    or b
    jp z,@invalid

; Compare absY with absX using explicitly 16-bit arithmetic.
    call w3d_death_load_abs_y
    ld de,0
    ld a,(w3d_death_abs_x+0)
    ld e,a
    ld a,(w3d_death_abs_x+1)
    ld d,a
    or a
    sbc.s hl,de
    jr c,@y_is_minor
    jr z,@y_is_minor

; angle_abs = 90 - atan(absX/absY)
    call w3d_death_load_abs_x
    ld de,0
    ld a,(w3d_death_abs_y+0)
    ld e,a
    ld a,(w3d_death_abs_y+1)
    ld d,a
    call w3d_slope8
    call w3d_death_lookup_atan
    ld b,a
    ld a,90
    sub b
    jr @acute_ready

@y_is_minor:
; angle_abs = atan(absY/absX)
    call w3d_death_load_abs_y
    ld de,0
    ld a,(w3d_death_abs_x+0)
    ld e,a
    ld a,(w3d_death_abs_x+1)
    ld d,a
    call w3d_slope8
    call w3d_death_lookup_atan

@acute_ready:
    ld (w3d_death_acute_angle),a
    ld a,(w3d_death_bearing_signs)
    bit 0,a
    jr nz,@x_negative
    bit 1,a
    jr nz,@quadrant_four
; Quadrant I: +X,+northY.
    ld hl,0
    ld a,(w3d_death_acute_angle)
    ld l,a
    or a
    ret

@quadrant_four:
; Quadrant IV: 360-acute.
    ld a,(w3d_death_acute_angle)
    or a
    jr z,@quadrant_four_zero
    ld hl,360
    ld de,0
    ld e,a
    or a
    sbc.s hl,de
    or a
    ret
@quadrant_four_zero:
    ld hl,0
    or a
    ret

@x_negative:
    bit 1,a
    jr nz,@quadrant_three
; Quadrant II: 180-acute.
    ld hl,180
    ld de,0
    ld a,(w3d_death_acute_angle)
    ld e,a
    or a
    sbc.s hl,de
    or a
    ret

@quadrant_three:
; Quadrant III: 180+acute.
    ld hl,180
    ld de,0
    ld a,(w3d_death_acute_angle)
    ld e,a
    add.s hl,de
    or a
    ret

@invalid:
    scf
    ret

w3d_death_capture_absolute_vector:
    ld hl,0
    ld a,(w3d_actor_projection_rel_x+0)
    ld l,a
    ld a,(w3d_actor_projection_rel_x+1)
    ld h,a
    bit 7,h
    call nz,w3d_death_negate_hl
    ld a,l
    ld (w3d_death_abs_x+0),a
    ld a,h
    ld (w3d_death_abs_x+1),a

    ld hl,0
    ld a,(w3d_actor_projection_rel_y+0)
    ld l,a
    ld a,(w3d_actor_projection_rel_y+1)
    ld h,a
    bit 7,h
    call nz,w3d_death_negate_hl
    ld a,l
    ld (w3d_death_abs_y+0),a
    ld a,h
    ld (w3d_death_abs_y+1),a
    ret

w3d_death_negate_hl:
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
    ret

; HL is a 0..256 Q8 ratio from w3d_slope8; return floor(atan(ratio)) in A.
w3d_death_lookup_atan:
    inc hl
    dec.s hl
    ld de,w3d_death_atan_q8_degrees
    add hl,de
    ld a,(hl)
    ret

; DE=token. Marking ownership is performed by w3d_death_begin_fizzle before
; this hook, so the byte stream cannot beat its completion mailbox state.
w3d_death_default_fizzle_start:
    ld a,e
    ld (@token+0),a
    ld a,d
    ld (@token+1),a
    ld hl,@command
    ld bc,@end-@command
    rst.lil 18h
    or a
    ret
@command:
    db 23,0,0a0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4ah,9
@token:
    dw 0
@end:

; A complete world reseed cannot be guessed here: its owner must rebuild VDP
; init_level state plus eZ80 doors/statics/actors/occupancy/areas/RNG and mark
; the full first snapshot dirty. Fail closed until that hook is installed.
w3d_death_default_reseed:
    scf
    ret

; ---------------------------------------------------------------------------
; Compact word helpers (never read the upper byte adjacent to a uint16)
; ---------------------------------------------------------------------------

w3d_death_load_target_angle:
    ld hl,0
    ld a,(w3d_death_target_angle+0)
    ld l,a
    ld a,(w3d_death_target_angle+1)
    ld h,a
    ret

w3d_death_load_positive_delta:
    ld hl,0
    ld a,(w3d_death_positive_delta+0)
    ld l,a
    ld a,(w3d_death_positive_delta+1)
    ld h,a
    ret

w3d_death_load_turn_remaining:
    ld hl,0
    ld a,(w3d_death_turn_remaining+0)
    ld l,a
    ld a,(w3d_death_turn_remaining+1)
    ld h,a
    ret

w3d_death_store_turn_remaining:
    ld a,l
    ld (w3d_death_turn_remaining+0),a
    ld a,h
    ld (w3d_death_turn_remaining+1),a
    ret

w3d_death_load_fizzle_token:
    ld hl,0
    ld a,(w3d_death_fizzle_token+0)
    ld l,a
    ld a,(w3d_death_fizzle_token+1)
    ld h,a
    ret

w3d_death_load_abs_x:
    ld hl,0
    ld a,(w3d_death_abs_x+0)
    ld l,a
    ld a,(w3d_death_abs_x+1)
    ld h,a
    ret

w3d_death_load_abs_y:
    ld hl,0
    ld a,(w3d_death_abs_y+0)
    ld l,a
    ld a,(w3d_death_abs_y+1)
    ld h,a
    ret

; floor(degrees(atan(index/256))), index 0..256.
w3d_death_atan_q8_degrees:
    db 0,0,0,0,0,1,1,1,1,2,2,2,2,2,3,3
    db 3,3,4,4,4,4,4,5,5,5,5,6,6,6,6,6
    db 7,7,7,7,8,8,8,8,8,9,9,9,9,9,10,10
    db 10,10,11,11,11,11,11,12,12,12,12,12,13,13,13,13
    db 14,14,14,14,14,15,15,15,15,15,16,16,16,16,16,17
    db 17,17,17,17,18,18,18,18,18,19,19,19,19,19,20,20
    db 20,20,20,21,21,21,21,21,22,22,22,22,22,23,23,23
    db 23,23,24,24,24,24,24,24,25,25,25,25,25,26,26,26
    db 26,26,26,27,27,27,27,27,27,28,28,28,28,28,29,29
    db 29,29,29,29,30,30,30,30,30,30,31,31,31,31,31,31
    db 32,32,32,32,32,32,32,33,33,33,33,33,33,34,34,34
    db 34,34,34,34,35,35,35,35,35,35,36,36,36,36,36,36
    db 36,37,37,37,37,37,37,37,37,38,38,38,38,38,38,38
    db 39,39,39,39,39,39,39,40,40,40,40,40,40,40,40,41
    db 41,41,41,41,41,41,41,42,42,42,42,42,42,42,42,43
    db 43,43,43,43,43,43,43,43,44,44,44,44,44,44,44,44
    db 45

; ---------------------------------------------------------------------------
; State storage
; ---------------------------------------------------------------------------

w3d_death_state_begin:
w3d_death_phase:
    db W3D_DEATH_PHASE_ALIVE
w3d_death_killer_slot:
    db W3D_SLOT_NONE
w3d_death_killer_valid:
    db 0
w3d_death_target_angle:
    ds 2
w3d_death_current_angle:
    ds 2
w3d_death_positive_delta:
    ds 2
w3d_death_turn_remaining:
    ds 2
w3d_death_turn_direction:
    db 0
w3d_death_turn_rate_phase:
    db 0
w3d_death_step_magnitude:
    db 0
w3d_death_hold_remaining:
    db 0
w3d_death_ack_armed:
    db 0
w3d_death_fault:
    db 0
w3d_death_fizzle_token:
    ds 2
w3d_death_respawn_lives:
    db 0
w3d_death_saved_difficulty:
    db 0
w3d_death_oldscore:
    ds 4
w3d_death_saved_next_extra:
    ds 4
w3d_death_bearing_hook:
    dl 0
w3d_death_fizzle_hook:
    dl 0
w3d_death_reseed_hook:
    dl 0
w3d_death_bearing_signs:
    db 0
w3d_death_abs_x:
    ds 2
w3d_death_abs_y:
    ds 2
w3d_death_acute_angle:
    db 0
w3d_death_state_end:
