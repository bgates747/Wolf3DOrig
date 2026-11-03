; Finite full-MOS regression for the production Wolf3D VDPlet serializer.
; It emits a complete generation-1 snapshot, an exact retry of that immutable
; batch, and a generation-2 dirty update built from changes accumulated while
; generation 1 was in flight.

    .assume adl=1
    .org 040000h
    jp start
    .align 64
    db "MOS",0,1

mos_fopen:          equ 0x0a
mos_fclose:         equ 0x0b
mos_fwrite:         equ 0x1b
fa_write:           equ 0x02
fa_create_always:   equ 0x08

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    include "wolf3d_world.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_vdplet_contract.inc"

W3D_VDPLET_WORKSPACE_BUFFER: equ 07100h
W3D_VDPLET_UPDATE_BUFFER:    equ 07101h

    include "wolf3d_actors.inc"
    include "wolf3d_vdplet_batch.inc"

start:
    push af
    push bc
    push de
    push ix
    push iy
    xor a
    ld (fixture_result_code),a
    call fixture_seed_world
    call fixture_run
    call fixture_write_result
    pop iy
    pop ix
    pop de
    pop bc
    pop af
    ld hl,0
    ret

fixture_run:
    call w3d_vdplet_batch_initialize

; Existing dirt is captured by the full batch and consumed on first submit.
    ld a,1
    ld (w3d_door_dirty+2),a
    ld (w3d_static_dirty+2),a
    ld (w3d_player_dirty),a
    ld (w3d_player_weapon_shape_dirty),a
    ld (w3d_world_dirty),a
    ld a,W3D_ACTOR_DIRTY_SET
    ld (w3d_actor_dirty+2),a
    ld a,03fh
    ld (w3d_hud_dirty),a

    call w3d_vdplet_batch_prepare
    jp c,fixture_lifecycle_failed
    ld (fixture_full_bytes),de
    ld hl,fixture_full_name
    call fixture_save_prepared
    jp c,fixture_file_failed
    call w3d_vdplet_batch_mark_submitted
    jp c,fixture_lifecycle_failed

; A live requested RUN owns the frozen batch. Neither a second prepare nor a
; level-transition full request may mutate or reacquire it.
    call w3d_vdplet_batch_prepare
    jp nc,fixture_lifecycle_failed
    ld a,(w3d_vdplet_batch_status)
    cp W3D_VDPLET_BATCH_STATUS_LIFECYCLE
    jp nz,fixture_lifecycle_failed
    call w3d_vdplet_batch_require_full
    jp nc,fixture_lifecycle_failed
    ld a,(w3d_vdplet_batch_status)
    cp W3D_VDPLET_BATCH_STATUS_LIFECYCLE
    jp nz,fixture_lifecycle_failed

; These changes occur while generation 1 owns the immutable batch. They must
; survive both the failed first attempt and the exact retry submission.
    ld a,1
    ld (w3d_pushwall_dirty),a
    ld (w3d_pushwall_payload+W3P_PUSHWALL_STATUS),a
    ld a,10
    ld (w3d_pushwall_payload+W3P_PUSHWALL_ORIGIN_X),a
    ld (w3d_pushwall_payload+W3P_PUSHWALL_ORIGIN_Y),a
    ld (w3d_pushwall_payload+W3P_PUSHWALL_CURRENT_X),a
    ld (w3d_pushwall_payload+W3P_PUSHWALL_CURRENT_Y),a
    ld a,32
    ld (w3d_pushwall_payload+W3P_PUSHWALL_POSITION),a
    ld a,4
    ld (w3d_pushwall_payload+W3P_PUSHWALL_TEXTURE),a
    ld a,1
    ld (w3d_door_dirty+0),a
    ld (w3d_static_dirty+1),a
    ld (w3d_player_dirty),a
    ld (w3d_player_weapon_shape_dirty),a
    ld (w3d_world_dirty),a
    ld a,W3D_ACTOR_DIRTY_REMOVE
    ld (w3d_actor_dirty+1),a
    ld a,011h
    ld (w3d_hud_dirty),a
    ld a,040h
    ld (w3d_player_pose+0),a
    ld a,080h
    ld (w3d_doors+W3D_DOOR_POSITION+0),a
    ld a,0ffh
    ld (w3d_statics+W3D_STATIC_SIZE+W3D_STATIC_SHAPENUM+0),a
    ld (w3d_statics+W3D_STATIC_SIZE+W3D_STATIC_SHAPENUM+1),a
    ld (w3d_player_weapon_shape+0),a
    ld (w3d_player_weapon_shape+1),a
    ld a,73
    ld (w3d_player_health),a
    ld a,2
    ld (w3d_player_face_frame),a

    call w3d_vdplet_batch_accept_failure
    jp c,fixture_lifecycle_failed
    call w3d_vdplet_batch_prepare
    jp c,fixture_lifecycle_failed
    ld hl,fixture_retry_name
    call fixture_save_prepared
    jp c,fixture_file_failed
    call w3d_vdplet_batch_mark_submitted
    jp c,fixture_lifecycle_failed
    call fixture_capture_dirty_mask
    ld (fixture_retry_dirty_mask),a
    call w3d_vdplet_batch_accept_success
    jp c,fixture_lifecycle_failed

; Generation 2 is the accumulated delta, not a rebuilt generation-1 batch.
    call w3d_vdplet_batch_prepare
    jp c,fixture_lifecycle_failed
    ld (fixture_dirty_bytes),de
    ld hl,fixture_dirty_name
    call fixture_save_prepared
    jp c,fixture_file_failed
    call w3d_vdplet_batch_mark_submitted
    jp c,fixture_lifecycle_failed
    call w3d_vdplet_batch_accept_success
    jp c,fixture_lifecycle_failed
    call fixture_capture_dirty_mask
    ld (fixture_final_dirty_mask),a

; No generation-3 batch may be fabricated from an empty dirty state.
    call w3d_vdplet_batch_prepare
    jr c,@expected_empty
    jp fixture_lifecycle_failed
@expected_empty:
    ld a,(w3d_vdplet_batch_status)
    ld (fixture_empty_status),a
    ret

fixture_lifecycle_failed:
    ld a,1
    ld (fixture_result_code),a
    ret

fixture_file_failed:
    ld a,2
    ld (fixture_result_code),a
    ret

; Bit 0 door, 1 actor, 2 static, 3 player, 4 HUD, 5 view, 6 world,
; bit 7 pushwall.
fixture_capture_dirty_mask:
    ld c,0
    ld a,(w3d_door_dirty+0)
    or a
    jr z,@actor
    set 0,c
@actor:
    ld a,(w3d_actor_dirty+1)
    or a
    jr z,@static
    set 1,c
@static:
    ld a,(w3d_static_dirty+1)
    or a
    jr z,@player
    set 2,c
@player:
    ld a,(w3d_player_dirty)
    or a
    jr z,@hud
    set 3,c
@hud:
    ld a,(w3d_hud_dirty)
    or a
    jr z,@view
    set 4,c
@view:
    ld a,(w3d_player_weapon_shape_dirty)
    or a
    jr z,@world
    set 5,c
@world:
    ld a,(w3d_world_dirty)
    or a
    jr z,@pushwall
    set 6,c
@pushwall:
    ld a,(w3d_pushwall_dirty)
    or a
    jr z,@done
    set 7,c
@done:
    ld a,c
    ret

; HL=filename; current prepared buffer and byte count are authoritative.
fixture_save_prepared:
    ld (fixture_save_name),hl
    ld hl,w3d_vdplet_batch_buffer
    ld (fixture_save_source),hl
    ld de,(w3d_vdplet_batch_bytes)
    ld (fixture_save_bytes),de
    ld hl,(fixture_save_name)
    ld c,fa_write | fa_create_always
    MOSCALL mos_fopen
    or a
    jr z,@failed
    ld (fixture_file_handle),a
    ld c,a
    ld hl,(fixture_save_source)
    ld de,(fixture_save_bytes)
    MOSCALL mos_fwrite
    push af
    ld a,(fixture_file_handle)
    ld c,a
    MOSCALL mos_fclose
    pop af
    or a
    jr nz,@failed
    or a
    ret
@failed:
    scf
    ret

fixture_write_result:
    ld a,(fixture_result_code)
    ld (fixture_result+4),a
    ld a,(fixture_retry_dirty_mask)
    ld (fixture_result+5),a
    ld a,(fixture_final_dirty_mask)
    ld (fixture_result+6),a
    ld a,(fixture_empty_status)
    ld (fixture_result+7),a
    ld a,(w3d_vdplet_batch_last_generation+0)
    ld (fixture_result+8),a
    ld a,(w3d_vdplet_batch_last_generation+1)
    ld (fixture_result+9),a
    ld a,(fixture_full_bytes+0)
    ld (fixture_result+10),a
    ld a,(fixture_full_bytes+1)
    ld (fixture_result+11),a
    ld a,(fixture_dirty_bytes+0)
    ld (fixture_result+12),a
    ld a,(fixture_dirty_bytes+1)
    ld (fixture_result+13),a
    ld hl,fixture_result_name
    ld c,fa_write | fa_create_always
    MOSCALL mos_fopen
    or a
    ret z
    ld (fixture_file_handle),a
    ld c,a
    ld hl,fixture_result
    ld de,fixture_result_end-fixture_result
    MOSCALL mos_fwrite
    ld a,(fixture_file_handle)
    ld c,a
    MOSCALL mos_fclose
    ret

fixture_seed_world:
    ld hl,w3d_pushwall_payload
    ld de,w3d_pushwall_payload+1
    ld bc,W3P_PUSHWALL_BYTES-1
    xor a
    ld (hl),a
    ldir
    ld (w3d_pushwall_dirty),a
    ld hl,w3d_fixture_initial_player_pose
    ld de,w3d_player_pose
    ld bc,10
    ldir
    ld hl,w3d_fixture_initial_doors
    ld de,w3d_doors
    ld bc,w3d_fixture_initial_doors_end-w3d_fixture_initial_doors
    ldir
    ld hl,w3d_fixture_initial_statics
    ld de,w3d_statics
    ld bc,w3d_fixture_initial_statics_end-w3d_fixture_initial_statics
    ldir
    ld a,W3D_FIXTURE_STATIC_COUNT & 0ffh
    ld (w3d_static_count+0),a
    ld a,W3D_FIXTURE_STATIC_COUNT / 256
    ld (w3d_static_count+1),a
    call w3d_initialize_actor_state
    ld a,100
    ld (w3d_player_health),a
    xor a
    ld (w3d_player_face_frame),a
    ld a,8
    ld (w3d_player_ammo),a
    ld a,1
    ld (w3d_player_weapon),a
    ld a,3
    ld (w3d_player_lives),a
    xor a
    ld (w3d_player_key_flags),a
    ld (w3d_level_requested_index),a
    ld (w3d_player_score+0),a
    ld (w3d_player_score+1),a
    ld (w3d_player_score+2),a
    ld (w3d_player_score+3),a
    ld a,0ffh
    ld (w3d_player_weapon_shape+0),a
    ld (w3d_player_weapon_shape+1),a
    ret

; Motion-owned helper used by the shared serializer.
w3d_door_pointer_from_index:
    ld d,a
    ld e,W3D_DOOR_SIZE
    mlt de
    inc de
    dec.s de
    ld hl,w3d_doors
    add hl,de
    push hl
    pop ix
    ret

fixture_full_name:        asciz "full.bin"
fixture_retry_name:       asciz "retry.bin"
fixture_dirty_name:       asciz "dirty.bin"
fixture_result_name:      asciz "batch.dat"
fixture_save_name:        dl 0
fixture_save_source:      dl 0
fixture_save_bytes:       dl 0
fixture_file_handle:      db 0
fixture_result_code:      db 0
fixture_retry_dirty_mask: db 0
fixture_final_dirty_mask: db 0
fixture_empty_status:     db 0
fixture_full_bytes:       dl 0
fixture_dirty_bytes:      dl 0

fixture_result:
    db "W3B1"
    ds 10
    dw W3P_SCHEMA_VERSION
fixture_result_end:

; Minimal motion/player storage consumed by the production serializer.
w3d_player_pose:                 ds 10
w3d_player_dirty:                db 0
w3d_world_dirty:                 db 0
w3d_player_key_flags:            db 0
w3d_player_health:               db 100
w3d_player_face_frame:           db 0
w3d_player_ammo:                 db 8
w3d_player_weapon:               db 1
w3d_player_lives:                db 3
w3d_player_score:                ds 4
w3d_hud_dirty:                  db 0
w3d_player_weapon_shape:         dw -1
w3d_player_weapon_shape_dirty:   db 0
w3d_level_requested_index:       db 0
w3d_pushwall_payload:             ds W3P_PUSHWALL_BYTES
w3d_pushwall_dirty:               db 0

w3d_doors:                       ds W3D_MAX_DOORS*W3D_DOOR_SIZE
w3d_door_dirty:                  ds W3D_MAX_DOORS
w3d_statics:                     ds W3D_MAX_STATICS*W3D_STATIC_SIZE
w3d_static_dirty:                ds W3D_MAX_STATICS
w3d_static_count:                dw W3D_FIXTURE_STATIC_COUNT

; Additional motion-owned fields referenced by wolf3d_actors.inc regressions.
w3d_clip_x_low:                  db 0
w3d_clip_x_high:                 db 0
w3d_clip_y_low:                  db 0
w3d_clip_y_high:                 db 0
