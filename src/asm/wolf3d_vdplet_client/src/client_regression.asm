; Finite full-MOS regression for the production Wolf VDPlet client foundation.
; It uses the accepted copied-pixel bounded module and scene, but every runtime
; transaction is issued and validated by wolf3d_vdplet_client.inc.
    .assume adl=1
    .org 040000h
    jp start
    .align 64
    db "MOS",0,1

mos_getkey:      equ 00h
mos_load:        equ 01h
mos_save:        equ 02h
mos_sysvars:     equ 08h
mos_setkbvector: equ 01dh
sysvar_time:     equ 00h
sysvar_scrMode:  equ 027h

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

; This finite fixture does not enable the optional full-game profiler.
    macro W3D_PROFILE_CALL target
@disabled:
    endmacro

    include "wolf3d_vdplet_package.inc"
    include "fixture_sizes.inc"
    include "wolf3d_vdplet_client.inc"

    macro UPLOAD_FILE filename, bytecount, bufferid
        ld hl,filename
        ld de,W3D_VDPLET_PACKAGE_ADDRESS
        ld bc,bytecount
        push ix
        push iy
        MOSCALL mos_load
        pop iy
        pop ix
        or a
        jp nz,fixture_file_failed
        ld bc,bufferid
        ld hl,W3D_VDPLET_PACKAGE_ADDRESS
        ld de,bytecount
        call w3d_vdplet_upload_buffer
        jp c,fixture_failed
    endmacro

start:
    push af
    push bc
    push de
    push ix
    push iy
    ld (fixture_saved_sp),sp
    xor a
    ld (fixture_callback_installed),a
    ld (fixture_result_code),a

    MOSCALL mos_sysvars
    ld a,(ix+sysvar_scrMode)
    and 07fh
    ld (fixture_saved_mode),a

    ld hl,fixture_packet_callback
    ld c,0
    MOSCALL mos_setkbvector
    ld a,1
    ld (fixture_callback_installed),a
    ei

    call w3d_vdplet_open
    jp c,fixture_failed

    UPLOAD_FILE fixture_workspace_name, W3D_FIXTURE_WORKSPACE_BYTES, W3D_VDPLET_WORKSPACE_BUFFER
    UPLOAD_FILE fixture_map_name, W3D_FIXTURE_MAP_BYTES, W3D_VDPLET_UPDATE_BUFFER
    UPLOAD_FILE fixture_textures_name, W3D_FIXTURE_TEXTURE_BYTES, W3D_VDPLET_CONFIG_BUFFER
    UPLOAD_FILE fixture_config_name, W3D_FIXTURE_CONFIG_BYTES, W3D_VDPLET_ARGUMENT_BUFFER

    ld hl,fixture_mode_packet
    ld bc,fixture_mode_packet_end-fixture_mode_packet
    rst.lil 18h

    ld bc,0
    ld de,W3D_VDPLET_ARGUMENT_BUFFER
    call w3d_vdplet_send_run
    jp c,fixture_failed
    call w3d_vdplet_wait_run
    jp c,fixture_failed

    ld bc,1
    ld de,W3D_VDPLET_ARGUMENT_BUFFER
    call w3d_vdplet_send_run
    jp c,fixture_failed
    call w3d_vdplet_wait_run
    jp c,fixture_failed

    ld hl,fixture_present_packet
    ld bc,fixture_present_packet_end-fixture_present_packet
    rst.lil 18h
    MOSCALL mos_getkey

    call w3d_vdplet_close
    jr c,fixture_failed_after_close
    xor a
    ld (fixture_result_code),a
    jr fixture_safe_finish

fixture_file_failed:
    ld a,W3D_VDPLET_STATUS_FILE
    ld (w3d_vdplet_status),a

fixture_failed:
    ld a,1
    ld (fixture_result_code),a
    ld a,(w3d_vdplet_transaction_pending)
    or a
    jr nz,fixture_ambiguous
    call w3d_vdplet_close
    jr c,fixture_failed_after_close
    jr fixture_safe_finish

fixture_failed_after_close:
    ld a,1
    ld (fixture_result_code),a
    ld a,(w3d_vdplet_transaction_pending)
    or a
    jr nz,fixture_ambiguous
    ld a,(w3d_vdplet_handle+0)
    ld b,a
    ld a,(w3d_vdplet_handle+1)
    or b
    jr nz,fixture_ambiguous

fixture_safe_finish:
    call fixture_remove_callback
    call fixture_restore_mode
    call fixture_write_result
    ld a,(fixture_result_code)
; MOS receives a 24-bit HL return status in ADL mode. Zero HLU as well as H so
; a successful result cannot inherit a false error from mos_save.
    ld hl,0
    ld l,a
    jr fixture_finish

; A timeout or ownership ambiguity is deliberately not disguised as cleanup.
; Keep the callback and referenced storage alive for a late matching response.
fixture_ambiguous:
    ld a,2
    ld (fixture_result_code),a
    call fixture_write_result
@hold:
    jr @hold

fixture_finish:
    ld (fixture_exit_code),hl
    ld sp,(fixture_saved_sp)
    pop iy
    pop ix
    pop de
    pop bc
    pop af
    ld hl,(fixture_exit_code)
    ret

; The combined MOS hook consumes only VDPL records. Ordinary keyboard traffic,
; including the injected acknowledgment key, remains untouched for MOS.
fixture_packet_callback:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    push de
    pop ix
    call w3d_vdplet_try_capture_packet
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret

fixture_remove_callback:
    ld a,(fixture_callback_installed)
    or a
    ret z
    xor a
    ld (fixture_callback_installed),a
    ld hl,0
    ld c,0
    MOSCALL mos_setkbvector
    ret

fixture_restore_mode:
    ld a,(fixture_saved_mode)
    ld (fixture_restore_packet+1),a
    ld hl,fixture_restore_packet
    ld bc,fixture_restore_packet_end-fixture_restore_packet
    rst.lil 18h
    ret

fixture_write_result:
    ld a,(fixture_result_code)
    ld (fixture_result+4),a
    ld a,(w3d_vdplet_status)
    ld (fixture_result+5),a
    ld a,(w3d_vdplet_transaction_pending)
    ld (fixture_result+6),a
    ld a,(w3d_vdplet_callback_error)
    ld (fixture_result+7),a
    ld a,(w3d_vdplet_handle+0)
    ld (fixture_result+8),a
    ld a,(w3d_vdplet_handle+1)
    ld (fixture_result+9),a
    ld a,(w3d_vdplet_native_error+0)
    ld (fixture_result+10),a
    ld a,(w3d_vdplet_native_error+1)
    ld (fixture_result+11),a
    ld a,(w3d_vdplet_token+0)
    ld (fixture_result+12),a
    ld a,(w3d_vdplet_token+1)
    ld (fixture_result+13),a
    ld hl,fixture_result_name
    ld de,fixture_result
    ld bc,fixture_result_end-fixture_result
    MOSCALL mos_save
    ret

fixture_mode_packet:
    db 22,136,23,1,0
fixture_mode_packet_end:
fixture_present_packet:
    db 23,0,0c3h
fixture_present_packet_end:
fixture_restore_packet:
    db 22,0,23,1,1,12,16
fixture_restore_packet_end:

fixture_workspace_name: asciz "workspace.bin"
fixture_map_name:       asciz "map.bin"
fixture_textures_name:  asciz "textures.bin"
fixture_config_name:    asciz "config.bin"
fixture_result_name:    asciz "client.dat"

fixture_callback_installed: db 0
fixture_saved_mode:          db 0
fixture_result_code:         db 0
fixture_saved_sp:            dl 0
fixture_exit_code:           dl 0
fixture_result:
    db "WVPC"
    ds 10
    dw 1                    ; result schema
fixture_result_end:

; Owned storage covers the largest uploaded fixture file, the module and
; shared client's4096-byte zero-buffer scratch. Never stage over live code.
    .align 4
W3D_VDPLET_PACKAGE_ADDRESS:
fixture_package_storage:
    ; The builder emits exactly W3D_FIXTURE_STORAGE_BYTES zero bytes.
    ; Use explicit data: DS is omitted at EOF and otherwise filled with FF.
    incbin "fixture_storage.bin"
fixture_package_storage_end:
