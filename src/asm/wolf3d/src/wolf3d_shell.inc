; =============================================================================
; First application shell. Graphics are original WL1 v1.4 assets; text uses
; the VDP font until the original proportional font decoder is promoted.
; =============================================================================

W3D_SHELL_RESULT_QUIT:     equ 0
W3D_SHELL_RESULT_NEW_GAME: equ 1

w3d_shell_setup:
    ld hl,@commands
    ld bc,@end-@commands
    rst.lil 18h
    ret
@commands:
    db 22,8                 ; 320x240x64, single buffered
    db 23,0,0c0h,0          ; native logical coordinates
    db 23,1,0               ; cursor hidden
    db 18,0,128
    db 16
@end:

; Explicit future extension point. It deliberately does nothing today.
w3d_shell_show_agon_splash:
    ret

w3d_shell_run:
    call w3d_shell_setup
    call w3d_shell_show_agon_splash
    ld hl,W3D_SHELL_TITLE_BUFFER
    call selectBitmap
    ld bc,0
    ld de,0
    call plotBitmap
    ld hl,@version_line
    call printString
    call w3d_shell_wait_any_press
    jp w3d_shell_main_menu
@version_line:
    db 31,8,26,"Wolf3DOrig App 0.1.0 Alpha 1",0

w3d_shell_main_menu:
    xor a
    ld (w3d_shell_menu_choice),a
@redraw:
    call w3d_shell_draw_main_menu
@wait:
    MOSCALL mos_getkbmap
    bit 1,(ix+7)             ; Up
    jr nz,@toggle
    bit 1,(ix+5)             ; Down
    jr nz,@toggle
    bit 1,(ix+9)             ; Enter
    jr nz,@accept
    bit 4,(ix+7)             ; keypad Enter
    jr nz,@accept
    bit 0,(ix+14)            ; Escape
    jr nz,@quit
    jr @wait
@toggle:
    ld a,(w3d_shell_menu_choice)
    xor 1
    ld (w3d_shell_menu_choice),a
    call w3d_shell_wait_all_released
    jr @redraw
@accept:
    call w3d_shell_wait_all_released
    ld a,(w3d_shell_menu_choice)
    or a
    jr nz,@quit
    call w3d_shell_choose_episode
    jr z,@redraw
    call w3d_shell_choose_difficulty
    jr z,@redraw
    ld a,W3D_SHELL_RESULT_NEW_GAME
    ret
@quit:
    call w3d_shell_wait_all_released
    xor a
    ret

w3d_shell_draw_main_menu:
    call w3d_shell_clear
    ld hl,W3D_SHELL_MENU_BACKDROP_BUFFER
    call selectBitmap
    ld bc,32
    ld de,28
    call plotBitmap
    ld hl,W3D_SHELL_OPTIONS_HEADING_BUFFER
    call selectBitmap
    ld bc,84
    ld de,0
    call plotBitmap
    ld hl,@labels
    call printString
    ld a,(w3d_shell_menu_choice)
    or a
    ld de,56
    jr z,@cursor
    ld de,173
@cursor:
    ld hl,W3D_SHELL_CURSOR_1_BUFFER
    call selectBitmap
    ld bc,96
    jp plotBitmap
@labels:
    db 17,15,31,15,7,"New Game"
    db 17,8,31,15,9,"Sound"
    db 31,15,11,"Control"
    db 31,15,13,"Load Game"
    db 31,15,15,"Save Game"
    db 31,15,17,"Change View"
    db 31,15,19,"Read This!"
    db 31,15,21,"View Scores"
    db 31,15,23,"Back to Demo"
    db 17,15,31,15,25,"Quit",0

w3d_shell_choose_episode:
    call w3d_shell_clear
    ld hl,@heading
    call printString
    ld hl,W3D_SHELL_EPISODE_1_BUFFER
    ld bc,42
    ld de,24
    call w3d_shell_plot_sequence
    ld hl,@labels
    call printString
@wait:
    MOSCALL mos_getkbmap
    bit 1,(ix+9)
    jr nz,@accept
    bit 4,(ix+7)
    jr nz,@accept
    bit 0,(ix+14)
    jr nz,@cancel
    jr @wait
@accept:
    call w3d_shell_wait_all_released
    ld a,1
    ret
@cancel:
    call w3d_shell_wait_all_released
    xor a
    ret
@heading:
    db 17,15,31,11,1,"Which episode to play?",0
@labels:
    db 31,13,4,"Episode 1  Escape from Wolfenstein"
    db 17,8,31,13,7,"Episode 2  Operation: Eisenfaust"
    db 31,13,10,"Episode 3  Die, Fuhrer, Die!"
    db 31,13,13,"Episode 4  A Dark Secret"
    db 31,13,16,"Episode 5  Trail of the Madman"
    db 31,13,19,"Episode 6  Confrontation",0

; Plot the six consecutive episode buffers at the original 26-pixel spacing.
w3d_shell_plot_sequence:
    ld a,6
@loop:
    push af
    push hl
    push bc
    push de
    call selectBitmap
    pop de
    pop bc
    pop hl
    pop af
    push af
    push hl
    push bc
    push de
    call plotBitmap
    pop de
    pop bc
    pop hl
    pop af
    inc hl
    ld bc,42
    push hl
    ld hl,26
    add hl,de
    ex de,hl
    pop hl
    dec a
    jr nz,@loop
    ret

w3d_shell_choose_difficulty:
    ld a,2
    ld (w3d_shell_difficulty),a
@redraw:
    call w3d_shell_clear
    ld hl,@labels
    call printString
    ld a,(w3d_shell_difficulty)
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    ld de,96
    add hl,de
    ex de,hl
    ld hl,W3D_SHELL_CURSOR_1_BUFFER
    call selectBitmap
    ld bc,72
    call plotBitmap
@wait:
    MOSCALL mos_getkbmap
    bit 1,(ix+7)
    jr nz,@up
    bit 1,(ix+5)
    jr nz,@down
    bit 1,(ix+9)
    jr nz,@accept
    bit 4,(ix+7)
    jr nz,@accept
    bit 0,(ix+14)
    jr nz,@cancel
    jr @wait
@up:
    ld a,(w3d_shell_difficulty)
    or a
    jr nz,@up_ok
    ld a,4
@up_ok:
    dec a
    ld (w3d_shell_difficulty),a
    call w3d_shell_wait_all_released
    jr @redraw
@down:
    ld a,(w3d_shell_difficulty)
    inc a
    and 3
    ld (w3d_shell_difficulty),a
    call w3d_shell_wait_all_released
    jr @redraw
@accept:
    call w3d_shell_wait_all_released
    ld a,(w3d_shell_difficulty)
    ld (w3d_requested_difficulty),a
    ld a,1
    ret
@cancel:
    call w3d_shell_wait_all_released
    xor a
    ret
@labels:
    db 17,15,31,12,8,"Can I play, Daddy?"
    db 31,12,10,"Don't hurt me."
    db 31,12,12,"Bring 'em on!"
    db 31,12,14,"I am Death incarnate!",0

w3d_shell_clear:
    ld a,16
    rst.lil 10h
    ret

w3d_shell_wait_any_press:
    call w3d_shell_wait_all_released
@wait:
    MOSCALL mos_getkbmap
    ld b,16
@scan:
    ld a,(ix)
    or a
    jr nz,w3d_shell_wait_all_released
    inc ix
    djnz @scan
    jr @wait

w3d_shell_wait_all_released:
    MOSCALL mos_getkbmap
    ld b,16
@scan:
    ld a,(ix)
    or a
    jr nz,w3d_shell_wait_all_released
    inc ix
    djnz @scan
    ret

w3d_shell_menu_choice:
    db 0
w3d_shell_difficulty:
    db 2
