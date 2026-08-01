; =============================================================================
; Original ordinary player-weapon combat.
;
; This include owns only the weapon state machine and target/damage dispatch.
; Motion remains authoritative for controls and inventory storage.  Call
; w3d_simulate_player_combat once per fixed update after player movement and
; pickups, before w3d_simulate_actors.  Both then consume the same prepared
; 2,2,3 original-tic quantum.
;
; Integration fields consumed from wolf3d_motion.inc:
;   w3d_controls, w3d_keyboard_masks
;   w3d_player_{dead,ammo,weapon,best_weapon,chosen_weapon}
;   w3d_mark_hud_dirty
; KillActor additionally calls the runtime-static seam:
;   w3d_place_item_type: A=itemnumber, B=tilex, C=tiley
; =============================================================================

W3D_WEAPON_KNIFE:              equ 0
W3D_WEAPON_PISTOL:             equ 1
W3D_WEAPON_MACHINEGUN:         equ 2
W3D_WEAPON_CHAINGUN:           equ 3
W3D_WEAPON_COUNT:              equ 4

W3D_PLAYER_ATTACK_RECORD_SIZE: equ 3
W3D_PLAYER_ATTACK_ROW_SIZE:    equ 12
W3D_PLAYER_ATTACK_FRAME_COUNT: equ 4
; Experimental aiming tune: narrower than the original viewwidth/10 cone.
W3D_PLAYER_SHOOT_DELTA:        equ 16
W3D_PLAYER_KNIFE_RANGE_Q8:     equ 0180h

W3D_PLAYER_ATTACK_NONE:        equ 0
W3D_PLAYER_ATTACK_GUN:         equ 1
W3D_PLAYER_ATTACK_KNIFE:       equ 2
W3D_PLAYER_ATTACK_REPEAT:      equ 3
W3D_PLAYER_ATTACK_CHAIN:       equ 4
W3D_PLAYER_ATTACK_FINISH:      equ 0ffh

W3D_PLAYER_SOUND_NONE:         equ 0
W3D_PLAYER_SOUND_KNIFE:        equ 1
W3D_PLAYER_SOUND_PISTOL:       equ 2
W3D_PLAYER_SOUND_MACHINEGUN:   equ 3
W3D_PLAYER_SOUND_CHAINGUN:     equ 4

; Reset weapon animation state around the already-initialized inventory.
; The resolved shape is dirtied so the VDP integration can submit the ready
; frame (or consume it as part of its initial snapshot).
w3d_initialize_player_combat:
    xor a
    ld (w3d_player_attack_active),a
    ld (w3d_player_attack_was_down),a
    ld (w3d_player_attack_repeat_down),a
    ld (w3d_player_attack_frame),a
    ld (w3d_player_attack_count+0),a
    ld (w3d_player_attack_count+1),a
    ld (w3d_player_weapon_frame),a
    ld (w3d_player_attack_sound),a
    ld (w3d_player_attack_sound_count+0),a
    ld (w3d_player_attack_sound_count+1),a
    ld (w3d_player_last_attack_hit),a
    ld (w3d_player_last_attack_damage),a
    ld (w3d_player_last_damage_result),a
    ld (w3d_player_combat_fault),a
    ld a,W3D_SLOT_NONE
    ld (w3d_player_last_attack_target),a
    ld a,0ffh
    ld (w3d_player_weapon_shape+0),a
    ld (w3d_player_weapon_shape+1),a
    xor a
    ld (w3d_player_weapon_shape_dirty),a
    jp w3d_player_combat_refresh_shape

; Hide the first-person weapon without changing the persistent status-bar
; weapon icon.  Died() uses exactly this distinction.
w3d_hide_player_weapon:
    ld a,0ffh
    ld b,a
    ld a,(w3d_player_weapon_shape+0)
    cp b
    jr nz,@changed
    ld a,(w3d_player_weapon_shape+1)
    cp b
    ret z
@changed:
    ld a,0ffh
    ld (w3d_player_weapon_shape+0),a
    ld (w3d_player_weapon_shape+1),a
    ld a,1
    ld (w3d_player_weapon_shape_dirty),a
    ld (w3d_world_dirty),a
    ret

; Public fixed-step entry.  Weapon selection is available only while idle;
; attacks retain source rising-edge and held automatic-fire behavior.
w3d_simulate_player_combat:
    ld a,(w3d_player_dead)
    or a
    jp nz,w3d_hide_player_weapon
    call w3d_prepare_actor_frame_tics
    call w3d_prepare_actor_sight_context

; A release is remembered even during an attack.  T_Attack suppresses a new
; press during that same animation by clearing buttonstate before it tests the
; automatic-fire records.  Keep a separate effective repeat bit so a repress
; cannot accidentally drive cases 3/4 merely because the physical key is
; down.  We intentionally leave attack_was_down clear: after the animation
; ends, a still-held repress becomes a fresh Cmd_Fire edge on the next fixed
; update, just as PollControls + T_Player do in the original game.
    xor a
    ld (w3d_player_attack_repeat_down),a
    ld a,(w3d_controls)
    and W3D_CONTROL_ATTACK
    jr nz,@attack_key_sampled
    xor a
    ld (w3d_player_attack_was_down),a
@attack_key_sampled:
    ld a,(w3d_player_attack_active)
    or a
    jr z,@idle
    ld a,(w3d_controls)
    and W3D_CONTROL_ATTACK
    jp z,w3d_player_combat_advance_attack
    ld a,(w3d_player_attack_was_down)
    or a
    jp z,w3d_player_combat_advance_attack
    ld a,1
    ld (w3d_player_attack_repeat_down),a
    jp w3d_player_combat_advance_attack

@idle:
    call w3d_player_combat_check_weapon_change
    ld a,(w3d_controls)
    and W3D_CONTROL_ATTACK
    ret z
    ld a,(w3d_player_attack_was_down)
    or a
    ret nz
    ld a,1
    ld (w3d_player_attack_was_down),a
    jp w3d_player_combat_begin_attack

; Source-order 1..4 selection.  Multiple held number keys choose the lowest;
; no weapon may be selected while ammo is zero.
w3d_player_combat_check_weapon_change:
    ld a,(w3d_player_ammo)
    or a
    ret z
    ld ix,w3d_keyboard_masks
    bit 0,(ix+6)                    ; top-row 1
    jr nz,@knife
    bit 1,(ix+6)                    ; top-row 2
    jr nz,@pistol
    bit 1,(ix+2)                    ; top-row 3
    jr nz,@machinegun
    bit 2,(ix+2)                    ; top-row 4
    ret z
    ld b,W3D_WEAPON_CHAINGUN
    jr @select
@machinegun:
    ld b,W3D_WEAPON_MACHINEGUN
    jr @select
@pistol:
    ld b,W3D_WEAPON_PISTOL
    jr @select
@knife:
    ld b,W3D_WEAPON_KNIFE
@select:
    ld a,(w3d_player_best_weapon)
    cp b
    ret c
    ld a,b
    ld (w3d_player_weapon),a
    ld (w3d_player_chosen_weapon),a
    xor a
    ld (w3d_player_weapon_frame),a
    ld a,00001000b                  ; W3D_HUD_DIRTY_WEAPON
    call w3d_mark_hud_dirty
    jp w3d_player_combat_refresh_shape

w3d_player_combat_begin_attack:
    ld a,1
    ld (w3d_player_attack_active),a
    xor a
    ld (w3d_player_attack_frame),a
    ld a,6
    ld (w3d_player_attack_count+0),a
    xor a
    ld (w3d_player_attack_count+1),a
    ld a,1
    ld (w3d_player_weapon_frame),a
    jp w3d_player_combat_refresh_shape

; Advance the active attack with the exact shared source-tic quantum.  Signed
; overshoot is retained, though a normal 2,2,3 step crosses at most one
; six-tic player frame.
w3d_player_combat_advance_attack:
    ld hl,0
    ld a,(w3d_player_attack_count+0)
    ld l,a
    ld a,(w3d_player_attack_count+1)
    ld h,a
    ld de,0
    ld a,(w3d_actor_frame_tics)
    ld e,a
    or a
    sbc.s hl,de
    ld a,l
    ld (w3d_player_attack_count+0),a
    ld a,h
    ld (w3d_player_attack_count+1),a
    bit 7,h
    jr nz,@due
    ld a,h
    or l
    ret nz
@due:
    call w3d_player_combat_attack_record
    jp c,@fault_finish
    ld a,(iy+0)
    ld (w3d_player_attack_record_tics),a
    ld a,(iy+1)
    cp W3D_PLAYER_ATTACK_FINISH
    jp z,w3d_player_combat_finish_attack
    cp W3D_PLAYER_ATTACK_KNIFE
    jr z,@knife
    cp W3D_PLAYER_ATTACK_GUN
    jr z,@gun
    cp W3D_PLAYER_ATTACK_REPEAT
    jr z,@repeat
    cp W3D_PLAYER_ATTACK_CHAIN
    jr z,@chain
    or a
    jr z,@frame_done
    jp @fault_finish

@knife:
    call w3d_player_knife_attack
    jr @frame_done

@repeat:
    ld a,(w3d_player_ammo)
    or a
    jr z,@frame_done
    ld a,(w3d_player_attack_repeat_down)
    or a
    jr z,@frame_done
    ld a,(w3d_player_attack_frame)
    sub 2
    ld (w3d_player_attack_frame),a
    jr @frame_done

@chain:
    ld a,(w3d_player_ammo)
    or a
    jr z,@frame_done
    ld a,(w3d_player_attack_repeat_down)
    or a
    jr z,@gun
    ld a,(w3d_player_attack_frame)
    sub 2
    ld (w3d_player_attack_frame),a
    ; fall through: chain action 4 also fires

@gun:
    ld a,(w3d_player_ammo)
    or a
    jr nz,@fire_gun
    ld hl,w3d_player_attack_frame
    inc (hl)                         ; source's empty-ammo case-1 skip
    jr @frame_done
@fire_gun:
    call w3d_player_gun_attack
    ld hl,w3d_player_ammo
    dec (hl)
    ld a,00000010b                  ; W3D_HUD_DIRTY_AMMO
    call w3d_mark_hud_dirty

@frame_done:
    ld hl,0
    ld a,(w3d_player_attack_count+0)
    ld l,a
    ld a,(w3d_player_attack_count+1)
    ld h,a
    ld de,0
    ld a,(w3d_player_attack_record_tics)
    ld e,a
    add.s hl,de
    ld a,l
    ld (w3d_player_attack_count+0),a
    ld a,h
    ld (w3d_player_attack_count+1),a
    ld hl,w3d_player_attack_frame
    inc (hl)
    call w3d_player_combat_attack_record
    jp c,@fault_finish
    ld a,(iy+2)
    ld (w3d_player_weapon_frame),a
    call w3d_player_combat_refresh_shape

    ld hl,0
    ld a,(w3d_player_attack_count+0)
    ld l,a
    ld a,(w3d_player_attack_count+1)
    ld h,a
    bit 7,h
    jp nz,@due
    ld a,h
    or l
    jp z,@due
    ret

@fault_finish:
    ld a,1
    ld (w3d_player_combat_fault),a
    jp w3d_player_combat_finish_attack

w3d_player_combat_finish_attack:
    xor a
    ld (w3d_player_attack_active),a
    ld (w3d_player_attack_frame),a
    ld (w3d_player_attack_count+0),a
    ld (w3d_player_attack_count+1),a
    ld (w3d_player_weapon_frame),a
    ld a,(w3d_player_ammo)
    or a
    jr nz,@chosen
    ld a,W3D_WEAPON_KNIFE
    jr @weapon_ready
@chosen:
    ld a,(w3d_player_chosen_weapon)
@weapon_ready:
    ld b,a
    ld a,(w3d_player_weapon)
    cp b
    jr z,@refresh
    ld a,b
    ld (w3d_player_weapon),a
    ld a,00001000b                  ; W3D_HUD_DIRTY_WEAPON
    call w3d_mark_hud_dirty
@refresh:
    jp w3d_player_combat_refresh_shape

; IY -> current 3-byte attack record.  Carry reports malformed inventory or
; frame state instead of reading beyond the immutable table.
w3d_player_combat_attack_record:
    ld a,(w3d_player_weapon)
    cp W3D_WEAPON_COUNT
    jr nc,@invalid
    ld d,a
    ld e,W3D_PLAYER_ATTACK_ROW_SIZE
    mlt de
    inc de
    dec.s de
    ld hl,w3d_player_attack_info
    add hl,de
    ld a,(w3d_player_attack_frame)
    cp W3D_PLAYER_ATTACK_FRAME_COUNT
    jr nc,@invalid
    ld d,a
    ld e,W3D_PLAYER_ATTACK_RECORD_SIZE
    mlt de
    inc de
    dec.s de
    add hl,de
    push hl
    pop iy
    or a
    ret
@invalid:
    scf
    ret

; Resolve the current first-person VSWAP shape and publish only a change.
w3d_player_combat_refresh_shape:
    ld a,(w3d_player_weapon)
    cp W3D_WEAPON_COUNT
    jp nc,w3d_hide_player_weapon
    add a,a
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_player_weapon_bases
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,(w3d_player_weapon_frame)
    add a,e
    ld e,a
    jr nc,@shape_ready
    inc d
@shape_ready:
    ld a,(w3d_player_weapon_shape+0)
    cp e
    jr nz,@changed
    ld a,(w3d_player_weapon_shape+1)
    cp d
    ret z
@changed:
    ld a,e
    ld (w3d_player_weapon_shape+0),a
    ld a,d
    ld (w3d_player_weapon_shape+1),a
    ld a,1
    ld (w3d_player_weapon_shape_dirty),a
    ld (w3d_world_dirty),a
    ret

; ---------------------------------------------------------------------------
; Deterministic CPU target selection
; ---------------------------------------------------------------------------

; Return A=nearest ordinary shootable actor in the strict center cone with a
; clear CPU line trace, or W3D_SLOT_NONE.  The original candidate set required
; renderer-owned FL_VISABLE before its final CheckLine.  A write-only VDP
; cannot return that bit, so current projection plus CheckLine is the durable
; synchronous replacement for both guns and the knife.  Filtering each
; candidate also prevents an occluded near actor from masking a farther clear
; one. Equal reduced depths retain linked-list order, matching the source's
; strict `transx < viewdist` comparison after the accepted Q8 reduction.
w3d_player_select_attack_target:
    call w3d_prepare_actor_sight_context
    ld a,W3D_SLOT_NONE
    ld (w3d_player_attack_target),a
    ld (w3d_player_target_scan),a
    ld a,0ffh
    ld (w3d_player_attack_best_depth+0),a
    ld (w3d_player_attack_best_depth+1),a
    ld a,(w3d_actor_live_head)
@loop:
    cp W3D_SLOT_NONE
    jp z,@done
    ld (w3d_player_target_scan),a
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_NEXT)
    ld (w3d_player_target_next),a
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_SHOOTABLE
    jr z,@next
    ld a,(ix+W3D_ACTOR_CLASS)
    cp W3D_CLASS_GUARD
    jr z,@class_ok
    cp W3D_CLASS_OFFICER
    jr z,@class_ok
    cp W3D_CLASS_MUTANT
    jr z,@class_ok
    cp W3D_CLASS_SS
    jr z,@class_ok
    cp W3D_CLASS_DOG
    jr nz,@next
@class_ok:
    call w3d_player_target_in_shoot_cone
    or a
    jr z,@next
    ld iy,w3d_actor_sight_context
    call w3d_CheckLine
    or a
    jr z,@next
    ld hl,0
    ld a,(w3d_actor_projection_nx+0)
    ld l,a
    ld a,(w3d_actor_projection_nx+1)
    ld h,a
    ld de,0
    ld a,(w3d_player_attack_best_depth+0)
    ld e,a
    ld a,(w3d_player_attack_best_depth+1)
    ld d,a
    or a
    sbc.s hl,de
    jr nc,@next                       ; source comparison is strict
    ld a,(w3d_actor_projection_nx+0)
    ld (w3d_player_attack_best_depth+0),a
    ld a,(w3d_actor_projection_nx+1)
    ld (w3d_player_attack_best_depth+1),a
    ld a,(w3d_player_target_scan)
    ld (w3d_player_attack_target),a
@next:
    ld a,(w3d_player_target_next)
    jp @loop
@done:
    ld a,(w3d_player_attack_target)
    ret

; IX=actor.  The existing projection first enforces the complete 0..255
; viewport.  For its signed truncation-toward-zero quotient, the source's
; strict abs(viewx-127)<25 is exactly abs(lateral)*87 < nx*25.
w3d_player_target_in_shoot_cone:
    call w3d_actor_cpu_visible
    or a
    ret z
    ld hl,0
    ld a,(w3d_actor_projection_nx+0)
    ld l,a
    ld a,(w3d_actor_projection_nx+1)
    ld h,a
    ld de,W3D_PLAYER_SHOOT_DELTA
    call w3d_umul16x16_32
    ld a,e
    ld (w3d_player_cone_right_product+0),a
    ld a,d
    ld (w3d_player_cone_right_product+1),a
    ld a,l
    ld (w3d_player_cone_right_product+2),a
    ld a,h
    ld (w3d_player_cone_right_product+3),a

    ld a,(w3d_actor_projection_left_product+3)
    ld b,a
    ld a,(w3d_player_cone_right_product+3)
    cp b
    jr c,@outside
    jr nz,@inside
    ld a,(w3d_actor_projection_left_product+2)
    ld b,a
    ld a,(w3d_player_cone_right_product+2)
    cp b
    jr c,@outside
    jr nz,@inside
    ld a,(w3d_actor_projection_left_product+1)
    ld b,a
    ld a,(w3d_player_cone_right_product+1)
    cp b
    jr c,@outside
    jr nz,@inside
    ld a,(w3d_actor_projection_left_product+0)
    ld b,a
    ld a,(w3d_player_cone_right_product+0)
    cp b
    jr c,@outside
    jr z,@outside                     ; left must be strictly below right
@inside:
    ld a,1
    ret
@outside:
    xor a
    ret

; ---------------------------------------------------------------------------
; Knife and gun actions
; ---------------------------------------------------------------------------

w3d_player_knife_attack:
    ld a,W3D_PLAYER_SOUND_KNIFE
    call w3d_player_publish_attack_sound
    call w3d_player_reset_attack_result
    call w3d_player_select_attack_target
    cp W3D_SLOT_NONE
    ret z
    ld (w3d_player_last_attack_target),a
    ld hl,0
    ld a,(w3d_player_attack_best_depth+0)
    ld l,a
    ld a,(w3d_player_attack_best_depth+1)
    ld h,a
    ld de,W3D_PLAYER_KNIFE_RANGE_Q8+1
    or a
    sbc.s hl,de
    ret nc                            ; inclusive <=0x180 source range
    call w3d_random_byte
    srl a
    srl a
    srl a
    srl a
    jp w3d_player_apply_attack_damage

w3d_player_gun_attack:
    ld a,(w3d_player_weapon)
    inc a                             ; pistol/MG/chain -> sound ids 2/3/4
    call w3d_player_publish_attack_sound
    call w3d_player_reset_attack_result
    call w3d_mark_player_noise        ; every gunshot, including a miss
    call w3d_player_select_attack_target
    cp W3D_SLOT_NONE
    ret z
    ld (w3d_player_last_attack_target),a
    call w3d_actor_pointer_from_id

    call w3d_actor_tile_deltas_abs
    ld a,(w3d_actor_chase_abs_x)
    ld b,a
    ld a,(w3d_actor_chase_abs_y)
    cp b
    jr c,@distance_ready
    ld b,a
@distance_ready:
    ld a,b
    ld (w3d_player_attack_distance),a
    cp 2
    jr c,@near
    cp 4
    jr c,@medium

; Far shots draw once for accuracy and only draw damage after passing
; floor(random/12) >= distance.
    call w3d_random_byte
    ld b,12
    call w3d_actor_u8_div_b
    ld b,a
    ld a,(w3d_player_attack_distance)
    ld c,a
    ld a,b
    cp c
    ret c
    call w3d_random_byte
    call w3d_actor_u8_div6
    jr w3d_player_apply_attack_damage
@medium:
    call w3d_random_byte
    call w3d_actor_u8_div6
    jr w3d_player_apply_attack_damage
@near:
    call w3d_random_byte
    srl a
    srl a
    ; fall through

; A=raw damage and last target is valid.  DamageActor deliberately receives
; zero too, preserving wake/pain behavior and exact RNG semantics.
w3d_player_apply_attack_damage:
    ld (w3d_player_last_attack_damage),a
    ld l,a
    ld h,0
    ld a,(w3d_player_last_attack_target)
    call w3d_damage_actor
    ld (w3d_player_last_damage_result),a
    cp W3D_DAMAGE_RESULT_CORRUPT
    ret z
    cp W3D_DAMAGE_RESULT_REJECTED
    ret z
    ld a,1
    ld (w3d_player_last_attack_hit),a
    ret

w3d_player_reset_attack_result:
    xor a
    ld (w3d_player_last_attack_hit),a
    ld (w3d_player_last_attack_damage),a
    ld (w3d_player_last_damage_result),a
    ld a,W3D_SLOT_NONE
    ld (w3d_player_last_attack_target),a
    ret

; Retain the original observable edge and enqueue its WL1 logical sound at
; full unpositioned gain.  w3d_audio_request owns the request copy, so this
; routine need not retain A/B/C after the call.
w3d_player_publish_attack_sound:
    ld (w3d_player_attack_sound),a
    ld hl,w3d_player_attack_sound_count
    inc (hl)
    jr nz,@map_sound
    inc hl
    inc (hl)
@map_sound:
    ld a,(w3d_player_attack_sound)
    cp W3D_PLAYER_SOUND_KNIFE
    jr z,@knife
    cp W3D_PLAYER_SOUND_PISTOL
    jr z,@pistol
    cp W3D_PLAYER_SOUND_MACHINEGUN
    jr z,@machinegun
    cp W3D_PLAYER_SOUND_CHAINGUN
    ret nz
    ld a,W3D_AUDIO_SOUND_ATKGATLING
    jr @request
@knife:
    ld a,W3D_AUDIO_SOUND_ATKKNIFE
    jr @request
@pistol:
    ld a,W3D_AUDIO_SOUND_ATKPISTOL
    jr @request
@machinegun:
    ld a,W3D_AUDIO_SOUND_ATKMACHINEGUN
@request:
    ld b,127
    ld c,0                          ; unpositioned
    call w3d_audio_request
    ret

; tics, signed action, first-person visual frame
w3d_player_attack_info:
    db 6,0,1, 6,2,2, 6,0,3, 6,0ffh,4
    db 6,0,1, 6,1,2, 6,0,3, 6,0ffh,4
    db 6,0,1, 6,1,2, 6,3,3, 6,0ffh,4
    db 6,0,1, 6,1,2, 6,4,3, 6,0ffh,4

; SPR_*READY bases in the original non-SPEAR WL_DEF.H enum.
w3d_player_weapon_bases:
    dw 416,421,426,431

; ---------------------------------------------------------------------------
; Player-combat-only state and observability
; ---------------------------------------------------------------------------

w3d_player_attack_active:
    db 0
w3d_player_attack_was_down:
    db 0
w3d_player_attack_repeat_down:
    db 0
w3d_player_attack_frame:
    db 0
w3d_player_attack_count:
    dw 0
w3d_player_attack_record_tics:
    db 0
w3d_player_weapon_frame:
    db 0
w3d_player_weapon_shape:
    dw 0ffffh
w3d_player_weapon_shape_dirty:
    db 0
w3d_player_attack_target:
    db W3D_SLOT_NONE
w3d_player_attack_best_depth:
    dw 0ffffh
w3d_player_target_scan:
    db W3D_SLOT_NONE
w3d_player_target_next:
    db W3D_SLOT_NONE
w3d_player_cone_right_product:
    ds 4
w3d_player_attack_distance:
    db 0
w3d_player_last_attack_target:
    db W3D_SLOT_NONE
w3d_player_last_attack_hit:
    db 0
w3d_player_last_attack_damage:
    db 0
w3d_player_last_damage_result:
    db 0
w3d_player_attack_sound:
    db W3D_PLAYER_SOUND_NONE
w3d_player_attack_sound_count:
    dw 0
w3d_player_combat_fault:
    db 0
