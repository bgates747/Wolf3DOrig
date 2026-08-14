; Direct real-eZ80 semantic regression for the production application shell.
; Production input is replaced through its public keyboard hook; rendering is
; recorded by test doubles so buffer IDs and original anchors are observable.
    assume adl=1
    org 040000h
    jp start
    align 64
    db "MOS",0,1

mos_fopen: equ 0ah
mos_fclose: equ 0bh
mos_fwrite: equ 1bh
mos_getkbmap: equ 1eh
fa_write: equ 02h
fa_create_always: equ 08h

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

    macro TEST_EPISODE_DRAW v0,b0,p0,p1,p2
        ld a,p2
        ld (test_case),a
        call test_reset_plots
        ld a,v0
        ld (w3d_shell_episode_choice),a
        call w3d_shell_draw_episode_menu
        CHECK_MEM8 test_plot_count,3,REASON_PLOT_COUNT
        CHECK_PLOT 6,b0,98,p0
        CHECK_PLOT 12,W3D_SHELL_CURSOR_1_BUFFER,8,p1
    endmacro

    macro TEST_DIFFICULTY_DRAW v0,b0,p0,p1,b1,p2
        ld a,p2
        ld (test_case),a
        call test_reset_plots
        ld a,v0
        ld (w3d_shell_difficulty),a
        call w3d_shell_draw_difficulty_menu
        CHECK_MEM8 test_plot_count,4,REASON_PLOT_COUNT
        CHECK_PLOT 6,b0,74,p0
        CHECK_PLOT 12,W3D_SHELL_CURSOR_1_BUFFER,48,p1
        CHECK_PLOT 18,b1,235,107
    endmacro

    include "wolf3d_shell_assets.inc"
w3d_app_version_text: db "Wolf3DOrig App 0.1.0 Alpha 1",0
w3d_requested_difficulty: db 2
    include "wolf3d_shell.inc"

SCRIPT_RELEASE: equ 0
SCRIPT_UP: equ 1
SCRIPT_DOWN: equ 2
SCRIPT_RETURN: equ 3
SCRIPT_KEYPAD: equ 4
SCRIPT_SPACE: equ 5
SCRIPT_ESCAPE: equ 6
SCRIPT_ANY: equ 7

REASON_ACTION: equ 1
REASON_RESULT: equ 2
REASON_FLAGS: equ 3
REASON_SELECTION: equ 4
REASON_DIFFICULTY: equ 5
REASON_NOTICE: equ 6
REASON_VERSION: equ 7
REASON_PLOT_COUNT: equ 8
REASON_PLOT_BUFFER: equ 9
REASON_PLOT_X: equ 10
REASON_PLOT_Y: equ 11

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
    ld a,0ffh
    ld (result_first_case),a
    ld hl,test_keyboard_hook
    call w3d_shell_set_keyboard_read_hook
    call test_input_actions
    call test_main_results
    call test_episode_semantics
    call test_difficulty_semantics
    call test_lifecycle_entries
    call test_draw_contract
    call write_result
    ret

test_input_actions:
    ld a,1
    ld (test_case),a
    ld hl,script_action_up
    call test_set_script
    call w3d_shell_wait_action
    CHECK_A W3D_SHELL_ACTION_UP,REASON_ACTION
    ld a,2
    ld (test_case),a
    ld hl,script_action_down
    call test_set_script
    call w3d_shell_wait_action
    CHECK_A W3D_SHELL_ACTION_DOWN,REASON_ACTION
    ld a,3
    ld (test_case),a
    ld hl,script_action_return
    call test_set_script
    call w3d_shell_wait_action
    CHECK_A W3D_SHELL_ACTION_ACCEPT,REASON_ACTION
    ld a,4
    ld (test_case),a
    ld hl,script_action_keypad
    call test_set_script
    call w3d_shell_wait_action
    CHECK_A W3D_SHELL_ACTION_ACCEPT,REASON_ACTION
    ld a,5
    ld (test_case),a
    ld hl,script_action_space
    call test_set_script
    call w3d_shell_wait_action
    CHECK_A W3D_SHELL_ACTION_ACCEPT,REASON_ACTION
    ld a,6
    ld (test_case),a
    ld hl,script_action_escape
    call test_set_script
    call w3d_shell_wait_action
    CHECK_A W3D_SHELL_ACTION_ESCAPE,REASON_ACTION
    ret

test_main_results:
    ld a,7
    ld (test_case),a
    ld hl,script_main_quit
    call test_set_script
    call w3d_shell_main_menu
    jr z,@quit_z
    ld a,1
    jr @quit_flag
@quit_z:
    xor a
@quit_flag:
    CHECK_A 0,REASON_FLAGS
    CHECK_MEM8 w3d_shell_main_choice,W3D_SHELL_MAIN_QUIT,REASON_SELECTION
    ld a,8
    ld (test_case),a
    ld hl,script_main_escape
    call test_set_script
    call w3d_shell_main_menu
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    ld a,9
    ld (test_case),a
    ld hl,script_new_game_medium
    call test_set_script
    call w3d_shell_main_menu
    jr nz,@new_nz
    xor a
    jr @new_flag
@new_nz:
    ld a,1
@new_flag:
    CHECK_A 1,REASON_FLAGS
    CHECK_MEM8 w3d_requested_difficulty,2,REASON_DIFFICULTY
    ret

test_episode_semantics:
    ld a,10
    ld (test_case),a
    call test_reset_plots
    ld hl,script_episode_locked_wrap
    call test_set_script
    call w3d_shell_choose_episode
    CHECK_A 1,REASON_RESULT
    CHECK_MEM8 w3d_shell_episode_choice,0,REASON_SELECTION
    CHECK_MEM8 test_notice_plots,1,REASON_NOTICE
; Proves difficulty Escape routes back to episode, then episode Escape routes
; to main. Directly returning difficulty Escape to main consumes the wrong key.
    ld a,11
    ld (test_case),a
    ld hl,script_difficulty_back_to_episode
    call test_set_script
    call w3d_shell_main_menu
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_MEM8 w3d_shell_main_choice,W3D_SHELL_MAIN_QUIT,REASON_SELECTION
    ret

test_difficulty_semantics:
    ld a,12
    ld (test_case),a
    ld hl,script_difficulty_medium
    call test_set_script
    call w3d_shell_choose_difficulty
    CHECK_A 1,REASON_RESULT
    CHECK_MEM8 w3d_requested_difficulty,2,REASON_DIFFICULTY
    ld a,13
    ld (test_case),a
    ld hl,script_difficulty_hard
    call test_set_script
    call w3d_shell_choose_difficulty
    CHECK_A 1,REASON_RESULT
    CHECK_MEM8 w3d_requested_difficulty,3,REASON_DIFFICULTY
    ld a,14
    ld (test_case),a
    ld hl,script_difficulty_easy
    call test_set_script
    call w3d_shell_choose_difficulty
    CHECK_A 1,REASON_RESULT
    CHECK_MEM8 w3d_requested_difficulty,1,REASON_DIFFICULTY
    ld a,15
    ld (test_case),a
    ld hl,script_difficulty_baby
    call test_set_script
    call w3d_shell_choose_difficulty
    CHECK_A 1,REASON_RESULT
    CHECK_MEM8 w3d_requested_difficulty,0,REASON_DIFFICULTY
    ret

test_lifecycle_entries:
    ld a,16
    ld (test_case),a
    xor a
    ld (test_version_prints),a
    ld hl,script_ack_then_escape
    call test_set_script
    call w3d_shell_run
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_MEM8 test_version_prints,1,REASON_VERSION
    ld a,17
    ld (test_case),a
    ld hl,script_ack_then_escape
    call test_set_script
    call w3d_shell_resume_after_victory
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    ret

test_draw_contract:
    ld a,18
    ld (test_case),a
    call test_reset_plots
    xor a
    ld (w3d_shell_main_choice),a
    call w3d_shell_draw_main_menu
    CHECK_MEM8 test_plot_count,3,REASON_PLOT_COUNT
    CHECK_PLOT 6,W3D_SHELL_MAIN_NEW_GAME_SELECTED_BUFFER,100,55
    CHECK_PLOT 12,W3D_SHELL_CURSOR_1_BUFFER,72,53
    ld a,19
    ld (test_case),a
    call test_reset_plots
    ld a,1
    ld (w3d_shell_main_choice),a
    call w3d_shell_draw_main_menu
    CHECK_MEM8 test_plot_count,3,REASON_PLOT_COUNT
    CHECK_PLOT 6,W3D_SHELL_MAIN_QUIT_SELECTED_BUFFER,100,172
    CHECK_PLOT 12,W3D_SHELL_CURSOR_1_BUFFER,72,170
    TEST_EPISODE_DRAW 0,W3D_SHELL_EPISODE_1_SELECTED_BUFFER,23,21,20
    TEST_EPISODE_DRAW 1,W3D_SHELL_EPISODE_2_SELECTED_BUFFER,49,47,21
    TEST_EPISODE_DRAW 2,W3D_SHELL_EPISODE_3_SELECTED_BUFFER,75,73,22
    TEST_EPISODE_DRAW 3,W3D_SHELL_EPISODE_4_SELECTED_BUFFER,101,99,23
    TEST_EPISODE_DRAW 4,W3D_SHELL_EPISODE_5_SELECTED_BUFFER,127,125,24
    TEST_EPISODE_DRAW 5,W3D_SHELL_EPISODE_6_SELECTED_BUFFER,153,151,25
    TEST_DIFFICULTY_DRAW 0,W3D_SHELL_DIFFICULTY_BABY_SELECTED_BUFFER,100,98,W3D_SHELL_DIFFICULTY_BABY_BUFFER,26
    TEST_DIFFICULTY_DRAW 1,W3D_SHELL_DIFFICULTY_EASY_SELECTED_BUFFER,113,111,W3D_SHELL_DIFFICULTY_EASY_BUFFER,27
    TEST_DIFFICULTY_DRAW 2,W3D_SHELL_DIFFICULTY_NORMAL_SELECTED_BUFFER,126,124,W3D_SHELL_DIFFICULTY_NORMAL_BUFFER,28
    TEST_DIFFICULTY_DRAW 3,W3D_SHELL_DIFFICULTY_HARD_SELECTED_BUFFER,139,137,W3D_SHELL_DIFFICULTY_HARD_BUFFER,29
    ret

test_set_script:
    ld (test_script_pointer),hl
    ret

test_keyboard_hook:
    xor a
    ld hl,test_keymap
    ld (hl),a
    ld de,test_keymap+1
    ld bc,15
    ldir
    ld hl,(test_script_pointer)
    ld a,(hl)
    inc hl
    ld (test_script_pointer),hl
    cp SCRIPT_UP
    jr z,@up
    cp SCRIPT_DOWN
    jr z,@down
    cp SCRIPT_RETURN
    jr z,@return
    cp SCRIPT_KEYPAD
    jr z,@keypad
    cp SCRIPT_SPACE
    jr z,@space
    cp SCRIPT_ESCAPE
    jr z,@escape
    cp SCRIPT_ANY
    jr z,@any
    jr @done
@up:
    ld a,00000010b
    ld (test_keymap+7),a
    jr @done
@down:
    ld a,00000010b
    ld (test_keymap+5),a
    jr @done
@return:
    ld a,00000010b
    ld (test_keymap+9),a
    jr @done
@keypad:
    ld a,00010000b
    ld (test_keymap+7),a
    jr @done
@space:
    ld a,00000100b
    ld (test_keymap+12),a
    jr @done
@escape:
    ld a,00000001b
    ld (test_keymap+14),a
    jr @done
@any:
    ld a,1
    ld (test_keymap+1),a
@done:
    ld ix,test_keymap
    ret

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
    ld a,(test_selected_bitmap+1)
    cp W3D_SHELL_EPISODE_UNAVAILABLE_NOTICE_BUFFER>>8
    jr nz,@not_notice
    ld a,(test_selected_bitmap+0)
    cp W3D_SHELL_EPISODE_UNAVAILABLE_NOTICE_BUFFER&0ffh
    jr nz,@not_notice
    ld hl,test_notice_plots
    inc (hl)
@not_notice:
    ld a,(test_plot_count)
    cp 32
    jr nc,@done
    ld hl,test_plot_log
    or a
    jr z,@address_ready
    ld b,a
@address_loop:
    ld de,6                 ; full ADL immediate, including DEU=0
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

printString:
    push af
    push de
    push hl
    ld de,w3d_app_version_text
    or a
    sbc hl,de
    jr nz,@not_version
    ld hl,test_version_prints
    inc (hl)
@not_version:
    pop hl
    pop de
    pop af
    ret

test_reset_plots:
    xor a
    ld (test_plot_count),a
    ld (test_notice_plots),a
    ld hl,test_plot_log
    ld (hl),a
    ld de,test_plot_log+1
    ld bc,test_plot_log_end-test_plot_log-1
    ldir
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

result_filename: db "shell_result.bin",0
output_handle: db 0
test_case: db 0
test_script_pointer: dl 0
test_keymap: ds 16
test_selected_bitmap: dw 0
test_plot_x: dw 0
test_plot_y: dw 0
test_plot_count: db 0
test_notice_plots: db 0
test_version_prints: db 0
test_plot_log: ds 32*6
test_plot_log_end:

result_data:
    db "W3S1"
result_checks: db 0
result_errors: db 0
result_first_case: db 0ffh
result_first_reason: db 0
result_first_expected: db 0
result_first_actual: db 0
    db 0,0,0,0,0,0
result_end:

script_action_up: db SCRIPT_UP,SCRIPT_RELEASE
script_action_down: db SCRIPT_DOWN,SCRIPT_RELEASE
script_action_return: db SCRIPT_RETURN,SCRIPT_RELEASE
script_action_keypad: db SCRIPT_KEYPAD,SCRIPT_RELEASE
script_action_space: db SCRIPT_SPACE,SCRIPT_RELEASE
script_action_escape: db SCRIPT_ESCAPE,SCRIPT_RELEASE
script_main_quit: db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_SPACE,SCRIPT_RELEASE
script_main_escape: db SCRIPT_ESCAPE,SCRIPT_RELEASE
script_new_game_medium:
    db SCRIPT_RETURN,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
    db SCRIPT_RETURN,SCRIPT_RELEASE
script_episode_locked_wrap:
    db SCRIPT_UP,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
    db SCRIPT_RELEASE,SCRIPT_ANY,SCRIPT_RELEASE
    db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
script_difficulty_back_to_episode:
    db SCRIPT_RETURN,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
    db SCRIPT_ESCAPE,SCRIPT_RELEASE,SCRIPT_ESCAPE,SCRIPT_RELEASE
    db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
script_difficulty_medium: db SCRIPT_RETURN,SCRIPT_RELEASE
script_difficulty_hard: db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
script_difficulty_easy: db SCRIPT_UP,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
script_difficulty_baby:
    db SCRIPT_UP,SCRIPT_RELEASE,SCRIPT_UP,SCRIPT_RELEASE
    db SCRIPT_RETURN,SCRIPT_RELEASE
script_ack_then_escape:
    db SCRIPT_RELEASE,SCRIPT_ANY,SCRIPT_RELEASE,SCRIPT_ESCAPE,SCRIPT_RELEASE
