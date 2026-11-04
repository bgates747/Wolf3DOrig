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
W3D_SHELL_PG13_TICKS:        equ 7*120
W3D_SHELL_TITLE_TICKS:       equ 15*120
W3D_SHELL_CREDITS_TICKS:     equ 10*120
W3D_SHELL_SCORES_TICKS:      equ 10*120
W3D_SHELL_CURSOR_HALF_TICKS: equ 14 ; round(8 source 70-Hz tics at 120 Hz)

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
    W3D_STARTUP_TRACE 030h
    xor a
    ld (w3d_shell_music_paused),a
    call w3d_shell_reset_exit_request
    call w3d_shell_setup
    W3D_STARTUP_TRACE 031h
    call w3d_shell_show_agon_splash
    call w3d_shell_show_original_splash
    W3D_STARTUP_TRACE 039h
    call w3d_shell_attract_until_input
    cp W3D_SHELL_RESULT_DEMO
    ret z
    jp w3d_shell_main_menu

; Original shareware startup: the linked 320x200 sign-on waits for one fresh
; local key, then INTROSONG begins and PG13() runs for seven seconds. DOS heap
; bars and ISA-device checkboxes remain at their linked defaults because they
; have no honest Agon equivalent. The exact VGA fades are an accepted platform
; difference. Each page owns its input, so the title requires a fresh key.
w3d_shell_show_original_splash:
    ld hl,W3D_SHELL_SIGNON_BUFFER
    call w3d_shell_plot_full_screen
    W3D_STARTUP_TRACE 032h
    call w3d_shell_wait_local_any_press
    W3D_STARTUP_TRACE 033h
    ld a,W3D_MUSIC_NAZI_NOR
    call w3d_music_start
    W3D_STARTUP_TRACE 034h
    ld a,1
    ld (w3d_shell_intro_music_ready),a
    ld hl,@blue_commands
    ld bc,@blue_end-@blue_commands
    rst.lil 18h
    ld hl,W3D_SHELL_PG13_BUFFER
    ld bc,W3D_SHELL_PG13_X
    ld de,W3D_SHELL_PG13_Y
    call w3d_shell_plot_at
    W3D_STARTUP_TRACE 035h
    ld de,W3D_SHELL_PG13_TICKS
    call w3d_shell_wait_input_timeout
    W3D_STARTUP_TRACE 036h
    ld hl,@black_commands
    ld bc,@black_end-@black_commands
    rst.lil 18h
    ret
@blue_commands:
    db 18,0,128+11          ; VGA $82 -> RGB222(0,2,3)
    db 16
@blue_end:
@black_commands:
    db 18,0,128             ; restore shell background before title
    db 16
@black_end:

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
    W3D_STARTUP_TRACE 050h
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
    jp z,@escape_quit
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
    call w3d_shell_choose_episode_local
    jp z,@redraw
@difficulty:
    call w3d_shell_choose_difficulty_local
; CP_NewGame's difficulty Escape returns to episode selection. A second
; Escape from the episode page returns to the parent main menu.
    jp z,@new_game
    W3D_STARTUP_TRACE 053h
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
    call w3d_shell_help_article
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
@escape_quit:
; HandleMenu returns -1 on Escape and CP_Quit then owns the confirmation.
; Undo wait_action's application-global latch until the player accepts it.
    call w3d_shell_reset_exit_request
@quit:
    xor a                           ; ordinary 320x200 Message() center
    call w3d_shell_confirm_quit
    or a
    jp z,@redraw
    call w3d_shell_request_exit
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
@quit:
    xor a                           ; full control-panel window
    call w3d_shell_confirm_quit
    or a
    jp z,@redraw
    call w3d_shell_request_exit
    ld a,W3D_SHELL_PAUSE_QUIT
    or a
    ret
@new_game:
    call w3d_shell_choose_episode_local
    jp z,@redraw
; CP_NewGame asks only after a valid episode was selected and before the
; difficulty page. Cancelling preserves the current game and returns here.
    call w3d_shell_confirm_current_game
    or a
    jp z,@redraw
    call w3d_shell_choose_difficulty_local
; The original jumps back through firstpart, including the episode page and
; (after another valid selection) this current-game confirmation.
    jp z,@new_game
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
    call w3d_shell_help_article
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

; A=w3d_panel_request_* selected by CheckKeys-style gameplay polling. The
; caller has already drained rendering and entered the single-buffered shell.
; F1-F6 jump directly to their source pages, F7/F10 retain confirmation/quit
; semantics, and F8/F9 use the last successful slot after their first full
; save/load selection.
w3d_shell_pause_quick:
    ld (w3d_shell_quick_request),a
    call w3d_shell_pause_wait_all_released
    ld a,(w3d_shell_quick_request)
    or a
    jp z,w3d_shell_pause_menu
    cp w3d_panel_request_help
    jp z,@help
    cp w3d_panel_request_save
    jp z,@save
    cp w3d_panel_request_load
    jp z,@load
    cp w3d_panel_request_sound
    jp z,@sound
    cp w3d_panel_request_view
    jp z,@view
    cp w3d_panel_request_control
    jp z,@control
    cp w3d_panel_request_end_game
    jp z,@end_game
    cp w3d_panel_request_quick_save
    jp z,@quick_save
    cp w3d_panel_request_quick_load
    jp z,@quick_load
    cp w3d_panel_request_cheater
    jp z,@cheater
    cp w3d_panel_request_keen
    jp z,@keen
; F10's source quick path temporarily sets WindowH=160, so center the same
; prompt twenty pixels higher than the ordinary control-panel version.
    ld a,1
    call w3d_shell_confirm_quit
    or a
    jp z,@resume
    call w3d_shell_request_exit
    ld a,W3D_SHELL_PAUSE_QUIT
    or a
    ret
@help:
    call w3d_shell_help_article
    jp @resume
@sound:
    call w3d_shell_sound_page
    jp @resume
@view:
    ld hl,W3D_SHELL_CHANGE_VIEW_PAGE_BUFFER
    call w3d_shell_information_page
    jp @resume
@control:
    ld hl,W3D_SHELL_CONTROL_PAGE_BUFFER
    call w3d_shell_information_page
    jp @resume
@cheater:
    ld hl,W3D_SHELL_CHEATER_NOTICE_BUFFER
    ld bc,W3D_SHELL_CHEATER_NOTICE_X
    ld de,W3D_SHELL_CHEATER_NOTICE_Y
    call w3d_shell_plot_at
    call w3d_shell_wait_any_local_press
    jp @resume
@keen:
    ld hl,W3D_SHELL_KEEN_NOTICE_BUFFER
    ld bc,W3D_SHELL_KEEN_NOTICE_X
    ld de,W3D_SHELL_KEEN_NOTICE_Y
    call w3d_shell_plot_at
    call w3d_shell_wait_any_local_press
    jp @resume
@save:
    ld a,1
    ld b,1
    call w3d_shell_save_load_menu
    jp @resume
@load:
    xor a
    ld b,1
    call w3d_shell_save_load_menu
    or a
    jp z,@resume
@loaded:
    ld a,W3D_SHELL_PAUSE_LOAD_GAME
    or a
    ret
@end_game:
; F7 temporarily uses WindowH=160 exactly like F10.
    call w3d_shell_confirm_end_game_quick
    or a
    jp z,@resume
    ld a,W3D_SHELL_PAUSE_END_GAME
    or a
    ret
@quick_save:
    call w3d_shell_quick_slot_available
    jr nz,@quick_save_available
; First-use F8 enters the full save page, which starts menu music and restarts
; the floor track on return. Promote the request so the gameplay owner knows
; this was not the remembered-slot overlay path.
    ld a,w3d_panel_request_save
    ld (w3d_gameplay_panel_request),a
    ld a,W3D_MUSIC_WONDERIN
    call w3d_music_start
    jp @save
@quick_save_available:
; CP_CheckQuick shows Message(STR_SAVING"...") before writing the remembered
; slot. The notice remains over the drained gameplay frame until resume.
    ld hl,W3D_SHELL_SAVING_NOTICE_BUFFER
    ld bc,W3D_SHELL_SAVING_NOTICE_X
    ld de,W3D_SHELL_SAVING_NOTICE_Y
    call w3d_shell_plot_at
    ld a,(w3d_shell_quick_slot)
    push af
    call w3d_shell_slot_name_pointer
    pop af
    call w3d_save_slot_store
    jp nc,@resume
    call w3d_shell_quick_io_error
    jp @resume
@quick_load:
    call w3d_shell_quick_slot_available
    jr nz,@quick_load_available
    ld a,w3d_panel_request_load
    ld (w3d_gameplay_panel_request),a
    ld a,W3D_MUSIC_WONDERIN
    call w3d_music_start
    jp @load
@quick_load_available:
    call w3d_shell_confirm_quick_load
    or a
    jp z,@resume
    ld a,(w3d_shell_quick_slot)
    call w3d_save_slot_load
    jp nc,@loaded
    call w3d_shell_quick_io_error
@resume:
    ld a,W3D_SHELL_PAUSE_RESUME
    or a
    ret

w3d_shell_quick_slot_available:
    ld a,(w3d_shell_quick_slot_valid)
    or a
    ret z
    ld a,(w3d_shell_quick_slot)
    jp w3d_shell_slot_is_available

w3d_shell_confirm_quick_load:
; Original CP_CheckQuick confirms `Load Game called\n"<name>"?` over the
; drained play border. The mutable name uses the same Agon text path as the
; full slot panel inside a source-styled Message()/DrawOutline window.
    ld hl,W3D_SHELL_QUICK_LOAD_NOTICE_BUFFER
    ld bc,W3D_SHELL_QUICK_LOAD_NOTICE_X
    ld de,W3D_SHELL_QUICK_LOAD_NOTICE_Y
    call w3d_shell_plot_at
    ld hl,w3d_shell_slot_text_colours
    ld bc,w3d_shell_slot_text_colours_end-w3d_shell_slot_text_colours
    rst.lil 18h
    ld a,4
    ld c,11
    call w3d_shell_slot_set_cursor
    ld hl,w3d_shell_quick_load_prefix
    call printString
    ld a,4
    ld c,13
    call w3d_shell_slot_set_cursor
    ld hl,w3d_shell_quick_load_open_quote
    call printString
    ld a,(w3d_shell_quick_slot)
    call w3d_shell_slot_name_pointer
    call printString
    ld hl,w3d_shell_quick_load_suffix
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
    ld a,W3D_AUDIO_SOUND_ESCPRESSED
    call w3d_shell_play_sound
    xor a
    ret
@yes:
    ld a,W3D_AUDIO_SOUND_SHOOT
    call w3d_shell_play_sound
    ld a,1
    or a
    ret

w3d_shell_quick_io_error:
    call w3d_shell_draw_slot_io_error
    jp w3d_shell_wait_any_local_press

w3d_shell_reset_quick_slot:
    xor a
    ld (w3d_shell_quick_slot_valid),a
    ld (w3d_shell_quick_slot),a
    ret

w3d_shell_remember_quick_slot:
    ld a,(w3d_shell_slot_choice)
    ld (w3d_shell_quick_slot),a
    ld a,1
    ld (w3d_shell_quick_slot_valid),a
    ret

; Original CP_EndGame -> Confirm(ENDGAMESTR).  Y accepts; N or Escape cancels
; and returns to the in-game panel without setting the application exit latch.
w3d_shell_confirm_end_game:
    ld hl,W3D_SHELL_END_GAME_NOTICE_BUFFER
    ld bc,W3D_SHELL_END_GAME_NOTICE_X
    ld de,W3D_SHELL_END_GAME_NOTICE_Y
    jr w3d_shell_confirm_notice

w3d_shell_confirm_end_game_quick:
    ld hl,W3D_SHELL_END_GAME_NOTICE_BUFFER
    ld bc,W3D_SHELL_END_GAME_NOTICE_X
    ld de,W3D_SHELL_END_GAME_NOTICE_Y-20
    jr w3d_shell_confirm_notice

; Original in-game CP_NewGame -> Confirm(CURGAME). The startup main menu never
; uses this warning because no game exists yet.
w3d_shell_confirm_current_game:
    ld hl,W3D_SHELL_CURRENT_GAME_NOTICE_BUFFER
    ld bc,W3D_SHELL_CURRENT_GAME_NOTICE_X
    ld de,W3D_SHELL_CURRENT_GAME_NOTICE_Y
w3d_shell_confirm_notice:
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
    ld a,W3D_AUDIO_SOUND_ESCPRESSED
    call w3d_shell_play_sound
    xor a
    ret
@yes:
    ld a,W3D_AUDIO_SOUND_SHOOT
    call w3d_shell_play_sound
    ld a,1
    or a
    ret

; Original CP_Quit/F10 confirmation. The source expression is intentionally
; preserved with C precedence: first_random & (7 + (second_random & 1)). This
; selects the exact nine humorous WL1 prompts and consumes two shared RNG
; bytes. A=0 uses the normal 320x200 center; A!=0 reproduces F10's temporary
; WindowH=160 by shifting the composed prompt twenty pixels upward.
w3d_shell_confirm_quit:
    ld (w3d_shell_quit_quick),a
    call w3d_random_byte
    ld (w3d_shell_quit_random),a
    call w3d_random_byte
    and 1
    add a,7
    ld b,a
    ld a,(w3d_shell_quit_random)
    and b
    ld (w3d_shell_quit_choice),a

    ld d,a
    ld e,7
    mlt de
    inc de
    dec.s de
    ld hl,w3d_shell_quit_notices
    add hl,de
    push hl
    pop ix
    ld l,(ix+0)
    ld h,(ix+1)
    inc hl
    dec.s hl
    ld c,(ix+3)
    ld b,(ix+4)
    ld e,(ix+5)
    ld d,(ix+6)
    ld a,(w3d_shell_quit_quick)
    or a
    jr z,@plot
    ld a,e
    sub 20
    ld e,a
@plot:
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
    ld a,W3D_AUDIO_SOUND_ESCPRESSED
    call w3d_shell_play_sound
    xor a
    ret
@yes:
    ld a,W3D_AUDIO_SOUND_SHOOT
    call w3d_shell_play_sound
    ld a,1
    or a
    ret

w3d_shell_quit_notices:
    dl W3D_SHELL_QUIT_NOTICE_0_BUFFER
    dw W3D_SHELL_QUIT_NOTICE_0_X,W3D_SHELL_QUIT_NOTICE_0_Y
    dl W3D_SHELL_QUIT_NOTICE_1_BUFFER
    dw W3D_SHELL_QUIT_NOTICE_1_X,W3D_SHELL_QUIT_NOTICE_1_Y
    dl W3D_SHELL_QUIT_NOTICE_2_BUFFER
    dw W3D_SHELL_QUIT_NOTICE_2_X,W3D_SHELL_QUIT_NOTICE_2_Y
    dl W3D_SHELL_QUIT_NOTICE_3_BUFFER
    dw W3D_SHELL_QUIT_NOTICE_3_X,W3D_SHELL_QUIT_NOTICE_3_Y
    dl W3D_SHELL_QUIT_NOTICE_4_BUFFER
    dw W3D_SHELL_QUIT_NOTICE_4_X,W3D_SHELL_QUIT_NOTICE_4_Y
    dl W3D_SHELL_QUIT_NOTICE_5_BUFFER
    dw W3D_SHELL_QUIT_NOTICE_5_X,W3D_SHELL_QUIT_NOTICE_5_Y
    dl W3D_SHELL_QUIT_NOTICE_6_BUFFER
    dw W3D_SHELL_QUIT_NOTICE_6_X,W3D_SHELL_QUIT_NOTICE_6_Y
    dl W3D_SHELL_QUIT_NOTICE_7_BUFFER
    dw W3D_SHELL_QUIT_NOTICE_7_X,W3D_SHELL_QUIT_NOTICE_7_Y
    dl W3D_SHELL_QUIT_NOTICE_8_BUFFER
    dw W3D_SHELL_QUIT_NOTICE_8_X,W3D_SHELL_QUIT_NOTICE_8_Y

w3d_shell_quit_quick:
    db 0
w3d_shell_quit_random:
    db 0
w3d_shell_quit_choice:
    db 0

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
; Turning effects off already played the generic accept while they were on.
; Turning them on could not, so reproduce CP_Sound's post-enable ShootSnd.
    or a
    jp z,@redraw
    ld a,W3D_AUDIO_SOUND_SHOOT
    call w3d_shell_play_sound
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

; Original WL_TEXT.C HelpScreens/ShowArticle contract. The canonical 41 pages
; are translated offline from VGAGRAPH.WL1 chunk 150 and kept in their own
; container: loading them only when Read This is selected avoids permanently
; occupying 2.6 MiB of VDP SRAM. Every buffer is cleared on every exit path.
;
; Navigation matches ShowArticle: Up/Page Up/Left goes back; Enter/Down/
; Page Down/Right advances; Escape returns locally to the control panel.
w3d_shell_help_article:
    ld a,W3D_MUSIC_CORNER
    call w3d_music_start
    xor a
    ld (w3d_shell_help_load_aborted),a
    ld de,help_filename
    ld hl,w3d_shell_help_load_callback
    call agnb_load_images_with_abortable_callback
    jr z,@loaded
    call w3d_shell_help_clear_buffers
    ld a,(w3d_shell_help_load_aborted)
    or a
    jr z,@fallback
    call w3d_shell_pause_wait_all_released
    jp @finish
; A malformed/missing optional article must not strand the shell. Preserve the
; concise resident page as a visible fallback while returning success locally.
@fallback:
    ld hl,W3D_SHELL_READ_THIS_PAGE_BUFFER
    call w3d_shell_information_page
    jp @finish
@loaded:
    xor a
    ld (w3d_shell_help_page),a
    call w3d_shell_pause_wait_all_released
@draw:
    call w3d_shell_clear
    ld hl,W3D_HELP_PAGE_BUFFER_BASE
    ld a,(w3d_shell_help_page)
    ld e,a
    ld d,0
    add hl,de
    call w3d_shell_plot_full_screen
@wait:
    call w3d_music_service
    call w3d_shell_read_keyboard
    bit 0,(ix+14)                   ; Escape
    jr nz,@leave
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
    ld a,(w3d_shell_help_page)
    or a
    jr z,@wait_release
    dec a
    ld (w3d_shell_help_page),a
    jr @changed
@next:
    ld a,(w3d_shell_help_page)
    cp W3D_HELP_PAGE_COUNT-1
    jr nc,@wait_release
    inc a
    ld (w3d_shell_help_page),a
@changed:
    call w3d_shell_pause_wait_all_released
    jr @draw
@wait_release:
    call w3d_shell_pause_wait_all_released
    jr @wait
@leave:
    call w3d_shell_pause_wait_all_released
    call w3d_shell_help_clear_buffers
@finish:
    ld a,W3D_MUSIC_WONDERIN
    jp w3d_music_start

; Keep music responsive while streaming. Escape aborts only this local article
; load, just as ShowArticle returns to its parent menu instead of quitting DOS.
w3d_shell_help_load_callback:
    call w3d_music_service
    call w3d_shell_read_keyboard
    bit 0,(ix+14)
    jr z,@continue
    ld a,1
    ld (w3d_shell_help_load_aborted),a
    ret
@continue:
    xor a
    ret

w3d_shell_help_clear_buffers:
    ld hl,W3D_HELP_PAGE_BUFFER_BASE
    ld b,W3D_HELP_PAGE_COUNT
@clear:
    push bc
    push hl
    call vdu_clear_buffer
    pop hl
    pop bc
    inc hl
    djnz @clear
    ret

; Original DemoLoop timings at the MOS 120-Hz clock. After the three pages,
; select the next canonical recorded stream and return it to the application.
; Any key enters the control panel without promoting Escape to application
; exit, matching IN_UserInput's attract-loop role.
w3d_shell_attract_until_input:
@title:
    W3D_STARTUP_TRACE 040h
    ld a,(w3d_shell_intro_music_ready)
    or a
    jr z,@start_title_music
    xor a
    ld (w3d_shell_intro_music_ready),a
    jr @draw_title
@start_title_music:
    ld a,W3D_MUSIC_NAZI_NOR
    call w3d_music_start
@draw_title:
    call w3d_shell_draw_title
    ld de,W3D_SHELL_TITLE_TICKS
    call w3d_shell_wait_input_timeout
    W3D_STARTUP_TRACE 041h
    ret nz
    call w3d_shell_clear
    ld hl,W3D_SHELL_CREDITS_BUFFER
    call w3d_shell_plot_full_screen
    W3D_STARTUP_TRACE 042h
    ld de,W3D_SHELL_CREDITS_TICKS
    call w3d_shell_wait_input_timeout
    W3D_STARTUP_TRACE 043h
    ret nz
    ld a,W3D_MUSIC_ROSTER
    call w3d_music_start
    call w3d_highscores_draw
    W3D_STARTUP_TRACE 044h
    ld de,W3D_SHELL_SCORES_TICKS
    call w3d_shell_wait_input_timeout
    W3D_STARTUP_TRACE 045h
    ret nz
    call w3d_demo_prepare_next
    W3D_STARTUP_TRACE 046h
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
    call w3d_shell_remember_quick_slot
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
    call w3d_shell_remember_quick_slot
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
    ld a,W3D_AUDIO_SOUND_ESCPRESSED
    call w3d_shell_play_sound
    xor a
    ret
@yes:
    ld a,W3D_AUDIO_SOUND_SHOOT
    call w3d_shell_play_sound
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
    ld a,W3D_AUDIO_SOUND_SHOOT
    call w3d_shell_play_sound
    ld a,1
    or a
    ret
@cancel:
    ld a,W3D_AUDIO_SOUND_ESCPRESSED
    call w3d_shell_play_sound
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
w3d_shell_quick_load_prefix:
    db "Load Game called",0
w3d_shell_quick_load_open_quote:
    db '"',0
w3d_shell_quick_load_suffix:
    db '"','?',0
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
    W3D_STARTUP_TRACE 051h
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
    ld a,W3D_AUDIO_SOUND_NOWAY
    call w3d_shell_play_sound
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
    W3D_STARTUP_TRACE 052h
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

; The explicit global entry points retain application-exit Escape for callers
; that require it. CP_NewGame uses the local variants from both parent menus:
; Episode returns to its parent, while Difficulty is routed back to Episode.
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

; Original HandleMenu feedback.  UI effects are deliberately monaural and
; immediate; every event owns a one-request quantum outside gameplay.  Cursor
; movement preserves DrawHalfStep's MOVEGUN1, eight source-tic pause, and
; DrawGun's MOVEGUN2 rather than collapsing both sounds into one VDP burst.
w3d_shell_play_sound:
    push af
    call w3d_audio_begin_quantum
    pop af
    ld b,127
    ld c,0
    call w3d_audio_request
    jp w3d_audio_flush_quantum

w3d_shell_play_action_sound:
    cp W3D_SHELL_ACTION_UP
    jr z,@move
    cp W3D_SHELL_ACTION_DOWN
    jr z,@move
    cp W3D_SHELL_ACTION_ACCEPT
    jr z,@accept
    ld a,W3D_AUDIO_SOUND_ESCPRESSED
    jp w3d_shell_play_sound
@accept:
    ld a,W3D_AUDIO_SOUND_SHOOT
    jp w3d_shell_play_sound
@move:
    ld a,W3D_AUDIO_SOUND_MOVEGUN1
    call w3d_shell_play_sound
    call w3d_shell_cursor_half_delay
    ld a,W3D_AUDIO_SOUND_MOVEGUN2
    jp w3d_shell_play_sound

w3d_shell_cursor_half_delay:
    ld ix,(w3d_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld de,W3D_SHELL_CURSOR_HALF_TICKS
    add hl,de
    ld (w3d_shell_cursor_half_deadline),hl
@wait:
    call w3d_music_service
    ld ix,(w3d_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld de,(w3d_shell_cursor_half_deadline)
    or a
    sbc hl,de
    jr c,@wait
    ret

w3d_shell_read_keyboard:
    call w3d_shell_service_pause_toggle
    ld hl,(w3d_shell_keyboard_read_hook)
    jp (hl)

; Source WL_MENU.C::CheckPause toggles the current music sequencer without
; changing the persistent Music preference.  SD_MusicOff/On preserve the IMF
; cursor, which maps directly to the production pause/resume pair.
w3d_shell_service_pause_toggle:
    ld a,(w3d_shell_pause_toggle_requested)
    or a
    ret z
    xor a
    ld (w3d_shell_pause_toggle_requested),a
    ld a,(w3d_shell_music_paused)
    xor 1
    ld (w3d_shell_music_paused),a
    or a
    jp z,w3d_music_resume
    jp w3d_music_pause

w3d_shell_read_keyboard_default:
    call w3d_music_service
    MOSCALL mos_getkbmap
    ret

w3d_shell_music_paused:
    db 0

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
    ld a,1
    ld (w3d_shell_pause_toggle_enabled),a
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
    push af
    call w3d_shell_play_action_sound
    pop af
    cp W3D_SHELL_ACTION_ESCAPE
    jr nz,@release
    push af
    call w3d_shell_request_exit
    pop af
@release:
    push af
    call w3d_shell_wait_all_released
    pop af
    push af
    xor a
    ld (w3d_shell_pause_toggle_enabled),a
    pop af
    ret

; In-game Escape means resume, not application exit.  All recognized keys are
; still edge-triggered so one held press cannot immediately select a row.
w3d_shell_wait_pause_action:
    ld a,1
    ld (w3d_shell_pause_toggle_enabled),a
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
    call w3d_shell_play_action_sound
    pop af
    push af
    call w3d_shell_pause_wait_all_released
    pop af
    push af
    xor a
    ld (w3d_shell_pause_toggle_enabled),a
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

; Fresh local acknowledgment used by FinishSignon. Escape is an ordinary
; acknowledgment here, exactly as DOS IN_Ack; it must not request app exit.
w3d_shell_wait_local_any_press:
    call w3d_shell_pause_wait_all_released
@wait:
    call w3d_shell_read_keyboard
    ld b,16
@scan:
    ld a,(ix)
    or a
    jr nz,w3d_shell_pause_wait_all_released
    inc ix
    djnz @scan
    jr @wait

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
w3d_shell_intro_music_ready:
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
w3d_shell_quick_request:
    db 0
w3d_shell_quick_slot_valid:
    db 0
w3d_shell_quick_slot:
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
w3d_shell_cursor_half_deadline:
    dl 0
w3d_shell_help_page:
    db 0
w3d_shell_help_load_aborted:
    db 0
