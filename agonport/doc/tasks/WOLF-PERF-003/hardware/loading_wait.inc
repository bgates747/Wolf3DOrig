; Loading-only continuation of ONE pending ordered query. No timed path uses it.
; MOS 41h only observes flags. Timeout does not cancel the outstanding reply.
; Exclusive mode-flag ownership, maximum ten public waits; never clear/requery
; between waits. Interrupts remain enabled. Host still enforces its 300s bound.
wp_loading_wait:
    push bc
    call wp_clock
    ld (wpl_start),hl
    ld hl,(wpl_fences)
    inc hl
    ld (wpl_fences),hl
    xor a
    ld (wpl_passes),a
    ld c,010h
    MOSCALL mos_clearvdpflags
    ld hl,wpl_query
    ld bc,3
    rst.lil 018h
@wait:
    ld c,010h
    MOSCALL mos_waitforvdpflags
    ld (wpl_status),a
    ld hl,wpl_passes
    inc (hl)
    or a
    jp z,@success
    ld hl,(wpl_timeouts)
    inc hl
    ld (wpl_timeouts),hl
    ld a,(wpl_first_status)
    or a
    jp nz,@continue
    ld a,(wpl_status)
    ld (wpl_first_status),a
    ld a,(wpl_phase)
    ld (wpl_first_phase),a
    ld hl,(wp_loading_total)
    ld (wpl_first_total),hl
    call wpl_elapsed
    ld (wpl_first_ticks),hl
@continue:
    call wpl_elapsed
    ld de,1200 ; independent MOS deadline, nominal ten seconds
    or a
    sbc hl,de
    jp nc,@expired
    ld a,(wpl_passes)
    cp 10
    jp c,@wait
@expired:
    call wpl_record_elapsed
    pop bc
    ld a,(wpl_status)
    scf
    ret
@success:
    ld a,(wpl_passes)
    cp 1
    jp z,@record
    ld hl,(wpl_recovered)
    inc hl
    ld (wpl_recovered),hl
@record:
    call wpl_record_elapsed
    pop bc
    xor a
    ret
wpl_elapsed:
    call wp_clock
    ld de,(wpl_start)
    or a
    sbc hl,de
    ret
wpl_record_elapsed:
    call wpl_elapsed
    ld (wpl_last_ticks),hl
    ld de,(wpl_max_ticks)
    or a
    sbc hl,de
    ret c
    ld hl,(wpl_last_ticks)
    ld (wpl_max_ticks),hl
    ret

; Called after main has closed its AGNB/config files and restored mode/callback.
; No file operations inside a loader callback, no benchmark failure trampoline.
wp_loading_save:
    ld a,(wp_loading_error)
    ld (wpl_error),a
    ld a,(agnb_last_error)
    ld (wpl_agnb_error),a
    ld hl,(wp_loading_count)
    ld (wpl_count),hl
    ld hl,(wp_loading_total)
    ld (wpl_total),hl
    ld hl,wpl_filename
    ld c,6 ; create-new, must not overwrite old evidence
    MOSCALL mos_fopen
    or a
    jp z,@failed
    ld (wpl_handle),a
    ld c,a
    ld hl,wpl_data
    ld de,wpl_end-wpl_data
    MOSCALL mos_fwrite
    push de
    ld a,(wpl_handle)
    ld c,a
    MOSCALL mos_fclose
    pop hl
    ld de,wpl_end-wpl_data
    or a
    sbc hl,de
    ret z
@failed:
    ld hl,wpl_save_failed
    call printString
    ret
wpl_query: db 23,0,086h
wpl_filename: db "loading.bin",0
wpl_save_failed: db "WOLF LOADING DIAGNOSTIC WRITE FAILED",13,10,0
wpl_handle: db 0
wpl_start: dl 0
; Fixed 48-byte little-endian record. Clock values are raw MOS low-24 ticks.
wpl_data: db "WPL2",1
wpl_error: db 0
wpl_phase: db 0 ; 1=post-present first page, 2=second paint, 3=proof flip
wpl_status: db 0
wpl_count: dl 0
wpl_total: dl 0
wpl_fences: dl 0
wpl_timeouts: dl 0
wpl_recovered: dl 0
wpl_max_ticks: dl 0
wpl_last_ticks: dl 0
wpl_first_total: dl 0
wpl_first_phase: db 0
wpl_first_status: db 0
wpl_first_ticks: dl 0
wpl_passes: db 0
    db 10,1 ; pass bound, main-returned marker
wpl_agnb_error: db 0
    dl 1200 ; raw MOS whole-wait deadline, checked after each public wait
    db 0,0,0,0
wpl_end:
