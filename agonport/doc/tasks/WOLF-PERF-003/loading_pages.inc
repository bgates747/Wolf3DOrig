; Task-only loading UI. Reconstruct BOTH pages from one authoritative state.
; No cursor position, old pixels or previous phase is trusted on either page.
; Called only at setup boundaries; two full room warmups precede measurement.
WP_LOADING_PAGE_PROOF: equ 0
wp_loading_begin:
    ld (wp_loading_stage),hl
    ld hl,0
    ld (wp_loading_count),hl
    jp wp_loading_update
wp_loading_ready:
    ld hl,wp_stage_ready
    ld (wp_loading_stage),hl
    ld hl,(wp_loading_total)
    ld (wp_loading_count),hl
    jp wp_loading_update
wp_loading_tick:
    push hl
    ld hl,(wp_loading_count)
    inc hl
    ld (wp_loading_count),hl
    ld hl,(wp_loading_total)
    inc hl
    ld (wp_loading_total),hl
    pop hl
wp_loading_update:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    ld a,(wp_loading_error)
    or a
    jr nz,@restore
    ld hl,(wp_loading_count)
    ld de,10000
    call wp_loading_digit
    ld (wp_loading_digits+0),a
    ld de,1000
    call wp_loading_digit
    ld (wp_loading_digits+1),a
    ld de,100
    call wp_loading_digit
    ld (wp_loading_digits+2),a
    ld de,10
    call wp_loading_digit
    ld (wp_loading_digits+3),a
    ld a,l
    add a,'0'
    ld (wp_loading_digits+4),a
    ; Paint current hidden page, show it, then reconstruct the other page.
    ; Both pages now contain the same stage/count, and no extra flip is needed.
    call wp_loading_paint
    call w3d_vdu_present
    call w3d_audio_wait_for_vdp_ingress
    jr c,@failed
    call wp_loading_paint
    call w3d_audio_wait_for_vdp_ingress
    jr c,@failed
    .if WP_LOADING_PAGE_PROOF
    ; Fab-only visual proof: hold each page at the same fifth-asset state.
    ; This branch is absent from both normal benchmark applications.
    ld hl,(wp_loading_total)
    ld de,5
    or a
    sbc hl,de
    jr nz,@restore
    call wp_settle_display
    call w3d_vdu_present
    call w3d_audio_wait_for_vdp_ingress
    jr c,@failed
    call wp_settle_display
    .endif
    jr @restore
@failed:
    ld a,1
    ld (wp_loading_error),a
@restore:
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ld a,(wp_loading_error)
    or a
    ret
; HL bounded u16 value; DE decimal place, returns ASCII digit/remainder.
wp_loading_digit:
    ld b,0
@subtract:
    or a
    sbc hl,de
    jr c,@done
    inc b
    jr @subtract
@done:
    add hl,de
    ld a,b
    add a,'0'
    ret
wp_loading_paint:
    ld a,12 ; CLS resets this page's text cursor before the full reconstruction.
    rst.lil 10h
    ld hl,wp_loading_title
    call printString
    call printNewLine
    call printNewLine
    ld hl,(wp_loading_stage)
    call printString
    call printNewLine
    call printNewLine
    ld hl,wp_loading_counter
    call printString
    call printNewLine
    call printNewLine
    ld hl,wp_loading_hint
    jp printString
wp_loading_title: db "Wolf3D fixture - loading",0
wp_loading_counter: db "Completed assets: "
wp_loading_digits: db "00000",0
wp_loading_hint: db "Rotation starts after loading.",0
wp_stage_shell: db "Shell graphics (shell.agnb)",0
wp_stage_sfx: db "Sound samples (sfx.agnb)",0
wp_stage_tiles: db "Wall/door textures (tiles.agnb)",0
wp_stage_sprites: db "Static sprites (sprites.agnb)",0
wp_stage_hud: db "Status panel (hud.agnb)",0
wp_stage_ready: db "Assets ready - room (34,36)",0
wp_loading_stage: dl wp_stage_shell
wp_loading_count: dl 0
wp_loading_total: dl 0
wp_loading_error: db 0
