; =============================================================================
; Original-facing Wolf3D shareware application shell.
;
; Rendering is deliberately kept behind small draw routines.  Input/state
; semantics can therefore be exercised directly on a real eZ80 without the
; VDP or MOS keyboard scanner.  The default keyboard hook calls mos_getkbmap;
; a regression may install a deterministic replacement which returns IX -> a
; sixteen-byte MOS key bitmap.
; =============================================================================

W3D_SHELL_RESULT_QUIT:       equ 0
W3D_SHELL_RESULT_NEW_GAME:   equ 1
W3D_SHELL_RESULT_LOAD_GAME:  equ 2
W3D_SHELL_RESULT_DEMO:       equ 3
W3D_SHELL_PAUSE_QUIT:        equ 0
W3D_SHELL_PAUSE_RESUME:      equ 1
W3D_SHELL_PAUSE_END_GAME:    equ 2
W3D_SHELL_PAUSE_LOAD_GAME:   equ 3
W3D_SHELL_PAUSE_NEW_GAME:    equ 4

W3D_SHELL_ACTION_NONE:       equ 0
W3D_SHELL_ACTION_UP:         equ 1
W3D_SHELL_ACTION_DOWN:       equ 2
W3D_SHELL_ACTION_ACCEPT:     equ 3
W3D_SHELL_ACTION_ESCAPE:     equ 4

; Preserve the exact WL_MENU MainItems order. The startup panel skips only
; Save Game (there is no live game); the in-game panel activates every row and
; substitutes End Game and Back to Game at the original indices.
W3D_SHELL_MAIN_NEW_GAME:     equ 0
W3D_SHELL_MAIN_SOUND:        equ 1
W3D_SHELL_MAIN_CONTROL:      equ 2
W3D_SHELL_MAIN_LOAD_GAME:    equ 3
W3D_SHELL_MAIN_SAVE_GAME:    equ 4
W3D_SHELL_MAIN_CHANGE_VIEW:  equ 5
W3D_SHELL_MAIN_READ_THIS:    equ 6
W3D_SHELL_MAIN_VIEW_SCORES:  equ 7
W3D_SHELL_MAIN_BACK_DEMO:    equ 8
W3D_SHELL_MAIN_QUIT:         equ 9
W3D_SHELL_MAIN_CHOICES:      equ 10
W3D_SHELL_PAUSE_CHOICE_LOAD: equ W3D_SHELL_MAIN_LOAD_GAME
W3D_SHELL_PAUSE_CHOICE_SAVE: equ W3D_SHELL_MAIN_SAVE_GAME
W3D_SHELL_PAUSE_CHOICE_END:  equ W3D_SHELL_MAIN_VIEW_SCORES
W3D_SHELL_PAUSE_CHOICE_BACK: equ W3D_SHELL_MAIN_BACK_DEMO
W3D_SHELL_PAUSE_CHOICE_QUIT: equ W3D_SHELL_MAIN_QUIT
W3D_SHELL_PAUSE_CHOICES:     equ W3D_SHELL_MAIN_CHOICES
W3D_SHELL_EPISODE_CHOICES:   equ 6
W3D_SHELL_DIFFICULTY_CHOICES: equ 4
W3D_SHELL_DIFFICULTY_MEDIUM: equ 2
W3D_SHELL_SAVE_SLOT_COUNT:   equ 10
W3D_SHELL_SAVE_NAME_SIZE:    equ 32
W3D_SHELL_SAVE_NAME_MAX:     equ 31
W3D_SHELL_TITLE_TICKS:       equ 15*120
W3D_SHELL_CREDITS_TICKS:     equ 10*120
W3D_SHELL_SCORES_TICKS:      equ 10*120

; Original WL_MENU.H anchors. Selected-entry overlays contain text only; the
; original cursor and difficulty portrait are plotted independently below.
W3D_SHELL_MAIN_OVERLAY_X:       equ 100
W3D_SHELL_MAIN_NEW_GAME_Y:      equ 55
W3D_SHELL_MAIN_CURSOR_X:        equ 72
W3D_SHELL_MAIN_CURSOR_Y:        equ 53
W3D_SHELL_PAUSE_LOAD_Y:          equ 94
W3D_SHELL_PAUSE_SAVE_Y:          equ 107
W3D_SHELL_PAUSE_END_Y:           equ 146
W3D_SHELL_PAUSE_BACK_Y:          equ 159
W3D_SHELL_PAUSE_QUIT_Y:          equ 172
W3D_SHELL_PAUSE_LOAD_CURSOR_Y:   equ 92
W3D_SHELL_PAUSE_SAVE_CURSOR_Y:   equ 105
W3D_SHELL_PAUSE_END_CURSOR_Y:    equ 144
W3D_SHELL_PAUSE_BACK_CURSOR_Y:   equ 157
W3D_SHELL_PAUSE_QUIT_CURSOR_Y:   equ 170
W3D_SHELL_EPISODE_OVERLAY_X:    equ 98
W3D_SHELL_EPISODE_OVERLAY_Y:    equ 23
W3D_SHELL_EPISODE_ROW_HEIGHT:   equ 26
W3D_SHELL_EPISODE_CURSOR_X:     equ 8
W3D_SHELL_EPISODE_CURSOR_Y:     equ 21
W3D_SHELL_DIFFICULTY_OVERLAY_X: equ 74
W3D_SHELL_DIFFICULTY_OVERLAY_Y: equ 100
W3D_SHELL_DIFFICULTY_ROW_HEIGHT: equ 13
W3D_SHELL_DIFFICULTY_CURSOR_X:  equ 48
W3D_SHELL_DIFFICULTY_CURSOR_Y:  equ 98
W3D_SHELL_DIFFICULTY_PORTRAIT_X: equ 235
W3D_SHELL_DIFFICULTY_PORTRAIT_Y: equ 107

w3d_shell_setup:
    ld hl,@commands
    ld bc,@end-@commands
    rst.lil 18h
    ret
@commands:
    db 22,8                 ; 320x240x64, single buffered
    db 23,0,0c0h,0          ; native logical coordinates
    db 23,1,0               ; cursor hidden
    db 18,0,128             ; black graphics background
    db 12                   ; clear text surface
    db 16                   ; clear graphics surface
@end:

; Explicit future extension point.  TODO 3b will fill this without changing
; the accepted original-facing startup flow.
w3d_shell_show_agon_splash:
    ret

; Initial application entry: setup -> reserved Agon hook -> source-timed
; original attract pages -> control panel. Returns W3D_SHELL_RESULT_* in A.
w3d_shell_run:
    call w3d_shell_reset_exit_request
    call w3d_shell_setup
    call w3d_shell_show_agon_splash
    call w3d_shell_attract_until_input
    cp W3D_SHELL_RESULT_DEMO
    ret z
    jp w3d_shell_main_menu

w3d_shell_resume_after_demo:
    call w3d_shell_setup
    call w3d_shell_attract_until_input
    cp W3D_SHELL_RESULT_DEMO
    ret z
    jp w3d_shell_main_menu

; Present the original Episode 1 Victory()/ENDART1 lifecycle, run the exact
; CheckHighScore(score,mapon+1) handoff, then resume the same main-menu flow.
w3d_shell_resume_after_victory:
    call w3d_shell_query_exit_request
    jp nz,w3d_shell_return_quit
    call w3d_shell_setup
    ld a,W3D_MUSIC_URAHERO
    call w3d_music_start
    call w3d_victory_present
    call w3d_shell_query_exit_request
    jp nz,w3d_shell_return_quit
    ld a,W3D_MUSIC_ROSTER
    call w3d_music_start
    call w3d_highscores_handle_game_end
    call w3d_shell_query_exit_request
    jp nz,w3d_shell_return_quit
    jp w3d_shell_main_menu

; Game over omits Victory()/ENDART1 but otherwise uses the same original
; CheckHighScore(score,mapon+1) -> control-panel handoff.
w3d_shell_resume_after_game_over:
    call w3d_shell_query_exit_request
    jp nz,w3d_shell_return_quit
    call w3d_shell_setup
    ld a,W3D_MUSIC_ROSTER
    call w3d_music_start
    call w3d_highscores_handle_game_end
    call w3d_shell_query_exit_request
    jp nz,w3d_shell_return_quit
    jp w3d_shell_main_menu

w3d_shell_show_title:
    call w3d_shell_query_exit_request
    jp nz,w3d_shell_return_quit
    call w3d_shell_draw_title
    call w3d_shell_wait_any_press
    call w3d_shell_query_exit_request
    jp nz,w3d_shell_return_quit
    ld a,W3D_SHELL_RESULT_NEW_GAME
    or a
    ret

w3d_shell_draw_title:
    call w3d_shell_clear
    ld hl,W3D_SHELL_TITLE_BUFFER
    call selectBitmap
    ld bc,0
    ld de,0
    call plotBitmap
    ld hl,@version_position
    call printString
    ld hl,w3d_app_version_text
    call printString
    ret
@version_position:
    db 17,15,31,8,26,0

; -----------------------------------------------------------------------------
; Main menu
; -----------------------------------------------------------------------------

w3d_shell_main_menu:
    call w3d_shell_query_exit_request
    jp nz,w3d_shell_return_quit
    ld a,W3D_MUSIC_WONDERIN
    call w3d_music_start
    ld a,W3D_SHELL_MAIN_NEW_GAME
    ld (w3d_shell_main_choice),a
@redraw:
    call w3d_shell_draw_main_menu
@wait:
    call w3d_shell_wait_action
    cp W3D_SHELL_ACTION_UP
    jr z,@move
    cp W3D_SHELL_ACTION_DOWN
    jr z,@move
    cp W3D_SHELL_ACTION_ACCEPT
    jr z,@accept
    cp W3D_SHELL_ACTION_ESCAPE
    jp z,@quit
    jr @wait
@move:
    cp W3D_SHELL_ACTION_UP
    jr z,@up
@down:
    ld a,(w3d_shell_main_choice)
    inc a
    cp W3D_SHELL_MAIN_CHOICES
    jr c,@down_active
    xor a
@down_active:
    cp W3D_SHELL_MAIN_SAVE_GAME
    jr nz,@store_move
    inc a                         ; Save is disabled before gameplay
    jr @store_move
@up:
    ld a,(w3d_shell_main_choice)
    or a
    jr nz,@have_up
    ld a,W3D_SHELL_MAIN_CHOICES
@have_up:
    dec a
    cp W3D_SHELL_MAIN_SAVE_GAME
    jr nz,@store_move
    dec a                         ; Save is disabled before gameplay
@store_move:
    ld (w3d_shell_main_choice),a
    jp @redraw
@accept:
    ld a,(w3d_shell_main_choice)
    cp W3D_SHELL_MAIN_QUIT
    jp z,@quit
    cp W3D_SHELL_MAIN_LOAD_GAME
    jp z,@load_game
    cp W3D_SHELL_MAIN_SOUND
    jp z,@sound
    cp W3D_SHELL_MAIN_CONTROL
    jp z,@control
    cp W3D_SHELL_MAIN_CHANGE_VIEW
    jp z,@change_view
    cp W3D_SHELL_MAIN_READ_THIS
    jp z,@read_this
    cp W3D_SHELL_MAIN_BACK_DEMO
    jp z,@back_to_demo
    cp W3D_SHELL_MAIN_VIEW_SCORES
    jr nz,@new_game
    ld a,W3D_MUSIC_ROSTER
    call w3d_music_start
    call w3d_highscores_view
    call w3d_shell_query_exit_request
    jp nz,@quit
    ld a,W3D_MUSIC_WONDERIN
    call w3d_music_start
    jp @redraw
@new_game:
    call w3d_shell_choose_episode
    jp z,@quit
@difficulty:
    call w3d_shell_choose_difficulty
    jp z,@quit
    ld a,W3D_SHELL_RESULT_NEW_GAME
    or a                    ; caller may branch on NZ
    ret
@sound:
    call w3d_shell_sound_page
    jp @redraw
@control:
    ld hl,W3D_SHELL_CONTROL_PAGE_BUFFER
    call w3d_shell_information_page
    jp @redraw
@change_view:
    ld hl,W3D_SHELL_CHANGE_VIEW_PAGE_BUFFER
    call w3d_shell_information_page
    jp @redraw
@read_this:
    ld a,W3D_MUSIC_CORNER
    call w3d_music_start
    ld hl,W3D_SHELL_READ_THIS_PAGE_BUFFER
    call w3d_shell_information_page
    ld a,W3D_MUSIC_WONDERIN
    call w3d_music_start
    jp @redraw
@back_to_demo:
    call w3d_shell_attract_until_input
    cp W3D_SHELL_RESULT_DEMO
    ret z
    ld a,W3D_MUSIC_WONDERIN
    call w3d_music_start
    jp @redraw
@load_game:
    xor a                   ; load screen, shell/global context
    ld b,a
    call w3d_shell_save_load_menu
    or a
    jp z,@redraw
    ld a,W3D_SHELL_RESULT_LOAD_GAME
    or a
    ret
@quit:
    jp w3d_shell_return_quit

w3d_shell_draw_main_menu:
    call w3d_shell_clear
    ld hl,W3D_SHELL_MAIN_BASE_BUFFER
    call w3d_shell_plot_full_screen
    ld a,(w3d_shell_main_choice)
    ld hl,w3d_shell_main_selected_buffers
    jp w3d_shell_draw_menu_selection

; -----------------------------------------------------------------------------
; In-game control panel. The original replaces View Scores with End Game and
; Back to Demo with Back to Game. Escape is synonymous with Back to Game and
; deliberately does not set the application-global quit latch.
; -----------------------------------------------------------------------------

w3d_shell_pause_menu:
    ld a,W3D_SHELL_PAUSE_CHOICE_BACK
    ld (w3d_shell_pause_choice),a
    call w3d_shell_pause_wait_all_released
@redraw:
    call w3d_shell_draw_pause_menu
@wait:
    call w3d_shell_wait_pause_action
    cp W3D_SHELL_ACTION_ESCAPE
    jp z,@resume
    cp W3D_SHELL_ACTION_UP
    jp z,@up
    cp W3D_SHELL_ACTION_DOWN
    jp z,@down
    cp W3D_SHELL_ACTION_ACCEPT
    jr nz,@wait
    ld a,(w3d_shell_pause_choice)
    or a
    jp z,@new_game
    cp W3D_SHELL_PAUSE_CHOICE_LOAD
    jp z,@load_game
    cp W3D_SHELL_PAUSE_CHOICE_SAVE
    jp z,@save_game
    cp W3D_SHELL_PAUSE_CHOICE_BACK
    jp z,@resume
    cp W3D_SHELL_PAUSE_CHOICE_END
    jp z,@end_game
    cp W3D_SHELL_MAIN_SOUND
    jp z,@sound
    cp W3D_SHELL_MAIN_CONTROL
    jp z,@control
    cp W3D_SHELL_MAIN_CHANGE_VIEW
    jp z,@change_view
    cp W3D_SHELL_MAIN_READ_THIS
    jp z,@read_this
    call w3d_shell_request_exit
    ld a,W3D_SHELL_PAUSE_QUIT
    or a
    ret
@new_game:
    call w3d_shell_choose_episode_local
    jp z,@redraw
    call w3d_shell_choose_difficulty_local
    jp z,@redraw
    ld a,W3D_SHELL_PAUSE_NEW_GAME
    or a
    ret
@sound:
    call w3d_shell_sound_page
    jp @redraw
@control:
    ld hl,W3D_SHELL_CONTROL_PAGE_BUFFER
    call w3d_shell_information_page
    jp @redraw
@change_view:
    ld hl,W3D_SHELL_CHANGE_VIEW_PAGE_BUFFER
    call w3d_shell_information_page
    jp @redraw
@read_this:
    ld hl,W3D_SHELL_READ_THIS_PAGE_BUFFER
    call w3d_shell_information_page
    jp @redraw
@up:
    ld a,(w3d_shell_pause_choice)
    or a
    jr nz,@have_up
    ld a,W3D_SHELL_PAUSE_CHOICES
@have_up:
    dec a
    ld (w3d_shell_pause_choice),a
    jp @redraw
@down:
    ld a,(w3d_shell_pause_choice)
    inc a
    cp W3D_SHELL_PAUSE_CHOICES
    jr c,@store_down
    xor a
@store_down:
    ld (w3d_shell_pause_choice),a
    jp @redraw
@resume:
    ld a,W3D_SHELL_PAUSE_RESUME
    or a
    ret
@end_game:
    call w3d_shell_confirm_end_game
    or a
    jp z,@redraw
    ld a,W3D_SHELL_PAUSE_END_GAME
    or a
    ret
@load_game:
    xor a                   ; load screen
    ld b,1                  ; in-game context
    call w3d_shell_save_load_menu
    or a
    jp z,@redraw
    ld a,W3D_SHELL_PAUSE_LOAD_GAME
    or a
    ret
@save_game:
    ld a,1                  ; save screen
    ld b,1                  ; in-game context
    call w3d_shell_save_load_menu
    jp @redraw

; Original CP_EndGame -> Confirm(ENDGAMESTR).  Y accepts; N or Escape cancels
; and returns to the in-game panel without setting the application exit latch.
w3d_shell_confirm_end_game:
    ld hl,W3D_SHELL_END_GAME_NOTICE_BUFFER
    ld bc,W3D_SHELL_END_GAME_NOTICE_X
    ld de,W3D_SHELL_END_GAME_NOTICE_Y
    call w3d_shell_plot_at
@wait:
    call w3d_shell_read_key
    cp 'Y'
    jr z,@yes
    cp 'y'
    jr z,@yes
    cp 'N'
    jr z,@no
    cp 'n'
    jr z,@no
    cp 27
    jr nz,@wait
@no:
    xor a
    ret
@yes:
    ld a,1
    or a
    ret

w3d_shell_draw_pause_menu:
    call w3d_shell_clear
    ld hl,W3D_SHELL_MAIN_BASE_BUFFER
    call w3d_shell_plot_full_screen
    ld hl,W3D_SHELL_MAIN_INGAME_TAIL_BUFFER
    ld bc,96
    ld de,143
    call w3d_shell_plot_at
    ld hl,W3D_SHELL_MAIN_SAVE_GAME_ACTIVE_BUFFER
    ld bc,W3D_SHELL_MAIN_OVERLAY_X
    ld de,W3D_SHELL_PAUSE_SAVE_Y
    call w3d_shell_plot_at
    ld a,(w3d_shell_pause_choice)
    ld hl,w3d_shell_pause_selected_buffers
    jp w3d_shell_draw_menu_selection

; A=choice (0..9), HL=table of ten 24-bit selected-overlay buffer ids.
w3d_shell_draw_menu_selection:
    push af
    push ix
    push hl
    pop ix
    ld b,a
@seek_buffer:
    ld a,b
    or a
    jr z,@read_buffer
    lea ix,ix+3
    djnz @seek_buffer
@read_buffer:
    ld l,(ix+0)
    ld h,(ix+1)
    inc hl
    dec.s hl                 ; zero HLU for intentionally 16-bit ids
    pop ix
    pop af
    push af                  ; retain row for cursor placement
    push hl                  ; retain overlay while deriving row y
    ld d,a
    ld e,13
    mlt de
    ld hl,W3D_SHELL_MAIN_NEW_GAME_Y
    add.s hl,de
    ex de,hl
    pop hl
    ld bc,W3D_SHELL_MAIN_OVERLAY_X
    call w3d_shell_plot_at
    pop af
    ld d,a
    ld e,13
    mlt de
    ld hl,W3D_SHELL_MAIN_CURSOR_Y
    add.s hl,de
    ex de,hl
    ld hl,W3D_SHELL_CURSOR_1_BUFFER
    ld bc,W3D_SHELL_MAIN_CURSOR_X
    jp w3d_shell_plot_at

w3d_shell_main_selected_buffers:
    dl W3D_SHELL_MAIN_NEW_GAME_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_SOUND_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_CONTROL_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_LOAD_GAME_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_SAVE_GAME_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_CHANGE_VIEW_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_READ_THIS_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_VIEW_SCORES_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_BACK_TO_DEMO_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_QUIT_SELECTED_BUFFER

w3d_shell_pause_selected_buffers:
    dl W3D_SHELL_MAIN_NEW_GAME_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_SOUND_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_CONTROL_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_LOAD_GAME_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_SAVE_GAME_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_CHANGE_VIEW_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_READ_THIS_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_END_GAME_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_BACK_TO_GAME_SELECTED_BUFFER
    dl W3D_SHELL_MAIN_QUIT_SELECTED_BUFFER

; Shared translated control-panel pages. These waits are always local: Escape
; closes the page rather than quitting either the game or application.
w3d_shell_sound_page:
    xor a
    ld (w3d_shell_sound_choice),a
@redraw:
    call w3d_shell_clear
    ld a,(w3d_music_enabled)
    or a
    jr z,@music_off
    ld a,(w3d_audio_sfx_enabled)
    or a
    ld hl,W3D_SHELL_SOUND_OFF_PAGE_BUFFER
    jr z,@draw
    ld hl,W3D_SHELL_SOUND_ON_PAGE_BUFFER
    jr @draw
@music_off:
    ld a,(w3d_audio_sfx_enabled)
    or a
    ld hl,W3D_SHELL_SOUND_OFF_MUSIC_OFF_PAGE_BUFFER
    jr z,@draw
    ld hl,W3D_SHELL_SOUND_ON_MUSIC_OFF_PAGE_BUFFER
@draw:
    call w3d_shell_plot_full_screen
    ld a,(w3d_shell_sound_choice)
    or a
    ld de,54
    jr z,@cursor
    ld de,74
@cursor:
    ld hl,W3D_SHELL_CURSOR_1_BUFFER
    ld bc,42
    call w3d_shell_plot_at
@wait:
    call w3d_shell_wait_pause_action
    cp W3D_SHELL_ACTION_ESCAPE
    ret z
    cp W3D_SHELL_ACTION_ACCEPT
    jr z,@toggle
    cp W3D_SHELL_ACTION_UP
    jr z,@move
    cp W3D_SHELL_ACTION_DOWN
    jr nz,@wait
@move:
    ld a,(w3d_shell_sound_choice)
    xor 1
    ld (w3d_shell_sound_choice),a
    jp @redraw
@toggle:
    ld a,(w3d_shell_sound_choice)
    or a
    jr nz,@toggle_music
    ld a,(w3d_audio_sfx_enabled)
    xor 1
    ld (w3d_audio_sfx_enabled),a
    jp @redraw
@toggle_music:
    ld a,(w3d_music_enabled)
    xor 1
    push af
    call w3d_music_set_enabled
    pop af
    or a
    jp z,@redraw
    ld a,W3D_MUSIC_WONDERIN
    call w3d_music_start
    jp @redraw

; HL=full-screen page buffer. Return on local Escape or Accept.
w3d_shell_information_page:
    push hl
    call w3d_shell_clear
    pop hl
    call w3d_shell_plot_full_screen
@wait:
    call w3d_shell_wait_pause_action
    cp W3D_SHELL_ACTION_ESCAPE
    ret z
    cp W3D_SHELL_ACTION_ACCEPT
    jr nz,@wait
    ret

; Original DemoLoop timings at the MOS 120-Hz clock. After the three pages,
; select the next canonical recorded stream and return it to the application.
; Any key enters the control panel without promoting Escape to application
; exit, matching IN_UserInput's attract-loop role.
w3d_shell_attract_until_input:
@title:
    ld a,W3D_MUSIC_NAZI_NOR
    call w3d_music_start
    call w3d_shell_draw_title
    ld de,W3D_SHELL_TITLE_TICKS
    call w3d_shell_wait_input_timeout
    ret nz
    call w3d_shell_clear
    ld hl,W3D_SHELL_CREDITS_BUFFER
    call w3d_shell_plot_full_screen
    ld de,W3D_SHELL_CREDITS_TICKS
    call w3d_shell_wait_input_timeout
    ret nz
    ld a,W3D_MUSIC_ROSTER
    call w3d_music_start
    call w3d_highscores_draw
    ld de,W3D_SHELL_SCORES_TICKS
    call w3d_shell_wait_input_timeout
    ret nz
    call w3d_demo_prepare_next
    ld a,W3D_SHELL_RESULT_DEMO
    or a
    ret

; DE=duration in MOS 120-Hz ticks. Returns A=1/NZ after any key and A=0/Z on
; timeout. The caller's duration is copied before DE becomes elapsed scratch.
w3d_shell_wait_input_timeout:
    ld (w3d_shell_timeout_ticks),de
    call w3d_shell_pause_wait_all_released
    ld ix,(w3d_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld (w3d_shell_timeout_started),hl
@wait:
    call w3d_shell_read_keyboard
    ld b,16
@scan:
    ld a,(ix)
    or a
    jr nz,@pressed
    inc ix
    djnz @scan
    ld ix,(w3d_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld de,(w3d_shell_timeout_started)
    or a
    sbc hl,de
    ld de,(w3d_shell_timeout_ticks)
    or a
    sbc hl,de
    jr c,@wait
    xor a
    ret
@pressed:
    call w3d_shell_pause_wait_all_released
    ld a,1
    or a
    ret

; -----------------------------------------------------------------------------
; Original ten-slot load/save panel. A=0 load / 1 save, B=0 startup shell /
; 1 in-game panel. Return A=1 only after a valid load has been staged or a
; save has been written; Escape/cancel returns zero without touching the
; application-global exit latch.
; -----------------------------------------------------------------------------

w3d_shell_save_load_menu:
    ld (w3d_shell_slot_mode),a
    ld a,b
    ld (w3d_shell_slot_context),a
    xor a
    ld (w3d_shell_slot_choice),a
    call w3d_shell_pause_wait_all_released
@redraw:
    call w3d_shell_draw_save_load_menu
@wait:
    call w3d_shell_wait_pause_action
    cp W3D_SHELL_ACTION_ESCAPE
    jp z,@cancel
    cp W3D_SHELL_ACTION_UP
    jp z,@up
    cp W3D_SHELL_ACTION_DOWN
    jp z,@down
    cp W3D_SHELL_ACTION_ACCEPT
    jr nz,@wait
    ld a,(w3d_shell_slot_mode)
    or a
    jr nz,@save
    ld a,(w3d_shell_slot_choice)
    call w3d_shell_slot_is_available
    jr z,@wait
    ld a,(w3d_shell_slot_choice)
    call w3d_save_slot_load
    jr c,@io_error
    ld a,1
    or a
    ret
@save:
    ld a,(w3d_shell_slot_choice)
    call w3d_shell_slot_is_available
    jr z,@edit
    call w3d_shell_confirm_save_overwrite
    or a
    jp z,@redraw
@edit:
    call w3d_shell_edit_save_name
    or a
    jp z,@redraw
    ld a,(w3d_shell_slot_choice)
    ld hl,w3d_shell_slot_name_edit
    call w3d_save_slot_store
    jr c,@io_error
    ld a,1
    or a
    ret
@io_error:
    call w3d_shell_draw_slot_io_error
    call w3d_shell_wait_any_local_press
    jp @redraw
@up:
    ld a,(w3d_shell_slot_choice)
    or a
    jr nz,@up_have
    ld a,W3D_SHELL_SAVE_SLOT_COUNT
@up_have:
    dec a
    ld (w3d_shell_slot_choice),a
    jp @redraw
@down:
    ld a,(w3d_shell_slot_choice)
    inc a
    cp W3D_SHELL_SAVE_SLOT_COUNT
    jr c,@down_have
    xor a
@down_have:
    ld (w3d_shell_slot_choice),a
    jp @redraw
@cancel:
    xor a
    ret

; A=slot, return A=0/Z for empty or 1/NZ for a validated cached slot.
w3d_shell_slot_is_available:
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_save_slot_available
    add hl,de
    ld a,(hl)
    or a
    ret

w3d_shell_draw_save_load_menu:
    call w3d_shell_clear
    ld a,(w3d_shell_slot_mode)
    or a
    ld hl,W3D_SHELL_LOAD_GAME_HEADING_BUFFER
    jr z,@heading
    ld hl,W3D_SHELL_SAVE_GAME_HEADING_BUFFER
@heading:
    ld bc,60
    ld de,0
    call w3d_shell_plot_at
    ld hl,w3d_shell_slot_text_colours
    ld bc,w3d_shell_slot_text_colours_end-w3d_shell_slot_text_colours
    rst.lil 18h
    xor a
    ld (w3d_shell_slot_draw_index),a
@row:
    ld a,(w3d_shell_slot_draw_index)
    add a,a
    add a,7
    ld c,a
    ld a,11
    call w3d_shell_slot_set_cursor
    ld a,(w3d_shell_slot_draw_index)
    call w3d_shell_slot_is_available
    ld hl,w3d_shell_empty_slot_text
    jr z,@print
    ld a,(w3d_shell_slot_draw_index)
    call w3d_shell_slot_name_pointer
@print:
    call printString
    ld a,(w3d_shell_slot_draw_index)
    inc a
    ld (w3d_shell_slot_draw_index),a
    cp W3D_SHELL_SAVE_SLOT_COUNT
    jr c,@row
    ld a,(w3d_shell_slot_choice)
    ld d,a
    ld e,13
    mlt de
    ld hl,53
    add.s hl,de
    ex de,hl
    ld hl,W3D_SHELL_CURSOR_1_BUFFER
    ld bc,60
    jp w3d_shell_plot_at

; A=slot, return HL -> cached 32-byte terminated name.
w3d_shell_slot_name_pointer:
    ld d,a
    ld e,W3D_SHELL_SAVE_NAME_SIZE
    mlt de
    inc de
    dec.s de
    ld hl,w3d_save_slot_names
    add hl,de
    ret

; A=text column, C=text row.
w3d_shell_slot_set_cursor:
    ld (w3d_shell_slot_cursor+1),a
    ld a,c
    ld (w3d_shell_slot_cursor+2),a
    ld hl,w3d_shell_slot_cursor
    ld bc,3
    rst.lil 18h
    ret

w3d_shell_confirm_save_overwrite:
    ld a,4
    ld c,28
    call w3d_shell_slot_set_cursor
    ld hl,w3d_shell_overwrite_text
    call printString
@wait:
    call w3d_shell_read_key
    cp 'Y'
    jr z,@yes
    cp 'y'
    jr z,@yes
    cp 'N'
    jr z,@no
    cp 'n'
    jr z,@no
    cp 27
    jr nz,@wait
@no:
    xor a
    ret
@yes:
    ld a,1
    or a
    ret

w3d_shell_edit_save_name:
    xor a
    ld (w3d_shell_slot_name_length),a
    ld hl,w3d_shell_slot_name_edit
    ld (hl),a
    ld a,(w3d_shell_slot_choice)
    call w3d_shell_slot_is_available
    jr z,@redraw
    ld a,(w3d_shell_slot_choice)
    call w3d_shell_slot_name_pointer
    ld de,w3d_shell_slot_name_edit
    ld b,W3D_SHELL_SAVE_NAME_MAX
@copy:
    ld a,(hl)
    or a
    jr z,@copied
    ld (de),a
    inc hl
    inc de
    ld a,(w3d_shell_slot_name_length)
    inc a
    ld (w3d_shell_slot_name_length),a
    djnz @copy
@copied:
    xor a
    ld (de),a
@redraw:
    call w3d_shell_draw_save_load_menu
    ld a,(w3d_shell_slot_choice)
    add a,a
    add a,7
    ld c,a
    ld a,11
    call w3d_shell_slot_set_cursor
    ld hl,w3d_shell_slot_clear_name
    call printString
    ld a,(w3d_shell_slot_choice)
    add a,a
    add a,7
    ld c,a
    ld a,11
    call w3d_shell_slot_set_cursor
    ld hl,w3d_shell_slot_name_edit
    call printString
    call w3d_shell_read_key
    cp 27
    jr z,@cancel
    cp 13
    jr z,@accept
    cp 10
    jr z,@accept
    cp 8
    jr z,@backspace
    cp 127
    jr z,@backspace
    cp 32
    jp c,@redraw
    cp 127
    jp nc,@redraw
    ld b,a
    ld a,(w3d_shell_slot_name_length)
    cp W3D_SHELL_SAVE_NAME_MAX
    jp nc,@redraw
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_shell_slot_name_edit
    add hl,de
    ld (hl),b
    inc hl
    ld (hl),0
    ld a,(w3d_shell_slot_name_length)
    inc a
    ld (w3d_shell_slot_name_length),a
    jp @redraw
@backspace:
    ld a,(w3d_shell_slot_name_length)
    or a
    jp z,@redraw
    dec a
    ld (w3d_shell_slot_name_length),a
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_shell_slot_name_edit
    add hl,de
    ld (hl),0
    jp @redraw
@accept:
    ld a,1
    or a
    ret
@cancel:
    xor a
    ret

w3d_shell_draw_slot_io_error:
    ld a,4
    ld c,28
    call w3d_shell_slot_set_cursor
    ld hl,w3d_shell_slot_io_error_text
    jp printString

; Local acknowledgment which deliberately never promotes Escape to the
; application-global quit latch.
w3d_shell_wait_any_local_press:
    call w3d_shell_pause_wait_all_released
@wait:
    call w3d_shell_read_keyboard
    ld b,16
@scan:
    ld a,(ix)
    or a
    jp nz,w3d_shell_pause_wait_all_released
    inc ix
    djnz @scan
    jr @wait

w3d_shell_slot_mode:
    db 0
w3d_shell_slot_context:
    db 0
w3d_shell_slot_choice:
    db 0
w3d_shell_slot_draw_index:
    db 0
w3d_shell_slot_name_length:
    db 0
w3d_shell_slot_name_edit:
    ds W3D_SHELL_SAVE_NAME_SIZE
w3d_shell_slot_cursor:
    db 31,0,0
w3d_shell_slot_text_colours:
    db 17,15
    db 17,128+1
w3d_shell_slot_text_colours_end:
w3d_shell_empty_slot_text:
    db "      - empty -",0
w3d_shell_overwrite_text:
    db "Overwrite this game? (Y or N)",0
w3d_shell_slot_io_error_text:
    db "Save/load failed. Press any key.",0
w3d_shell_slot_clear_name:
    db "                             ",0

; -----------------------------------------------------------------------------
; Shareware episode menu.  All six rows navigate exactly like the original;
; only Episode 1 is available.  Accepting another episode retains selection,
; displays the original-style unavailable notice, and requires acknowledgment.
; Escape requests application-global exit from this or any nested notice.
; -----------------------------------------------------------------------------

w3d_shell_choose_episode:
    xor a
    ld (w3d_shell_choice_local),a
    jr w3d_shell_choose_episode_inner
w3d_shell_choose_episode_local:
    ld a,1
    ld (w3d_shell_choice_local),a
w3d_shell_choose_episode_inner:
    ld a,(w3d_shell_choice_local)
    or a
    jr nz,@begin
    call w3d_shell_query_exit_request
    jp nz,w3d_shell_return_quit
@begin:
    xor a
    ld (w3d_shell_episode_choice),a
@redraw:
    call w3d_shell_draw_episode_menu
@wait:
    call w3d_shell_wait_choice_action
    cp W3D_SHELL_ACTION_UP
    jr z,@up
    cp W3D_SHELL_ACTION_DOWN
    jr z,@down
    cp W3D_SHELL_ACTION_ACCEPT
    jr z,@accept
    cp W3D_SHELL_ACTION_ESCAPE
    jr z,@cancel
    jr @wait
@up:
    ld a,(w3d_shell_episode_choice)
    or a
    jr nz,@up_have
    ld a,W3D_SHELL_EPISODE_CHOICES
@up_have:
    dec a
    ld (w3d_shell_episode_choice),a
    jr @redraw
@down:
    ld a,(w3d_shell_episode_choice)
    inc a
    cp W3D_SHELL_EPISODE_CHOICES
    jr c,@down_have
    xor a
@down_have:
    ld (w3d_shell_episode_choice),a
    jr @redraw
@accept:
    ld a,(w3d_shell_episode_choice)
    or a
    jr z,@accepted
    call w3d_shell_draw_episode_unavailable
    ld a,(w3d_shell_choice_local)
    or a
    jr z,@global_notice
    call w3d_shell_wait_any_local_press
    jr @redraw
@global_notice:
    call w3d_shell_wait_any_press
    call w3d_shell_query_exit_request
    jr nz,@cancel
    jr @redraw
@accepted:
    ld a,1
    or a
    ret
@cancel:
    ld a,(w3d_shell_choice_local)
    or a
    jr z,@global_cancel
    xor a
    ret
@global_cancel:
    jp w3d_shell_return_quit

w3d_shell_draw_episode_menu:
    call w3d_shell_clear
    ld hl,W3D_SHELL_EPISODE_BASE_BUFFER
    call w3d_shell_plot_full_screen
    ld a,(w3d_shell_episode_choice)
    ld e,a
    ld d,0
    ld hl,W3D_SHELL_EPISODE_1_SELECTED_BUFFER
    add.s hl,de
    push hl
    ld d,a
    ld e,W3D_SHELL_EPISODE_ROW_HEIGHT
    mlt de
    ld hl,W3D_SHELL_EPISODE_OVERLAY_Y
    add.s hl,de
    ex de,hl
    pop hl
    ld bc,W3D_SHELL_EPISODE_OVERLAY_X
    call w3d_shell_plot_at
    ld a,(w3d_shell_episode_choice)
    ld d,a
    ld e,W3D_SHELL_EPISODE_ROW_HEIGHT
    mlt de
    ld hl,W3D_SHELL_EPISODE_CURSOR_Y
    add.s hl,de
    ex de,hl
    ld hl,W3D_SHELL_CURSOR_1_BUFFER
    ld bc,W3D_SHELL_EPISODE_CURSOR_X
    jp w3d_shell_plot_at

w3d_shell_draw_episode_unavailable:
    ld hl,W3D_SHELL_EPISODE_UNAVAILABLE_NOTICE_BUFFER
    ld bc,W3D_SHELL_EPISODE_UNAVAILABLE_NOTICE_X
    ld de,W3D_SHELL_EPISODE_UNAVAILABLE_NOTICE_Y
    jp w3d_shell_plot_at

; -----------------------------------------------------------------------------
; Difficulty menu.  Medium is the original default.  Escape requests the same
; application-global exit as it does everywhere else in the shell.
; -----------------------------------------------------------------------------

w3d_shell_choose_difficulty:
    xor a
    ld (w3d_shell_choice_local),a
    jr w3d_shell_choose_difficulty_inner
w3d_shell_choose_difficulty_local:
    ld a,1
    ld (w3d_shell_choice_local),a
w3d_shell_choose_difficulty_inner:
    ld a,(w3d_shell_choice_local)
    or a
    jr nz,@begin
    call w3d_shell_query_exit_request
    jp nz,w3d_shell_return_quit
@begin:
    ld a,W3D_SHELL_DIFFICULTY_MEDIUM
    ld (w3d_shell_difficulty),a
@redraw:
    call w3d_shell_draw_difficulty_menu
@wait:
    call w3d_shell_wait_choice_action
    cp W3D_SHELL_ACTION_UP
    jr z,@up
    cp W3D_SHELL_ACTION_DOWN
    jr z,@down
    cp W3D_SHELL_ACTION_ACCEPT
    jr z,@accept
    cp W3D_SHELL_ACTION_ESCAPE
    jr z,@cancel
    jr @wait
@up:
    ld a,(w3d_shell_difficulty)
    or a
    jr nz,@up_have
    ld a,W3D_SHELL_DIFFICULTY_CHOICES
@up_have:
    dec a
    ld (w3d_shell_difficulty),a
    jr @redraw
@down:
    ld a,(w3d_shell_difficulty)
    inc a
    and W3D_SHELL_DIFFICULTY_CHOICES-1
    ld (w3d_shell_difficulty),a
    jr @redraw
@accept:
    ld a,(w3d_shell_difficulty)
    ld (w3d_requested_difficulty),a
    ld a,1
    or a
    ret
@cancel:
    ld a,(w3d_shell_choice_local)
    or a
    jr z,@global_cancel
    xor a
    ret
@global_cancel:
    jp w3d_shell_return_quit

; Episode/difficulty screens use global Escape during startup but local Escape
; when invoked from the in-game New Game row.
w3d_shell_wait_choice_action:
    ld a,(w3d_shell_choice_local)
    or a
    jp nz,w3d_shell_wait_pause_action
    jp w3d_shell_wait_action

w3d_shell_draw_difficulty_menu:
    call w3d_shell_clear
    ld hl,W3D_SHELL_DIFFICULTY_BASE_BUFFER
    call w3d_shell_plot_full_screen
    ld a,(w3d_shell_difficulty)
    ld e,a
    ld d,0
    ld hl,W3D_SHELL_DIFFICULTY_BABY_SELECTED_BUFFER
    add.s hl,de
    push hl
    ld d,a
    ld e,W3D_SHELL_DIFFICULTY_ROW_HEIGHT
    mlt de
    ld hl,W3D_SHELL_DIFFICULTY_OVERLAY_Y
    add.s hl,de
    ex de,hl
    pop hl
    ld bc,W3D_SHELL_DIFFICULTY_OVERLAY_X
    call w3d_shell_plot_at
    ld a,(w3d_shell_difficulty)
    ld d,a
    ld e,W3D_SHELL_DIFFICULTY_ROW_HEIGHT
    mlt de
    ld hl,W3D_SHELL_DIFFICULTY_CURSOR_Y
    add.s hl,de
    ex de,hl
    ld hl,W3D_SHELL_CURSOR_1_BUFFER
    ld bc,W3D_SHELL_DIFFICULTY_CURSOR_X
    call w3d_shell_plot_at
    ld a,(w3d_shell_difficulty)
    ld e,a
    ld d,0
    ld hl,W3D_SHELL_DIFFICULTY_BABY_BUFFER
    add.s hl,de
    ld bc,W3D_SHELL_DIFFICULTY_PORTRAIT_X
    ld de,W3D_SHELL_DIFFICULTY_PORTRAIT_Y
    jp w3d_shell_plot_at

; -----------------------------------------------------------------------------
; Rendering helpers
; -----------------------------------------------------------------------------

w3d_shell_clear:
    ld hl,@commands
    ld bc,@end-@commands
    rst.lil 18h
    ret
@commands:
    db 12                   ; text surface
    db 16                   ; graphics surface
@end:

w3d_shell_plot_full_screen:
    ld bc,0
    ld de,0
    jr w3d_shell_plot_at

; HL=buffer, BC=x, DE=y.
w3d_shell_plot_at:
    push bc
    push de
    call selectBitmap
    pop de
    pop bc
    jp plotBitmap

; -----------------------------------------------------------------------------
; Input normalization and deterministic hook
; -----------------------------------------------------------------------------

; Install HL -> routine returning IX -> current sixteen-byte MOS keymap.
w3d_shell_set_keyboard_read_hook:
    ld (w3d_shell_keyboard_read_hook),hl
    ret

w3d_shell_reset_keyboard_read_hook:
    ld hl,w3d_shell_read_keyboard_default
    ld (w3d_shell_keyboard_read_hook),hl
    ret

; Application-global exit latch.  The shell resets it exactly once on fresh
; application entry.  Nested shell screens and gameplay may request it, then
; cheaply poll it without coupling themselves to a particular input reader.
w3d_shell_reset_exit_request:
    xor a
    ld (w3d_shell_exit_requested),a
    ret

w3d_shell_request_exit:
    ld a,1
    ld (w3d_shell_exit_requested),a
    or a
    ret

; Returns A=0/Z when execution may continue, A=1/NZ when exit was requested.
w3d_shell_query_exit_request:
    ld a,(w3d_shell_exit_requested)
    or a
    ret

w3d_shell_return_quit:
    ld a,W3D_SHELL_RESULT_QUIT
    or a
    ret

w3d_shell_read_keyboard:
    ld hl,(w3d_shell_keyboard_read_hook)
    jp (hl)

w3d_shell_read_keyboard_default:
    call w3d_music_service
    MOSCALL mos_getkbmap
    ret

w3d_shell_set_key_read_hook:
    ld (w3d_shell_key_read_hook),hl
    ret

w3d_shell_reset_key_read_hook:
    ld hl,w3d_shell_read_key_default
    ld (w3d_shell_key_read_hook),hl
    ret

w3d_shell_read_key:
    ld hl,(w3d_shell_key_read_hook)
    jp (hl)

w3d_shell_read_key_default:
    call w3d_music_service
    MOSCALL mos_getkey
    ret

; Return one normalized W3D_SHELL_ACTION_* in A.  Every recognized press is
; edge-triggered: wait for complete release before returning it to a state.
; Accept honors both Enter keys and Space, matching original HandleMenu.
w3d_shell_wait_action:
@wait:
    call w3d_shell_read_keyboard
    bit 0,(ix+14)            ; Escape wins even if another key is also held
    ld a,W3D_SHELL_ACTION_ESCAPE
    jr nz,@recognized
    bit 1,(ix+7)             ; Up
    ld a,W3D_SHELL_ACTION_UP
    jr nz,@recognized
    bit 1,(ix+5)             ; Down
    ld a,W3D_SHELL_ACTION_DOWN
    jr nz,@recognized
    bit 1,(ix+9)             ; Return
    ld a,W3D_SHELL_ACTION_ACCEPT
    jr nz,@recognized
    bit 4,(ix+7)             ; keypad Enter
    ld a,W3D_SHELL_ACTION_ACCEPT
    jr nz,@recognized
    bit 2,(ix+12)            ; Space
    ld a,W3D_SHELL_ACTION_ACCEPT
    jr nz,@recognized
    jr @wait
@recognized:
    cp W3D_SHELL_ACTION_ESCAPE
    jr nz,@release
    push af
    call w3d_shell_request_exit
    pop af
@release:
    push af
    call w3d_shell_wait_all_released
    pop af
    ret

; In-game Escape means resume, not application exit.  All recognized keys are
; still edge-triggered so one held press cannot immediately select a row.
w3d_shell_wait_pause_action:
@wait:
    call w3d_shell_read_keyboard
    bit 0,(ix+14)
    ld a,W3D_SHELL_ACTION_ESCAPE
    jr nz,@recognized
    bit 1,(ix+7)
    ld a,W3D_SHELL_ACTION_UP
    jr nz,@recognized
    bit 1,(ix+5)
    ld a,W3D_SHELL_ACTION_DOWN
    jr nz,@recognized
    bit 1,(ix+9)
    ld a,W3D_SHELL_ACTION_ACCEPT
    jr nz,@recognized
    bit 4,(ix+7)
    ld a,W3D_SHELL_ACTION_ACCEPT
    jr nz,@recognized
    bit 2,(ix+12)
    ld a,W3D_SHELL_ACTION_ACCEPT
    jr nz,@recognized
    jr @wait
@recognized:
    push af
    call w3d_shell_pause_wait_all_released
    pop af
    ret

w3d_shell_pause_wait_all_released:
    call w3d_shell_read_keyboard
    ld b,16
@scan:
    ld a,(ix)
    or a
    jr nz,w3d_shell_pause_wait_all_released
    inc ix
    djnz @scan
    ret

w3d_shell_wait_any_press:
    call w3d_shell_wait_all_released
    call w3d_shell_query_exit_request
    ret nz
@wait:
    call w3d_shell_read_keyboard
    bit 0,(ix+14)            ; Escape is globally meaningful on every wait
    jr z,@scan_any
    call w3d_shell_request_exit
    jp w3d_shell_wait_all_released
@scan_any:
    ld b,16
@scan:
    ld a,(ix)
    or a
    jr nz,@pressed
    inc ix
    djnz @scan
    jr @wait
@pressed:
    jp w3d_shell_wait_all_released

w3d_shell_wait_all_released:
    call w3d_shell_read_keyboard
    bit 0,(ix+14)            ; never swallow an Escape held on wait entry
    jr z,@scan_all
    call w3d_shell_request_exit
@scan_all:
    ld b,16
@scan:
    ld a,(ix)
    or a
    jr nz,w3d_shell_wait_all_released
    inc ix
    djnz @scan
    ret

w3d_shell_keyboard_read_hook:
    dl w3d_shell_read_keyboard_default
w3d_shell_key_read_hook:
    dl w3d_shell_read_key_default
w3d_shell_exit_requested:
    db 0
w3d_shell_main_choice:
    db W3D_SHELL_MAIN_NEW_GAME
w3d_shell_episode_choice:
    db 0
w3d_shell_difficulty:
    db W3D_SHELL_DIFFICULTY_MEDIUM
w3d_shell_pause_choice:
    db W3D_SHELL_PAUSE_CHOICE_BACK
w3d_shell_sound_choice:
    db 0
w3d_shell_choice_local:
    db 0
; User-facing preference deliberately lives outside w3d_audio_state_begin so
; loading another floor cannot silently re-enable sound effects.
w3d_audio_sfx_enabled:
    db 1
w3d_shell_timeout_ticks:
    dl 0
w3d_shell_timeout_started:
    dl 0
