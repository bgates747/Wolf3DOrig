; =============================================================================
; Wolf3DOrig application identity and renderer compatibility handshake.
;
; Application, Wolf VDP extension, upstream VDP, and wire ABI versions evolve
; independently. Compatibility is decided only from the explicit W3DV reply:
; matching ABI major, sufficient ABI minor, and every required capability.
; Semantic versions remain human-readable provenance.
; =============================================================================

W3D_APP_VERSION_MAJOR:              equ 0
W3D_APP_VERSION_MINOR:              equ 1
W3D_APP_VERSION_PATCH:              equ 0
W3D_APP_VERSION_PRERELEASE:         equ 1 ; 0=release, 1=alpha
W3D_APP_VERSION_PRERELEASE_NUMBER:  equ 1

; Single authoritative human-readable application identity. Startup,
; application shell, future splash screens, and diagnostics all reference
; this byte string instead of maintaining copies that can drift.
w3d_app_version_text:
    db "Wolf3DOrig App 0.1.0 Alpha 1",0

W3D_VERSION_REPLY_SIZE:             equ 20
W3D_VERSION_REPLY_SCHEMA:           equ 1
W3D_RENDERER_ABI_REQUIRED_MAJOR:    equ 1
W3D_RENDERER_ABI_REQUIRED_MINOR:    equ 0

W3D_CAP_WORLD_RENDERER:             equ 0001h
W3D_CAP_ACTORS:                     equ 0002h
W3D_CAP_HUD_VIEW_WEAPON:            equ 0004h
W3D_CAP_ASYNC_RENDER:               equ 0008h
W3D_CAP_DEATH_FIZZLE:               equ 0010h
W3D_CAP_ENHANCED_AUDIO:             equ 0020h
W3D_REQUIRED_CAPABILITIES:          equ 003fh

W3D_VERSION_OFF_SCHEMA:             equ 4
W3D_VERSION_OFF_ABI_MAJOR:          equ 5
W3D_VERSION_OFF_ABI_MINOR:          equ 6
W3D_VERSION_OFF_CAPABILITIES:       equ 7
W3D_VERSION_OFF_EXTENSION_MAJOR:    equ 9
W3D_VERSION_OFF_EXTENSION_MINOR:    equ 10
W3D_VERSION_OFF_EXTENSION_PATCH:    equ 11
W3D_VERSION_OFF_PRERELEASE:         equ 12
W3D_VERSION_OFF_PRERELEASE_NUMBER:  equ 13
W3D_VERSION_OFF_UPSTREAM_MAJOR:     equ 14
W3D_VERSION_OFF_UPSTREAM_MINOR:     equ 15
W3D_VERSION_OFF_UPSTREAM_PATCH:     equ 16
W3D_VERSION_OFF_RESERVED:           equ 17
W3D_VERSION_OFF_COOKIE:             equ 18

W3D_VERSION_STATUS_OK:              equ 0
W3D_VERSION_STATUS_TIMEOUT:         equ 1
W3D_VERSION_STATUS_MALFORMED:       equ 2
W3D_VERSION_STATUS_INCOMPATIBLE:    equ 3

w3d_version_reply_cookie:           equ 0a55ah
w3d_version_timeout_ticks:          equ 120 ; one second at the MOS 120 Hz clock

; Called by the MOS UART callback with IX -> candidate packet. Carry is set
; when a W3DV packet was consumed. The fixed cookie distinguishes a complete
; reply without placing unsafe payload bytes after the query subcommand.
; The callback itself preserves all interrupted registers.
w3d_try_capture_version_packet:
    ld a,(ix+0)
    cp 'W'
    jr nz,@not_version
    ld a,(ix+1)
    cp '3'
    jr nz,@not_version
    ld a,(ix+2)
    cp 'D'
    jr nz,@not_version
    ld a,(ix+3)
    cp 'V'
    jr nz,@not_version

    ld a,(ix+W3D_VERSION_OFF_COOKIE+0)
    cp w3d_version_reply_cookie & 0ffh
    jr nz,@consume_only
    ld a,(ix+W3D_VERSION_OFF_COOKIE+1)
    cp w3d_version_reply_cookie >> 8
    jr nz,@consume_only

    push ix
    pop hl
    ld de,w3d_version_record
    ld bc,W3D_VERSION_REPLY_SIZE
    ldir
    ld a,1
    ld (w3d_version_ready),a

@consume_only:
; Prevent MOS from interpreting the synthetic keycode payload as a key event.
    xor a
    ld (ix+0),a
    ld (ix+1),a
    ld (ix+2),a
    ld (ix+3),a
    scf
    ret

@not_version:
    or a
    ret

; Send payload-free subcommand 40 and wait at most one real second for the
; callback. Carry is clear only when w3d_validate_version_record accepts the
; reply.
w3d_query_renderer_compatibility:
    xor a
    ld (w3d_version_ready),a
    ld a,W3D_VERSION_STATUS_TIMEOUT
    ld (w3d_version_status),a

    MOSCALL mos_sysvars
    ld (w3d_version_sysvars_pointer),ix
    ld hl,(ix+sysvar_time)
    ld (w3d_version_query_started),hl

    ld hl,@command
    ld bc,@end-@command
    rst.lil 18h

@wait:
    ld a,(w3d_version_ready)
    or a
    jp nz,w3d_validate_version_record

    ld ix,(w3d_version_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld de,(w3d_version_query_started)
    or a
    sbc hl,de
    ld de,w3d_version_timeout_ticks
    or a
    sbc hl,de
    jr c,@wait
    scf
    ret

@command:
    db 23,0,0a0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 04ah,40
@end:

; Validate a captured response. This routine is deliberately independent of
; transport/timing so direct eZ80 regression can exercise malformed, future-
; compatible, and incompatible records without a custom test VDP.
w3d_validate_version_record:
    ld a,(w3d_version_record+0)
    cp 'W'
    jr nz,@malformed
    ld a,(w3d_version_record+1)
    cp '3'
    jr nz,@malformed
    ld a,(w3d_version_record+2)
    cp 'D'
    jr nz,@malformed
    ld a,(w3d_version_record+3)
    cp 'V'
    jr nz,@malformed
    ld a,(w3d_version_record+W3D_VERSION_OFF_SCHEMA)
    cp W3D_VERSION_REPLY_SCHEMA
    jr nz,@malformed
    ld a,(w3d_version_record+W3D_VERSION_OFF_RESERVED)
    or a
    jr nz,@malformed
    ld a,(w3d_version_record+W3D_VERSION_OFF_COOKIE+0)
    cp w3d_version_reply_cookie & 0ffh
    jr nz,@malformed
    ld a,(w3d_version_record+W3D_VERSION_OFF_COOKIE+1)
    cp w3d_version_reply_cookie >> 8
    jr nz,@malformed

    ld a,(w3d_version_record+W3D_VERSION_OFF_ABI_MAJOR)
    cp W3D_RENDERER_ABI_REQUIRED_MAJOR
    jr nz,@incompatible
    ld a,(w3d_version_record+W3D_VERSION_OFF_ABI_MINOR)
    cp W3D_RENDERER_ABI_REQUIRED_MINOR
    jr c,@incompatible

    ld a,(w3d_version_record+W3D_VERSION_OFF_CAPABILITIES+0)
    and W3D_REQUIRED_CAPABILITIES & 0ffh
    cp W3D_REQUIRED_CAPABILITIES & 0ffh
    jr nz,@incompatible
    ld a,(w3d_version_record+W3D_VERSION_OFF_CAPABILITIES+1)
    and W3D_REQUIRED_CAPABILITIES >> 8
    cp W3D_REQUIRED_CAPABILITIES >> 8
    jr nz,@incompatible

    xor a
    ld (w3d_version_status),a
    or a
    ret

@malformed:
    ld a,W3D_VERSION_STATUS_MALFORMED
    ld (w3d_version_status),a
    scf
    ret

@incompatible:
    ld a,W3D_VERSION_STATUS_INCOMPATIBLE
    ld (w3d_version_status),a
    scf
    ret

w3d_version_ready:
    db 0
w3d_version_status:
    db W3D_VERSION_STATUS_TIMEOUT
w3d_version_record:
    ds W3D_VERSION_REPLY_SIZE
w3d_version_query_started:
    dl 0
w3d_version_sysvars_pointer:
    dl 0
