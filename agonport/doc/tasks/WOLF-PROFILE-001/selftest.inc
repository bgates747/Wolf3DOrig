; Test-only actual-assembly driver, not a shipping game or FPS measurement.
; WPT_FULL_GAME selects ordinary gameplay with bounded held-turn steering.
wp_test:
    ld hl,0
    add hl,sp
    ld (wp_test_entry_sp),hl
    .if WPT_FULL_GAME
    ld a,2
    ld (w3d_requested_difficulty),a
    call w3d_run_gameplay_session
    .else
    call w3d_enter_gameplay_display
    call w3d_initialize_render_state
    xor a
    ld hl,w3d_player_pose
    ld (hl),a
    ld de,w3d_player_pose+1
    ld bc,9
    ldir
    ld hl,0
    ld (w3d_simulation_accumulator),hl
    call w3d_profile_game_open
    ld hl,wp_test_label
    ld bc,wp_test_label_end-wp_test_label
    rst.lil 18h
@frame:
    call w3d_profile_prepare
    call w3d_mark_render_submitted
    call w3d_profile_submitted
    call wp_test_tick
    call w3d_profile_callback
    xor a
    ld (w3d_render_in_flight),a
    ld (w3d_async_owner),a
    call w3d_profile_before_present
    call w3d_vdu_present
    call w3d_profile_after_present
    ld a,(wp_status)
    or a
    jr nz,@done
    ld hl,(wp_sequence)
    ld de,WPT_FRAMES
    or a
    sbc hl,de
    jr c,@frame
@done:
    call w3d_profile_game_close
    .endif
    ld hl,0
    add hl,sp
    ld (wp_test_exit_sp),hl
    ret

; Called only by a disposable full-game producer. Polling, elapsed-time
; simulation, actors, render dispatch and completed-frame hooks remain real.
wp_test_steer:
    ld a,W3D_CONTROL_LEFT
    ld (w3d_controls),a
    ld hl,(wp_sequence)
    ld de,WPT_FRAMES
    or a
    sbc hl,de
    ret c
    ld a,1
    ld (w3d_demo_finished),a         ; existing drain-and-return shutdown seam
    ret

wp_test_tick:
    ld hl,(wp_ticks)
    ld (wp_test_wait),hl
@wait:
    ld hl,(wp_ticks)
    ld de,(wp_test_wait)
    or a
    sbc hl,de
    jr z,@wait
    ret

; Visibility qualification only. Production code has no added sleep/hold.
wp_test_hold:
    ld hl,(wp_ticks)
    ld (wp_test_hold_at),hl
@wait:
    ld hl,(wp_ticks)
    ld de,(wp_test_hold_at)
    or a
    sbc hl,de
    ld de,200
    or a
    sbc hl,de
    jr c,@wait
    ret

wp_test_result:
    ld a,(wp_status)
    ld (wp_test_report+4),a
    ld a,(wp_owned)
    ld (wp_test_report+5),a
    ld a,(wp_count)
    ld (wp_test_report+6),a
    in0 a,(083h)
    ld (wp_test_report+7),a
    ld hl,(wp_sequence)
    ld (wp_test_report+8),hl
    ld hl,(wp_test_entry_sp)
    ld (wp_test_report+12),hl
    ld hl,(wp_test_exit_sp)
    ld (wp_test_report+16),hl
    ld hl,(wp_dropped)
    ld (wp_test_report+20),hl
    ld hl,wp_test_report_name
    ld c,fa_write|fa_create_always
    MOSCALL mos_fopen
    or a
    ret z
    ld c,a
    push bc
    ld hl,wp_test_report
    ld de,32
    MOSCALL mos_fwrite
    pop bc
    MOSCALL mos_fclose
    ret

wp_test_short_write:
    dec de
    MOSCALL mos_fwrite
    ret

    .if WPT_NATIVE_MOCK
wp_test_read16:
    ld hl,(wp_native_offset)
    ld de,wp_test_native
    add hl,de
    ld e,(hl)
    inc hl
    ld a,(hl)
    ld hl,0
    ld l,e
    ld h,a
    or a
    ret
wp_test_native:
    include "native-mock.inc"
    .endif

wp_test_label:
    db 31,0,22,"PROFILER I/O TEST ONLY"
wp_test_label_end:
wp_test_report_name: db "DONE.BIN",0
wp_test_report:
    db "WPT1",0,0,0,0
    ds 24
wp_test_entry_sp: dl 0
wp_test_exit_sp: dl 0
wp_test_wait: dl 0
wp_test_hold_at: dl 0
