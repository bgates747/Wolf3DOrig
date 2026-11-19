; Timing builds use the full game and the first stock attract input stream.
w3d_weapon_bench_demo:
    xor a
    ld (w3d_demo_next_index),a
    ld (weapon_bench_done),a
    call w3d_demo_prepare_next
    call w3d_run_gameplay_session
    cp W3D_GAMEPLAY_RESULT_DEMO_DONE
    ret nz
    ld a,(w3d_demo_aborted)
    or a
    ret nz
    inc a
    ld (weapon_bench_done),a
    ret

w3d_weapon_bench_report:
    ld hl,weapon_bench_fail
    ld a,(weapon_bench_done)
    or a
    jp z,printString
    ld a,(wp_status)
    or a
    jp nz,printString
    ld de,(wp_sequence)
    ld a,d
    or e
    jp z,printString
    ld hl,weapon_bench_pass
    jp printString

weapon_bench_done: db 0
weapon_bench_pass: db "WOLFWEAPON PASS",13,10,0
weapon_bench_fail: db "WOLFWEAPON FAIL",13,10,0
