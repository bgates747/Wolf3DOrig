; Direct real-eZ80 regression for production Wolf3D mono positional audio.
; All expected values are generated from the independent SetSoundLoc oracle;
; every vector calls the production actor/tile adapter and captures A/B/C at
; its w3d_audio_request boundary.

    assume adl=1
    org 0x040000
    jp start
    align 64
    db "MOS",0,1

mos_fopen:          equ 0x0a
mos_fclose:         equ 0x0b
mos_fwrite:         equ 0x1b
mos_getkbmap:       equ 0x1e
fa_write:           equ 0x02
fa_create_always:   equ 0x08

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    macro CHECK_VECTOR_MEM address, offset, why
        ld a,(address)
        ld b,(iy+offset)
        ld c,why
        call assert_equal
    endmacro

    macro CHECK_LITERAL_MEM address, expected, why
        ld a,(address)
        ld b,expected
        ld c,why
        call assert_equal
    endmacro

    macro CHECK_MEM_MEM actual_mem, expected_mem, why
        ld a,(expected_mem)
        ld b,a
        ld a,(actual_mem)
        ld c,why
        call assert_equal
    endmacro

; Mirror the production dependency order, omitting wolf3d_audio.inc so the
; request sink below can capture the adapter's exact public ABI.
    include "wolf3d_sight.inc"
    include "wolf3d_audio_assets.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_actors.inc"
    include "wolf3d_areas.inc"
    include "wolf3d_actor_sim.inc"
    include "wolf3d_motion.inc"
    include "wolf3d_player_combat.inc"
    include "wolf3d_audio_spatial.inc"
    include "spatial_vectors.inc"

phase_actor:        equ 1
phase_tile:         equ 2
phase_count:        equ 2

reason_call_count:  equ 1
reason_sound_id:    equ 2
reason_gain:        equ 3
reason_flags:       equ 4
reason_relative:    equ 5
reason_table_index: equ 6
reason_ix:          equ 7

vector_kind:        equ 0
vector_sound:       equ 1
vector_heading:     equ 2
vector_player_x:    equ 4
vector_player_y:    equ 8
vector_source_x:    equ 12
vector_source_y:    equ 16
vector_relative_x:  equ 20
vector_relative_y:  equ 22
vector_row:         equ 24
vector_column:      equ 25
vector_gain:        equ 26
vector_flags:       equ 27

start:
    push af
    push bc
    push de
    push ix
    push iy
    call run_tests
    pop iy
    pop ix
    pop de
    pop bc
    pop af
    ld hl,0
    ret

run_tests:
    xor a
    ld hl,result_checks
    ld (hl),a
    ld de,result_checks+1
    ld bc,result_end-result_checks-1
    ldir
    ld a,1
    ld (result_schema),a

    ld iy,spatial_vectors
    ld bc,W3D_AUDIO_SPATIAL_VECTOR_COUNT
@vector_loop:
    push bc
    call run_vector
    pop bc
    lea iy,iy+W3D_AUDIO_SPATIAL_VECTOR_SIZE
    ld hl,result_vector_count
    inc (hl)
    jr nz,@vector_counted
    inc hl
    inc (hl)
@vector_counted:
    dec.s bc
    ld a,b
    or c
    jr nz,@vector_loop

    call write_result
    call print_report
    ret

run_vector:
    ld a,(iy+vector_kind)
    inc a
    ld (test_phase),a

; Authoritative full 16.16 listener pose and normalized uint16 heading.
    ld a,(iy+vector_player_x+0)
    ld (w3d_player_pose+0),a
    ld a,(iy+vector_player_x+1)
    ld (w3d_player_pose+1),a
    ld a,(iy+vector_player_x+2)
    ld (w3d_player_pose+2),a
    ld a,(iy+vector_player_x+3)
    ld (w3d_player_pose+3),a
    ld a,(iy+vector_player_y+0)
    ld (w3d_player_pose+4),a
    ld a,(iy+vector_player_y+1)
    ld (w3d_player_pose+5),a
    ld a,(iy+vector_player_y+2)
    ld (w3d_player_pose+6),a
    ld a,(iy+vector_player_y+3)
    ld (w3d_player_pose+7),a
    ld a,(iy+vector_heading+0)
    ld (w3d_player_pose+8),a
    ld a,(iy+vector_heading+1)
    ld (w3d_player_pose+9),a

    xor a
    ld (capture_calls),a
    ld (capture_sound),a
    ld (capture_gain),a
    ld (capture_flags),a

    ld a,(iy+vector_kind)
    cp W3D_AUDIO_SPATIAL_KIND_TILE
    jp z,@tile

; Actor entry: source is a real full-width actor record and IX must survive.
    ld a,(iy+vector_source_x+0)
    ld (spatial_actor+W3D_ACTOR_X+0),a
    ld a,(iy+vector_source_x+1)
    ld (spatial_actor+W3D_ACTOR_X+1),a
    ld a,(iy+vector_source_x+2)
    ld (spatial_actor+W3D_ACTOR_X+2),a
    ld a,(iy+vector_source_x+3)
    ld (spatial_actor+W3D_ACTOR_X+3),a
    ld a,(iy+vector_source_y+0)
    ld (spatial_actor+W3D_ACTOR_Y+0),a
    ld a,(iy+vector_source_y+1)
    ld (spatial_actor+W3D_ACTOR_Y+1),a
    ld a,(iy+vector_source_y+2)
    ld (spatial_actor+W3D_ACTOR_Y+2),a
    ld a,(iy+vector_source_y+3)
    ld (spatial_actor+W3D_ACTOR_Y+3),a
    ld ix,spatial_actor
    ld a,(iy+vector_sound)
    call w3d_audio_request_actor
    ld (observed_ix),ix
    ld hl,result_actor_count
    inc (hl)
    jr nz,@check_ix
    inc hl
    inc (hl)
@check_ix:
    CHECK_MEM_MEM observed_ix+0,expected_ix+0,reason_ix
    CHECK_MEM_MEM observed_ix+1,expected_ix+1,reason_ix
    CHECK_MEM_MEM observed_ix+2,expected_ix+2,reason_ix
    jr @common

@tile:
; Tile entry receives byte tile coordinates but represents the exact center.
    ld b,(iy+vector_source_x+2)
    ld c,(iy+vector_source_y+2)
    ld a,(iy+vector_sound)
    call w3d_audio_request_tile
    ld hl,result_tile_count
    inc (hl)
    jr nz,@common
    inc hl
    inc (hl)

@common:
    CHECK_LITERAL_MEM capture_calls,1,reason_call_count
    CHECK_VECTOR_MEM capture_sound,vector_sound,reason_sound_id
    CHECK_VECTOR_MEM capture_gain,vector_gain,reason_gain
    CHECK_VECTOR_MEM capture_flags,vector_flags,reason_flags
    CHECK_VECTOR_MEM w3d_actor_projection_rel_x+0,vector_relative_x+0,reason_relative
    CHECK_VECTOR_MEM w3d_actor_projection_rel_x+1,vector_relative_x+1,reason_relative
    CHECK_VECTOR_MEM w3d_actor_projection_rel_y+0,vector_relative_y+0,reason_relative
    CHECK_VECTOR_MEM w3d_actor_projection_rel_y+1,vector_relative_y+1,reason_relative
    CHECK_VECTOR_MEM w3d_audio_spatial_row,vector_row,reason_table_index
    CHECK_VECTOR_MEM w3d_audio_spatial_column,vector_column,reason_table_index
    ret

; Capture the final public producer ABI. The production adapter tail-jumps
; here, so RET completes the original actor/tile call normally.
w3d_audio_request:
    ld (capture_sound),a
    ld a,b
    ld (capture_gain),a
    ld a,c
    ld (capture_flags),a
    ld hl,capture_calls
    inc (hl)
    ret

; Current motion include dependencies not exercised by this focused fixture.
w3d_audio_begin_quantum:
    ret
w3d_death_fixed_step:
    or a
    ret
w3d_death_promote_lethal_latch:
    or a
    ret
w3d_mark_render_submitted:
    ret
w3d_elapsed_ticks:
    dl 0
w3d_exit_requested:
    db 0

; A=actual, B=expected, C=reason. IY remains the current vector pointer.
assert_equal:
    ld (assert_actual),a
    ld a,b
    ld (assert_expected),a
    push hl
    ld hl,result_checks
    inc (hl)
    jr nz,@compare
    inc hl
    inc (hl)
@compare:
    ld a,(assert_actual)
    cp b
    jr z,@return
    ld hl,result_errors
    inc (hl)
    jr nz,@bucket
    inc hl
    inc (hl)
@bucket:
    ld a,(test_phase)
    or a
    jr z,@first
    dec a
    cp phase_count
    jr nc,@first
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,result_phase_errors
    add hl,de
    inc (hl)
@first:
    ld a,(result_first_reason)
    or a
    jr nz,@return
    ld a,(test_phase)
    ld (result_first_phase),a
    ld a,c
    ld (result_first_reason),a
    ld a,(assert_expected)
    ld (result_first_expected),a
    ld a,(assert_actual)
    ld (result_first_actual),a
    ld a,(result_vector_count+0)
    ld (result_first_vector+0),a
    ld a,(result_vector_count+1)
    ld (result_first_vector+1),a
@return:
    pop hl
    ret

write_result:
    ld hl,result_filename
    ld c,fa_write | fa_create_always
    MOSCALL mos_fopen
    or a
    ret z
    ld (output_handle),a
    ld c,a
    ld hl,result_data
    ld de,result_end-result_data
    MOSCALL mos_fwrite
    ld a,(output_handle)
    ld c,a
    MOSCALL mos_fclose
    ret

print_report:
    ld hl,report_banner
    call print_string
    ld a,(result_errors+0)
    ld b,a
    ld a,(result_errors+1)
    or b
    ld hl,report_pass
    jr z,@emit
    ld hl,report_fail
@emit:
    jp print_string

print_string:
    push bc
    ld bc,0
    xor a
    rst.lil 18h
    pop bc
    ret

report_banner:      db 13,10,"Wolf3D audio spatial direct regression",13,10,0
report_pass:        db "PASS",13,10,0
report_fail:        db "FAIL",13,10,0
result_filename:    asciz "spatial_result.bin"

test_phase:         db 0
output_handle:      db 0
assert_expected:    db 0
assert_actual:      db 0
capture_calls:      db 0
capture_sound:      db 0
capture_gain:       db 0
capture_flags:      db 0
observed_ix:        dl 0
expected_ix:        dl spatial_actor
spatial_actor:      ds W3D_ACTOR_SIZE

result_data:
    db "W3SP"
result_checks:              dw 0
result_errors:              dw 0
result_first_phase:         db 0
result_first_reason:        db 0
result_first_expected:      db 0
result_first_actual:        db 0
result_first_vector:        dw 0
result_phase_errors:        ds phase_count
result_vector_count:        dw 0
result_actor_count:         dw 0
result_tile_count:          dw 0
result_schema:              db 0
result_reserved:            ds 9
result_end:
