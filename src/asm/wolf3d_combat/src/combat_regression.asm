; Direct real-eZ80 regression for production Wolf3D ordinary combat.
; Synthetic inputs and literal expectations only; every gameplay decision
; calls production labels from wolf3d_actor_sim.inc / wolf3d_motion.inc.

    assume adl=1
    org 0x040000
    jp start
    align 64
    db "MOS",0,1

mos_fopen:          equ 0x0a
mos_fclose:         equ 0x0b
mos_fwrite:         equ 0x1b
mos_getkbmap:       equ 0x1e
fa_write:           equ 0x02
fa_create_always:   equ 0x08

prt_reload_1ms:     equ 72
TMR1_CTL:           equ 083h
TMR_REG_CTL:        equ 0
TMR_RES_LOW:        equ 1
TMR_RES_HIGH:       equ 2
PRT_OFF:            equ %00001110
PRT_ON:             equ %01011111
timing_iterations:  equ 10000

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    macro CHECK_A expected, why
        ld b,expected
        ld c,why
        call assert_equal
    endmacro

    macro CHECK_MEM8 address, expected, why
        ld a,(address)
        CHECK_A expected,why
    endmacro

    macro CHECK_IX8 offset, expected, why
        ld a,(ix+offset)
        CHECK_A expected,why
    endmacro

    macro CHECK_IX24 offset, b0, b1, b2, why
        CHECK_IX8 offset+0,b0,why
        CHECK_IX8 offset+1,b1,why
        CHECK_IX8 offset+2,b2,why
    endmacro

    include "wolf3d_audio_assets.inc"
    include "wolf3d_sight.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_actors.inc"
    include "wolf3d_areas.inc"
    include "wolf3d_actor_sim.inc"
    include "wolf3d_motion.inc"
    include "wolf3d_player_combat.inc"

phase_states:       equ 1
phase_entry:        equ 2
phase_timing:       equ 3
phase_shoot:        equ 4
phase_visibility:   equ 5
phase_thrust:       equ 6
phase_bite:         equ 7
phase_damage:       equ 8
phase_containment:  equ 9
phase_benchmark:    equ 10
phase_count:        equ 10

reason_scalar:      equ 1
reason_state:       equ 2
reason_rng:         equ 3
reason_health:      equ 4
reason_visibility:  equ 5
reason_thrust:      equ 6
reason_death:       equ 7
reason_table:       equ 8
reason_fault:       equ 9
reason_reservation: equ 10
reason_clock:       equ 11
reason_pose:        equ 12
reason_audio:       equ 13

cell_center:        equ 20*64+20

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
    ld hl,result_checks
    ld (hl),a
    ld de,result_checks+1
    ld bc,result_end-result_checks-1
    ldir
    ld a,1
    ld (result_schema),a
    call prt_irq_install
    call test_state_table
    call test_entry_latches
    call test_state_timing
    call test_shoot
    call test_visibility
    call test_thrust
    call test_bite
    call test_damage
    call test_audio_events
    call test_containment_scheduler
    call time_combat
    call prt_irq_restore
    call write_result
    call print_report
    ret

; ---------------------------------------------------------------------------
; 1. All 24 attack records and total state count.
; ---------------------------------------------------------------------------

test_state_table:
    ld a,phase_states
    ld (test_phase),a
    ld a,1
    ld (test_detail),a
    ld a,W3D_STATE_COUNT
    CHECK_A 130,reason_scalar
    ld hl,w3d_actor_states_end-w3d_actor_states
    ld a,l
    CHECK_A 010h,reason_scalar
    ld a,h
    CHECK_A 4,reason_scalar
    ld ix,w3d_actor_states+616       ; 77 * 8
    ld iy,expected_attack_states
    ld de,expected_attack_states_end-expected_attack_states
    ld c,reason_table
    jp assert_memory

; ---------------------------------------------------------------------------
; 2. Class-specific NewState entry latches.
; ---------------------------------------------------------------------------

test_entry_latches:
    ld a,phase_entry
    ld (test_phase),a

    ld a,1
    ld (test_detail),a
    call prepare_guard
    call w3d_actor_begin_ranged_attack
    ld a,0
    adc a,0
    CHECK_A 0,reason_scalar
    CHECK_IX8 W3D_ACTOR_STATE,W3D_STATE_GRD_SHOOT1,reason_state
    CHECK_IX8 W3D_ACTOR_TICCOUNT,20,reason_state

    ld a,2
    ld (test_detail),a
    call prepare_guard
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_OFFICER
    call w3d_actor_begin_ranged_attack
    CHECK_IX8 W3D_ACTOR_STATE,W3D_STATE_OFC_SHOOT1,reason_state
    CHECK_IX8 W3D_ACTOR_TICCOUNT,6,reason_state

    ld a,3
    ld (test_detail),a
    call prepare_guard
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_MUTANT
    call w3d_actor_begin_ranged_attack
    CHECK_IX8 W3D_ACTOR_STATE,W3D_STATE_MUT_SHOOT1,reason_state
    CHECK_IX8 W3D_ACTOR_TICCOUNT,6,reason_state

    ld a,4
    ld (test_detail),a
    call prepare_guard
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_SS
    call w3d_actor_begin_ranged_attack
    CHECK_IX8 W3D_ACTOR_STATE,W3D_STATE_SS_SHOOT1,reason_state
    CHECK_IX8 W3D_ACTOR_TICCOUNT,20,reason_state

    ld a,5
    ld (test_detail),a
    call prepare_guard
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_DOG
    ld a,W3D_STATE_DOG_JUMP1
    call w3d_actor_new_state
    CHECK_IX8 W3D_ACTOR_STATE,W3D_STATE_DOG_JUMP1,reason_state
    CHECK_IX8 W3D_ACTOR_TICCOUNT,10,reason_state
    ret

; ---------------------------------------------------------------------------
; 3. 2,2,3 timing, multi-action overshoot, same-call chase think.
; ---------------------------------------------------------------------------

test_state_timing:
    ld a,phase_timing
    ld (test_phase),a

; Officer reaches shoot3 on the twelfth 2,2,3 frame: elapsed 28, countdown 8.
; Cached distance 36 makes its one muzzle action an unclamped guaranteed miss.
    ld a,1
    ld (test_detail),a
    call prepare_guard
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_OFFICER
    ld (ix+W3D_ACTOR_TILEX),60
    call w3d_actor_begin_ranged_attack
    ld a,82                          ; next native byte table[83] = 0
    ld (w3d_random_index),a
    ld hl,clock_12
    ld b,12
@officer_loop:
    ld a,(hl)
    inc hl
    push bc
    push hl
    call run_actor_with_tics
    pop hl
    pop bc
    djnz @officer_loop
    ld a,1
    call w3d_actor_pointer_from_id
    CHECK_IX8 W3D_ACTOR_STATE,W3D_STATE_OFC_SHOOT3,reason_state
    CHECK_IX8 W3D_ACTOR_TICCOUNT,8,reason_state
    CHECK_MEM8 w3d_random_index,83,reason_rng

; One 36-tic synthetic overshoot executes both mutant muzzle actions. Area is
; disconnected so actions consume no RNG; action-before-NEXT still advances.
    ld a,2
    ld (test_detail),a
    call prepare_guard
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_MUTANT
    call w3d_actor_begin_ranged_attack
    xor a
    ld (w3d_area_by_player+2),a
    ld a,42
    ld (w3d_random_index),a
    ld a,36
    call run_actor_with_tics
    ld a,1
    call w3d_actor_pointer_from_id
    CHECK_IX8 W3D_ACTOR_STATE,W3D_STATE_MUT_SHOOT4,reason_state
    CHECK_IX8 W3D_ACTOR_TICCOUNT,20,reason_state
    CHECK_MEM8 w3d_random_index,42,reason_rng

; Expiring guard shoot3 installs chase1 and runs its think in the same call.
; A wall blocks the attack probe while east-leg motion advances 0x400 units.
    ld a,3
    ld (test_detail),a
    call prepare_guard
    ld (ix+W3D_ACTOR_STATE),W3D_STATE_GRD_SHOOT3
    ld (ix+W3D_ACTOR_TICCOUNT),2
    ld (ix+W3D_ACTOR_DIR),W3D_DIR_EAST
    ld (ix+W3D_ACTOR_TILEX),21
    ld (ix+W3D_ACTOR_DISTANCE+0),0
    ld (ix+W3D_ACTOR_DISTANCE+1),0
    ld (ix+W3D_ACTOR_DISTANCE+2),1
    ld a,1
    ld (test_tilemap+1302),a
    ld hl,01e8000h
    ld de,0148000h
    call set_player_xy
    ld a,2
    call run_actor_with_tics
    ld a,1
    call w3d_actor_pointer_from_id
    CHECK_IX8 W3D_ACTOR_STATE,W3D_STATE_GRD_CHASE1,reason_state
    CHECK_IX8 W3D_ACTOR_TICCOUNT,10,reason_state
    CHECK_IX24 W3D_ACTOR_X,0,084h,014h,reason_pose
    ret

; ---------------------------------------------------------------------------
; 4. T_Shoot gates, strict chance, damage bands, SS reduction, RNG wrap.
; ---------------------------------------------------------------------------

test_shoot:
    ld a,phase_shoot
    ld (test_phase),a

; Disconnected area and blocked line both consume no RNG or health.
    ld a,1
    ld (test_detail),a
    call prepare_shoot_east2
    xor a
    ld (w3d_area_by_player+2),a
    ld a,42
    ld (w3d_random_index),a
    call w3d_actor_action_shoot
    CHECK_MEM8 w3d_random_index,42,reason_rng
    CHECK_MEM8 w3d_player_health,100,reason_health

    ld a,2
    ld (test_detail),a
    call prepare_guard
    ld a,1
    ld (test_tilemap+1302),a
    ld a,42
    ld (w3d_random_index),a
    call w3d_actor_action_shoot
    CHECK_MEM8 w3d_random_index,42,reason_rng

; Visible stationary distance 2 has chance 224: roll 224 misses exactly.
    ld a,3
    ld (test_detail),a
    call prepare_shoot_east2
    ld a,54                          ; table[55] = 224
    ld (w3d_random_index),a
    call w3d_actor_action_shoot
    CHECK_MEM8 w3d_random_index,55,reason_rng
    CHECK_MEM8 w3d_player_health,100,reason_health
    CHECK_MEM8 w3d_actor_combat_hitchance+0,224,reason_scalar
    CHECK_MEM8 w3d_actor_combat_hitchance+1,0,reason_scalar

; Roll 223 hits; next byte 239 at distance 2 deals 29.
    ld a,4
    ld (test_detail),a
    call prepare_shoot_east2
    ld a,168                         ; 223,239
    ld (w3d_random_index),a
    call w3d_actor_action_shoot
    CHECK_MEM8 w3d_random_index,170,reason_rng
    CHECK_MEM8 w3d_player_health,71,reason_health

; Exact running threshold changes chance to 128; roll 128 misses.
    ld a,5
    ld (test_detail),a
    call prepare_shoot_east2
    ld a,070h
    ld (w3d_player_thrustspeed+0),a
    ld a,017h
    ld (w3d_player_thrustspeed+1),a
    ld a,22                          ; table[23] = 128
    ld (w3d_random_index),a
    call w3d_actor_action_shoot
    CHECK_MEM8 w3d_random_index,23,reason_rng
    CHECK_MEM8 w3d_player_health,100,reason_health
    CHECK_MEM8 w3d_actor_combat_hitchance+0,128,reason_scalar

; Same cached tile: chance 256. Index 255 wraps to 0 then 1; damage 8>>2=2.
    ld a,6
    ld (test_detail),a
    call prepare_shoot_same_tile
    ld a,255
    ld (w3d_random_index),a
    call w3d_actor_action_shoot
    CHECK_MEM8 w3d_random_index,1,reason_rng
    CHECK_MEM8 w3d_player_health,98,reason_health
    CHECK_MEM8 w3d_actor_combat_hitchance+0,0,reason_scalar
    CHECK_MEM8 w3d_actor_combat_hitchance+1,1,reason_scalar

; Native 109,220 pair pins all three damage shifts.
    ld a,7
    ld (test_detail),a
    call prepare_shoot_east1
    ld a,1
    ld (w3d_random_index),a
    call w3d_actor_action_shoot
    CHECK_MEM8 w3d_player_health,45,reason_health       ; 220>>2 = 55

    ld a,8
    ld (test_detail),a
    call prepare_shoot_east2
    ld a,1
    ld (w3d_random_index),a
    call w3d_actor_action_shoot
    CHECK_MEM8 w3d_player_health,73,reason_health       ; 220>>3 = 27

    ld a,9
    ld (test_detail),a
    call prepare_shoot_east4
    ld a,1
    ld (w3d_random_index),a
    call w3d_actor_action_shoot
    CHECK_MEM8 w3d_player_health,87,reason_health       ; 220>>4 = 13

; SS raw distance 5 becomes effective 3; roll 200 then 50 gives damage 6.
    ld a,10
    ld (test_detail),a
    call prepare_shoot_east5
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_SS
    ld a,37
    ld (w3d_random_index),a
    call w3d_actor_action_shoot
    CHECK_MEM8 w3d_actor_combat_distance,3,reason_scalar
    CHECK_MEM8 w3d_actor_combat_hitchance+0,208,reason_scalar
    CHECK_MEM8 w3d_random_index,39,reason_rng
    CHECK_MEM8 w3d_player_health,94,reason_health
    ret

; ---------------------------------------------------------------------------
; 5. CPU TransformActor visibility replacement, including exact boundaries.
; ---------------------------------------------------------------------------

test_visibility:
    ld a,phase_visibility
    ld (test_phase),a

; Helper inputs are relative signed 8.8 X/Y in HL/DE and heading in BC.
    ld a,1
    ld (test_detail),a
    call prepare_guard
    ld hl,512
    ld de,0
    ld bc,0
    call set_projection_vector
    call w3d_actor_cpu_visible
    CHECK_A 1,reason_visibility
    CHECK_MEM8 w3d_actor_projection_nx+0,017h,reason_visibility ; 535 low
    CHECK_MEM8 w3d_actor_projection_nx+1,2,reason_visibility

    ld a,2
    ld (test_detail),a
    call prepare_guard
    ld hl,-512
    ld de,0
    ld bc,0
    call set_projection_vector
    call w3d_actor_cpu_visible
    CHECK_A 0,reason_visibility

; Near plane: forward 64 gives nx=87 rejected; 65 gives nx=88 accepted.
    ld a,3
    ld (test_detail),a
    call prepare_guard
    ld hl,64
    ld de,0
    ld bc,0
    call set_projection_vector
    call w3d_actor_cpu_visible
    CHECK_A 0,reason_visibility
    call prepare_guard
    ld hl,65
    ld de,0
    ld bc,0
    call set_projection_vector
    call w3d_actor_cpu_visible
    CHECK_A 1,reason_visibility
    CHECK_MEM8 w3d_actor_projection_nx+0,058h,reason_visibility

; Inclusive screen columns: left 0/right 255 accepted; -1/256 rejected.
    ld a,4
    ld (test_detail),a
    call prepare_guard
    ld hl,233
    ld de,-374
    ld bc,0
    call set_projection_vector
    call w3d_actor_cpu_visible
    CHECK_A 1,reason_visibility
    call prepare_guard
    ld hl,233
    ld de,-377
    ld bc,0
    call set_projection_vector
    call w3d_actor_cpu_visible
    CHECK_A 0,reason_visibility
    call prepare_guard
    ld hl,233
    ld de,377
    ld bc,0
    call set_projection_vector
    call w3d_actor_cpu_visible
    CHECK_A 1,reason_visibility
    call prepare_guard
    ld hl,233
    ld de,380
    ld bc,0
    call set_projection_vector
    call w3d_actor_cpu_visible
    CHECK_A 0,reason_visibility

; One-degree vector catches negative-product truncation toward zero.
    ld a,5
    ld (test_detail),a
    call prepare_guard
    ld hl,70
    ld de,-140
    ld bc,1
    call set_projection_vector
    call w3d_actor_cpu_visible
    CHECK_A 1,reason_visibility
    CHECK_MEM8 w3d_actor_projection_nx+0,94,reason_visibility

; A full 16.16 delta of -1 must borrow into reduced Q8=-1. The expected
; 30-degree projection remains visible with nx=123.
    ld a,6
    ld (test_detail),a
    call prepare_guard
    ld hl,00a8000h
    ld de,00a8000h
    call set_player_xy
    ld hl,00a7fffh
    ld (ix+W3D_ACTOR_X),hl
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld hl,009b800h
    ld (ix+W3D_ACTOR_Y),hl
    ld (ix+W3D_ACTOR_Y+3),a
    ld a,30
    ld (w3d_player_pose+8),a
    xor a
    ld (w3d_player_pose+9),a
    call w3d_actor_cpu_visible
    CHECK_A 1,reason_visibility
    CHECK_MEM8 w3d_actor_projection_rel_x+0,0ffh,reason_visibility
    CHECK_MEM8 w3d_actor_projection_rel_x+1,0ffh,reason_visibility
    CHECK_MEM8 w3d_actor_projection_nx+0,123,reason_visibility
    ret

; ---------------------------------------------------------------------------
; 6. Fixed-step thrustspeed producer and adjacent-byte ADL sentinel.
; ---------------------------------------------------------------------------

test_thrust:
    ld a,phase_thrust
    ld (test_phase),a
    ld a,0a5h
    ld (w3d_player_health),a

    xor a
    ld (w3d_controls),a
    call w3d_update_player_thrustspeed
    CHECK_MEM8 w3d_player_thrustspeed+0,0,reason_thrust
    CHECK_MEM8 w3d_player_thrustspeed+1,0,reason_thrust

    ld a,W3D_CONTROL_W
    ld (w3d_controls),a
    call w3d_update_player_thrustspeed
    CHECK_MEM8 w3d_player_thrustspeed+0,0,reason_thrust
    CHECK_MEM8 w3d_player_thrustspeed+1,010h,reason_thrust

    ld a,W3D_CONTROL_W|W3D_CONTROL_A
    ld (w3d_controls),a
    call w3d_update_player_thrustspeed
    CHECK_MEM8 w3d_player_thrustspeed+0,0,reason_thrust
    CHECK_MEM8 w3d_player_thrustspeed+1,020h,reason_thrust

    ld a,W3D_CONTROL_W|W3D_CONTROL_S|W3D_CONTROL_A
    ld (w3d_controls),a
    call w3d_update_player_thrustspeed
    CHECK_MEM8 w3d_player_thrustspeed+1,010h,reason_thrust

    ld a,W3D_CONTROL_W|W3D_CONTROL_S|W3D_CONTROL_A|W3D_CONTROL_D
    ld (w3d_controls),a
    call w3d_update_player_thrustspeed
    CHECK_MEM8 w3d_player_thrustspeed+1,0,reason_thrust
    CHECK_MEM8 w3d_player_health,0a5h,reason_thrust
    ret

; ---------------------------------------------------------------------------
; 7. Dog bite physical square, strict RNG and baby damage.
; ---------------------------------------------------------------------------

test_bite:
    ld a,phase_bite
    ld (test_phase),a

; Exact +2-tile/+2-tile corner is in range. Native 8,109 hits for damage 6.
    ld a,1
    ld (test_detail),a
    call prepare_dog
    ld hl,00c8000h
    ld (ix+W3D_ACTOR_X),hl
    ld (ix+W3D_ACTOR_Y),hl
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld (ix+W3D_ACTOR_Y+3),a
    ld a,0
    ld (w3d_random_index),a
    call w3d_actor_action_bite
    CHECK_MEM8 w3d_random_index,2,reason_rng
    CHECK_MEM8 w3d_player_health,94,reason_health

; One LSB past either axis is out of range and consumes no RNG.
    ld a,2
    ld (test_detail),a
    call prepare_dog
    ld hl,00c8001h
    ld (ix+W3D_ACTOR_X),hl
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld a,42
    ld (w3d_random_index),a
    call w3d_actor_action_bite
    CHECK_MEM8 w3d_random_index,42,reason_rng
    CHECK_MEM8 w3d_player_health,100,reason_health

; In range but roll 222 misses strictly after one draw.
    ld a,3
    ld (test_detail),a
    call prepare_dog
    ld a,3                           ; table[4] = 222
    ld (w3d_random_index),a
    call w3d_actor_action_bite
    CHECK_MEM8 w3d_random_index,4,reason_rng
    CHECK_MEM8 w3d_player_health,100,reason_health

; Baby quarters the six-point damage to one.
    ld a,4
    ld (test_detail),a
    call prepare_dog
    xor a
    ld (w3d_game_difficulty),a
    ld (w3d_random_index),a
    call w3d_actor_action_bite
    CHECK_MEM8 w3d_random_index,2,reason_rng
    CHECK_MEM8 w3d_player_health,99,reason_health
    ret

; ---------------------------------------------------------------------------
; 8. Health saturation, HUD/death latch and same-pass killer overwrite.
; ---------------------------------------------------------------------------

test_damage:
    ld a,phase_damage
    ld (test_phase),a
    call prepare_guard
    ld a,10
    ld (w3d_player_health),a
    ld a,12
    call w3d_take_player_damage
    CHECK_MEM8 w3d_player_health,0,reason_health
    CHECK_MEM8 w3d_player_dead,1,reason_death
    CHECK_MEM8 w3d_player_last_attacker,1,reason_death
    CHECK_MEM8 w3d_player_killer,1,reason_death
    ld a,(w3d_hud_dirty)
    and W3D_HUD_DIRTY_HEALTH
    CHECK_A W3D_HUD_DIRTY_HEALTH,reason_death
    CHECK_MEM8 w3d_pickup_scan_needed,1,reason_death

; Actor two's later zero-point hit still replaces killer while health is zero.
    ld a,2
    ld (w3d_current_actor_index),a
    xor a
    call w3d_take_player_damage
    CHECK_MEM8 w3d_player_last_attacker,2,reason_death
    CHECK_MEM8 w3d_player_killer,2,reason_death

; Baby direct damage: 25>>2 = 6.
    call prepare_guard
    xor a
    ld (w3d_game_difficulty),a
    ld a,25
    call w3d_take_player_damage
    CHECK_MEM8 w3d_player_health,94,reason_health
    ret

; ---------------------------------------------------------------------------
; Direct producer ABI: positioning, ordering, and false-event gates.
; ---------------------------------------------------------------------------

test_audio_events:
    ld a,phase_damage
    ld (test_phase),a

; Disconnected and wall-blocked T_Shoot actions do not enqueue anything.
    ld a,20
    ld (test_detail),a
    call prepare_shoot_east2
    xor a
    ld (w3d_area_by_player+2),a
    call w3d_actor_action_shoot
    CHECK_MEM8 test_audio_count+0,0,reason_audio

    call prepare_shoot_east2
    ld a,1
    ld (test_tilemap+651),a
    call w3d_actor_action_shoot
    CHECK_MEM8 test_audio_count+0,0,reason_audio

; A clear guard miss still emits positioned NAZIFIRESND with the actor ABI.
    call prepare_shoot_east2
    ld a,54                         ; table[55]=224: exact miss
    ld (w3d_random_index),a
    call w3d_actor_action_shoot
    CHECK_MEM8 test_audio_count+0,1,reason_audio
    CHECK_MEM8 test_audio_last_id,58,reason_audio
    CHECK_MEM8 test_audio_kind,1,reason_audio
    CHECK_MEM8 test_audio_arg_b,12,reason_audio
    CHECK_MEM8 test_audio_arg_c,10,reason_audio

; SS chooses its distinct shot id. A guard hit orders shot before player pain.
    call prepare_shoot_east2
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_SS
    ld a,4                          ; table[5]=241: miss chance 240 exactly
    ld (w3d_random_index),a
    call w3d_actor_action_shoot
    CHECK_MEM8 test_audio_count+0,1,reason_audio
    CHECK_MEM8 test_audio_last_id,60,reason_audio

    call prepare_shoot_east2
    ld a,1                          ; 109 hits, 220 damages
    ld (w3d_random_index),a
    call w3d_actor_action_shoot
    CHECK_MEM8 test_audio_count+0,2,reason_audio
    CHECK_MEM8 test_audio_previous_id,58,reason_audio
    CHECK_MEM8 test_audio_last_id,16,reason_audio
    CHECK_MEM8 test_audio_kind,0,reason_audio
    CHECK_MEM8 test_audio_arg_b,127,reason_audio
    CHECK_MEM8 test_audio_arg_c,0,reason_audio

; Every valid dog bite action barks, including an out-of-range no-RNG action;
; a wrong-class direct call fails closed and silent.
    call prepare_dog
    ld hl,00c8001h
    ld (ix+W3D_ACTOR_X),hl
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    call w3d_actor_action_bite
    CHECK_MEM8 test_audio_count+0,1,reason_audio
    CHECK_MEM8 test_audio_last_id,68,reason_audio
    CHECK_MEM8 test_audio_kind,1,reason_audio

    call prepare_guard
    call w3d_actor_action_bite
    CHECK_MEM8 test_audio_count+0,0,reason_audio

; Zero damage is silent; actual damage is full-gain unpositioned id 16.
    call prepare_guard
    xor a
    call w3d_take_player_damage
    CHECK_MEM8 test_audio_count+0,0,reason_audio
    ld a,1
    call w3d_take_player_damage
    CHECK_MEM8 test_audio_count+0,1,reason_audio
    CHECK_MEM8 test_audio_last_id,16,reason_audio
    CHECK_MEM8 test_audio_arg_b,127,reason_audio
    CHECK_MEM8 test_audio_arg_c,0,reason_audio

; A_DeathScream: guard consumes exactly one native RNG byte and uses parity;
; the fixed class sounds consume none. All are actor-positioned.
    call prepare_guard
    xor a
    ld (w3d_random_index),a          ; table[1]=8 -> guard variant 29
    call w3d_actor_action_death_scream
    CHECK_MEM8 w3d_random_index,1,reason_rng
    CHECK_MEM8 test_audio_last_id,29,reason_audio
    CHECK_MEM8 test_audio_kind,1,reason_audio

    call prepare_guard
    ld a,1                           ; table[2]=109 -> guard variant 22
    ld (w3d_random_index),a
    call w3d_actor_action_death_scream
    CHECK_MEM8 w3d_random_index,2,reason_rng
    CHECK_MEM8 test_audio_last_id,22,reason_audio

    call prepare_guard
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_OFFICER
    call w3d_actor_action_death_scream
    CHECK_MEM8 test_audio_last_id,67,reason_audio
    call prepare_guard
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_MUTANT
    call w3d_actor_action_death_scream
    CHECK_MEM8 test_audio_last_id,52,reason_audio
    call prepare_guard
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_SS
    call w3d_actor_action_death_scream
    CHECK_MEM8 test_audio_last_id,56,reason_audio
    call prepare_dog
    call w3d_actor_action_death_scream
    CHECK_MEM8 test_audio_last_id,10,reason_audio
    CHECK_MEM8 test_audio_count+0,1,reason_audio
    ret

; ---------------------------------------------------------------------------
; 9. Corrupt action/class/area plus live scheduler reservation/dirtiness.
; ---------------------------------------------------------------------------

test_containment_scheduler:
    ld a,phase_containment
    ld (test_phase),a

    ld a,1
    ld (test_detail),a
    call prepare_guard
    ld a,4
    call w3d_actor_dispatch_action
    ld a,0
    adc a,0
    CHECK_A 1,reason_fault

    ld a,2
    ld (test_detail),a
    call prepare_guard
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_DOG
    call w3d_actor_action_shoot
    ld a,0
    adc a,0
    CHECK_A 1,reason_fault

    ld a,3
    ld (test_detail),a
    call prepare_guard
    ld (ix+W3D_ACTOR_AREA),W3D_NUM_AREAS
    call w3d_actor_action_shoot
    ld a,0
    adc a,0
    CHECK_A 1,reason_fault

; Successful scheduler transition releases/reclaims its tile and dirties the
; changed attack shape.
    ld a,4
    ld (test_detail),a
    call prepare_guard
    ld (ix+W3D_ACTOR_STATE),W3D_STATE_GRD_SHOOT1
    ld (ix+W3D_ACTOR_TICCOUNT),1
    xor a
    ld (w3d_area_by_player+2),a
    call w3d_simulate_actors
    ld a,1
    call w3d_actor_pointer_from_id
    CHECK_IX8 W3D_ACTOR_STATE,W3D_STATE_GRD_SHOOT2,reason_state
    CHECK_IX8 W3D_ACTOR_TICCOUNT,19,reason_state
    CHECK_MEM8 w3d_actorat+cell_center,1,reason_reservation
    CHECK_MEM8 w3d_actor_dirty+1,W3D_ACTOR_DIRTY_SET,reason_reservation
    CHECK_MEM8 w3d_actor_fault_count,0,reason_fault
    CHECK_MEM8 w3d_actor_frame_tics,2,reason_clock

; Corrupt shoot action through the scheduler faults, frees and unreserves.
    ld a,5
    ld (test_detail),a
    call prepare_guard
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_DOG
    ld (ix+W3D_ACTOR_STATE),W3D_STATE_GRD_SHOOT2
    ld (ix+W3D_ACTOR_TICCOUNT),1
    call w3d_simulate_actors
    ld a,1
    call w3d_actor_pointer_from_id
    CHECK_IX8 W3D_ACTOR_ACTIVE,W3D_ACTOR_ACTIVE_FREE,reason_fault
    CHECK_MEM8 w3d_actor_fault_count,1,reason_fault
    CHECK_MEM8 w3d_actorat+cell_center,0,reason_reservation
    CHECK_MEM8 w3d_actor_dirty+1,W3D_ACTOR_DIRTY_REMOVE,reason_reservation
    ret

; ---------------------------------------------------------------------------
; 10. Hardware-compatible PRT1 timings; setup/assertions/I/O stay outside.
; ---------------------------------------------------------------------------

time_combat:
    ld a,phase_benchmark
    ld (test_phase),a

; Clear LOS, visible distance two. Fill deterministic test RNG with 255 so
; every chance-224 shot follows the stable one-draw miss path.
    ld a,1
    ld (test_detail),a
    call prepare_shoot_east2
    ld hl,w3d_random_table
    ld b,0
    ld a,255
@fill_rng:
    ld (hl),a
    inc hl
    djnz @fill_rng
    ld hl,timing_iterations
    ld (timing_left),hl
    call prt_start
@shoot_loop:
    call w3d_actor_action_shoot
    ld hl,(timing_left)
    dec hl
    ld (timing_left),hl
    ld a,h
    or l
    jr nz,@shoot_loop
    call prt_stop_shoot
    CHECK_MEM8 w3d_player_health,100,reason_health

; In-range dog bite with the same 255 stream follows stable one-draw misses.
    ld a,2
    ld (test_detail),a
    call prepare_dog
    ld hl,w3d_random_table
    ld b,0
    ld a,255
@fill_rng_bite:
    ld (hl),a
    inc hl
    djnz @fill_rng_bite
    ld hl,timing_iterations
    ld (timing_left),hl
    call prt_start
@bite_loop:
    call w3d_actor_action_bite
    ld hl,(timing_left)
    dec hl
    ld (timing_left),hl
    ld a,h
    or l
    jr nz,@bite_loop
    call prt_stop_bite
    CHECK_MEM8 w3d_player_health,100,reason_health
    ret

; ---------------------------------------------------------------------------
; Synthetic world/actor setup.
; ---------------------------------------------------------------------------

reset_combat_world:
    call test_audio_reset
    xor a
    ld hl,w3d_actors
    ld (hl),a
    ld de,w3d_actors+1
    ld bc,W3D_MAX_ACTORS*W3D_ACTOR_SIZE-1
    ldir
    ld hl,w3d_actorat
    ld (hl),a
    ld de,w3d_actorat+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,w3d_actor_dirty
    ld (hl),a
    ld de,w3d_actor_dirty+1
    ld bc,W3D_MAX_ACTORS-1
    ldir
    ld hl,test_tilemap
    ld (hl),a
    ld de,test_tilemap+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,test_area_map
    ld (hl),a
    ld de,test_area_map+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,test_static_bits
    ld (hl),a
    ld de,test_static_bits+1
    ld bc,511
    ldir
    ld hl,w3d_area_by_player
    ld (hl),a
    ld de,w3d_area_by_player+1
    ld bc,W3D_NUM_AREAS-1
    ldir
    ld hl,w3d_player_pose
    ld (hl),a
    ld de,w3d_player_pose+1
    ld bc,9
    ldir
    ld hl,w3d_hud_dirty
    ld (hl),a
    ld (w3d_pickup_scan_needed),a
    ld (w3d_player_thrustspeed+0),a
    ld (w3d_player_thrustspeed+1),a
    ld (w3d_player_dead),a
    ld (w3d_controls),a
    ld a,100
    ld (w3d_player_health),a
    ld a,W3D_SLOT_NONE
    ld (w3d_player_last_attacker),a
    ld (w3d_player_killer),a
    ld a,W3D_FIXTURE_DIFFICULTY
    ld (w3d_game_difficulty),a

    call w3d_initialize_actor_simulation
    ld hl,test_tilemap
    ld (w3d_map_ptr),hl
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_TILEMAP),hl
    ld hl,w3d_doors
    ld (w3d_doors_ptr),hl
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_DOORS),hl
    ld hl,w3d_area_by_player
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_AREAS),hl
    ld hl,test_area_map
    ld (w3d_area_map_ptr),hl
    ld hl,test_static_bits
    ld (w3d_static_blocking_ptr),hl
    ld a,W3D_SLOT_NONE
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
    ld a,1
    ld (w3d_actor_free_head),a
    xor a
    ld (w3d_actor_count),a
    ret

prepare_guard:
    call reset_combat_world
    ld a,1
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
    ld (w3d_actor_count),a
    ld a,2
    ld (w3d_actor_free_head),a
    ld a,1
    call w3d_actor_pointer_from_id
    ld hl,0148000h
    ld (ix+W3D_ACTOR_X),hl
    ld (ix+W3D_ACTOR_Y),hl
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld (ix+W3D_ACTOR_Y+3),a
    ld (ix+W3D_ACTOR_TILEX),20
    ld (ix+W3D_ACTOR_TILEY),20
    ld (ix+W3D_ACTOR_AREA),2
    ld (ix+W3D_ACTOR_DIR),W3D_DIR_NODIR
    ld (ix+W3D_ACTOR_ACTIVE),W3D_ACTOR_ACTIVE_YES
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_GUARD
    ld (ix+W3D_ACTOR_FLAGS),W3D_ACTOR_FLAG_SHOOTABLE
    ld (ix+W3D_ACTOR_STATE),W3D_STATE_GRD_CHASE1
    ld (ix+W3D_ACTOR_STATE+1),a
    ld (ix+W3D_ACTOR_TICCOUNT),a
    ld (ix+W3D_ACTOR_TICCOUNT+1),a
    ld (ix+W3D_ACTOR_DISTANCE+0),a
    ld (ix+W3D_ACTOR_DISTANCE+1),a
    ld (ix+W3D_ACTOR_DISTANCE+2),1
    ld (ix+W3D_ACTOR_DISTANCE+3),a
    ld (ix+W3D_ACTOR_SPEED+0),a
    ld (ix+W3D_ACTOR_SPEED+1),2
    ld (ix+W3D_ACTOR_SPEED+2),a
    ld (ix+W3D_ACTOR_SPEED+3),a
    ld (ix+W3D_ACTOR_NEXT),W3D_SLOT_NONE
    ld (ix+W3D_ACTOR_PREV),W3D_SLOT_NONE
    ld a,1
    ld (w3d_area_by_player+2),a
    ld (w3d_current_actor_index),a
    call w3d_actorat_claim
    ld hl,0188000h
    ld de,0148000h
    call set_player_xy
    ld a,180
    ld (w3d_player_pose+8),a
    xor a
    ld (w3d_player_pose+9),a
    ld a,1
    call w3d_actor_pointer_from_id
    ret

prepare_dog:
    call prepare_guard
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_DOG
    ld hl,00a8000h
    ld de,00a8000h
    call set_player_xy
    ld hl,00a8000h
    ld de,00a8000h
    ld (ix+W3D_ACTOR_X),hl
    ld (ix+W3D_ACTOR_Y),de
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld (ix+W3D_ACTOR_Y+3),a
    ret

prepare_shoot_east1:
    ld b,1
    jr prepare_shoot_east_n
prepare_shoot_east2:
    ld b,2
    jr prepare_shoot_east_n
prepare_shoot_east4:
    ld b,4
    jr prepare_shoot_east_n
prepare_shoot_east5:
    ld b,5
prepare_shoot_east_n:
    ld a,b
    ld (shoot_distance),a
    call prepare_guard
    ld hl,00a8000h
    ld de,00a8000h
    call set_player_xy
    xor a
    ld (w3d_player_pose+8),a
    ld (w3d_player_pose+9),a
    ld a,(shoot_distance)
    ld b,a
    ld a,10
    add a,b
    ld (ix+W3D_ACTOR_TILEX),a
    ld (ix+W3D_ACTOR_TILEY),10
    ld hl,00a8000h
    ld de,010000h
    ld a,(shoot_distance)
    ld b,a
@add_tile:
    add hl,de
    djnz @add_tile
    ld (ix+W3D_ACTOR_X),hl
    ld hl,00a8000h
    ld (ix+W3D_ACTOR_Y),hl
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld (ix+W3D_ACTOR_Y+3),a
    call w3d_prepare_actor_sight_context
    ret

prepare_shoot_same_tile:
    call prepare_guard
    ld hl,00a8000h
    ld de,00a8000h
    call set_player_xy
    xor a
    ld (w3d_player_pose+8),a
    ld (w3d_player_pose+9),a
    ld hl,00ac100h                  ; player + 65 Q8 units
    ld (ix+W3D_ACTOR_X),hl
    ld hl,00a8000h
    ld (ix+W3D_ACTOR_Y),hl
    ld (ix+W3D_ACTOR_X+3),a
    ld (ix+W3D_ACTOR_Y+3),a
    ld (ix+W3D_ACTOR_TILEX),10
    ld (ix+W3D_ACTOR_TILEY),10
    call w3d_prepare_actor_sight_context
    ret

; HL/DE are signed relative Q8 X/Y, BC=heading. Convert to full 16.16 around
; player base 10.5. Input words are preserved in scratch before arithmetic.
set_projection_vector:
    ld a,l
    ld (projection_rel_x+0),a
    ld a,h
    ld (projection_rel_x+1),a
    bit 7,h
    ld a,0
    jr z,@x_sign
    dec a
@x_sign:
    ld (projection_rel_x+2),a
    ex de,hl
    ld a,l
    ld (projection_rel_y+0),a
    ld a,h
    ld (projection_rel_y+1),a
    bit 7,h
    ld a,0
    jr z,@y_sign
    dec a
@y_sign:
    ld (projection_rel_y+2),a
    ld a,c
    ld (projection_heading+0),a
    ld a,b
    ld (projection_heading+1),a
    ld hl,00a8000h
    ld de,00a8000h
    call set_player_xy
    ld a,(projection_heading+0)
    ld (w3d_player_pose+8),a
    ld a,(projection_heading+1)
    ld (w3d_player_pose+9),a
    ld hl,(projection_rel_x)
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ld de,00a8000h
    add hl,de
    ld (ix+W3D_ACTOR_X),hl
    ld a,0
    adc a,0
    neg
    ld (ix+W3D_ACTOR_X+3),a
    ld hl,(projection_rel_y)
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ld de,00a8000h
    add hl,de
    ld (ix+W3D_ACTOR_Y),hl
    ld a,0
    adc a,0
    neg
    ld (ix+W3D_ACTOR_Y+3),a
    ret

; A=tics. Reacquire the production current actor around arbitrary callbacks.
run_actor_with_tics:
    ld (w3d_actor_frame_tics),a
    ld a,1
    ld (w3d_current_actor_index),a
    call w3d_actor_pointer_from_id
    jp w3d_actor_run_current

; HL=x low24, DE=y low24; test fixtures are positive and byte3 zero.
set_player_xy:
    ld (w3d_player_pose+0),hl
    ld (w3d_player_pose+4),de
    xor a
    ld (w3d_player_pose+3),a
    ld (w3d_player_pose+7),a
    jp w3d_prepare_actor_sight_context

; ---------------------------------------------------------------------------
; PRT1 stopwatch: 18.432 MHz / 256 / 72 = 1 kHz, hardware compatible.
; ---------------------------------------------------------------------------

prt_start:
    di
    ld hl,0
    ld (prt_irq_counter),hl
    ld hl,prt_reload_1ms
    out0 (TMR1_CTL+TMR_RES_LOW),l
    out0 (TMR1_CTL+TMR_RES_HIGH),h
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld a,PRT_ON
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ei
    ret

prt_stop_shoot:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_irq_counter)
    ld (result_timing_shoot),hl
    ei
    ret

prt_stop_bite:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_irq_counter)
    ld (result_timing_bite),hl
    ei
    ret

prt_irq_install:
    di
    ld hl,0
    ld a,($10c)
    ld l,a
    ld a,($10d)
    ld h,a
    inc hl
    ld hl,(hl)
    ld (prt_vector),hl
    ld a,(hl)
    ld (prt_saved_vector+0),a
    inc hl
    ld a,(hl)
    ld (prt_saved_vector+1),a
    inc hl
    ld a,(hl)
    ld (prt_saved_vector+2),a
    inc hl
    ld a,(hl)
    ld (prt_saved_vector+3),a
    ld hl,(prt_vector)
    ld (hl),0c3h
    inc hl
    ld de,prt_irq_handler
    ld (hl),de
    ei
    ret

prt_irq_restore:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_vector)
    ld a,(prt_saved_vector+0)
    ld (hl),a
    inc hl
    ld a,(prt_saved_vector+1)
    ld (hl),a
    inc hl
    ld a,(prt_saved_vector+2)
    ld (hl),a
    inc hl
    ld a,(prt_saved_vector+3)
    ld (hl),a
    ei
    ret

prt_irq_handler:
    di
    push af
    push hl
    in0 a,(TMR1_CTL+TMR_REG_CTL)
    ld hl,(prt_irq_counter)
    inc hl
    ld (prt_irq_counter),hl
    pop hl
    pop af
    ei
    reti.l

; ---------------------------------------------------------------------------
; Comparators and fixed mailbox.
; ---------------------------------------------------------------------------

; IX=actual, IY=expected, DE=count, C=reason.
assert_memory:
@loop:
    ld a,d
    or e
    ret z
    ld a,(ix+0)
    ld b,(iy+0)
    push de
    call assert_equal
    pop de
    inc ix
    inc iy
    dec.s de
    jr @loop

; A=actual, B=expected, C=reason.
assert_equal:
    ld (assert_actual),a
    ld a,b
    ld (assert_expected),a
    push hl
    ld hl,result_checks
    inc (hl)
    jr nz,@compare
    inc hl
    inc (hl)
@compare:
    ld a,(assert_actual)
    cp b
    jr z,@index
    ld hl,result_errors
    inc (hl)
    jr nz,@bucket
    inc hl
    inc (hl)
@bucket:
    ld a,(test_phase)
    or a
    jr z,@first
    dec a
    cp phase_count
    jr nc,@first
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,result_phase_errors
    add hl,de
    inc (hl)
@first:
    ld a,(result_first_reason)
    or a
    jr nz,@index
    ld a,(test_phase)
    ld (result_first_phase),a
    ld a,c
    ld (result_first_reason),a
    ld a,(assert_expected)
    ld (result_first_expected),a
    ld a,(assert_actual)
    ld (result_first_actual),a
    ld a,(test_detail)
    ld (result_first_detail),a
    ld a,(test_index+0)
    ld (result_first_index+0),a
    ld a,(test_index+1)
    ld (result_first_index+1),a
@index:
    ld hl,test_index
    inc (hl)
    jr nz,@return
    inc hl
    inc (hl)
@return:
    pop hl
    ret

write_result:
    ld hl,result_filename
    ld c,fa_write | fa_create_always
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

print_report:
    ld hl,report_banner
    call print_string
    ld a,(result_errors+0)
    ld b,a
    ld a,(result_errors+1)
    or b
    ld hl,report_pass
    jr z,@emit
    ld hl,report_fail
@emit:
    jp print_string

print_string:
    push bc
    ld bc,0
    ld a,0
    rst.lil 18h
    pop bc
    ret

; Normal-world fixture: death presentation is deliberately inactive.
w3d_death_fixed_step:
    or a
    ret
w3d_death_promote_lethal_latch:
    or a
    ret

; Required by wolf3d_motion.inc but not exercised by this fixture.
w3d_mark_render_submitted:
    ret
w3d_audio_begin_quantum:
    ret

; Direct capture doubles for the fixed audio producer ABI. Actor/tile helpers
; record their spatial arguments and otherwise deliberately share the same
; monotonically wrapping request log as unpositioned requests.
w3d_audio_request:
    ld d,a
    xor a
    ld (test_audio_kind),a
    ld a,b
    ld (test_audio_arg_b),a
    ld a,c
    ld (test_audio_arg_c),a
    ld a,d
    jp test_audio_record

w3d_audio_request_actor:
    ld d,a
    ld a,1
    ld (test_audio_kind),a
    ld a,(ix+W3D_ACTOR_TILEX)
    ld (test_audio_arg_b),a
    ld a,(ix+W3D_ACTOR_TILEY)
    ld (test_audio_arg_c),a
    ld a,d
    jp test_audio_record

w3d_audio_request_tile:
    ld d,a
    ld a,2
    ld (test_audio_kind),a
    ld a,b
    ld (test_audio_arg_b),a
    ld a,c
    ld (test_audio_arg_c),a
    ld a,d

test_audio_record:
    ld d,a
    ld a,(test_audio_last_id)
    ld (test_audio_previous_id),a
    ld a,d
    ld (test_audio_last_id),a
    ld hl,test_audio_count
    inc (hl)
    jr nz,@done
    inc hl
    inc (hl)
@done:
    or a
    ret

test_audio_reset:
    xor a
    ld hl,test_audio_begin
    ld (hl),a
    ld de,test_audio_begin+1
    ld bc,test_audio_end-test_audio_begin-1
    ldir
    ret

w3d_elapsed_ticks:
    dl 0
w3d_exit_requested:
    db 0

test_audio_begin:
test_audio_count:       dw 0
test_audio_previous_id: db 0
test_audio_last_id:     db 0
test_audio_kind:        db 0
test_audio_arg_b:       db 0
test_audio_arg_c:       db 0
test_audio_end:

; Literal source-derived attack records, ids 77..100.
expected_attack_states:
    dw 96
    db 0
    dw 20
    db 0,0,78
    dw 97
    db 0
    dw 20
    db 0,1,79
    dw 98
    db 0
    dw 20
    db 0,0,47
    dw 135
    db 0
    dw 10
    db 0,0,81
    dw 136
    db 0
    dw 10
    db 0,2,82
    dw 137
    db 0
    dw 10
    db 0,0,83
    dw 135
    db 0
    dw 10
    db 0,0,84
    dw 99
    db 0
    dw 10
    db 0,0,48
    dw 285
    db 0
    dw 6
    db 0,0,86
    dw 286
    db 0
    dw 20
    db 0,1,87
    dw 287
    db 0
    dw 10
    db 0,0,49
    dw 234
    db 0
    dw 6
    db 0,1,89
    dw 235
    db 0
    dw 20
    db 0,0,90
    dw 236
    db 0
    dw 10
    db 0,1,91
    dw 237
    db 0
    dw 20
    db 0,0,50
    dw 184
    db 0
    dw 20
    db 0,0,93
    dw 185
    db 0
    dw 20
    db 0,1,94
    dw 186
    db 0
    dw 10
    db 0,0,95
    dw 185
    db 0
    dw 10
    db 0,1,96
    dw 186
    db 0
    dw 10
    db 0,0,97
    dw 185
    db 0
    dw 10
    db 0,1,98
    dw 186
    db 0
    dw 10
    db 0,0,99
    dw 185
    db 0
    dw 10
    db 0,1,100
    dw 186
    db 0
    dw 10
    db 0,0,51
expected_attack_states_end:

clock_12:
    db 2,2,3,2,2,3,2,2,3,2,2,3

report_banner:      db 13,10,"Wolf3D combat direct regression",13,10,0
report_pass:        db "PASS",13,10,0
report_fail:        db "FAIL",13,10,0
result_filename:    asciz "combat_result.bin"

test_phase:         db 0
test_detail:        db 0
test_index:         dw 0
output_handle:      db 0
assert_expected:    db 0
assert_actual:      db 0
timing_left:        dl 0
shoot_distance:     db 0
projection_rel_x:   dl 0
projection_rel_y:   dl 0
projection_heading: dw 0
prt_vector:         dl 0
prt_saved_vector:   db 0,0,0,0
prt_irq_counter:    dl 0

result_data:
    db "W3CO"
result_checks:              dw 0
result_errors:              dw 0
result_first_phase:         db 0
result_first_reason:        db 0
result_first_expected:      db 0
result_first_actual:        db 0
result_first_detail:        db 0
result_first_index:         dw 0
result_phase_errors:        ds phase_count
result_timing_shoot:        dl 0
result_timing_bite:         dl 0
result_schema:              db 1
result_end:

test_tilemap:       ds W3D_MAP_BYTES
test_area_map:      ds W3D_MAP_BYTES
test_static_bits:   ds 512
