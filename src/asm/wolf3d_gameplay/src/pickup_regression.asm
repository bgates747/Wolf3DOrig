; Directed real-eZ80 regression for production Wolf3D pickup state.
;
; This deliberately includes and calls src/asm/wolf3d/src/wolf3d_motion.inc.
; Each table record seeds one authoritative W3D_STATIC_SIZE slot, invokes
; w3d_apply_current_pickup, and validates every gameplay/HUD mutation plus
; the complete per-static dirty array.  pickup_result.bin is a compact
; 16-byte mailbox decoded by run_pickup_emulator_regression.py.

    assume adl=1
    org 0x040000
    jp start
    align 64
    db "MOS",0,1

mos_getkbmap:       equ 0x1e
mos_fopen:          equ 0x0a
mos_fclose:         equ 0x0b
mos_fwrite:         equ 0x1b
fa_write:           equ 0x02
fa_create_always:   equ 0x08

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    include "wolf3d_backend.inc"
    include "wolf3d_audio_assets.inc"
    include "wolf3d_sight.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_actors.inc"
    include "wolf3d_areas.inc"
; This focused fixture does not include the victory presentation module, but
; production actor simulation exposes its BJ callbacks.
w3d_victory_think_bj_jump:
w3d_victory_think_bj_run:
w3d_victory_bj_yell:
w3d_victory_bj_done:
    ret
    include "wolf3d_actor_sim.inc"
w3d_initialize_victory_state:
    xor a
    ld (w3d_victory_active),a
    ret
w3d_begin_victory_sequence:
w3d_simulate_victory_step:
    ret
w3d_victory_active:
    db 0
    include "wolf3d_motion.inc"
    include "wolf3d_player_combat.inc"

rec_item:               equ 0
rec_slot:               equ 1       ; uint16
rec_initial_health:     equ 3
rec_initial_ammo:       equ 4
rec_initial_keys:       equ 5
rec_initial_weapon:     equ 6
rec_initial_best:       equ 7
rec_initial_chosen:     equ 8
rec_initial_lives:      equ 9
rec_initial_score:      equ 10      ; uint32
rec_initial_next:       equ 14      ; uint32
rec_initial_treasure:   equ 18      ; uint16
rec_expected_return:    equ 20
rec_expected_health:    equ 21
rec_expected_ammo:      equ 22
rec_expected_keys:      equ 23
rec_expected_weapon:    equ 24
rec_expected_best:      equ 25
rec_expected_chosen:    equ 26
rec_expected_lives:     equ 27
rec_expected_score:     equ 28      ; uint32
rec_expected_next:      equ 32      ; uint32
rec_expected_treasure:  equ 36      ; uint16
rec_expected_hud:       equ 38
rec_expected_world:     equ 39
rec_expected_shape:     equ 40      ; int16
rec_expected_dirty:     equ 42
record_size:            equ 43
pickup_case_count:      equ 13

reason_return:          equ 1
reason_health:          equ 2
reason_ammo:            equ 3
reason_keys:            equ 4
reason_weapon:          equ 5
reason_best_weapon:     equ 6
reason_chosen_weapon:   equ 7
reason_lives:           equ 8
reason_score:           equ 9
reason_next_extra:      equ 10
reason_hud_dirty:       equ 11
reason_world_dirty:     equ 12
reason_shape:           equ 13
reason_static_dirty:    equ 14
reason_dirty_count:     equ 15
reason_player_dirty:    equ 16
reason_treasure_count:  equ 17
reason_audio:           equ 18

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
    ld (result_records),a
    ld (result_errors),a
    ld (result_first_reason),a
    ld (result_first_expected),a
    ld (result_first_actual),a
    dec a
    ld (result_first_case),a

    ld iy,pickup_cases
    ld b,pickup_case_count
@loop:
    push bc
    call run_case
    lea iy,iy+record_size
    pop bc
    djnz @loop

    call test_pickup_audio
    call test_chaingun_face
    call test_score32_bonus
    call test_score_capped_sound
    call write_result
    call print_report
    ret

; Exercise every successful GetBonus sound branch plus representative refusal
; and unsupported cases. Records are item, initial health/ammo, consumed, id;
; id FF means no request is permitted.
audio_case_item:       equ 0
audio_case_health:     equ 1
audio_case_ammo:       equ 2
audio_case_consumed:   equ 3
audio_case_sound:      equ 4
audio_case_size:       equ 5
audio_case_count:      equ 18

test_pickup_audio:
    ld iy,pickup_audio_cases
    ld b,audio_case_count
@loop:
    push bc
    xor a
    ld (case_failed),a
    call prepare_audio_pickup
    call w3d_apply_current_pickup
    ld b,(iy+audio_case_consumed)
    ld c,reason_audio
    call assert_equal

    ld a,(iy+audio_case_sound)
    cp 0ffh
    jr z,@silent
    ld b,a
    ld a,(test_audio_count)
    push bc
    ld b,1
    call assert_equal
    pop bc
    ld a,(test_audio_last_id)
    call assert_equal
    ld a,(test_audio_arg_b)
    ld b,127
    ld c,reason_audio
    call assert_equal
    ld a,(test_audio_arg_c)
    ld b,0
    call assert_equal
    jr @finished
@silent:
    ld a,(test_audio_count)
    ld b,0
    ld c,reason_audio
    call assert_equal
@finished:
    ld a,(result_records)
    inc a
    ld (result_records),a
    lea iy,iy+audio_case_size
    pop bc
    djnz @loop
    ret

; The source draws GOTGATLINGPIC for every chaingun pickup, including when the
; player already owns the weapon.  Pin the transient presentation and its
; generated duration independently of the table-driven inventory cases.
test_chaingun_face:
    ld iy,pickup_audio_chaingun
    call prepare_audio_pickup
    ld a,W3D_WEAPON_CHAINGUN
    ld (w3d_player_weapon),a
    ld (w3d_player_best_weapon),a
    ld (w3d_player_chosen_weapon),a
    ld a,55
    ld (w3d_player_face_count+0),a
    xor a
    ld (w3d_player_face_count+1),a
    ld (w3d_hud_dirty),a
    call w3d_apply_current_pickup
    ld b,1
    ld c,reason_return
    call assert_equal
    ld a,(w3d_player_face_special)
    ld b,1
    ld c,reason_health
    call assert_equal
    ld a,(w3d_player_face_special_ticks)
    ld b,W3D_AUDIO_GETGATLING_HOLD_TICKS
    ld c,reason_health
    call assert_equal
    ld a,(w3d_player_face_count+0)
    ld b,0
    ld c,reason_health
    call assert_equal
    ld a,(w3d_hud_dirty)
    and W3D_HUD_DIRTY_FACE
    ld b,W3D_HUD_DIRTY_FACE
    ld c,reason_hud_dirty
    call assert_equal

; Full heal always calls HealSelf in the source. It therefore cancels the
; special face even when health was already 100 and no health digit changes.
    ld iy,pickup_audio_fullheal
    call prepare_audio_pickup
    ld a,100
    ld (w3d_player_health),a
    call w3d_begin_chaingun_face
    call w3d_apply_current_pickup
    ld a,(w3d_player_face_special)
    ld b,0
    ld c,reason_health
    call assert_equal
    ret

; Floor completion may award 135,000 points in one call. Exercise the shipping
; 32-bit GivePoints path across four extra-life thresholds.
test_score32_bonus:
    xor a
    ld (case_failed),a
    call test_audio_reset
    ld (w3d_hud_dirty),a
    ld (w3d_world_dirty),a
    ld (w3d_player_score+2),a
    ld (w3d_player_score+3),a
    ld (w3d_player_next_extra+2),a
    ld (w3d_player_next_extra+3),a
    ld a,0dch
    ld (w3d_player_score+0),a
    ld a,09bh
    ld (w3d_player_score+1),a
    ld a,040h
    ld (w3d_player_next_extra+0),a
    ld a,09ch
    ld (w3d_player_next_extra+1),a
    ld a,3
    ld (w3d_player_lives),a
    ld hl,test_score32_increment
    call w3d_add_player_score32_ptr
    ld hl,w3d_player_score
    ld de,test_score32_expected
    ld c,reason_score
    call assert_four_bytes
    ld hl,w3d_player_next_extra
    ld de,test_score32_next
    ld c,reason_next_extra
    call assert_four_bytes
    ld a,(w3d_player_lives)
    ld b,7
    ld c,reason_lives
    call assert_equal
    ld a,(w3d_hud_dirty)
    ld b,W3D_HUD_DIRTY_SCORE|W3D_HUD_DIRTY_LIVES
    ld c,reason_hud_dirty
    call assert_equal
    ld a,(w3d_world_dirty)
    ld b,1
    ld c,reason_world_dirty
    call assert_equal
    ld a,(test_audio_count+0)
    ld b,4
    ld c,reason_audio
    call assert_equal
    ld a,(test_audio_count+1)
    ld b,0
    ld c,reason_audio
    call assert_equal
    ld a,(test_audio_last_id)
    ld b,W3D_AUDIO_SOUND_BONUS1UP
    ld c,reason_audio
    call assert_equal
    ld a,(test_audio_arg_b)
    ld b,127
    ld c,reason_audio
    call assert_equal
    ld a,(test_audio_arg_c)
    ld b,0
    ld c,reason_audio
    call assert_equal
    ld a,(result_records)
    inc a
    ld (result_records),a
    ret

; GiveExtraMan still plays BONUS1UPSND when the nine-life cap suppresses the
; inventory/HUD mutation. The score and next threshold must advance normally.
test_score_capped_sound:
    xor a
    ld (case_failed),a
    call test_audio_reset
    ld (w3d_hud_dirty),a
    ld (w3d_world_dirty),a
    ld (w3d_player_score+2),a
    ld (w3d_player_score+3),a
    ld (w3d_player_next_extra+2),a
    ld (w3d_player_next_extra+3),a
    ld a,0dch
    ld (w3d_player_score+0),a
    ld a,09bh
    ld (w3d_player_score+1),a
    ld a,040h
    ld (w3d_player_next_extra+0),a
    ld a,09ch
    ld (w3d_player_next_extra+1),a
    ld a,9
    ld (w3d_player_lives),a
    ld hl,100
    call w3d_add_player_score
    ld hl,w3d_player_score
    ld de,test_score_capped_expected
    ld c,reason_score
    call assert_four_bytes
    ld hl,w3d_player_next_extra
    ld de,test_score_capped_next
    ld c,reason_next_extra
    call assert_four_bytes
    ld a,(w3d_player_lives)
    ld b,9
    ld c,reason_lives
    call assert_equal
    ld a,(w3d_hud_dirty)
    ld b,W3D_HUD_DIRTY_SCORE
    ld c,reason_hud_dirty
    call assert_equal
    ld a,(w3d_world_dirty)
    ld b,1
    ld c,reason_world_dirty
    call assert_equal
    ld a,(test_audio_count+0)
    ld b,1
    ld c,reason_audio
    call assert_equal
    ld a,(test_audio_count+1)
    ld b,0
    ld c,reason_audio
    call assert_equal
    ld a,(test_audio_last_id)
    ld b,W3D_AUDIO_SOUND_BONUS1UP
    ld c,reason_audio
    call assert_equal
    ld a,(test_audio_arg_b)
    ld b,127
    ld c,reason_audio
    call assert_equal
    ld a,(test_audio_arg_c)
    ld b,0
    ld c,reason_audio
    call assert_equal
    ld a,(result_records)
    inc a
    ld (result_records),a
    ret

prepare_audio_pickup:
    call test_audio_reset
    xor a
    ld (w3d_hud_dirty),a
    ld (w3d_world_dirty),a
    ld (w3d_player_key_flags),a
    ld (w3d_player_score+0),a
    ld (w3d_player_score+1),a
    ld (w3d_player_score+2),a
    ld (w3d_player_score+3),a
    ld (w3d_player_treasure_count+0),a
    ld (w3d_player_treasure_count+1),a
    ld (w3d_player_attack_frame),a
    ld (w3d_player_next_extra+2),a
    ld (w3d_player_next_extra+3),a
    ld a,040h
    ld (w3d_player_next_extra+0),a
    ld a,09ch
    ld (w3d_player_next_extra+1),a
    ld hl,0
    ld (w3d_current_static_index),hl
    ld a,(iy+audio_case_health)
    ld (w3d_player_health),a
    ld a,(iy+audio_case_ammo)
    ld (w3d_player_ammo),a
    ld a,3
    ld (w3d_player_lives),a
    ld a,W3D_WEAPON_PISTOL
    ld (w3d_player_weapon),a
    ld (w3d_player_best_weapon),a
    ld (w3d_player_chosen_weapon),a
    ld ix,w3d_statics
    xor a
    ld (ix+W3D_STATIC_TILEX),a
    ld (ix+W3D_STATIC_TILEY),a
    ld (ix+W3D_STATIC_SHAPENUM+1),a
    ld a,1
    ld (ix+W3D_STATIC_SHAPENUM+0),a
    ld a,W3D_STATIC_FLAG_BONUS
    ld (ix+W3D_STATIC_FLAGS),a
    ld a,(iy+audio_case_item)
    ld (ix+W3D_STATIC_ITEMNUMBER),a
    ret

run_case:
    xor a
    ld (case_failed),a
    call prepare_case
    call w3d_apply_current_pickup
    ld (actual_return),a
    call validate_case
    ld a,(result_records)
    inc a
    ld (result_records),a
    ret

prepare_case:
    ; Every case begins with completely clean authoritative static/dirty state.
    xor a
    ld hl,w3d_statics
    ld (hl),a
    ld de,w3d_statics+1
    ld bc,W3D_FIXTURE_STATIC_COUNT*W3D_STATIC_SIZE-1
    ldir
    ld hl,w3d_static_dirty
    ld (hl),a
    ld de,w3d_static_dirty+1
    ld bc,W3D_FIXTURE_STATIC_COUNT-1
    ldir
    ld (w3d_hud_dirty),a
    ld (w3d_world_dirty),a
    ld (w3d_player_dirty),a
    ld (w3d_palette_damage_count+0),a
    ld (w3d_palette_damage_count+1),a
    ld (w3d_palette_bonus_count+0),a
    ld (w3d_palette_bonus_count+1),a
    ld (w3d_palette_tick_phase),a
    ld (w3d_palette_shift_wire),a

    ld a,(iy+rec_initial_health)
    ld (w3d_player_health),a
    ld a,(iy+rec_initial_ammo)
    ld (w3d_player_ammo),a
    ld a,(iy+rec_initial_keys)
    ld (w3d_player_key_flags),a
    ld a,(iy+rec_initial_weapon)
    ld (w3d_player_weapon),a
    ld a,(iy+rec_initial_best)
    ld (w3d_player_best_weapon),a
    ld a,(iy+rec_initial_chosen)
    ld (w3d_player_chosen_weapon),a
    ld a,(iy+rec_initial_lives)
    ld (w3d_player_lives),a
    lea hl,iy+rec_initial_score
    ld de,w3d_player_score
    ld bc,4
    ldir
    lea hl,iy+rec_initial_next
    ld de,w3d_player_next_extra
    ld bc,4
    ldir
    ld a,(iy+rec_initial_treasure+0)
    ld (w3d_player_treasure_count+0),a
    ld a,(iy+rec_initial_treasure+1)
    ld (w3d_player_treasure_count+1),a

    ; Read the uint16 slot without allowing the following health byte into HLU.
    ld hl,0
    ld l,(iy+rec_slot+0)
    ld h,(iy+rec_slot+1)
    ld (w3d_current_static_index),hl
    call w3d_static_pointer_from_current
    xor a
    ld (ix+W3D_STATIC_TILEX),a
    ld (ix+W3D_STATIC_TILEY),a
    ld a,034h
    ld (ix+W3D_STATIC_SHAPENUM+0),a
    ld a,012h
    ld (ix+W3D_STATIC_SHAPENUM+1),a
    ld a,W3D_STATIC_FLAG_BONUS
    ld (ix+W3D_STATIC_FLAGS),a
    ld a,(iy+rec_item)
    ld (ix+W3D_STATIC_ITEMNUMBER),a
    ret

validate_case:
    ld a,(actual_return)
    ld b,(iy+rec_expected_return)
    ld c,reason_return
    call assert_equal
    ld b,0
    ld a,(actual_return)
    or a
    jr z,@bonus_expected
    ld b,18
@bonus_expected:
    ld a,(w3d_palette_bonus_count+0)
    ld c,reason_hud_dirty
    call assert_equal
    ld a,(w3d_palette_bonus_count+1)
    ld b,0
    ld c,reason_hud_dirty
    call assert_equal
    ld a,(w3d_player_health)
    ld b,(iy+rec_expected_health)
    ld c,reason_health
    call assert_equal
    ld a,(w3d_player_ammo)
    ld b,(iy+rec_expected_ammo)
    ld c,reason_ammo
    call assert_equal
    ld a,(w3d_player_key_flags)
    ld b,(iy+rec_expected_keys)
    ld c,reason_keys
    call assert_equal
    ld a,(w3d_player_weapon)
    ld b,(iy+rec_expected_weapon)
    ld c,reason_weapon
    call assert_equal
    ld a,(w3d_player_best_weapon)
    ld b,(iy+rec_expected_best)
    ld c,reason_best_weapon
    call assert_equal
    ld a,(w3d_player_chosen_weapon)
    ld b,(iy+rec_expected_chosen)
    ld c,reason_chosen_weapon
    call assert_equal
    ld a,(w3d_player_lives)
    ld b,(iy+rec_expected_lives)
    ld c,reason_lives
    call assert_equal

    ld hl,w3d_player_score
    lea de,iy+rec_expected_score
    ld c,reason_score
    call assert_four_bytes
    ld hl,w3d_player_next_extra
    lea de,iy+rec_expected_next
    ld c,reason_next_extra
    call assert_four_bytes
    ld a,(w3d_player_treasure_count+0)
    ld b,(iy+rec_expected_treasure+0)
    ld c,reason_treasure_count
    call assert_equal
    ld a,(w3d_player_treasure_count+1)
    ld b,(iy+rec_expected_treasure+1)
    ld c,reason_treasure_count
    call assert_equal

    ld a,(w3d_hud_dirty)
    ld b,(iy+rec_expected_hud)
    ld c,reason_hud_dirty
    call assert_equal
    ld a,(w3d_world_dirty)
    ld b,(iy+rec_expected_world)
    ld c,reason_world_dirty
    call assert_equal
    ld a,(w3d_player_dirty)
    ld b,0
    ld c,reason_player_dirty
    call assert_equal

    ld a,(ix+W3D_STATIC_SHAPENUM+0)
    ld b,(iy+rec_expected_shape+0)
    ld c,reason_shape
    call assert_equal
    ld a,(ix+W3D_STATIC_SHAPENUM+1)
    ld b,(iy+rec_expected_shape+1)
    ld c,reason_shape
    call assert_equal

    ; The target byte must have the expected dirty state...
    ld hl,(w3d_current_static_index)
    ld de,w3d_static_dirty
    add hl,de
    ld a,(hl)
    ld b,(iy+rec_expected_dirty)
    ld c,reason_static_dirty
    call assert_equal
    ; ...and the sum over the complete array must match it, proving no other
    ; slot was dirtied (including when the tested slot is index 120).
    ld hl,w3d_static_dirty
    ld b,W3D_FIXTURE_STATIC_COUNT
    ld d,0
@dirty_sum:
    ld a,(hl)
    add a,d
    ld d,a
    inc hl
    djnz @dirty_sum
    ld a,d
    ld b,(iy+rec_expected_dirty)
    ld c,reason_dirty_count
    jp assert_equal

; Compare four bytes at HL with four expected bytes at DE. C is the reason.
assert_four_bytes:
    ld a,(de)
    ld b,a
    ld a,(hl)
    call assert_equal
    inc hl
    inc de
    ld a,(de)
    ld b,a
    ld a,(hl)
    call assert_equal
    inc hl
    inc de
    ld a,(de)
    ld b,a
    ld a,(hl)
    call assert_equal
    inc hl
    inc de
    ld a,(de)
    ld b,a
    ld a,(hl)
    jp assert_equal

; A=actual, B=expected, C=reason. Count at most one failure per case while
; retaining the exact first mismatch for the runner's diagnostic.
assert_equal:
    cp b
    ret z
    ld (assert_actual),a
    ld a,b
    ld (assert_expected),a
    ld a,(case_failed)
    or a
    ret nz
    ld a,1
    ld (case_failed),a
    ld a,(result_errors)
    or a
    jr nz,@count
    ld a,(result_records)
    ld (result_first_case),a
    ld a,c
    ld (result_first_reason),a
    ld a,(assert_expected)
    ld (result_first_expected),a
    ld a,(assert_actual)
    ld (result_first_actual),a
@count:
    ld a,(result_errors)
    inc a
    ld (result_errors),a
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
    ld a,(result_errors)
    or a
    ld hl,report_pass
    jr z,@emit
    ld hl,report_fail
@emit:
    call print_string
    ret

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

; Required by the included interactive module but not exercised here.
w3d_mark_render_submitted:
    ret
w3d_audio_begin_quantum:
    ret
w3d_audio_request:
    ld (test_audio_last_id),a
    ld a,b
    ld (test_audio_arg_b),a
    ld a,c
    ld (test_audio_arg_c),a
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

result_filename:            asciz "pickup_result.bin"
report_banner:              asciz "\r\nWolf3D eZ80 pickup regression: "
report_pass:                asciz "PASS\r\n"
report_fail:                asciz "FAIL\r\n"

output_handle:              db 0
case_failed:                db 0
actual_return:              db 0
assert_expected:            db 0
assert_actual:              db 0

test_audio_begin:
test_audio_count:           dw 0
test_audio_last_id:         db 0
test_audio_arg_b:           db 0
test_audio_arg_c:           db 0
test_audio_end:

test_score32_increment:      db 058h,00fh,002h,000h ; 135,000
test_score32_expected:       db 034h,0abh,002h,000h ; 174,900
test_score32_next:           db 040h,00dh,003h,000h ; 200,000
test_score_capped_expected:  db 040h,09ch,000h,000h ; 40,000
test_score_capped_next:      db 080h,038h,001h,000h ; 80,000

result_data:
    db "W3P1"
result_records:             db 0
result_errors:              db 0
result_first_case:          db 0ffh
result_first_reason:        db 0
result_first_expected:      db 0
result_first_actual:        db 0
                            db 0,0,0,0,0,0
result_end:

pickup_audio_cases:
    db W3D_ITEM_GIBS,10,50,1,61
    db W3D_ITEM_ALPO,50,50,1,33
    db W3D_ITEM_FIRSTAID,50,50,1,34
    db W3D_ITEM_KEY1,50,50,1,12
    db W3D_ITEM_KEY4,50,50,1,12
    db W3D_ITEM_CROSS,50,50,1,35
    db W3D_ITEM_CHALICE,50,50,1,36
    db W3D_ITEM_BIBLE,50,50,1,37
    db W3D_ITEM_CROWN,50,50,1,45
    db W3D_ITEM_CLIP,50,50,1,31
    db W3D_ITEM_CLIP2,50,50,1,31
    db W3D_ITEM_MACHINEGUN,50,50,1,30
    db W3D_ITEM_CHAINGUN,50,50,1,38
    db W3D_ITEM_FOOD,50,50,1,33
    db W3D_ITEM_FULLHEAL,50,50,1,44
    db W3D_ITEM_FIRSTAID,100,50,0,0ffh
    db W3D_ITEM_CLIP,50,99,0,0ffh
    db W3D_ITEM_DRESSING,50,50,0,0ffh

pickup_audio_chaingun:
    db W3D_ITEM_CHAINGUN,50,50,1,38
pickup_audio_fullheal:
    db W3D_ITEM_FULLHEAL,100,50,1,44

; Record 0: full-health first aid is refused, active, and completely clean.
pickup_cases:
    db W3D_ITEM_FIRSTAID
    dw 0
    db 100,8,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 0,0
    db 0,100,8,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 0,0
    db 0,0
    dw 01234h
    db 0

; Record 1: full-ammo clip is refused at the final real E1L1 slot.
    db W3D_ITEM_CLIP
    dw 120
    db 75,99,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 0,0
    db 0,75,99,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 0,0
    db 0,0
    dw 01234h
    db 0

; Record 2: first aid saturates health at 100 and consumes the object.
    db W3D_ITEM_FIRSTAID
    dw 1
    db 90,8,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 0,0
    db 1,100,8,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 0,0
    db W3D_HUD_DIRTY_HEALTH,1
    dw 0ffffh
    db 1

; Record 3: a clip saturates ammo at 99 and consumes the object.
    db W3D_ITEM_CLIP
    dw 2
    db 75,95,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 0,0
    db 1,75,99,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 0,0
    db W3D_HUD_DIRTY_AMMO,1
    dw 0ffffh
    db 1

; Record 4: key 3 sets bit 2 and dirties only the keys HUD field.
    db W3D_ITEM_KEY3
    dw 3
    db 75,8,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 0,0
    db 1,75,8,4,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 0,0
    db W3D_HUD_DIRTY_KEYS,1
    dw 0ffffh
    db 1

; Record 5: a cross takes 39,900 to 40,000, awarding exactly one life and
; advancing the next threshold to 80,000.
    db W3D_ITEM_CROSS
    dw 4
    db 75,8,0,1,1,1,3
    db 0dch,09bh,0,0
    db 040h,09ch,0,0
    db 7,0
    db 1,75,8,0,1,1,1,4
    db 040h,09ch,0,0
    db 080h,038h,1,0
    db 8,0
    db W3D_HUD_DIRTY_SCORE | W3D_HUD_DIRTY_LIVES,1
    dw 0ffffh
    db 1

; Record 6: machine gun adds ammo and promotes current/best/chosen weapon.
    db W3D_ITEM_MACHINEGUN
    dw 5
    db 75,8,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 0,0
    db 1,75,14,0,2,2,2,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 0,0
    db W3D_HUD_DIRTY_AMMO | W3D_HUD_DIRTY_WEAPON,1
    dw 0ffffh
    db 1

; Record 7: fullheal sets health, saturates ammo, adds a life and treasure.
    db W3D_ITEM_FULLHEAL
    dw 6
    db 25,90,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 041h,0
    db 1,100,99,0,1,1,1,4
    db 0,0,0,0
    db 040h,09ch,0,0
    db 042h,0
    db W3D_HUD_DIRTY_HEALTH | W3D_HUD_DIRTY_AMMO | W3D_HUD_DIRTY_LIVES,1
    dw 0ffffh
    db 1

; Record 8: at the nine-life cap, crossing 40,000 still advances the score
; threshold and treasure count, but must not dirty lives or exceed nine.
    db W3D_ITEM_CROSS
    dw 7
    db 75,8,0,1,1,1,9
    db 0dch,09bh,0,0
    db 040h,09ch,0,0
    db 034h,012h
    db 1,75,8,0,1,1,1,9
    db 040h,09ch,0,0
    db 080h,038h,1,0
    db 035h,012h
    db W3D_HUD_DIRTY_SCORE,1
    dw 0ffffh
    db 1

; Record 9: fullheal at nine lives still heals, fills ammo and increments
; treasure, while leaving lives capped and the lives HUD bit clear.
    db W3D_ITEM_FULLHEAL
    dw 8
    db 25,90,0,1,1,1,9
    db 0,0,0,0
    db 040h,09ch,0,0
    db 99,0
    db 1,100,99,0,1,1,1,9
    db 0,0,0,0
    db 040h,09ch,0,0
    db 100,0
    db W3D_HUD_DIRTY_HEALTH | W3D_HUD_DIRTY_AMMO,1
    dw 0ffffh
    db 1

; Record 10: gibs are accepted only at health 10 or below. They add one
; health, consume the object, and do not alter treasure state.
    db W3D_ITEM_GIBS
    dw 9
    db 10,8,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 022h,022h
    db 1,11,8,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 022h,022h
    db W3D_HUD_DIRTY_HEALTH,1
    dw 0ffffh
    db 1

; Record 11: at health 11, gibs are refused and remain active with no dirty
; state and no inventory/statistics mutation.
    db W3D_ITEM_GIBS
    dw 10
    db 11,8,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 022h,022h
    db 0,11,8,0,1,1,1,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 022h,022h
    db 0,0
    dw 01234h
    db 0

; Record 12: GiveAmmo from zero restores the chosen weapon when idle. Current
; knife becomes chosen chaingun; best/chosen and treasure remain unchanged.
    db W3D_ITEM_CLIP
    dw 11
    db 75,0,0,0,3,3,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 033h,033h
    db 1,75,8,0,3,3,3,3
    db 0,0,0,0
    db 040h,09ch,0,0
    db 033h,033h
    db W3D_HUD_DIRTY_AMMO | W3D_HUD_DIRTY_WEAPON,1
    dw 0ffffh
    db 1
pickup_cases_end:
