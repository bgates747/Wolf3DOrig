; =============================================================================
; Shared-runtime VDPlet client foundation for the Wolf3D production backend.
;
; The standalone backend does not assemble this file. The VDPlet build driver
; supplies a nonzero package size in a temporary source tree and places the
; matching wolf3d.vdpl beside the candidate application. This layer owns only
; runtime discovery, package staging, LOAD/RUN/UNLOAD transactions and its
; ten-byte VDPL reply mailbox. Dynamic game-state batching is a separate layer.
; =============================================================================

W3D_VDPL_SELECTOR:             equ 0d8h
W3D_VDPL_PROTOCOL:             equ 1
W3D_VDPL_OP_LOAD:              equ 1
W3D_VDPL_OP_RUN:               equ 2
W3D_VDPL_OP_UNLOAD:            equ 3
W3D_VDPL_OP_INFO:              equ 4
W3D_VDPL_REPLY_LOADED:         equ 2
W3D_VDPL_REPLY_DONE:           equ 3
W3D_VDPL_REPLY_VALUE:          equ 4
W3D_VDPL_REPLY_ERROR:          equ 5
W3D_VDPL_REPLY_IDENT:          equ 1

W3D_VDPLET_RUNTIME_IDENTITY:   equ 0100h
W3D_VDPLET_REQUIRED_CAPS:      equ 0101h ; buffers + direct colour rows
W3D_VDPLET_MODULE_BUFFER:      equ 0ea77h
W3D_VDPLET_WORKSPACE_BUFFER:   equ 07100h
W3D_VDPLET_UPDATE_BUFFER:      equ 07101h
W3D_VDPLET_CONFIG_BUFFER:      equ 07102h
W3D_VDPLET_ARGUMENT_BUFFER:    equ 07103h
W3D_VDPLET_PACKAGE_ADDRESS:    equ 0a0000h
W3D_VDPLET_PACKAGE_LIMIT:      equ 22573
W3D_VDPLET_UPLOAD_CHUNK:       equ 4096
W3D_VDPLET_TIMEOUT_TICKS:      equ 1200 ; ten seconds at the 120 Hz MOS clock

W3D_VDPLET_STATUS_OK:          equ 0
W3D_VDPLET_STATUS_TIMEOUT:     equ 1
W3D_VDPLET_STATUS_PROTOCOL:    equ 2
W3D_VDPLET_STATUS_RUNTIME:     equ 3
W3D_VDPLET_STATUS_INCOMPATIBLE: equ 4
W3D_VDPLET_STATUS_FILE:        equ 5
W3D_VDPLET_STATUS_PACKAGE:     equ 6
W3D_VDPLET_STATUS_TOKEN:       equ 7

; Human-readable startup diagnostics use these stable stage numbers. They are
; deliberately client-local and are not part of the VDPL wire ABI.
W3D_VDPLET_STAGE_NONE:         equ 00h
W3D_VDPLET_STAGE_DISCOVER:     equ 01h
W3D_VDPLET_STAGE_IDENTITY:     equ 02h
W3D_VDPLET_STAGE_CAPABILITIES: equ 03h
W3D_VDPLET_STAGE_SLOT:         equ 04h
W3D_VDPLET_STAGE_READ_PACKAGE: equ 05h
W3D_VDPLET_STAGE_UPLOAD_PACKAGE: equ 06h
W3D_VDPLET_STAGE_LOAD_MODULE:  equ 07h
W3D_VDPLET_STAGE_WORKSPACE:    equ 08h
W3D_VDPLET_STAGE_DESCRIPTOR:   equ 09h
W3D_VDPLET_STAGE_CONFIG:       equ 0ah
W3D_VDPLET_STAGE_RESET:        equ 0bh
W3D_VDPLET_STAGE_RENDER:       equ 0ch
W3D_VDPLET_STAGE_FIZZLE:      equ 0dh

; Reset all application-side runtime ownership. The caller installs the shared
; keyboard/render callback before issuing the first request.
w3d_vdplet_initialize:
    xor a
    ld (w3d_vdplet_reply_ready),a
    ld (w3d_vdplet_callback_error),a
    ld (w3d_vdplet_status),a
    ld (w3d_vdplet_expected_kind),a
    ld (w3d_vdplet_transaction_pending),a
    ld (w3d_vdplet_handle+0),a
    ld (w3d_vdplet_handle+1),a
    ld (w3d_vdplet_token+0),a
    ld (w3d_vdplet_token+1),a
    ld (w3d_vdplet_last_value+0),a
    ld (w3d_vdplet_last_value+1),a
    ld (w3d_vdplet_native_error+0),a
    ld (w3d_vdplet_native_error+1),a
    ld (w3d_vdplet_stage),a
    push ix
    MOSCALL mos_sysvars
    ld (w3d_vdplet_sysvars),ix       ; ADL24 OK: destination is dl storage.
    pop ix
    ret

; Interrupt callback helper. IX points at the MOS packet. Carry set means a
; VDPL record was consumed and neutralized; carry clear means it was not ours.
w3d_vdplet_try_capture_packet:
    ld a,(ix+0)
    cp 'V'
    jr nz,@not_vdpl
    ld a,(ix+1)
    cp 'D'
    jr nz,@not_vdpl
    ld a,(ix+2)
    cp 'P'
    jr nz,@not_vdpl
    ld a,(ix+3)
    cp 'L'
    jr nz,@not_vdpl

    ld a,(w3d_vdplet_reply_ready)
    or a
    jr z,@copy
    ld a,1
    ld (w3d_vdplet_callback_error),a
    jr @neutralize
@copy:
    push ix
    pop hl
    ld de,w3d_vdplet_mailbox
    ld bc,10
    ldir
    ld a,1
    ld (w3d_vdplet_reply_ready),a
@neutralize:
    xor a
    ld (ix+0),a
    ld (ix+1),a
    ld (ix+2),a
    ld (ix+3),a
    scf
    ret
@not_vdpl:
    or a
    ret

; HL points at the u16 token field of a prepared request; A is the expected
; successful reply kind. Arm before sending so an immediate reply cannot race
; stale mailbox state.
w3d_vdplet_arm_request:
    ld b,a
    ld a,(w3d_vdplet_transaction_pending)
    or a
    jr nz,@already_pending
    ld a,b
    ld (w3d_vdplet_expected_kind),a
    push hl
    ld hl,0
    ld a,(w3d_vdplet_token+0)
    ld l,a
    ld a,(w3d_vdplet_token+1)
    ld h,a
    ld a,h
    and l
    cp 0ffh
    jr z,@token_exhausted
    inc hl
@token_ready:
    ld a,l
    ld (w3d_vdplet_token+0),a
    ld a,h
    ld (w3d_vdplet_token+1),a
    pop de
    ld a,l
    ld (de),a
    inc de
    ld a,h
    ld (de),a
    di
    xor a
    ld (w3d_vdplet_reply_ready),a
    inc a
    ld (w3d_vdplet_transaction_pending),a
    ei
    or a
    ret
@token_exhausted:
    pop hl
    ld a,W3D_VDPLET_STATUS_TOKEN
    ld (w3d_vdplet_status),a
    scf
    ret
@already_pending:
    ld a,W3D_VDPLET_STATUS_PROTOCOL
    ld (w3d_vdplet_status),a
    scf
    ret

; Discovery is the only token-zero transaction. It is operand-free so an old
; stream parser cannot reinterpret unknown payload bytes as unrelated VDU data.
w3d_vdplet_arm_discovery:
    ld a,(w3d_vdplet_transaction_pending)
    or a
    jr nz,@already_pending
    ld a,W3D_VDPL_REPLY_IDENT
    ld (w3d_vdplet_expected_kind),a
    xor a
    ld (w3d_vdplet_token+0),a
    ld (w3d_vdplet_token+1),a
    di
    ld (w3d_vdplet_reply_ready),a
    inc a
    ld (w3d_vdplet_transaction_pending),a
    ei
    or a
    ret
@already_pending:
    ld a,W3D_VDPLET_STATUS_PROTOCOL
    ld (w3d_vdplet_status),a
    scf
    ret

; Wait for and validate the one armed ten-byte VDPL reply. Carry is clear on a
; successful kind/token match and HL is the zero-extended u16 reply value.
; Carry is set on timeout, malformed/error reply or callback overlap.
w3d_vdplet_wait_reply:
    ld ix,(w3d_vdplet_sysvars)
    ld hl,(ix+sysvar_time)
    ld (w3d_vdplet_wait_started),hl ; ADL24 OK: destination is dl storage.
@wait:
    ld a,(w3d_vdplet_callback_error)
    or a
    jp nz,@protocol_error
    ld a,(w3d_vdplet_reply_ready)
    or a
    jr nz,@snapshot
    ld hl,(ix+sysvar_time)
    ld de,(w3d_vdplet_wait_started)
    or a
    sbc hl,de
    ld de,W3D_VDPLET_TIMEOUT_TICKS
    or a
    sbc hl,de
    jr c,@wait
    ld a,W3D_VDPLET_STATUS_TIMEOUT
    ld (w3d_vdplet_status),a
    scf
    ret

@snapshot:
    di
    ld hl,w3d_vdplet_mailbox
    ld de,w3d_vdplet_snapshot
    ld bc,10
    ldir
    xor a
    ld (w3d_vdplet_reply_ready),a
    ei
    ld a,(w3d_vdplet_snapshot+0)
    cp 'V'
    jp nz,@protocol_error
    ld a,(w3d_vdplet_snapshot+1)
    cp 'D'
    jp nz,@protocol_error
    ld a,(w3d_vdplet_snapshot+2)
    cp 'P'
    jp nz,@protocol_error
    ld a,(w3d_vdplet_snapshot+3)
    cp 'L'
    jp nz,@protocol_error
    ld a,(w3d_vdplet_snapshot+4)
    cp W3D_VDPL_PROTOCOL
    jp nz,@protocol_error
    ld a,(w3d_vdplet_snapshot+6)
    ld b,a
    ld a,(w3d_vdplet_token+0)
    cp b
    jp nz,@wait
    ld a,(w3d_vdplet_snapshot+7)
    ld b,a
    ld a,(w3d_vdplet_token+1)
    cp b
    jp nz,@wait

    xor a
    ld (w3d_vdplet_transaction_pending),a

; Reply values are u16. Zero HLU before publishing HL: identity compares use
; 24-bit ADL arithmetic and must not inherit an unrelated upper byte.
    ld hl,0
    ld a,(w3d_vdplet_snapshot+8)
    ld (w3d_vdplet_last_value+0),a
    ld l,a
    ld a,(w3d_vdplet_snapshot+9)
    ld (w3d_vdplet_last_value+1),a
    ld h,a
    ld a,(w3d_vdplet_snapshot+5)
    cp W3D_VDPL_REPLY_ERROR
    jp z,@runtime_error
    ld b,a
    ld a,(w3d_vdplet_expected_kind)
    cp b
    jp nz,@protocol_error
    xor a
    ld (w3d_vdplet_status),a
    scf
    ccf
    ret

@runtime_error:
    ld a,W3D_VDPLET_STATUS_RUNTIME
    ld (w3d_vdplet_status),a
    scf
    ret
@protocol_error:
    ld a,W3D_VDPLET_STATUS_PROTOCOL
    ld (w3d_vdplet_status),a
    scf
    ret

; Operand-free runtime discovery. IDENT/token0 is validated by the common
; mailbox path; its value is the available capability mask.
w3d_vdplet_discover:
    call w3d_vdplet_arm_discovery
    ret c
    ld hl,@packet
    ld bc,@end-@packet
    rst.lil 18h
    call w3d_vdplet_wait_reply
    ret c
    ld de,W3D_VDPLET_REQUIRED_CAPS
    ld a,l
    and e
    cp e
    jr nz,@incompatible
    ld a,h
    and d
    cp d
    ret z
@incompatible:
    ld a,W3D_VDPLET_STATUS_INCOMPATIBLE
    ld (w3d_vdplet_status),a
    scf
    ret
@packet:
    db 23,0,0d9h
@end:

; Send INFO0 and require the frozen protocol identity 0x0100.
w3d_vdplet_query_identity:
    ld a,W3D_VDPL_REPLY_VALUE
    ld hl,@token
    call w3d_vdplet_arm_request
    ret c
    ld hl,@packet
    ld bc,@end-@packet
    rst.lil 18h
    call w3d_vdplet_wait_reply
    ret c
    ld de,W3D_VDPLET_RUNTIME_IDENTITY
    or a
    sbc hl,de
    ret z
    ld a,W3D_VDPLET_STATUS_INCOMPATIBLE
    ld (w3d_vdplet_status),a
    scf
    ret
@packet:
    db 23,0,W3D_VDPL_SELECTOR
    dw 8
    db W3D_VDPL_PROTOCOL,W3D_VDPL_OP_INFO
@token:
    dw 0
    db 1,0
    dw 0
@end:

; Send INFO1 and require every capability used by the direct-row candidate.
w3d_vdplet_query_capabilities:
    ld a,W3D_VDPL_REPLY_VALUE
    ld hl,@token
    call w3d_vdplet_arm_request
    ret c
    ld hl,@packet
    ld bc,@end-@packet
    rst.lil 18h
    call w3d_vdplet_wait_reply
    ret c
    ld de,W3D_VDPLET_REQUIRED_CAPS
    ld a,l
    and e
    cp e
    jr nz,@incompatible
    ld a,h
    and d
    cp d
    ret z
@incompatible:
    ld a,W3D_VDPLET_STATUS_INCOMPATIBLE
    ld (w3d_vdplet_status),a
    scf
    ret
@packet:
    db 23,0,W3D_VDPL_SELECTOR
    dw 8
    db W3D_VDPL_PROTOCOL,W3D_VDPL_OP_INFO
@token:
    dw 0
    db 1,0
    dw 1
@end:

; Return INFO2's current slot handle in HL. This is both the pre-LOAD ownership
; check and the post-error way to establish whether an UNLOAD released its slot.
w3d_vdplet_query_slot:
    ld a,W3D_VDPL_REPLY_VALUE
    ld hl,@token
    call w3d_vdplet_arm_request
    ret c
    ld hl,@packet
    ld bc,@end-@packet
    rst.lil 18h
    call w3d_vdplet_wait_reply
    ret
@packet:
    db 23,0,W3D_VDPL_SELECTOR
    dw 8
    db W3D_VDPL_PROTOCOL,W3D_VDPL_OP_INFO
@token:
    dw 0
    db 1,0
    dw 2
@end:

; INFO2 must report an empty slot. A live handle belongs to somebody else and
; is never authority for this application to unload or replace it.
w3d_vdplet_require_empty_slot:
    call w3d_vdplet_query_slot
    ret c
    ld a,h
    or l
    ret z
    ld a,W3D_VDPLET_STATUS_INCOMPATIBLE
    ld (w3d_vdplet_status),a
    scf
    ret

; Load the selected package from MOS storage into high eZ80 RAM. The exact
; length is generated by the durable builder and is also sent to VDPL LOAD.
w3d_vdplet_read_package:
    ld hl,W3D_VDPLET_PACKAGE_BYTES
    ld de,0
    or a
    sbc hl,de
    jr z,@bad_package
    ld hl,W3D_VDPLET_PACKAGE_BYTES
    ld de,W3D_VDPLET_PACKAGE_LIMIT
    or a
    sbc hl,de
    jr nc,@bad_package
    ld hl,w3d_vdplet_package_filename
    ld de,W3D_VDPLET_PACKAGE_ADDRESS
    ld bc,W3D_VDPLET_PACKAGE_BYTES
    push ix
    push iy
    MOSCALL mos_load
    pop iy
    pop ix
    or a
    ret z
    ld a,W3D_VDPLET_STATUS_FILE
    ld (w3d_vdplet_status),a
    scf
    ret
@bad_package:
    ld a,W3D_VDPLET_STATUS_PACKAGE
    ld (w3d_vdplet_status),a
    scf
    ret

; Upload the selected package through the generic bounded buffer uploader.
w3d_vdplet_upload_package:
    ld bc,W3D_VDPLET_MODULE_BUFFER
    ld hl,W3D_VDPLET_PACKAGE_ADDRESS
    ld de,W3D_VDPLET_PACKAGE_BYTES
    jp w3d_vdplet_upload_buffer

; BC=destination buffer ID, HL=source address and DE=nonzero byte count. Clear,
; append complete <=4096-byte stock WRITE blocks, then consolidate to the one
; contiguous block required by LOAD/RUN services. Consolidation has no reply;
; the consuming LOAD/RUN is the authoritative allocation/shape check.
w3d_vdplet_upload_buffer:
    ld a,c
    ld (@clear_id+0),a
    ld (@write_id+0),a
    ld (@finish_id+0),a
    ld a,b
    ld (@clear_id+1),a
    ld (@write_id+1),a
    ld (@finish_id+1),a
    ld (w3d_vdplet_upload_source),hl ; ADL24 OK: destination is dl storage.
    push de
    pop hl
    ld bc,0
    or a
    sbc hl,bc
    jp z,@bad_size
    push de
    ld hl,@clear
    ld bc,@clear_end-@clear
    rst.lil 18h
    pop de
    ld (w3d_vdplet_upload_remaining),de ; ADL24 OK: destination is dl storage.
@loop:
    ld hl,(w3d_vdplet_upload_remaining)
    ld de,0
    or a
    sbc hl,de
    jr z,@consolidate
    ld hl,(w3d_vdplet_upload_remaining)
    ld de,W3D_VDPLET_UPLOAD_CHUNK
    or a
    sbc hl,de
    jr c,@use_remaining
    ld bc,W3D_VDPLET_UPLOAD_CHUNK
    jr @chunk_ready
@use_remaining:
    ld bc,(w3d_vdplet_upload_remaining)
@chunk_ready:
    ld (w3d_vdplet_upload_chunk),bc ; ADL24 OK: destination is dl storage.
    ld a,c
    ld (@length+0),a
    ld a,b
    ld (@length+1),a
    ld hl,@write
    ld bc,@write_end-@write
    rst.lil 18h
    ld hl,(w3d_vdplet_upload_source)
    ld bc,(w3d_vdplet_upload_chunk)
    rst.lil 18h
    ld hl,(w3d_vdplet_upload_source)
    ld de,(w3d_vdplet_upload_chunk)
    add hl,de
    ld (w3d_vdplet_upload_source),hl ; ADL24 OK: destination is dl storage.
    ld hl,(w3d_vdplet_upload_remaining)
    or a
    sbc hl,de
    ld (w3d_vdplet_upload_remaining),hl ; ADL24 OK: destination is dl storage.
    jr @loop
@consolidate:
    ld hl,@finish
    ld bc,@finish_end-@finish
    rst.lil 18h
    or a
    ret
@bad_size:
    ld a,W3D_VDPLET_STATUS_PACKAGE
    ld (w3d_vdplet_status),a
    scf
    ret
@clear:
    db 23,0,0a0h
@clear_id:
    dw 0
    db 2
@clear_end:
@write:
    db 23,0,0a0h
@write_id:
    dw 0
    db 0
@length:
    dw 0
@write_end:
@finish:
    db 23,0,0a0h
@finish_id:
    dw 0
    db 14
@finish_end:

; BC=destination buffer ID and DE=nonzero 24-bit byte count. Construct a
; contiguous zero-filled VDP buffer without reserving the complete object in
; eZ80 RAM. LOAD has already copied the module into VDP-owned memory before
; this helper is used, so its former package staging page is safe scratch.
; Reusing that one 4096-byte page for every stock WRITE keeps the 92 KiB
; production workspace out of the application's address-space budget.
w3d_vdplet_create_zero_buffer:
    ld a,c
    ld (@zero_clear_id+0),a
    ld (@zero_write_id+0),a
    ld (@zero_finish_id+0),a
    ld a,b
    ld (@zero_clear_id+1),a
    ld (@zero_write_id+1),a
    ld (@zero_finish_id+1),a
    push de
    pop hl
    ld bc,0
    or a
    sbc hl,bc
    jp z,@bad_zero_size
    ld (w3d_vdplet_upload_remaining),de ; ADL24 OK: dl storage.

    ld hl,W3D_VDPLET_PACKAGE_ADDRESS
    xor a
    ld (hl),a
    ld de,W3D_VDPLET_PACKAGE_ADDRESS+1
    ld bc,W3D_VDPLET_UPLOAD_CHUNK-1
    ldir

    ld hl,@zero_clear
    ld bc,@zero_clear_end-@zero_clear
    rst.lil 18h
@zero_loop:
    ld hl,(w3d_vdplet_upload_remaining)
    ld de,0
    or a
    sbc hl,de
    jr z,@zero_consolidate
    ld hl,(w3d_vdplet_upload_remaining)
    ld de,W3D_VDPLET_UPLOAD_CHUNK
    or a
    sbc hl,de
    jr c,@zero_use_remaining
    ld bc,W3D_VDPLET_UPLOAD_CHUNK
    jr @zero_chunk_ready
@zero_use_remaining:
    ld bc,(w3d_vdplet_upload_remaining)
@zero_chunk_ready:
    ld (w3d_vdplet_upload_chunk),bc ; ADL24 OK: dl storage.
    ld a,c
    ld (@zero_length+0),a
    ld a,b
    ld (@zero_length+1),a
    ld hl,@zero_write
    ld bc,@zero_write_end-@zero_write
    rst.lil 18h
    ld hl,W3D_VDPLET_PACKAGE_ADDRESS
    ld bc,(w3d_vdplet_upload_chunk)
    rst.lil 18h
    ld hl,(w3d_vdplet_upload_remaining)
    ld de,(w3d_vdplet_upload_chunk)
    or a
    sbc hl,de
    ld (w3d_vdplet_upload_remaining),hl ; ADL24 OK: dl storage.
    jr @zero_loop
@zero_consolidate:
    ld hl,@zero_finish
    ld bc,@zero_finish_end-@zero_finish
    rst.lil 18h
    or a
    ret
@bad_zero_size:
    ld a,W3D_VDPLET_STATUS_PACKAGE
    ld (w3d_vdplet_status),a
    scf
    ret
@zero_clear:
    db 23,0,0a0h
@zero_clear_id:
    dw 0
    db 2
@zero_clear_end:
@zero_write:
    db 23,0,0a0h
@zero_write_id:
    dw 0
    db 0
@zero_length:
    dw 0
@zero_write_end:
@zero_finish:
    db 23,0,0a0h
@zero_finish_id:
    dw 0
    db 14
@zero_finish_end:

; LOAD the consolidated package and retain only the fresh nonzero handle.
w3d_vdplet_load_module:
    ld hl,W3D_VDPLET_PACKAGE_BYTES
    ld (@package_bytes),hl ; ADL24 OK: low three bytes of allocated u32.
    xor a
    ld (@package_bytes+3),a
    ld a,W3D_VDPL_REPLY_LOADED
    ld hl,@token
    call w3d_vdplet_arm_request
    ret c
    ld hl,@packet
    ld bc,@end-@packet
    rst.lil 18h
    call w3d_vdplet_wait_reply
    ret c
    ld a,l
    or h
    jr z,@bad_handle
    ld a,l
    ld (w3d_vdplet_handle+0),a
    ld a,h
    ld (w3d_vdplet_handle+1),a
    or a
    ret
@bad_handle:
    ld a,W3D_VDPLET_STATUS_PROTOCOL
    ld (w3d_vdplet_status),a
    scf
    ret
@packet:
    db 23,0,W3D_VDPL_SELECTOR
    dw 14
    db W3D_VDPL_PROTOCOL,W3D_VDPL_OP_LOAD
@token:
    dw 0
    db 1,0
    dw W3D_VDPLET_MODULE_BUFFER
@package_bytes:
    ds 4
    dw 0
@end:

; BC=entry and DE=argument buffer ID. Arm and emit a requested RUN without
; waiting; callers use w3d_vdplet_wait_run when their ownership model permits.
w3d_vdplet_send_run:
    ld a,(w3d_vdplet_handle+0)
    ld (@handle+0),a
    ld a,(w3d_vdplet_handle+1)
    ld (@handle+1),a
    ld a,c
    ld (@entry+0),a
    ld a,b
    ld (@entry+1),a
    ld a,e
    ld (@arguments+0),a
    ld a,d
    ld (@arguments+1),a
    ld a,W3D_VDPL_REPLY_DONE
    ld hl,@token
    call w3d_vdplet_arm_request
    ret c
    ld hl,@packet
    ld bc,@end-@packet
    rst.lil 18h
    or a
    ret
@packet:
    db 23,0,W3D_VDPL_SELECTOR
    dw 12
    db W3D_VDPL_PROTOCOL,W3D_VDPL_OP_RUN
@token:
    dw 0
    db 1,0
@handle:
    dw 0
@entry:
    dw 0
@arguments:
    dw 0
@end:

w3d_vdplet_wait_run:
    call w3d_vdplet_wait_reply
    ret c
    ld a,h
    or l
    ret z
    ld a,W3D_VDPLET_STATUS_RUNTIME
    ld (w3d_vdplet_status),a
    scf
    ret

; Unload only our saved live handle. DONE proves release. ERROR provenance is
; ambiguous (runtime admission or native FINI), so INFO2 establishes whether
; the owned handle remains before any caller-owned buffer can be cleared.
w3d_vdplet_unload_module:
    ld a,(w3d_vdplet_handle+0)
    ld b,a
    ld (@handle+0),a
    ld a,(w3d_vdplet_handle+1)
    ld (@handle+1),a
    or b
    ret z
    ld a,W3D_VDPL_REPLY_DONE
    ld hl,@token
    call w3d_vdplet_arm_request
    ret c
    ld hl,@packet
    ld bc,@end-@packet
    rst.lil 18h
    call w3d_vdplet_wait_reply
    jr nc,@released
    ld a,(w3d_vdplet_status)
    cp W3D_VDPLET_STATUS_RUNTIME
    ret nz
    ld a,(w3d_vdplet_last_value+0)
    ld (w3d_vdplet_native_error+0),a
    ld a,(w3d_vdplet_last_value+1)
    ld (w3d_vdplet_native_error+1),a
    call w3d_vdplet_query_slot
    ret c
    ld a,h
    or l
    jr z,@released_with_error
; The same handle means admission was rejected or FINI left the slot live.
; Any different nonzero handle is also ownership ambiguity; retain our saved
; handle and all referenced storage, and report protocol failure.
    ld a,(w3d_vdplet_handle+0)
    cp l
    jr nz,@foreign_slot
    ld a,(w3d_vdplet_handle+1)
    cp h
    jr nz,@foreign_slot
    ld a,W3D_VDPLET_STATUS_RUNTIME
    ld (w3d_vdplet_status),a
    scf
    ret
@foreign_slot:
    ld a,W3D_VDPLET_STATUS_PROTOCOL
    ld (w3d_vdplet_status),a
    scf
    ret
@released_with_error:
    xor a
    ld (w3d_vdplet_handle+0),a
    ld (w3d_vdplet_handle+1),a
    ld a,W3D_VDPLET_STATUS_RUNTIME
    ld (w3d_vdplet_status),a
    scf
    ret
@released:
    ld a,h
    or l
    jr nz,@bad_done
    xor a
    ld (w3d_vdplet_handle+0),a
    ld (w3d_vdplet_handle+1),a
    or a
    ret
@bad_done:
    ld a,W3D_VDPLET_STATUS_PROTOCOL
    ld (w3d_vdplet_status),a
    scf
    ret
@packet:
    db 23,0,W3D_VDPL_SELECTOR
    dw 8
    db W3D_VDPL_PROTOCOL,W3D_VDPL_OP_UNLOAD
@token:
    dw 0
    db 1,0
@handle:
    dw 0
@end:

; Clear only buffers allocated by the Wolf VDPlet client. Resident game assets
; and audio buffers belong to their existing loaders and are untouched.
w3d_vdplet_clear_owned_buffers:
    ld hl,@commands
    ld bc,@end-@commands
    rst.lil 18h
    ret
@commands:
    db 23,0,0a0h
    dw W3D_VDPLET_MODULE_BUFFER
    db 2
    db 23,0,0a0h
    dw W3D_VDPLET_WORKSPACE_BUFFER
    db 2
    db 23,0,0a0h
    dw W3D_VDPLET_UPDATE_BUFFER
    db 2
    db 23,0,0a0h
    dw W3D_VDPLET_CONFIG_BUFFER
    db 2
    db 23,0,0a0h
    dw W3D_VDPLET_ARGUMENT_BUFFER
    db 2
@end:

; Finite startup foundation: identify the runtime, upload and LOAD the package.
w3d_vdplet_open:
    call w3d_vdplet_initialize
    ld a,W3D_VDPLET_STAGE_DISCOVER
    ld (w3d_vdplet_stage),a
    call w3d_vdplet_discover
    ret c
    ld a,W3D_VDPLET_STAGE_IDENTITY
    ld (w3d_vdplet_stage),a
    call w3d_vdplet_query_identity
    ret c
    ld a,W3D_VDPLET_STAGE_CAPABILITIES
    ld (w3d_vdplet_stage),a
    call w3d_vdplet_query_capabilities
    ret c
    ld a,W3D_VDPLET_STAGE_SLOT
    ld (w3d_vdplet_stage),a
    call w3d_vdplet_require_empty_slot
    ret c
    ld a,W3D_VDPLET_STAGE_READ_PACKAGE
    ld (w3d_vdplet_stage),a
    call w3d_vdplet_read_package
    ret c
    ld a,W3D_VDPLET_STAGE_UPLOAD_PACKAGE
    ld (w3d_vdplet_stage),a
    call w3d_vdplet_upload_package
    ret c
    ld a,W3D_VDPLET_STAGE_LOAD_MODULE
    ld (w3d_vdplet_stage),a
    call w3d_vdplet_load_module
    ret

; Orderly shutdown. Preserve a failure carry/status from UNLOAD, but always
; clear the application's ordinary staging/work buffers afterward.
w3d_vdplet_close:
    ld a,(w3d_vdplet_transaction_pending)
    or a
    jr z,@unload
    ld a,W3D_VDPLET_STATUS_TIMEOUT
    ld (w3d_vdplet_status),a
    scf
    ret
@unload:
    call w3d_vdplet_unload_module
    jr nc,@clear_ok
    ld a,(w3d_vdplet_handle+0)
    ld b,a
    ld a,(w3d_vdplet_handle+1)
    or b
    jr z,@clear_released_error
; A live handle means storage and callback ownership remain unresolved. The
; bytewise nonzero test cleared carry, so explicitly restore the failure flag.
    scf
    ret
@clear_released_error:
    push af
    call w3d_vdplet_clear_owned_buffers
    pop af
    scf
    ret
@clear_ok:
    call w3d_vdplet_clear_owned_buffers
    or a
    ret

w3d_vdplet_package_filename:
    asciz "wolf3d.vdpl"

w3d_vdplet_reply_ready:
    db 0
w3d_vdplet_callback_error:
    db 0
w3d_vdplet_status:
    db W3D_VDPLET_STATUS_OK
w3d_vdplet_expected_kind:
    db 0
w3d_vdplet_transaction_pending:
    db 0
w3d_vdplet_token:
    dw 0
w3d_vdplet_handle:
    dw 0
w3d_vdplet_last_value:
    dw 0
w3d_vdplet_native_error:
    dw 0
w3d_vdplet_stage:
    db W3D_VDPLET_STAGE_NONE
w3d_vdplet_mailbox:
    ds 10
w3d_vdplet_snapshot:
    ds 10
w3d_vdplet_sysvars:
    dl 0
w3d_vdplet_wait_started:
    dl 0
w3d_vdplet_upload_source:
    dl 0
w3d_vdplet_upload_remaining:
    dl 0
w3d_vdplet_upload_chunk:
    dl 0
