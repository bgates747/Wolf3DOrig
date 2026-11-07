; =============================================================================
; Wolf3D eZ80 client -- the real, growing game application.
;
; Distinct from its two siblings under src/asm/: wolf3d_hello (raw wire-
; protocol smoke test for the BUFFERED_WOLF3D VDP opcode) and wolf3d_ai (the
; sight/collision logic's own prototyping + regression-test project, whose
; validated reusable API graduated into this app once that work was done --
; see wolf3d_world.inc/wolf3d_math.inc/wolf3d_sight.inc below).
;
; The original player's-first-position render fixture (Author decision
; 2026-07-31) has grown into the application shell and complete shareware-floor
; loader. It loads each floor's real wall/door and static-sprite art through the
; vendored AGNB loader, uploads the runtime W3L tilemap, and drives the settled
; BUFFERED_WOLF3D wire protocol with callback-gated rendering. Player collision,
; eZ80-authoritative moving doors, blocking decorations, and mutable pickup/HUD
; state are live. The authoritative actor pool advances original-timed path
; patrols, awareness/reaction, ordinary chase/dodge movement, ranged and dog
; attack chains, player damage, all four ordinary player weapons, actor pain/
; death, scores and drops, and the original ordinary death/fizzle/respawn loop.
; Native-rate digitized combat, pickup, door, and environment effects are
; loaded through AGNB and arbitrated once per caught-up simulation quantum.
; Episode 1 floor routing, original-looking floor intermissions, and the E1L9
; victory return are live. Bosses and the intermission's original count-up/
; bonus animation are live; paid-episode projectile actors remain future work
; and are not present in the WL1 maps. Original
; IMF register streams drive a nonblocking nine-voice VDP music translation.
; =============================================================================

mos_getkey:      equ 00h
mos_load:        equ 01h
mos_sysvars:     equ 08h
mos_fopen:       equ 0Ah
mos_fclose:      equ 0Bh
mos_fread:       equ 1Ah
mos_fwrite:      equ 1Bh
mos_setkbvector: equ 1Dh
mos_getkbmap:    equ 1Eh
mos_clearvdpflags: equ 40h
mos_waitforvdpflags: equ 41h
sysvar_time:     equ 00h
sysvar_scrMode:  equ 27h

vdp_pflag_mode:                 equ 00010000b
W3D_MODE_FENCE_WAIT_PASSES:     equ 10
fa_write:                       equ 02h
fa_create_always:               equ 08h

    MACRO MOSCALL function
        ld a,function
        rst.lil 08h
    ENDMACRO

    .assume adl=1
    .org 040000h

    jp start

    .align 64
    .db "MOS",0,1

    include "wolf3d_backend.inc"
    include "wolf3d_start.inc"
WP_MODE: equ 2
    include "wolf3d_sight.inc"
    include "agnb_dependencies.inc"
    include "agnb_api.inc"
    include "wolf3d_audio_assets.inc"
    include "wolf3d_music_assets.inc"
    include "wolf3d_shell_assets.inc"
    include "wolf3d_version.inc"
    include "wolf3d_music.inc"
    include "wolf3d_config.inc"
    include "wolf3d_highscores.inc"
    include "wolf3d_shell.inc"
    include "wolf3d_intermission.inc"
    include "wolf3d_audio.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_render_async.inc"
    .if W3D_RENDER_BACKEND
    include "wolf3d_vdplet_contract.inc"
    include "wolf3d_vdplet_package.inc"
    include "wolf3d_vdplet_client.inc"
    .endif
    include "wolf3d_actors.inc"
    .if W3D_RENDER_BACKEND
    include "wolf3d_vdplet_batch.inc"
    include "wolf3d_vdplet_backend.inc"
    .endif
    include "wolf3d_areas.inc"
    include "wolf3d_actor_sim.inc"
    include "wolf3d_victory.inc"
    include "wolf3d_motion.inc"
    include "wolf3d_panel_music.inc"
    include "wolf3d_player_combat.inc"
    include "wolf3d_death.inc"
    include "wolf3d_audio_spatial.inc"
    include "wolf3d_level_loader.inc"
    include "wolf3d_save.inc"
    include "wolf3d_save_slots.inc"

start:
    push af
    push bc
    push de
    push ix
    push iy
    call wpl3_init
    call main
    call wp_loading_save
    call wpl3_save

exit:
    pop iy
    pop ix
    pop de
    pop bc
    pop af
    ld hl,0
    ret

assets_filename:
    db "tiles.agnb",0
sprites_filename:
    db "sprites.agnb",0
hud_filename:
    db "hud.agnb",0
sfx_filename:
    db "sfx.agnb",0
shell_filename:
    db "shell.agnb",0
help_filename:
    db "help.agnb",0
end_filename:
    db "end.agnb",0
loading_msg:
    db "Loading floor wall/door textures (tiles.agnb)",0
loading_sprites_msg:
    db "Loading floor static sprite art (sprites.agnb)",0
loading_hud_msg:
    db "Loading original in-game status panel (hud.agnb)",0
loading_sfx_msg:
    db "Loading native-rate Wolf3D sound effects (sfx.agnb)",0
loading_shell_msg:
    db "Loading original Wolf3D application shell (shell.agnb)",0
rendering_msg:
    db "Uploading tilemap and rendering initial floor view",0
level_state_loading_msg:
    db "Loading runtime level state",0
level_state_error_msg:
    db "Runtime level-state load or validation failed.",0
level_state_file_error_msg:
    db "Runtime level-state file error.",0
level_state_magic_error_msg:
    db "Runtime level-state magic error.",0
level_state_version_error_msg:
    db "Runtime level-state version error.",0
level_state_id_error_msg:
    db "Runtime level-state level/difficulty error.",0
level_state_count_error_msg:
    db "Runtime level-state capacity error.",0
level_state_bounds_error_msg:
    db "Runtime level-state layout/size error.",0
assets_error_msg:
    db "AGNB texture load failed; render not submitted.",0
sfx_error_msg:
    db "AGNB sound load incomplete; continuing with available effects.",0
audio_install_error_msg:
    db "VDP audio procedure installation timed out.",0
gallery_msg:
    db "VDP-uploaded texture gallery (one dot per finalized bitmap):",0
gallery_done_msg:
    db "Assets complete. Press any key to enter the Wolf3D view.",0
vdp_check_msg:
    db "Checking Wolf3DOrig VDP renderer compatibility",0
vdp_check_ok_msg:
    db "Renderer ABI 1.0 and required capabilities confirmed.",0
vdp_check_missing_msg:
    db "Wolf3DOrig VDP extension not found (no W3DV reply).",0
vdp_check_bad_msg:
    db "Incompatible or malformed Wolf3DOrig VDP response.",0
vdp_check_required_msg:
    db "This application requires renderer ABI 1.0 and capabilities 003Fh.",0
vdp_check_return_msg:
    db "Press any key to return safely to MOS.",0
farewell_msg:
    db "Thanks for playing Wolf3DOrig!",10,0
w3d_exit_message_ptr:
    dl farewell_msg

; Select the 320x240x64 double-buffered display before loading the level's
; VDP-resident image set.  Mode 136 must allocate a second 320x240 framebuffer;
; asking for it only after the large tile/sprite/HUD containers have fragmented
; SRAM is both needlessly fragile and, on physical VDPs, intermittently fatal.
; The renderer draws its 256x160 view into the hidden surface; validated W3DR
; completion presents it with C3.
w3d_display_mode_command:
    db 22,8+128             ; MODE 8: 320x240x64, double buffered
w3d_display_mode_command_end:

; These commands must not share the VDU burst containing VDU 22.  The mode
; reply below owns the framebuffer-rebuild boundary; only after it arrives is
; it safe to configure and clear the newly constructed surface.
w3d_display_post_mode_setup:
    db 23,0,$C0,0           ; logical coordinate scaling off
    db 23,1,0               ; cursor off
    db 18,0,128             ; graphics background logical colour 0 (black)
    db 16                   ; clear current graphics draw buffer
w3d_display_post_mode_setup_end:

; Diagnostic gallery setup. Mode 0 leaves ample room for a 4x4 grid of the
; sixteen 64x64 textures without scaling or clipping.
w3d_gallery_setup:
    db 22,0                 ; 640x480, single buffered
    db 23,0,$C0,0           ; logical coordinate scaling off
    db 23,1,0               ; cursor off
    db 18,0,128             ; graphics background logical colour 0 (black)
    db 16                   ; clear visible graphics surface
w3d_gallery_setup_end:

; Preserve the caller's display geometry before either loading gallery or game
; changes it. Wolf3D always restores the same base mode without the caller's
; buffering request: bit 7 is a VDP double-buffer flag, not part of the MOS
; mode number.
w3d_capture_original_screen_mode:
    MOSCALL mos_sysvars
    ld (w3d_sysvars_pointer),ix
    ld a,(ix+sysvar_scrMode)
    and 07Fh
    ld (w3d_restore_mode_command+1),a
    ret

; Return MOS to the display mode from which the game was launched. Clear both
; the text and graphics surfaces so neither the last 3D frame nor stale MOS
; text survives the handoff. VDU 22 remains asynchronous here: do not expose a
; live MOS prompt (and a possible immediate second RUN) until the matching
; mode-reply flag proves framebuffer reconstruction is complete.
w3d_restore_original_screen_mode:
    call w3d_arm_gameplay_mode_fence
    ld hl,w3d_restore_mode_command
    ld bc,w3d_restore_mode_command_end-w3d_restore_mode_command
    rst.lil 18h
    call w3d_wait_for_gameplay_mode
    ret c
    ld hl,w3d_restore_post_mode_command
    ld bc,w3d_restore_post_mode_command_end-w3d_restore_post_mode_command
    rst.lil 18h
    or a
    ret

w3d_restore_mode_command:
    db 22,0                 ; saved base mode, patched during startup
w3d_restore_mode_command_end:
w3d_restore_post_mode_command:
    db 12                   ; CLS: clear text viewport
    db 16                   ; CLG: clear graphics viewport
w3d_restore_post_mode_command_end:

; A mode change is asynchronous: RST 18h returns after queuing VDU 22, while
; the VDP rebuilds its framebuffer and MOS consumes the resulting mode packet.
; Do not issue the first VDPlet discovery command into that ownership window.
; Physical tracing caught the otherwise intermittent failure as a completed
; mode 136 transition followed by MOS mode queries but no D9 arrival; every
; later VDU byte was then stranded even though the eZ80 returned to MOS.
;
; Clear MOS's canonical mode-reply semaphore before emitting VDU 22.
w3d_arm_gameplay_mode_fence:
    ld c,vdp_pflag_mode
    MOSCALL mos_clearvdpflags
    ret

; MOS wait-for-VDP-flags is the authoritative mode-reply fence. One pass has
; its own finite timeout; repeat without clearing so a slow physical mode
; rebuild may still publish the same flag. Carry clear means MOS consumed the
; mode packet. Carry set selects a durable startup error after ten passes.
w3d_wait_for_gameplay_mode:
    push bc
    ld b,W3D_MODE_FENCE_WAIT_PASSES
@wait:
    ld c,vdp_pflag_mode
    MOSCALL mos_waitforvdpflags
    or a
    jr z,@ready
    djnz @wait
    pop bc
    ld hl,w3d_mode_fence_error_msg
    ld (w3d_exit_message_ptr),hl
    scf
    ret
@ready:
    pop bc
    or a
    ret

; Enter gameplay mode without placing any later VDU selector inside the
; asynchronous framebuffer reconstruction window.  A second ordered ingress
; fence proves the post-mode setup was parsed before renderer traffic begins.
w3d_enter_gameplay_display:
    ld a,(w3d_display_acquired)
    or a
    jr nz,@configure
    MOSCALL mos_sysvars
    ld a,(ix+sysvar_scrMode)
    cp 136
    jr z,@mode_ready
    call w3d_arm_gameplay_mode_fence
    ld hl,w3d_display_mode_command
    ld bc,w3d_display_mode_command_end-w3d_display_mode_command
    rst.lil 18h
    call w3d_wait_for_gameplay_mode
    ret c
@mode_ready:
    call wp_settle_display
    ld a,1
    ld (w3d_display_acquired),a
@configure:
    ld hl,w3d_display_post_mode_setup
    ld bc,w3d_display_post_mode_setup_end-w3d_display_post_mode_setup
    rst.lil 18h
    jp w3d_audio_wait_for_vdp_ingress

; Mode 136 is an application-lifetime allocation.  Once acquired, shell,
; intermission, pause, and gameplay owners share the same two physical
; surfaces; later calls above only restore draw-state and never rebuild the
; framebuffer under VDP SRAM pressure.
w3d_display_acquired:
    db 0

w3d_mode_fence_error_msg:
    db "VDP gameplay mode transition did not complete.",10,0

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

; A=W3D_LEVEL_LOAD_* nonzero result. Select a specific fail-closed reason for
; main to print after restoring the caller's MOS mode.
w3d_set_level_load_error:
    cp W3D_LEVEL_LOAD_BOUNDS_ERROR+1
    ld hl,level_state_error_msg
    jr nc,@selected
    dec a
    ld b,a
    add a,a
    add a,b
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_level_error_message_table
    add hl,de
    ld hl,(hl)
@selected:
    ld (w3d_exit_message_ptr),hl
    ret

w3d_level_error_message_table:
    dl level_state_file_error_msg
    dl level_state_magic_error_msg
    dl level_state_version_error_msg
    dl level_state_id_error_msg
    dl level_state_count_error_msg
    dl level_state_bounds_error_msg

; One breadcrumb means one image record was fully streamed, consolidated, and
; finalized as a VDP bitmap by the modern AGNB container loader.
printImageBreadcrumb:
; Select the bitmap ID supplied by the current AGNB metadata. The metadata
; field is u16; inc/dec.s preserves it while forcing HLU to zero.
    ld hl,(agnb_metadata+agnb_meta_bufferId)
    inc hl
    dec.s hl
    call selectBitmap

; Plot the completed 64x64 bitmap unscaled into the current 4x4 gallery cell.
    ld bc,(gallery_x)
    ld de,(gallery_y)
    call plotBitmap

; Advance across four columns, then wrap to the next 64-pixel row.
    ld a,(gallery_column)
    inc a
    cp 4
    jr z,@next_row
    ld (gallery_column),a
    ld hl,(gallery_x)
    ld de,64
    add hl,de
    ld (gallery_x),hl
    jr @breadcrumb
@next_row:
    xor a
    ld (gallery_column),a
    ld hl,0
    ld (gallery_x),hl
    ld hl,(gallery_y)
    ld de,64
    add hl,de
    ld (gallery_y),hl

@breadcrumb:
    ld a,'.'
    rst.lil 10h
    xor a
    ret

initializeTextureGallery:
    xor a
    ld (gallery_column),a
    ld hl,0
    ld (gallery_x),hl
    ld hl,32
    ld (gallery_y),hl
    ret

; Sprite containers can hold hundreds of records. Preserve the same durable
; one-dot-per-finalized-bitmap breadcrumb without issuing off-screen gallery
; plots for each one.
printImageDot:
    jp wp_loading_tick

; Common application-exit predicate. The shell latch covers menus and
; synchronous loaders; once the gameplay keycode callback is installed its
; low-latency render-state latch also preserves a short Escape between polls.
w3d_query_application_exit:
    call w3d_shell_query_exit_request
    ret nz
    ld a,(w3d_exit_requested)
    or a
    ret

; Poll the shared shell keyboard seam at synchronous loading boundaries.
; Once Escape is seen the application-level request remains latched, so every
; later abortable callback returns nonzero even after the physical key lifts.
; All callers ultimately converge on main's mode restoration and farewell.
w3d_poll_application_escape:
    call w3d_query_application_exit
    ret nz
    call w3d_shell_read_keyboard
    bit 0,(ix+14)                 ; Escape
    jr z,@continue
    jp w3d_shell_request_exit
@continue:
    xor a
    ret

; Abortable AGNB image callback used during textual bootstrap loading.
; One dot still means one finalized bitmap; only Escape returns nonzero.
printImageDotAndPollEscape:
    call printImageDot
    ret nz ; failed page update aborts loader
    call w3d_music_service
    jp w3d_poll_application_escape

; One dot means one PCM record was streamed, converted to a VDP sample, and
; admitted to the runtime loaded-sample table. The exact buffer-ID callback
; prevents a malformed or sparse container from making unavailable effects
; appear playable.
printAudioDot:
    ld hl,(agnb_audio_metadata+agnb_audio_meta_bufferId)
    inc hl
    dec.s hl
    call w3d_audio_mark_sample_buffer_loaded
    jp wp_loading_tick

; Preserve the exact loaded-sample bookkeeping before checking Escape.
printAudioDotAndPollEscape:
    call printAudioDot
    ret nz ; failed page update aborts loader
    .if W3D_DIAGNOSTIC_STARTUP_TRACE
    push af
    ld a,(agnb_audio_metadata+agnb_audio_meta_bufferId)
    call w3d_startup_trace_audio_sample
    pop af
    .endif
    call w3d_music_service
    jp w3d_poll_application_escape

; Canonical Agon bitmap-buffer selection. The one-byte padding deliberately
; absorbs HLU from the native-ADL three-byte store; it is outside the command
; length and is never sent to the VDP.
selectBitmap:
    ld (@bufferId),hl
    ld hl,@command
    ld bc,@end-@command
    rst.lil 18h
    ret
@command:
    db 23,27,$20
@bufferId:
    dw 0
@end:
    db 0

; Canonical VDU 25 bitmap plot: absolute foreground bitmap at BC,DE. The
; final padding similarly absorbs DEU from the native-ADL store into @y.
plotBitmap:
    ld (@x),bc
    ld (@y),de
    ld hl,@command
    ld bc,@end-@command
    rst.lil 18h
    ret
@command:
    db 25,$ED              ; bitmap plot ($E8) + absolute foreground (5)
@x:
    dw 0
@y:
    dw 0
@end:
    db 0

gallery_column:
    db 0
gallery_x:
    dl 0
gallery_y:
    dl 32

; A=stage byte. Diagnostic builds emit one existing buffered-debug command to
; reserved buffer D0xx. The VDP consumes the six bytes and prints its normal
; debug line on USB serial; no callback or MOS-visible reply is generated.
; Production compiles every caller and this emitter out.
    .if W3D_DIAGNOSTIC_STARTUP_TRACE
w3d_startup_trace_stage:
    push af
    push bc
    push de
    push hl
    ld (w3d_startup_trace_stage_id),a
    ld hl,w3d_startup_trace_command
    ld bc,w3d_startup_trace_command_end-w3d_startup_trace_command
    rst.lil 18h
    pop hl
    pop de
    pop bc
    pop af
    ret

; A=logical sound ID. D1xx separates finalized PCM records from lifecycle
; stages without requiring any extra parser feature in the diagnostic VDP.
w3d_startup_trace_audio_sample:
    push af
    push bc
    push de
    push hl
    ld (w3d_startup_trace_sample_id),a
    ld hl,w3d_startup_trace_sample_command
    ld bc,w3d_startup_trace_sample_command_end-w3d_startup_trace_sample_command
    rst.lil 18h
    pop hl
    pop de
    pop bc
    pop af
    ret

; A=raw FatFS FRESULT from the failed open. D3xx keeps it separate from the
; D0xx lifecycle and D1xx audio streams.
w3d_startup_trace_fresult:
    push af
    push bc
    push de
    push hl
    ld (w3d_startup_trace_fresult_id),a
    ld hl,w3d_startup_trace_fresult_command
    ld bc,w3d_startup_trace_fresult_command_end-w3d_startup_trace_fresult_command
    rst.lil 18h
    pop hl
    pop de
    pop bc
    pop af
    ret

; HL=zero-terminated filename. Emit D2FE, one D2xx byte per character, D2FF.
; This is deliberately verbose but diagnostic-only and runs solely on failure.
w3d_startup_trace_path:
    push af
    push bc
    push hl
    ld a,0feh
    call w3d_startup_trace_path_byte
@next:
    ld a,(hl)
    or a
    jr z,@end
    call w3d_startup_trace_path_byte
    inc hl
    jr @next
@end:
    ld a,0ffh
    call w3d_startup_trace_path_byte
    pop hl
    pop bc
    pop af
    ret

w3d_startup_trace_path_byte:
    push af
    push bc
    push de
    push hl
    ld (w3d_startup_trace_path_id),a
    ld hl,w3d_startup_trace_path_command
    ld bc,w3d_startup_trace_path_command_end-w3d_startup_trace_path_command
    rst.lil 18h
    pop hl
    pop de
    pop bc
    pop af
    ret

; Emit D2FB, D3xx for FatFS's getcwd result, then its zero-terminated cwd as
; D2 bytes. Keep the direct FatFS macro out of the backend macro definition so
; ordinary builds can discard all diagnostic code before macro expansion.
w3d_startup_trace_emit_cwd:
    push af
    push bc
    push hl
    ld a,0fbh
    call w3d_startup_trace_path_byte
    ld hl,w3d_startup_trace_cwd
    ld bc,w3d_startup_trace_cwd_size
    FFSCALL ffs_getcwd
    call w3d_startup_trace_fresult
    ld hl,w3d_startup_trace_cwd
    call w3d_startup_trace_path
    pop hl
    pop bc
    pop af
    ret

w3d_startup_trace_command:
    db 23,0,0a0h
w3d_startup_trace_stage_id:
    db 0,0d0h
    db 080h
w3d_startup_trace_command_end:
w3d_startup_trace_sample_command:
    db 23,0,0a0h
w3d_startup_trace_sample_id:
    db 0,0d1h
    db 080h
w3d_startup_trace_sample_command_end:
w3d_startup_trace_fresult_command:
    db 23,0,0a0h
w3d_startup_trace_fresult_id:
    db 0,0d3h
    db 080h
w3d_startup_trace_fresult_command_end:
w3d_startup_trace_path_command:
    db 23,0,0a0h
w3d_startup_trace_path_id:
    db 0,0d2h
    db 080h
w3d_startup_trace_path_command_end:
w3d_startup_trace_cwd_size: equ 128
w3d_startup_trace_cwd:
    blkb w3d_startup_trace_cwd_size,0
    .endif

main:
    W3D_STARTUP_TRACE 001h
    ld hl,farewell_msg
    ld (w3d_exit_message_ptr),hl
    call w3d_capture_original_screen_mode
    W3D_STARTUP_TRACE 002h
; Reserve both physical mode-8 surfaces before the first shell bitmap, sound
; sample, or command buffer can allocate VDP SRAM.  This deliberately makes
; mode 136 an application-global resource rather than a gameplay transition.
    W3D_STARTUP_TRACE 00ah
    call w3d_enter_gameplay_display
    jp c,@restore_screen
    W3D_STARTUP_TRACE 00bh
    call w3d_seed_random_from_clock
    call w3d_music_initialize
    W3D_STARTUP_TRACE 003h
    call w3d_audio_initialize
    W3D_STARTUP_TRACE 004h
    call w3d_config_initialize
    W3D_STARTUP_TRACE 005h
    call w3d_main_body
    W3D_STARTUP_TRACE 006h
    call w3d_config_save
    W3D_STARTUP_TRACE 007h
    call w3d_audio_shutdown
    W3D_STARTUP_TRACE 008h
    call w3d_music_shutdown
    W3D_STARTUP_TRACE 009h
@restore_screen:
    call w3d_restore_original_screen_mode
    ld hl,(w3d_exit_message_ptr)
    call printString
    ret

w3d_main_body:
    W3D_STARTUP_TRACE 010h
; Establish the application-global Escape latch before the first potentially
; long container load.  w3d_shell_run resets it again for a fresh shell
; lifecycle; it deliberately remains sticky everywhere else. Clear the older
; gameplay latch too so a second MOS RUN of the resident binary starts clean.
    xor a
    ld (w3d_exit_requested),a
    call w3d_shell_reset_exit_request
    ld hl,w3d_app_version_text
    call printString
    call printNewLine

; Shell graphics are application-global. Load them before showing any game
; screen, then keep them resident across gameplay sessions and Episode 1
; victory returns.
    ld hl,loading_shell_msg
    call printString
    call printNewLine
    ld hl,wp_stage_shell
    call wp_loading_begin
    W3D_STARTUP_TRACE 011h
    ld de,shell_filename
    ld hl,printImageDotAndPollEscape
    call agnb_load_images_with_abortable_callback
    jr z,@shell_loaded
    call w3d_shell_query_exit_request
    ret nz
    W3D_STARTUP_TRACE 0f1h
    ld hl,assets_error_msg
    ld (w3d_exit_message_ptr),hl
    ret
@shell_loaded:
    W3D_STARTUP_TRACE 012h
    call printNewLine
; Sound effects are application-global just like the shell graphics.  This
; makes the source control-panel effects available before the first game and
; avoids reloading the same resident container after every demo, death, or
; victory return.
    ld hl,loading_sfx_msg
    call printString
    call printNewLine
    ld hl,wp_stage_sfx
    call wp_loading_begin
    W3D_STARTUP_TRACE 020h
    ld de,sfx_filename
    ld hl,printAudioDotAndPollEscape
    call agnb_load_audio_with_abortable_callback
    jr z,@sfx_loaded
    call w3d_shell_query_exit_request
    ret nz
    W3D_STARTUP_TRACE 0f2h
    call printNewLine
    ld hl,sfx_error_msg
    call printString
@sfx_loaded:
    W3D_STARTUP_TRACE 021h
    call printNewLine
    call w3d_poll_application_escape
    ret nz
    W3D_STARTUP_TRACE 022h
    call w3d_audio_install_available_command_buffers
    jr nc,@audio_commands_installed
    W3D_STARTUP_TRACE 0f3h
    ld hl,audio_install_error_msg
    ld (w3d_exit_message_ptr),hl
    ret
@audio_commands_installed:
    W3D_STARTUP_TRACE 023h
    call w3d_poll_application_escape
    ret nz
    call w3d_highscores_initialize
    call w3d_save_slots_initialize
    call w3d_shell_reset_quick_slot
    .if W3D_DIAGNOSTIC_HIGHSCORE_MODE
    call w3d_acceptance_run_highscore
    .else
    W3D_STARTUP_TRACE 024h
    call w3d_open_shell_callback
    ld a,W3D_SHELL_RESULT_NEW_GAME
    push af
    call w3d_close_shell_callback
    pop af
    W3D_STARTUP_TRACE 025h
    .endif

@route_shell_result:
    cp W3D_SHELL_RESULT_NEW_GAME
    jr z,@run_new_game
    cp W3D_SHELL_RESULT_LOAD_GAME
    jr z,@run_loaded_game
    cp W3D_SHELL_RESULT_DEMO
    jr z,@run_gameplay
    ret
@run_new_game:
    call w3d_demo_cancel
    call w3d_shell_reset_quick_slot
    jr @run_gameplay
@run_loaded_game:
    call w3d_demo_cancel
@run_gameplay:
    call w3d_run_gameplay_session
    cp W3D_GAMEPLAY_RESULT_LOAD
    jr z,@run_gameplay
    cp W3D_GAMEPLAY_RESULT_NEW_GAME
    jr z,@restart_new_game
    cp W3D_GAMEPLAY_RESULT_DEMO_DONE
    jr z,@demo_done
    cp W3D_GAMEPLAY_RESULT_VICTORY
    jr z,@victory
    cp W3D_GAMEPLAY_RESULT_GAME_OVER
    ret nz
    call w3d_open_shell_callback
    call w3d_shell_resume_after_game_over
    push af
    call w3d_close_shell_callback
    pop af
    jr @route_shell_result
@victory:
    call w3d_open_shell_callback
    call w3d_shell_resume_after_victory
    push af
    call w3d_close_shell_callback
    pop af
    jr @route_shell_result
@demo_done:
    ld a,(w3d_demo_aborted)
    push af
    call w3d_demo_cancel
    call w3d_open_shell_callback
    pop af
    or a
    jr nz,@demo_aborted
    call w3d_shell_resume_after_demo
    jr @demo_shell_done
@demo_aborted:
    call w3d_shell_resume_after_demo_abort
@demo_shell_done:
    push af
    call w3d_close_shell_callback
    pop af
    jr @route_shell_result
@restart_new_game:
    call w3d_shell_reset_quick_slot
    jr @run_gameplay

; Disposable visual-acceptance route. Production assembles this branch out.
; It starts after the real shell/SFX bootstrap, uses the production table,
; editor, timeout, persistence, music, and control panel, and merely supplies
; a deterministic candidate so the Author need not play to reach either path.
    .if W3D_DIAGNOSTIC_HIGHSCORE_MODE
w3d_acceptance_run_highscore:
    call w3d_shell_setup
    ld a,W3D_MUSIC_ROSTER
    call w3d_music_start
    call w3d_highscores_reset_defaults
    xor a
    ld (w3d_level_requested_index),a
    ld hl,w3d_player_score
    ld a,W3D_DIAGNOSTIC_HIGHSCORE_MODE
    cp 1
    jr nz,@nonqualifying
    ld (hl),0ffh
    inc hl
    ld (hl),0ffh
    inc hl
    ld (hl),0ffh
    inc hl
    ld (hl),07fh
    jr @candidate_ready
@nonqualifying:
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),a
@candidate_ready:
    call w3d_highscores_handle_game_end
    call w3d_shell_query_exit_request
    ret nz
    jp w3d_shell_main_menu
    .endif

; One complete gameplay ownership lifetime. A selected difficulty is already
; authoritative when this routine begins, so the matching level package and
; actor population are loaded only after the shell returns NEW_GAME.
w3d_run_gameplay_session:
    W3D_STARTUP_TRACE 060h
; The shell/attract track is useful while the player is choosing a game, but
; continuing to service a delayed IMF stream from every AGNB callback makes
; it compete with the large level/SFX/HUD upload. On physical hardware that
; backlog was audible and compounded the former late framebuffer-allocation
; hazard. Silence the old context before loading, then fence its final nine
; voice-reset commands. The selected floor track starts only after the
; gameplay renderer has opened, below.
    call w3d_music_stop
    call w3d_audio_wait_for_vdp_ingress
    jp c,w3d_gameplay_fatal_before_runtime
    call w3d_shell_clear
    xor a
    ld (w3d_victory_final_render_submitted),a

; FUTURE: The W3DV startup compatibility gate is deliberately preserved below
; but disabled. Its VDP-native and direct-eZ80 validation tests pass, while the
; real MOS keycode-callback transport currently produces a false incompatibility
; result. The Author wants to ship tonight, so startup temporarily retains the
; established pre-gate behavior. Diagnose the raw callback bytes before
; reenabling this block.
;    call w3d_initialize_render_state
;    call w3d_install_render_callback
;    ei
;    ld hl,vdp_check_msg
;    call printString
;    call printNewLine
;    call w3d_query_renderer_compatibility
;    jr c,@vdp_incompatible
;    call w3d_remove_render_callback
;    ld hl,vdp_check_ok_msg
;    call printString
;    call printNewLine
;    jr @vdp_compatible
;
;@vdp_incompatible:
;    call w3d_remove_render_callback
;    ld a,(w3d_version_status)
;    cp W3D_VERSION_STATUS_TIMEOUT
;    ld hl,vdp_check_missing_msg
;    jr z,@print_vdp_error
;    ld hl,vdp_check_bad_msg
;@print_vdp_error:
;    call printString
;    call printNewLine
;    ld hl,vdp_check_required_msg
;    call printString
;    call printNewLine
;    ld hl,vdp_check_return_msg
;    call printString
;    call printNewLine
;    MOSCALL mos_getkey
;    ret
;
;@vdp_compatible:

; The package itself is a single synchronous FatFS operation, so poll on both
; sides of it.  AGNB containers below provide finer image/sample boundaries.
    call w3d_poll_application_escape
    jp nz,w3d_gameplay_exit_before_runtime
    ld a,(w3d_requested_difficulty)
    ld b,a
    ld a,(w3d_save_pending_load)
    or a
    jr z,@fresh_level
    ld a,(w3d_save_file_buffer+W3D_SAVE_H_LEVEL)
    jr @level_selected
@fresh_level:
    ld a,(w3d_demo_active)
    or a
    jr z,@ordinary_fresh_level
    ld a,(w3d_demo_level)
    jr @level_selected
@ordinary_fresh_level:
    .if W3D_INITIAL_LEVEL
    ld a,W3D_INITIAL_LEVEL
    .else
    xor a
    .endif
@level_selected:
    W3D_STARTUP_TRACE 061h
    call w3d_load_level_package
    push af
    call w3d_poll_application_escape
    jr nz,@level_load_aborted
    pop af
    jr z,@level_state_loaded
    call w3d_set_level_load_error
    jp w3d_gameplay_fatal_before_runtime
@level_load_aborted:
    pop af
    jp w3d_gameplay_exit_before_runtime
@level_state_loaded:
    W3D_STARTUP_TRACE 062h

; Reassert the already-established display state before tiles, sprites, and HUD
; claim additional VDP SRAM. Since main acquired mode 136 first, this call only
; restores draw configuration and fences it; it cannot request another
; framebuffer under later memory pressure.
    W3D_STARTUP_TRACE 069h
    call w3d_enter_gameplay_display
    jp c,w3d_gameplay_fatal_before_runtime
    W3D_STARTUP_TRACE 06ah

    ld hl,loading_msg
    call printString
    call printNewLine
    ld hl,wp_stage_tiles
    call wp_loading_begin

; Wall-gallery upload diagnostics are intentionally retained but disabled.
; Uncomment this block and select printImageBreadcrumb below when a future
; asset-upload failure needs bitmap-by-bitmap visual inspection.
;    ld hl,w3d_gallery_setup
;    ld bc,w3d_gallery_setup_end-w3d_gallery_setup
;    rst.lil 18h
;    ld hl,gallery_msg
;    call printString
;    call printNewLine
;    call initializeTextureGallery

    ld de,w3d_level_tiles_filename
;    ld hl,printImageBreadcrumb ; diagnostic wall gallery
    ld hl,printImageDotAndPollEscape ; normal breadcrumb-only loading
    W3D_STARTUP_TRACE 063h
    call agnb_load_images_with_abortable_callback
    .if W3D_DIAGNOSTIC_STARTUP_TRACE
    jp z,@assets_loaded
    .else
    jr z,@assets_loaded
    .endif
    W3D_STARTUP_TRACE_AGNB_ERROR w3d_level_tiles_filename
    call w3d_shell_query_exit_request
    jp nz,w3d_gameplay_exit_before_runtime
    ld hl,assets_error_msg
    ld (w3d_exit_message_ptr),hl
    jp w3d_gameplay_fatal_before_runtime
@assets_loaded:
    W3D_STARTUP_TRACE 064h
    call printNewLine
    ld hl,loading_sprites_msg
    call printString
    call printNewLine
    ld hl,wp_stage_sprites
    call wp_loading_begin
    ld de,w3d_level_sprites_filename
    ld hl,printImageDotAndPollEscape
    W3D_STARTUP_TRACE 065h
    call agnb_load_images_with_abortable_callback
    .if W3D_DIAGNOSTIC_STARTUP_TRACE
    jp z,@sprites_loaded
    .else
    jr z,@sprites_loaded
    .endif
    W3D_STARTUP_TRACE_AGNB_ERROR w3d_level_sprites_filename
    call w3d_shell_query_exit_request
    jp nz,w3d_gameplay_exit_before_runtime
    ld hl,assets_error_msg
    ld (w3d_exit_message_ptr),hl
    jp w3d_gameplay_fatal_before_runtime
@sprites_loaded:
    W3D_STARTUP_TRACE 066h
    call printNewLine
    ld hl,loading_hud_msg
    call printString
    call printNewLine
    ld hl,wp_stage_hud
    call wp_loading_begin
    ld de,hud_filename
    ld hl,printImageDotAndPollEscape
    W3D_STARTUP_TRACE 067h
    call agnb_load_images_with_abortable_callback
    .if W3D_DIAGNOSTIC_STARTUP_TRACE
    jp z,@hud_loaded
    .else
    jr z,@hud_loaded
    .endif
    W3D_STARTUP_TRACE_AGNB_ERROR hud_filename
    call w3d_shell_query_exit_request
    jp nz,w3d_gameplay_exit_before_runtime
    ld hl,assets_error_msg
    ld (w3d_exit_message_ptr),hl
    jp w3d_gameplay_fatal_before_runtime
@hud_loaded:
    W3D_STARTUP_TRACE 068h
    call printNewLine

; Gallery review pause, retained alongside the disabled diagnostic block.
;    ld hl,gallery_done_msg
;    call printString
;    call printNewLine
;    MOSCALL mos_getkey

    ld hl,rendering_msg
    call printString
    call printNewLine
    call w3d_replace_level_tilemap_buffer

; AGNB image uploads and the tilemap-buffer replacement are asynchronous at
; the VDP parser boundary.  The framebuffer is already reserved, but the first
; renderer command must still wait until that complete asset stream has been
; consumed.  The ordered screen-info reply is the same proven ingress fence
; used by audio command-buffer setup.
    W3D_STARTUP_TRACE 06eh
    call w3d_audio_wait_for_vdp_ingress
    jp c,w3d_gameplay_fatal_before_runtime
    W3D_STARTUP_TRACE 06fh

    call w3d_initialize_control_clock
    W3D_STARTUP_TRACE 080h
    call w3d_initialize_render_state
    W3D_STARTUP_TRACE 081h
; Intermission polling primarily reads the held-key map, but the installed MOS
; callback may observe and latch a shorter Escape entirely between two asset
; boundaries. Give it the same common predicate so that event cannot be lost.
    ld hl,w3d_query_application_exit
    call w3d_intermission_set_application_exit_query_hook
    W3D_STARTUP_TRACE 082h
; Transition-time AGNB streaming has no textual breadcrumb delay. Reuse the
; proven audio-loader screen-info round trip as an ordered VDP ingress fence
; after every finalized destination image.
    ld hl,w3d_audio_wait_for_vdp_ingress
    call w3d_intermission_set_ingress_fence_hook
    ld hl,w3d_intermission_audio_hook
    call w3d_intermission_set_sound_hook
    ld hl,w3d_intermission_award_hook_production
    call w3d_intermission_set_award_hook
    ld hl,w3d_intermission_wait_30hz
    call w3d_intermission_set_wait_hook
    W3D_STARTUP_TRACE 083h
    ld a,(w3d_save_pending_load)
    or a
    jr z,@initialize_new_game
    W3D_STARTUP_TRACE 084h
; Death initialization normally captures the just-created level-entry score.
; A saved game already owns that checkpoint, so clear/install the death
; lifecycle first and let the transactional decode restore oldscore afterward.
    call w3d_initialize_death_state
    call w3d_save_slot_publish_pending
    jp c,w3d_gameplay_fatal_shutdown
    jr @simulation_state_ready
@initialize_new_game:
    W3D_STARTUP_TRACE 085h
    call w3d_initialize_motion_state
    W3D_STARTUP_TRACE 086h
    call w3d_initialize_death_state
    W3D_STARTUP_TRACE 087h
    call w3d_demo_begin_session
    W3D_STARTUP_TRACE 088h
@simulation_state_ready:
; GameLoop stops floor music before Died() and restarts it only after the
; attempt world has been rebuilt.  The death module owns those exact edges;
; production supplies the actual IMF sequencer operations here.
    ld hl,w3d_music_stop
    call w3d_death_set_music_stop_hook
    ld hl,w3d_music_start_current_floor
    call w3d_death_set_music_restart_hook
    ld hl,w3d_reseed_level_attempt
    call w3d_death_set_reseed_hook
    W3D_STARTUP_TRACE 089h
    call w3d_install_render_callback
    W3D_STARTUP_TRACE 08ah
    call w3d_enable_render_notifications
    W3D_STARTUP_TRACE 08bh
    ei
    W3D_STARTUP_TRACE 08ch
    .if W3D_RENDER_BACKEND
    W3D_STARTUP_TRACE 06bh
    call w3d_vdplet_backend_open
    jp c,w3d_gameplay_fatal_shutdown
    W3D_STARTUP_TRACE 06ch
    .endif
    call wp_loading_ready
    ld a,(wp_loading_error)
    or a
    jp nz,w3d_gameplay_exit_shutdown
    ld a,1
    ld (wpl3_reached),a
    call wp_run
    jp w3d_gameplay_exit_shutdown

; The initial world snapshot is complete. Use the same generic init/full-replay
; path as a later floor transition; the generated fixture command stream is no
; longer the application's runtime-level authority.
    call w3d_mark_full_level_dirty
    call w3d_death_prepare_next_render
    call w3d_submit_level_reset
    jp c,w3d_gameplay_fatal_shutdown
    W3D_STARTUP_TRACE 06dh

mainloop:
    call w3d_music_service
; A completed or user-aborted attract demo drains its one outstanding frame,
; then returns to the source-timed shell without scoring or persistence.
    ld a,(w3d_demo_finished)
    or a
    jr z,@check_completion
    call w3d_death_foreground_update
    ld a,(w3d_callback_error)
    or a
    jp nz,@fatal_shutdown
    ld a,(w3d_async_owner)
    or a
    jp nz,mainloop
    jp w3d_gameplay_demo_done_shutdown

@check_completion:
; Any completion freezes input/simulation immediately. The final ordinary
; snapshot, if any, still owns its callback; consume it before either loading
; a floor or returning the display to the application shell.
    ld a,(w3d_level_completion)
    or a
    jr z,@simulate
    call w3d_death_foreground_update
    ld a,(w3d_callback_error)
    or a
    jp nz,@shutdown
    ld a,(w3d_async_owner)
    or a
    jp nz,mainloop
; Completion owns this branch, but Escape remains globally stronger.  A key
; pressed on the same fixed quantum as an elevator/EXITTILE must still use the
; common application exit instead of entering intermission or victory UI.
    ld a,(w3d_exit_requested)
    or a
    jr z,@classify_completion
    call w3d_shell_request_exit
    jp w3d_gameplay_exit_shutdown
@classify_completion:
    call w3d_level_completion_is_victory
    jr z,@victory
; The completed floor remains authoritative until its intermission has
; captured and presented the source-level state.  We reach this seam only
; after the previous renderer/fizzle owner drained, and victory deliberately
; bypasses it for the separate episode-ending lifecycle below.
    ld a,W3D_MUSIC_ENDLEVEL
    call w3d_music_start
    call w3d_intermission_begin
    call w3d_transition_to_next_level
    jr nc,@transition_ready
    call w3d_shell_query_exit_request
    jp nz,w3d_gameplay_exit_shutdown
    jr @fatal_shutdown
@transition_ready:
    jp mainloop

@victory:
; A defensive normal-completion signal on E1L9 is normalized to the explicit
; victory result. Never allow the generic next-floor loader to reinterpret it
; as a request for the secret floor.
    ld a,W3D_LEVEL_COMPLETION_VICTORY
    ld (w3d_level_completion),a
; Present exactly one terminal snapshot after the prior asynchronous owner has
; drained. A real EXITTILE move dirtied the accepted pose and hidden weapon;
; this makes both visible before returning to the application shell. The next
; pass drains this render through the normal callback path before teardown.
    ld a,(w3d_victory_final_render_submitted)
    or a
    jp nz,w3d_gameplay_victory_shutdown
    ld a,1
    ld (w3d_victory_final_render_submitted),a
    call w3d_death_prepare_next_render
    call w3d_submit_dirty_world_render
    jp c,w3d_gameplay_fatal_shutdown
    jp mainloop

@simulate:
; Input and simulation run at an exact 30 Hz fixed step (four 120 Hz MOS
; ticks), independently of render completion.
    call w3d_poll_keys
    call w3d_tick_control_clock
    call w3d_accumulate_simulation_time
    call w3d_run_simulation_batch

; A max-step catch-up pass may still leave complete 30-Hz quanta queued. Keep
; only its newest pending requests and emit nothing stale; the next simulated
; quantum replaces them. Once fully caught up, flush the winning requests
; independently of whether the VDP renderer is still busy.
    ld hl,(w3d_simulation_accumulator)
    ld de,W3D_SIMULATION_STEP_TICKS
    or a
    sbc hl,de
    jr nc,@audio_backlog_remains
    call w3d_audio_flush_quantum
@audio_backlog_remains:

; Consume and route both ordinary render and death-fizzle completions. Only
; event-1 renders issue C3; event-2 already leaves both VDP surfaces mirrored.
    call w3d_death_foreground_update

; Once the final life has completed its fizzle/hold, the original routes the
; current score and one-based floor through CheckHighScore before returning to
; the control panel.  No render owner remains in the terminal phase.
    ld a,(w3d_death_phase)
    cp W3D_DEATH_PHASE_GAME_OVER
    jp z,w3d_gameplay_game_over_shutdown

; Escape exits cleanly once no asynchronous producer remains in flight. A
; malformed completion is different: validation deliberately retains its
; owner, so waiting would spin forever. In that terminal fault case disable
; future notifications and remove the callback immediately; any late UART
; record then falls through MOS's ordinary keyboard path instead of targeting
; application memory.
    ld a,(w3d_exit_requested)
    or a
    jr z,@continue
    ld a,(w3d_callback_error)
    or a
    jr nz,@shutdown
    ld a,(w3d_async_owner)
    or a
    jp nz,mainloop

@shutdown:
    ld a,(w3d_callback_error)
    or a
    jr nz,@fatal_shutdown
    jp w3d_gameplay_pause

@fatal_shutdown:
    jp w3d_gameplay_fatal_shutdown

@continue:
; A new render may be submitted only when the previous one completed and the
; simulation is fully caught up. Thus 30 Hz is both the simulation quantum and
; the maximum presentation cadence; slower rendering skips stale snapshots
; without slowing world time.
    ld a,(w3d_async_owner)
    or a
    jp nz,mainloop

    ld hl,(w3d_simulation_accumulator)
    ld de,W3D_SIMULATION_STEP_TICKS
    or a
    sbc hl,de
    jp nc,mainloop

; Completion routing owns the next submission. In particular, EXITTILE must
; not fall through and submit its dirty pose here and then submit the explicit
; terminal victory snapshot a second time on the next main-loop pass.
    ld a,(w3d_level_completion)
    or a
    jp nz,mainloop

    call w3d_death_render_permitted
    or a
    jp z,mainloop

; A successful death reseed must begin with init_level, then replay the full
; authoritative fixture snapshot into the cleared VDP mirror. No other phase
; may use this reset submission path.
    ld a,(w3d_death_phase)
    cp W3D_DEATH_PHASE_WAIT_RESPAWN_FRAME
    jr nz,@ordinary_render
    call w3d_death_prepare_next_render
    call w3d_submit_level_reset
    jp mainloop

@ordinary_render:
    ld a,(w3d_world_dirty)
    or a
    jp z,mainloop
    call w3d_death_prepare_next_render
    call w3d_submit_dirty_world_render
    jp mainloop

; Gameplay Escape opens the original in-game control-panel seam after every
; asynchronous owner has drained. The VDPlet and callback remain installed
; while the retained double-buffered shell is visible; no render command is
; submitted, and resuming rebuilds both native framebuffers from authoritative
; eZ80 state.
w3d_gameplay_pause:
    ld a,(w3d_gameplay_panel_request)
    cp w3d_panel_request_pause
    jr z,@pause_overlay
    call w3d_gameplay_panel_open_music
    call w3d_gameplay_backdrop_capture
    call w3d_shell_setup
    call w3d_audio_wait_for_vdp_ingress
    jr nc,@shell_mode_ready
    call w3d_gameplay_backdrop_release
    jp w3d_gameplay_fatal_shutdown
@shell_mode_ready:
    call w3d_gameplay_backdrop_plot
    ld a,(w3d_gameplay_panel_request)
; The PAUSED overlay must retain gameplay callback semantics so a second Pause
; can acknowledge it.  Only ordinary in-game control-panel pages inherit
; WL_MENU.C::CheckPause's music-toggle context.
    cp w3d_panel_request_pause
    jr z,@invoke_shell_quick
    push af
    call w3d_begin_shell_callback_context
    pop af
@invoke_shell_quick:
    call w3d_shell_pause_quick
    push af
    ld a,(w3d_shell_callback_active)
    or a
    call nz,w3d_end_shell_callback_context
    call w3d_gameplay_backdrop_release
    pop af
    cp W3D_SHELL_PAUSE_RESUME
    jp z,w3d_gameplay_resume
    cp W3D_SHELL_PAUSE_NEW_GAME
    jp z,w3d_gameplay_new_game_shutdown
    cp W3D_SHELL_PAUSE_END_GAME
    jr z,@end_game
    cp W3D_SHELL_PAUSE_LOAD_GAME
    jp z,w3d_gameplay_load_shutdown
    jp w3d_gameplay_exit_shutdown

@end_game:
; CP_EndGame sets lives to zero and routes through the ordinary Died() path.
; Preserve that visible turn/fizzle/hold rather than jumping straight to the
; roster: the next fixed quantum promotes this lethal latch, and finish-hold
; decrements zero to -1 before selecting the game-over high-score handoff.
    xor a
    ld (w3d_player_lives),a
    ld (w3d_player_health),a
    ld a,1
    ld (w3d_player_dead),a
    ld a,W3D_SLOT_NONE
    ld (w3d_player_killer),a
    jp w3d_gameplay_resume

@pause_overlay:
; WL_PLAY.C draws PAUSEDPIC at (16 chars, 64 pixels), turns music off, waits
; for a fresh acknowledgment, then resumes the sequencer at the same position.
; Rendering has already drained, so the bitmap and C3 operate without
; competing with a VDPlet render owner. The normal resume path reconstructs
; both framebuffers.
    call w3d_music_pause
    ld hl,W3D_SHELL_PAUSED_BUFFER
    call selectBitmap
    ld bc,128
    ld de,64
    call plotBitmap
    call w3d_vdu_present
    call w3d_gameplay_pause_wait_all_released
    ld a,1
    ld (w3d_pause_ack_armed),a
@pause_wait:
    ld a,(w3d_pause_ack_requested)
    or a
    jr nz,@pause_accepted
    MOSCALL mos_getkbmap
    ld b,16
@pause_scan:
    ld a,(ix)
    or a
    jr nz,@pause_accepted
    inc ix
    djnz @pause_scan
    jr @pause_wait
@pause_accepted:
    call w3d_gameplay_pause_wait_all_released
    xor a
    ld (w3d_pause_ack_armed),a
    ld (w3d_pause_ack_requested),a
    jp w3d_gameplay_resume

; Ignore held gameplay controls. The callback-only Pause key is intentionally
; absent from this scan and is handled by w3d_pause_ack_requested above.
w3d_gameplay_pause_wait_all_released:
    MOSCALL mos_getkbmap
    ld b,16
@pause_release_scan:
    ld a,(ix)
    or a
    jr nz,w3d_gameplay_pause_wait_all_released
    inc ix
    djnz @pause_release_scan
    ret

w3d_gameplay_resume:
    call w3d_gameplay_panel_resume_music
    call w3d_enter_gameplay_display
    jp c,w3d_gameplay_fatal_shutdown
    call w3d_initialize_control_clock
    call w3d_initialize_render_state
    call w3d_mark_full_level_dirty
    call w3d_death_prepare_next_render
    call w3d_submit_level_reset
    jp c,w3d_gameplay_fatal_shutdown
    jp mainloop

w3d_gameplay_fatal_before_runtime:
    W3D_STARTUP_TRACE 0f4h
    ld a,W3D_GAMEPLAY_RESULT_FATAL
    ret

w3d_gameplay_exit_before_runtime:
    ld a,W3D_GAMEPLAY_RESULT_EXIT
    ret

w3d_gameplay_exit_shutdown:
    ld a,W3D_GAMEPLAY_RESULT_EXIT
    jr w3d_gameplay_shutdown

w3d_gameplay_victory_shutdown:
    ld a,W3D_GAMEPLAY_RESULT_VICTORY
    jr w3d_gameplay_shutdown

w3d_gameplay_game_over_shutdown:
    ld a,W3D_GAMEPLAY_RESULT_GAME_OVER
    jr w3d_gameplay_shutdown

w3d_gameplay_load_shutdown:
    ld a,W3D_GAMEPLAY_RESULT_LOAD
    jr w3d_gameplay_shutdown

w3d_gameplay_new_game_shutdown:
    ld a,W3D_GAMEPLAY_RESULT_NEW_GAME
    jr w3d_gameplay_shutdown

w3d_gameplay_demo_done_shutdown:
    ld a,W3D_GAMEPLAY_RESULT_DEMO_DONE
    jr w3d_gameplay_shutdown

w3d_gameplay_fatal_shutdown:
    W3D_STARTUP_TRACE 0f5h
    ld a,W3D_GAMEPLAY_RESULT_FATAL

w3d_gameplay_shutdown:
    W3D_STARTUP_TRACE 070h
    ld (w3d_gameplay_result),a
    call w3d_audio_stop_channels
    call w3d_disable_render_notifications
    .if W3D_RENDER_BACKEND
    call w3d_vdplet_backend_close
    jr nc,@renderer_closed
    W3D_STARTUP_TRACE 0f6h
    ld a,W3D_GAMEPLAY_RESULT_FATAL
    ld (w3d_gameplay_result),a
@renderer_closed:
    .endif
    call w3d_remove_render_callback
    ld a,(w3d_gameplay_result)
    ret

; Intermission hooks ---------------------------------------------------------

; A=logical id.  Count-up events are not part of the gameplay simulation
; queue, so each one owns and flushes a single immediate quantum.
w3d_intermission_audio_hook:
    push af
    call w3d_audio_begin_quantum
    pop af
    ld b,127
    ld c,0
    call w3d_audio_request
    jp w3d_audio_flush_quantum

; DE -> little-endian u32 bonus.
w3d_intermission_award_hook_production:
    push de
    ld hl,w3d_player_next_extra
    ld de,w3d_intermission_old_next_extra
    ld bc,4
    ldir
    pop de
    ex de,hl
    call w3d_add_player_score32_ptr
    ld hl,w3d_player_next_extra
    ld de,w3d_intermission_old_next_extra
    ld b,4
@compare_threshold:
    ld a,(de)
    cp (hl)
    jr nz,@extra_life
    inc hl
    inc de
    djnz @compare_threshold
    ret
@extra_life:
    ld a,W3D_AUDIO_SOUND_BONUS1UP
    jp w3d_intermission_audio_hook

; Pace post-loading count-up at 30 Hz from the MOS 120 Hz clock. Loading-time
; image callbacks intentionally do not call this hook: their completed-record
; boundaries already provide useful animation cadence without stalling AGNB.
w3d_intermission_wait_30hz:
    ld ix,(w3d_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld (w3d_intermission_wait_started),hl
@wait:
    call w3d_music_service
    ld ix,(w3d_sysvars_pointer)
    ld hl,(ix+sysvar_time)
    ld de,(w3d_intermission_wait_started)
    or a
    sbc hl,de
    ld de,4
    or a
    sbc hl,de
    jr c,@wait
    ret

W3D_GAMEPLAY_RESULT_EXIT:     equ 0
W3D_GAMEPLAY_RESULT_VICTORY:  equ 1
W3D_GAMEPLAY_RESULT_GAME_OVER: equ 2
W3D_GAMEPLAY_RESULT_FATAL:    equ 3
W3D_GAMEPLAY_RESULT_LOAD:     equ 4
W3D_GAMEPLAY_RESULT_NEW_GAME: equ 5
W3D_GAMEPLAY_RESULT_DEMO_DONE: equ 6

w3d_gameplay_result:
    db W3D_GAMEPLAY_RESULT_EXIT
w3d_victory_final_render_submitted:
    db 0
w3d_intermission_wait_started:
    dl 0
w3d_intermission_old_next_extra:
    ds 4

    include "bench.inc"

    include "loading_pages.inc"
