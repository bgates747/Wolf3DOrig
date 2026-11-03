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
; victory return are live. Bosses, projectiles, music, and the intermission's
; original count-up/bonus animation remain future work.
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
    include "wolf3d_sight.inc"
    include "agnb_dependencies.inc"
    include "agnb_api.inc"
    include "wolf3d_audio_assets.inc"
    include "wolf3d_shell_assets.inc"
    include "wolf3d_version.inc"
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
    call main

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

; Select the 320x240x64 double-buffered display only after all bootstrap
; diagnostics and asset loading are complete. The renderer draws its 256x160
; view into the hidden surface; validated W3DR completion presents it with C3.
w3d_display_setup:
    db 22,8+128             ; MODE 8: 320x240x64, double buffered
    db 23,0,$C0,0           ; logical coordinate scaling off
    db 23,1,0               ; cursor off
    db 18,0,128             ; graphics background logical colour 0 (black)
    db 16                   ; clear current graphics draw buffer
w3d_display_setup_end:

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
; changes it. Wolf3D always restores the same base mode in single-buffered
; form: bit 7 is a VDP double-buffer request, not part of the MOS mode number.
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
    jp w3d_wait_for_gameplay_mode

w3d_restore_mode_command:
    db 22,0                 ; saved base mode, patched during startup
    db 12                   ; CLS: clear text viewport
    db 16                   ; CLG: clear graphics viewport
w3d_restore_mode_command_end:

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
    ld a,'.'
    rst.lil 10h
    xor a
    ret

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
    ld a,'.'
    rst.lil 10h
    xor a
    ret

; Preserve the exact loaded-sample bookkeeping before checking Escape.
printAudioDotAndPollEscape:
    call printAudioDot
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

main:
    ld hl,farewell_msg
    ld (w3d_exit_message_ptr),hl
    call w3d_capture_original_screen_mode
    call w3d_main_body
    call w3d_restore_original_screen_mode
    ld hl,(w3d_exit_message_ptr)
    call printString
    ret

w3d_main_body:
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
    ld de,shell_filename
    ld hl,printImageDotAndPollEscape
    call agnb_load_images_with_abortable_callback
    jr z,@shell_loaded
    call w3d_shell_query_exit_request
    ret nz
    ld hl,assets_error_msg
    ld (w3d_exit_message_ptr),hl
    ret
@shell_loaded:
    call printNewLine
    call w3d_highscores_initialize
    call w3d_save_slots_initialize
    call w3d_shell_run

@route_shell_result:
    cp W3D_SHELL_RESULT_NEW_GAME
    jr z,@run_gameplay
    cp W3D_SHELL_RESULT_LOAD_GAME
    ret nz
@run_gameplay:
    call w3d_run_gameplay_session
    cp W3D_GAMEPLAY_RESULT_LOAD
    jr z,@run_gameplay
    cp W3D_GAMEPLAY_RESULT_NEW_GAME
    jr z,@run_gameplay
    cp W3D_GAMEPLAY_RESULT_VICTORY
    jr z,@victory
    cp W3D_GAMEPLAY_RESULT_GAME_OVER
    ret nz
    call w3d_shell_resume_after_game_over
    jr @route_shell_result
@victory:
    call w3d_shell_resume_after_victory
    jr @route_shell_result

; One complete gameplay ownership lifetime. A selected difficulty is already
; authoritative when this routine begins, so the matching level package and
; actor population are loaded only after the shell returns NEW_GAME.
w3d_run_gameplay_session:
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
    .if W3D_INITIAL_LEVEL
    ld a,W3D_INITIAL_LEVEL
    .else
    xor a
    .endif
@level_selected:
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

    ld hl,loading_msg
    call printString
    call printNewLine

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
    call agnb_load_images_with_abortable_callback
    jr z,@assets_loaded
    call w3d_shell_query_exit_request
    jp nz,w3d_gameplay_exit_before_runtime
    ld hl,assets_error_msg
    ld (w3d_exit_message_ptr),hl
    jp w3d_gameplay_fatal_before_runtime
@assets_loaded:
    call printNewLine
    ld hl,loading_sprites_msg
    call printString
    call printNewLine
    ld de,w3d_level_sprites_filename
    ld hl,printImageDotAndPollEscape
    call agnb_load_images_with_abortable_callback
    jr z,@sprites_loaded
    call w3d_shell_query_exit_request
    jp nz,w3d_gameplay_exit_before_runtime
    ld hl,assets_error_msg
    ld (w3d_exit_message_ptr),hl
    jp w3d_gameplay_fatal_before_runtime
@sprites_loaded:
    call printNewLine
    ld hl,loading_hud_msg
    call printString
    call printNewLine
    ld de,hud_filename
    ld hl,printImageDotAndPollEscape
    call agnb_load_images_with_abortable_callback
    jr z,@hud_loaded
    call w3d_shell_query_exit_request
    jp nz,w3d_gameplay_exit_before_runtime
    ld hl,assets_error_msg
    ld (w3d_exit_message_ptr),hl
    jp w3d_gameplay_fatal_before_runtime
@hud_loaded:
    call printNewLine
    ld hl,loading_sfx_msg
    call printString
    call printNewLine
    call w3d_audio_initialize
    ld de,sfx_filename
    ld hl,printAudioDotAndPollEscape
    call agnb_load_audio_with_abortable_callback
    jr z,@sfx_loaded
    call w3d_shell_query_exit_request
    jp nz,w3d_gameplay_exit_before_runtime
    call printNewLine
    ld hl,sfx_error_msg
    call printString
@sfx_loaded:
    call printNewLine
; Partial containers remain useful: install procedures only for callbacks
; that reached the finalized-sample boundary before any loader error.
    call w3d_poll_application_escape
    jp nz,w3d_gameplay_exit_before_runtime
    call w3d_audio_install_available_command_buffers
    jr nc,@audio_commands_installed
    ld hl,audio_install_error_msg
    ld (w3d_exit_message_ptr),hl
    jp w3d_gameplay_fatal_before_runtime
@audio_commands_installed:
    call w3d_poll_application_escape
    jp nz,w3d_gameplay_exit_before_runtime

; Gallery review pause, retained alongside the disabled diagnostic block.
;    ld hl,gallery_done_msg
;    call printString
;    call printNewLine
;    MOSCALL mos_getkey

    ld hl,rendering_msg
    call printString
    call printNewLine
    call w3d_replace_level_tilemap_buffer

    .if W3D_RENDER_BACKEND
    call w3d_arm_gameplay_mode_fence
    .endif
    ld hl,w3d_display_setup
    ld bc,w3d_display_setup_end-w3d_display_setup
    rst.lil 18h
    .if W3D_RENDER_BACKEND
    call w3d_wait_for_gameplay_mode
    jp c,w3d_gameplay_fatal_before_runtime
    .endif

    call w3d_initialize_control_clock
    call w3d_initialize_render_state
; Intermission polling primarily reads the held-key map, but the installed MOS
; callback may observe and latch a shorter Escape entirely between two asset
; boundaries. Give it the same common predicate so that event cannot be lost.
    ld hl,w3d_query_application_exit
    call w3d_intermission_set_application_exit_query_hook
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
    ld a,(w3d_save_pending_load)
    or a
    jr z,@initialize_new_game
; Death initialization normally captures the just-created level-entry score.
; A saved game already owns that checkpoint, so clear/install the death
; lifecycle first and let the transactional decode restore oldscore afterward.
    call w3d_initialize_death_state
    call w3d_save_slot_publish_pending
    jp c,w3d_gameplay_fatal_shutdown
    jr @simulation_state_ready
@initialize_new_game:
    call w3d_initialize_motion_state
    call w3d_initialize_death_state
@simulation_state_ready:
    ld hl,w3d_reseed_level_attempt
    call w3d_death_set_reseed_hook
    call w3d_install_render_callback
    call w3d_enable_render_notifications
    ei
    .if W3D_RENDER_BACKEND
    call w3d_vdplet_backend_open
    jp c,w3d_gameplay_fatal_shutdown
    .endif

; The initial world snapshot is complete. Use the same generic init/full-replay
; path as a later floor transition; the generated fixture command stream is no
; longer the application's runtime-level authority.
    call w3d_mark_full_level_dirty
    call w3d_death_prepare_next_render
    call w3d_submit_level_reset
    jp c,w3d_gameplay_fatal_shutdown

mainloop:
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
; while the single-buffered shell is visible; no render command is submitted,
; and resuming rebuilds both native framebuffers from authoritative eZ80 state.
w3d_gameplay_pause:
    call w3d_arm_gameplay_mode_fence
    call w3d_shell_setup
    call w3d_wait_for_gameplay_mode
    jp c,w3d_gameplay_fatal_shutdown
    call w3d_shell_pause_menu
    cp W3D_SHELL_PAUSE_RESUME
    jr z,@resume
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

@resume:
    call w3d_arm_gameplay_mode_fence
    ld hl,w3d_display_setup
    ld bc,w3d_display_setup_end-w3d_display_setup
    rst.lil 18h
    call w3d_wait_for_gameplay_mode
    jp c,w3d_gameplay_fatal_shutdown
    call w3d_initialize_control_clock
    call w3d_initialize_render_state
    call w3d_mark_full_level_dirty
    call w3d_death_prepare_next_render
    call w3d_submit_level_reset
    jp c,w3d_gameplay_fatal_shutdown
    jp mainloop

w3d_gameplay_fatal_before_runtime:
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

w3d_gameplay_fatal_shutdown:
    ld a,W3D_GAMEPLAY_RESULT_FATAL

w3d_gameplay_shutdown:
    ld (w3d_gameplay_result),a
    call w3d_audio_shutdown
    call w3d_disable_render_notifications
    .if W3D_RENDER_BACKEND
    call w3d_vdplet_backend_close
    jr nc,@renderer_closed
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

w3d_gameplay_result:
    db W3D_GAMEPLAY_RESULT_EXIT
w3d_victory_final_render_submitted:
    db 0
w3d_intermission_wait_started:
    dl 0
w3d_intermission_old_next_extra:
    ds 4
