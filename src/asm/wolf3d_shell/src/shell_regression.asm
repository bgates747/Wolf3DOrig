; Direct real-eZ80 semantic regression for the production application shell.
; Production input is replaced through its public keyboard hook; rendering is
; recorded by test doubles so buffer IDs and original anchors are observable.
    assume adl=1
    org 040000h
    jp start
    align 64
    db "MOS",0,1

mos_fopen: equ 0ah
mos_getkey: equ 00h
mos_fclose: equ 0bh
mos_fwrite: equ 1bh
mos_getkbmap: equ 1eh
sysvar_time: equ 0
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

    macro CHECK_EXIT expected
        call w3d_shell_query_exit_request
        CHECK_A expected,REASON_EXIT_LATCH
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
w3d_sysvars_pointer: dl test_sysvars

; Save/load persistence itself has a separate direct regression. This shell
; fixture exposes one validated slot and records load dispatch.
w3d_save_slot_load:
    ld hl,test_save_load_count
    inc (hl)
    or a
    ret
w3d_save_slot_store:
    ld hl,test_save_store_count
    inc (hl)
    or a
    ret
w3d_save_slot_available:
    db 1,0,0,0,0,0,0,0,0,0
w3d_save_slot_names:
    db "Regression slot",0
    ds 32-16
    ds 9*32

; The full victory presentation has its own direct regression.  This shell
; seam records that the production lifecycle invokes it exactly once before
; returning to the main menu.
w3d_victory_present:
    ld hl,test_victory_present_count
    inc (hl)
    ret

w3d_highscores_handle_game_end:
    ld hl,test_highscore_handoff_count
    inc (hl)
    ret

w3d_highscores_view:
    ld hl,test_highscore_view_count
    inc (hl)
    ret

w3d_highscores_draw:
    ld hl,test_highscore_draw_count
    inc (hl)
    ret

    include "wolf3d_shell.inc"

SCRIPT_RELEASE: equ 0
SCRIPT_UP: equ 1
SCRIPT_DOWN: equ 2
SCRIPT_RETURN: equ 3
SCRIPT_KEYPAD: equ 4
SCRIPT_SPACE: equ 5
SCRIPT_ESCAPE: equ 6
SCRIPT_ANY: equ 7
SCRIPT_ESCAPE_ACCEPT: equ 8
SCRIPT_TICK: equ 9

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
REASON_EXIT_LATCH: equ 12
REASON_VICTORY_PRESENT: equ 13
REASON_HIGHSCORE_HANDOFF: equ 14
REASON_CONFIRM_PLOTS: equ 15
REASON_SFX_PREFERENCE: equ 16

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
    ld hl,test_key_hook
    call w3d_shell_set_key_read_hook
    ld a,1
    call mark_stage
    call test_input_actions
    ld a,2
    call mark_stage
    call test_main_results
    ld a,3
    call mark_stage
    call test_episode_semantics
    ld a,4
    call mark_stage
    call test_difficulty_semantics
    ld a,5
    call mark_stage
    call test_lifecycle_entries
    ld a,6
    call mark_stage
    call test_pause_menu
    ld a,7
    call mark_stage
    call test_control_pages
    ld a,8
    call mark_stage
    call test_attract_timing
    ld a,9
    call mark_stage
    call test_draw_contract
    ld a,1
    ld (result_done),a
    call write_result
    ret

; Publish a partial receipt before each finite group. The host runner waits
; for result_done, but can name the exact group if a target-side loop stalls.
mark_stage:
    ld (result_stage),a
    jp write_result

test_input_actions:
    call w3d_shell_reset_exit_request
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
    CHECK_EXIT 1
    call w3d_shell_reset_exit_request
    ld hl,script_action_escape_accept
    call test_set_script
    call w3d_shell_wait_action
    CHECK_A W3D_SHELL_ACTION_ESCAPE,REASON_ACTION
    CHECK_EXIT 1
    ld a,7
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_wait_any_ordinary
    call test_set_script
    call w3d_shell_wait_any_press
    CHECK_EXIT 0
    ld a,8
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_wait_any_escape
    call test_set_script
    call w3d_shell_wait_any_press
    CHECK_EXIT 1
    call w3d_shell_reset_exit_request
    ld hl,script_wait_any_held_ordinary_then_escape
    call test_set_script
    call w3d_shell_wait_any_press
    CHECK_EXIT 1
    call w3d_shell_reset_exit_request
    ld hl,script_wait_any_held_escape
    call test_set_script
    call w3d_shell_wait_any_press
    CHECK_EXIT 1
    ret

test_main_results:
    ld a,9
    ld (test_case),a
    add a,100
    call mark_stage
    call w3d_shell_reset_exit_request
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
    CHECK_EXIT 0
    ld a,10
    ld (test_case),a
    add a,100
    call mark_stage
    call w3d_shell_reset_exit_request
    ld hl,script_main_escape
    call test_set_script
    call w3d_shell_main_menu
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_EXIT 1
    ld a,11
    ld (test_case),a
    add a,100
    call mark_stage
    call w3d_shell_reset_exit_request
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
    CHECK_EXIT 0
    ld a,36
    ld (test_case),a
    add a,100
    call mark_stage
    call w3d_shell_reset_exit_request
    xor a
    ld (test_highscore_view_count),a
    ld hl,script_main_view_scores
    call test_set_script
    call w3d_shell_main_menu
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_MEM8 test_highscore_view_count,1,REASON_HIGHSCORE_HANDOFF
    CHECK_EXIT 1
    ld a,47
    ld (test_case),a
    add a,100
    call mark_stage
    call w3d_shell_reset_exit_request
    xor a
    ld (test_save_load_count),a
    ld hl,script_main_load_game
    call test_set_script
    call w3d_shell_main_menu
    CHECK_A W3D_SHELL_RESULT_LOAD_GAME,REASON_RESULT
    CHECK_MEM8 test_save_load_count,1,REASON_SELECTION
    CHECK_EXIT 0
    ret

test_episode_semantics:
    ld a,12
    ld (test_case),a
    call w3d_shell_reset_exit_request
    call test_reset_plots
    ld hl,script_episode_locked_wrap
    call test_set_script
    call w3d_shell_choose_episode
    CHECK_A 1,REASON_RESULT
    CHECK_MEM8 w3d_shell_episode_choice,0,REASON_SELECTION
    CHECK_MEM8 test_notice_plots,1,REASON_NOTICE
    CHECK_EXIT 0
    ld a,13
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_episode_escape
    call test_set_script
    call w3d_shell_choose_episode
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_EXIT 1
    ld a,14
    ld (test_case),a
    call w3d_shell_reset_exit_request
    call test_reset_plots
    ld hl,script_episode_unavailable_escape
    call test_set_script
    call w3d_shell_choose_episode
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_MEM8 test_notice_plots,1,REASON_NOTICE
    CHECK_EXIT 1
    ld a,15
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_main_episode_escape
    call test_set_script
    call w3d_shell_main_menu
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_EXIT 1
    ret

test_difficulty_semantics:
    ld a,16
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_difficulty_medium
    call test_set_script
    call w3d_shell_choose_difficulty
    CHECK_A 1,REASON_RESULT
    CHECK_MEM8 w3d_requested_difficulty,2,REASON_DIFFICULTY
    CHECK_EXIT 0
    ld a,17
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_difficulty_hard
    call test_set_script
    call w3d_shell_choose_difficulty
    CHECK_A 1,REASON_RESULT
    CHECK_MEM8 w3d_requested_difficulty,3,REASON_DIFFICULTY
    CHECK_EXIT 0
    ld a,18
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_difficulty_easy
    call test_set_script
    call w3d_shell_choose_difficulty
    CHECK_A 1,REASON_RESULT
    CHECK_MEM8 w3d_requested_difficulty,1,REASON_DIFFICULTY
    CHECK_EXIT 0
    ld a,19
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_difficulty_baby
    call test_set_script
    call w3d_shell_choose_difficulty
    CHECK_A 1,REASON_RESULT
    CHECK_MEM8 w3d_requested_difficulty,0,REASON_DIFFICULTY
    CHECK_EXIT 0
    ld a,20
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_difficulty_escape
    call test_set_script
    call w3d_shell_choose_difficulty
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_EXIT 1
    ld a,21
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_main_difficulty_escape
    call test_set_script
    call w3d_shell_main_menu
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_EXIT 1
    ret

test_lifecycle_entries:
    ld a,22
    ld (test_case),a
    xor a
    ld (test_version_prints),a
    ld hl,script_title_escape
    call test_set_script
    call w3d_shell_run
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_MEM8 test_version_prints,1,REASON_VERSION
    CHECK_EXIT 1
    ld a,23
    ld (test_case),a
    xor a
    ld (test_version_prints),a
    ld hl,script_ack_then_escape
    call test_set_script
    call w3d_shell_run
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_MEM8 test_version_prints,1,REASON_VERSION
    CHECK_EXIT 1
    ld a,24
    ld (test_case),a
    call w3d_shell_reset_exit_request
    xor a
    ld (test_victory_present_count),a
    ld (test_highscore_handoff_count),a
    ld hl,script_victory_escape
    call test_set_script
    call w3d_shell_resume_after_victory
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_MEM8 test_victory_present_count,1,REASON_VICTORY_PRESENT
    CHECK_MEM8 test_highscore_handoff_count,1,REASON_HIGHSCORE_HANDOFF
    CHECK_EXIT 1
    ld a,25
    ld (test_case),a
    call w3d_shell_reset_exit_request
    xor a
    ld (test_victory_present_count),a
    ld (test_highscore_handoff_count),a
    ld hl,script_ack_then_escape
    call test_set_script
    call w3d_shell_resume_after_victory
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_MEM8 test_victory_present_count,1,REASON_VICTORY_PRESENT
    CHECK_MEM8 test_highscore_handoff_count,1,REASON_HIGHSCORE_HANDOFF
    CHECK_EXIT 1
    ld a,35
    ld (test_case),a
    call w3d_shell_reset_exit_request
    xor a
    ld (test_victory_present_count),a
    ld (test_highscore_handoff_count),a
    ld hl,script_action_escape
    call test_set_script
    call w3d_shell_resume_after_game_over
    CHECK_A W3D_SHELL_RESULT_QUIT,REASON_RESULT
    CHECK_MEM8 test_victory_present_count,0,REASON_VICTORY_PRESENT
    CHECK_MEM8 test_highscore_handoff_count,1,REASON_HIGHSCORE_HANDOFF
    CHECK_EXIT 1
    ret

test_pause_menu:
    ld a,39
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_pause_escape
    call test_set_script
    call w3d_shell_pause_menu
    CHECK_A W3D_SHELL_PAUSE_RESUME,REASON_RESULT
    CHECK_EXIT 0
    ld a,40
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_pause_end
    call test_set_script
    ld hl,script_confirm_yes
    call test_set_key_script
    call w3d_shell_pause_menu
    CHECK_A W3D_SHELL_PAUSE_END_GAME,REASON_RESULT
    CHECK_EXIT 0
    ld a,45
    ld (test_case),a
    call w3d_shell_reset_exit_request
    call test_reset_plots
    ld hl,script_pause_end_then_back
    call test_set_script
    ld hl,script_confirm_no
    call test_set_key_script
    call w3d_shell_pause_menu
    CHECK_A W3D_SHELL_PAUSE_RESUME,REASON_RESULT
    CHECK_EXIT 0
    CHECK_MEM8 test_plot_count,21,REASON_CONFIRM_PLOTS
    CHECK_PLOT 60,W3D_SHELL_END_GAME_NOTICE_BUFFER,53,76
    ld a,46
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_pause_end_then_back
    call test_set_script
    ld hl,script_confirm_escape
    call test_set_key_script
    call w3d_shell_pause_menu
    CHECK_A W3D_SHELL_PAUSE_RESUME,REASON_RESULT
    CHECK_EXIT 0
    ld a,41
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_pause_quit
    call test_set_script
    call w3d_shell_pause_menu
    CHECK_A W3D_SHELL_PAUSE_QUIT,REASON_RESULT
    CHECK_EXIT 1
    ld a,42
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_pause_accept_back
    call test_set_script
    call w3d_shell_pause_menu
    CHECK_A W3D_SHELL_PAUSE_RESUME,REASON_RESULT
    CHECK_EXIT 0
    ld a,48
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld hl,script_pause_new_game
    call test_set_script
    call w3d_shell_pause_menu
    CHECK_A W3D_SHELL_PAUSE_NEW_GAME,REASON_RESULT
    CHECK_MEM8 w3d_requested_difficulty,2,REASON_DIFFICULTY
    CHECK_EXIT 0
    ret

test_control_pages:
    ld a,49
    ld (test_case),a
    call w3d_shell_reset_exit_request
    ld a,1
    ld (w3d_audio_sfx_enabled),a
    call test_reset_plots
    ld hl,script_sound_toggle_return
    call test_set_script
    call w3d_shell_sound_page
    CHECK_MEM8 w3d_audio_sfx_enabled,0,REASON_SFX_PREFERENCE
    CHECK_EXIT 0
    CHECK_MEM8 test_plot_count,2,REASON_PLOT_COUNT
    CHECK_PLOT 0,W3D_SHELL_SOUND_ON_PAGE_BUFFER,0,0
    CHECK_PLOT 6,W3D_SHELL_SOUND_OFF_PAGE_BUFFER,0,0
    ld a,1
    ld (w3d_audio_sfx_enabled),a
    ld a,50
    ld (test_case),a
    call test_reset_plots
    ld hl,script_local_escape
    call test_set_script
    ld hl,W3D_SHELL_CONTROL_PAGE_BUFFER
    call w3d_shell_information_page
    CHECK_EXIT 0
    CHECK_MEM8 test_plot_count,1,REASON_PLOT_COUNT
    CHECK_PLOT 0,W3D_SHELL_CONTROL_PAGE_BUFFER,0,0
    ret

test_attract_timing:
    ld a,51
    ld (test_case),a
    xor a
    ld (test_highscore_draw_count),a
    ld hl,test_sysvars
    ld (hl),a
    ld de,test_sysvars+1
    ld bc,23
    ldir
    call test_reset_plots
    ld hl,script_attract_cycle
    call test_set_script
    call w3d_shell_attract_until_input
    CHECK_MEM8 test_highscore_draw_count,1,REASON_HIGHSCORE_HANDOFF
    CHECK_MEM8 test_plot_count,3,REASON_PLOT_COUNT
    CHECK_PLOT 0,W3D_SHELL_TITLE_BUFFER,0,0
    CHECK_PLOT 6,W3D_SHELL_CREDITS_BUFFER,0,0
    CHECK_PLOT 12,W3D_SHELL_TITLE_BUFFER,0,0
    CHECK_EXIT 0
    ret

test_draw_contract:
    ld a,26
    ld (test_case),a
    call test_reset_plots
    CHECK_MEM8 w3d_shell_main_selected_buffers+0,W3D_SHELL_MAIN_NEW_GAME_SELECTED_BUFFER&0ffh,REASON_PLOT_BUFFER
    CHECK_MEM8 w3d_shell_main_selected_buffers+1,W3D_SHELL_MAIN_NEW_GAME_SELECTED_BUFFER>>8,REASON_PLOT_BUFFER
    xor a
    ld (w3d_shell_main_choice),a
    call w3d_shell_draw_main_menu
    CHECK_MEM8 test_plot_count,3,REASON_PLOT_COUNT
    CHECK_MEM8 test_plot_log+0,W3D_SHELL_MAIN_BASE_BUFFER&0ffh,REASON_PLOT_BUFFER
    CHECK_MEM8 test_selected_bitmap+0,W3D_SHELL_CURSOR_1_BUFFER&0ffh,REASON_PLOT_BUFFER
    CHECK_MEM8 test_select_history+2,W3D_SHELL_MAIN_NEW_GAME_SELECTED_BUFFER&0ffh,REASON_PLOT_BUFFER
    CHECK_MEM8 test_select_history+3,W3D_SHELL_MAIN_NEW_GAME_SELECTED_BUFFER>>8,REASON_PLOT_BUFFER
    CHECK_PLOT 6,W3D_SHELL_MAIN_NEW_GAME_SELECTED_BUFFER,100,55
    CHECK_PLOT 12,W3D_SHELL_CURSOR_1_BUFFER,72,53
    ld a,27
    ld (test_case),a
    call test_reset_plots
    ld a,W3D_SHELL_MAIN_VIEW_SCORES
    ld (w3d_shell_main_choice),a
    call w3d_shell_draw_main_menu
    CHECK_MEM8 test_plot_count,3,REASON_PLOT_COUNT
    CHECK_PLOT 6,W3D_SHELL_MAIN_VIEW_SCORES_SELECTED_BUFFER,100,146
    CHECK_PLOT 12,W3D_SHELL_CURSOR_1_BUFFER,72,144
    ld a,38
    ld (test_case),a
    call test_reset_plots
    ld a,W3D_SHELL_MAIN_QUIT
    ld (w3d_shell_main_choice),a
    call w3d_shell_draw_main_menu
    CHECK_MEM8 test_plot_count,3,REASON_PLOT_COUNT
    CHECK_PLOT 6,W3D_SHELL_MAIN_QUIT_SELECTED_BUFFER,100,172
    CHECK_PLOT 12,W3D_SHELL_CURSOR_1_BUFFER,72,170
    ld a,43
    ld (test_case),a
    call test_reset_plots
    ld a,W3D_SHELL_PAUSE_CHOICE_END
    ld (w3d_shell_pause_choice),a
    call w3d_shell_draw_pause_menu
    CHECK_MEM8 test_plot_count,5,REASON_PLOT_COUNT
    CHECK_PLOT 6,W3D_SHELL_MAIN_INGAME_TAIL_BUFFER,96,143
    CHECK_PLOT 12,W3D_SHELL_MAIN_SAVE_GAME_ACTIVE_BUFFER,100,107
    CHECK_PLOT 18,W3D_SHELL_MAIN_END_GAME_SELECTED_BUFFER,100,146
    CHECK_PLOT 24,W3D_SHELL_CURSOR_1_BUFFER,72,144
    ld a,44
    ld (test_case),a
    call test_reset_plots
    ld a,W3D_SHELL_PAUSE_CHOICE_BACK
    ld (w3d_shell_pause_choice),a
    call w3d_shell_draw_pause_menu
    CHECK_MEM8 test_plot_count,5,REASON_PLOT_COUNT
    CHECK_PLOT 6,W3D_SHELL_MAIN_INGAME_TAIL_BUFFER,96,143
    CHECK_PLOT 12,W3D_SHELL_MAIN_SAVE_GAME_ACTIVE_BUFFER,100,107
    CHECK_PLOT 18,W3D_SHELL_MAIN_BACK_TO_GAME_SELECTED_BUFFER,100,159
    CHECK_PLOT 24,W3D_SHELL_CURSOR_1_BUFFER,72,157
    TEST_EPISODE_DRAW 0,W3D_SHELL_EPISODE_1_SELECTED_BUFFER,23,21,28
    TEST_EPISODE_DRAW 1,W3D_SHELL_EPISODE_2_SELECTED_BUFFER,49,47,29
    TEST_EPISODE_DRAW 2,W3D_SHELL_EPISODE_3_SELECTED_BUFFER,75,73,30
    TEST_EPISODE_DRAW 3,W3D_SHELL_EPISODE_4_SELECTED_BUFFER,101,99,31
    TEST_EPISODE_DRAW 4,W3D_SHELL_EPISODE_5_SELECTED_BUFFER,127,125,32
    TEST_EPISODE_DRAW 5,W3D_SHELL_EPISODE_6_SELECTED_BUFFER,153,151,33
    TEST_DIFFICULTY_DRAW 0,W3D_SHELL_DIFFICULTY_BABY_SELECTED_BUFFER,100,98,W3D_SHELL_DIFFICULTY_BABY_BUFFER,34
    TEST_DIFFICULTY_DRAW 1,W3D_SHELL_DIFFICULTY_EASY_SELECTED_BUFFER,113,111,W3D_SHELL_DIFFICULTY_EASY_BUFFER,35
    TEST_DIFFICULTY_DRAW 2,W3D_SHELL_DIFFICULTY_NORMAL_SELECTED_BUFFER,126,124,W3D_SHELL_DIFFICULTY_NORMAL_BUFFER,36
    TEST_DIFFICULTY_DRAW 3,W3D_SHELL_DIFFICULTY_HARD_SELECTED_BUFFER,139,137,W3D_SHELL_DIFFICULTY_HARD_BUFFER,37
    ret

test_set_script:
    ld (test_script_pointer),hl
    ret

test_set_key_script:
    ld (test_key_script_pointer),hl
    ret

test_key_hook:
    ld hl,(test_key_script_pointer)
    ld a,(hl)
    inc hl
    ld (test_key_script_pointer),hl
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
    cp SCRIPT_ESCAPE_ACCEPT
    jr z,@escape_accept
    cp SCRIPT_TICK
    jr z,@tick
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
@escape_accept:
    ld a,00000001b
    ld (test_keymap+14),a
    ld a,00000010b
    ld (test_keymap+9),a
    jr @done
@any:
    ld a,1
    ld (test_keymap+1),a
    jr @done
@tick:
    ld hl,(test_sysvars+sysvar_time)
    ld de,2000
    add hl,de
    ld (test_sysvars+sysvar_time),hl
@done:
    ld ix,test_keymap
    ret

selectBitmap:
    ld a,l
    ld (test_selected_bitmap+0),a
    ld a,h
    ld (test_selected_bitmap+1),a
    push bc
    push de
    push hl
    ld a,(test_select_count)
    cp 16
    jr nc,@history_done
    ld e,a
    ld d,2
    mlt de
    inc de
    dec.s de
    ld hl,test_select_history
    add hl,de
    ld a,(test_selected_bitmap+0)
    ld (hl),a
    inc hl
    ld a,(test_selected_bitmap+1)
    ld (hl),a
    ld hl,test_select_count
    inc (hl)
@history_done:
    pop hl
    pop de
    pop bc
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
    ld (test_select_count),a
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
test_key_script_pointer: dl 0
test_keymap: ds 16
test_selected_bitmap: dw 0
test_select_count: db 0
test_select_history: ds 16*2
test_plot_x: dw 0
test_plot_y: dw 0
test_plot_count: db 0
test_notice_plots: db 0
test_version_prints: db 0
test_victory_present_count: db 0
test_highscore_handoff_count: db 0
test_highscore_view_count: db 0
test_highscore_draw_count: db 0
test_save_load_count: db 0
test_save_store_count: db 0
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
result_stage: db 0
result_done: db 0
    db 0,0,0,0
result_end:

script_action_up: db SCRIPT_UP,SCRIPT_RELEASE
script_action_down: db SCRIPT_DOWN,SCRIPT_RELEASE
script_action_return: db SCRIPT_RETURN,SCRIPT_RELEASE
script_action_keypad: db SCRIPT_KEYPAD,SCRIPT_RELEASE
script_action_space: db SCRIPT_SPACE,SCRIPT_RELEASE
script_action_escape: db SCRIPT_ESCAPE,SCRIPT_RELEASE
script_action_escape_accept: db SCRIPT_ESCAPE_ACCEPT,SCRIPT_RELEASE
script_wait_any_ordinary: db SCRIPT_RELEASE,SCRIPT_ANY,SCRIPT_RELEASE
script_wait_any_escape: db SCRIPT_RELEASE,SCRIPT_ESCAPE,SCRIPT_RELEASE
script_wait_any_held_escape: db SCRIPT_ESCAPE,SCRIPT_RELEASE
script_wait_any_held_ordinary_then_escape:
    db SCRIPT_ANY,SCRIPT_RELEASE,SCRIPT_ESCAPE,SCRIPT_RELEASE
script_main_quit:
    db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_DOWN,SCRIPT_RELEASE
    db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_DOWN,SCRIPT_RELEASE
    db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_DOWN,SCRIPT_RELEASE
    db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_DOWN,SCRIPT_RELEASE
    db SCRIPT_SPACE,SCRIPT_RELEASE
script_main_view_scores:
    db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_DOWN,SCRIPT_RELEASE
    db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_DOWN,SCRIPT_RELEASE
    db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_DOWN,SCRIPT_RELEASE
    db SCRIPT_SPACE,SCRIPT_RELEASE
    db SCRIPT_ESCAPE,SCRIPT_RELEASE
script_main_load_game:
    db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_DOWN,SCRIPT_RELEASE
    db SCRIPT_DOWN,SCRIPT_RELEASE
    db SCRIPT_SPACE,SCRIPT_RELEASE
    db SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
script_pause_escape:
    db SCRIPT_RELEASE,SCRIPT_ESCAPE,SCRIPT_RELEASE
script_pause_end:
    db SCRIPT_RELEASE,SCRIPT_UP,SCRIPT_RELEASE
    db SCRIPT_RETURN,SCRIPT_RELEASE
script_pause_end_then_back:
    db SCRIPT_RELEASE,SCRIPT_UP,SCRIPT_RELEASE
    db SCRIPT_RETURN,SCRIPT_RELEASE
    db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
script_confirm_yes: db 'Y'
script_confirm_no: db 'n'
script_confirm_escape: db 27
script_pause_quit:
    db SCRIPT_RELEASE,SCRIPT_DOWN,SCRIPT_RELEASE
    db SCRIPT_RETURN,SCRIPT_RELEASE
script_pause_accept_back:
    db SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
script_pause_new_game:
    db SCRIPT_RELEASE,SCRIPT_DOWN,SCRIPT_RELEASE
    db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
    db SCRIPT_RETURN,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
script_sound_toggle_return:
    db SCRIPT_RETURN,SCRIPT_RELEASE,SCRIPT_ESCAPE,SCRIPT_RELEASE
script_local_escape:
    db SCRIPT_ESCAPE,SCRIPT_RELEASE
script_main_escape: db SCRIPT_ESCAPE,SCRIPT_RELEASE
script_new_game_medium:
    db SCRIPT_RETURN,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
    db SCRIPT_RETURN,SCRIPT_RELEASE
script_episode_locked_wrap:
    db SCRIPT_UP,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
    db SCRIPT_RELEASE,SCRIPT_ANY,SCRIPT_RELEASE
    db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
script_episode_escape: db SCRIPT_ESCAPE,SCRIPT_RELEASE
script_episode_unavailable_escape:
    db SCRIPT_UP,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
    db SCRIPT_ESCAPE,SCRIPT_RELEASE
script_main_episode_escape:
    db SCRIPT_RETURN,SCRIPT_RELEASE,SCRIPT_ESCAPE,SCRIPT_RELEASE
script_difficulty_medium: db SCRIPT_RETURN,SCRIPT_RELEASE
script_difficulty_hard: db SCRIPT_DOWN,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
script_difficulty_easy: db SCRIPT_UP,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
script_difficulty_baby:
    db SCRIPT_UP,SCRIPT_RELEASE,SCRIPT_UP,SCRIPT_RELEASE
    db SCRIPT_RETURN,SCRIPT_RELEASE
script_difficulty_escape: db SCRIPT_ESCAPE,SCRIPT_RELEASE
script_main_difficulty_escape:
    db SCRIPT_RETURN,SCRIPT_RELEASE,SCRIPT_RETURN,SCRIPT_RELEASE
    db SCRIPT_ESCAPE,SCRIPT_RELEASE
script_title_escape:
    db SCRIPT_RELEASE,SCRIPT_ESCAPE,SCRIPT_RELEASE
    db SCRIPT_ESCAPE,SCRIPT_RELEASE
script_victory_escape:
    db SCRIPT_ESCAPE,SCRIPT_RELEASE
script_ack_then_escape:
    db SCRIPT_RELEASE,SCRIPT_ANY,SCRIPT_RELEASE,SCRIPT_ESCAPE,SCRIPT_RELEASE
script_attract_cycle:
    db SCRIPT_RELEASE,SCRIPT_TICK,SCRIPT_RELEASE
    db SCRIPT_TICK,SCRIPT_RELEASE,SCRIPT_TICK,SCRIPT_RELEASE
    db SCRIPT_ANY,SCRIPT_RELEASE

test_sysvars:
    ds 24
