; =============================================================================
; Original-facing floor-completion intermission.
;
; The bundled v1.4 archive does not contain a whole completion screen.
; WL_INTER.C composes it from the level-end portrait/picture alphabet over VGA
; colour 127.  build_hud_assets.py reproduces the invariant 320x200 fields at
; $4100/$4101 and stages the original dynamic glyphs at $4038..$4043.
;
; The original score/count-up state starts immediately and the destination
; floor may begin loading as soon as w3d_intermission_begin returns.  An
; abortable AGNB loader uses w3d_intermission_loading_tick directly: it polls
; Escape, latches a fresh non-Escape acknowledgment, advances the count-up,
; and animates BJ at completed-image boundaries.  After loading,
; w3d_intermission_finish paces any remaining count-up while continuing to
; honor Escape and the complete release/press/release acknowledgment contract.
;
; Kill and treasure totals are derived from the completed floor's immutable
; W3L seeds before the destination package replaces them. Pushwall secret
; count/total state is authoritative in the simulation.  Bonus arithmetic,
; score/life thresholds, and the eight ordinary-floor ratio records match the
; shareware LevelCompleted contract. Its five non-digitized effects are
; rendered offline from the original PC-speaker streams and use the ordinary
; resident buffered-audio path.
; =============================================================================

W3D_INTERMISSION_RESULT_CONTINUE:  equ 0
W3D_INTERMISSION_RESULT_ESCAPE:    equ 2
W3D_INTERMISSION_RESULT_INGRESS:   equ 3
W3D_INTERMISSION_ANIMATION_DIVIDER: equ 4

W3D_INTERMISSION_STAGE_TIME:         equ 0
W3D_INTERMISSION_STAGE_KILL:         equ 1
W3D_INTERMISSION_STAGE_SECRET:       equ 2
W3D_INTERMISSION_STAGE_TREASURE:     equ 3
W3D_INTERMISSION_STAGE_DONE:         equ 4

; Compact durable equivalent of shareware LRstruct.  Values retain the
; original widths (three 16-bit ratios and a 32-bit elapsed-second count) so a
; later save-game/victory implementation can consume them without migration.
W3D_LEVEL_RATIO_KILL:                 equ 0
W3D_LEVEL_RATIO_SECRET:               equ 2
W3D_LEVEL_RATIO_TREASURE:             equ 4
W3D_LEVEL_RATIO_TIME:                 equ 6
W3D_LEVEL_RATIO_SIZE:                 equ 10
W3D_LEVEL_RATIO_COUNT:                equ 8

W3D_INTERMISSION_GUY_1_BUFFER:      equ 04037h
W3D_INTERMISSION_GUY_2_BUFFER:      equ 04060h
W3D_INTERMISSION_FLOOR_BASE_BUFFER:  equ 04100h
W3D_INTERMISSION_SECRET_BASE_BUFFER: equ 04101h
W3D_INTERMISSION_VICTORY_BASE_BUFFER: equ 04102h
W3D_INTERMISSION_STATUSBAR_BUFFER:   equ 04062h
W3D_INTERMISSION_WEAPON_KNIFE_BUFFER: equ 04067h
W3D_INTERMISSION_KEY_NONE_BUFFER:    equ 0406Bh
W3D_INTERMISSION_KEY_GOLD_BUFFER:    equ 0406Ch
W3D_INTERMISSION_KEY_SILVER_BUFFER:  equ 0406Dh
W3D_INTERMISSION_HUD_BLANK_BUFFER:   equ 0406Eh
W3D_INTERMISSION_HUD_DIGIT_0_BUFFER: equ 0406Fh
W3D_INTERMISSION_FACE_1_A_BUFFER:    equ 04079h
W3D_INTERMISSION_FACE_DEAD_BUFFER:   equ 0408Eh
W3D_INTERMISSION_COLON_BUFFER:       equ 04038h
W3D_INTERMISSION_DIGIT_0_BUFFER:     equ 04039h

W3D_INTERMISSION_FLOOR_NUMBER_X:     equ 208
W3D_INTERMISSION_FLOOR_NUMBER_Y:     equ 16
W3D_INTERMISSION_TIME_X:             equ 208
W3D_INTERMISSION_TIME_Y:             equ 80
W3D_INTERMISSION_PAR_X:              equ 208
W3D_INTERMISSION_PAR_Y:              equ 96
W3D_INTERMISSION_KILL_RATIO_Y:       equ 112
W3D_INTERMISSION_SECRET_RATIO_Y:     equ 128
W3D_INTERMISSION_TREASURE_RATIO_Y:   equ 144
W3D_INTERMISSION_BONUS_Y:            equ 56
W3D_INTERMISSION_STATUSBAR_Y:        equ 200

W3D_VICTORY_TIME_X:                  equ 113
W3D_VICTORY_TIME_Y:                  equ 64
W3D_VICTORY_KILL_Y:                  equ 112
W3D_VICTORY_SECRET_Y:                equ 128
W3D_VICTORY_TREASURE_Y:              equ 144

W3D_INTERMISSION_HUD_NUMBER_Y:       equ 216
W3D_INTERMISSION_HUD_LEVEL_X:        equ 16
W3D_INTERMISSION_HUD_SCORE_X:        equ 48
W3D_INTERMISSION_HUD_LIVES_X:        equ 112
W3D_INTERMISSION_HUD_FACE_X:         equ 136
W3D_INTERMISSION_HUD_FACE_Y:         equ 204
W3D_INTERMISSION_HUD_HEALTH_X:       equ 168
W3D_INTERMISSION_HUD_AMMO_X:         equ 216
W3D_INTERMISSION_HUD_KEYS_X:         equ 240
W3D_INTERMISSION_HUD_GOLD_KEY_Y:     equ 204
W3D_INTERMISSION_HUD_SILVER_KEY_Y:   equ 220
W3D_INTERMISSION_HUD_WEAPON_X:       equ 256
W3D_INTERMISSION_HUD_WEAPON_Y:       equ 208

; Called only after the completed floor's asynchronous owner has drained.
; Mode 136 remains allocated for the process lifetime. Complete logical
; intermission states are presented and replayed into the new hidden page so
; neither page exposes stale gameplay or partial count-up state.
;
; This entry point is deliberately nonblocking. It draws the complete source-
; floor result before any destination state can replace that source data, then
; returns A=0/carry clear so loading may begin immediately.
w3d_intermission_begin:
; WL_GAME.C clears gamestate.keys before LevelCompleted draws the completed
; floor.  Do this before composing the retained status bar so a key carried
; into the elevator cannot leak onto the tally screen; destination seeding
; will independently start the next floor with the same empty inventory.
    xor a
    ld (w3d_player_key_flags),a
    xor a
    ld (w3d_intermission_input_armed),a
    ld (w3d_intermission_acknowledged),a
    ld (w3d_intermission_ack_released),a
    ld (w3d_intermission_escape_requested),a
    ld (w3d_intermission_ingress_failed),a
    ld (w3d_intermission_animation_counter),a
    ld (w3d_intermission_portrait_frame),a
    ld (w3d_intermission_bonus_awarded),a
    ld (w3d_intermission_stage_counter+0),a
    ld (w3d_intermission_stage_counter+1),a
    ld (w3d_intermission_current_ratio),a
    ld hl,w3d_intermission_current_bonus
    ld (hl),a
    ld de,w3d_intermission_current_bonus+1
    ld bc,3
    ldir
    call w3d_shell_setup
    ld a,(w3d_level_requested_index)
    cp 9
    jp z,@secret_floor

    ld hl,W3D_INTERMISSION_FLOOR_BASE_BUFFER
    call w3d_shell_plot_full_screen
    call w3d_intermission_draw_statusbar
    call w3d_intermission_draw_floor_number
    call w3d_intermission_draw_time
    call w3d_intermission_draw_par

; Kill ratio: every original seed carrying FL_SHOOTABLE contributes once.
    call w3d_intermission_count_kill_total
    ld bc,0
    ld a,(w3d_player_kill_count+0)
    ld c,a
    ld a,(w3d_player_kill_count+1)
    ld b,a
    call w3d_intermission_percent
    ld (w3d_intermission_kill_ratio),a
    xor a
    ld de,W3D_INTERMISSION_KILL_RATIO_Y
    call w3d_intermission_draw_percentage

; Secret ratio uses original plane-1 marker totals and successful pushes.
    ld de,(w3d_player_secret_total)
    ld bc,(w3d_player_secret_count)
    call w3d_intermission_percent
    ld (w3d_intermission_secret_ratio),a
    xor a
    ld de,W3D_INTERMISSION_SECRET_RATIO_Y
    call w3d_intermission_draw_percentage

; Treasure total matches SpawnStatic: cross/chalice/bible/crown/full-heal.
    call w3d_intermission_count_treasure_total
    ld bc,0
    ld a,(w3d_player_treasure_count+0)
    ld c,a
    ld a,(w3d_player_treasure_count+1)
    ld b,a
    call w3d_intermission_percent
    ld (w3d_intermission_treasure_ratio),a
    xor a
    ld de,W3D_INTERMISSION_TREASURE_RATIO_Y
    call w3d_intermission_draw_percentage
    call w3d_intermission_prepare_ordinary
    call w3d_intermission_draw_bonus
    jr @done

@secret_floor:
    ld hl,W3D_INTERMISSION_SECRET_BASE_BUFFER
    call w3d_shell_plot_full_screen
    ld a,15000&0ffh
    ld (w3d_intermission_final_bonus+0),a
    ld a,15000>>8
    ld (w3d_intermission_final_bonus+1),a
    xor a
    ld (w3d_intermission_final_bonus+2),a
    ld (w3d_intermission_final_bonus+3),a
    ld a,W3D_INTERMISSION_STAGE_DONE
    ld (w3d_intermission_stage),a
    call w3d_intermission_finalize
    call w3d_intermission_draw_statusbar

@done:
    call w3d_intermission_commit_frame
    xor a
    ret

; Shell/intermission presentation remains in mode 136 for the entire process.
; Every completed logical frame is therefore presented once, then rebuilt in
; the new hidden page. This keeps incremental count-up and modal drawing from
; alternating between a current page and stale gameplay pixels.
w3d_intermission_commit_frame:
    call w3d_vdu_present
    jp w3d_intermission_redraw_current_frame

w3d_intermission_redraw_current_frame:
    ld a,(w3d_level_requested_index)
    cp 9
    jr z,@secret

    ld hl,W3D_INTERMISSION_FLOOR_BASE_BUFFER
    call w3d_shell_plot_full_screen
    call w3d_intermission_draw_statusbar
    call w3d_intermission_draw_floor_number
    call w3d_intermission_draw_time
    call w3d_intermission_draw_par

; Values before the active stage are complete, the active ratio uses the
; current count, and later stages remain zero.  TIME precedes every ratio.
    xor a
    ld b,a
    ld a,(w3d_intermission_stage)
    cp W3D_INTERMISSION_STAGE_KILL
    jr c,@kill_ready
    jr z,@kill_current
    ld a,(w3d_intermission_kill_ratio)
    jr @kill_ready_a
@kill_current:
    ld a,(w3d_intermission_current_ratio)
@kill_ready_a:
    ld b,a
@kill_ready:
    ld a,b
    ld de,W3D_INTERMISSION_KILL_RATIO_Y
    call w3d_intermission_draw_percentage

    xor a
    ld b,a
    ld a,(w3d_intermission_stage)
    cp W3D_INTERMISSION_STAGE_SECRET
    jr c,@secret_ready
    jr z,@secret_current
    ld a,(w3d_intermission_secret_ratio)
    jr @secret_ready_a
@secret_current:
    ld a,(w3d_intermission_current_ratio)
@secret_ready_a:
    ld b,a
@secret_ready:
    ld a,b
    ld de,W3D_INTERMISSION_SECRET_RATIO_Y
    call w3d_intermission_draw_percentage

    xor a
    ld b,a
    ld a,(w3d_intermission_stage)
    cp W3D_INTERMISSION_STAGE_TREASURE
    jr c,@treasure_ready
    jr z,@treasure_current
    ld a,(w3d_intermission_treasure_ratio)
    jr @treasure_ready_a
@treasure_current:
    ld a,(w3d_intermission_current_ratio)
@treasure_ready_a:
    ld b,a
@treasure_ready:
    ld a,b
    ld de,W3D_INTERMISSION_TREASURE_RATIO_Y
    call w3d_intermission_draw_percentage
    call w3d_intermission_draw_bonus
    jr @portrait

@secret:
    ld hl,W3D_INTERMISSION_SECRET_BASE_BUFFER
    call w3d_shell_plot_full_screen
    call w3d_intermission_draw_statusbar

@portrait:
    ld a,(w3d_intermission_portrait_frame)
    ld hl,W3D_INTERMISSION_GUY_1_BUFFER
    or a
    jr z,@plot_portrait
    ld hl,W3D_INTERMISSION_GUY_2_BUFFER
@plot_portrait:
    ld bc,0
    ld de,16
    jp w3d_shell_plot_at

; Capture every source-floor value needed after the destination W3L replaces
; the live package, derive the exact original bonus, and persist the ordinary
; LevelRatios record used by the Episode 1 victory averages.
w3d_intermission_prepare_ordinary:
; elapsed seconds = minutes*60 + seconds (the gameplay clock already clamps
; at 99:00, matching the original LevelCompleted cap).
    ld hl,0
    ld a,(w3d_intermission_level_minutes)
    or a
    jr z,@elapsed_seconds
    ld b,a
@elapsed_minutes:
    ld de,60
    add.s hl,de
    djnz @elapsed_minutes
@elapsed_seconds:
    ld de,0
    ld a,(w3d_intermission_level_seconds)
    ld e,a
    add.s hl,de
    ld a,l
    ld (w3d_intermission_elapsed_seconds+0),a
    ld a,h
    ld (w3d_intermission_elapsed_seconds+1),a

; par seconds = displayed minutes*60 + seconds.
    ld hl,0
    ld a,(w3d_intermission_par_minutes)
    or a
    jr z,@par_seconds
    ld b,a
@par_minutes:
    ld de,60
    add.s hl,de
    djnz @par_minutes
@par_seconds:
    ld de,0
    ld a,(w3d_intermission_par_seconds)
    ld e,a
    add.s hl,de

; timeleft = max(par-elapsed,0).
    ld de,0
    ld a,(w3d_intermission_elapsed_seconds+0)
    ld e,a
    ld a,(w3d_intermission_elapsed_seconds+1)
    ld d,a
    or a
    sbc.s hl,de
    jr nc,@timeleft_ready
    ld hl,0
@timeleft_ready:
    ld a,l
    ld (w3d_intermission_timeleft+0),a
    ld a,h
    ld (w3d_intermission_timeleft+1),a

; final bonus starts at timeleft*500.  E1's maximum timeleft is 210, so the
; compact one-time loop is bounded and keeps the arithmetic auditable.
    xor a
    ld hl,w3d_intermission_final_bonus
    ld (hl),a
    ld de,w3d_intermission_final_bonus+1
    ld bc,3
    ldir
    ld bc,0
    ld a,(w3d_intermission_timeleft+0)
    ld c,a
    ld a,(w3d_intermission_timeleft+1)
    ld b,a
@time_bonus_loop:
    ld a,b
    or c
    jr z,@ratio_bonus
    ld de,500
    call w3d_intermission_add_de_to_final_bonus
    dec.s bc
    jr @time_bonus_loop

@ratio_bonus:
    ld a,(w3d_intermission_kill_ratio)
    call w3d_intermission_add_perfect_bonus
    ld a,(w3d_intermission_secret_ratio)
    call w3d_intermission_add_perfect_bonus
    ld a,(w3d_intermission_treasure_ratio)
    call w3d_intermission_add_perfect_bonus
    call w3d_intermission_store_level_ratio

; A zero time bonus skips directly to the kill count-up, exactly as the C
; source skips its first loop when `bonus` is zero.
    ld a,(w3d_intermission_timeleft+0)
    ld b,a
    ld a,(w3d_intermission_timeleft+1)
    or b
    ld a,W3D_INTERMISSION_STAGE_TIME
    jr nz,@stage_ready
    ld a,W3D_INTERMISSION_STAGE_KILL
@stage_ready:
    ld (w3d_intermission_stage),a
    ret

; A=ratio. Add the original 10,000-point perfect-ratio award when A==100.
w3d_intermission_add_perfect_bonus:
    cp 100
    ret nz
    ld de,10000
    jr w3d_intermission_add_de_to_final_bonus

; DE=unsigned 16-bit increment, added to the little-endian final bonus.
w3d_intermission_add_de_to_final_bonus:
    ld a,(w3d_intermission_final_bonus+0)
    add a,e
    ld (w3d_intermission_final_bonus+0),a
    ld a,(w3d_intermission_final_bonus+1)
    adc a,d
    ld (w3d_intermission_final_bonus+1),a
    ld a,(w3d_intermission_final_bonus+2)
    adc a,0
    ld (w3d_intermission_final_bonus+2),a
    ld a,(w3d_intermission_final_bonus+3)
    adc a,0
    ld (w3d_intermission_final_bonus+3),a
    ret

; Store the completed ordinary-floor LRstruct-equivalent.  Intermission is
; never entered for E1L9 victory, but the bound keeps injected regressions and
; future routing changes from corrupting adjacent state.
w3d_intermission_store_level_ratio:
    ld a,(w3d_level_requested_index)
    cp W3D_LEVEL_RATIO_COUNT
    ret nc
    ld hl,w3d_level_ratios
    or a
    jr z,@ratio_address_ready
    ld b,a
@ratio_address:
    ld de,W3D_LEVEL_RATIO_SIZE
    add hl,de
    djnz @ratio_address
@ratio_address_ready:
    ld a,(w3d_intermission_kill_ratio)
    ld (hl),a
    inc hl
    ld (hl),0
    inc hl
    ld a,(w3d_intermission_secret_ratio)
    ld (hl),a
    inc hl
    ld (hl),0
    inc hl
    ld a,(w3d_intermission_treasure_ratio)
    ld (hl),a
    inc hl
    ld (hl),0
    inc hl
    ld a,(w3d_intermission_elapsed_seconds+0)
    ld (hl),a
    inc hl
    ld a,(w3d_intermission_elapsed_seconds+1)
    ld (hl),a
    inc hl
    ld (hl),0
    inc hl
    ld (hl),0
    ret

; Advance exactly one original-facing count-up quantum.  Destination image
; callbacks provide most quanta for free; after loading, finish supplies the
; same routine through an installable pacing hook.
w3d_intermission_advance_countup:
    ld a,(w3d_intermission_stage)
    cp W3D_INTERMISSION_STAGE_DONE
    ret z
    cp W3D_INTERMISSION_STAGE_TIME
    jp z,@time

; Select the active ratio target and its screen row.
    cp W3D_INTERMISSION_STAGE_KILL
    jr nz,@not_kill
    ld a,(w3d_intermission_kill_ratio)
    ld de,W3D_INTERMISSION_KILL_RATIO_Y
    jr @ratio_selected
@not_kill:
    ld a,(w3d_intermission_stage)
    cp W3D_INTERMISSION_STAGE_SECRET
    jr nz,@treasure
    ld a,(w3d_intermission_secret_ratio)
    ld de,W3D_INTERMISSION_SECRET_RATIO_Y
    jr @ratio_selected
@treasure:
    ld a,(w3d_intermission_treasure_ratio)
    ld de,W3D_INTERMISSION_TREASURE_RATIO_Y
@ratio_selected:
    ld (w3d_intermission_ratio_target),a
    ld a,(w3d_intermission_current_ratio)
    call w3d_intermission_draw_percentage

; ENDBONUS1 fires at 0,10,... just as `!(i%10)` in the C source.
    ld a,(w3d_intermission_current_ratio)
    call w3d_intermission_reduce_modulo_ten
    or a
    jr nz,@ratio_no_tick_sound
    ld a,W3D_AUDIO_SOUND_ENDBONUS1
    call w3d_intermission_emit_sound
@ratio_no_tick_sound:
    ld a,(w3d_intermission_current_ratio)
    ld b,a
    ld a,(w3d_intermission_ratio_target)
    cp b
    jr z,@ratio_complete
    ld a,b
    inc a
    ld (w3d_intermission_current_ratio),a
    ret

@ratio_complete:
    ld a,b
    cp 100
    jr nz,@ratio_not_perfect
    ld de,10000
    call w3d_intermission_add_de_to_current_bonus
    call w3d_intermission_draw_bonus
    ld a,W3D_AUDIO_SOUND_PERCENT100
    call w3d_intermission_emit_sound
    jr @next_ratio
@ratio_not_perfect:
    or a
    jr nz,@ratio_partial
    ld a,W3D_AUDIO_SOUND_NOBONUS
    call w3d_intermission_emit_sound
    jr @next_ratio
@ratio_partial:
    ld a,W3D_AUDIO_SOUND_ENDBONUS2
    call w3d_intermission_emit_sound
@next_ratio:
    xor a
    ld (w3d_intermission_current_ratio),a
    ld a,(w3d_intermission_stage)
    inc a
    ld (w3d_intermission_stage),a
    cp W3D_INTERMISSION_STAGE_DONE
    ret nz
    jp w3d_intermission_finalize

@time:
    call w3d_intermission_draw_bonus
; Original time count-up uses the same tick at i=0 and every 50 seconds.
    ld a,(w3d_intermission_stage_counter+1)
    or a
    jr nz,@time_no_tick_sound
    ld a,(w3d_intermission_stage_counter+0)
    or a
    jr z,@time_tick_sound
    cp 50
    jr z,@time_tick_sound
    cp 100
    jr z,@time_tick_sound
    cp 150
    jr z,@time_tick_sound
    cp 200
    jr nz,@time_no_tick_sound
@time_tick_sound:
    ld a,W3D_AUDIO_SOUND_ENDBONUS1
    call w3d_intermission_emit_sound
@time_no_tick_sound:
    ld a,(w3d_intermission_stage_counter+0)
    ld b,a
    ld a,(w3d_intermission_timeleft+0)
    cp b
    jr nz,@time_continue
    ld a,(w3d_intermission_stage_counter+1)
    ld b,a
    ld a,(w3d_intermission_timeleft+1)
    cp b
    jr nz,@time_continue
    ld a,W3D_AUDIO_SOUND_ENDBONUS2
    call w3d_intermission_emit_sound
    ld a,W3D_INTERMISSION_STAGE_KILL
    ld (w3d_intermission_stage),a
    xor a
    ld (w3d_intermission_stage_counter+0),a
    ld (w3d_intermission_stage_counter+1),a
    ret
@time_continue:
    ld hl,w3d_intermission_stage_counter
    inc (hl)
    jr nz,@time_add
    inc hl
    inc (hl)
@time_add:
    ld de,500
    jp w3d_intermission_add_de_to_current_bonus

; DE=unsigned 16-bit increment, added to displayed count-up bonus.
w3d_intermission_add_de_to_current_bonus:
    ld a,(w3d_intermission_current_bonus+0)
    add a,e
    ld (w3d_intermission_current_bonus+0),a
    ld a,(w3d_intermission_current_bonus+1)
    adc a,d
    ld (w3d_intermission_current_bonus+1),a
    ld a,(w3d_intermission_current_bonus+2)
    adc a,0
    ld (w3d_intermission_current_bonus+2),a
    ld a,(w3d_intermission_current_bonus+3)
    adc a,0
    ld (w3d_intermission_current_bonus+3),a
    ret

; A fresh acknowledgment skips only the animation, never its authoritative
; result.  Destination loading and the required release still continue.
w3d_intermission_handle_ack_skip:
    ld a,(w3d_intermission_acknowledged)
    or a
    ret z
    ld a,(w3d_intermission_stage)
    cp W3D_INTERMISSION_STAGE_DONE
    ret z
    jr w3d_intermission_finalize

; Install the exact final display, award points once, and refresh the HUD score
; and lives.  The secret screen already owns its literal "15000 BONUS!" art,
; so it deliberately skips ordinary dynamic fields.
w3d_intermission_finalize:
    ld a,(w3d_intermission_bonus_awarded)
    or a
    ret nz
    ld hl,w3d_intermission_final_bonus
    ld de,w3d_intermission_current_bonus
    ld bc,4
    ldir
    ld a,(w3d_level_requested_index)
    cp 9
    jr z,@award
    ld a,(w3d_intermission_kill_ratio)
    ld de,W3D_INTERMISSION_KILL_RATIO_Y
    call w3d_intermission_draw_percentage
    ld a,(w3d_intermission_secret_ratio)
    ld de,W3D_INTERMISSION_SECRET_RATIO_Y
    call w3d_intermission_draw_percentage
    ld a,(w3d_intermission_treasure_ratio)
    ld de,W3D_INTERMISSION_TREASURE_RATIO_Y
    call w3d_intermission_draw_percentage
    call w3d_intermission_draw_bonus
@award:
    ld hl,w3d_intermission_final_bonus
    call w3d_intermission_award_points
    ld a,1
    ld (w3d_intermission_bonus_awarded),a
    ld a,W3D_INTERMISSION_STAGE_DONE
    ld (w3d_intermission_stage),a
    ld a,(w3d_level_requested_index)
    cp 9
    ret z
    jp w3d_intermission_draw_statusbar

; A=logical sound id.  Production installs an immediate one-quantum transport;
; the focused arithmetic regression retains the no-op default.
w3d_intermission_emit_sound:
    ld hl,(w3d_intermission_sound_hook)
    jp (hl)

w3d_intermission_sound_default:
    ret

; HL -> little-endian u32 points.  The installed hook receives DE=that pointer.
; Production delegates to GivePoints parity;
; the default keeps this include independently testable.
w3d_intermission_award_points:
    push hl
    ld hl,(w3d_intermission_award_hook)
    pop de
    jp (hl)

w3d_intermission_award_default:
    ret

; Nonblocking completed-image callback for the destination AGNB loaders.
;
; Returns A=0/carry clear after an ordinary tick, including a newly latched
; acknowledgment. Returns A=W3D_INTERMISSION_RESULT_ESCAPE/carry set when
; Escape is held. The zero/nonzero result makes this entry point directly
; compatible with agnb_load_images_with_abortable_callback.
w3d_intermission_loading_tick:
    call w3d_music_service
    call w3d_intermission_poll_input
    ret c
    call w3d_intermission_handle_ack_skip

; AGNB's FatFS reads pace the producer only indirectly. During an in-session
; floor transition the emulator can still accept several complete 4 KiB
; bitmap records faster than the VDP parser consumes them, eventually
; blocking the eZ80 in the middle of RST 18h. The installed production hook
; emits a screen-info query and waits for its reply, making every completed
; image an ordered ingress boundary. The default hook is a no-op so focused
; arithmetic/input regressions remain independent of a physical VDP.
    call w3d_intermission_run_ingress_fence
    jr nc,@ingress_ready
    ld a,1
    ld (w3d_intermission_ingress_failed),a
    ld a,W3D_INTERMISSION_RESULT_INGRESS
    scf
    ret
@ingress_ready:

    call w3d_intermission_advance_countup

    ld a,(w3d_intermission_animation_counter)
    inc a
    cp W3D_INTERMISSION_ANIMATION_DIVIDER
    jr nc,@animate
    ld (w3d_intermission_animation_counter),a
    call w3d_intermission_commit_frame
    xor a
    ret

@animate:
    xor a
    ld (w3d_intermission_animation_counter),a
    ld a,(w3d_intermission_portrait_frame)
    xor 1
    ld (w3d_intermission_portrait_frame),a
    ld hl,W3D_INTERMISSION_GUY_1_BUFFER
    or a
    jr z,@plot
    ld hl,W3D_INTERMISSION_GUY_2_BUFFER
@plot:
    ld bc,0
    ld de,16
    call w3d_shell_plot_at
    call w3d_intermission_commit_frame
    xor a
    ret

; Complete the presentation after destination loading. A non-Escape press
; latched by loading_tick avoids waiting for another press, but this still
; waits until a subsequent poll observes every key released. That preserves
; the shell's fresh-press-and-release contract and prevents the acknowledgment
; key from leaking into the destination floor. Escape remains authoritative
; at every lifecycle seam.
;
; Returns A=0/carry clear for normal continuation, or
; A=W3D_INTERMISSION_RESULT_ESCAPE/carry set for application shutdown.
w3d_intermission_finish:
@wait:
    call w3d_intermission_poll_input
    ret c
    call w3d_intermission_handle_ack_skip
    ld a,(w3d_intermission_ack_released)
    or a
    jr z,@advance
    call w3d_intermission_commit_frame
    jr @continue
@advance:
    call w3d_intermission_wait_quantum
    call w3d_intermission_advance_countup
    call w3d_intermission_commit_frame
    jr @wait
@continue:
    xor a
    ret

; Input state machine shared by loading_tick and finish. The installable
; application-exit predicate is queried before the live keymap, preserving a
; short Escape tap latched by an interrupt/keycode callback between foreground
; polls. Either source is recognized before acknowledgment arming, including
; when Escape was already held as this screen appeared. Every other key must
; first be fully released, preventing the elevator/use key which completed the
; floor from auto-acknowledging it.
;
; Returns A=0/carry clear for continue/ack, or Escape result/carry set.
w3d_intermission_poll_input:
    call w3d_intermission_query_application_exit
    or a
    jr nz,@escape
    call w3d_shell_read_keyboard
    bit 0,(ix+14)                  ; Escape is never release-gated
    jr nz,@escape

    ld b,16
@scan:
    ld a,(ix)
    or a
    jr nz,@pressed
    inc ix
    djnz @scan

    ld a,1
    ld (w3d_intermission_input_armed),a
    ld a,(w3d_intermission_acknowledged)
    or a
    jr z,@continue
    ld a,1
    ld (w3d_intermission_ack_released),a
    jr @continue

@pressed:
; Any currently held ordinary key makes it unsafe to enter gameplay, even if
; an earlier acknowledgment had already completed a press/release cycle.
    xor a
    ld (w3d_intermission_ack_released),a
    ld a,(w3d_intermission_input_armed)
    or a
    jr z,@continue                 ; inherited completion key is ignored
    ld a,1
    ld (w3d_intermission_acknowledged),a
@continue:
    xor a
    ret

@escape:
    ld a,1
    ld (w3d_intermission_escape_requested),a
    ld a,W3D_INTERMISSION_RESULT_ESCAPE
    scf
    ret

; Install HL -> application-global exit predicate. The predicate returns
; A=0/Z while the application should continue or A!=0/NZ after any durable
; exit source has fired. This is intentionally independent of a main-owned
; symbol: production may combine its shell latch and render-callback latch,
; while the focused regression injects deterministic state.
w3d_intermission_set_application_exit_query_hook:
    ld (w3d_intermission_application_exit_query_hook),hl
    ret

w3d_intermission_reset_application_exit_query_hook:
    ld hl,w3d_intermission_application_exit_query_default
    ld (w3d_intermission_application_exit_query_hook),hl
    ret

; Install HL -> ordered VDP-ingress fence. The hook returns carry clear when
; all preceding VDU input has been consumed, or carry set after a finite
; transport timeout. It is deliberately separate from Escape so callers can
; report a real asset/transport failure rather than a clean user exit.
w3d_intermission_set_ingress_fence_hook:
    ld (w3d_intermission_ingress_fence_hook),hl
    ret

w3d_intermission_reset_ingress_fence_hook:
    ld hl,w3d_intermission_ingress_fence_default
    ld (w3d_intermission_ingress_fence_hook),hl
    ret

w3d_intermission_run_ingress_fence:
    ld hl,(w3d_intermission_ingress_fence_hook)
    jp (hl)

w3d_intermission_ingress_fence_default:
    xor a
    ret

; Install production lifecycle seams without coupling this reusable include to
; the audio engine, score owner, or MOS clock.
w3d_intermission_set_sound_hook:
    ld (w3d_intermission_sound_hook),hl
    ret

w3d_intermission_reset_sound_hook:
    ld hl,w3d_intermission_sound_default
    ld (w3d_intermission_sound_hook),hl
    ret

w3d_intermission_set_award_hook:
    ld (w3d_intermission_award_hook),hl
    ret

w3d_intermission_reset_award_hook:
    ld hl,w3d_intermission_award_default
    ld (w3d_intermission_award_hook),hl
    ret

w3d_intermission_set_wait_hook:
    ld (w3d_intermission_wait_hook),hl
    ret

w3d_intermission_reset_wait_hook:
    ld hl,w3d_intermission_wait_default
    ld (w3d_intermission_wait_hook),hl
    ret

w3d_intermission_wait_quantum:
    ld hl,(w3d_intermission_wait_hook)
    jp (hl)

w3d_intermission_wait_default:
    ret

w3d_intermission_ingress_has_failed:
    ld a,(w3d_intermission_ingress_failed)
    or a
    ret

w3d_intermission_query_application_exit:
    ld hl,(w3d_intermission_application_exit_query_hook)
    jp (hl)

w3d_intermission_application_exit_query_default:
    xor a
    ret

; NZ means an abortable loader callback observed Escape. AGNB deliberately
; translates a callback's nonzero result to its generic callback-abort code,
; so the transition owner can query this durable latch to distinguish a clean
; user exit from an asset/transport failure.
w3d_intermission_escape_is_requested:
    ld a,(w3d_intermission_escape_requested)
    or a
    ret

w3d_intermission_draw_statusbar:
    ld hl,W3D_INTERMISSION_STATUSBAR_BUFFER
    ld bc,0
    ld de,W3D_INTERMISSION_STATUSBAR_Y
    call w3d_shell_plot_at

; Preserve the exact live gameplay HUD on the original completion screen.
; Chunk 98 is only the invariant panel artwork; every value and icon below is
; a separate original HUD picture and must be composed over it explicitly.
    ld a,(w3d_level_requested_index)
    inc a
    ld bc,W3D_INTERMISSION_HUD_LEVEL_X
    ld de,W3D_INTERMISSION_HUD_NUMBER_Y
    call w3d_intermission_draw_hud_two_digits

    call w3d_intermission_prepare_score_digits
    ld hl,w3d_intermission_score_digits
    ld b,6
    ld de,W3D_INTERMISSION_HUD_NUMBER_Y
    ld ix,W3D_INTERMISSION_HUD_SCORE_X
    call w3d_intermission_draw_hud_digit_string

    ld a,(w3d_player_lives)
    call w3d_intermission_reduce_modulo_ten
    ld bc,W3D_INTERMISSION_HUD_LIVES_X
    ld de,W3D_INTERMISSION_HUD_NUMBER_Y
    call w3d_intermission_draw_hud_digit

    call w3d_intermission_select_face_buffer
    ld bc,W3D_INTERMISSION_HUD_FACE_X
    ld de,W3D_INTERMISSION_HUD_FACE_Y
    call w3d_shell_plot_at

    ld a,(w3d_player_health)
    ld bc,W3D_INTERMISSION_HUD_HEALTH_X
    ld de,W3D_INTERMISSION_HUD_NUMBER_Y
    call w3d_intermission_draw_hud_three_digits

    ld a,(w3d_player_ammo)
    ld bc,W3D_INTERMISSION_HUD_AMMO_X
    ld de,W3D_INTERMISSION_HUD_NUMBER_Y
    call w3d_intermission_draw_hud_two_digits

    ld hl,W3D_INTERMISSION_KEY_NONE_BUFFER
    ld a,(w3d_player_key_flags)
    bit 0,a
    jr z,@gold_ready
    ld hl,W3D_INTERMISSION_KEY_GOLD_BUFFER
@gold_ready:
    ld bc,W3D_INTERMISSION_HUD_KEYS_X
    ld de,W3D_INTERMISSION_HUD_GOLD_KEY_Y
    call w3d_shell_plot_at

    ld hl,W3D_INTERMISSION_KEY_NONE_BUFFER
    ld a,(w3d_player_key_flags)
    bit 1,a
    jr z,@silver_ready
    ld hl,W3D_INTERMISSION_KEY_SILVER_BUFFER
@silver_ready:
    ld bc,W3D_INTERMISSION_HUD_KEYS_X
    ld de,W3D_INTERMISSION_HUD_SILVER_KEY_Y
    call w3d_shell_plot_at

    ld a,(w3d_player_weapon)
    cp 4
    jr c,@weapon_ready
    xor a
@weapon_ready:
    ld l,a
    ld h,0
    inc hl
    dec.s hl
    ld bc,W3D_INTERMISSION_WEAPON_KNIFE_BUFFER
    add.s hl,bc
    ld bc,W3D_INTERMISSION_HUD_WEAPON_X
    ld de,W3D_INTERMISSION_HUD_WEAPON_Y
    jp w3d_shell_plot_at

; A=0..255 -> A=value modulo ten.
w3d_intermission_reduce_modulo_ten:
    cp 10
    ret c
    sub 10
    jr w3d_intermission_reduce_modulo_ten

; A=value, BC=x, DE=y. Draw a right-aligned two-character HUD number with an
; original blank picture in the unused leading position.
w3d_intermission_draw_hud_two_digits:
    push af
    push bc
    push de
    ld l,0
@tens:
    cp 10
    jr c,@two_ready
    sub 10
    inc l
    jr @tens
@two_ready:
    ld (w3d_intermission_hud_remainder),a
    ld a,l
    or a
    jr nz,@draw_tens
    ld a,10
@draw_tens:
    call w3d_intermission_draw_hud_digit
    push bc
    pop hl
    push de
    ld de,8
    add.s hl,de
    pop de
    push hl
    pop bc
    ld a,(w3d_intermission_hud_remainder)
    call w3d_intermission_draw_hud_digit
    pop de
    pop bc
    pop af
    ret

; A=value, BC=x, DE=y. Draw a right-aligned three-character HUD number.
w3d_intermission_draw_hud_three_digits:
    push af
    push bc
    push de
    xor a
    ld (w3d_intermission_hud_started),a
    pop de
    pop bc
    pop af
    push af
    push bc
    push de
    ld l,0
@hundreds:
    cp 100
    jr c,@hundreds_ready
    sub 100
    inc l
    jr @hundreds
@hundreds_ready:
    ld (w3d_intermission_hud_remainder),a
    ld a,l
    or a
    jr nz,@draw_hundreds
    ld a,10
    jr @hundreds_selected
@draw_hundreds:
    ld a,1
    ld (w3d_intermission_hud_started),a
    ld a,l
@hundreds_selected:
    call w3d_intermission_draw_hud_digit
    push bc
    pop hl
    push de
    ld de,8
    add.s hl,de
    pop de
    push hl
    pop bc
    ld a,(w3d_intermission_hud_remainder)
    ld l,0
@health_tens:
    cp 10
    jr c,@health_tens_ready
    sub 10
    inc l
    jr @health_tens
@health_tens_ready:
    ld (w3d_intermission_hud_remainder),a
    ld a,l
    or a
    jr nz,@draw_health_tens
    ld a,(w3d_intermission_hud_started)
    or a
    jr nz,@zero_health_tens
    ld a,10
    jr @health_tens_selected
@zero_health_tens:
    xor a
    jr @health_tens_selected
@draw_health_tens:
    ld a,1
    ld (w3d_intermission_hud_started),a
    ld a,l
@health_tens_selected:
    call w3d_intermission_draw_hud_digit
    push bc
    pop hl
    push de
    ld de,8
    add.s hl,de
    pop de
    push hl
    pop bc
    ld a,(w3d_intermission_hud_remainder)
    call w3d_intermission_draw_hud_digit
    pop de
    pop bc
    pop af
    ret

; A=0..9 draws a numeric HUD glyph; A=10 draws the original blank glyph.
; Coordinates and caller registers are preserved like the completion digits.
w3d_intermission_draw_hud_digit:
    push af
    push bc
    push de
    cp 10
    jr nz,@numeric
    ld hl,W3D_INTERMISSION_HUD_BLANK_BUFFER
    jr @selected
@numeric:
    ld l,a
    ld h,0
    inc hl
    dec.s hl
    push de
    ld de,W3D_INTERMISSION_HUD_DIGIT_0_BUFFER
    add.s hl,de
    pop de
@selected:
    call w3d_shell_plot_at
    pop de
    pop bc
    pop af
    ret

; HL=digit bytes, B=count, IX=x, DE=y. Leading zeroes become blanks but the
; final digit is always shown. The prepared score uses exactly six digits,
; matching the gameplay renderer's modulo-1,000,000 contract.
w3d_intermission_draw_hud_digit_string:
    ld a,(hl)
    ld c,a
    ld a,(w3d_intermission_hud_started)
    or a
    jr nz,@string_digit
    ld a,c
    or a
    jr nz,@start_string
    ld a,b
    cp 1
    jr z,@string_digit
    ld c,10
    jr @string_digit
@start_string:
    ld a,1
    ld (w3d_intermission_hud_started),a
@string_digit:
    push hl
    push bc
    push de
    ld a,c
    push af
    push ix
    pop bc
    pop af
    call w3d_intermission_draw_hud_digit
    pop de
    pop bc
    pop hl
    inc hl
    lea ix,ix+8
    djnz w3d_intermission_draw_hud_digit_string
    ret

; Convert the 32-bit score into its six least-significant decimal digits.
; The in-place divide is bounded: 6 digits * 4 bytes * 8 bits.
w3d_intermission_prepare_score_digits:
    ld hl,w3d_player_score
    jr w3d_intermission_prepare_u32_digits

; HL -> little-endian u32. Result uses the shared six-digit workspace.
w3d_intermission_prepare_u32_digits:
    ld de,w3d_intermission_score_work
    ld bc,4
    ldir
    ld hl,w3d_intermission_score_digits+5
    ld d,6
@score_digit:
    push de
    push hl
    xor a
    ld hl,w3d_intermission_score_work+3
    ld b,(hl)
    call w3d_intermission_divide_score_byte
    ld (hl),c
    dec hl
    ld b,(hl)
    call w3d_intermission_divide_score_byte
    ld (hl),c
    dec hl
    ld b,(hl)
    call w3d_intermission_divide_score_byte
    ld (hl),c
    dec hl
    ld b,(hl)
    call w3d_intermission_divide_score_byte
    ld (hl),c
    pop hl
    ld (hl),a
    dec hl
    pop de
    dec d
    jr nz,@score_digit
    xor a
    ld (w3d_intermission_hud_started),a
    ret

; Draw the current animated bonus as original 16x16 digits, right-aligned at
; x=288 like `Write(36-strlen(tempstr)*2,7,tempstr)` in WL_INTER.C.  Count-up
; values only gain digits, so the invariant background needs no erase pass.
w3d_intermission_draw_bonus:
    ld hl,w3d_intermission_current_bonus
    call w3d_intermission_prepare_u32_digits
    ld ix,w3d_intermission_score_digits
    ld b,6
@find_first:
    ld a,(ix)
    or a
    jr nz,@first_ready
    ld a,b
    cp 1
    jr z,@first_ready
    lea ix,ix+1
    djnz @find_first
@first_ready:
    ld a,b
    ld (w3d_intermission_bonus_digit_count),a
    ld hl,288
    ld de,16
@x_loop:
    or a
    sbc.s hl,de
    djnz @x_loop
    ld a,l
    ld (w3d_intermission_bonus_x+0),a
    ld a,h
    ld (w3d_intermission_bonus_x+1),a
@draw_loop:
    ld a,(ix)
    ld bc,0
    ld a,(w3d_intermission_bonus_x+0)
    ld c,a
    ld a,(w3d_intermission_bonus_x+1)
    ld b,a
    ld de,W3D_INTERMISSION_BONUS_Y
    ld a,(ix)
    call w3d_intermission_draw_digit
    ld hl,16
    add.s hl,bc
    ld a,l
    ld (w3d_intermission_bonus_x+0),a
    ld a,h
    ld (w3d_intermission_bonus_x+1),a
    lea ix,ix+1
    ld a,(w3d_intermission_bonus_digit_count)
    dec a
    ld (w3d_intermission_bonus_digit_count),a
    jr nz,@draw_loop
    ret

; One byte of big-endian long division by ten. A is the incoming remainder
; (0..9), B the next source byte; C receives quotient byte, A the remainder.
w3d_intermission_divide_score_byte:
    ld c,0
    ld e,8
@score_bit:
    sla b
    rla
    sla c
    cp 10
    jr c,@score_bit_ready
    sub 10
    inc c
@score_bit_ready:
    dec e
    jr nz,@score_bit
    ret

; Return HL=the original face chunk for current health, using frame A. This is
; the same health-band calculation as the gameplay renderer.
w3d_intermission_select_face_buffer:
    ld a,(w3d_player_health)
    or a
    jr nz,@living
    ld hl,W3D_INTERMISSION_FACE_DEAD_BUFFER
    ret
@living:
    cp 101
    jr c,@health_valid
    ld a,100
@health_valid:
    ld b,a
    ld a,100
    sub b
    ld b,0
@face_band:
    cp 16
    jr c,@face_ready
    sub 16
    inc b
    jr @face_band
@face_ready:
    ld a,b
    add a,a
    add a,b
    ld l,a
    ld h,0
    inc hl
    dec.s hl
    ld bc,W3D_INTERMISSION_FACE_1_A_BUFFER
    add.s hl,bc
    ret

w3d_intermission_draw_floor_number:
    ld a,(w3d_level_requested_index)
    inc a
    ld bc,W3D_INTERMISSION_FLOOR_NUMBER_X
    ld de,W3D_INTERMISSION_FLOOR_NUMBER_Y
    jp w3d_intermission_draw_digit

w3d_intermission_draw_time:
    ld a,(w3d_intermission_level_minutes)
    ld bc,W3D_INTERMISSION_TIME_X
    ld de,W3D_INTERMISSION_TIME_Y
    call w3d_intermission_draw_two_digits
    ld hl,W3D_INTERMISSION_COLON_BUFFER
    ld bc,W3D_INTERMISSION_TIME_X+32
    ld de,W3D_INTERMISSION_TIME_Y
    call w3d_shell_plot_at
    ld a,(w3d_intermission_level_seconds)
    ld bc,W3D_INTERMISSION_TIME_X+40
    ld de,W3D_INTERMISSION_TIME_Y
    jp w3d_intermission_draw_two_digits

w3d_intermission_draw_par:
    ld a,(w3d_level_requested_index)
    add a,a
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_intermission_par_times
    add hl,de
    ld a,(hl)
    ld (w3d_intermission_par_minutes),a
    inc hl
    ld a,(hl)
    ld (w3d_intermission_par_seconds),a

    ld a,(w3d_intermission_par_minutes)
    ld bc,W3D_INTERMISSION_PAR_X
    ld de,W3D_INTERMISSION_PAR_Y
    call w3d_intermission_draw_two_digits
    ld hl,W3D_INTERMISSION_COLON_BUFFER
    ld bc,W3D_INTERMISSION_PAR_X+32
    ld de,W3D_INTERMISSION_PAR_Y
    call w3d_shell_plot_at
    ld a,(w3d_intermission_par_seconds)
    ld bc,W3D_INTERMISSION_PAR_X+40
    ld de,W3D_INTERMISSION_PAR_Y
    jp w3d_intermission_draw_two_digits

; Return completed-floor kill total in DE.
w3d_intermission_count_kill_total:
    push ix
    ld ix,(w3d_level_actor_seed_ptr)
    ld de,0
    ld a,(w3d_level_actor_count)
    or a
    jr z,@done
    ld b,a
@loop:
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_SHOOTABLE
    jr z,@next
    inc de
@next:
    lea ix,ix+W3D_ACTOR_SIZE
    djnz @loop
@done:
    pop ix
    ret

; Return completed-floor treasure total in DE.  The comparisons deliberately
; mirror the original SpawnStatic treasuretotal set: item 9..12 and item 18.
w3d_intermission_count_treasure_total:
    push ix
    ld ix,(w3d_level_static_seed_ptr)
    ld bc,0
    ld a,(w3d_level_static_count+0)
    ld c,a
    ld a,(w3d_level_static_count+1)
    ld b,a
    ld de,0
    ld a,b
    or c
    jr z,@done
@loop:
    ld a,(ix+W3D_STATIC_ITEMNUMBER)
    cp W3D_ITEM_CROSS
    jr c,@next
    cp W3D_ITEM_CROWN+1
    jr c,@treasure
    cp W3D_ITEM_FULLHEAL
    jr nz,@next
@treasure:
    inc de
@next:
    lea ix,ix+W3D_STATIC_SIZE
    dec.s bc
    ld a,b
    or c
    jr nz,@loop
@done:
    pop ix
    ret

; BC=count, DE=total -> A=floor(count*100/total), capped at 100.  This runs
; once per displayed statistic, so a compact <=100-iteration division is more
; useful than burdening any gameplay hot loop.
w3d_intermission_percent:
    ld a,d
    or e
    jr z,@zero
    push bc
    pop hl
    inc hl
    dec.s hl
    or a
    sbc.s hl,de
    jr nc,@hundred

    ld a,e
    ld (w3d_intermission_divisor+0),a
    ld a,d
    ld (w3d_intermission_divisor+1),a

; HL = count*100 = count*(64+32+4), bounded to 40000 for current totals.
    push bc
    pop hl
    inc hl
    dec.s hl
    add.s hl,hl                 ; 2c
    add.s hl,hl                 ; 4c
    push hl                     ; retain 4c
    add.s hl,hl                 ; 8c
    add.s hl,hl                 ; 16c
    add.s hl,hl                 ; 32c
    push hl                     ; retain 32c
    add.s hl,hl                 ; 64c
    pop bc
    add.s hl,bc                 ; 96c
    pop de
    add.s hl,de                 ; 100c

    ld de,0
    ld a,(w3d_intermission_divisor+0)
    ld e,a
    ld a,(w3d_intermission_divisor+1)
    ld d,a
    ld c,0
@divide:
    or a
    sbc.s hl,de
    jr c,@quotient
    inc c
    jr @divide
@quotient:
    ld a,c
    ret
@hundred:
    ld a,100
    ret
@zero:
    xor a
    ret

; A=0..100, DE=y.  Original Write() right-aligns the significant digits so
; their right edge meets the percent picture at x=296.
w3d_intermission_draw_percentage:
    cp 100
    jr z,@hundred
    cp 10
    jr c,@one_digit
    ld bc,264
    jp w3d_intermission_draw_two_digits
@one_digit:
    ld bc,280
    jp w3d_intermission_draw_digit
@hundred:
    ld a,1
    ld bc,248
    call w3d_intermission_draw_digit
    ld a,0
    ld bc,264
    call w3d_intermission_draw_digit
    ld bc,280
    jp w3d_intermission_draw_digit

; A=0..99, BC=x, DE=y.  Draw exactly two original 16x16 digit pictures.
w3d_intermission_draw_two_digits:
    push af
    push bc
    push de
    push bc
    push de
    ld c,0
@divide_ten:
    cp 10
    jr c,@digits_ready
    sub 10
    inc c
    jr @divide_ten
@digits_ready:
    ld (w3d_intermission_digit_remainder),a
    ld a,c
    ld (w3d_intermission_digit_quotient),a
    pop de
    pop bc
    ld a,(w3d_intermission_digit_quotient)
    call w3d_intermission_draw_digit
    push bc
    pop hl
    push de
    ld de,16
    add.s hl,de
    pop de
    push hl
    pop bc
    ld a,(w3d_intermission_digit_remainder)
    call w3d_intermission_draw_digit
    pop de
    pop bc
    pop af
    ret

; A=digit, BC=x, DE=y. Preserve the caller's registers around the generic VDU
; helpers, whose command buffers legitimately borrow HL/BC/DE.
w3d_intermission_draw_digit:
    push af
    push bc
    push de
    push bc
    push de
    ld l,a
    ld h,0
    inc hl
    dec.s hl
    push hl
    ld de,W3D_INTERMISSION_DIGIT_0_BUFFER
    add.s hl,de
    call selectBitmap
    pop hl
    pop de
    pop bc
    call plotBitmap
    pop de
    pop bc
    pop af
    ret

; ---------------------------------------------------------------------------
; Episode 1 Victory() presentation
; ---------------------------------------------------------------------------

; Reproduce the non-SPEAR WL_INTER.C victory summary from the eight ordinary
; LevelRatios records, then show the exact two-page WL1 ENDART1 article. The
; in-world BJ sequence owns the preceding gameplay phase; this routine begins
; only after its renderer and VDPlet have shut down cleanly.
w3d_victory_present:
    call w3d_victory_calculate_totals
    call @summary
    call w3d_vdu_present
    call @summary
    jr @summary_ready
@summary:
    ld hl,W3D_INTERMISSION_VICTORY_BASE_BUFFER
    call w3d_shell_plot_full_screen
    jp w3d_victory_draw_totals
@summary_ready:
    call w3d_shell_wait_any_press
    call w3d_shell_query_exit_request
    ret nz
    call w3d_victory_end_article
    jp w3d_shell_query_exit_request

; Original WL_TEXT.C ShowArticle navigation over the two pages rendered from
; VGAGRAPH.WL1 chunk 155. The 128 KiB container is loaded only for this ending
; and every buffer is reclaimed on all exit/failure paths. Unlike DOS's local
; article Escape, the Agon application's explicit global-Escape safety policy
; remains authoritative here and requests a clean return to MOS.
w3d_victory_end_article:
    xor a
    ld (w3d_victory_end_page),a
    ld (w3d_victory_end_load_aborted),a
    ld de,end_filename
    ld hl,w3d_victory_end_load_callback
    call agnb_load_images_with_abortable_callback
    jr z,@loaded
    call w3d_victory_end_clear_buffers
    ld a,(w3d_victory_end_load_aborted)
    or a
    jp nz,@finish
; Missing/corrupt optional art must not strand a completed game. The resident
; exact-prose fallback retains the old acknowledgment flow.
    call w3d_victory_draw_end_page_1
    call w3d_shell_wait_any_press
    call w3d_shell_query_exit_request
    jp nz,@finish
    call w3d_victory_draw_end_page_2
    call w3d_shell_wait_any_press
    jp @finish
@loaded:
    call w3d_shell_wait_all_released
    call w3d_shell_query_exit_request
    jp nz,@leave
@draw:
    call w3d_shell_clear
    call w3d_victory_end_plot_page
    call w3d_vdu_present
    call w3d_shell_clear
    call w3d_victory_end_plot_page
@wait:
    call w3d_music_service
    call w3d_shell_read_keyboard
    bit 0,(ix+14)                   ; Escape: application-global clean exit
    jr nz,@escape
    bit 1,(ix+7)                    ; Up
    jr nz,@previous
    bit 1,(ix+3)                    ; Left
    jr nz,@previous
    bit 7,(ix+7)                    ; Page Up
    jr nz,@previous
    bit 1,(ix+5)                    ; Down
    jr nz,@next
    bit 1,(ix+15)                   ; Right
    jr nz,@next
    bit 6,(ix+9)                    ; Page Down
    jr nz,@next
    bit 1,(ix+9)                    ; Return
    jr nz,@next
    bit 4,(ix+7)                    ; keypad Enter
    jr nz,@next
    jr @wait
@previous:
    ld a,(w3d_victory_end_page)
    or a
    jr z,@wait_release
    dec a
    ld (w3d_victory_end_page),a
    jr @changed
@next:
    ld a,(w3d_victory_end_page)
    cp W3D_END_PAGE_COUNT-1
    jr nc,@wait_release
    inc a
    ld (w3d_victory_end_page),a
@changed:
    call w3d_shell_wait_all_released
    call w3d_shell_query_exit_request
    jr nz,@leave
    jr @draw
@wait_release:
    call w3d_shell_wait_all_released
    call w3d_shell_query_exit_request
    jr nz,@leave
    jr @wait
@escape:
    call w3d_shell_request_exit
    call w3d_shell_wait_all_released
@leave:
    call w3d_victory_end_clear_buffers
@finish:
    jp w3d_shell_query_exit_request

w3d_victory_end_plot_page:
    ld hl,W3D_END_PAGE_BUFFER_BASE
    ld a,(w3d_victory_end_page)
    ld e,a
    ld d,0
    add.s hl,de
    jp w3d_shell_plot_full_screen

; Keep URAHERO responsive during the upload. Escape aborts the transfer and
; promotes the common application exit latch before the callback returns NZ.
w3d_victory_end_load_callback:
    call w3d_music_service
    call w3d_shell_read_keyboard
    bit 0,(ix+14)
    jr z,@continue
    call w3d_shell_request_exit
    ld a,1
    ld (w3d_victory_end_load_aborted),a
    ret
@continue:
    xor a
    ret

w3d_victory_end_clear_buffers:
    ld hl,W3D_END_PAGE_BUFFER_BASE
    ld b,W3D_END_PAGE_COUNT
@clear:
    push bc
    push hl
    call vdu_clear_buffer
    pop hl
    pop bc
    inc hl
    djnz @clear
    ret

; Sum u32 time and three u16 percentages, then divide the ratios by eight.
w3d_victory_calculate_totals:
    xor a
    ld hl,w3d_victory_total_seconds
    ld (hl),a
    ld de,w3d_victory_total_seconds+1
    ld bc,9
    ldir
    ld ix,w3d_level_ratios
    ld b,W3D_LEVEL_RATIO_COUNT
@ratio_loop:
    ld a,(w3d_victory_kill_sum+0)
    add a,(ix+W3D_LEVEL_RATIO_KILL+0)
    ld (w3d_victory_kill_sum+0),a
    ld a,(w3d_victory_kill_sum+1)
    adc a,(ix+W3D_LEVEL_RATIO_KILL+1)
    ld (w3d_victory_kill_sum+1),a
    ld a,(w3d_victory_secret_sum+0)
    add a,(ix+W3D_LEVEL_RATIO_SECRET+0)
    ld (w3d_victory_secret_sum+0),a
    ld a,(w3d_victory_secret_sum+1)
    adc a,(ix+W3D_LEVEL_RATIO_SECRET+1)
    ld (w3d_victory_secret_sum+1),a
    ld a,(w3d_victory_treasure_sum+0)
    add a,(ix+W3D_LEVEL_RATIO_TREASURE+0)
    ld (w3d_victory_treasure_sum+0),a
    ld a,(w3d_victory_treasure_sum+1)
    adc a,(ix+W3D_LEVEL_RATIO_TREASURE+1)
    ld (w3d_victory_treasure_sum+1),a
    ld a,(w3d_victory_total_seconds+0)
    add a,(ix+W3D_LEVEL_RATIO_TIME+0)
    ld (w3d_victory_total_seconds+0),a
    ld a,(w3d_victory_total_seconds+1)
    adc a,(ix+W3D_LEVEL_RATIO_TIME+1)
    ld (w3d_victory_total_seconds+1),a
    ld a,(w3d_victory_total_seconds+2)
    adc a,(ix+W3D_LEVEL_RATIO_TIME+2)
    ld (w3d_victory_total_seconds+2),a
    ld a,(w3d_victory_total_seconds+3)
    adc a,(ix+W3D_LEVEL_RATIO_TIME+3)
    ld (w3d_victory_total_seconds+3),a
    lea ix,ix+W3D_LEVEL_RATIO_SIZE
    djnz @ratio_loop

    ld hl,(w3d_victory_kill_sum)
    srl h
    rr l
    srl h
    rr l
    srl h
    rr l
    ld a,l
    ld (w3d_victory_kill_average),a
    ld hl,(w3d_victory_secret_sum)
    srl h
    rr l
    srl h
    rr l
    srl h
    rr l
    ld a,l
    ld (w3d_victory_secret_average),a
    ld hl,(w3d_victory_treasure_sum)
    srl h
    rr l
    srl h
    rr l
    srl h
    rr l
    ld a,l
    ld (w3d_victory_treasure_average),a
    jp w3d_victory_split_time

; Convert the accumulated u32 seconds by bounded repeated subtraction.  The
; original clamps any result beyond 99 minutes to 99:99.
w3d_victory_split_time:
    ld hl,0
    ld (w3d_victory_minutes),hl
@minute_loop:
    ld a,(w3d_victory_total_seconds+3)
    or a
    jr nz,@subtract
    ld a,(w3d_victory_total_seconds+2)
    or a
    jr nz,@subtract
    ld hl,(w3d_victory_total_seconds)
    ld de,60
    or a
    sbc.s hl,de
    jr c,@seconds_ready
@subtract:
    ld a,(w3d_victory_total_seconds+0)
    sub 60
    ld (w3d_victory_total_seconds+0),a
    ld a,(w3d_victory_total_seconds+1)
    sbc a,0
    ld (w3d_victory_total_seconds+1),a
    ld a,(w3d_victory_total_seconds+2)
    sbc a,0
    ld (w3d_victory_total_seconds+2),a
    ld a,(w3d_victory_total_seconds+3)
    sbc a,0
    ld (w3d_victory_total_seconds+3),a
    ld hl,(w3d_victory_minutes)
    inc hl
    ld (w3d_victory_minutes),hl
    ld de,100
    or a
    sbc.s hl,de
    jr c,@minute_loop
    ld a,99
    ld (w3d_victory_minutes),a
    ld (w3d_victory_seconds),a
    ret
@seconds_ready:
    ld a,(w3d_victory_total_seconds)
    ld (w3d_victory_seconds),a
    ret

w3d_victory_draw_totals:
    ld a,(w3d_victory_minutes)
    ld bc,W3D_VICTORY_TIME_X
    ld de,W3D_VICTORY_TIME_Y
    call w3d_intermission_draw_two_digits
    ld hl,W3D_INTERMISSION_COLON_BUFFER
    ld bc,W3D_VICTORY_TIME_X+32
    ld de,W3D_VICTORY_TIME_Y
    call w3d_shell_plot_at
    ld a,(w3d_victory_seconds)
    ld bc,W3D_VICTORY_TIME_X+40
    ld de,W3D_VICTORY_TIME_Y
    call w3d_intermission_draw_two_digits
    ld a,(w3d_victory_kill_average)
    ld de,W3D_VICTORY_KILL_Y
    call w3d_victory_draw_average
    ld a,(w3d_victory_secret_average)
    ld de,W3D_VICTORY_SECRET_Y
    call w3d_victory_draw_average
    ld a,(w3d_victory_treasure_average)
    ld de,W3D_VICTORY_TREASURE_Y
    jp w3d_victory_draw_average

; A=0..100, DE=y.  Victory() right-aligns against column 30 (x=240).
w3d_victory_draw_average:
    cp 100
    jr z,@hundred
    cp 10
    jr c,@one
    ld bc,208
    jp w3d_intermission_draw_two_digits
@one:
    ld bc,224
    jp w3d_intermission_draw_digit
@hundred:
    ld a,1
    ld bc,192
    call w3d_intermission_draw_digit
    xor a
    ld bc,208
    call w3d_intermission_draw_digit
    ld bc,224
    jp w3d_intermission_draw_digit

; Resident fallback for a missing/corrupt end.agnb. These strings retain the
; exact ENDART1 prose while mapping its markup to the native text surface.
w3d_victory_draw_end_page_1:
    call @frame
    call w3d_vdu_present
@frame:
    call w3d_shell_clear
    ld hl,@text
    jp printString
@text:
    db 17,15,62,31,11,2,"CONGRATULATIONS!"
    db 17,15,63,31,2,5,"You run out of the castle and hook up"
    db 31,2,6,"with the Underground. They inform you that"
    db 31,2,7,"the rumors were true: some hideous human"
    db 31,2,8,"experiments were seen around Castle"
    db 31,2,9,"Hollehammer. So Operation Eisenfaust is"
    db 31,2,10,"real!"
    db 31,2,13,"You must journey there and terminate the"
    db 31,2,14,"maniacal Dr. Schabbs before his undead"
    db 31,2,15,"army marches against humanity!"
    db 31,10,22,"Press any key",0

w3d_victory_draw_end_page_2:
    call @frame
    call w3d_vdu_present
@frame:
    call w3d_shell_clear
    ld hl,@text
    jp printString
@text:
    db 17,15,62,31,11,2,"MORE WOLFENSTEIN"
    db 17,15,63,31,2,5,"And in episode three, Hitler hides in"
    db 31,2,6,"his titanic bunker as the Third Reich"
    db 31,2,7,"crumbles about him. It is your job to"
    db 31,2,8,"assassinate him, ending his mad reign."
    db 31,2,11,"And if you like Wolfenstein, you'll love"
    db 31,2,12,"the prequel trilogy of Nocturnal Missions!"
    db 31,2,13,"Thirty more action-packed, super-"
    db 31,2,14,"challenging levels!"
    db 31,2,17,"See the \"Read Me\" choice in the menu"
    db 31,2,18,"for more information or call Apogee at"
    db 31,2,19,"1-800-GAME123!"
    db 31,10,24,"Press any key",0

w3d_intermission_par_times:
    db 1,30, 2,0, 2,0, 3,30, 3,0, 3,0, 2,30, 2,30, 0,0, 0,0

w3d_intermission_par_minutes:
    db 0
w3d_intermission_par_seconds:
    db 0
w3d_intermission_digit_quotient:
    db 0
w3d_intermission_digit_remainder:
    db 0
w3d_intermission_divisor:
    dw 0
w3d_intermission_hud_remainder:
    db 0
w3d_intermission_hud_started:
    db 0
w3d_intermission_score_work:
    ds 4
w3d_intermission_score_digits:
    ds 6
w3d_victory_total_seconds:
    ds 4
w3d_victory_kill_sum:
    dw 0
w3d_victory_secret_sum:
    dw 0
w3d_victory_treasure_sum:
    dw 0
w3d_victory_minutes:
    dw 0
w3d_victory_seconds:
    db 0
w3d_victory_kill_average:
    db 0
w3d_victory_secret_average:
    db 0
w3d_victory_treasure_average:
    db 0
w3d_victory_end_page:
    db 0
w3d_victory_end_load_aborted:
    db 0
w3d_intermission_kill_ratio:
    db 0
w3d_intermission_secret_ratio:
    db 0
w3d_intermission_treasure_ratio:
    db 0
w3d_intermission_ratio_target:
    db 0
w3d_intermission_current_ratio:
    db 0
w3d_intermission_stage:
    db W3D_INTERMISSION_STAGE_DONE
w3d_intermission_stage_counter:
    dw 0
w3d_intermission_elapsed_seconds:
    dw 0
w3d_intermission_timeleft:
    dw 0
w3d_intermission_current_bonus:
    ds 4
w3d_intermission_final_bonus:
    ds 4
w3d_intermission_bonus_awarded:
    db 0
w3d_intermission_bonus_digit_count:
    db 0
w3d_intermission_bonus_x:
    dw 0
w3d_intermission_input_armed:
    db 0
w3d_intermission_acknowledged:
    db 0
w3d_intermission_ack_released:
    db 0
w3d_intermission_escape_requested:
    db 0
w3d_intermission_ingress_failed:
    db 0
w3d_intermission_animation_counter:
    db 0
w3d_intermission_portrait_frame:
    db 0
w3d_intermission_application_exit_query_hook:
    dl w3d_intermission_application_exit_query_default
w3d_intermission_ingress_fence_hook:
    dl w3d_intermission_ingress_fence_default
w3d_intermission_sound_hook:
    dl w3d_intermission_sound_default
w3d_intermission_award_hook:
    dl w3d_intermission_award_default
w3d_intermission_wait_hook:
    dl w3d_intermission_wait_default

; One record for each ordinary E1 floor (E1L1..E1L8). Secret/boss screens do
; not overwrite this table, matching the original victory-average contract.
w3d_level_ratios:
    ds W3D_LEVEL_RATIO_SIZE*W3D_LEVEL_RATIO_COUNT
