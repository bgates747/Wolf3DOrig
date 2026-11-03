; Gameplay-to-shell music policy for original CheckKeys requests.
;
; M+L+I and B+A+T display ordinary Message()/IN_Ack modals without entering
; US_ControlPanel, so the current floor track continues uninterrupted. Source
; CheckKeys also treats F7-F10 as quick overlays over the live play screen;
; only F1-F6/Escape enter the full panel and select MENUSONG (WONDERIN).
; First-use F8/F9 promotion into the full save/load pages is handled where the
; shell discovers that no remembered slot exists.

; VDP 2.6+ screen capture produces a mode-independent RGBA2222 bitmap. Keep
; the original CP_CheckQuick/Message() presentation over the stopped gameplay
; frame even though the Agon shell itself uses a single-buffered mode.
W3D_GAMEPLAY_BACKDROP_BUFFER: equ $4700

; A=request. Return Z for requests which preserve floor music on entry.
w3d_panel_request_preserves_floor_music_on_open:
    cp w3d_panel_request_end_game
    jr nc,@preserve
    or 1
    ret
@preserve:
    cp a
    ret

; Start control-panel music only when the request actually enters that panel.
w3d_gameplay_panel_open_music:
    ld a,(w3d_gameplay_panel_request)
    call w3d_panel_request_preserves_floor_music_on_open
    ret z
    ld a,W3D_MUSIC_WONDERIN
    jp w3d_music_start

; A=request. Return Z when the source draws a quick Message()/confirmation
; over the play screen rather than entering the full control-panel surface.
; F8/F9 are classified here even on first use; their fallback pages simply
; cover the captured image after promoting the request to full Save/Load.
w3d_panel_request_uses_gameplay_backdrop:
    cp w3d_panel_request_pause
    jr z,@does_not_use
    cp w3d_panel_request_end_game
    jr nc,@uses
@does_not_use:
    or 1
    ret
@uses:
    cp a
    ret

; Capture the current draw surface before MODE 8+128 is replaced. After a C3
; presentation FabGL's canvas names the other physical surface, so this may be
; the immediately preceding 30-Hz frame; it is nevertheless a real stopped
; gameplay frame and avoids a destructive black shell clear. The two native
; absolute moves define an inclusive 320x240 rectangle on VDP 2.6+.
w3d_gameplay_backdrop_capture:
    ld a,(w3d_gameplay_panel_request)
    call w3d_panel_request_uses_gameplay_backdrop
    jr z,@capture
    xor a
    ld (w3d_gameplay_backdrop_active),a
    ret
@capture:
    ld hl,@commands
    ld bc,@end-@commands
    rst.lil 18h
    ld a,1
    ld (w3d_gameplay_backdrop_active),a
    ret
@commands:
    db 25,4
    dw 0,0
    db 25,4
    dw 319,239
    db 23,27,$21
    dw W3D_GAMEPLAY_BACKDROP_BUFFER,0
@end:

w3d_gameplay_backdrop_plot:
    ld a,(w3d_gameplay_backdrop_active)
    or a
    ret z
    ld hl,W3D_GAMEPLAY_BACKDROP_BUFFER
    call selectBitmap
    ld bc,0
    ld de,0
    jp plotBitmap

w3d_gameplay_backdrop_release:
    ld a,(w3d_gameplay_backdrop_active)
    or a
    ret z
    xor a
    ld (w3d_gameplay_backdrop_active),a
    ld hl,W3D_GAMEPLAY_BACKDROP_BUFFER
    jp vdu_clear_buffer

; F1-F6/Escape restart floor music after the full panel. F9 does so even for
; its remembered-slot confirmation. F7, remembered F8, F10, MLI and BAT leave
; the track untouched. Pause resumes its frozen sequencer position separately.
w3d_gameplay_panel_resume_music:
    ld a,(w3d_gameplay_panel_request)
    cp w3d_panel_request_pause
    jp z,w3d_music_resume
    cp w3d_panel_request_quick_load
    jp z,w3d_music_start_current_floor
    cp w3d_panel_request_end_game
    ret nc
    jp w3d_music_start_current_floor

w3d_gameplay_backdrop_active: db 0
