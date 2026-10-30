; =============================================================================
; Original-facing floor-completion intermission.
;
; The bundled v1.4 archive does not contain a whole completion screen.
; WL_INTER.C composes it from the level-end portrait/picture alphabet over VGA
; colour 127.  build_hud_assets.py reproduces the invariant 320x200 fields at
; $4100/$4101 and stages the original dynamic glyphs at $4038..$4043.
;
; Final values are presented immediately and the destination floor may begin
; loading as soon as w3d_intermission_begin returns.  An abortable AGNB loader
; can use w3d_intermission_loading_tick directly: it polls Escape, latches a
; fresh non-Escape acknowledgment, and advances BJ's two-frame breathing
; animation at completed-image boundaries.  w3d_intermission_finish returns
; after a latched acknowledgment has been released, or waits for the complete
; release/press/release contract after loading.
;
; Kill and treasure totals are derived from the completed floor's immutable
; W3L seeds before the destination package replaces them. Pushwall secrets are
; not implemented yet, so their honest current ratio is zero. Bonus count-up
; and scoring remain later fidelity work.
; =============================================================================

W3D_INTERMISSION_RESULT_CONTINUE:  equ 0
W3D_INTERMISSION_RESULT_ESCAPE:    equ 2
W3D_INTERMISSION_ANIMATION_DIVIDER: equ 4

W3D_INTERMISSION_GUY_1_BUFFER:      equ 04037h
W3D_INTERMISSION_GUY_2_BUFFER:      equ 04060h
W3D_INTERMISSION_FLOOR_BASE_BUFFER:  equ 04100h
W3D_INTERMISSION_SECRET_BASE_BUFFER: equ 04101h
W3D_INTERMISSION_STATUSBAR_BUFFER:   equ 04062h
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
W3D_INTERMISSION_STATUSBAR_Y:        equ 200

; Called only after the completed floor's asynchronous owner has drained.
; Switching to mode 8 single-buffered makes the presentation stable; the
; transition loader restores mode 8+128 before it submits the next world.
;
; This entry point is deliberately nonblocking. It draws the complete source-
; floor result before any destination state can replace that source data, then
; returns A=0/carry clear so loading may begin immediately.
w3d_intermission_begin:
    xor a
    ld (w3d_intermission_input_armed),a
    ld (w3d_intermission_acknowledged),a
    ld (w3d_intermission_ack_released),a
    ld (w3d_intermission_escape_requested),a
    ld (w3d_intermission_animation_counter),a
    ld (w3d_intermission_portrait_frame),a
    call w3d_shell_setup
    ld a,(w3d_level_requested_index)
    cp 9
    jr z,@secret_floor

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
    ld de,W3D_INTERMISSION_KILL_RATIO_Y
    call w3d_intermission_draw_percentage

; Pushwalls/secret discovery are not part of the current simulation.
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
    ld de,W3D_INTERMISSION_TREASURE_RATIO_Y
    call w3d_intermission_draw_percentage
    jr @done

@secret_floor:
    ld hl,W3D_INTERMISSION_SECRET_BASE_BUFFER
    call w3d_shell_plot_full_screen
    call w3d_intermission_draw_statusbar

@done:
    xor a
    ret

; Nonblocking completed-image callback for the destination AGNB loaders.
;
; Returns A=0/carry clear after an ordinary tick, including a newly latched
; acknowledgment. Returns A=W3D_INTERMISSION_RESULT_ESCAPE/carry set when
; Escape is held. The zero/nonzero result makes this entry point directly
; compatible with agnb_load_images_with_abortable_callback.
w3d_intermission_loading_tick:
    call w3d_intermission_poll_input
    ret c

    ld a,(w3d_intermission_animation_counter)
    inc a
    cp W3D_INTERMISSION_ANIMATION_DIVIDER
    jr nc,@animate
    ld (w3d_intermission_animation_counter),a
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
    ld a,(w3d_intermission_ack_released)
    or a
    jr z,@wait
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
    jp w3d_shell_plot_at

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

w3d_intermission_par_times:
    db 1,30, 2,0, 2,0, 3,30, 3,0, 3,0, 2,30, 2,30

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
w3d_intermission_input_armed:
    db 0
w3d_intermission_acknowledged:
    db 0
w3d_intermission_ack_released:
    db 0
w3d_intermission_escape_requested:
    db 0
w3d_intermission_animation_counter:
    db 0
w3d_intermission_portrait_frame:
    db 0
w3d_intermission_application_exit_query_hook:
    dl w3d_intermission_application_exit_query_default
