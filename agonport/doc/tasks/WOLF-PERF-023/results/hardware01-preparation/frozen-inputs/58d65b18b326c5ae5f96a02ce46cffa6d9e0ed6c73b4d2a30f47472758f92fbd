; Small arithmetic subset reused from the project-owned AgonMaths 3D work.
; Only low 16-bit GP words are significant; 32-bit products use H:L:D:E.

; Unsigned HL * DE -> H:L:D:E.
w3d_umul16x16_32:
    ld b,e
    ld c,l
    ld l,e
    ld e,c
    mlt bc
    ld a,b
    ld b,h
    mlt hl
    add a,l
    ld l,a
    adc a,h
    sub a,l
    ld h,a
    ld a,c
    ld c,d
    mlt de
    add.s hl,de
    ld e,a
    ld d,l
    ld l,h
    ld h,0
    rl h
    mlt bc
    add.s hl,bc
    ret

; Signed HL * DE -> H:L:D:E.
w3d_smul16x16_32:
    ld a,h
    xor d
    ex af,af'
    bit 7,h
    jr z,@hl_positive
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
@hl_positive:
    bit 7,d
    jr z,@de_positive
    xor a
    sub e
    ld e,a
    ld a,0
    sbc a,d
    ld d,a
@de_positive:
    call w3d_umul16x16_32
    ex af,af'
    ret p
    xor a
    sub e
    ld e,a
    ld a,0
    sbc a,d
    ld d,a
    ld a,0
    sbc a,l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
    or a
    ret

; Compute a signed 8.8 boundary step:
;   clamp(trunc((minor_delta << 8) / major_distance), -32767, 32767)
;
; input:  HL signed minor delta in 8.8 coordinate units
;         DE unsigned nonzero major distance
; output: HL signed step
; destroys AF, BC, DE; AF' preserved
w3d_slope8:
    ld a,h
    and 0x80
    ld (w3d_math_sign),a
    bit 7,h
    jr z,@magnitude_ready
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
@magnitude_ready:
    push hl
    ; A quotient can exceed 32767 only when denominator is below 128.
    ld a,d
    or a
    jr nz,@not_clamped
    ld a,e
    cp 128
    jr nc,@not_clamped
    ld c,e
    ld b,0
    sla c
    rl b
    sla c
    rl b
    sla c
    rl b
    sla c
    rl b
    sla c
    rl b
    sla c
    rl b
    sla c
    rl b
    or a
    sbc.s hl,bc
    jr c,@not_clamped
    pop hl
    ld hl,0x7fff
    jr @apply_sign
@not_clamped:
    pop hl
    ; Build abs(delta)<<8 as H:L:D:E and divide by the 16-bit DE
    ; denominator using a 16-round restoring division. The pre-check above
    ; guarantees the quotient fits below 0x8000.
    ld b,d
    ld c,e
    ld a,h
    ld d,l
    ld e,0
    ld l,a
    ld h,0
    ld a,16
@divide_loop:
    sla e
    rl d
    rl l
    rl h
    or a
    sbc.s hl,bc
    jr nc,@quotient_bit
    add.s hl,bc
    jr @next_bit
@quotient_bit:
    inc.s de
@next_bit:
    dec a
    jr nz,@divide_loop
    ex de,hl
@apply_sign:
    ld a,(w3d_math_sign)
    or a
    ret z
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
    ret

; Apply an unsigned 0..256 partial-tile distance to a signed 8.8 step.
;
; input:  HL signed step, DE unsigned partial distance
; output: HL = arithmetic_floor(step*partial/256)
; destroys AF, BC, DE and AF'
w3d_step_partial:
    ld a,d
    cp 1
    jr nz,@multiply
    ld a,e
    or a
    ret z
@multiply:
    call w3d_smul16x16_32
    ld h,l
    ld l,d
    ret

w3d_math_sign:
    db 0

