; =============================================================================
; Episode 1 in-world victory sequence.
;
; This is the shareware WL_AGENT.C::VictoryTile/VictorySpin and
; WL_ACT2.C::SpawnBJVictory/T_BJRun/T_BJJump/T_BJDone path. Once the player
; reaches EXITTILE, ordinary controls and hostile simulation stop. The player
; turns toward 270 degrees and moves to the scripted camera position while a
; dynamic BJ actor follows the map arrows, runs six cells, jumps, and finally
; latches ex_victorious for the shell.
; =============================================================================

W3D_BJ_RUN_SPEED:              equ 00800h
W3D_BJ_JUMP_SPEED:             equ 002a8h
W3D_VICTORY_PLAYER_SPEED:      equ 01000h
W3D_VICTORY_PLAYER_ANGLE:      equ 270
W3D_VICTORY_ANGLE_SPEED:       equ 3
W3D_VICTORY_RUN_TILES:         equ 6

w3d_initialize_victory_state:
    xor a
    ld (w3d_victory_active),a
    ld a,W3D_SLOT_NONE
    ld (w3d_victory_bj_slot),a
    xor a
    ld hl,w3d_victory_player_target_y
    ld (hl),a
    ld de,w3d_victory_player_target_y+1
    ld bc,3
    ldir
    ret

; Begin the noninteractive in-world sequence. Allocation failure must not trap
; the application in a permanent victoryflag state: it falls forward to the
; post-level victory presentation while retaining the hidden weapon contract.
w3d_begin_victory_sequence:
    ld a,(w3d_victory_active)
    or a
    ret nz
    call w3d_hide_player_weapon

; VictorySpin's destination is based on the player's cached tile at the
; trigger: ((tiley-5)<<16)-0x3000.
    xor a
    ld (w3d_victory_player_target_y+0),a
    ld a,0d0h
    ld (w3d_victory_player_target_y+1),a
    ld a,(w3d_player_pose+6)
    sub 6
    ld (w3d_victory_player_target_y+2),a
    xor a
    ld (w3d_victory_player_target_y+3),a

    call w3d_actor_alloc
    jp nc,@allocation_failed
    ld (w3d_victory_bj_slot),a

; SpawnNewObj(player tilex, player tiley+1, s_bjrun1), then reproduce the
; original pose override and BJ-specific fields.
    ld hl,w3d_player_pose
    push ix
    pop de
    ld bc,8
    ldir
    ld a,(w3d_player_pose+2)
    ld (ix+W3D_ACTOR_TILEX),a
    ld a,(w3d_player_pose+6)
    inc a
    ld (ix+W3D_ACTOR_TILEY),a
    call w3d_actor_area_at_cached_tile
    ld (ix+W3D_ACTOR_AREA),a
    ld a,W3D_DIR_NORTH
    ld (ix+W3D_ACTOR_DIR),a
    ld a,W3D_ACTOR_ACTIVE_ALWAYS
    ld (ix+W3D_ACTOR_ACTIVE),a
    ld a,W3D_CLASS_BJ
    ld (ix+W3D_ACTOR_CLASS),a
    xor a
    ld (ix+W3D_ACTOR_FLAGS),a
    ld (ix+W3D_ACTOR_DISTANCE+0),a
    ld (ix+W3D_ACTOR_DISTANCE+1),a
    ld (ix+W3D_ACTOR_DISTANCE+2),a
    ld (ix+W3D_ACTOR_DISTANCE+3),a
    ld (ix+W3D_ACTOR_ANGLE+0),a
    ld (ix+W3D_ACTOR_ANGLE+1),a
    ld (ix+W3D_ACTOR_HITPOINTS+0),a
    ld (ix+W3D_ACTOR_HITPOINTS+1),a
    ld (ix+W3D_ACTOR_SPEED+0),a
    ld a,08h
    ld (ix+W3D_ACTOR_SPEED+1),a
    xor a
    ld (ix+W3D_ACTOR_SPEED+2),a
    ld (ix+W3D_ACTOR_SPEED+3),a
    ld a,W3D_VICTORY_RUN_TILES
    ld (ix+W3D_ACTOR_TEMP1+0),a
    xor a
    ld (ix+W3D_ACTOR_TEMP1+1),a
    ld (ix+W3D_ACTOR_TEMP2+0),a
    ld (ix+W3D_ACTOR_TEMP2+1),a
    ld (ix+W3D_ACTOR_TEMP3+0),a
    ld (ix+W3D_ACTOR_TEMP3+1),a
    ld a,W3D_STATE_BJ_RUN1
    ld (ix+W3D_ACTOR_STATE+0),a
    xor a
    ld (ix+W3D_ACTOR_STATE+1),a

; SpawnNewObj consumes one US_RndT byte and seeds ticcount modulo 12.
    call w3d_random_byte
@mod12:
    cp 12
    jr c,@ticcount_ready
    sub 12
    jr @mod12
@ticcount_ready:
    ld (ix+W3D_ACTOR_TICCOUNT+0),a
    xor a
    ld (ix+W3D_ACTOR_TICCOUNT+1),a
    ld a,(w3d_victory_bj_slot)
    call w3d_actor_publish
    ld a,1
    ld (w3d_victory_active),a
    ld (w3d_player_dirty),a
    ld (w3d_world_dirty),a
    or a
    ret

@allocation_failed:
    ld a,W3D_LEVEL_COMPLETION_VICTORY
    ld (w3d_level_completion),a
    or a
    ret

; One fixed gameplay quantum after victoryflag. Only the player camera and BJ
; actor advance; doors, pushwalls, pickups, weapons, and hostile actors freeze.
w3d_simulate_victory_step:
    call w3d_prepare_actor_frame_tics
    call w3d_victory_spin_player
    ld a,(w3d_victory_bj_slot)
    cp W3D_SLOT_NONE
    jr z,@fail_forward
    ld (w3d_current_actor_index),a
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_ACTIVE)
    cp W3D_ACTOR_ACTIVE_FREE
    jr z,@fail_forward
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_NONMARK|W3D_ACTOR_FLAG_NEVERMARK
    jr nz,@run
    ld a,(w3d_current_actor_index)
    call w3d_actorat_release
@run:
    call w3d_actor_run_current
    jr c,@fail_forward
    ld a,(w3d_current_actor_index)
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_NONMARK|W3D_ACTOR_FLAG_NEVERMARK
    jr nz,@done
    ld a,(w3d_current_actor_index)
    call w3d_actorat_claim
@done:
    xor a
    ld (w3d_actor_tics_prepared),a
    ld (w3d_player_made_noise),a
    ret
@fail_forward:
    ld a,W3D_LEVEL_COMPLETION_VICTORY
    ld (w3d_level_completion),a
    jr @done

; VictorySpin: converge angle at 3 degrees/original tic and y at 4096
; units/original tic, clamping both without wrap or overshoot.
w3d_victory_spin_player:
    call w3d_load_player_angle
    ld de,W3D_VICTORY_PLAYER_ANGLE
    or a
    sbc.s hl,de
    jr z,@move_y
    jr c,@turn_up
; Current angle > 270.
    ld hl,0
    ld a,(w3d_actor_frame_tics)
    ld l,a
    add.s hl,hl
    ld de,0
    ld e,a
    add.s hl,de                     ; tics * 3
    push hl
    call w3d_load_player_angle
    ex de,hl
    pop hl
    ex de,hl
    or a
    sbc.s hl,de
    ld de,W3D_VICTORY_PLAYER_ANGLE
    push hl
    or a
    sbc.s hl,de
    pop hl
    jr nc,@store_angle
    ld hl,W3D_VICTORY_PLAYER_ANGLE
    jr @store_angle
@turn_up:
    ld hl,0
    ld a,(w3d_actor_frame_tics)
    ld l,a
    add.s hl,hl
    ld de,0
    ld e,a
    add.s hl,de
    push hl
    call w3d_load_player_angle
    ex de,hl
    pop hl
    add.s hl,de
    ld de,W3D_VICTORY_PLAYER_ANGLE
    push hl
    or a
    sbc.s hl,de
    pop hl
    jr c,@store_angle
    ld hl,W3D_VICTORY_PLAYER_ANGLE
@store_angle:
    ld a,l
    ld (w3d_player_pose+8),a
    ld a,h
    ld (w3d_player_pose+9),a
    ld a,1
    ld (w3d_player_dirty),a

@move_y:
    ld hl,(w3d_player_pose+4)
    ld de,(w3d_victory_player_target_y)
    or a
    sbc hl,de
    ret c
    ld a,h
    or l
    ret z
    ld hl,W3D_VICTORY_PLAYER_SPEED*2
    ld a,(w3d_actor_frame_tics)
    cp 3
    jr nz,@y_step_ready
    ld de,W3D_VICTORY_PLAYER_SPEED
    add hl,de
@y_step_ready:
    ld de,(w3d_player_pose+4)
    ex de,hl
    or a
    sbc hl,de
    ld de,(w3d_victory_player_target_y)
    push hl
    or a
    sbc hl,de
    pop hl
    jr nc,@store_y
    ld hl,(w3d_victory_player_target_y)
@store_y:
    ld (w3d_player_pose+4),hl
    xor a
    ld (w3d_player_pose+7),a
    inc a
    ld (w3d_player_dirty),a
    ret

; IX=current BJ. Exact T_BJRun budget and center/path-arrow loop.
w3d_victory_think_bj_run:
    ld hl,W3D_BJ_RUN_SPEED*2
    ld a,(w3d_actor_frame_tics)
    cp 3
    jr nz,@budget_ready
    ld de,W3D_BJ_RUN_SPEED
    add hl,de
@budget_ready:
    ld (w3d_actor_move_remaining),hl
@loop:
    ld hl,(w3d_actor_move_remaining)
    ld a,h
    or l
    ret z
    ld de,(ix+W3D_ACTOR_DISTANCE)
    or a
    sbc hl,de
    jr nc,@reach_center
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
    ld hl,0
    ld l,(ix+W3D_ACTOR_TEMP1+0)
    ld h,(ix+W3D_ACTOR_TEMP1+1)
    dec.s hl
    ld (ix+W3D_ACTOR_TEMP1+0),l
    ld (ix+W3D_ACTOR_TEMP1+1),h
    ld a,h
    or l
    jr nz,@continue
    ld hl,W3D_STATE_BJ_JUMP1
    jp w3d_actor_new_state16
@continue:
    ld a,(ix+W3D_ACTOR_DIR)
    cp W3D_DIR_NODIR
    ret nc
    jr @loop

w3d_victory_think_bj_jump:
    ld hl,W3D_BJ_JUMP_SPEED*2
    ld a,(w3d_actor_frame_tics)
    cp 3
    jr nz,@move
    ld de,W3D_BJ_JUMP_SPEED
    add hl,de
@move:
    ld (w3d_actor_move_amount),hl
    jp w3d_actor_move_obj

; YEAHSND is not present in the WL1 audio corpus. Retain the action edge as a
; successful no-op instead of substituting a non-original effect.
w3d_victory_bj_yell:
    or a
    ret

w3d_victory_bj_done:
    ld a,W3D_LEVEL_COMPLETION_VICTORY
    ld (w3d_level_completion),a
    or a
    ret

w3d_victory_active:
    db 0
w3d_victory_bj_slot:
    db W3D_SLOT_NONE
w3d_victory_player_target_y:
    dl 0
    db 0
