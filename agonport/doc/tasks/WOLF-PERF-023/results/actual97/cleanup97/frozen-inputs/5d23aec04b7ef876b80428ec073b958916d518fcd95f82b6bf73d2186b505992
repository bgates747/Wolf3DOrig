; =============================================================================
; Wolf3D mono positional-audio adapter.
;
; The original game rotates a world-space source into the listener frame and
; indexes WL_GAME.C's 15x30 left/right attenuation tables.  Agon output is
; mono, so wolf3d_audio_assets.inc supplies the generated, source-grounded
; mono collapse of those tables.  This file deliberately reuses the reduced
; Q8/Q12 transform already proven by the CPU actor projection path.
;
; Public producer helpers:
;   w3d_audio_request_actor: A=logical sound id, IX=actor
;   w3d_audio_request_tile:  A=logical sound id, B=tile x, C=tile y
;
; Both submit a positioned request through w3d_audio_request with B=gain and
; C bit 0 set.  IX is preserved by the actor entry point; other GP registers
; and flags are caller-saved.
; =============================================================================

; WL_MAIN.C's FOCALLENGTH (0x5700 in 16.16) reduced to this adapter's Q8.
; Original SetSoundLoc measures from the renderer's focal point rather than
; the player center, which is exactly a +0x57 bias on listener-forward.
W3D_AUDIO_FOCAL_Q8: equ 057h

w3d_audio_request_actor:
    ld (w3d_audio_spatial_sound),a
    push ix
    call w3d_actor_load_relative_q8
    call w3d_audio_request_relative_q8
    pop ix
    ret

; Build signed (tile-center - player)>>8 without materializing a 32-bit world
; coordinate.  The discarded low fractional byte still participates in the
; borrow, matching the actor-relative reduction.
w3d_audio_request_tile:
    ld (w3d_audio_spatial_sound),a
    ld a,b
    ld (w3d_audio_spatial_tile_x),a
    ld a,c
    ld (w3d_audio_spatial_tile_y),a

    ld a,(w3d_player_pose+0)
    ld d,a
    xor a
    sub d
    ld a,(w3d_player_pose+1)
    ld d,a
    ld a,080h
    sbc a,d
    ld (w3d_actor_projection_rel_x+0),a
    ld a,(w3d_player_pose+2)
    ld d,a
    ld a,(w3d_audio_spatial_tile_x)
    sbc a,d
    ld (w3d_actor_projection_rel_x+1),a

    ld a,(w3d_player_pose+4)
    ld d,a
    xor a
    sub d
    ld a,(w3d_player_pose+5)
    ld d,a
    ld a,080h
    sbc a,d
    ld (w3d_actor_projection_rel_y+0),a
    ld a,(w3d_player_pose+6)
    ld d,a
    ld a,(w3d_audio_spatial_tile_y)
    sbc a,d
    ld (w3d_actor_projection_rel_y+1),a
    jp w3d_audio_request_relative_q8

; Consume w3d_actor_projection_rel_{x,y} as signed Q8 map coordinates.
; Original SetSoundLoc names the listener-forward result x and the lateral
; result y.  Its table row is abs(forward), while its column retains the sign
; of lateral so stereo panning can differ.  The generated mono table keeps
; that exact indexing even though left/right are collapsed to one gain.
w3d_audio_request_relative_q8:
    call w3d_actor_load_heading_q12

; forward = relx*cos + rely*(-sin)
    ld hl,0
    ld a,(w3d_actor_projection_rel_x+0)
    ld l,a
    ld a,(w3d_actor_projection_rel_x+1)
    ld h,a
    ld de,0
    ld a,(w3d_actor_projection_cos+0)
    ld e,a
    ld a,(w3d_actor_projection_cos+1)
    ld d,a
    call w3d_actor_mul_q8_q12
    ld a,l
    ld (w3d_audio_spatial_term+0),a
    ld a,h
    ld (w3d_audio_spatial_term+1),a

    ld hl,0
    ld a,(w3d_actor_projection_rel_y+0)
    ld l,a
    ld a,(w3d_actor_projection_rel_y+1)
    ld h,a
    ld de,0
    ld a,(w3d_actor_projection_forward_y+0)
    ld e,a
    ld a,(w3d_actor_projection_forward_y+1)
    ld d,a
    call w3d_actor_mul_q8_q12
    ld de,0
    ld a,(w3d_audio_spatial_term+0)
    ld e,a
    ld a,(w3d_audio_spatial_term+1)
    ld d,a
    add.s hl,de
    ld de,W3D_AUDIO_FOCAL_Q8
    add.s hl,de

; Row = min(abs(signed high byte),14).  NEG's -128 case is harmless because
; every magnitude >=15 takes the clamp.
    ld a,h
    bit 7,a
    jr z,@forward_absolute
    neg
@forward_absolute:
    cp 15
    jr c,@forward_clamped
    ld a,14
@forward_clamped:
    ld (w3d_audio_spatial_row),a

; lateral = rely*cos + relx*sin = rely*cos - relx*(-sin)
    ld hl,0
    ld a,(w3d_actor_projection_rel_y+0)
    ld l,a
    ld a,(w3d_actor_projection_rel_y+1)
    ld h,a
    ld de,0
    ld a,(w3d_actor_projection_cos+0)
    ld e,a
    ld a,(w3d_actor_projection_cos+1)
    ld d,a
    call w3d_actor_mul_q8_q12
    ld a,l
    ld (w3d_audio_spatial_term+0),a
    ld a,h
    ld (w3d_audio_spatial_term+1),a

    ld hl,0
    ld a,(w3d_actor_projection_rel_x+0)
    ld l,a
    ld a,(w3d_actor_projection_rel_x+1)
    ld h,a
    ld de,0
    ld a,(w3d_actor_projection_forward_y+0)
    ld e,a
    ld a,(w3d_actor_projection_forward_y+1)
    ld d,a
    call w3d_actor_mul_q8_q12
    ex de,hl
    ld hl,0
    ld a,(w3d_audio_spatial_term+0)
    ld l,a
    ld a,(w3d_audio_spatial_term+1)
    ld h,a
    or a
    sbc.s hl,de

; Column = clamp(signed high byte,-15,14)+15, yielding 0..29.
    ld a,h
    bit 7,a
    jr z,@lateral_nonnegative
    cp 0f1h
    jr nc,@lateral_add_bias
    xor a
    jr @lateral_clamped
@lateral_nonnegative:
    cp 15
    jr c,@lateral_add_bias
    ld a,29
    jr @lateral_clamped
@lateral_add_bias:
    add a,15
@lateral_clamped:
    ld (w3d_audio_spatial_column),a

; Offset = row*30 + column.  The table is only 450 bytes, but build the
; offset explicitly with 16-bit operations so no eZ80 upper register byte is
; ever significant.
    ld hl,0
    ld a,(w3d_audio_spatial_row)
    ld l,a
    add.s hl,hl                    ; 2*row
    ld d,h
    ld e,l
    add.s hl,hl                    ; 4*row
    add.s hl,hl                    ; 8*row
    add.s hl,hl                    ; 16*row
    add.s hl,hl                    ; 32*row
    or a
    sbc.s hl,de                    ; 30*row
    ld de,0
    ld a,(w3d_audio_spatial_column)
    ld e,a
    add.s hl,de
    ld de,w3d_audio_mono_gain_table
    add hl,de
    ld b,(hl)
    ld a,(w3d_audio_spatial_sound)
    ld c,1                         ; positioned metadata
    jp w3d_audio_request

w3d_audio_spatial_sound:
    db 0
w3d_audio_spatial_tile_x:
    db 0
w3d_audio_spatial_tile_y:
    db 0
w3d_audio_spatial_term:
    dw 0
w3d_audio_spatial_row:
    db 0
w3d_audio_spatial_column:
    db 0
