; =============================================================================
; Wolf3D VDP dispatch smoke test.
;
; Sends VDU 23,0,&A0,bufferId;&4A,0 (the BUFFERED_WOLF3D hello-world
; subcommand) and VDU 23,0,&A0,bufferId;&4A,41,mode,token; (the render-done
; callback register/unregister subcommand, mirroring Pingo's own 41) to
; prove the opcode/subcommand wire encoding round-trips correctly. Modeled on
; the MOS/VDU conventions in pingoasm/apps/moveair-local/src/jet.asm (see
; /memories/repo/agon-ez80-assembly-notes.md), written standalone here rather
; than depending on that sibling project's files.
;
; This does not wait for a render-done callback: no Wolf3D render pipeline
; exists yet to ever send one (see video/wolf3d.h in agon-vdp-wolf3d), so
; the notify-register call here just demonstrates the encoding and leaves
; notification disabled (mode 0).
; =============================================================================

    .assume adl=1
    .org 040000h

    jp start

    .align 64
    .db "MOS",0,1

start:
    push af
    push bc
    push de
    push ix
    push iy
    call main

exit:
    pop iy
    pop ix
    pop de
    pop bc
    pop af
    ld hl,0
    ret

banner:
    db "Wolf3D VDP dispatch smoke test",0
sent_hello_msg:
    db "Sent VDU 23,0,&A0,0;&4A,0 (hello) to the VDP",0
sent_notify_msg:
    db "Sent VDU 23,0,&A0,0;&4A,41,0,0; (render-done notify, disabled) to the VDP",0

; ---------------------------------------------------------------------------
; VDU helpers
; ---------------------------------------------------------------------------

; Print a null-terminated string at HL using VDU 0 (text output).
printString:
    push bc
    ld bc,0
    ld a,0
    rst.lil 18h
    pop bc
    ret

printNewLine:
    ld a,'\r'
    rst.lil 10h
    ld a,'\n'
    rst.lil 10h
    ret

; VDU 23, 0, &A0, bufferId; &4A, 0 : Wolf3D hello-world dispatch smoke test
    MACRO WOLF3D_HELLO BUFFER_ID
    ld hl,@beg
    ld bc,@end-@beg
    rst.lil 18h
    jp @end
@beg:
    db 23,0,0xA0
    dw BUFFER_ID
    db 0x4A,0
@end:
    ENDMACRO

; VDU 23, 0, &A0, bufferId; &4A, 41, mode, token; : Wolf3D render-done
; callback register/unregister (mirrors Pingo's own subcommand 41)
    MACRO WOLF3D_SET_RENDER_NOTIFY BUFFER_ID, MODE, TOKEN
    ld hl,@beg
    ld bc,@end-@beg
    rst.lil 18h
    jp @end
@beg:
    db 23,0,0xA0
    dw BUFFER_ID
    db 0x4A,41,MODE
    dw TOKEN
@end:
    ENDMACRO

main:
    ld hl,banner
    call printString
    call printNewLine

    WOLF3D_HELLO 0
    ld hl,sent_hello_msg
    call printString
    call printNewLine

    WOLF3D_SET_RENDER_NOTIFY 0,0,0
    ld hl,sent_notify_msg
    call printString
    call printNewLine

    ret
