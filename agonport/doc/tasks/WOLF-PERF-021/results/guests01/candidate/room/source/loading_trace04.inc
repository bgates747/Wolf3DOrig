; WOLF-PERF-003-16 loading-only RAM observation, pinned EMOS c9c8b6b.
; Side-effect-free RAM reads only. No UART port reads, DI, writes to firmware,
; query resend or debug transport. Hooks preserve AF/BC/DE/HL/IX/IY.
WPL3_SIZE: equ 128
WPL3_CAPACITY: equ 32
wpl3_init:
    push af
    push bc
    push de
    push hl
    xor a
    ld hl,wpl3_mutable
    ld (hl),a
    ld de,wpl3_mutable+1
    ld bc,wpl3_end-wpl3_mutable-1
    ldir
    pop hl
    pop de
    pop bc
    pop af
    ret

wpl3_paint_begin:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call wp_clock
    ld (wpl3_paint_start),hl
    ld hl,0
    ld (wpl3_present_start),hl
    ld (wpl3_present_end),hl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

wpl3_paint_end:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call wp_clock
    ld (wpl3_paint_stop),hl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

wpl3_present_begin:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call wp_clock
    ld (wpl3_present_start),hl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

wpl3_present_done:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call wp_clock
    ld (wpl3_present_end),hl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

wpl3_begin_fence:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    xor a
    ld hl,wpl3_current
    ld (hl),a
    ld de,wpl3_current+1
    ld bc,WPL3_SIZE-1
    ldir
    ld hl,(wpl_fences)
    ld (wpl3_current+0),hl
    ld hl,(wp_loading_stage)
    ld (wpl3_current+4),hl
    ld hl,(wp_loading_count)
    ld (wpl3_current+7),hl
    ld hl,(wp_loading_total)
    ld (wpl3_current+10),hl
    ld hl,(agnb_metadata+agnb_meta_data_size)
    ld (wpl3_current+15),hl
    ld hl,(agnb_stream_remaining)
    ld (wpl3_current+19),hl
    ld hl,(agnb_stream_block_size)
    ld (wpl3_current+22),hl
    ld a,(wpl_phase)
    ld (wpl3_current+3),a
    ld hl,(agnb_metadata+agnb_meta_bufferId)
    ld a,l
    ld (wpl3_current+13),a
    ld a,h
    ld (wpl3_current+14),a
    ld a,(agnb_metadata+agnb_meta_data_size+3)
    ld (wpl3_current+18),a
    ld a,mb
    ld (wpl3_current+25),a
    ld hl,wpl_query
    ld de,wpl3_current+26
    ld bc,3
    ldir
    ld hl,wpl_query
    ld (wpl3_current+29),hl
    ld hl,3
    ld (wpl3_current+32),hl
    ld hl,wpl3_paint_start
    ld de,wpl3_current+35
    ld bc,12
    ldir
    ld a,(0bc35ah) ; private source-bound _serialFlags, ordinary RAM
    ld (wpl3_current+80),a
    ld a,(0bcb25h) ; committed backend byte, ordinary RAM
    ld (wpl3_current+82),a
    ld a,(0bc378h) ; EMOS REPLY parser state, not VDP command grammar
    ld (wpl3_current+84),a
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

wpl3_clear_begin:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call wp_clock
    ld (wpl3_current+47),hl
    ld a,(ix+4)
    ld (wpl3_current+73),a
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

wpl3_clear_end:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call wp_clock
    ld (wpl3_current+50),hl
    ld a,(ix+4)
    ld (wpl3_current+74),a
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

wpl3_tx_begin:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call wp_clock
    ld (wpl3_current+53),hl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

wpl3_tx_end:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    ld (wpl3_current+67),hl
    ld (wpl3_current+70),bc
    push af
    ld hl,0
    add hl,sp
    ld a,(hl)
    ld (wpl3_current+66),a ; F from saved AF, no mixed-width stack pop
    inc hl
    ld a,(hl)
    ld (wpl3_current+65),a ; A from saved AF
    pop af
    call wp_clock
    ld (wpl3_current+56),hl
    ld a,(ix+4)
    ld (wpl3_current+75),a
    ld a,(0bc35ah)
    ld (wpl3_current+81),a
    ld a,(0bcb25h)
    ld (wpl3_current+83),a
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

wpl3_wait_begin:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call wp_clock
    ld (wpl3_current+59),hl
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

wpl3_wait_end:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call wp_clock
    ld (wpl3_current+62),hl
    ld a,(ix+4)
    ld (wpl3_current+76),a
    ld a,(wpl_status)
    ld (wpl3_current+77),a
    ld a,(wpl_passes)
    ld (wpl3_current+78),a
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

wpl3_commit:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    ld a,(wpl3_frozen)
    or a
    jp nz,wpl3_commit_done
    ld a,(wpl_status)
    ld (wpl3_error),a
    or a
    jr z,@not_failed
    ld a,1
    ld (wpl3_frozen),a
@not_failed:
    ld a,1
    ld (wpl3_current+79),a ; observer returned, not a success flag
    ld a,(0bc378h)
    ld (wpl3_current+85),a
    ld a,(0bc379h)
    ld (wpl3_current+86),a
    ld a,(0bc37ah)
    ld (wpl3_current+87),a
    ld hl,(0bc37bh)
    ld (wpl3_current+88),hl
    ld hl,0bc37eh
    ld de,wpl3_current+91
    ld bc,16
    ldir ; IRQ may change reply parser between these reads; not atomic
    ld a,(wpl3_next)
    ld hl,0
    ld l,a
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl ; index*128
    ld de,wpl3_ring
    add hl,de
    ex de,hl
    ld hl,wpl3_current
    ld bc,WPL3_SIZE
    ldir
    ld a,(wpl3_next)
    inc a
    and WPL3_CAPACITY-1
    ld (wpl3_next),a
    ld a,(wpl3_valid)
    cp WPL3_CAPACITY
    jr z,@full
    inc a
    ld (wpl3_valid),a
@full:
    ld hl,(wpl_fences)
    ld (wpl3_fences),hl
    ld hl,(wp_loading_total)
    ld (wpl3_total),hl
wpl3_commit_done:
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

wpl3_save:
    ld a,1
    ld (wpl3_returned),a
    ld a,(wp_loading_error)
    ld (wpl3_error),a
    ld hl,wpl3_filename
    ld c,6
    MOSCALL mos_fopen
    or a
    jr z,@failed
    ld (wpl3_handle),a
    ld c,a
    ld hl,wpl3_header
    ld de,wpl3_file_end-wpl3_header
    MOSCALL mos_fwrite
    push de
    ld a,(wpl3_handle)
    ld c,a
    MOSCALL mos_fclose
    pop hl
    ld de,wpl3_file_end-wpl3_header
    or a
    sbc hl,de
    ret z
@failed:
    ld a,1
    ld (wpl3_save_failed),a
    ret
wpl3_filename: db "loading3.bin",0
wpl3_handle: db 0
wpl3_header: db "WPQ3",1,WPL3_SIZE,WPL3_CAPACITY
wpl3_mutable:
wpl3_next: db 0
wpl3_valid: db 0
wpl3_frozen: db 0
wpl3_returned: db 0
wpl3_error: db 0
wpl3_fences: dl 0
wpl3_total: dl 0
wpl3_save_failed: db 0
wpl3_reached: db 0
    ds 44 ; 64-byte header; cleared explicitly before main
wpl3_current: ds WPL3_SIZE
wpl3_ring: ds WPL3_SIZE*WPL3_CAPACITY
wpl3_file_end:
wpl3_paint_start: dl 0
wpl3_paint_stop: dl 0
wpl3_present_start: dl 0
wpl3_present_end: dl 0
wpl3_end:
