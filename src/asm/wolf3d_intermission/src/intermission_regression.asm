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

; Production-owned globals are reduced to the exact fields this include reads.
w3d_level_requested_index:  db 0
w3d_level_actor_seed_ptr:   dl test_actor_seeds
w3d_level_actor_count:      db 0
w3d_level_static_seed_ptr:  dl test_static_seeds
w3d_level_static_count:     dw 0
w3d_player_kill_count:      dw 0
w3d_player_treasure_count:  dw 0

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
    call w3d_intermission_begin
    call capture_result

    CHECK_MEM8 test_setup_count,1,REASON_SETUP_COUNT
    CHECK_MEM8 test_wait_count,0,REASON_WAIT_COUNT
    CHECK_MEM8 test_plot_count,19,REASON_PLOT_COUNT
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
    CHECK_PLOT 12,W3D_INTERMISSION_DIGIT_0_BUFFER+1,208,16
    CHECK_PLOT 18,W3D_INTERMISSION_DIGIT_0_BUFFER+0,208,80
    CHECK_PLOT 24,W3D_INTERMISSION_DIGIT_0_BUFFER+1,224,80
    CHECK_PLOT 30,W3D_INTERMISSION_COLON_BUFFER,240,80
    CHECK_PLOT 36,W3D_INTERMISSION_DIGIT_0_BUFFER+0,248,80
    CHECK_PLOT 42,W3D_INTERMISSION_DIGIT_0_BUFFER+2,264,80
    CHECK_PLOT 48,W3D_INTERMISSION_DIGIT_0_BUFFER+0,208,96
    CHECK_PLOT 54,W3D_INTERMISSION_DIGIT_0_BUFFER+1,224,96
    CHECK_PLOT 60,W3D_INTERMISSION_COLON_BUFFER,240,96
    CHECK_PLOT 66,W3D_INTERMISSION_DIGIT_0_BUFFER+3,248,96
    CHECK_PLOT 72,W3D_INTERMISSION_DIGIT_0_BUFFER+0,264,96
; 2/3 kills -> 66%, secret -> 0%, 5/5 treasures -> 100%.
    CHECK_PLOT 78,W3D_INTERMISSION_DIGIT_0_BUFFER+6,264,112
    CHECK_PLOT 84,W3D_INTERMISSION_DIGIT_0_BUFFER+6,280,112
    CHECK_PLOT 90,W3D_INTERMISSION_DIGIT_0_BUFFER+0,280,128
    CHECK_PLOT 96,W3D_INTERMISSION_DIGIT_0_BUFFER+1,248,144
    CHECK_PLOT 102,W3D_INTERMISSION_DIGIT_0_BUFFER+0,264,144
    CHECK_PLOT 108,W3D_INTERMISSION_DIGIT_0_BUFFER+0,280,144
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
    CHECK_MEM8 test_plot_count,2,REASON_PLOT_COUNT
    CHECK_MEM8 test_result_a,W3D_INTERMISSION_RESULT_CONTINUE,REASON_RESULT
    CHECK_MEM8 test_result_carry,0,REASON_CARRY
    CHECK_PLOT 0,W3D_INTERMISSION_SECRET_BASE_BUFFER,0,0
    CHECK_PLOT 6,W3D_INTERMISSION_STATUSBAR_BUFFER,0,200
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

; -----------------------------------------------------------------------------
; Shell/VDP seams. Every plot is recorded as buffer:u16, x:u16, y:u16.
; -----------------------------------------------------------------------------

w3d_shell_setup:
    ld hl,test_setup_count
    inc (hl)
    ret

; Injected application-global exit predicate. This models a short Escape tap
; retained by a keycode/render callback after the live keymap is empty.
test_application_exit_query:
    ld hl,test_exit_query_count
    inc (hl)
    ld a,(test_application_exit)
    or a
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
    cp 32
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
    ld (test_result_a),a
    ld (test_result_carry),a
    ld (test_keyboard_script_frames),a
    ld hl,test_keymap
    ld (test_keyboard_script_ptr),hl
    call w3d_intermission_reset_application_exit_query_hook
    ld hl,test_keymap
    ld (hl),a
    ld de,test_keymap+1
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
test_plot_log: ds 32*6
test_plot_log_end:

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
