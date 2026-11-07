; =============================================================================
; Per-level elapsed-time clock shared by gameplay and floor intermission.
;
; Motion includes this file directly so every standalone production-motion
; regression receives the same implementation without depending on the UI.
; One tick is one accepted 30 Hz simulation quantum.  The display-compatible
; state clamps at the original game's 99:00 maximum.
; =============================================================================

W3D_LEVEL_TIME_TICKS_PER_SECOND: equ 30

w3d_intermission_tick_level_time:
    ld a,(w3d_intermission_level_minutes)
    cp 99
    ret z
    ld a,(w3d_intermission_level_subticks)
    inc a
    cp W3D_LEVEL_TIME_TICKS_PER_SECOND
    jr z,@second
    ld (w3d_intermission_level_subticks),a
    ret
@second:
    xor a
    ld (w3d_intermission_level_subticks),a
    ld a,(w3d_intermission_level_seconds)
    inc a
    cp 60
    jr z,@minute
    ld (w3d_intermission_level_seconds),a
    ret
@minute:
    xor a
    ld (w3d_intermission_level_seconds),a
    ld a,(w3d_intermission_level_minutes)
    inc a
    ld (w3d_intermission_level_minutes),a
    ret

w3d_intermission_reset_level_time:
    xor a
    ld (w3d_intermission_level_subticks),a
    ld (w3d_intermission_level_seconds),a
    ld (w3d_intermission_level_minutes),a
    ret

w3d_intermission_level_subticks:
    db 0
w3d_intermission_level_seconds:
    db 0
w3d_intermission_level_minutes:
    db 0
