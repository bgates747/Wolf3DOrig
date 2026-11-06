; Task-only stable-lifecycle INFO snapshot. EMOS5735812 ten-byte VDPL callback.
; No graphics, timer, module, audio or buffer mutation. Failed pending request
; keeps resident callback/code; never returns into a late interrupt after timeout.
    .assume adl=1
    .org 040000h
    jp start
    .align 64
    db "MOS",0,1
start:
    push af
    push bc
    push de
    push ix
    push iy
    ld hl,(0bc38eh)
    ld de,0
    or a
    sbc hl,de
    jp nz,refused
    ld hl,callback
    ld c,0
    ld a,01dh
    rst.lil 08h
    ld hl,values
    ld (next_value),hl
    ld b,18
next:
    push bc
    xor a
    ld (ready),a
    ld hl,token
    inc (hl)
    ld a,08h
    rst.lil 08h
    ld hl,(ix+0)
    ld (began),hl
    ld hl,packet
    ld bc,packet_end-packet
    rst.lil 18h
wait:
    ld a,(ready)
    or a
    jp nz,received
    ld a,08h
    rst.lil 08h
    ld hl,(ix+0)
    ld de,(began)
    or a
    sbc hl,de
    ld de,240
    or a
    sbc hl,de
    jp c,wait
failed:
    ld hl,failure
    call print
hold:
    jp hold
received:
    ld a,(mailbox+4)
    cp 1
    jp nz,failed
    ld a,(mailbox+5)
    cp 4
    jp nz,failed
    ld a,(mailbox+6)
    ld hl,token
    cp (hl)
    jp nz,failed
    ld a,(mailbox+7)
    or a
    jp nz,failed
    ld hl,(next_value)
    ld a,(mailbox+8)
    ld (hl),a
    inc hl
    ld a,(mailbox+9)
    ld (hl),a
    inc hl
    ld (next_value),hl
    ld hl,field
    inc (hl)
    pop bc
    dec b
    jp nz,next
    ld hl,0
    ld c,0
    ld a,01dh
    rst.lil 08h
    ld hl,(0bc38eh)
    ld de,0
    or a
    sbc hl,de
    jp nz,failed
    ld a,1
    ld (complete),a
    ld hl,filename
    ld c,6
    ld a,00ah
    rst.lil 08h
    or a
    jp z,failed
    ld (handle),a
    ld c,a
    ld hl,result
    ld de,result_end-result
    ld a,01bh
    rst.lil 08h
    push de
    ld a,(handle)
    ld c,a
    ld a,00bh
    rst.lil 08h
    pop hl
    ld de,result_end-result
    or a
    sbc hl,de
    jp nz,failed
    ld hl,success
    call print
refused:
    pop iy
    pop ix
    pop de
    pop bc
    pop af
    ld hl,0
    ret
print:
    ld bc,0
    xor a
    rst.lil 18h
    ret
callback:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    push de
    pop ix
    ld hl,(ix+0)
    ld de,0504456h ; VDP
    or a
    sbc hl,de
    jp nz,callback_end
    ld a,(ix+3)
    cp 'L'
    jp nz,callback_end
    ld a,(ready)
    or a
    jp nz,callback_end
    push ix
    pop hl
    ld de,mailbox
    ld bc,10
    ldir
    ld a,1
    ld (ready),a
callback_end:
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret
packet:
    db 23,0,0d8h
    dw 8
    db 1,4
token: dw 0
    db 1,0
field: dw 0
packet_end:
began: dl 0
next_value: dl 0
ready: db 0
handle: db 0
mailbox: ds 10
filename: asciz "resource.bin"
success: db "WOLF RESOURCE COMPLETE",13,10,0
failure: db "WOLF RESOURCE FAILED - RESIDENT HOLD",13,10,0
result: db "WPR1"
complete: db 0
    db 0
    dw 18
values: ds 36
result_end:
