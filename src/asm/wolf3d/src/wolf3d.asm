; =============================================================================
; Wolf3D eZ80 client -- the real, growing game application.
;
; Distinct from its two siblings under src/asm/: wolf3d_hello (raw wire-
; protocol smoke test for the BUFFERED_WOLF3D VDP opcode) and wolf3d_ai (the
; sight/collision logic's own prototyping + regression-test project, whose
; validated reusable API graduated into this app once that work was done --
; see wolf3d_world.inc/wolf3d_math.inc/wolf3d_sight.inc below).
;
; Currently just proves the reusable gameplay API and the vendored .agnb
; asset loader assemble and link together; the real MOS-driven main loop
; (map load, actor think/render dispatch to the VDP, input) is future work.
; =============================================================================

    .assume adl=1
    .org 040000h

    jp start

    .align 64
    .db "MOS",0,1

    include "wolf3d_sight.inc"
    include "agnb_dependencies.inc"
    include "agnb_api.inc"

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
    db "Wolf3D eZ80 client",0

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

main:
    ld hl,banner
    call printString
    call printNewLine
    ret
