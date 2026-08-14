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

W3D_SHELL_ACTION_NONE:       equ 0
W3D_SHELL_ACTION_UP:         equ 1
W3D_SHELL_ACTION_DOWN:       equ 2
W3D_SHELL_ACTION_ACCEPT:     equ 3
W3D_SHELL_ACTION_ESCAPE:     equ 4

W3D_SHELL_MAIN_NEW_GAME:     equ 0
W3D_SHELL_MAIN_QUIT:         equ 1
W3D_SHELL_MAIN_CHOICES:      equ 2
W3D_SHELL_EPISODE_CHOICES:   equ 6
W3D_SHELL_DIFFICULTY_CHOICES: equ 4
W3D_SHELL_DIFFICULTY_MEDIUM: equ 2

; Original WL_MENU.H anchors. Selected-entry overlays contain text only; the
; original cursor and difficulty portrait are plotted independently below.
W3D_SHELL_MAIN_OVERLAY_X:       equ 100
W3D_SHELL_MAIN_NEW_GAME_Y:      equ 55
W3D_SHELL_MAIN_QUIT_Y:          equ 172
W3D_SHELL_MAIN_CURSOR_X:        equ 72
W3D_SHELL_MAIN_CURSOR_Y:        equ 53
W3D_SHELL_MAIN_QUIT_CURSOR_Y:   equ 170
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

; Initial application entry: setup -> reserved Agon hook -> original title ->
; original control panel.  Returns W3D_SHELL_RESULT_* in A with flags fixed to
; that result (Z for quit, NZ for new game).
w3d_shell_run:
    call w3d_shell_setup
    call w3d_shell_show_agon_splash
    call w3d_shell_show_title
    jp w3d_shell_main_menu

; Episode victory currently has no promoted intermission/high-score screen.
; Acknowledge the completed shareware episode and resume the same main-menu
; lifecycle.  This is intentionally distinct from initial title presentation.
w3d_shell_resume_after_victory:
    call w3d_shell_setup
    call w3d_shell_draw_victory_acknowledgment
    call w3d_shell_wait_any_press
    jp w3d_shell_main_menu

w3d_shell_show_title:
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
    call w3d_shell_wait_any_press
    ret
@version_position:
    db 17,15,31,8,26,0

w3d_shell_draw_victory_acknowledgment:
    call w3d_shell_clear
    ld hl,@message
    jp printString
@message:
    db 17,15,31,11,10,"Episode 1 complete!"
    db 31,8,13,"Press any key",0

; -----------------------------------------------------------------------------
; Main menu
; -----------------------------------------------------------------------------

w3d_shell_main_menu:
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
    jr z,@quit
    jr @wait
@move:
    ld a,(w3d_shell_main_choice)
    xor 1
    ld (w3d_shell_main_choice),a
    jr @redraw
@accept:
    ld a,(w3d_shell_main_choice)
    cp W3D_SHELL_MAIN_QUIT
    jr z,@quit
    call w3d_shell_choose_episode
    jr z,@redraw
@difficulty:
    call w3d_shell_choose_difficulty
    jr z,@episode_again
    ld a,W3D_SHELL_RESULT_NEW_GAME
    or a                    ; caller may branch on NZ
    ret
@episode_again:
    call w3d_shell_choose_episode
    jr z,@redraw
    jr @difficulty
@quit:
    ld a,W3D_SHELL_RESULT_QUIT
    or a                    ; caller may branch on Z
    ret

w3d_shell_draw_main_menu:
    call w3d_shell_clear
    ld hl,W3D_SHELL_MAIN_BASE_BUFFER
    call w3d_shell_plot_full_screen
    ld a,(w3d_shell_main_choice)
    or a
    jr nz,@quit
    ld hl,W3D_SHELL_MAIN_NEW_GAME_SELECTED_BUFFER
    ld de,W3D_SHELL_MAIN_NEW_GAME_Y
    jr @selected
@quit:
    ld hl,W3D_SHELL_MAIN_QUIT_SELECTED_BUFFER
    ld de,W3D_SHELL_MAIN_QUIT_Y
@selected:
    ld bc,W3D_SHELL_MAIN_OVERLAY_X
    call w3d_shell_plot_at
    ld a,(w3d_shell_main_choice)
    or a
    ld de,W3D_SHELL_MAIN_CURSOR_Y
    jr z,@cursor
    ld de,W3D_SHELL_MAIN_QUIT_CURSOR_Y
@cursor:
    ld hl,W3D_SHELL_CURSOR_1_BUFFER
    ld bc,W3D_SHELL_MAIN_CURSOR_X
    jp w3d_shell_plot_at

; -----------------------------------------------------------------------------
; Shareware episode menu.  All six rows navigate exactly like the original;
; only Episode 1 is available.  Accepting another episode retains selection,
; displays the original-style unavailable notice, and requires acknowledgment.
; Escape returns to the main menu.
; -----------------------------------------------------------------------------

w3d_shell_choose_episode:
    xor a
    ld (w3d_shell_episode_choice),a
@redraw:
    call w3d_shell_draw_episode_menu
@wait:
    call w3d_shell_wait_action
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
    call w3d_shell_wait_any_press
    jr @redraw
@accepted:
    ld a,1
    or a
    ret
@cancel:
    xor a
    ret

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
; Difficulty menu.  Medium is the original default.  Escape returns to episode
; selection so a user never has to restart the complete New Game path.
; -----------------------------------------------------------------------------

w3d_shell_choose_difficulty:
    ld a,W3D_SHELL_DIFFICULTY_MEDIUM
    ld (w3d_shell_difficulty),a
@redraw:
    call w3d_shell_draw_difficulty_menu
@wait:
    call w3d_shell_wait_action
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
    xor a
    ret

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

w3d_shell_read_keyboard:
    ld hl,(w3d_shell_keyboard_read_hook)
    jp (hl)

w3d_shell_read_keyboard_default:
    MOSCALL mos_getkbmap
    ret

; Return one normalized W3D_SHELL_ACTION_* in A.  Every recognized press is
; edge-triggered: wait for complete release before returning it to a state.
; Accept honors both Enter keys and Space, matching original HandleMenu.
w3d_shell_wait_action:
@wait:
    call w3d_shell_read_keyboard
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
    bit 0,(ix+14)            ; Escape
    ld a,W3D_SHELL_ACTION_ESCAPE
    jr nz,@recognized
    jr @wait
@recognized:
    push af
    call w3d_shell_wait_all_released
    pop af
    ret

w3d_shell_wait_any_press:
    call w3d_shell_wait_all_released
@wait:
    call w3d_shell_read_keyboard
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
w3d_shell_main_choice:
    db W3D_SHELL_MAIN_NEW_GAME
w3d_shell_episode_choice:
    db 0
w3d_shell_difficulty:
    db W3D_SHELL_DIFFICULTY_MEDIUM
