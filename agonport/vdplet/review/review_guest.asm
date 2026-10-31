; Bounded Wolf3D VDPlet human-review host.
; The reviewed 320x240 scene is drawn entirely by wolf3d_scene.vdpl. This
; eZ80 program only uploads assets, invokes the module, swaps the hidden frame,
; waits for one key, and restores MOS presentation/keyboard ownership.
    .assume adl=1
    .org 0x040000
    jp start
    .align 64
    db "MOS",0,1
    include "mos_api.inc"

start:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    ld (saved_sp),sp
    xor a
    ld (installed),a
    ld (cleaned),a
    ld (module_handle),a
    ld (module_handle+1),a

    MOSCALL mos_sysvars
    push ix
    pop iy
    ld a,(iy+sysvar_scrMode)
    and 127                    ; Never restore a double-buffered MOS prompt.
    ld (saved_mode),a

    ld hl,script_name
    ld de,0x050000
    ld bc,0x020000
    push iy
    MOSCALL mos_load
    pop iy
    or a
    jp nz,failed

    ld hl,packet_callback
    ld c,0
    push iy
    MOSCALL mos_setkbvector
    pop iy
    ld a,1
    ld (installed),a
    ld hl,observations
    ld (cursor),hl
    ld hl,loading_message
    ld bc,loading_message_end-loading_message
    call send
    ld ix,0x050000

next_record:
    ld a,(ix+0)
    inc ix
    or a
    jp z,complete
    cp 1
    jp z,raw_record
    cp 2
    jp z,transaction_record
    cp 3
    jp z,clear_handle_record
    cp 9
    jp z,wait_key_record
    jp failed

raw_record:
    call tape_word
    push ix
    pop hl
    push hl
    add hl,bc
    push hl
    pop ix
    pop hl
    call send
    jp next_record

clear_handle_record:
    xor a
    ld (module_handle),a
    ld (module_handle+1),a
    jp next_record

wait_key_record:
    push ix
    push iy
    MOSCALL mos_getkey
    pop iy
    pop ix
    jp next_record

; Metadata: token:u16, kind:u8, flags:u8, value:u16, handle-patch:u16,
; packet-bytes:u16, then the raw VDU packet. flags bit0 captures a handle;
; bit1 accepts any value. FFFF means there is no handle patch.
transaction_record:
    ld a,(ix+0)
    ld (expected_token),a
    ld a,(ix+1)
    ld (expected_token+1),a
    ld a,(ix+2)
    ld (expected_kind),a
    ld a,(ix+3)
    ld (reply_flags),a
    ld a,(ix+4)
    ld (expected_value),a
    ld a,(ix+5)
    ld (expected_value+1),a
    ld de,0
    ld e,(ix+6)
    ld d,(ix+7)
    lea ix,ix+8
    call tape_word
    push ix
    pop hl
    ld a,d
    and e
    cp 255
    jr z,transaction_packet_ready
    push hl
    add hl,de
    ld a,(module_handle)
    ld (hl),a
    inc hl
    ld a,(module_handle+1)
    ld (hl),a
    pop hl
transaction_packet_ready:
    push hl
    add hl,bc
    push hl
    pop ix
    pop hl
    xor a
    ld (reply_ready),a
    call send
    ld de,(iy+sysvar_time)
wait_reply:
    ld a,(reply_ready)
    or a
    jr nz,got_reply
    ld hl,(iy+sysvar_time)
    or a
    sbc hl,de
    ld bc,12000
    or a
    sbc hl,bc
    jr c,wait_reply
    jp failed
got_reply:
    di
    ld hl,mailbox
    ld de,snapshot
    ld bc,10
    ldir
    xor a
    ld (reply_ready),a
    ei
    ld a,(snapshot+4)
    cp 1
    jp nz,failed
    ld a,(expected_kind)
    ld hl,snapshot+5
    cp (hl)
    jp nz,failed
    ld a,(expected_token)
    inc hl
    cp (hl)
    jp nz,failed
    ld a,(expected_token+1)
    inc hl
    cp (hl)
    jp nz,failed
    ld a,(reply_flags)
    bit 0,a
    jr z,check_value
    ld a,(snapshot+8)
    ld (module_handle),a
    ld b,a
    ld a,(snapshot+9)
    ld (module_handle+1),a
    or b
    jp z,failed
    jr append_reply
check_value:
    bit 1,a
    jr nz,append_reply
    ld a,(expected_value)
    ld hl,snapshot+8
    cp (hl)
    jp nz,failed
    ld a,(expected_value+1)
    inc hl
    cp (hl)
    jp nz,failed
append_reply:
    ld hl,snapshot
    ld de,(cursor)
    ld bc,10
    ldir
    ld (cursor),de
    ld hl,transactions
    inc (hl)
    jp next_record

tape_word:
    ld bc,0
    ld c,(ix+0)
    ld b,(ix+1)
    inc ix
    inc ix
    ret

send:
    push ix
    push iy
    xor a
    rst.lil 18h
    pop iy
    pop ix
    ret

; MOS invokes this for every keyboard-protocol packet. VDPL packets are copied
; to the mailbox and converted to a null key-up record before MOS continues.
packet_callback:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    push de
    pop ix
    ld a,(ix+0)
    cp 'V'
    jr nz,callback_done
    ld a,(ix+1)
    cp 'D'
    jr nz,callback_done
    ld a,(ix+2)
    cp 'P'
    jr nz,callback_done
    ld a,(ix+3)
    cp 'L'
    jr nz,callback_done
    push ix
    pop hl
    ld de,mailbox
    ld bc,10
    ldir
    xor a
    ld (ix+0),a
    ld (ix+1),a
    ld (ix+2),a
    ld (ix+3),a
    inc a
    ld (reply_ready),a
callback_done:
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

complete:
    ld a,(transactions)
    cp 5
    jp nz,failed
    call cleanup_once
    ld hl,(cursor)
    ld de,observations
    or a
    sbc hl,de
    push hl
    pop bc
    ld hl,result_name
    push iy
    MOSCALL mos_save
    pop iy
    or a
    jp nz,failed_after_cleanup
    ld hl,success_message
    ld bc,success_message_end-success_message
    call send
    ld hl,0
    jr finish

failed:
    call cleanup_once
failed_after_cleanup:
    ld hl,failure_name
    ld de,transactions
    ld bc,failure_state_end-transactions
    push iy
    MOSCALL mos_save
    pop iy
    ld hl,failure_message
    ld bc,failure_message_end-failure_message
    call send
    ld hl,1

finish:
    ld (exit_code),hl
    ld sp,(saved_sp)
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ld hl,(exit_code)
    ret

cleanup_once:
    ld a,(cleaned)
    or a
    ret nz
    inc a
    ld (cleaned),a
    call unload_if_needed
    ld hl,clear_buffers_packet
    ld bc,clear_buffers_packet_end-clear_buffers_packet
    call send
    call remove_callback
    ld a,(saved_mode)
    ld (restore_packet+1),a
    ld hl,restore_packet
    ld bc,restore_packet_end-restore_packet
    call send
    ret

unload_if_needed:
    ld a,(module_handle)
    ld b,a
    ld a,(module_handle+1)
    or b
    ret z
    ld a,(module_handle)
    ld (cleanup_unload_handle),a
    ld a,(module_handle+1)
    ld (cleanup_unload_handle+1),a
    ld hl,cleanup_unload_packet
    ld bc,cleanup_unload_packet_end-cleanup_unload_packet
    call send
    xor a
    ld (module_handle),a
    ld (module_handle+1),a
    ret

remove_callback:
    ld a,(installed)
    or a
    ret z
    xor a
    ld (installed),a
    ld hl,0
    ld c,0
    push iy
    MOSCALL mos_setkbvector
    pop iy
    ret

script_name: asciz "script.bin"
result_name: asciz "results.dat"
failure_name: asciz "failure.dat"

loading_message:
    db 13,10,"Loading exact bounded Wolf3D VDPlet review scene...",13,10
    db "The reviewed frame will contain no host labels.",13,10
loading_message_end:
success_message:
    db 13,10,"Wolf VDPlet review finished.",13,10
    db "The scene was drawn entirely by wolf3d_scene.vdpl.",13,10
    db "Host labels were shown only before and after that frame.",13,10
    db "Type dir at the MOS prompt below and report that it works.",13,10
success_message_end:
failure_message:
    db 13,10,"Wolf VDPlet review failed; keep this profile for diagnosis.",13,10
    db "Type dir to confirm MOS keyboard recovery.",13,10
failure_message_end:

; Unrequested best-effort unload used only by a graceful error path.
cleanup_unload_packet:
    db 23,0,216
    dw 8
    db 1,3
    dw 0
    db 0,0
cleanup_unload_handle: dw 0
cleanup_unload_packet_end:

clear_buffers_packet:
    db 23,0,160,0x77,0xea,2
    db 23,0,160,0x00,0x71,2
    db 23,0,160,0x01,0x71,2
    db 23,0,160,0x02,0x71,2
    db 23,0,160,0x03,0x71,2
clear_buffers_packet_end:
restore_packet:
    db 22,0,23,1,1,12
restore_packet_end:

installed: db 0
cleaned: db 0
saved_mode: db 0
reply_ready: db 0
transactions: db 0
reply_flags: db 0
expected_kind: db 0
expected_token: dw 0
expected_value: dw 0
module_handle: dw 0
mailbox: blkb 10,0
snapshot: blkb 10,0
failure_state_end:
saved_sp: dl 0
cursor: dl 0
exit_code: dl 0
observations: blkb 50,0
