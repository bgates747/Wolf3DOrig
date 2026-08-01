; Direct real-eZ80 regression for production Wolf3D actor awareness.
;
; The fixture supplies only directed actor/world inputs and literal expected
; outputs.  Every awareness decision calls production labels from
; wolf3d_actor_sim.inc and wolf3d_sight.inc; no detection logic is copied here.

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

; PRT1: 18.432 MHz / 256 / 72 = 1 kHz.  This is the same hardware-compatible
; stopwatch and interrupt-vector discipline as the patrol/DDA regressions.
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

    include "wolf3d_audio_assets.inc"
    include "wolf3d_sight.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_actors.inc"
    include "wolf3d_areas.inc"
    include "wolf3d_actor_sim.inc"
    include "wolf3d_motion.inc"
    include "wolf3d_player_combat.inc"

phase_rng:              equ 1
phase_delay:            equ 2
phase_area:             equ 3
phase_visual:           equ 4
phase_noise:            equ 5
phase_ambush:           equ 6
phase_countdown:        equ 7
phase_first_sighting:   equ 8
phase_containment:      equ 9
phase_noise_pass:       equ 10
phase_timing:           equ 11
phase_count:            equ 11

reason_scalar:          equ 1
reason_rng:             equ 2
reason_temp2:           equ 3
reason_flags:           equ 4
reason_state_tics:      equ 5
reason_speed:           equ 6
reason_distance:        equ 7
reason_pose_active:     equ 8
reason_containment:     equ 9
reason_noise:           equ 10
reason_clock:           equ 11
reason_actor_record:    equ 12
reason_audio:           equ 13

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
    call prt_irq_install
    call test_rng_contract
    call test_reaction_delays
    call test_area_gates
    call test_quiet_visual_paths
    call test_noise_bypass
    call test_ambush_paths
    call test_countdown_cadence
    call test_first_sighting_all_classes
    call test_corrupt_containment
    call test_noise_lifetime_whole_pass
    call time_quiet_visual_acquisition
    call prt_irq_restore
    call write_result
    call print_report
    ret

; ---------------------------------------------------------------------------
; Case 1: exact US_RndT continuation and uint8 wrap.
; ---------------------------------------------------------------------------

test_rng_contract:
    ld a,phase_rng
    ld (test_phase),a
    ld a,1
    ld (test_detail),a
    call reset_awareness_world

    ld a,(w3d_random_index)
    ld b,W3D_FIXTURE_RND_INDEX_AFTER_SPAWN
    ld c,reason_rng
    call assert_equal

; Spawn-time fixture consumption ends at index 6.  US_RndT increments first:
; table[7]=107, table[8]=75.
    call w3d_random_byte
    ld b,107
    ld c,reason_rng
    call assert_equal
    ld a,(w3d_random_index)
    ld b,7
    ld c,reason_rng
    call assert_equal
    call w3d_random_byte
    ld b,75
    ld c,reason_rng
    call assert_equal
    ld a,(w3d_random_index)
    ld b,8
    ld c,reason_rng
    call assert_equal

; Index 254 advances to table[255]=249, then wraps to table[0]=0.
    ld a,254
    ld (w3d_random_index),a
    call w3d_random_byte
    ld b,249
    ld c,reason_rng
    call assert_equal
    ld a,(w3d_random_index)
    ld b,255
    ld c,reason_rng
    call assert_equal
    call w3d_random_byte
    ld b,0
    ld c,reason_rng
    call assert_equal
    ld a,(w3d_random_index)
    ld b,0
    ld c,reason_rng
    jp assert_equal

; ---------------------------------------------------------------------------
; Case 2: all five class formulas and officer's no-consume exception.
; ---------------------------------------------------------------------------

test_reaction_delays:
    ld a,phase_delay
    ld (test_phase),a
    call prepare_one_actor

; Setting the index to 157 makes the next byte table[158]=255.
    ld a,1
    ld (test_detail),a
    ld a,W3D_CLASS_GUARD
    ld (ix+W3D_ACTOR_CLASS),a
    ld a,157
    ld (w3d_random_index),a
    call w3d_actor_reaction_delay
    ld b,64
    ld c,reason_scalar
    call assert_equal
    ld a,(w3d_random_index)
    ld b,158
    ld c,reason_rng
    call assert_equal

    ld a,2
    ld (test_detail),a
    ld a,W3D_CLASS_OFFICER
    ld (ix+W3D_ACTOR_CLASS),a
    ld a,157
    ld (w3d_random_index),a
    call w3d_actor_reaction_delay
    ld b,2
    ld c,reason_scalar
    call assert_equal
    ld a,(w3d_random_index)
    ld b,157                         ; fixed delay consumed no byte
    ld c,reason_rng
    call assert_equal

    ld a,3
    ld (test_detail),a
    ld a,W3D_CLASS_MUTANT
    ld (ix+W3D_ACTOR_CLASS),a
    ld a,157
    ld (w3d_random_index),a
    call w3d_actor_reaction_delay
    ld b,43
    ld c,reason_scalar
    call assert_equal
    ld a,(w3d_random_index)
    ld b,158
    ld c,reason_rng
    call assert_equal

    ld a,4
    ld (test_detail),a
    ld a,W3D_CLASS_SS
    ld (ix+W3D_ACTOR_CLASS),a
    ld a,157
    ld (w3d_random_index),a
    call w3d_actor_reaction_delay
    ld b,43
    ld c,reason_scalar
    call assert_equal
    ld a,(w3d_random_index)
    ld b,158
    ld c,reason_rng
    call assert_equal

    ld a,5
    ld (test_detail),a
    ld a,W3D_CLASS_DOG
    ld (ix+W3D_ACTOR_CLASS),a
    ld a,157
    ld (w3d_random_index),a
    call w3d_actor_reaction_delay
    ld b,32
    ld c,reason_scalar
    call assert_equal
    ld a,(w3d_random_index)
    ld b,158
    ld c,reason_rng
    jp assert_equal

; ---------------------------------------------------------------------------
; Case 3: noise acquisition still requires a valid connected area.
; ---------------------------------------------------------------------------

test_area_gates:
    ld a,phase_area
    ld (test_phase),a

; Connected area 2 starts the shortest guard delay from table[83]=0.
    ld a,1
    ld (test_detail),a
    call prepare_one_actor
    ld a,82
    ld (w3d_random_index),a
    call w3d_mark_player_noise
    call w3d_actor_sight_player
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,1
    ld c,reason_temp2
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+1)
    ld b,0
    ld c,reason_temp2
    call assert_equal
    ld a,(w3d_random_index)
    ld b,83
    ld c,reason_rng
    call assert_equal

; Disconnected, area 37, and 0xff all reject before RNG consumption.
    ld a,2
    ld (test_detail),a
    call prepare_one_actor
    xor a
    ld (w3d_area_by_player+2),a
    call w3d_mark_player_noise
    call check_unaware_no_rng

    ld a,3
    ld (test_detail),a
    call prepare_one_actor
    ld a,W3D_NUM_AREAS
    ld (ix+W3D_ACTOR_AREA),a
    call w3d_mark_player_noise
    call check_unaware_no_rng

    ld a,4
    ld (test_detail),a
    call prepare_one_actor
    ld a,W3D_SLOT_NONE
    ld (ix+W3D_ACTOR_AREA),a
    call w3d_mark_player_noise
    jp check_unaware_no_rng

check_unaware_no_rng:
    ld a,82
    ld (w3d_random_index),a
    call w3d_actor_sight_player
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,0
    ld c,reason_temp2
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+1)
    ld b,0
    ld c,reason_temp2
    call assert_equal
    ld a,(w3d_random_index)
    ld b,82
    ld c,reason_rng
    jp assert_equal

; ---------------------------------------------------------------------------
; Case 4: quiet visual clear/blocked/facing and strict proximity boundary.
; ---------------------------------------------------------------------------

test_quiet_visual_paths:
    ld a,phase_visual
    ld (test_phase),a
    call prepare_one_actor
    ld a,W3D_CLASS_OFFICER
    ld (ix+W3D_ACTOR_CLASS),a

; Clear four-tile east-facing trace acquires and seeds fixed delay two.
    ld a,1
    ld (test_detail),a
    call clear_actor_temp2
    call set_player_ahead
    call w3d_prepare_actor_sight_context
    call w3d_actor_sight_player
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,2
    ld c,reason_temp2
    call assert_equal

; Wall at (22,20) blocks the same otherwise-valid trace.
    ld a,2
    ld (test_detail),a
    call clear_actor_temp2
    ld a,1
    ld (test_tilemap+1302),a
    call w3d_actor_sight_player
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,0
    ld c,reason_temp2
    call assert_equal
    xor a
    ld (test_tilemap+1302),a

; A player four tiles west is outside an east-facing half-plane.
    ld a,3
    ld (test_detail),a
    call clear_actor_temp2
    call set_player_behind
    call w3d_prepare_actor_sight_context
    call w3d_actor_sight_player
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,0
    ld c,reason_temp2
    call assert_equal

; One 16.16 LSB inside 1.5 tiles is automatic despite facing.  The exact
; boundary is not automatic and therefore fails the same facing gate.
    ld a,4
    ld (test_detail),a
    call clear_actor_temp2
    ld hl,0130001h
    ld de,0148000h
    call set_player_xy
    call w3d_prepare_actor_sight_context
    call w3d_actor_sight_player
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,2
    ld c,reason_temp2
    call assert_equal

    ld a,5
    ld (test_detail),a
    call clear_actor_temp2
    ld hl,0130000h
    ld de,0148000h
    call set_player_xy
    call w3d_prepare_actor_sight_context
    call w3d_actor_sight_player
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,0
    ld c,reason_temp2
    jp assert_equal

; ---------------------------------------------------------------------------
; Case 5: ordinary noise bypasses facing and the complete wall/door trace.
; ---------------------------------------------------------------------------

test_noise_bypass:
    ld a,phase_noise
    ld (test_phase),a
    ld a,1
    ld (test_detail),a
    call prepare_one_actor
    ld a,W3D_CLASS_OFFICER
    ld (ix+W3D_ACTOR_CLASS),a
    call set_player_behind
    ld a,1
    ld (test_tilemap+1298),a          ; wall (18,20) blocks westward trace
    call w3d_mark_player_noise
    call w3d_prepare_actor_sight_context

; The wrapper owns noise; CheckSight must always receive false here.
    ld a,(w3d_actor_sight_context+W3D_SIGHT_CTX_MADENOISE)
    ld b,0
    ld c,reason_noise
    call assert_equal
    call w3d_actor_sight_player
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,2
    ld c,reason_temp2
    call assert_equal
    ld a,(ix+W3D_ACTOR_FLAGS)
    ld b,W3D_ACTOR_FLAG_SHOOTABLE
    ld c,reason_flags
    jp assert_equal

; ---------------------------------------------------------------------------
; Case 6: ambush ignores noise, requires visual sight, and clears on acquire.
; ---------------------------------------------------------------------------

test_ambush_paths:
    ld a,phase_ambush
    ld (test_phase),a
    call prepare_one_actor
    ld a,W3D_CLASS_OFFICER
    ld (ix+W3D_ACTOR_CLASS),a
    ld a,W3D_ACTOR_FLAG_SHOOTABLE|W3D_ACTOR_FLAG_AMBUSH
    ld (ix+W3D_ACTOR_FLAGS),a

; Noise cannot wake an ambush actor facing away through a wall.
    ld a,1
    ld (test_detail),a
    call set_player_behind
    ld a,1
    ld (test_tilemap+1298),a
    call w3d_mark_player_noise
    call w3d_prepare_actor_sight_context
    call w3d_actor_sight_player
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,0
    ld c,reason_temp2
    call assert_equal
    ld a,(ix+W3D_ACTOR_FLAGS)
    ld b,W3D_ACTOR_FLAG_SHOOTABLE|W3D_ACTOR_FLAG_AMBUSH
    ld c,reason_flags
    call assert_equal

; A later clear visual trace seeds the delay and clears AMBUSH immediately.
    ld a,2
    ld (test_detail),a
    xor a
    ld (test_tilemap+1298),a
    call set_player_ahead
    call w3d_prepare_actor_sight_context
    call w3d_actor_sight_player
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,2
    ld c,reason_temp2
    call assert_equal
    ld a,(ix+W3D_ACTOR_FLAGS)
    ld b,W3D_ACTOR_FLAG_SHOOTABLE
    ld c,reason_flags
    jp assert_equal

; ---------------------------------------------------------------------------
; Case 7: pending reaction consumes the exact shared 2,2,3 cadence.
; ---------------------------------------------------------------------------

test_countdown_cadence:
    ld a,phase_countdown
    ld (test_phase),a
    ld a,1
    ld (test_detail),a
    call prepare_one_actor
    ld a,7
    ld (ix+W3D_ACTOR_TEMP2+0),a
    xor a
    ld (ix+W3D_ACTOR_TEMP2+1),a

    call w3d_actor_advance_frame_tics
    ld a,(w3d_actor_frame_tics)
    ld b,2
    ld c,reason_clock
    call assert_equal
    call w3d_actor_sight_player
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,5
    ld c,reason_temp2
    call assert_equal

    call w3d_actor_advance_frame_tics
    ld a,(w3d_actor_frame_tics)
    ld b,2
    ld c,reason_clock
    call assert_equal
    call w3d_actor_sight_player
    ld b,0
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,3
    ld c,reason_temp2
    call assert_equal

; Once pending, a disconnect cannot cancel the reaction.
    xor a
    ld (w3d_area_by_player+2),a
    call w3d_actor_advance_frame_tics
    ld a,(w3d_actor_frame_tics)
    ld b,3
    ld c,reason_clock
    call assert_equal
    call w3d_actor_sight_player
    ld b,1
    ld c,reason_scalar
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,0
    ld c,reason_temp2
    call assert_equal
    ld a,(w3d_actor_tic_phase)
    ld b,0
    ld c,reason_clock
    call assert_equal
    ld a,(w3d_random_index)
    ld b,W3D_FIXTURE_RND_INDEX_AFTER_SPAWN
    ld c,reason_rng
    jp assert_equal

; ---------------------------------------------------------------------------
; Case 8: literal FirstSighting effects for all five ordinary classes.
; ---------------------------------------------------------------------------

fs_class:          equ 0
fs_state:          equ 1
fs_speed_in:       equ 2
fs_speed_out:      equ 4
fs_distance_in:    equ 6
fs_distance_out:   equ 10
fs_active:         equ 14
fs_size:           equ 15

test_first_sighting_all_classes:
    ld a,phase_first_sighting
    ld (test_phase),a
    ld hl,first_sighting_cases
    ld (first_sighting_ptr),hl
    ld a,1
    ld (test_detail),a
@loop:
    call prepare_one_actor
    ld hl,(first_sighting_ptr)
    push hl
    pop iy

    ld a,(iy+fs_class)
    ld (expected_class),a
    ld (ix+W3D_ACTOR_CLASS),a
    ld a,(iy+fs_state)
    ld (expected_state),a
    ld a,(iy+fs_speed_in+0)
    ld (ix+W3D_ACTOR_SPEED+0),a
    ld a,(iy+fs_speed_in+1)
    ld (ix+W3D_ACTOR_SPEED+1),a
    xor a
    ld (ix+W3D_ACTOR_SPEED+2),a
    ld (ix+W3D_ACTOR_SPEED+3),a
    ld a,(iy+fs_speed_out+0)
    ld (expected_speed+0),a
    ld a,(iy+fs_speed_out+1)
    ld (expected_speed+1),a
    ld a,(iy+fs_active)
    ld (ix+W3D_ACTOR_ACTIVE),a

    ld a,(iy+fs_distance_in+0)
    ld (ix+W3D_ACTOR_DISTANCE+0),a
    ld a,(iy+fs_distance_in+1)
    ld (ix+W3D_ACTOR_DISTANCE+1),a
    ld a,(iy+fs_distance_in+2)
    ld (ix+W3D_ACTOR_DISTANCE+2),a
    ld a,(iy+fs_distance_in+3)
    ld (ix+W3D_ACTOR_DISTANCE+3),a
    ld a,(iy+fs_distance_out+0)
    ld (expected_distance+0),a
    ld a,(iy+fs_distance_out+1)
    ld (expected_distance+1),a
    ld a,(iy+fs_distance_out+2)
    ld (expected_distance+2),a
    ld a,(iy+fs_distance_out+3)
    ld (expected_distance+3),a

; X/Y, cached tile, area, direction, and ACTIVE are one contiguous 13-byte
; prefix.  FirstSighting must leave every byte unchanged.
    push ix
    pop hl
    ld de,pose_before
    ld bc,13
    ldir

    call w3d_actor_first_sighting
    ld (last_return),a
    ld a,1
    call w3d_actor_pointer_from_id

    ld a,(last_return)
    ld b,1
    ld c,reason_scalar
    call assert_equal
    ld a,(expected_state)
    ld b,a
    ld a,(ix+W3D_ACTOR_STATE+0)
    ld c,reason_state_tics
    call assert_equal
    ld a,(ix+W3D_ACTOR_STATE+1)
    ld b,0
    ld c,reason_state_tics
    call assert_equal
    ld a,(ix+W3D_ACTOR_TICCOUNT+0)
    ld b,10
    ld c,reason_state_tics
    call assert_equal
    ld a,(ix+W3D_ACTOR_TICCOUNT+1)
    ld b,0
    ld c,reason_state_tics
    call assert_equal

    ld a,(expected_speed+0)
    ld b,a
    ld a,(ix+W3D_ACTOR_SPEED+0)
    ld c,reason_speed
    call assert_equal
    ld a,(expected_speed+1)
    ld b,a
    ld a,(ix+W3D_ACTOR_SPEED+1)
    ld c,reason_speed
    call assert_equal
    ld a,(ix+W3D_ACTOR_SPEED+2)
    ld b,0
    ld c,reason_speed
    call assert_equal
    ld a,(ix+W3D_ACTOR_SPEED+3)
    ld b,0
    ld c,reason_speed
    call assert_equal

    ld a,(ix+W3D_ACTOR_FLAGS)
    ld b,W3D_ACTOR_FLAG_SHOOTABLE|W3D_ACTOR_FLAG_ATTACKMODE|W3D_ACTOR_FLAG_FIRSTATTACK
    ld c,reason_flags
    call assert_equal

    lea iy,ix+W3D_ACTOR_DISTANCE
    ld ix,expected_distance
    ld de,4
    ld c,reason_distance
    call assert_memory_reverse

    ld a,1
    call w3d_actor_pointer_from_id
    ld iy,pose_before
    ld de,13
    ld c,reason_pose_active
    call assert_memory

    ld a,1
    call w3d_actor_pointer_from_id
    ld a,(expected_class)
    ld b,a
    ld a,(ix+W3D_ACTOR_CLASS)
    ld c,reason_pose_active
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,0
    ld c,reason_temp2
    call assert_equal
    ld a,(ix+W3D_ACTOR_TEMP2+1)
    ld b,0
    ld c,reason_temp2
    call assert_equal

; Successful FirstSighting emits one positioned class sound, except for the
; source-silent mutant case.
    ld a,(expected_class)
    cp W3D_CLASS_MUTANT
    jr z,@audio_silent
    ld b,21                         ; guard HALTSND
    cp W3D_CLASS_GUARD
    jr z,@audio_id_ready
    ld b,66                         ; officer SPIONSND
    cp W3D_CLASS_OFFICER
    jr z,@audio_id_ready
    ld b,51                         ; SS SCHUTZADSND
    cp W3D_CLASS_SS
    jr z,@audio_id_ready
    ld b,41                         ; dog DOGBARKSND
@audio_id_ready:
    ld a,(test_audio_count)
    ld c,reason_audio
    push bc
    ld b,1
    call assert_equal
    pop bc
    ld a,(test_audio_last_id)
    call assert_equal
    ld a,(test_audio_kind)
    ld b,1
    ld c,reason_audio
    call assert_equal
    ld a,(test_audio_arg_b)
    ld b,20
    call assert_equal
    ld a,(test_audio_arg_c)
    ld b,20
    call assert_equal
    jr @audio_done
@audio_silent:
    ld a,(test_audio_count)
    ld b,0
    ld c,reason_audio
    call assert_equal
@audio_done:

    ld hl,(first_sighting_ptr)
    ld de,fs_size
    add hl,de
    ld (first_sighting_ptr),hl
    ld a,(test_detail)
    inc a
    ld (test_detail),a
    cp 6
    jp c,@loop
    ret

; ---------------------------------------------------------------------------
; Case 9: bad class/attack-mode calls fail closed; full runner removes them.
; ---------------------------------------------------------------------------

test_corrupt_containment:
    ld a,phase_containment
    ld (test_phase),a

; Direct unsupported class: FF and a byte-identical record, no RNG draw.
    ld a,1
    ld (test_detail),a
    call prepare_one_actor
    ld a,99
    ld (ix+W3D_ACTOR_CLASS),a
    call w3d_mark_player_noise
    push ix
    pop hl
    ld de,actor_before
    ld bc,W3D_ACTOR_SIZE
    ldir
    call w3d_actor_sight_player
    ld (last_return),a
    ld a,(last_return)
    ld b,0ffh
    ld c,reason_containment
    call assert_equal
    ld a,1
    call w3d_actor_pointer_from_id
    ld iy,actor_before
    ld de,W3D_ACTOR_SIZE
    ld c,reason_actor_record
    call assert_memory
    ld a,(w3d_random_index)
    ld b,W3D_FIXTURE_RND_INDEX_AFTER_SPAWN
    ld c,reason_rng
    call assert_equal

; Direct attack-mode misuse is equally non-mutating.
    ld a,2
    ld (test_detail),a
    call prepare_one_actor
    ld a,W3D_ACTOR_FLAG_SHOOTABLE|W3D_ACTOR_FLAG_ATTACKMODE
    ld (ix+W3D_ACTOR_FLAGS),a
    push ix
    pop hl
    ld de,actor_before
    ld bc,W3D_ACTOR_SIZE
    ldir
    call w3d_actor_sight_player
    ld (last_return),a
    ld a,(last_return)
    ld b,0ffh
    ld c,reason_containment
    call assert_equal
    ld a,1
    call w3d_actor_pointer_from_id
    ld iy,actor_before
    ld de,W3D_ACTOR_SIZE
    ld c,reason_actor_record
    call assert_memory

; Through DoActor, either corrupt condition increments the fault count and
; removes the actor instead of freezing the foreground loop.
    ld a,3
    ld (test_detail),a
    call prepare_one_actor
    ld a,99
    ld (ix+W3D_ACTOR_CLASS),a
    call w3d_mark_player_noise
    call w3d_simulate_actors
    call check_faulted_actor_removed

    ld a,4
    ld (test_detail),a
    call prepare_one_actor
    ld a,W3D_ACTOR_FLAG_SHOOTABLE|W3D_ACTOR_FLAG_ATTACKMODE
    ld (ix+W3D_ACTOR_FLAGS),a
    call w3d_simulate_actors
    jp check_faulted_actor_removed

check_faulted_actor_removed:
    ld a,(w3d_actor_fault_count+0)
    ld b,1
    ld c,reason_containment
    call assert_equal
    ld a,(w3d_actor_fault_count+1)
    ld b,0
    ld c,reason_containment
    call assert_equal
    ld a,(w3d_actor_count)
    ld b,0
    ld c,reason_containment
    call assert_equal
    ld a,(w3d_actor_live_head)
    ld b,W3D_SLOT_NONE
    ld c,reason_containment
    call assert_equal
    ld a,(w3d_actor_live_tail)
    ld b,W3D_SLOT_NONE
    ld c,reason_containment
    call assert_equal
    ld a,(w3d_actor_free_head)
    ld b,1
    ld c,reason_containment
    call assert_equal
    ld a,(w3d_actor_dirty+1)
    ld b,W3D_ACTOR_DIRTY_REMOVE
    ld c,reason_containment
    call assert_equal
    ld a,(w3d_player_made_noise)
    ld b,0
    ld c,reason_noise
    jp assert_equal

; ---------------------------------------------------------------------------
; Case 10: a noise byte remains set for every actor, then clears once.
; ---------------------------------------------------------------------------

test_noise_lifetime_whole_pass:
    ld a,phase_noise_pass
    ld (test_phase),a
    ld a,1
    ld (test_detail),a
    call prepare_two_officers
    call set_player_behind
    ld a,1
    ld (test_tilemap+1298),a
    call w3d_mark_player_noise
    call w3d_simulate_actors

; Both east-facing actors are west of neither?  The player is west of both and
; a wall blocks the trace, so temp2=2 on both proves the same noise event was
; visible throughout the complete list pass.
    ld a,1
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,2
    ld c,reason_temp2
    call assert_equal
    ld a,2
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,2
    ld c,reason_temp2
    call assert_equal
    ld a,(w3d_player_made_noise)
    ld b,0
    ld c,reason_noise
    call assert_equal
    ld a,(w3d_actor_sight_context+W3D_SIGHT_CTX_MADENOISE)
    ld b,0
    ld c,reason_noise
    call assert_equal
    ld a,(w3d_actor_count)
    ld b,2
    ld c,reason_containment
    call assert_equal
    ld a,(w3d_actor_tic_phase)
    ld b,1
    ld c,reason_clock
    jp assert_equal

; ---------------------------------------------------------------------------
; Case 11: PRT1 budget for 10,000 connected quiet visual acquisitions.
; ---------------------------------------------------------------------------

time_quiet_visual_acquisition:
    ld a,phase_timing
    ld (test_phase),a
    ld a,1
    ld (test_detail),a
    call prepare_one_actor
    ld a,W3D_CLASS_OFFICER
    ld (ix+W3D_ACTOR_CLASS),a
    call set_player_ahead
    call w3d_prepare_actor_sight_context
    ld hl,timing_iterations
    ld (timing_left),hl
    call prt_start
@loop:
    ld a,1
    call w3d_actor_pointer_from_id
    xor a
    ld (ix+W3D_ACTOR_TEMP2+0),a
    ld (ix+W3D_ACTOR_TEMP2+1),a
    call w3d_actor_sight_player
    ld hl,(timing_left)
    dec hl
    ld (timing_left),hl
    ld a,h
    or l
    jr nz,@loop
    call prt_stop

    ld a,1
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_TEMP2+0)
    ld b,2
    ld c,reason_temp2
    call assert_equal
    ld a,(w3d_player_made_noise)
    ld b,0
    ld c,reason_noise
    jp assert_equal

; ---------------------------------------------------------------------------
; Synthetic world/actor setup.
; ---------------------------------------------------------------------------

reset_awareness_world:
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
    ld hl,w3d_doors
    ld (hl),a
    ld de,w3d_doors+1
    ld bc,W3D_FIXTURE_DOOR_COUNT*W3D_DOOR_SIZE-1
    ldir
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
    ld hl,w3d_area_by_player
    ld (hl),a
    ld de,w3d_area_by_player+1
    ld bc,W3D_NUM_AREAS-1
    ldir

    ld a,0ffh
    ld hl,test_path_directions
    ld (hl),a
    ld de,test_path_directions+1
    ld bc,W3D_MAP_BYTES-1
    ldir

; Conservative solid outer ring; all directed sight segments stay inside it.
    xor a
    ld hl,test_tilemap
    ld iy,test_tilemap+4032
    ld b,64
@horizontal:
    ld (hl),1
    ld (iy+0),1
    inc hl
    inc iy
    djnz @horizontal
    ld iy,test_tilemap+64
    ld b,62
@vertical:
    ld (iy+0),1
    ld (iy+63),1
    lea iy,iy+64
    djnz @vertical

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
    ld hl,test_path_directions
    ld (w3d_path_directions_ptr),hl
    ld hl,test_static_bits
    ld (w3d_static_blocking_ptr),hl

    ld a,W3D_SLOT_NONE
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
    ld a,1
    ld (w3d_actor_free_head),a
    xor a
    ld (w3d_actor_count),a
    ld (w3d_world_dirty),a
    ld (w3d_player_dirty),a
    ld (w3d_area_fault_count+0),a
    ld (w3d_area_fault_count+1),a
    call set_player_ahead
    jp w3d_prepare_actor_sight_context

prepare_one_actor:
    call reset_awareness_world
    ld a,1
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
    ld (w3d_actor_count),a
    ld a,2
    ld (w3d_actor_free_head),a
    ld a,1
    call w3d_actor_pointer_from_id

; Center (20.5,20.5), stable cached tile (20,20).
    ld hl,0148000h
    ld (ix+W3D_ACTOR_X),hl
    ld (ix+W3D_ACTOR_Y),hl
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld (ix+W3D_ACTOR_Y+3),a
    ld a,20
    ld (ix+W3D_ACTOR_TILEX),a
    ld (ix+W3D_ACTOR_TILEY),a
    ld a,2
    ld (ix+W3D_ACTOR_AREA),a
    ld (w3d_area_by_player+2),a       ; any nonzero byte is connected
    ld a,W3D_DIR_EAST
    ld (ix+W3D_ACTOR_DIR),a
    ld a,W3D_ACTOR_ACTIVE_YES
    ld (ix+W3D_ACTOR_ACTIVE),a
    ld a,W3D_CLASS_GUARD
    ld (ix+W3D_ACTOR_CLASS),a
    ld a,W3D_ACTOR_FLAG_SHOOTABLE
    ld (ix+W3D_ACTOR_FLAGS),a
    ld a,W3D_STATE_GRD_STAND
    ld (ix+W3D_ACTOR_STATE+0),a
    xor a
    ld (ix+W3D_ACTOR_STATE+1),a
    ld (ix+W3D_ACTOR_TICCOUNT+0),a
    ld (ix+W3D_ACTOR_TICCOUNT+1),a
    ld (ix+W3D_ACTOR_TEMP2+0),a
    ld (ix+W3D_ACTOR_TEMP2+1),a
    ld (ix+W3D_ACTOR_DISTANCE+0),a
    ld (ix+W3D_ACTOR_DISTANCE+1),a
    inc a
    ld (ix+W3D_ACTOR_DISTANCE+2),a
    xor a
    ld (ix+W3D_ACTOR_DISTANCE+3),a
    ld (ix+W3D_ACTOR_SPEED+0),a
    ld a,2
    ld (ix+W3D_ACTOR_SPEED+1),a
    xor a
    ld (ix+W3D_ACTOR_SPEED+2),a
    ld (ix+W3D_ACTOR_SPEED+3),a
    ld a,W3D_SLOT_NONE
    ld (ix+W3D_ACTOR_NEXT),a
    ld (ix+W3D_ACTOR_PREV),a
    ld a,1
    ld (w3d_current_actor_index),a
    call w3d_actorat_claim
    ret

prepare_two_officers:
    call prepare_one_actor
    ld a,W3D_CLASS_OFFICER
    ld (ix+W3D_ACTOR_CLASS),a
    ld a,W3D_STATE_OFC_STAND
    ld (ix+W3D_ACTOR_STATE+0),a
    ld (ix+W3D_ACTOR_NEXT),2

; Clone the initialized record, then install slot-two identity/pose/list links.
    ld a,2
    call w3d_actor_pointer_from_id
    push ix
    pop de
    ld hl,w3d_actors+W3D_ACTOR_SIZE
    ld bc,W3D_ACTOR_SIZE
    ldir
    ld a,2
    call w3d_actor_pointer_from_id
    ld hl,0158000h
    ld (ix+W3D_ACTOR_X),hl
    ld (ix+W3D_ACTOR_Y),hl
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld (ix+W3D_ACTOR_Y+3),a
    ld a,21
    ld (ix+W3D_ACTOR_TILEX),a
    ld (ix+W3D_ACTOR_TILEY),a
    ld a,W3D_SLOT_NONE
    ld (ix+W3D_ACTOR_NEXT),a
    ld a,1
    ld (ix+W3D_ACTOR_PREV),a
    ld a,2
    ld (w3d_actor_live_tail),a
    ld (w3d_actor_count),a
    ld a,3
    ld (w3d_actor_free_head),a
    ld a,2
    call w3d_actorat_claim
    ret

clear_actor_temp2:
    xor a
    ld (ix+W3D_ACTOR_TEMP2+0),a
    ld (ix+W3D_ACTOR_TEMP2+1),a
    ret

set_player_ahead:
    ld hl,0188000h                   ; (24.5,20.5)
    ld de,0148000h
    jp set_player_xy

set_player_behind:
    ld hl,0108000h                   ; (16.5,20.5)
    ld de,0148000h

; HL=x low 24 bits, DE=y low 24 bits. Valid fixture coordinates have byte3=0.
set_player_xy:
    ld (w3d_player_pose+0),hl
    ld (w3d_player_pose+4),de
    xor a
    ld (w3d_player_pose+3),a
    ld (w3d_player_pose+7),a
    ret

; ---------------------------------------------------------------------------
; PRT1 stopwatch.
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

prt_stop:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_irq_counter)
    ld (result_timing_milliseconds),hl
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
; Comparators and mailbox.
; ---------------------------------------------------------------------------

; IX=actual, IY=expected, DE=count, C=reason.
assert_memory:
@loop:
    ld a,d
    or e
    ret z
    ld a,(ix+0)
    ld b,(iy+0)
    call assert_equal
    inc ix
    inc iy
    call increment_test_index
    dec.s de
    jr @loop

; IX=expected, IY=actual.  This keeps the production actor pointer recoverable
; after a small expected buffer was already convenient in IX.
assert_memory_reverse:
@loop:
    ld a,d
    or e
    ret z
    ld a,(iy+0)
    ld b,(ix+0)
    call assert_equal
    inc ix
    inc iy
    call increment_test_index
    dec.s de
    jr @loop

increment_test_index:
    push hl
    ld hl,test_index
    inc (hl)
    jr nz,@done
    inc hl
    inc (hl)
@done:
    pop hl
    ret

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
    jr z,@return
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
    jr nz,@return
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

; Required by wolf3d_motion.inc but not exercised here.
w3d_mark_render_submitted:
    ret
w3d_audio_begin_quantum:
    ret
w3d_audio_request:
    ld d,a
    xor a
    ld (test_audio_kind),a
    ld a,b
    ld (test_audio_arg_b),a
    ld a,c
    ld (test_audio_arg_c),a
    ld a,d
    jr test_audio_record
w3d_audio_request_actor:
    ld d,a
    ld a,1
    ld (test_audio_kind),a
    ld a,(ix+W3D_ACTOR_TILEX)
    ld (test_audio_arg_b),a
    ld a,(ix+W3D_ACTOR_TILEY)
    ld (test_audio_arg_c),a
    ld a,d
    jr test_audio_record
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
test_audio_count:   dw 0
test_audio_last_id: db 0
test_audio_kind:    db 0
test_audio_arg_b:   db 0
test_audio_arg_c:   db 0
test_audio_end:

; class, chase state, speed in/out, distance in/out, active.
first_sighting_cases:
    db W3D_CLASS_GUARD,W3D_STATE_GRD_CHASE1
    dw 512,1536
    db 0ffh,0ffh,0ffh,0ffh, 0,0,0,0, W3D_ACTOR_ACTIVE_NO
    db W3D_CLASS_OFFICER,W3D_STATE_OFC_CHASE1
    dw 512,2560
    db 045h,023h,001h,0, 045h,023h,001h,0, W3D_ACTOR_ACTIVE_YES
    db W3D_CLASS_MUTANT,W3D_STATE_MUT_CHASE1
    dw 512,1536
    db 0f7h,0ffh,0ffh,0ffh, 0,0,0,0, W3D_ACTOR_ACTIVE_ALWAYS
    db W3D_CLASS_SS,W3D_STATE_SS_CHASE1
    dw 512,2048
    db 0,0,0,0, 0,0,0,0, W3D_ACTOR_ACTIVE_NO
    db W3D_CLASS_DOG,W3D_STATE_DOG_CHASE1
    dw 1500,3000
    db 0,0,1,0, 0,0,1,0, W3D_ACTOR_ACTIVE_YES

result_filename:            asciz "aware_result.bin"
report_banner:              asciz "\r\nWolf3D eZ80 awareness regression: "
report_pass:                asciz "PASS\r\n"
report_fail:                asciz "FAIL\r\n"

output_handle:              db 0
test_phase:                 db 0
test_detail:                db 0
test_index:                 dw 0
assert_expected:            db 0
assert_actual:              db 0
last_return:                db 0
expected_class:             db 0
expected_state:             db 0
expected_speed:             dw 0
expected_distance:          ds 4
first_sighting_ptr:         dl 0
timing_left:                dl 0
prt_vector:                 dl 0
prt_saved_vector:           db 0,0,0,0
prt_irq_counter:            dl 0
pose_before:                ds 13
actor_before:               ds W3D_ACTOR_SIZE

result_data:
    db "W3AW"
result_checks:              dw 0
result_errors:              dw 0
result_first_phase:         db 0
result_first_reason:        db 0
result_first_expected:      db 0
result_first_actual:        db 0
result_first_detail:        db 0
result_first_index:         dw 0
                            db 0
result_phase_errors:        ds phase_count
result_timing_milliseconds: dl 0
                            db 0,0
result_end:

test_tilemap:
    ds W3D_MAP_BYTES
test_path_directions:
    ds W3D_MAP_BYTES
test_area_map:
    ds W3D_MAP_BYTES
test_static_bits:
    ds 512
