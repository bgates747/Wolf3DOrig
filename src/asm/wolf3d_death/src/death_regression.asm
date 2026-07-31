; Direct real-eZ80 regression for production Wolf3D death/render state.
;
; This fixture includes the same production files as the application. It
; exercises callback routing, ownership/token/sequence validation, killer
; bearing, shortest-path turning, double-buffer target synchronization,
; fizzle completion, held-key acknowledgment, and life/attempt reset. The
; 16-byte death_result.bin mailbox is decoded by the companion runner.
    assume adl=1
    org 040000h
    jp start
    align 64
    db "MOS",0,1

mos_sysvars:         equ 08h
mos_fopen:           equ 0ah
mos_fclose:          equ 0bh
mos_fwrite:          equ 1bh
mos_getkbmap:        equ 1eh
mos_setkbvector:     equ 1dh
sysvar_time:         equ 00h
fa_write:            equ 02h
fa_create_always:    equ 08h

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    include "wolf3d_sight.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_render_async.inc"
    include "wolf3d_actors.inc"
    include "wolf3d_areas.inc"
    include "wolf3d_actor_sim.inc"
    include "wolf3d_motion.inc"
    include "wolf3d_player_combat.inc"
    include "wolf3d_death.inc"

; ez80asm evaluates mixed arithmetic strictly left-to-right. Name the two
; products so neither a base-address addition nor a subtraction can bind
; before the multiplication.
W3D_FIXTURE_STATIC_BYTES: equ W3D_FIXTURE_STATIC_COUNT*W3D_STATIC_SIZE
W3D_STATIC_TAIL_COUNT:    equ W3D_MAX_STATICS-W3D_FIXTURE_STATIC_COUNT
W3D_STATIC_TAIL_BYTES:    equ W3D_STATIC_TAIL_COUNT*W3D_STATIC_SIZE

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
    ld (result_checks),a
    ld (result_errors),a
    ld (result_first_case),a
    ld (result_first_reason),a
    ld (result_first_expected),a
    ld (result_first_actual),a
    call test_callback_routing
    call test_render_events
    call test_fizzle_events
    call test_default_bearings
    call test_turn_routes_and_cadence
    call test_fizzle_phase
    call test_hold_and_lives
    call test_production_reseed_and_submission
    call write_result
    ret

; ---------------------------------------------------------------------------
; Event callback, ownership, purpose, and sequence tests
; ---------------------------------------------------------------------------

test_callback_routing:
    call w3d_initialize_render_state
    ld hl,render_packet_template
    ld de,callback_render_packet
    ld bc,10
    ldir
    ld de,callback_render_packet
    call w3d_render_packet_callback
    ld c,1
    ld d,1
    ld a,(w3d_completion_ready)
    ld b,1
    call expect_a
    ld d,2
    ld a,(w3d_fizzle_completion_ready)
    ld b,0
    call expect_a
    ld d,3
    ld a,(callback_render_packet+0)
    ld b,0
    call expect_a
    ld hl,w3d_completion_record
    ld de,render_packet_template
    ld bc,10
    call test_memory_equal
    ld c,1
    ld d,7
    ld b,1
    call expect_a

    call w3d_initialize_render_state
    ld hl,fizzle_packet_template
    ld de,callback_fizzle_packet
    ld bc,10
    ldir
    ld de,callback_fizzle_packet
    call w3d_render_packet_callback
    ld d,4
    ld a,(w3d_completion_ready)
    ld b,0
    call expect_a
    ld d,5
    ld a,(w3d_fizzle_completion_ready)
    ld b,1
    call expect_a
    ld d,6
    ld a,(callback_fizzle_packet+0)
    ld b,0
    call expect_a
    ld hl,w3d_fizzle_completion_record
    ld de,fizzle_packet_template
    ld bc,10
    call test_memory_equal
    ld c,1
    ld d,8
    ld b,1
    jp expect_a

test_render_events:
    call w3d_initialize_render_state
    ld a,W3D_RENDER_PURPOSE_DEATH_TARGET
    call w3d_set_next_render_purpose
    call w3d_mark_render_submitted
    ld a,0
    adc a,0
    ld c,2
    ld d,1
    ld b,0
    call expect_a
    ld d,2
    ld a,(w3d_async_owner)
    ld b,W3D_ASYNC_OWNER_RENDER
    call expect_a
    ld d,3
    ld a,(w3d_render_in_flight_purpose)
    ld b,W3D_RENDER_PURPOSE_DEATH_TARGET
    call expect_a

    ld hl,render_packet_template
    ld de,w3d_completion_record
    ld bc,10
    ldir
    ld a,1
    ld (w3d_completion_ready),a
    call w3d_consume_render_completion
    ld c,2
    ld d,4
    ld a,(w3d_render_in_flight)
    ld b,0
    call expect_a
    ld d,5
    ld a,(w3d_async_owner)
    ld b,W3D_ASYNC_OWNER_NONE
    call expect_a
    call w3d_take_render_event
    ld (test_render_purpose),a
    ld c,2
    ld a,0
    adc a,0
    ld d,6
    ld b,1
    call expect_a
    ld a,(test_render_purpose)
    ld d,7
    ld b,W3D_RENDER_PURPOSE_DEATH_TARGET
    call expect_a
    call w3d_take_render_event
    ld a,0
    adc a,0
    ld d,8
    ld b,0
    call expect_a

; Accept the exact next sequence, then replay it against the following render.
    call w3d_mark_render_submitted
    ld hl,render_packet_template
    ld de,w3d_completion_record
    ld bc,10
    ldir
    ld a,6
    ld (w3d_completion_record+8),a
    call w3d_consume_render_completion
    ld c,2
    ld d,9
    ld a,(w3d_async_owner)
    ld b,W3D_ASYNC_OWNER_NONE
    call expect_a
    call w3d_mark_render_submitted
    ld hl,render_packet_template
    ld de,w3d_completion_record
    ld bc,10
    ldir
    ld a,6
    ld (w3d_completion_record+8),a
    call w3d_consume_render_completion
    ld c,2
    ld d,10
    ld a,(w3d_callback_error)
    ld b,1
    call expect_a
    ld d,11
    ld a,(w3d_async_owner)
    ld b,W3D_ASYNC_OWNER_RENDER
    call expect_a
    ld d,12
    ld a,(w3d_render_in_flight)
    ld b,1
    call expect_a
    ld hl,09999h
    call w3d_mark_fizzle_submitted
    ld c,2
    ld d,13
    call expect_carry_set
    ld d,14
    ld a,(w3d_fizzle_in_flight)
    ld b,0
    call expect_a
    jp w3d_initialize_render_state

test_fizzle_events:
    call w3d_initialize_render_state
    ld hl,01234h
    call w3d_mark_fizzle_submitted
    ld a,0
    adc a,0
    ld c,3
    ld d,1
    ld b,0
    call expect_a
    ld d,2
    ld a,(w3d_async_owner)
    ld b,W3D_ASYNC_OWNER_FIZZLE
    call expect_a
    ld hl,fizzle_packet_template
    ld de,w3d_fizzle_completion_record
    ld bc,10
    ldir
    call w3d_consume_fizzle_completion
    ld c,3
    ld d,3
    ld a,(w3d_async_owner)
    ld b,W3D_ASYNC_OWNER_NONE
    call expect_a
    ld d,4
    ld a,(w3d_frame_presented)
    ld b,0
    call expect_a
    call w3d_take_fizzle_event
    ld a,0
    adc a,0
    ld d,5
    ld b,1
    call expect_a
    ld d,6
    ld a,l
    ld b,034h
    call expect_a
    ld d,7
    ld a,h
    ld b,012h
    call expect_a

; The next fizzle sequence must be 10. Replay 9 and require a fail-closed
; owner with the callback fault/exit latches asserted.
    ld hl,05678h
    call w3d_mark_fizzle_submitted
    ld hl,fizzle_stale_packet_template
    ld de,w3d_fizzle_completion_record
    ld bc,10
    ldir
    call w3d_consume_fizzle_completion
    ld d,8
    ld a,(w3d_callback_error)
    ld b,1
    call expect_a
    ld d,9
    ld a,(w3d_exit_requested)
    ld b,1
    call expect_a
    ld d,10
    ld a,(w3d_fizzle_in_flight)
    ld b,1
    call expect_a
    call w3d_cancel_fizzle_submission

; Fizzle ownership rejects a render mark without disturbing either owner.
    call w3d_initialize_render_state
    ld hl,09999h
    call w3d_mark_fizzle_submitted
    call w3d_mark_render_submitted
    ld c,3
    ld d,11
    call expect_carry_set
    ld d,12
    ld a,(w3d_async_owner)
    ld b,W3D_ASYNC_OWNER_FIZZLE
    call expect_a
    ld d,13
    ld a,(w3d_render_in_flight)
    ld b,0
    call expect_a
    call w3d_cancel_fizzle_submission

; A correct first sequence with the wrong token must still fail closed.
    call w3d_initialize_render_state
    ld hl,09999h
    call w3d_mark_fizzle_submitted
    ld hl,fizzle_packet_template
    ld de,w3d_fizzle_completion_record
    ld bc,10
    ldir
    call w3d_consume_fizzle_completion
    ld c,3
    ld d,14
    ld a,(w3d_callback_error)
    ld b,1
    call expect_a
    ld d,15
    ld a,(w3d_fizzle_in_flight)
    ld b,1
    call expect_a
    jp w3d_cancel_fizzle_submission

; ---------------------------------------------------------------------------
; Default bearing and shortest-turn tests
; ---------------------------------------------------------------------------

test_default_bearings:
    ld c,4
    ld b,1
    ld e,0
    call seed_actor_relative_tiles
    ld a,1
    call w3d_death_default_bearing
    ld d,1
    call expect_carry_clear
    ld a,l
    ld b,0
    ld d,2
    call expect_a
    ld a,h
    ld b,0
    ld d,3
    call expect_a

    ld b,0
    ld e,0ffh
    call seed_actor_relative_tiles
    ld a,1
    call w3d_death_default_bearing
    ld d,4
    call expect_carry_clear
    ld a,l
    ld b,90
    ld d,5
    call expect_a

    ld b,0ffh
    ld e,0
    call seed_actor_relative_tiles
    ld a,1
    call w3d_death_default_bearing
    ld d,6
    call expect_carry_clear
    ld a,l
    ld b,180
    ld d,7
    call expect_a

    ld b,0
    ld e,1
    call seed_actor_relative_tiles
    ld a,1
    call w3d_death_default_bearing
    ld d,8
    call expect_carry_clear
    ld a,l
    ld b,14
    ld d,9
    call expect_a
    ld a,h
    ld b,1
    ld d,10
    call expect_a

    ld b,1
    ld e,0ffh
    call seed_actor_relative_tiles
    ld a,1
    call w3d_death_default_bearing
    ld d,11
    call expect_carry_clear
    ld a,l
    ld b,45
    ld d,12
    call expect_a

    ld b,0
    ld e,0
    call seed_actor_relative_tiles
    ld a,1
    call w3d_death_default_bearing
    ld d,13
    call expect_carry_set

    xor a
    call w3d_death_default_bearing
    ld d,14
    call expect_carry_set
    ld a,W3D_MAX_ACTORS
    call w3d_death_default_bearing
    ld d,15
    call expect_carry_set
    ld b,1
    ld e,0
    call seed_actor_relative_tiles
    ld a,W3D_ACTOR_ACTIVE_FREE
    ld (ix+W3D_ACTOR_ACTIVE),a
    ld a,1
    call w3d_death_default_bearing
    ld d,16
    call expect_carry_set

; Complete the four diagonal quadrants (NE was checked above).
    ld b,0ffh
    ld e,0ffh
    call seed_actor_relative_tiles
    ld a,1
    call w3d_death_default_bearing
    ld d,17
    call expect_carry_clear
    ld a,l
    ld b,135
    ld d,18
    call expect_a
    ld a,h
    ld b,0
    ld d,19
    call expect_a

    ld b,0ffh
    ld e,1
    call seed_actor_relative_tiles
    ld a,1
    call w3d_death_default_bearing
    ld d,20
    call expect_carry_clear
    ld a,l
    ld b,225
    ld d,21
    call expect_a
    ld a,h
    ld b,0
    ld d,22
    call expect_a

    ld b,1
    ld e,1
    call seed_actor_relative_tiles
    ld a,1
    call w3d_death_default_bearing
    ld d,23
    call expect_carry_clear
    ld a,l
    ld b,315 & 0ffh
    ld d,24
    call expect_a
    ld a,h
    ld b,315 >> 8
    ld d,25
    jp expect_a

; B=signed X tile delta, E=signed map-Y tile delta.
seed_actor_relative_tiles:
    push bc
    push de
    xor a
    ld (w3d_player_pose+0),a
    ld (w3d_player_pose+1),a
    ld (w3d_player_pose+3),a
    ld (w3d_player_pose+4),a
    ld (w3d_player_pose+5),a
    ld (w3d_player_pose+7),a
    ld a,32
    ld (w3d_player_pose+2),a
    ld (w3d_player_pose+6),a
    ld a,1
    call w3d_actor_pointer_from_id
    pop de
    pop bc
    xor a
    ld (ix+W3D_ACTOR_X+0),a
    ld (ix+W3D_ACTOR_X+1),a
    ld (ix+W3D_ACTOR_X+3),a
    ld (ix+W3D_ACTOR_Y+0),a
    ld (ix+W3D_ACTOR_Y+1),a
    ld (ix+W3D_ACTOR_Y+3),a
    ld a,32
    add a,b
    ld (ix+W3D_ACTOR_X+2),a
    ld a,32
    add a,e
    ld (ix+W3D_ACTOR_Y+2),a
    ld (ix+W3D_ACTOR_ACTIVE),W3D_ACTOR_ACTIVE_YES
    ret

test_turn_routes_and_cadence:
    call prepare_death_test
    ld hl,test_bearing_ok
    call w3d_death_set_bearing_hook
    ld a,10
    ld (test_bearing_angle+0),a
    xor a
    ld (test_bearing_angle+1),a
    ld a,350 & 0ffh
    ld (w3d_player_pose+8),a
    ld a,350 >> 8
    ld (w3d_player_pose+9),a
    call w3d_death_promote_lethal_latch
    ld c,5
    ld d,1
    call expect_carry_set
    ld d,2
    ld a,(w3d_death_phase)
    ld b,W3D_DEATH_PHASE_WAIT_DEAD_FRAME
    call expect_a
    ld d,3
    ld a,(w3d_death_turn_direction)
    ld b,1
    call expect_a
    ld d,4
    ld a,(w3d_death_turn_remaining+0)
    ld b,20
    call expect_a
    ld d,17
    ld a,(w3d_player_weapon_shape+0)
    ld b,0ffh
    call expect_a
    ld d,18
    ld a,(w3d_player_weapon_shape+1)
    ld b,0ffh
    call expect_a
    ld d,19
    ld a,(w3d_player_weapon_shape_dirty)
    ld b,1
    call expect_a
    ld d,20
    ld a,(w3d_player_health)
    ld b,0
    call expect_a

    ld a,W3D_RENDER_PURPOSE_DEAD_FACE
    call w3d_death_accept_render_purpose
    ld d,5
    ld a,(w3d_death_phase)
    ld b,W3D_DEATH_PHASE_TURN
    call expect_a

    call w3d_death_fixed_step
    ld a,(w3d_player_pose+8)
    ld b,354 & 0ffh
    ld d,6
    call expect_a
    call w3d_death_fixed_step
    ld a,(w3d_player_pose+8)
    ld b,358 & 0ffh
    ld d,7
    call expect_a
    call w3d_death_fixed_step
    ld a,(w3d_player_pose+8)
    ld b,4
    ld d,8
    call expect_a
    call w3d_death_fixed_step
    ld a,(w3d_player_pose+8)
    ld b,8
    ld d,9
    call expect_a
    call w3d_death_fixed_step
    ld a,(w3d_player_pose+8)
    ld b,10
    ld d,10
    call expect_a
    ld d,11
    ld a,(w3d_death_phase)
    ld b,W3D_DEATH_PHASE_WAIT_TARGET_FRAME
    call expect_a
    call w3d_death_prepare_next_render
    ld d,12
    ld b,W3D_RENDER_PURPOSE_DEATH_TARGET
    call expect_a

; Reverse wrap and exact 180 tie both take the negative route.
    call prepare_death_test
    ld hl,test_bearing_ok
    call w3d_death_set_bearing_hook
    ld a,350 & 0ffh
    ld (test_bearing_angle+0),a
    ld a,350 >> 8
    ld (test_bearing_angle+1),a
    ld a,10
    ld (w3d_player_pose+8),a
    xor a
    ld (w3d_player_pose+9),a
    call w3d_death_promote_lethal_latch
    ld d,13
    ld a,(w3d_death_turn_direction)
    ld b,0ffh
    call expect_a
    ld d,14
    ld a,(w3d_death_turn_remaining+0)
    ld b,20
    call expect_a

    call prepare_death_test
    ld hl,test_bearing_ok
    call w3d_death_set_bearing_hook
    ld a,180
    ld (test_bearing_angle+0),a
    xor a
    ld (test_bearing_angle+1),a
    ld (w3d_player_pose+8),a
    ld (w3d_player_pose+9),a
    call w3d_death_promote_lethal_latch
    ld d,15
    ld a,(w3d_death_turn_direction)
    ld b,0ffh
    call expect_a
    ld d,16
    ld a,(w3d_death_turn_remaining+0)
    ld b,180
    jp expect_a

prepare_death_test:
    call w3d_initialize_render_state
    xor a
    ld (w3d_player_score+0),a
    ld (w3d_player_score+1),a
    ld (w3d_player_score+2),a
    ld (w3d_player_score+3),a
    call w3d_initialize_death_state
    ld a,1
    ld (w3d_player_dead),a
    ld (w3d_player_killer),a
    ld a,100
    ld (w3d_player_health),a
    xor a
    ld (w3d_hud_dirty),a
    ld (w3d_world_dirty),a
    ld (w3d_player_weapon_shape_dirty),a
    ld a,0a5h
    ld (w3d_player_weapon_shape+0),a
    ld a,1
    ld (w3d_player_weapon_shape+1),a
    ret

test_bearing_ok:
    ld hl,0
    ld a,(test_bearing_angle+0)
    ld l,a
    ld a,(test_bearing_angle+1)
    ld h,a
    or a
    ret

; ---------------------------------------------------------------------------
; Fizzle phase, held-key acknowledgment, life decrement, and respawn tests
; ---------------------------------------------------------------------------

test_fizzle_phase:
    call prepare_death_test
    ld hl,test_fizzle_ok
    call w3d_death_set_fizzle_hook
    ld a,W3D_DEATH_PHASE_WAIT_TARGET_FRAME
    ld (w3d_death_phase),a
    ld a,W3D_RENDER_PURPOSE_DEATH_TARGET
    call w3d_death_accept_render_purpose
    ld c,6
    ld d,1
    ld a,(w3d_death_phase)
    ld b,W3D_DEATH_PHASE_WAIT_TARGET_SYNC_FRAME
    call expect_a
    ld d,2
    ld a,(w3d_async_owner)
    ld b,W3D_ASYNC_OWNER_NONE
    call expect_a
    call w3d_death_prepare_next_render
    ld d,3
    ld b,W3D_RENDER_PURPOSE_DEATH_TARGET_SYNC
    call expect_a
    ld a,W3D_RENDER_PURPOSE_DEATH_TARGET_SYNC
    call w3d_death_accept_render_purpose
    ld d,4
    ld a,(w3d_death_phase)
    ld b,W3D_DEATH_PHASE_WAIT_FIZZLE
    call expect_a
    ld d,5
    ld a,(w3d_async_owner)
    ld b,W3D_ASYNC_OWNER_FIZZLE
    call expect_a
    ld d,6
    ld a,(w3d_death_fizzle_token+0)
    ld b,a
    ld a,(test_fizzle_token+0)
    call expect_a

    ld hl,fizzle_packet_template
    ld de,w3d_fizzle_completion_record
    ld bc,10
    ldir
    ld a,(w3d_death_fizzle_token+0)
    ld (w3d_fizzle_completion_record+6),a
    ld a,(w3d_death_fizzle_token+1)
    ld (w3d_fizzle_completion_record+7),a
    ld a,1
    ld (w3d_fizzle_completion_ready),a
    call w3d_death_foreground_update
    ld c,6
    ld d,7
    ld a,(w3d_death_phase)
    ld b,W3D_DEATH_PHASE_HOLD
    call expect_a
    ld d,8
    ld a,(w3d_death_hold_remaining)
    ld b,W3D_DEATH_HOLD_STEPS
    call expect_a
    ld d,9
    ld a,(w3d_async_owner)
    ld b,W3D_ASYNC_OWNER_NONE
    jp expect_a

test_fizzle_ok:
    ld a,e
    ld (test_fizzle_token+0),a
    ld a,d
    ld (test_fizzle_token+1),a
    or a
    ret

test_hold_and_lives:
    call w3d_initialize_render_state
    ld a,1
    ld (w3d_player_score+0),a
    ld a,2
    ld (w3d_player_score+1),a
    ld a,3
    ld (w3d_player_score+2),a
    ld a,4
    ld (w3d_player_score+3),a
    call w3d_initialize_death_state
    ld hl,test_reseed_ok
    call w3d_death_set_reseed_hook
    xor a
    ld (test_reseed_calls),a
    ld a,3
    ld (w3d_player_lives),a
    ld a,2
    ld (w3d_game_difficulty),a
    ld a,011h
    ld (w3d_player_next_extra+0),a
    ld a,022h
    ld (w3d_player_next_extra+1),a
    ld a,033h
    ld (w3d_player_next_extra+2),a
    ld a,044h
    ld (w3d_player_next_extra+3),a
    ld a,0aah
    ld (w3d_player_score+0),a
    ld a,1
    ld (w3d_player_dead),a
    call w3d_reset_keys
    ld a,1
    ld (w3d_keyboard_masks+0),a
    ld a,W3D_DEATH_PHASE_HOLD
    ld (w3d_death_phase),a
    ld a,10
    ld (w3d_death_hold_remaining),a

    call w3d_death_fixed_step
    ld c,7
    ld d,1
    ld a,(w3d_death_ack_armed)
    ld b,0
    call expect_a
    ld d,2
    ld a,(w3d_death_hold_remaining)
    ld b,9
    call expect_a
    call w3d_reset_keys
    call w3d_death_fixed_step
    ld d,3
    ld a,(w3d_death_ack_armed)
    ld b,1
    call expect_a
    ld a,1
    ld (w3d_keyboard_masks+1),a
    call w3d_death_fixed_step
    ld c,7
    ld d,4
    ld a,(w3d_death_phase)
    ld b,W3D_DEATH_PHASE_WAIT_RESPAWN_FRAME
    call expect_a
    ld d,5
    ld a,(w3d_player_lives)
    ld b,2
    call expect_a
    ld d,6
    ld a,(w3d_player_health)
    ld b,100
    call expect_a
    ld d,7
    ld a,(w3d_player_ammo)
    ld b,8
    call expect_a
    ld d,8
    ld a,(w3d_player_score+0)
    ld b,1
    call expect_a
    ld d,9
    ld a,(w3d_player_score+3)
    ld b,4
    call expect_a
    ld d,10
    ld a,(w3d_player_next_extra+2)
    ld b,033h
    call expect_a
    ld d,11
    ld a,(w3d_player_dead)
    ld b,1
    call expect_a
    ld d,12
    ld a,(test_reseed_calls)
    ld b,1
    call expect_a
    ld hl,w3d_player_score
    ld de,test_hold_score
    ld bc,4
    call test_memory_equal
    ld c,7
    ld d,23
    ld b,1
    call expect_a
    ld hl,w3d_player_next_extra
    ld de,test_hold_next_extra
    ld bc,4
    call test_memory_equal
    ld c,7
    ld d,24
    ld b,1
    call expect_a
    ld d,25
    ld a,(w3d_game_difficulty)
    ld b,2
    call expect_a
    ld d,26
    ld a,(w3d_player_weapon)
    ld b,1
    call expect_a
    ld d,27
    ld a,(w3d_player_best_weapon)
    ld b,1
    call expect_a
    ld d,28
    ld a,(w3d_player_chosen_weapon)
    ld b,1
    call expect_a
    ld d,29
    ld a,(w3d_player_key_flags)
    ld b,0
    call expect_a
    ld a,W3D_RENDER_PURPOSE_RESPAWN
    call w3d_death_accept_render_purpose
    ld d,13
    ld a,(w3d_death_phase)
    ld b,W3D_DEATH_PHASE_ALIVE
    call expect_a
    ld d,14
    ld a,(w3d_player_dead)
    ld b,0
    call expect_a

; One displayed life becomes zero and still respawns.
    call prepare_life_finish
    ld a,1
    ld (w3d_player_lives),a
    call w3d_death_finish_hold
    ld d,15
    ld a,(w3d_player_lives)
    ld b,0
    call expect_a
    ld d,16
    ld a,(w3d_death_phase)
    ld b,W3D_DEATH_PHASE_WAIT_RESPAWN_FRAME
    call expect_a

; Displayed zero decrements to signed -1 and enters game over without reseed.
    call prepare_life_finish
    xor a
    ld (test_reseed_calls),a
    ld (w3d_player_lives),a
    call w3d_death_finish_hold
    ld d,17
    ld a,(w3d_player_lives)
    ld b,0ffh
    call expect_a
    ld d,18
    ld a,(w3d_death_phase)
    ld b,W3D_DEATH_PHASE_GAME_OVER
    call expect_a
    ld d,19
    ld a,(test_reseed_calls)
    ld b,0
    call expect_a

; A continuously held key cannot arm acknowledgment, but the original timed
; hold must still expire and consume one life.
    call prepare_life_finish
    ld a,3
    ld (w3d_player_lives),a
    ld a,W3D_DEATH_PHASE_HOLD
    ld (w3d_death_phase),a
    ld a,2
    ld (w3d_death_hold_remaining),a
    call w3d_reset_keys
    ld a,1
    ld (w3d_keyboard_masks+0),a
    call w3d_death_fixed_step
    ld c,7
    ld d,20
    ld a,(w3d_death_phase)
    ld b,W3D_DEATH_PHASE_HOLD
    call expect_a
    call w3d_death_fixed_step
    ld c,7
    ld d,21
    ld a,(w3d_death_phase)
    ld b,W3D_DEATH_PHASE_WAIT_RESPAWN_FRAME
    call expect_a
    ld d,22
    ld a,(w3d_player_lives)
    ld b,2
    jp expect_a

prepare_life_finish:
    xor a
    ld (w3d_player_score+0),a
    ld (w3d_player_score+1),a
    ld (w3d_player_score+2),a
    ld (w3d_player_score+3),a
    call w3d_initialize_death_state
    ld hl,test_reseed_ok
    call w3d_death_set_reseed_hook
    ret

test_reseed_ok:
    ld a,(test_reseed_calls)
    inc a
    ld (test_reseed_calls),a
; Deliberately vandalize every persistent/canonical field. The death layer,
; not this hook, must reapply checkpoint and attempt-reset semantics.
    ld a,0eeh
    ld (w3d_player_score+0),a
    ld (w3d_player_score+1),a
    ld (w3d_player_score+2),a
    ld (w3d_player_score+3),a
    ld (w3d_player_next_extra+0),a
    ld (w3d_player_next_extra+1),a
    ld (w3d_player_next_extra+2),a
    ld (w3d_player_next_extra+3),a
    ld (w3d_game_difficulty),a
    ld (w3d_player_lives),a
    ld (w3d_player_health),a
    ld (w3d_player_ammo),a
    ld (w3d_player_weapon),a
    ld (w3d_player_best_weapon),a
    ld (w3d_player_chosen_weapon),a
    ld (w3d_player_key_flags),a
    or a
    ret

; ---------------------------------------------------------------------------
; Real E1L1 attempt reseed and fail-closed reset submission
; ---------------------------------------------------------------------------

test_production_reseed_and_submission:
    call w3d_initialize_render_state
    call w3d_initialize_motion_state
    ld a,(w3d_player_area)
    ld (test_saved_player_area),a

; Poison every large authoritative region. Passing the comparisons below then
; requires the production reseed to rebuild records, tails, occupancy, areas,
; RNG, controls, and dirty prefixes rather than inheriting fixture state.
    ld a,0a5h
    ld hl,w3d_player_pose
    ld bc,10
    call test_fill_memory
    ld hl,w3d_doors
    ld bc,W3D_FIXTURE_DOOR_COUNT*W3D_DOOR_SIZE
    call test_fill_memory
    ld hl,w3d_door_timers
    ld bc,W3D_FIXTURE_DOOR_COUNT*2
    call test_fill_memory
    ld hl,w3d_statics
    ld bc,W3D_MAX_STATICS*W3D_STATIC_SIZE
    call test_fill_memory
    ld hl,w3d_static_dirty
    ld bc,W3D_MAX_STATICS
    call test_fill_memory
    ld hl,w3d_actors
    ld bc,W3D_MAX_ACTORS*W3D_ACTOR_SIZE
    call test_fill_memory
    ld hl,w3d_actorat
    ld bc,W3D_MAP_BYTES
    call test_fill_memory
    ld hl,w3d_actor_dirty
    ld bc,W3D_MAX_ACTORS
    call test_fill_memory
    ld hl,w3d_keyboard_masks
    ld bc,16
    call test_fill_memory
    ld hl,w3d_area_by_player
    ld bc,W3D_NUM_AREAS
    call test_fill_memory
    ld (w3d_static_count+0),a
    ld (w3d_static_count+1),a
    ld (w3d_actor_count),a
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
    ld (w3d_actor_free_head),a
    ld (w3d_random_index),a
    ld (w3d_player_area),a

; These are game-persistent, not attempt-local, and the real reseed hook must
; leave them untouched for wolf3d_death.inc to reconcile afterward.
    ld hl,test_persistent_score
    ld de,w3d_player_score
    ld bc,4
    ldir
    ld hl,test_persistent_next_extra
    ld de,w3d_player_next_extra
    ld bc,4
    ldir
    ld a,2
    ld (w3d_player_lives),a
    ld a,1
    ld (w3d_game_difficulty),a

    call w3d_reseed_level_attempt
    ld c,8
    ld d,1
    call expect_carry_clear

    ld hl,w3d_player_pose
    ld de,w3d_fixture_initial_player_pose
    ld bc,w3d_fixture_initial_player_pose_end-w3d_fixture_initial_player_pose
    call test_memory_equal
    ld c,8
    ld d,2
    ld b,1
    call expect_a
    ld hl,w3d_doors
    ld de,w3d_fixture_initial_doors
    ld bc,w3d_fixture_initial_doors_end-w3d_fixture_initial_doors
    call test_memory_equal
    ld c,8
    ld d,3
    ld b,1
    call expect_a
    xor a
    ld hl,w3d_door_timers
    ld bc,W3D_FIXTURE_DOOR_COUNT*2
    call test_memory_all_value
    ld c,8
    ld d,4
    ld b,1
    call expect_a
    ld hl,w3d_statics
    ld de,w3d_fixture_initial_statics
    ld bc,w3d_fixture_initial_statics_end-w3d_fixture_initial_statics
    call test_memory_equal
    ld c,8
    ld d,5
    ld b,1
    call expect_a
    xor a
    ld hl,w3d_statics+W3D_FIXTURE_STATIC_BYTES
    ld bc,W3D_STATIC_TAIL_BYTES
    call test_memory_all_value
    ld c,8
    ld d,6
    ld b,1
    call expect_a
    ld a,(w3d_static_count+0)
    ld c,8
    ld d,7
    ld b,W3D_FIXTURE_STATIC_COUNT & 0ffh
    call expect_a
    ld a,(w3d_static_count+1)
    ld d,8
    ld b,W3D_FIXTURE_STATIC_COUNT >> 8
    call expect_a
    ld hl,w3d_actors+W3D_ACTOR_SIZE
    ld de,w3d_fixture_initial_actors
    ld bc,w3d_fixture_initial_actors_end-w3d_fixture_initial_actors
    call test_memory_equal
    ld c,8
    ld d,9
    ld b,1
    call expect_a
    ld a,(w3d_actor_count)
    ld d,10
    ld b,W3D_FIXTURE_ACTOR_COUNT
    call expect_a
    ld a,(w3d_actor_live_head)
    ld d,11
    ld b,1
    call expect_a
    ld a,(w3d_actor_live_tail)
    ld d,12
    ld b,W3D_FIXTURE_ACTOR_COUNT
    call expect_a
    ld a,(w3d_actor_free_head)
    ld d,13
    ld b,W3D_FIXTURE_ACTOR_COUNT+1
    call expect_a
    ld b,33
    ld c,9
    call w3d_actorat_get
    ld c,8
    ld d,14
    ld b,1
    call expect_a
    ld a,(w3d_random_index)
    ld d,15
    ld b,W3D_FIXTURE_RND_INDEX_AFTER_SPAWN
    call expect_a
    ld a,(test_saved_player_area)
    ld b,a
    ld a,(w3d_player_area)
    ld d,16
    call expect_a
    xor a
    ld hl,w3d_keyboard_masks
    ld bc,16
    call test_memory_all_value
    ld c,8
    ld d,17
    ld b,1
    call expect_a
    ld hl,w3d_player_score
    ld de,test_persistent_score
    ld bc,4
    call test_memory_equal
    ld c,8
    ld d,18
    ld b,1
    call expect_a
    ld hl,w3d_player_next_extra
    ld de,test_persistent_next_extra
    ld bc,4
    call test_memory_equal
    ld c,8
    ld d,19
    ld b,1
    call expect_a
    ld a,(w3d_player_lives)
    ld d,20
    ld b,2
    call expect_a
    ld a,(w3d_game_difficulty)
    ld d,21
    ld b,1
    call expect_a

    ld a,1
    ld hl,w3d_door_dirty
    ld bc,W3D_FIXTURE_DOOR_COUNT
    call test_memory_all_value
    ld c,8
    ld d,22
    ld b,1
    call expect_a
    ld a,1
    ld hl,w3d_static_dirty
    ld bc,W3D_FIXTURE_STATIC_COUNT
    call test_memory_all_value
    ld c,8
    ld d,23
    ld b,1
    call expect_a
    xor a
    ld hl,w3d_static_dirty+W3D_FIXTURE_STATIC_COUNT
    ld bc,W3D_MAX_STATICS-W3D_FIXTURE_STATIC_COUNT
    call test_memory_all_value
    ld c,8
    ld d,24
    ld b,1
    call expect_a
    ld a,(w3d_actor_dirty+0)
    ld d,25
    ld b,0
    call expect_a
    ld a,W3D_ACTOR_DIRTY_SET
    ld hl,w3d_actor_dirty+1
    ld bc,W3D_FIXTURE_ACTOR_COUNT
    call test_memory_all_value
    ld c,8
    ld d,26
    ld b,1
    call expect_a
    xor a
    ld hl,w3d_actor_dirty+W3D_FIXTURE_ACTOR_COUNT+1
    ld bc,W3D_MAX_ACTORS-W3D_FIXTURE_ACTOR_COUNT-1
    call test_memory_all_value
    ld c,8
    ld d,27
    ld b,1
    call expect_a
    ld a,(w3d_hud_dirty)
    ld d,28
    ld b,W3D_HUD_DIRTY_HEALTH|W3D_HUD_DIRTY_AMMO|W3D_HUD_DIRTY_KEYS|W3D_HUD_DIRTY_WEAPON|W3D_HUD_DIRTY_SCORE|W3D_HUD_DIRTY_LIVES
    call expect_a
    ld a,(w3d_player_dirty)
    ld d,29
    ld b,1
    call expect_a
    ld a,(w3d_player_weapon_shape_dirty)
    ld d,30
    ld b,1
    call expect_a
    ld a,(w3d_world_dirty)
    ld d,31
    ld b,1
    call expect_a
    ld a,(w3d_player_health)
    ld d,32
    ld b,100
    call expect_a
    ld a,(w3d_player_dead)
    ld d,33
    ld b,0
    call expect_a

; Exercise the production init_level/full-replay preflight without sending
; BUFFERED_WOLF3D bytes to this runner's intentionally stock VDP. A fizzle
; owner must make reset submission fail before init_level and preserve the
; complete reseed dirty set plus the still-pending RESPawn purpose.
    call w3d_initialize_render_state
    ld a,W3D_DEATH_PHASE_WAIT_RESPAWN_FRAME
    ld (w3d_death_phase),a
    call w3d_death_prepare_next_render
    ld c,8
    ld d,34
    ld b,W3D_RENDER_PURPOSE_RESPAWN
    call expect_a
    ld hl,07777h
    call w3d_mark_fizzle_submitted
    ld c,8
    ld d,35
    call expect_carry_clear
    ld a,(w3d_async_owner)
    ld d,36
    ld b,W3D_ASYNC_OWNER_FIZZLE
    call expect_a
    call w3d_death_render_permitted
    ld d,37
    ld b,0
    call expect_a
    call w3d_submit_level_reset
    ld c,8
    ld d,38
    call expect_carry_set
    ld a,(w3d_async_owner)
    ld d,39
    ld b,W3D_ASYNC_OWNER_FIZZLE
    call expect_a
    ld a,(w3d_render_in_flight)
    ld d,40
    ld b,0
    call expect_a
    ld a,(w3d_next_render_purpose)
    ld d,41
    ld b,W3D_RENDER_PURPOSE_RESPAWN
    call expect_a
    ld a,(w3d_world_dirty)
    ld d,42
    ld b,1
    call expect_a
    ld a,1
    ld hl,w3d_door_dirty
    ld bc,W3D_FIXTURE_DOOR_COUNT
    call test_memory_all_value
    ld c,8
    ld d,43
    ld b,1
    call expect_a
    ld a,1
    ld hl,w3d_static_dirty
    ld bc,W3D_FIXTURE_STATIC_COUNT
    call test_memory_all_value
    ld c,8
    ld d,44
    ld b,1
    call expect_a
    ld a,W3D_ACTOR_DIRTY_SET
    ld hl,w3d_actor_dirty+1
    ld bc,W3D_FIXTURE_ACTOR_COUNT
    call test_memory_all_value
    ld c,8
    ld d,45
    ld b,1
    call expect_a
    call w3d_cancel_fizzle_submission

; A conflicting direct caller must emit nothing and retain its dirty state.
    call w3d_initialize_render_state
    call w3d_mark_render_submitted
    ld c,8
    ld d,46
    call expect_carry_clear
    call w3d_submit_dirty_world_render
    ld c,8
    ld d,47
    call expect_carry_set
    ld a,(w3d_world_dirty)
    ld d,48
    ld b,1
    call expect_a
    ld a,(w3d_player_dirty)
    ld d,49
    ld b,1
    call expect_a

; Once shutdown is requested, releasing TARGET_SYNC must not create a fizzle.
    call w3d_initialize_render_state
    ld a,W3D_DEATH_PHASE_WAIT_TARGET_SYNC_FRAME
    ld (w3d_death_phase),a
    ld a,1
    ld (w3d_exit_requested),a
    ld a,W3D_RENDER_PURPOSE_DEATH_TARGET_SYNC
    call w3d_death_accept_render_purpose
    ld c,8
    ld d,50
    ld a,(w3d_death_phase)
    ld b,W3D_DEATH_PHASE_WAIT_TARGET_SYNC_FRAME
    call expect_a
    ld d,51
    ld a,(w3d_async_owner)
    ld b,W3D_ASYNC_OWNER_NONE
    call expect_a

; Pin every phase branch in the public render gate. A render owner was
; already checked above; all of these run with owner NONE.
    call w3d_initialize_render_state
    ld ix,test_render_gate_cases
    ld a,10
    ld (test_gate_remaining),a
    ld a,52
    ld (test_gate_reason),a
@gate_loop:
    ld a,(ix+0)
    ld (w3d_death_phase),a
    call w3d_death_render_permitted
    ld e,a
    ld b,(ix+1)
    ld c,8
    ld a,(test_gate_reason)
    ld d,a
    ld a,e
    call expect_a
    lea ix,ix+2
    ld a,(test_gate_reason)
    inc a
    ld (test_gate_reason),a
    ld hl,test_gate_remaining
    dec (hl)
    jr nz,@gate_loop
    call w3d_initialize_render_state
    call w3d_mark_render_submitted
    call w3d_death_render_permitted
    ld c,8
    ld d,62
    ld b,0
    jp expect_a

; A=value, HL=destination, BC=uint16 length.
test_fill_memory:
    ld d,a
@loop:
    ld a,b
    or c
    ret z
    ld a,d
    ld (hl),a
    inc hl
    dec.s bc
    jr @loop

; HL=actual, DE=expected, BC=uint16 length -> A=1 equal, A=0 mismatch.
test_memory_equal:
@loop:
    ld a,b
    or c
    jr z,@equal
    ld a,(de)
    cp (hl)
    jr nz,@different
    inc hl
    inc de
    dec.s bc
    jr @loop
@equal:
    ld a,1
    ret
@different:
    xor a
    ret

; A=expected byte, HL=actual, BC=uint16 length -> A=1/0.
test_memory_all_value:
    ld (test_memory_expected),a
@loop:
    ld a,b
    or c
    jr z,@equal
    ld a,(test_memory_expected)
    cp (hl)
    jr nz,@different
    inc hl
    dec.s bc
    jr @loop
@equal:
    ld a,1
    ret
@different:
    xor a
    ret

; ---------------------------------------------------------------------------
; Assertions and result mailbox
; ---------------------------------------------------------------------------

; C=case, D=reason, B=expected, A=actual.
expect_a:
    ld e,a
    ld a,(result_checks)
    inc a
    ld (result_checks),a
    ld a,e
    cp b
    ret z
    ld a,(result_errors)
    inc a
    ld (result_errors),a
    cp 1
    ret nz
    ld a,c
    ld (result_first_case),a
    ld a,d
    ld (result_first_reason),a
    ld a,b
    ld (result_first_expected),a
    ld a,e
    ld (result_first_actual),a
    ret

expect_carry_set:
    ld a,0
    adc a,0
    ld b,1
    jp expect_a

expect_carry_clear:
    ld a,0
    adc a,0
    ld b,0
    jp expect_a

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

render_packet_template:
    db 'W','3','D','R',1,W3D_RENDER_EVENT_COMPLETE
    dw w3d_render_notify_token
    dw 5
fizzle_packet_template:
    db 'W','3','D','R',1,W3D_RENDER_EVENT_FIZZLE_COMPLETE
    dw 01234h
    dw 9
fizzle_stale_packet_template:
    db 'W','3','D','R',1,W3D_RENDER_EVENT_FIZZLE_COMPLETE
    dw 05678h
    dw 9

callback_render_packet: ds 10
callback_fizzle_packet: ds 10
test_bearing_angle:     ds 2
test_render_purpose:    db 0
test_fizzle_token:      ds 2
test_reseed_calls:      db 0
test_saved_player_area: db 0
test_memory_expected:  db 0
test_gate_remaining:   db 0
test_gate_reason:      db 0
test_render_gate_cases:
    db W3D_DEATH_PHASE_ALIVE,1
    db W3D_DEATH_PHASE_WAIT_DEAD_FRAME,1
    db W3D_DEATH_PHASE_TURN,1
    db W3D_DEATH_PHASE_WAIT_TARGET_FRAME,1
    db W3D_DEATH_PHASE_WAIT_TARGET_SYNC_FRAME,1
    db W3D_DEATH_PHASE_WAIT_RESPAWN_FRAME,1
    db W3D_DEATH_PHASE_WAIT_FIZZLE,0
    db W3D_DEATH_PHASE_HOLD,0
    db W3D_DEATH_PHASE_RESEED,0
    db W3D_DEATH_PHASE_GAME_OVER,0
test_hold_score:       db 1,2,3,4
test_hold_next_extra:  db 011h,022h,033h,044h
test_persistent_score: db 011h,022h,033h,044h
test_persistent_next_extra: db 055h,066h,077h,088h

result_filename:        db "death_result.bin",0
output_handle:          db 0
result_data:
    db 'W','3','D','1'
result_checks:          db 0
result_errors:          db 0
result_first_case:      db 0
result_first_reason:    db 0
result_first_expected:  db 0
result_first_actual:    db 0
                        db 0,0,0,0,0,1
result_end:
