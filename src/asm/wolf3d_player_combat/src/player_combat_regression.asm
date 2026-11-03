; Direct eZ80 regression for production ordinary player combat.

    assume adl=1
    org 0x040000
    jp start
    align 64
    db "MOS",0,1

mos_fopen:          equ 0x0a
mos_fclose:         equ 0x0b
mos_fwrite:         equ 0x1b
mos_getkbmap:       equ 0x1e
sysvar_time:         equ 0
fa_write:           equ 0x02
fa_create_always:   equ 0x08

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

    macro CHECK_PANEL_KEY offset,mask,panel_value
        call prepare_test_world
        xor a
        ld (w3d_exit_requested),a
        ld (w3d_gameplay_panel_request),a
        ld a,mask
        ld (w3d_keyboard_masks+offset),a
        call w3d_latch_exit_request
        CHECK_MEM8 w3d_exit_requested,1,reason_inventory
        CHECK_MEM8 w3d_gameplay_panel_request,panel_value,reason_inventory
    endmacro

    include "wolf3d_backend.inc"
    include "wolf3d_audio_assets.inc"
    include "wolf3d_sight.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_actors.inc"
    include "wolf3d_areas.inc"
; The player-combat fixture does not include the victory presentation module,
; but production actor simulation exposes its BJ-jump think callback.
w3d_victory_think_bj_jump:
    ret
w3d_victory_think_bj_run:
    ret
w3d_victory_bj_yell:
    ret
w3d_victory_bj_done:
    ret
    include "wolf3d_actor_sim.inc"
w3d_initialize_victory_state:
    xor a
    ld (w3d_victory_active),a
    ret
w3d_begin_victory_sequence:
    ret
w3d_simulate_victory_step:
    ret
w3d_victory_active:
    db 0
    include "wolf3d_motion.inc"
    include "wolf3d_player_combat.inc"

; Standalone production-motion clock seam. Ordinary tests overwrite the RNG
; index explicitly after initialization; the backing sysvar only keeps the
; production SetupGameLevel seed path linked and deterministic here.
w3d_sysvars_pointer: dl test_sysvars

phase_states:       equ 1
phase_timeline:     equ 2
phase_target:       equ 3
phase_damage:       equ 4
phase_inventory:    equ 5
phase_face:         equ 6
phase_palette:      equ 7
phase_count:        equ 7

reason_scalar:      equ 1
reason_state:       equ 2
reason_rng:         equ 3
reason_target:      equ 4
reason_inventory:   equ 5
reason_drop:        equ 6
reason_table:       equ 7
reason_audio:       equ 8

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
    call test_state_table
    call test_pistol_timeline
    call test_target_boundaries
    call test_damage_death_drops
    call test_weapon_selection
    call test_player_audio_requests
    call test_face_timeline
    call test_palette_timeline
    call write_result
    call print_report
    ret

; ---------------------------------------------------------------------------
; 7. Original red/white palette counters, priority, cadence and clearing.
; ---------------------------------------------------------------------------

test_palette_timeline:
    ld a,phase_palette
    ld (test_phase),a
    call prepare_test_world
    xor a
    ld (w3d_hud_dirty),a
    call w3d_start_bonus_flash
    call w3d_update_palette_shift
    CHECK_MEM8 w3d_palette_shift_wire,W3D_PALETTE_WHITE_FLAG+3,reason_state
    CHECK_MEM8 w3d_palette_bonus_count+0,16,reason_state
    CHECK_MEM8 w3d_palette_tick_phase,1,reason_state
    CHECK_MEM8 w3d_hud_dirty,W3D_HUD_DIRTY_PALETTE,reason_inventory

; The 2,2,3 sequence reaches source count 11, then drops from white level 3
; to level 2 on the following publish.
    xor a
    ld (w3d_hud_dirty),a
    call w3d_update_palette_shift
    CHECK_MEM8 w3d_palette_bonus_count+0,14,reason_state
    CHECK_MEM8 w3d_palette_tick_phase,2,reason_state
    CHECK_MEM8 w3d_hud_dirty,0,reason_inventory
    call w3d_update_palette_shift
    CHECK_MEM8 w3d_palette_bonus_count+0,11,reason_state
    CHECK_MEM8 w3d_palette_tick_phase,0,reason_state
    call w3d_update_palette_shift
    CHECK_MEM8 w3d_palette_shift_wire,W3D_PALETTE_WHITE_FLAG+2,reason_state
    CHECK_MEM8 w3d_palette_bonus_count+0,9,reason_state
    CHECK_MEM8 w3d_hud_dirty,W3D_HUD_DIRTY_PALETTE,reason_inventory

; Damage is additive and wins over a simultaneously live bonus counter.
    ld a,25
    call w3d_start_damage_flash
    xor a
    ld (w3d_hud_dirty),a
    call w3d_update_palette_shift
    CHECK_MEM8 w3d_palette_shift_wire,3,reason_state
    CHECK_MEM8 w3d_palette_damage_count+0,23,reason_state
    CHECK_MEM8 w3d_palette_bonus_count+0,7,reason_state
    CHECK_MEM8 w3d_hud_dirty,W3D_HUD_DIRTY_PALETTE,reason_inventory
    ld a,40
    call w3d_start_damage_flash
    call w3d_update_palette_shift
    CHECK_MEM8 w3d_palette_shift_wire,6,reason_state

; A final one-point red count is visible for one update, then publishes the
; normal palette on the next update.
    ld a,1
    ld (w3d_palette_damage_count+0),a
    xor a
    ld (w3d_palette_damage_count+1),a
    ld (w3d_palette_bonus_count+0),a
    ld (w3d_palette_bonus_count+1),a
    ld (w3d_hud_dirty),a
    call w3d_update_palette_shift
    CHECK_MEM8 w3d_palette_shift_wire,1,reason_state
    CHECK_MEM8 w3d_palette_damage_count+0,0,reason_state
    xor a
    ld (w3d_hud_dirty),a
    call w3d_update_palette_shift
    CHECK_MEM8 w3d_palette_shift_wire,0,reason_state
    CHECK_MEM8 w3d_hud_dirty,W3D_HUD_DIRTY_PALETTE,reason_inventory
    ret

; ---------------------------------------------------------------------------
; 1. Exact source-derived pain/death records.
; ---------------------------------------------------------------------------

test_state_table:
    ld a,phase_states
    ld (test_phase),a
    ld a,W3D_STATE_COUNT
    CHECK_A 162,reason_scalar
    ld hl,w3d_actor_states_end-w3d_actor_states
    ld a,l
    CHECK_A 0b2h,reason_scalar
    ld a,h
    CHECK_A 5,reason_scalar
    ld ix,w3d_actor_states+909        ; 101 * 9, literal avoids precedence
    ld iy,expected_injury_states
    ld de,expected_injury_states_end-expected_injury_states
    ld c,reason_table
    call assert_memory
; WL_DEF.H orders Hans as walk 296..299, shoot 300..302, dead 303,
; then die 304..306. Pin the complete source-derived graph so firing and
; death art can never be transposed while timing/actions still look valid.
    ld ix,w3d_actor_states+1224        ; 136 * 9
    ld iy,expected_boss_states
    ld de,expected_boss_states_end-expected_boss_states
    ld c,reason_table
    jp assert_memory

; ---------------------------------------------------------------------------
; 2. Pistol attack: ready/frame timing, one shot, one RNG draw and pain.
; ---------------------------------------------------------------------------

test_pistol_timeline:
    ld a,phase_timeline
    ld (test_phase),a
    call prepare_test_world
    ld a,W3D_CONTROL_ATTACK
    ld (w3d_controls),a
    xor a
    ld (w3d_world_dirty),a
    ld (w3d_player_weapon_shape_dirty),a
    call advance_player_quantum         ; Cmd_Fire, no immediate action
    CHECK_MEM8 w3d_player_attack_active,1,reason_state
    CHECK_MEM8 w3d_player_attack_count,6,reason_state
    CHECK_MEM8 w3d_player_weapon_frame,1,reason_state
    CHECK_MEM8 w3d_player_weapon_shape+0,0a6h,reason_state ; 422
    CHECK_MEM8 w3d_player_weapon_shape+1,1,reason_state
    CHECK_MEM8 w3d_player_weapon_shape_dirty,1,reason_state
    CHECK_MEM8 w3d_world_dirty,1,reason_state
    CHECK_MEM8 w3d_player_ammo,8,reason_inventory

    call advance_player_quantum         ; -2 -> 4
    call advance_player_quantum         ; -3 -> 1
    call advance_player_quantum         ; -2 -> -1 + 6, enter frame 1
    CHECK_MEM8 w3d_player_attack_frame,1,reason_state
    CHECK_MEM8 w3d_player_attack_count,5,reason_state
    call advance_player_quantum         ; -2 -> 3
    call advance_player_quantum         ; -3 -> shot at exact zero
    CHECK_MEM8 w3d_player_ammo,7,reason_inventory
    CHECK_MEM8 w3d_random_index,1,reason_rng
    CHECK_MEM8 w3d_player_last_attack_target,1,reason_target
    CHECK_MEM8 w3d_player_last_attack_hit,1,reason_target
    CHECK_MEM8 w3d_player_last_attack_damage,1,reason_scalar
    CHECK_MEM8 w3d_player_attack_frame,2,reason_state
    CHECK_MEM8 w3d_player_weapon_frame,3,reason_state
    ld a,1
    call w3d_actor_pointer_from_id
    CHECK_IX8 W3D_ACTOR_HITPOINTS,24,reason_state
    CHECK_IX8 W3D_ACTOR_STATE,W3D_STATE_GRD_PAIN1,reason_state
    ret

; ---------------------------------------------------------------------------
; 3. Strict center cone and inclusive knife reach.
; ---------------------------------------------------------------------------

test_target_boundaries:
    ld a,phase_target
    ld (test_phase),a
    call prepare_test_world
; rel=(512,+98) Q8 is inside: 98*87 < (512+23)*16.
    ld ix,w3d_actors+W3D_ACTOR_SIZE
    ld a,0e2h
    ld (ix+W3D_ACTOR_Y+1),a
    ld a,10
    ld (ix+W3D_ACTOR_Y+2),a
    call w3d_player_select_attack_target
    CHECK_A 1,reason_target
; One Q8 lateral unit farther is strictly outside.
    ld ix,w3d_actors+W3D_ACTOR_SIZE
    ld a,0e3h
    ld (ix+W3D_ACTOR_Y+1),a
    call w3d_player_select_attack_target
    CHECK_A W3D_SLOT_NONE,reason_target

; relx=361 Q8 produces nx=0x180, the inclusive knife boundary.
    call prepare_test_world
    ld ix,w3d_actors+W3D_ACTOR_SIZE
    xor a
    ld (ix+W3D_ACTOR_X+0),a
    ld a,0e9h
    ld (ix+W3D_ACTOR_X+1),a
    ld a,11
    ld (ix+W3D_ACTOR_X+2),a
    ld (ix+W3D_ACTOR_TILEX),a
    call w3d_player_knife_attack
    CHECK_MEM8 w3d_player_last_attack_hit,1,reason_target
    CHECK_MEM8 w3d_random_index,1,reason_rng
; relx=362 gives nx=0x181 and must not draw RNG.
    call prepare_test_world
    ld ix,w3d_actors+W3D_ACTOR_SIZE
    xor a
    ld (ix+W3D_ACTOR_X+0),a
    ld a,0eah
    ld (ix+W3D_ACTOR_X+1),a
    ld a,11
    ld (ix+W3D_ACTOR_X+2),a
    ld (ix+W3D_ACTOR_TILEX),a
    call w3d_player_knife_attack
    CHECK_MEM8 w3d_player_last_attack_hit,0,reason_target
    CHECK_MEM8 w3d_random_index,0,reason_rng

; Projection alone is not source FL_VISABLE.  A wall in the intervening tile
; must remove the otherwise centered target for both gun and knife selection.
    call prepare_test_world
    ld a,1
    ld (test_tilemap+651),a             ; y=10, x=11
    call w3d_player_select_attack_target
    CHECK_A W3D_SLOT_NONE,reason_target
    call w3d_player_knife_attack
    CHECK_MEM8 w3d_player_last_attack_hit,0,reason_target
    CHECK_MEM8 w3d_random_index,0,reason_rng

; A nearer projected actor must not mask a farther clear actor.  Actor 1's
; ray crosses wall (13,11); actor 2's equally valid narrower-cone ray crosses
; (13,10), so the production linked-list scan must continue and select id 2.
    call prepare_test_world
    ld ix,w3d_actors+W3D_ACTOR_SIZE
    ld a,14
    ld (ix+W3D_ACTOR_X+2),a
    ld (ix+W3D_ACTOR_TILEX),a
    ld a,11
    ld (ix+W3D_ACTOR_Y+2),a
    ld (ix+W3D_ACTOR_TILEY),a
    ld a,2
    ld (ix+W3D_ACTOR_NEXT),a

    ld hl,w3d_actors+W3D_ACTOR_SIZE
    ld de,w3d_actors+W3D_ACTOR_SIZE+W3D_ACTOR_SIZE
    ld bc,W3D_ACTOR_SIZE
    ldir
    ld ix,w3d_actors+W3D_ACTOR_SIZE+W3D_ACTOR_SIZE
    ld a,16
    ld (ix+W3D_ACTOR_X+2),a
    ld (ix+W3D_ACTOR_TILEX),a
    xor a
    ld (ix+W3D_ACTOR_Y+1),a
    ld a,10
    ld (ix+W3D_ACTOR_Y+2),a
    ld (ix+W3D_ACTOR_TILEY),a
    ld a,1
    ld (ix+W3D_ACTOR_PREV),a
    ld a,W3D_SLOT_NONE
    ld (ix+W3D_ACTOR_NEXT),a
    ld a,2
    ld (w3d_actor_live_tail),a
    ld (w3d_actor_count),a
    ld a,1
    ld (test_tilemap+717),a             ; y=11, x=13
    call w3d_player_select_attack_target
    CHECK_A 2,reason_target

; Bosses share the ordinary hitscan target selector.  This is intentionally
; a complete gun-to-death-path test: accepting boss damage directly is not
; sufficient if the selector filters Hans out before DamageActor is reached.
    call prepare_test_world
    ld ix,w3d_actors+W3D_ACTOR_SIZE
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_BOSS
    ld (ix+W3D_ACTOR_STATE+0),W3D_STATE_BOSS_CHASE1
    ld (ix+W3D_ACTOR_STATE+1),0
    ld (ix+W3D_ACTOR_HITPOINTS+0),1
    ld (ix+W3D_ACTOR_HITPOINTS+1),0
    call w3d_player_gun_attack
    CHECK_MEM8 w3d_player_last_attack_target,1,reason_target
    CHECK_MEM8 w3d_player_last_attack_hit,1,reason_target
    CHECK_MEM8 w3d_player_last_attack_damage,1,reason_scalar
    CHECK_MEM8 w3d_player_last_damage_result,W3D_DAMAGE_RESULT_KILLED,reason_scalar
    ld a,1
    call w3d_actor_pointer_from_id
    CHECK_IX8 W3D_ACTOR_STATE+0,W3D_STATE_BOSS_DIE1,reason_state
    CHECK_IX8 W3D_ACTOR_STATE+1,0,reason_state
    CHECK_IX8 W3D_ACTOR_FLAGS,W3D_ACTOR_FLAG_ATTACKMODE|W3D_ACTOR_FLAG_NONMARK,reason_state
    CHECK_MEM8 w3d_player_score+0,088h,reason_inventory
    CHECK_MEM8 w3d_player_score+1,013h,reason_inventory
    CHECK_MEM8 w3d_player_kill_count,1,reason_inventory
    ret

; ---------------------------------------------------------------------------
; 4. Ordinary and shareware-boss death ownership, points and runtime drops.
; ---------------------------------------------------------------------------

test_damage_death_drops:
    ld a,phase_damage
    ld (test_phase),a
    call prepare_test_world
    ld ix,w3d_actors+W3D_ACTOR_SIZE
    ld (ix+W3D_ACTOR_HITPOINTS+0),10
    xor a
    ld (ix+W3D_ACTOR_HITPOINTS+1),a
    ld hl,10
    ld a,1
    call w3d_damage_actor
    CHECK_A W3D_DAMAGE_RESULT_KILLED,reason_scalar
    ld a,1
    call w3d_actor_pointer_from_id
    CHECK_IX8 W3D_ACTOR_STATE,W3D_STATE_GRD_DIE1,reason_state
    CHECK_IX8 W3D_ACTOR_TICCOUNT,15,reason_state
    CHECK_IX8 W3D_ACTOR_FLAGS,W3D_ACTOR_FLAG_ATTACKMODE|W3D_ACTOR_FLAG_NONMARK,reason_state
    CHECK_MEM8 w3d_player_score,100,reason_inventory
    CHECK_MEM8 w3d_player_kill_count,1,reason_inventory
    CHECK_MEM8 w3d_static_count,W3D_FIXTURE_STATIC_COUNT+1,reason_drop
    ld hl,W3D_FIXTURE_STATIC_COUNT
    ld (w3d_current_static_index),hl
    call w3d_static_pointer_from_current
    CHECK_IX8 W3D_STATIC_TILEX,12,reason_drop
    CHECK_IX8 W3D_STATIC_TILEY,10,reason_drop
    CHECK_IX8 W3D_STATIC_SHAPENUM,28,reason_drop
    CHECK_IX8 W3D_STATIC_ITEMNUMBER,W3D_ITEM_CLIP2,reason_drop

; SS drops a machinegun while the player's best weapon is still the pistol.
    call prepare_test_world
    ld ix,w3d_actors+W3D_ACTOR_SIZE
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_SS
    ld (ix+W3D_ACTOR_STATE+0),W3D_STATE_SS_CHASE1
    ld (ix+W3D_ACTOR_HITPOINTS+0),1
    ld hl,1
    ld a,1
    call w3d_damage_actor
    CHECK_A W3D_DAMAGE_RESULT_KILLED,reason_scalar
    ld a,1
    call w3d_actor_pointer_from_id
    CHECK_IX8 W3D_ACTOR_STATE,W3D_STATE_SS_DIE1,reason_state
    CHECK_MEM8 w3d_player_score+0,0f4h,reason_inventory
    CHECK_MEM8 w3d_player_score+1,1,reason_inventory
    ld hl,W3D_FIXTURE_STATIC_COUNT
    ld (w3d_current_static_index),hl
    call w3d_static_pointer_from_current
    CHECK_IX8 W3D_STATIC_SHAPENUM,29,reason_drop
    CHECK_IX8 W3D_STATIC_ITEMNUMBER,W3D_ITEM_MACHINEGUN,reason_drop

; Hans has no pain arm. A lethal hit enters the widened death chain, awards
; 5000 points, and places the gold key using its original SPR_STAT_20 shape.
    call prepare_test_world
    ld ix,w3d_actors+W3D_ACTOR_SIZE
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_BOSS
    ld (ix+W3D_ACTOR_STATE+0),W3D_STATE_BOSS_CHASE1
    xor a
    ld (ix+W3D_ACTOR_STATE+1),a
    ld (ix+W3D_ACTOR_HITPOINTS+0),1
    ld hl,1
    ld a,1
    call w3d_damage_actor
    CHECK_A W3D_DAMAGE_RESULT_KILLED,reason_scalar
    ld a,1
    call w3d_actor_pointer_from_id
    CHECK_IX8 W3D_ACTOR_STATE+0,W3D_STATE_BOSS_DIE1,reason_state
    CHECK_IX8 W3D_ACTOR_STATE+1,0,reason_state
    CHECK_IX8 W3D_ACTOR_TICCOUNT,15,reason_state
    CHECK_MEM8 w3d_player_score+0,088h,reason_inventory
    CHECK_MEM8 w3d_player_score+1,013h,reason_inventory
    CHECK_MEM8 w3d_player_kill_count,1,reason_inventory
    CHECK_MEM8 w3d_static_count,W3D_FIXTURE_STATIC_COUNT+1,reason_drop
    ld hl,W3D_FIXTURE_STATIC_COUNT
    ld (w3d_current_static_index),hl
    call w3d_static_pointer_from_current
    CHECK_IX8 W3D_STATIC_SHAPENUM,22,reason_drop
    CHECK_IX8 W3D_STATIC_ITEMNUMBER,W3D_ITEM_KEY1,reason_drop
    ret

; ---------------------------------------------------------------------------
; 5. Raw keymap 1..4 selection and resolved ready shape.
; ---------------------------------------------------------------------------

test_weapon_selection:
    ld a,phase_inventory
    ld (test_phase),a
    ld a,1
    ld (test_case),a

; Physical key contract: Up Arrow is Use, Space is Attack, and the old generic
; Ctrl binding is deliberately unassigned.
    call prepare_test_world
    ld a,00000010b                   ; Up arrow: kbmap byte 7 bit 1
    ld (w3d_keyboard_masks+7),a
    call w3d_sample_controls
    CHECK_MEM8 w3d_controls,W3D_CONTROL_USE,reason_inventory

    call prepare_test_world
    ld a,00000100b                   ; Space: kbmap byte 12 bit 2
    ld (w3d_keyboard_masks+12),a
    call w3d_sample_controls
    CHECK_MEM8 w3d_controls,W3D_CONTROL_ATTACK,reason_inventory

    call prepare_test_world
    ld a,00000010b                   ; generic Ctrl: kbmap byte 0 bit 1
    ld (w3d_keyboard_masks+0),a
    call w3d_sample_controls
    CHECK_MEM8 w3d_controls,0,reason_inventory

; Escape is authoritative in the held-key hot loop, independent of whether
; the asynchronous keyboard callback receives an ASCII key-down record.
    ld a,2
    ld (test_case),a
    call prepare_test_world
    xor a
    ld (w3d_exit_requested),a
    ld a,00000001b                   ; Escape: kbmap byte 14 bit 0
    ld (w3d_keyboard_masks+14),a
    call w3d_latch_exit_request
    CHECK_MEM8 w3d_exit_requested,1,reason_inventory
    CHECK_MEM8 w3d_gameplay_panel_request,w3d_panel_request_menu,reason_inventory

; MOS's BBC-compatible keymap scatters F1-F10 across three bytes. Pin every
; source CheckKeys/CP_CheckQuick route rather than assuming enum adjacency.
    ld a,3
    ld (test_case),a
    CHECK_PANEL_KEY 14,00000010b,w3d_panel_request_help
    CHECK_PANEL_KEY 14,00000100b,w3d_panel_request_save
    CHECK_PANEL_KEY 14,00001000b,w3d_panel_request_load
    CHECK_PANEL_KEY 2,00010000b,w3d_panel_request_sound
    CHECK_PANEL_KEY 14,00010000b,w3d_panel_request_view
    CHECK_PANEL_KEY 14,00100000b,w3d_panel_request_control
    CHECK_PANEL_KEY 2,01000000b,w3d_panel_request_end_game
    CHECK_PANEL_KEY 14,01000000b,w3d_panel_request_quick_save
    CHECK_PANEL_KEY 14,10000000b,w3d_panel_request_quick_load
    CHECK_PANEL_KEY 3,01000000b,w3d_panel_request_quit

; The shipped M+L+I chord is ordinary CheckKeys behavior, not part of the
; command-line-gated `goobers` debug arm. Pin the physical MOS key locations,
; full state mutation, exact ten-minute penalty, and modal handoff.
    ld a,4
    ld (test_case),a
    call prepare_test_world
    xor a
    ld (w3d_exit_requested),a
    ld (w3d_gameplay_panel_request),a
    ld a,17
    ld (w3d_player_health),a
    ld a,2
    ld (w3d_player_ammo),a
    xor a
    ld (w3d_player_key_flags),a
    ld a,078h
    ld (w3d_player_score+0),a
    ld a,056h
    ld (w3d_player_score+1),a
    ld a,034h
    ld (w3d_player_score+2),a
    ld a,012h
    ld (w3d_player_score+3),a
    ld a,12
    ld (w3d_intermission_level_minutes),a
    ld a,34
    ld (w3d_intermission_level_seconds),a
    ld a,5
    ld (w3d_intermission_level_subticks),a
    xor a
    ld (w3d_hud_dirty),a
    ld (w3d_world_dirty),a
    ld a,00100000b                  ; I: byte 4 bit 5
    ld (w3d_keyboard_masks+4),a
    ld a,01000000b                  ; L: byte 10 bit 6
    ld (w3d_keyboard_masks+10),a
    ld a,00100000b                  ; M: byte 12 bit 5
    ld (w3d_keyboard_masks+12),a
    call w3d_check_shipped_key_chords
    CHECK_A 1,reason_inventory
    CHECK_MEM8 w3d_exit_requested,1,reason_inventory
    CHECK_MEM8 w3d_gameplay_panel_request,w3d_panel_request_cheater,reason_inventory
    CHECK_MEM8 w3d_player_health,100,reason_inventory
    CHECK_MEM8 w3d_player_ammo,99,reason_inventory
    CHECK_MEM8 w3d_player_key_flags,3,reason_table
    CHECK_MEM8 w3d_player_score+0,0,reason_inventory
    CHECK_MEM8 w3d_player_score+1,0,reason_inventory
    CHECK_MEM8 w3d_player_score+2,0,reason_inventory
    CHECK_MEM8 w3d_player_score+3,0,reason_inventory
    CHECK_MEM8 w3d_player_weapon,3,reason_table
    CHECK_MEM8 w3d_player_best_weapon,3,reason_table
    CHECK_MEM8 w3d_player_chosen_weapon,3,reason_table
    CHECK_MEM8 w3d_intermission_level_minutes,22,reason_inventory
    CHECK_MEM8 w3d_intermission_level_seconds,34,reason_inventory
    CHECK_MEM8 w3d_intermission_level_subticks,5,reason_inventory
    CHECK_MEM8 w3d_hud_dirty,01fh,reason_inventory ; health/ammo/keys/weapon/score
    CHECK_MEM8 w3d_world_dirty,1,reason_inventory

; Crossing the original 99:00 intermission cap clears seconds/subticks rather
; than manufacturing an impossible 99:34 display.
    ld a,95
    ld (w3d_intermission_level_minutes),a
    ld a,34
    ld (w3d_intermission_level_seconds),a
    ld a,5
    ld (w3d_intermission_level_subticks),a
    call w3d_check_shipped_key_chords
    CHECK_MEM8 w3d_intermission_level_minutes,99,reason_inventory
    CHECK_MEM8 w3d_intermission_level_seconds,0,reason_inventory
    CHECK_MEM8 w3d_intermission_level_subticks,0,reason_inventory

; B+A+T is the separate Commander Keen message and changes no player state.
    call prepare_test_world
    xor a
    ld (w3d_exit_requested),a
    ld (w3d_gameplay_panel_request),a
    ld a,42
    ld (w3d_player_health),a
    ld a,00100000b                  ; I only: partial MLI must not trigger
    ld (w3d_keyboard_masks+4),a
    call w3d_check_shipped_key_chords
    CHECK_A 0,reason_inventory
    CHECK_MEM8 w3d_exit_requested,0,reason_inventory
    ld a,00001000b                  ; T: byte 4 bit 3
    ld (w3d_keyboard_masks+4),a
    ld a,00000010b                  ; A: byte 8 bit 1
    ld (w3d_keyboard_masks+8),a
    ld a,00010000b                  ; B: byte 12 bit 4
    ld (w3d_keyboard_masks+12),a
    call w3d_check_shipped_key_chords
    CHECK_A 1,reason_inventory
    CHECK_MEM8 w3d_gameplay_panel_request,w3d_panel_request_keen,reason_inventory
    CHECK_MEM8 w3d_player_health,42,reason_inventory

; CheckKeys returns immediately during demo playback, even with a complete
; physical chord held.
    call prepare_test_world
    xor a
    ld (w3d_exit_requested),a
    ld (w3d_gameplay_panel_request),a
    ld a,42
    ld (w3d_player_health),a
    ld a,1
    ld (w3d_demo_active),a
    ld a,00100000b
    ld (w3d_keyboard_masks+4),a
    ld a,01000000b
    ld (w3d_keyboard_masks+10),a
    ld a,00100000b
    ld (w3d_keyboard_masks+12),a
    call w3d_check_shipped_key_chords
    CHECK_A 0,reason_inventory
    CHECK_MEM8 w3d_exit_requested,0,reason_inventory
    CHECK_MEM8 w3d_player_health,42,reason_inventory

; Number keys continue to select carried weapons; pin the fourth physical key
; here while the host oracle covers all four selection policies.
    ld a,5
    ld (test_case),a
    call prepare_test_world
    ld a,W3D_WEAPON_CHAINGUN
    ld (w3d_player_best_weapon),a
    ld a,00000100b                   ; top-row 4: kbmap byte 2 bit 2
    ld (w3d_keyboard_masks+2),a
    xor a
    ld (w3d_controls),a
    call advance_player_quantum
    CHECK_MEM8 w3d_player_weapon,W3D_WEAPON_CHAINGUN,reason_inventory
    CHECK_MEM8 w3d_player_chosen_weapon,W3D_WEAPON_CHAINGUN,reason_inventory
    CHECK_MEM8 w3d_player_weapon_shape+0,0afh,reason_inventory ; 431
    CHECK_MEM8 w3d_player_weapon_shape+1,1,reason_inventory

; A release/repress during an active machine-gun attack is not automatic
; hold.  Original T_Attack clears that frame's buttonstate, so action 3 must
; advance to frame 3 instead of looping back to frame 1.
    call prepare_test_world
    ld a,W3D_WEAPON_MACHINEGUN
    ld (w3d_player_weapon),a
    ld (w3d_player_best_weapon),a
    ld (w3d_player_chosen_weapon),a
    ld a,1
    ld (w3d_player_attack_active),a
    xor a                              ; already released during animation
    ld (w3d_player_attack_was_down),a
    ld a,2
    ld (w3d_player_attack_frame),a
    ld (w3d_player_attack_count+0),a   ; this 2-tic quantum reaches action 3
    xor a
    ld (w3d_player_attack_count+1),a
    ld a,W3D_CONTROL_ATTACK            ; physical repress
    ld (w3d_controls),a
    call advance_player_quantum
    CHECK_MEM8 w3d_player_attack_frame,3,reason_state
    CHECK_MEM8 w3d_player_attack_repeat_down,0,reason_state
    CHECK_MEM8 w3d_player_attack_was_down,0,reason_state

; GiveAmmo restores the chosen weapon only while attackframe is zero and must
; refresh the cached first-person shape when it does change the weapon.
    call prepare_test_world
    xor a
    ld (w3d_player_ammo),a
    ld (w3d_player_weapon),a             ; knife
    ld a,W3D_WEAPON_MACHINEGUN
    ld (w3d_player_best_weapon),a
    ld (w3d_player_chosen_weapon),a
    xor a
    ld (w3d_player_weapon_frame),a
    call w3d_player_combat_refresh_shape
    xor a
    ld (w3d_player_weapon_shape_dirty),a
    ld a,4
    call w3d_add_player_ammo
    CHECK_MEM8 w3d_player_ammo,4,reason_inventory
    CHECK_MEM8 w3d_player_weapon,W3D_WEAPON_MACHINEGUN,reason_inventory
    CHECK_MEM8 w3d_player_weapon_shape+0,0aah,reason_inventory ; 426
    CHECK_MEM8 w3d_player_weapon_shape+1,1,reason_inventory
    CHECK_MEM8 w3d_player_weapon_shape_dirty,1,reason_inventory

; Mid-animation ammo acquisition must not switch attackinfo rows.
    call prepare_test_world
    xor a
    ld (w3d_player_ammo),a
    ld (w3d_player_weapon),a             ; knife
    ld a,W3D_WEAPON_MACHINEGUN
    ld (w3d_player_best_weapon),a
    ld (w3d_player_chosen_weapon),a
    ld a,1
    ld (w3d_player_attack_active),a
    ld (w3d_player_attack_frame),a
    ld a,2
    ld (w3d_player_weapon_frame),a
    call w3d_player_combat_refresh_shape
    ld a,4
    call w3d_add_player_ammo
    CHECK_MEM8 w3d_player_ammo,4,reason_inventory
    CHECK_MEM8 w3d_player_weapon,W3D_WEAPON_KNIFE,reason_inventory
    CHECK_MEM8 w3d_player_weapon_shape+0,0a2h,reason_inventory ; 418
    CHECK_MEM8 w3d_player_weapon_shape+1,1,reason_inventory

; GiveWeapon changes all inventory weapon fields and refreshes the currently
; displayed animation frame immediately.
    call prepare_test_world
    ld a,2
    ld (w3d_player_weapon_frame),a
    ld a,W3D_WEAPON_CHAINGUN
    call w3d_set_player_weapon
    CHECK_MEM8 w3d_player_weapon,W3D_WEAPON_CHAINGUN,reason_inventory
    CHECK_MEM8 w3d_player_chosen_weapon,W3D_WEAPON_CHAINGUN,reason_inventory
    CHECK_MEM8 w3d_player_best_weapon,W3D_WEAPON_CHAINGUN,reason_inventory
    CHECK_MEM8 w3d_player_weapon_shape+0,0b1h,reason_inventory ; 433
    CHECK_MEM8 w3d_player_weapon_shape+1,1,reason_inventory
    ret

; The retained 1..4 observability id is translated exactly once into the
; generated WL1 id at full unpositioned gain. Unsupported internal ids do not
; leak a backend request.
test_player_audio_requests:
    ld a,phase_timeline
    ld (test_phase),a
    call test_audio_reset
    ld a,W3D_PLAYER_SOUND_KNIFE
    call w3d_player_publish_attack_sound
    CHECK_MEM8 test_audio_last_id,23,reason_audio
    ld a,W3D_PLAYER_SOUND_PISTOL
    call w3d_player_publish_attack_sound
    CHECK_MEM8 test_audio_last_id,24,reason_audio
    ld a,W3D_PLAYER_SOUND_MACHINEGUN
    call w3d_player_publish_attack_sound
    CHECK_MEM8 test_audio_last_id,26,reason_audio
    ld a,W3D_PLAYER_SOUND_CHAINGUN
    call w3d_player_publish_attack_sound
    CHECK_MEM8 test_audio_last_id,11,reason_audio
    CHECK_MEM8 test_audio_count+0,4,reason_audio
    CHECK_MEM8 test_audio_gain,127,reason_audio
    CHECK_MEM8 test_audio_flags,0,reason_audio
    xor a
    call w3d_player_publish_attack_sound
    CHECK_MEM8 test_audio_count+0,4,reason_audio
    ret

; ---------------------------------------------------------------------------
; 6. Original UpdateFace random/cadence contract and strict threshold.
; ---------------------------------------------------------------------------

test_face_timeline:
    ld a,phase_face
    ld (test_phase),a
    call prepare_test_world

; Starting at table index 1 gives thresholds 109,220,222: no transition,
; while the exact 2,2,3 tic cadence accumulates 2,4,7.
    ld a,1
    ld (w3d_random_index),a
    call w3d_update_player_face
    CHECK_MEM8 w3d_player_face_count+0,2,reason_state
    CHECK_MEM8 w3d_player_face_tick_phase,1,reason_state
    CHECK_MEM8 w3d_random_index,2,reason_rng
    call w3d_update_player_face
    CHECK_MEM8 w3d_player_face_count+0,4,reason_state
    CHECK_MEM8 w3d_player_face_tick_phase,2,reason_state
    CHECK_MEM8 w3d_random_index,3,reason_rng
    call w3d_update_player_face
    CHECK_MEM8 w3d_player_face_count+0,7,reason_state
    CHECK_MEM8 w3d_player_face_tick_phase,0,reason_state
    CHECK_MEM8 w3d_random_index,4,reason_rng

; The source comparison is strict: 6+2 == table[1] (8) does not change.
    xor a
    ld (w3d_random_index),a
    ld (w3d_player_face_tick_phase),a
    ld (w3d_hud_dirty),a
    ld a,6
    ld (w3d_player_face_count+0),a
    xor a
    ld (w3d_player_face_count+1),a
    ld a,2
    ld (w3d_player_face_frame),a
    call w3d_update_player_face
    CHECK_MEM8 w3d_player_face_count+0,8,reason_state
    CHECK_MEM8 w3d_player_face_frame,2,reason_state
    CHECK_MEM8 w3d_random_index,1,reason_rng
    CHECK_MEM8 w3d_hud_dirty,0,reason_inventory

; 7+2 > table[1] consumes table[2] (109), selects frame 1, resets the
; counter, and makes the complete HUD record dirty.
    xor a
    ld (w3d_random_index),a
    ld (w3d_player_face_tick_phase),a
    ld (w3d_hud_dirty),a
    ld a,7
    ld (w3d_player_face_count+0),a
    call w3d_update_player_face
    CHECK_MEM8 w3d_player_face_count+0,0,reason_state
    CHECK_MEM8 w3d_player_face_frame,1,reason_state
    CHECK_MEM8 w3d_random_index,2,reason_rng
    CHECK_MEM8 w3d_hud_dirty,W3D_HUD_DIRTY_FACE,reason_inventory

; A raw 3 from the high two bits is folded to frame 1 exactly as DOS did.
    ld a,2
    ld (w3d_random_index),a
    xor a
    ld (w3d_player_face_tick_phase),a
    ld (w3d_hud_dirty),a
    ld a,0ffh
    ld (w3d_player_face_count+0),a
    call w3d_update_player_face
    CHECK_MEM8 w3d_player_face_frame,1,reason_state
    CHECK_MEM8 w3d_random_index,4,reason_rng

; And a high-bit pattern of 2 remains frame 2.
    ld a,21
    ld (w3d_random_index),a
    xor a
    ld (w3d_player_face_tick_phase),a
    ld a,0ffh
    ld (w3d_player_face_count+0),a
    call w3d_update_player_face
    CHECK_MEM8 w3d_player_face_frame,2,reason_state
    CHECK_MEM8 w3d_random_index,23,reason_rng

; GOTGATLINGPIC is a transient wire presentation, not a replacement for the
; persistent ordinary faceframe.  Its generated hold consumes no gameplay
; random numbers and no ordinary face time.
    xor a
    ld (w3d_random_index),a
    ld (w3d_hud_dirty),a
    ld a,77
    ld (w3d_player_face_count+0),a
    call w3d_begin_chaingun_face
    CHECK_MEM8 w3d_player_face_special,1,reason_state
    CHECK_MEM8 w3d_player_face_special_ticks,W3D_AUDIO_GETGATLING_HOLD_TICKS,reason_state
    CHECK_MEM8 w3d_player_face_count+0,0,reason_state
    CHECK_MEM8 w3d_hud_dirty,W3D_HUD_DIRTY_FACE,reason_inventory
    ld b,W3D_AUDIO_GETGATLING_HOLD_TICKS
@special_hold:
    push bc
    call w3d_update_player_face
    pop bc
    djnz @special_hold
    CHECK_MEM8 w3d_player_face_special,1,reason_state
    CHECK_MEM8 w3d_player_face_special_ticks,0,reason_state
    CHECK_MEM8 w3d_player_face_count+0,0,reason_state
    CHECK_MEM8 w3d_random_index,0,reason_rng

; Sound expiry alone does not redraw the face: the next ordinary random
; transition does, exactly as UpdateFace/DrawFace did in the source.
    ld a,7
    ld (w3d_player_face_count+0),a
    call w3d_update_player_face
    CHECK_MEM8 w3d_player_face_special,0,reason_state
    CHECK_MEM8 w3d_player_face_frame,1,reason_state
    CHECK_MEM8 w3d_random_index,2,reason_rng

; Damage and successful healing both call DrawFace immediately and cancel the
; special presentation even while its modeled sound hold remains active.
    call w3d_begin_chaingun_face
    ld a,1
    ld (w3d_current_actor_index),a
    call w3d_take_player_damage
    CHECK_MEM8 w3d_player_face_special,0,reason_state
    call w3d_begin_chaingun_face
    ld a,99
    ld (w3d_player_health),a
    ld a,1
    call w3d_add_player_health
    CHECK_MEM8 w3d_player_face_special,0,reason_state
    call w3d_begin_chaingun_face
    xor a
    ld (w3d_game_difficulty),a       ; baby: raw 1 scales to zero
    ld a,1
    call w3d_take_player_damage
    CHECK_MEM8 w3d_player_health,100,reason_inventory
    CHECK_MEM8 w3d_player_face_special,0,reason_state
    ret

; ---------------------------------------------------------------------------
; Deterministic test-world setup.
; ---------------------------------------------------------------------------

prepare_test_world:
    call w3d_initialize_motion_state
    call w3d_initialize_player_combat
; Open 64x64 trace map and connected area zero.
    xor a
    ld hl,test_tilemap
    ld (hl),a
    ld de,test_tilemap+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,test_areas
    ld (hl),1
    ld de,test_areas+1
    ld bc,W3D_NUM_AREAS-1
    ldir
    ld hl,test_tilemap
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_TILEMAP),hl
    ld hl,w3d_doors
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_DOORS),hl
    ld hl,test_areas
    ld (w3d_actor_sight_context+W3D_SIGHT_CTX_AREAS),hl

; Player center (10.5,10.5), east=0.
    xor a
    ld (w3d_player_pose+0),a
    ld a,080h
    ld (w3d_player_pose+1),a
    ld a,10
    ld (w3d_player_pose+2),a
    xor a
    ld (w3d_player_pose+3),a
    ld (w3d_player_pose+4),a
    ld a,080h
    ld (w3d_player_pose+5),a
    ld a,10
    ld (w3d_player_pose+6),a
    xor a
    ld (w3d_player_pose+7),a
    ld (w3d_player_pose+8),a
    ld (w3d_player_pose+9),a

; One attack-mode guard at (12.5,10.5).
    ld ix,w3d_actors+W3D_ACTOR_SIZE
    push ix
    pop hl
    xor a
    ld (hl),a
    ld de,0
    push ix
    pop de
    inc de
    ld bc,W3D_ACTOR_SIZE-1
    ldir
    xor a
    ld (ix+W3D_ACTOR_X+0),a
    ld a,080h
    ld (ix+W3D_ACTOR_X+1),a
    ld a,12
    ld (ix+W3D_ACTOR_X+2),a
    xor a
    ld (ix+W3D_ACTOR_X+3),a
    ld (ix+W3D_ACTOR_Y+0),a
    ld a,080h
    ld (ix+W3D_ACTOR_Y+1),a
    ld a,10
    ld (ix+W3D_ACTOR_Y+2),a
    xor a
    ld (ix+W3D_ACTOR_Y+3),a
    ld (ix+W3D_ACTOR_TILEX),12
    ld (ix+W3D_ACTOR_TILEY),10
    ld (ix+W3D_ACTOR_AREA),0
    ld (ix+W3D_ACTOR_DIR),W3D_DIR_WEST
    ld (ix+W3D_ACTOR_ACTIVE),W3D_ACTOR_ACTIVE_YES
    ld (ix+W3D_ACTOR_CLASS),W3D_CLASS_GUARD
    ld (ix+W3D_ACTOR_FLAGS),W3D_ACTOR_FLAG_SHOOTABLE|W3D_ACTOR_FLAG_ATTACKMODE
    ld (ix+W3D_ACTOR_STATE+0),W3D_STATE_GRD_CHASE1
    ld (ix+W3D_ACTOR_STATE+1),0
    ld (ix+W3D_ACTOR_HITPOINTS+0),25
    ld (ix+W3D_ACTOR_HITPOINTS+1),0
    ld (ix+W3D_ACTOR_SPEED+0),0
    ld (ix+W3D_ACTOR_SPEED+1),2
    ld (ix+W3D_ACTOR_NEXT),W3D_SLOT_NONE
    ld (ix+W3D_ACTOR_PREV),W3D_SLOT_NONE
    ld a,1
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
    ld (w3d_actor_count),a

    xor a
    ld hl,w3d_actorat
    ld (hl),a
    ld de,w3d_actorat+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld a,1
    call w3d_actor_pointer_from_id
    call w3d_actorat_claim

    xor a
    ld (w3d_random_index),a
    ld (w3d_demo_active),a
    ld (w3d_controls),a
    ld (w3d_player_dead),a
    ld (w3d_player_score+0),a
    ld (w3d_player_score+1),a
    ld (w3d_player_score+2),a
    ld (w3d_player_score+3),a
    ld (w3d_player_kill_count+0),a
    ld (w3d_player_kill_count+1),a
    ld a,8
    ld (w3d_player_ammo),a
    ld a,W3D_WEAPON_PISTOL
    ld (w3d_player_weapon),a
    ld (w3d_player_best_weapon),a
    ld (w3d_player_chosen_weapon),a
    xor a
    ld hl,w3d_keyboard_masks
    ld (hl),a
    ld de,w3d_keyboard_masks+1
    ld bc,15
    ldir
    call w3d_initialize_player_combat
    ret

advance_player_quantum:
    call w3d_simulate_player_combat
    xor a
    ld (w3d_actor_tics_prepared),a
    ret

; ---------------------------------------------------------------------------
; Comparators and result mailbox.
; ---------------------------------------------------------------------------

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
    jr nz,@first
    inc hl
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
    ld a,(result_checks+0)
    ld (result_first_check+0),a
    ld a,(result_checks+1)
    ld (result_first_check+1),a
    ld a,(test_case)
    ld (result_first_case),a
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
    ld (test_audio_last_id),a
    ld a,b
    ld (test_audio_gain),a
    ld a,c
    ld (test_audio_flags),a
    ld hl,test_audio_count
    inc (hl)
    jr nz,@done
    inc hl
    inc (hl)
@done:
    or a
    ret
w3d_audio_request_actor:
    jp w3d_audio_request
w3d_audio_request_tile:
    jp w3d_audio_request
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
w3d_gameplay_panel_request:
    db 0

expected_injury_states:
    dw 90
    db 2
    dw 10
    db 0,0
    dw W3D_STATE_GRD_CHASE1
    dw 94
    db 2
    dw 10
    db 0,0
    dw W3D_STATE_GRD_CHASE1
    dw 91
    db 0
    dw 15
    db 0,W3D_STATE_ACTION_DEATH_SCREAM
    dw W3D_STATE_GRD_DIE2
    dw 92
    db 0
    dw 15
    db 0,0
    dw W3D_STATE_GRD_DIE3
    dw 93
    db 0
    dw 15
    db 0,0
    dw W3D_STATE_GRD_DEAD
    dw 131
    db 0
    dw 15
    db 0,W3D_STATE_ACTION_DEATH_SCREAM
    dw W3D_STATE_DOG_DIE2
    dw 132
    db 0
    dw 15
    db 0,0
    dw W3D_STATE_DOG_DIE3
    dw 133
    db 0
    dw 15
    db 0,0
    dw W3D_STATE_DOG_DEAD
    dw 134
    db 0
    dw 15
    db 0,0
    dw W3D_STATE_DOG_DEAD
    dw 278
    db 2
    dw 10
    db 0,0
    dw W3D_STATE_OFC_CHASE1
    dw 282
    db 2
    dw 10
    db 0,0
    dw W3D_STATE_OFC_CHASE1
    dw 279
    db 0
    dw 11
    db 0,W3D_STATE_ACTION_DEATH_SCREAM
    dw W3D_STATE_OFC_DIE2
    dw 280
    db 0
    dw 11
    db 0,0
    dw W3D_STATE_OFC_DIE3
    dw 281
    db 0
    dw 11
    db 0,0
    dw W3D_STATE_OFC_DIE4
    dw 283
    db 0
    dw 11
    db 0,0
    dw W3D_STATE_OFC_DEAD
    dw 284
    db 0
    dw 0
    db 0,0
    dw W3D_STATE_OFC_DEAD
    dw 227
    db 2
    dw 10
    db 0,0
    dw W3D_STATE_MUT_CHASE1
    dw 231
    db 2
    dw 10
    db 0,0
    dw W3D_STATE_MUT_CHASE1
    dw 228
    db 0
    dw 7
    db 0,W3D_STATE_ACTION_DEATH_SCREAM
    dw W3D_STATE_MUT_DIE2
    dw 229
    db 0
    dw 7
    db 0,0
    dw W3D_STATE_MUT_DIE3
    dw 230
    db 0
    dw 7
    db 0,0
    dw W3D_STATE_MUT_DIE4
    dw 232
    db 0
    dw 7
    db 0,0
    dw W3D_STATE_MUT_DEAD
    dw 233
    db 0
    dw 0
    db 0,0
    dw W3D_STATE_MUT_DEAD
    dw 178
    db 2
    dw 10
    db 0,0
    dw W3D_STATE_SS_CHASE1
    dw 182
    db 2
    dw 10
    db 0,0
    dw W3D_STATE_SS_CHASE1
    dw 179
    db 0
    dw 15
    db 0,W3D_STATE_ACTION_DEATH_SCREAM
    dw W3D_STATE_SS_DIE2
    dw 180
    db 0
    dw 15
    db 0,0
    dw W3D_STATE_SS_DIE3
    dw 181
    db 0
    dw 15
    db 0,0
    dw W3D_STATE_SS_DEAD
    dw 183
    db 0
    dw 0
    db 0,0
    dw W3D_STATE_SS_DEAD
expected_injury_states_end:

expected_boss_states:
    dw 304
    db 0
    dw 15
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_DEATH_SCREAM
    dw W3D_STATE_BOSS_DIE2
    dw 305
    db 0
    dw 15
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE
    dw W3D_STATE_BOSS_DIE3
    dw 306
    db 0
    dw 15
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE
    dw W3D_STATE_BOSS_DEAD
    dw 303
    db 0
    dw 0
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE
    dw W3D_STATE_BOSS_DEAD
    dw 300
    db 0
    dw 30
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE
    dw W3D_STATE_BOSS_SHOOT2
    dw 301
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT
    dw W3D_STATE_BOSS_SHOOT3
    dw 302
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT
    dw W3D_STATE_BOSS_SHOOT4
    dw 301
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT
    dw W3D_STATE_BOSS_SHOOT5
    dw 302
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT
    dw W3D_STATE_BOSS_SHOOT6
    dw 301
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT
    dw W3D_STATE_BOSS_SHOOT7
    dw 302
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT
    dw W3D_STATE_BOSS_SHOOT8
    dw 300
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE
    dw W3D_STATE_BOSS_CHASE1
expected_boss_states_end:

report_banner:      db 13,10,"Wolf3D player combat direct regression",13,10,0
report_pass:        db "PASS",13,10,0
report_fail:        db "FAIL",13,10,0
result_filename:    asciz "player_combat_result.bin"
test_phase:         db 0
output_handle:      db 0
assert_expected:    db 0
assert_actual:      db 0

test_audio_begin:
test_audio_count:   dw 0
test_audio_last_id: db 0
test_audio_gain:    db 0
test_audio_flags:   db 0
test_audio_end:
test_case:          db 0

result_data:
    db "W3PC"
result_checks:              dw 0
result_errors:              dw 0
result_first_phase:         db 0
result_first_reason:        db 0
result_first_expected:      db 0
result_first_actual:        db 0
result_schema:              db 1
result_first_check:         dw 0
result_first_case:          db 0
    ds 16
result_end:

test_tilemap:       ds W3D_MAP_BYTES
test_areas:         ds W3D_NUM_AREAS
test_sysvars:       ds 24
