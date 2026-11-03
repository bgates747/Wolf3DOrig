; Direct real-eZ80 regression for production wolf3d_intermission.inc.
;
; The fixture supplies only the production include's external state and small
; shell/VDP seams. Timer arithmetic, seed scans, percentage arithmetic, par
; lookup, digit selection, ordinary/secret drawing, nonblocking load-time
; animation, input arming/acknowledgment, and Escape abortion all execute
; directly from the shipping include.

    assume adl=1
    org 040000h
    jp start
    align 64
    db "MOS",0,1

mos_fopen:          equ 0ah
mos_fclose:         equ 0bh
mos_fwrite:         equ 1bh
fa_write:           equ 02h
fa_create_always:   equ 08h

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    macro CHECK_A expected,reason
        ld b,expected
        ld c,reason
        call assert_a
    endmacro

    macro CHECK_MEM8 address,expected,reason
        ld a,(address)
        CHECK_A expected,reason
    endmacro

    macro CHECK_PLOT offset,buffer,x,y
        CHECK_MEM8 test_plot_log+offset+0,buffer&0ffh,REASON_PLOT_BUFFER
        CHECK_MEM8 test_plot_log+offset+1,buffer>>8,REASON_PLOT_BUFFER
        CHECK_MEM8 test_plot_log+offset+2,x&0ffh,REASON_PLOT_X
        CHECK_MEM8 test_plot_log+offset+3,x>>8,REASON_PLOT_X
        CHECK_MEM8 test_plot_log+offset+4,y&0ffh,REASON_PLOT_Y
        CHECK_MEM8 test_plot_log+offset+5,y>>8,REASON_PLOT_Y
    endmacro

; Minimal stable world-layout ABI consumed by the production include.
W3D_ACTOR_FLAG_SHOOTABLE: equ 001h
W3D_ACTOR_FLAGS:          equ 14
W3D_ACTOR_SIZE:           equ 39
W3D_STATIC_ITEMNUMBER:    equ 5
W3D_STATIC_SIZE:          equ 6
W3D_ITEM_CROSS:           equ 9
W3D_ITEM_CHALICE:         equ 10
W3D_ITEM_BIBLE:           equ 11
W3D_ITEM_CROWN:           equ 12
W3D_ITEM_FULLHEAL:        equ 18
W3D_AUDIO_SOUND_ENDBONUS1: equ 42
W3D_AUDIO_SOUND_ENDBONUS2: equ 43
W3D_AUDIO_SOUND_NOBONUS:   equ 47
W3D_AUDIO_SOUND_PERCENT100: equ 48

; Production-owned globals are reduced to the exact fields this include reads.
w3d_level_requested_index:  db 0
w3d_level_actor_seed_ptr:   dl test_actor_seeds
w3d_level_actor_count:      db 0
w3d_level_static_seed_ptr:  dl test_static_seeds
w3d_level_static_count:     dw 0
w3d_player_kill_count:      dw 0
w3d_player_secret_count:    dw 0
w3d_player_secret_total:    dw 0
w3d_player_treasure_count:  dw 0
w3d_player_health:          db 100
w3d_player_ammo:            db 8
w3d_player_key_flags:       db 0
w3d_player_weapon:          db 1
w3d_player_lives:           db 3
w3d_player_score:           dl 0
                            db 0

    include "wolf3d_level_time.inc"
    include "wolf3d_intermission.inc"

REASON_SUBTICKS:       equ 1
REASON_SECONDS:        equ 2
REASON_MINUTES:        equ 3
REASON_TOTAL_LOW:      equ 4
REASON_TOTAL_HIGH:     equ 5
REASON_PERCENT:        equ 6
REASON_SETUP_COUNT:    equ 7
REASON_WAIT_COUNT:     equ 8
REASON_PLOT_COUNT:     equ 9
REASON_PLOT_BUFFER:    equ 10
REASON_PLOT_X:         equ 11
REASON_PLOT_Y:         equ 12
REASON_PAR_MINUTES:    equ 13
REASON_PAR_SECONDS:    equ 14
REASON_RESULT:         equ 15
REASON_CARRY:          equ 16
REASON_INPUT_ARMED:    equ 17
REASON_ACKNOWLEDGED:   equ 18
REASON_ANIMATION_COUNT: equ 19
REASON_PORTRAIT_FRAME: equ 20
REASON_READ_COUNT:     equ 21
REASON_ESCAPE_LATCH:   equ 22
REASON_ACK_RELEASED:   equ 23
REASON_EXIT_QUERY_COUNT: equ 24
REASON_INGRESS_FENCE_COUNT: equ 25
REASON_INGRESS_FAILURE: equ 26
REASON_TIMELEFT:        equ 27
REASON_BONUS_BYTE:      equ 28
REASON_RATIO_RECORD:    equ 29
REASON_AWARD_COUNT:     equ 30
REASON_SOUND_COUNT:     equ 31
REASON_SOUND_ID:        equ 32
REASON_STAGE:           equ 33
REASON_VICTORY_MINUTES: equ 34
REASON_VICTORY_SECONDS: equ 35
REASON_VICTORY_KILL:    equ 36
REASON_VICTORY_SECRET:  equ 37
REASON_VICTORY_TREASURE: equ 38

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
    dec a
    ld (result_first_case),a

    call test_timer_reset
    call test_timer_tick_boundary
    call test_timer_minute_rollover
    call test_timer_clamp
    call test_kill_total
    call test_treasure_total
    call test_percent
    call test_ordinary_draw
    call test_secret_draw
    call test_animation_cadence
    call test_held_key_arming_and_ack_latch
    call test_finish_waits_for_fresh_press
    call test_loading_escape_abort
    call test_finish_escape_abort
    call test_loading_hook_only_escape_abort
    call test_finish_hook_only_escape_abort
    call test_loading_ingress_fence
    call test_loading_ingress_failure
    call test_bonus_derivation_and_ratio_record
    call test_finalize_awards_once
    call test_countup_state_machine
    call test_victory_totals
    call test_victory_time_clamp
    call write_result
    ret

test_timer_reset:
    ld a,1
    ld (test_case),a
    ld a,0ffh
    ld (w3d_intermission_level_subticks),a
    ld (w3d_intermission_level_seconds),a
    ld (w3d_intermission_level_minutes),a
    call w3d_intermission_reset_level_time
    CHECK_MEM8 w3d_intermission_level_subticks,0,REASON_SUBTICKS
    CHECK_MEM8 w3d_intermission_level_seconds,0,REASON_SECONDS
    CHECK_MEM8 w3d_intermission_level_minutes,0,REASON_MINUTES
    ret

test_timer_tick_boundary:
    ld a,2
    ld (test_case),a
    call w3d_intermission_reset_level_time
    ld b,29
@tick_29:
    call w3d_intermission_tick_level_time
    djnz @tick_29
    CHECK_MEM8 w3d_intermission_level_subticks,29,REASON_SUBTICKS
    CHECK_MEM8 w3d_intermission_level_seconds,0,REASON_SECONDS
    CHECK_MEM8 w3d_intermission_level_minutes,0,REASON_MINUTES

    ld a,3
    ld (test_case),a
    call w3d_intermission_tick_level_time
    CHECK_MEM8 w3d_intermission_level_subticks,0,REASON_SUBTICKS
    CHECK_MEM8 w3d_intermission_level_seconds,1,REASON_SECONDS
    CHECK_MEM8 w3d_intermission_level_minutes,0,REASON_MINUTES
    ret

test_timer_minute_rollover:
    ld a,4
    ld (test_case),a
    ld a,29
    ld (w3d_intermission_level_subticks),a
    ld a,59
    ld (w3d_intermission_level_seconds),a
    ld (w3d_intermission_level_minutes),a
    call w3d_intermission_tick_level_time
    CHECK_MEM8 w3d_intermission_level_subticks,0,REASON_SUBTICKS
    CHECK_MEM8 w3d_intermission_level_seconds,0,REASON_SECONDS
    CHECK_MEM8 w3d_intermission_level_minutes,60,REASON_MINUTES
    ret

test_timer_clamp:
    ld a,5
    ld (test_case),a
    ld a,29
    ld (w3d_intermission_level_subticks),a
    ld a,59
    ld (w3d_intermission_level_seconds),a
    ld a,98
    ld (w3d_intermission_level_minutes),a
    call w3d_intermission_tick_level_time
    CHECK_MEM8 w3d_intermission_level_subticks,0,REASON_SUBTICKS
    CHECK_MEM8 w3d_intermission_level_seconds,0,REASON_SECONDS
    CHECK_MEM8 w3d_intermission_level_minutes,99,REASON_MINUTES

    ld a,6
    ld (test_case),a
    ld b,60
@past_clamp:
    call w3d_intermission_tick_level_time
    djnz @past_clamp
    CHECK_MEM8 w3d_intermission_level_subticks,0,REASON_SUBTICKS
    CHECK_MEM8 w3d_intermission_level_seconds,0,REASON_SECONDS
    CHECK_MEM8 w3d_intermission_level_minutes,99,REASON_MINUTES
    ret

test_kill_total:
    ld a,7
    ld (test_case),a
    ld hl,test_actor_seeds
    ld (w3d_level_actor_seed_ptr),hl
    ld a,5
    ld (w3d_level_actor_count),a
    call w3d_intermission_count_kill_total
    ld a,e
    ld (test_total_low),a
    ld a,d
    ld (test_total_high),a
    CHECK_MEM8 test_total_low,3,REASON_TOTAL_LOW
    CHECK_MEM8 test_total_high,0,REASON_TOTAL_HIGH
    ret

test_treasure_total:
    ld a,8
    ld (test_case),a
    ld hl,test_static_seeds
    ld (w3d_level_static_seed_ptr),hl
    ld a,9
    ld (w3d_level_static_count+0),a
    xor a
    ld (w3d_level_static_count+1),a
    call w3d_intermission_count_treasure_total
    ld a,e
    ld (test_total_low),a
    ld a,d
    ld (test_total_high),a
    CHECK_MEM8 test_total_low,5,REASON_TOTAL_LOW
    CHECK_MEM8 test_total_high,0,REASON_TOTAL_HIGH
    ret

test_percent:
; A zero denominator is zero even for a nonzero count.
    ld a,9
    ld (test_case),a
    ld bc,7
    ld de,0
    call w3d_intermission_percent
    CHECK_A 0,REASON_PERCENT

; Integer division truncates: floor(2*100/3) = 66.
    ld a,10
    ld (test_case),a
    ld bc,2
    ld de,3
    call w3d_intermission_percent
    CHECK_A 66,REASON_PERCENT

; Equality is exactly 100 and an over-total count is capped to 100.
    ld a,11
    ld (test_case),a
    ld bc,3
    ld de,3
    call w3d_intermission_percent
    CHECK_A 100,REASON_PERCENT
    ld a,12
    ld (test_case),a
    ld bc,4
    ld de,3
    call w3d_intermission_percent
    CHECK_A 100,REASON_PERCENT
    ret

test_bonus_derivation_and_ratio_record:
    ld a,24
    ld (test_case),a
    call test_reset_shell_stubs
    xor a
    ld (w3d_level_requested_index),a
    ld a,1
    ld (w3d_intermission_level_minutes),a
    ld a,2
    ld (w3d_intermission_level_seconds),a
    ld a,1
    ld (w3d_intermission_par_minutes),a
    ld a,30
    ld (w3d_intermission_par_seconds),a
    ld a,66
    ld (w3d_intermission_kill_ratio),a
    ld a,50
    ld (w3d_intermission_secret_ratio),a
    ld a,100
    ld (w3d_intermission_treasure_ratio),a
    call w3d_intermission_prepare_ordinary
    CHECK_MEM8 w3d_intermission_elapsed_seconds+0,62,REASON_SECONDS
    CHECK_MEM8 w3d_intermission_elapsed_seconds+1,0,REASON_SECONDS
    CHECK_MEM8 w3d_intermission_timeleft+0,28,REASON_TIMELEFT
    CHECK_MEM8 w3d_intermission_timeleft+1,0,REASON_TIMELEFT
; 28*500 + one perfect ratio = 24,000 = 0x00005dc0.
    CHECK_MEM8 w3d_intermission_final_bonus+0,0c0h,REASON_BONUS_BYTE
    CHECK_MEM8 w3d_intermission_final_bonus+1,05dh,REASON_BONUS_BYTE
    CHECK_MEM8 w3d_intermission_final_bonus+2,0,REASON_BONUS_BYTE
    CHECK_MEM8 w3d_intermission_final_bonus+3,0,REASON_BONUS_BYTE
    CHECK_MEM8 w3d_intermission_stage,W3D_INTERMISSION_STAGE_TIME,REASON_STAGE
    CHECK_MEM8 w3d_level_ratios+W3D_LEVEL_RATIO_KILL,66,REASON_RATIO_RECORD
    CHECK_MEM8 w3d_level_ratios+W3D_LEVEL_RATIO_KILL+1,0,REASON_RATIO_RECORD
    CHECK_MEM8 w3d_level_ratios+W3D_LEVEL_RATIO_SECRET,50,REASON_RATIO_RECORD
    CHECK_MEM8 w3d_level_ratios+W3D_LEVEL_RATIO_TREASURE,100,REASON_RATIO_RECORD
    CHECK_MEM8 w3d_level_ratios+W3D_LEVEL_RATIO_TIME,62,REASON_RATIO_RECORD
    CHECK_MEM8 w3d_level_ratios+W3D_LEVEL_RATIO_TIME+1,0,REASON_RATIO_RECORD
    ret

test_finalize_awards_once:
    ld a,25
    ld (test_case),a
    call test_reset_shell_stubs
    ld hl,test_award_points
    call w3d_intermission_set_award_hook
    xor a
    ld (w3d_level_requested_index),a
    ld a,0c0h
    ld (w3d_intermission_final_bonus+0),a
    ld a,05dh
    ld (w3d_intermission_final_bonus+1),a
    xor a
    ld (w3d_intermission_final_bonus+2),a
    ld (w3d_intermission_final_bonus+3),a
    ld (w3d_intermission_bonus_awarded),a
    ld a,66
    ld (w3d_intermission_kill_ratio),a
    ld a,50
    ld (w3d_intermission_secret_ratio),a
    ld a,100
    ld (w3d_intermission_treasure_ratio),a
    call w3d_intermission_finalize
    CHECK_MEM8 test_award_count,1,REASON_AWARD_COUNT
    CHECK_MEM8 test_award_value+0,0c0h,REASON_BONUS_BYTE
    CHECK_MEM8 test_award_value+1,05dh,REASON_BONUS_BYTE
    CHECK_MEM8 test_award_value+2,0,REASON_BONUS_BYTE
    CHECK_MEM8 test_award_value+3,0,REASON_BONUS_BYTE
    CHECK_MEM8 w3d_intermission_stage,W3D_INTERMISSION_STAGE_DONE,REASON_STAGE
    call w3d_intermission_finalize
    CHECK_MEM8 test_award_count,1,REASON_AWARD_COUNT
    ret

test_countup_state_machine:
    ld a,26
    ld (test_case),a
    call test_reset_shell_stubs
    ld hl,test_record_sound
    call w3d_intermission_set_sound_hook
    ld hl,test_award_points
    call w3d_intermission_set_award_hook
    xor a
    ld (w3d_level_requested_index),a
    ld (w3d_intermission_current_ratio),a
    ld (w3d_intermission_stage_counter+0),a
    ld (w3d_intermission_stage_counter+1),a
    ld (w3d_intermission_kill_ratio),a
    ld (w3d_intermission_secret_ratio),a
    ld (w3d_intermission_treasure_ratio),a
    ld (w3d_intermission_bonus_awarded),a
    ld (w3d_intermission_current_bonus+0),a
    ld (w3d_intermission_current_bonus+1),a
    ld (w3d_intermission_current_bonus+2),a
    ld (w3d_intermission_current_bonus+3),a
    ld a,1000&0ffh
    ld (w3d_intermission_final_bonus+0),a
    ld a,1000>>8
    ld (w3d_intermission_final_bonus+1),a
    xor a
    ld (w3d_intermission_final_bonus+2),a
    ld (w3d_intermission_final_bonus+3),a
    ld a,2
    ld (w3d_intermission_timeleft+0),a
    xor a
    ld (w3d_intermission_timeleft+1),a
    ld a,W3D_INTERMISSION_STAGE_TIME
    ld (w3d_intermission_stage),a

; i=0,1,2; then one zero-valued iteration for each ratio.
    call w3d_intermission_advance_countup
    call w3d_intermission_advance_countup
    call w3d_intermission_advance_countup
    call w3d_intermission_advance_countup
    call w3d_intermission_advance_countup
    call w3d_intermission_advance_countup
    CHECK_MEM8 w3d_intermission_stage,W3D_INTERMISSION_STAGE_DONE,REASON_STAGE
    CHECK_MEM8 w3d_intermission_current_bonus+0,1000&0ffh,REASON_BONUS_BYTE
    CHECK_MEM8 w3d_intermission_current_bonus+1,1000>>8,REASON_BONUS_BYTE
    CHECK_MEM8 test_award_count,1,REASON_AWARD_COUNT
    CHECK_MEM8 test_sound_count,8,REASON_SOUND_COUNT
    CHECK_MEM8 test_sound_log+0,W3D_AUDIO_SOUND_ENDBONUS1,REASON_SOUND_ID
    CHECK_MEM8 test_sound_log+1,W3D_AUDIO_SOUND_ENDBONUS2,REASON_SOUND_ID
    CHECK_MEM8 test_sound_log+2,W3D_AUDIO_SOUND_ENDBONUS1,REASON_SOUND_ID
    CHECK_MEM8 test_sound_log+3,W3D_AUDIO_SOUND_NOBONUS,REASON_SOUND_ID
    CHECK_MEM8 test_sound_log+4,W3D_AUDIO_SOUND_ENDBONUS1,REASON_SOUND_ID
    CHECK_MEM8 test_sound_log+5,W3D_AUDIO_SOUND_NOBONUS,REASON_SOUND_ID
    CHECK_MEM8 test_sound_log+6,W3D_AUDIO_SOUND_ENDBONUS1,REASON_SOUND_ID
    CHECK_MEM8 test_sound_log+7,W3D_AUDIO_SOUND_NOBONUS,REASON_SOUND_ID
    ret

; The original Victory() sums all eight ordinary-floor LRstruct records,
; divides each ratio by eight, and displays the aggregate elapsed time.
test_victory_totals:
    ld a,27
    ld (test_case),a
    ld hl,test_victory_ratios
    ld de,w3d_level_ratios
    ld bc,W3D_LEVEL_RATIO_COUNT*W3D_LEVEL_RATIO_SIZE
    ldir
    call w3d_victory_calculate_totals
    CHECK_MEM8 w3d_victory_minutes,20,REASON_VICTORY_MINUTES
    CHECK_MEM8 w3d_victory_seconds,0,REASON_VICTORY_SECONDS
    CHECK_MEM8 w3d_victory_kill_average,65,REASON_VICTORY_KILL
    CHECK_MEM8 w3d_victory_secret_average,35,REASON_VICTORY_SECRET
    CHECK_MEM8 w3d_victory_treasure_average,100,REASON_VICTORY_TREASURE
    ret

; Victory() deliberately uses 99:99, rather than 99:59, as its overflow
; sentinel whenever the episode total reaches 100 minutes.
test_victory_time_clamp:
    ld a,28
    ld (test_case),a
    ld hl,6000
    ld (w3d_victory_total_seconds),hl
    xor a
    ld (w3d_victory_total_seconds+3),a
    call w3d_victory_split_time
    CHECK_MEM8 w3d_victory_minutes,99,REASON_VICTORY_MINUTES
    CHECK_MEM8 w3d_victory_seconds,99,REASON_VICTORY_SECONDS
    ret

test_ordinary_draw:
    ld a,13
    ld (test_case),a
    call test_reset_shell_stubs
    xor a
    ld (w3d_level_requested_index),a
    ld a,1
    ld (w3d_intermission_level_minutes),a
    ld a,2
    ld (w3d_intermission_level_seconds),a
    ld a,2
    ld (w3d_player_kill_count+0),a
    xor a
    ld (w3d_player_kill_count+1),a
    ld a,5
    ld (w3d_player_treasure_count+0),a
    xor a
    ld (w3d_player_treasure_count+1),a
    ld a,5
    ld (w3d_level_actor_count),a
    ld a,9
    ld (w3d_level_static_count+0),a
    xor a
    ld (w3d_level_static_count+1),a
    ld a,7
    ld (w3d_player_health),a
    ld a,8
    ld (w3d_player_ammo),a
    ld a,1
    ld (w3d_player_key_flags),a
    ld (w3d_player_weapon),a
    ld a,3
    ld (w3d_player_lives),a
    ld hl,12345
    ld (w3d_player_score),hl
    xor a
    ld (w3d_player_score+3),a
    call w3d_intermission_begin
    call capture_result

    CHECK_MEM8 test_setup_count,1,REASON_SETUP_COUNT
    CHECK_MEM8 test_wait_count,0,REASON_WAIT_COUNT
    CHECK_MEM8 test_plot_count,35,REASON_PLOT_COUNT
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_CONTINUE,REASON_RESULT
    CHECK_MEM8 test_result_carry,0,REASON_CARRY
    CHECK_MEM8 w3d_intermission_input_armed,0,REASON_INPUT_ARMED
    CHECK_MEM8 w3d_intermission_acknowledged,0,REASON_ACKNOWLEDGED
    CHECK_MEM8 w3d_intermission_ack_released,0,REASON_ACK_RELEASED
    CHECK_MEM8 w3d_intermission_escape_requested,0,REASON_ESCAPE_LATCH
    CHECK_MEM8 w3d_intermission_animation_counter,0,REASON_ANIMATION_COUNT
    CHECK_MEM8 w3d_intermission_portrait_frame,0,REASON_PORTRAIT_FRAME
    CHECK_MEM8 w3d_intermission_par_minutes,1,REASON_PAR_MINUTES
    CHECK_MEM8 w3d_intermission_par_seconds,30,REASON_PAR_SECONDS

    CHECK_PLOT 0,W3D_INTERMISSION_FLOOR_BASE_BUFFER,0,0
    CHECK_PLOT 6,W3D_INTERMISSION_STATUSBAR_BUFFER,0,200
; Live status-bar overlay: floor 1, score 012345 with one leading blank,
; lives 3, health-band face 6A, health 7, ammo 8, gold key, pistol.
    CHECK_PLOT 12,W3D_INTERMISSION_HUD_BLANK_BUFFER,16,216
    CHECK_PLOT 18,W3D_INTERMISSION_HUD_DIGIT_0_BUFFER+1,24,216
    CHECK_PLOT 24,W3D_INTERMISSION_HUD_BLANK_BUFFER,48,216
    CHECK_PLOT 30,W3D_INTERMISSION_HUD_DIGIT_0_BUFFER+1,56,216
    CHECK_PLOT 36,W3D_INTERMISSION_HUD_DIGIT_0_BUFFER+2,64,216
    CHECK_PLOT 42,W3D_INTERMISSION_HUD_DIGIT_0_BUFFER+3,72,216
    CHECK_PLOT 48,W3D_INTERMISSION_HUD_DIGIT_0_BUFFER+4,80,216
    CHECK_PLOT 54,W3D_INTERMISSION_HUD_DIGIT_0_BUFFER+5,88,216
    CHECK_PLOT 60,W3D_INTERMISSION_HUD_DIGIT_0_BUFFER+3,112,216
    CHECK_PLOT 66,W3D_INTERMISSION_FACE_1_A_BUFFER+15,136,204
    CHECK_PLOT 72,W3D_INTERMISSION_HUD_BLANK_BUFFER,168,216
    CHECK_PLOT 78,W3D_INTERMISSION_HUD_BLANK_BUFFER,176,216
    CHECK_PLOT 84,W3D_INTERMISSION_HUD_DIGIT_0_BUFFER+7,184,216
    CHECK_PLOT 90,W3D_INTERMISSION_HUD_BLANK_BUFFER,216,216
    CHECK_PLOT 96,W3D_INTERMISSION_HUD_DIGIT_0_BUFFER+8,224,216
    CHECK_PLOT 102,W3D_INTERMISSION_KEY_GOLD_BUFFER,240,204
    CHECK_PLOT 108,W3D_INTERMISSION_KEY_NONE_BUFFER,240,220
    CHECK_PLOT 114,W3D_INTERMISSION_WEAPON_KNIFE_BUFFER+1,256,208
    CHECK_PLOT 120,W3D_INTERMISSION_DIGIT_0_BUFFER+1,208,16
    CHECK_PLOT 126,W3D_INTERMISSION_DIGIT_0_BUFFER+0,208,80
    CHECK_PLOT 132,W3D_INTERMISSION_DIGIT_0_BUFFER+1,224,80
    CHECK_PLOT 138,W3D_INTERMISSION_COLON_BUFFER,240,80
    CHECK_PLOT 144,W3D_INTERMISSION_DIGIT_0_BUFFER+0,248,80
    CHECK_PLOT 150,W3D_INTERMISSION_DIGIT_0_BUFFER+2,264,80
    CHECK_PLOT 156,W3D_INTERMISSION_DIGIT_0_BUFFER+0,208,96
    CHECK_PLOT 162,W3D_INTERMISSION_DIGIT_0_BUFFER+1,224,96
    CHECK_PLOT 168,W3D_INTERMISSION_COLON_BUFFER,240,96
    CHECK_PLOT 174,W3D_INTERMISSION_DIGIT_0_BUFFER+3,248,96
    CHECK_PLOT 180,W3D_INTERMISSION_DIGIT_0_BUFFER+0,264,96
; Count-up starts at zero while authoritative targets retain 66/0/100.
    CHECK_PLOT 186,W3D_INTERMISSION_DIGIT_0_BUFFER+0,280,112
    CHECK_PLOT 192,W3D_INTERMISSION_DIGIT_0_BUFFER+0,280,128
    CHECK_PLOT 198,W3D_INTERMISSION_DIGIT_0_BUFFER+0,280,144
    CHECK_PLOT 204,W3D_INTERMISSION_DIGIT_0_BUFFER+0,272,56
    CHECK_MEM8 w3d_intermission_kill_ratio,66,REASON_PERCENT
    CHECK_MEM8 w3d_intermission_secret_ratio,0,REASON_PERCENT
    CHECK_MEM8 w3d_intermission_treasure_ratio,100,REASON_PERCENT
    ld hl,test_plot_log
    ld de,test_ordinary_plot_log
    ld bc,37*6
    ldir
    ret

test_secret_draw:
    ld a,14
    ld (test_case),a
    call test_reset_shell_stubs
    ld a,9
    ld (w3d_level_requested_index),a
    call w3d_intermission_begin
    call capture_result
    CHECK_MEM8 test_setup_count,1,REASON_SETUP_COUNT
    CHECK_MEM8 test_wait_count,0,REASON_WAIT_COUNT
    CHECK_MEM8 test_plot_count,20,REASON_PLOT_COUNT
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_CONTINUE,REASON_RESULT
    CHECK_MEM8 test_result_carry,0,REASON_CARRY
    CHECK_PLOT 0,W3D_INTERMISSION_SECRET_BASE_BUFFER,0,0
    CHECK_PLOT 6,W3D_INTERMISSION_STATUSBAR_BUFFER,0,200
    CHECK_PLOT 114,W3D_INTERMISSION_WEAPON_KNIFE_BUFFER+1,256,208
    ret

test_animation_cadence:
    ld a,15
    ld (test_case),a
    call test_reset_shell_stubs
    ld a,9
    ld (w3d_level_requested_index),a
    call w3d_intermission_begin
    call test_reset_plot_stub

; Empty input arms acknowledgment, but the first three completed-image
; boundaries leave BJ's initial portrait untouched.
    call w3d_intermission_loading_tick
    call capture_result
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_CONTINUE,REASON_RESULT
    CHECK_MEM8 test_result_carry,0,REASON_CARRY
    call w3d_intermission_loading_tick
    call w3d_intermission_loading_tick
    CHECK_MEM8 test_plot_count,0,REASON_PLOT_COUNT
    CHECK_MEM8 w3d_intermission_animation_counter,3,REASON_ANIMATION_COUNT
    CHECK_MEM8 w3d_intermission_portrait_frame,0,REASON_PORTRAIT_FRAME

; Boundary four breathes to GUY2; boundary eight returns to GUY1.
    call w3d_intermission_loading_tick
    call capture_result
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_CONTINUE,REASON_RESULT
    CHECK_MEM8 test_result_carry,0,REASON_CARRY
    CHECK_MEM8 test_plot_count,1,REASON_PLOT_COUNT
    CHECK_MEM8 w3d_intermission_animation_counter,0,REASON_ANIMATION_COUNT
    CHECK_MEM8 w3d_intermission_portrait_frame,1,REASON_PORTRAIT_FRAME
    CHECK_PLOT 0,W3D_INTERMISSION_GUY_2_BUFFER,0,16

    call w3d_intermission_loading_tick
    call w3d_intermission_loading_tick
    call w3d_intermission_loading_tick
    call w3d_intermission_loading_tick
    CHECK_MEM8 test_plot_count,2,REASON_PLOT_COUNT
    CHECK_MEM8 w3d_intermission_animation_counter,0,REASON_ANIMATION_COUNT
    CHECK_MEM8 w3d_intermission_portrait_frame,0,REASON_PORTRAIT_FRAME
    CHECK_PLOT 6,W3D_INTERMISSION_GUY_1_BUFFER,0,16
    ret

test_held_key_arming_and_ack_latch:
    ld a,16
    ld (test_case),a
    call test_reset_shell_stubs
    ld a,9
    ld (w3d_level_requested_index),a
    call w3d_intermission_begin

; The use/elevator key inherited from gameplay cannot acknowledge.
    ld a,00000100b               ; Space in MOS keymap byte 12
    ld (test_keymap+12),a
    call w3d_intermission_loading_tick
    call capture_result
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_CONTINUE,REASON_RESULT
    CHECK_MEM8 test_result_carry,0,REASON_CARRY
    CHECK_MEM8 w3d_intermission_input_armed,0,REASON_INPUT_ARMED
    CHECK_MEM8 w3d_intermission_acknowledged,0,REASON_ACKNOWLEDGED

; Complete release arms; only the subsequent fresh press latches ack.
    xor a
    ld (test_keymap+12),a
    call w3d_intermission_loading_tick
    CHECK_MEM8 w3d_intermission_input_armed,1,REASON_INPUT_ARMED
    CHECK_MEM8 w3d_intermission_acknowledged,0,REASON_ACKNOWLEDGED
    ld a,00000100b
    ld (test_keymap+12),a
    call w3d_intermission_loading_tick
    call capture_result
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_CONTINUE,REASON_RESULT
    CHECK_MEM8 test_result_carry,0,REASON_CARRY
    CHECK_MEM8 w3d_intermission_acknowledged,1,REASON_ACKNOWLEDGED
    CHECK_MEM8 w3d_intermission_ack_released,0,REASON_ACK_RELEASED

; Loading continues. Finish needs no second press, but it still polls once and
; observes the acknowledgment key's release before returning to gameplay.
    xor a
    ld (test_keymap+12),a
    ld (test_read_count),a
    call w3d_intermission_finish
    call capture_result
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_CONTINUE,REASON_RESULT
    CHECK_MEM8 test_result_carry,0,REASON_CARRY
    CHECK_MEM8 test_read_count,1,REASON_READ_COUNT
    CHECK_MEM8 w3d_intermission_ack_released,1,REASON_ACK_RELEASED
    ret

test_finish_waits_for_fresh_press:
    ld a,17
    ld (test_case),a
    call test_reset_shell_stubs
    ld a,9
    ld (w3d_level_requested_index),a
    call w3d_intermission_begin

; No loading callback occurred: finish itself observes a complete release,
; then a fresh ordinary keypress, and does not return until a third scripted
; frame observes every key released again.
    ld hl,test_finish_input_script
    ld (test_keyboard_script_ptr),hl
    ld a,3
    ld (test_keyboard_script_frames),a
    call w3d_intermission_finish
    call capture_result
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_CONTINUE,REASON_RESULT
    CHECK_MEM8 test_result_carry,0,REASON_CARRY
    CHECK_MEM8 test_read_count,3,REASON_READ_COUNT
    CHECK_MEM8 w3d_intermission_input_armed,1,REASON_INPUT_ARMED
    CHECK_MEM8 w3d_intermission_acknowledged,1,REASON_ACKNOWLEDGED
    CHECK_MEM8 w3d_intermission_ack_released,1,REASON_ACK_RELEASED
    ret

test_loading_escape_abort:
    ld a,18
    ld (test_case),a
    call test_reset_shell_stubs
    ld a,9
    ld (w3d_level_requested_index),a
    call w3d_intermission_begin
    ld a,00000001b               ; Escape, before acknowledgment is armed
    ld (test_keymap+14),a
    call w3d_intermission_loading_tick
    call capture_result
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_ESCAPE,REASON_RESULT
    CHECK_MEM8 test_result_carry,1,REASON_CARRY
    CHECK_MEM8 w3d_intermission_input_armed,0,REASON_INPUT_ARMED
    CHECK_MEM8 w3d_intermission_acknowledged,0,REASON_ACKNOWLEDGED
    CHECK_MEM8 w3d_intermission_animation_counter,0,REASON_ANIMATION_COUNT
    call w3d_intermission_escape_is_requested
    CHECK_A 1,REASON_ESCAPE_LATCH
    ret

test_finish_escape_abort:
    ld a,19
    ld (test_case),a
    call test_reset_shell_stubs
    ld a,9
    ld (w3d_level_requested_index),a
    call w3d_intermission_begin
; Even a previously latched acknowledgment cannot outrank current Escape.
    ld a,1
    ld (w3d_intermission_acknowledged),a
    ld (test_keymap+14),a
    call w3d_intermission_finish
    call capture_result
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_ESCAPE,REASON_RESULT
    CHECK_MEM8 test_result_carry,1,REASON_CARRY
    CHECK_MEM8 test_read_count,1,REASON_READ_COUNT
    call w3d_intermission_escape_is_requested
    CHECK_A 1,REASON_ESCAPE_LATCH
    ret

test_loading_hook_only_escape_abort:
    ld a,20
    ld (test_case),a
    call test_reset_shell_stubs
    ld a,9
    ld (w3d_level_requested_index),a
    ld hl,test_application_exit_query
    call w3d_intermission_set_application_exit_query_hook
    call w3d_intermission_begin          ; begin must preserve installed hook
    ld a,1
    ld (test_application_exit),a
; The keymap remains completely empty. Only the injected callback-style latch
; can request exit, and it must be consulted before MOS keyboard input.
    call w3d_intermission_loading_tick
    call capture_result
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_ESCAPE,REASON_RESULT
    CHECK_MEM8 test_result_carry,1,REASON_CARRY
    CHECK_MEM8 test_exit_query_count,1,REASON_EXIT_QUERY_COUNT
    CHECK_MEM8 test_read_count,0,REASON_READ_COUNT
    call w3d_intermission_escape_is_requested
    CHECK_A 1,REASON_ESCAPE_LATCH
    ret

test_finish_hook_only_escape_abort:
    ld a,21
    ld (test_case),a
    call test_reset_shell_stubs
    ld a,9
    ld (w3d_level_requested_index),a
    ld hl,test_application_exit_query
    call w3d_intermission_set_application_exit_query_hook
    call w3d_intermission_begin          ; begin must preserve installed hook
    ld a,1
    ld (test_application_exit),a
    call w3d_intermission_finish
    call capture_result
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_ESCAPE,REASON_RESULT
    CHECK_MEM8 test_result_carry,1,REASON_CARRY
    CHECK_MEM8 test_exit_query_count,1,REASON_EXIT_QUERY_COUNT
    CHECK_MEM8 test_read_count,0,REASON_READ_COUNT
    call w3d_intermission_escape_is_requested
    CHECK_A 1,REASON_ESCAPE_LATCH
    ret

test_loading_ingress_fence:
    ld a,22
    ld (test_case),a
    call test_reset_shell_stubs
    ld hl,test_ingress_fence
    call w3d_intermission_set_ingress_fence_hook
    ld a,9
    ld (w3d_level_requested_index),a
    call w3d_intermission_begin
    call w3d_intermission_loading_tick
    call capture_result
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_CONTINUE,REASON_RESULT
    CHECK_MEM8 test_result_carry,0,REASON_CARRY
    CHECK_MEM8 test_ingress_fence_count,1,REASON_INGRESS_FENCE_COUNT
    CHECK_MEM8 w3d_intermission_ingress_failed,0,REASON_INGRESS_FAILURE
    ret

test_loading_ingress_failure:
    ld a,23
    ld (test_case),a
    call test_reset_shell_stubs
    ld hl,test_ingress_fence
    call w3d_intermission_set_ingress_fence_hook
    ld a,1
    ld (test_ingress_fence_failure),a
    ld a,9
    ld (w3d_level_requested_index),a
    call w3d_intermission_begin
    call w3d_intermission_loading_tick
    call capture_result
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_INGRESS,REASON_RESULT
    CHECK_MEM8 test_result_carry,1,REASON_CARRY
    CHECK_MEM8 test_ingress_fence_count,1,REASON_INGRESS_FENCE_COUNT
    CHECK_MEM8 w3d_intermission_ingress_failed,1,REASON_INGRESS_FAILURE
    CHECK_MEM8 w3d_intermission_animation_counter,0,REASON_ANIMATION_COUNT
    ret

; -----------------------------------------------------------------------------
; Shell/VDP seams. Every plot is recorded as buffer:u16, x:u16, y:u16.
; -----------------------------------------------------------------------------

w3d_shell_setup:
    ld hl,test_setup_count
    inc (hl)
    ret

; Victory-presentation seams are present so the complete production include
; assembles; arithmetic tests call only its non-visual calculation routines.
w3d_shell_clear:
    ret

w3d_shell_query_exit_request:
    xor a
    ret

printString:
    ret

; Injected application-global exit predicate. This models a short Escape tap
; retained by a keycode/render callback after the live keymap is empty.
test_application_exit_query:
    ld hl,test_exit_query_count
    inc (hl)
    ld a,(test_application_exit)
    or a
    ret

; Ordered-ingress seam. Carry set models the finite timeout returned by the
; production screen-info fence after a destination image boundary.
test_ingress_fence:
    ld hl,test_ingress_fence_count
    inc (hl)
    ld a,(test_ingress_fence_failure)
    or a
    ret z
    scf
    ret

; Intermission hook seams. Award receives DE -> little-endian u32; sound
; receives the logical AUDIOWL1 id in A.
test_award_points:
    ld hl,test_award_count
    inc (hl)
    ex de,hl
    ld de,test_award_value
    ld bc,4
    ldir
    ret

test_record_sound:
    push af
    ld a,(test_sound_count)
    cp 16
    jr nc,@count
    ld de,0
    ld e,a
    ld hl,test_sound_log
    add hl,de
    pop af
    ld (hl),a
    push af
@count:
    ld hl,test_sound_count
    inc (hl)
    pop af
    ret

; Deterministic keymap seam. With zero scripted frames this returns the
; mutable test_keymap. Otherwise each call advances through one 16-byte frame,
; retaining the final frame after the script is exhausted.
w3d_shell_read_keyboard:
    ld hl,test_read_count
    inc (hl)
    ld ix,(test_keyboard_script_ptr)
    ld a,(test_keyboard_script_frames)
    or a
    ret z
    dec a
    ld (test_keyboard_script_frames),a
    ret z
    push ix
    pop hl
    ld de,16
    add hl,de
    ld (test_keyboard_script_ptr),hl
    ret

; Retained as a poison seam: the production load-concurrent intermission must
; never fall back to the old blocking shell helper.
w3d_shell_wait_any_press:
    ld hl,test_wait_count
    inc (hl)
    ret

w3d_shell_plot_full_screen:
    ld bc,0
    ld de,0
    jr w3d_shell_plot_at

w3d_shell_plot_at:
    push bc
    push de
    call selectBitmap
    pop de
    pop bc
    jp plotBitmap

selectBitmap:
    ld a,l
    ld (test_selected_bitmap+0),a
    ld a,h
    ld (test_selected_bitmap+1),a
    ret

plotBitmap:
    push af
    ld a,c
    ld (test_plot_x+0),a
    ld a,b
    ld (test_plot_x+1),a
    ld a,e
    ld (test_plot_y+0),a
    ld a,d
    ld (test_plot_y+1),a
    push bc
    push de
    push hl
    ld a,(test_plot_count)
    cp 64
    jr nc,@done
    ld hl,test_plot_log
    or a
    jr z,@address_ready
    ld b,a
@address_loop:
    ld de,6
    add hl,de
    djnz @address_loop
@address_ready:
    ld a,(test_selected_bitmap+0)
    ld (hl),a
    inc hl
    ld a,(test_selected_bitmap+1)
    ld (hl),a
    inc hl
    ld a,(test_plot_x+0)
    ld (hl),a
    inc hl
    ld a,(test_plot_x+1)
    ld (hl),a
    inc hl
    ld a,(test_plot_y+0)
    ld (hl),a
    inc hl
    ld a,(test_plot_y+1)
    ld (hl),a
    ld hl,test_plot_count
    inc (hl)
@done:
    pop hl
    pop de
    pop bc
    pop af
    ret

test_reset_shell_stubs:
    xor a
    ld (test_setup_count),a
    ld (test_wait_count),a
    ld (test_read_count),a
    ld (test_exit_query_count),a
    ld (test_application_exit),a
    ld (test_ingress_fence_count),a
    ld (test_ingress_fence_failure),a
    ld (test_result_a),a
    ld (test_result_carry),a
    ld (test_keyboard_script_frames),a
    ld (test_award_count),a
    ld (test_sound_count),a
    ld hl,test_keymap
    ld (test_keyboard_script_ptr),hl
    call w3d_intermission_reset_application_exit_query_hook
    call w3d_intermission_reset_ingress_fence_hook
    call w3d_intermission_reset_sound_hook
    call w3d_intermission_reset_award_hook
    call w3d_intermission_reset_wait_hook
    ld hl,test_keymap
    ld (hl),a
    ld de,test_keymap+1
    ld bc,15
    ldir
    ld hl,test_award_value
    ld (hl),a
    ld de,test_award_value+1
    ld bc,3
    ldir
    ld hl,test_sound_log
    ld (hl),a
    ld de,test_sound_log+1
    ld bc,15
    ldir
    call test_reset_plot_stub
    ret

test_reset_plot_stub:
    xor a
    ld (test_plot_count),a
    ld hl,test_plot_log
    ld (hl),a
    ld de,test_plot_log+1
    ld bc,test_plot_log_end-test_plot_log-1
    ldir
    ret

; Capture the public A/carry result before assertion macros alter flags.
capture_result:
    ld (test_result_a),a
    ld a,0
    adc a,0
    ld (test_result_carry),a
    ret

; A=actual, B=expected, C=reason.
assert_a:
    ld d,a
    ld hl,result_checks
    inc (hl)
    cp b
    ret z
    ld hl,result_errors
    ld a,(hl)
    inc (hl)
    or a
    ret nz
    ld a,(test_case)
    ld (result_first_case),a
    ld a,c
    ld (result_first_reason),a
    ld a,b
    ld (result_first_expected),a
    ld a,d
    ld (result_first_actual),a
    ret

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
    ld hl,test_ordinary_plot_log
    ld de,37*6
    MOSCALL mos_fwrite
    ld a,(output_handle)
    ld c,a
    MOSCALL mos_fclose
    ret

    macro ACTOR_SEED flags
        ds W3D_ACTOR_FLAGS
        db flags
        ds W3D_ACTOR_SIZE-W3D_ACTOR_FLAGS-1
    endmacro

test_actor_seeds:
    ACTOR_SEED W3D_ACTOR_FLAG_SHOOTABLE
    ACTOR_SEED 0                    ; inert/dead actor: must not count
    ACTOR_SEED W3D_ACTOR_FLAG_SHOOTABLE|004h
    ACTOR_SEED 080h                 ; active-looking but not shootable
    ACTOR_SEED W3D_ACTOR_FLAG_SHOOTABLE

    macro STATIC_SEED item
        db 0,0,0,0,0,item
    endmacro

test_static_seeds:
    STATIC_SEED 8
    STATIC_SEED W3D_ITEM_CROSS
    STATIC_SEED W3D_ITEM_CHALICE
    STATIC_SEED W3D_ITEM_BIBLE
    STATIC_SEED W3D_ITEM_CROWN
    STATIC_SEED 13
    STATIC_SEED 17
    STATIC_SEED W3D_ITEM_FULLHEAL
    STATIC_SEED 19

    macro VICTORY_RATIO kill,secret,treasure,time
        dw kill
        dw secret
        dw treasure
        dw time
        dw 0
    endmacro

; Totals: 1200 seconds, 520 kills, 280 secrets, 800 treasures.
test_victory_ratios:
    VICTORY_RATIO 100,0,100,90
    VICTORY_RATIO 90,10,100,120
    VICTORY_RATIO 80,20,100,120
    VICTORY_RATIO 70,30,100,210
    VICTORY_RATIO 60,40,100,180
    VICTORY_RATIO 50,50,100,180
    VICTORY_RATIO 40,60,100,150
    VICTORY_RATIO 30,70,100,150

result_filename: db "intermission_result.bin",0
output_handle: db 0
test_case: db 0
test_total_low: db 0
test_total_high: db 0
test_selected_bitmap: dw 0
test_plot_x: dw 0
test_plot_y: dw 0
test_setup_count: db 0
test_wait_count: db 0
test_read_count: db 0
test_exit_query_count: db 0
test_application_exit: db 0
test_ingress_fence_count: db 0
test_ingress_fence_failure: db 0
test_award_count: db 0
test_award_value: ds 4
test_sound_count: db 0
test_sound_log: ds 16
test_result_a: db 0
test_result_carry: db 0
test_keyboard_script_ptr: dl test_keymap
test_keyboard_script_frames: db 0
test_keymap: ds 16
test_finish_input_script:
    db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 ; complete release
    db 1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 ; fresh non-Escape key
    db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 ; release after acknowledgment
test_plot_count: db 0
test_plot_log: ds 64*6
test_plot_log_end:
test_ordinary_plot_log: ds 37*6

result_data:
    db "W3I1"
result_checks: db 0
result_errors: db 0
result_first_case: db 0ffh
result_first_reason: db 0
result_first_expected: db 0
result_first_actual: db 0
    db 0,0,0,0,0,0
result_end:
