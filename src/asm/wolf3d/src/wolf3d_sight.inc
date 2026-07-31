; Planar Wolf3D gameplay visibility routines.
;
; Public ABI for w3d_CheckLine and w3d_CheckSight:
;   IX -> W3D_SIGHT_ACTOR_* view
;   IY -> W3D_SIGHT_CTX_* context
;   A=1 and Z clear when visible, A=0 and Z set when blocked
;   carry clear for every valid-contract call
;   BC, DE, HL, IX, IY and all shadow GP registers preserved
;   AF and AF' destroyed
;
; Coordinates must satisfy 0 <= coordinate < 64<<16. The hot trace
; deliberately reduces them to 8.8. The actor's cached tile bytes are not
; trusted; tiles are derived from the coordinate view.

    include "wolf3d_world.inc"
    include "wolf3d_math.inc"

w3d_CheckLine:
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_load_sight_inputs
    call w3d_canonicalize_trace
    call w3d_scan_x_boundaries
    or a
    jr z,@return
    call w3d_scan_y_boundaries
@return:
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    or a
    ret

; This is the visual/proximity predicate, not the complete SightPlayer wake-up
; wrapper. w3d_actor_sight_player accepts made-noise immediately for a
; non-ambush actor in a connected area without invoking this line trace;
; ambush actors still take the visual path here with context noise forced off.
w3d_CheckSight:
    push bc
    push de
    push hl
    push ix
    push iy

    ; Area connectivity is authoritative even for proximity/noise.
    ld a,(ix+W3D_SIGHT_ACTOR_AREA)
    cp W3D_NUM_AREAS
    jr nc,@blocked
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,(iy+W3D_SIGHT_CTX_AREAS)
    add hl,de
    ld a,(hl)
    or a
    jr z,@blocked

    call w3d_load_sight_inputs
    call w3d_is_near_exact
    or a
    jr nz,@visible

    ld hl,(w3d_x2)
    ld de,(w3d_x1)
    or a
    sbc.s hl,de
    ld (w3d_delta_x),hl
    ld hl,(w3d_y2)
    ld de,(w3d_y1)
    or a
    sbc.s hl,de
    ld (w3d_delta_y),hl

    ld a,(iy+W3D_SIGHT_CTX_MADENOISE)
    or a
    jr nz,@trace
    ld a,(ix+W3D_SIGHT_ACTOR_DIR)
    call w3d_facing_accepts
    or a
    jr z,@blocked

@trace:
    call w3d_canonicalize_trace
    call w3d_scan_x_boundaries
    or a
    jr z,@blocked
    call w3d_scan_y_boundaries
    or a
    jr z,@blocked
@visible:
    ld a,1
    jr @return
@blocked:
    xor a
@return:
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    or a
    ret

; Cache context pointers and the four positions reduced from 16.16 to 8.8.
w3d_load_sight_inputs:
    ld hl,(iy+W3D_SIGHT_CTX_TILEMAP)
    ld (w3d_map_ptr),hl
    ld hl,(iy+W3D_SIGHT_CTX_DOORS)
    ld (w3d_doors_ptr),hl

    ld a,(ix+W3D_SIGHT_ACTOR_X+1)
    ld (w3d_x1),a
    ld a,(ix+W3D_SIGHT_ACTOR_X+2)
    ld (w3d_x1+1),a
    ld a,(ix+W3D_SIGHT_ACTOR_Y+1)
    ld (w3d_y1),a
    ld a,(ix+W3D_SIGHT_ACTOR_Y+2)
    ld (w3d_y1+1),a
    ld a,(iy+W3D_SIGHT_CTX_PLAYER_X+1)
    ld (w3d_x2),a
    ld a,(iy+W3D_SIGHT_CTX_PLAYER_X+2)
    ld (w3d_x2+1),a
    ld a,(iy+W3D_SIGHT_CTX_PLAYER_Y+1)
    ld (w3d_y2),a
    ld a,(iy+W3D_SIGHT_CTX_PLAYER_Y+2)
    ld (w3d_y2+1),a
    ret

; Exact strict 1.5-tile proximity gate from the original 16.16 endpoints.
w3d_is_near_exact:
    ld hl,(iy+W3D_SIGHT_CTX_PLAYER_X)
    ld de,(ix+W3D_SIGHT_ACTOR_X)
    or a
    sbc hl,de
    jr nc,@x_magnitude
    ld hl,(ix+W3D_SIGHT_ACTOR_X)
    ld de,(iy+W3D_SIGHT_CTX_PLAYER_X)
    or a
    sbc hl,de
@x_magnitude:
    ld de,W3D_MIN_SIGHT_16_16
    or a
    sbc hl,de
    jr nc,@not_near

    ld hl,(iy+W3D_SIGHT_CTX_PLAYER_Y)
    ld de,(ix+W3D_SIGHT_ACTOR_Y)
    or a
    sbc hl,de
    jr nc,@y_magnitude
    ld hl,(ix+W3D_SIGHT_ACTOR_Y)
    ld de,(iy+W3D_SIGHT_CTX_PLAYER_Y)
    or a
    sbc hl,de
@y_magnitude:
    ld de,W3D_MIN_SIGHT_16_16
    or a
    sbc hl,de
    jr nc,@not_near
    ld a,1
    ret
@not_near:
    xor a
    ret

; Give both directions of the same segment one deterministic 8.8 walk.
; CheckSight computes and stores its actor-to-player deltas before this call.
w3d_canonicalize_trace:
    ld hl,(w3d_x1)
    ld de,(w3d_x2)
    or a
    sbc.s hl,de
    jr c,@ordered
    jr nz,@swap
    ld hl,(w3d_y1)
    ld de,(w3d_y2)
    or a
    sbc.s hl,de
    jr c,@ordered
    ret z
@swap:
    ld hl,(w3d_x1)
    ld de,(w3d_x2)
    ld (w3d_x1),de
    ld (w3d_x2),hl
    ld hl,(w3d_y1)
    ld de,(w3d_y2)
    ld (w3d_y1),de
    ld (w3d_y2),hl
@ordered:
    ret

w3d_scan_x_boundaries:
    ld a,(w3d_x1+1)
    ld b,a
    ld a,(w3d_x2+1)
    cp b
    jp z,w3d_scan_clear
    ld (w3d_target_tile),a
    jr c,@west

    ld a,1
    ld (w3d_major_step),a
    ld a,(w3d_x1)
    cpl
    ld e,a
    ld d,0
    inc.s de
    jr @direction_ready
@west:
    ld a,0xff
    ld (w3d_major_step),a
    ld a,(w3d_x1)
    ld e,a
    ld d,0
@direction_ready:
    ld (w3d_partial),de

    ld hl,(w3d_x2)
    ld de,(w3d_x1)
    or a
    sbc.s hl,de
    call w3d_abs_hl
    ex de,hl
    ld hl,(w3d_y2)
    ld bc,(w3d_y1)
    or a
    sbc.s hl,bc
    call w3d_slope8
    ld (w3d_minor_step),hl
    ld de,(w3d_partial)
    call w3d_step_partial
    ld de,(w3d_y1)
    add.s hl,de
    ld (w3d_crossing),hl

    ld a,(w3d_x1+1)
    ld b,a
    ld a,(w3d_major_step)
    add a,b
    ld (w3d_current_tile),a
@loop:
    ld b,a
    ld a,(w3d_crossing+1)
    ld c,a
    ld a,b
    ld (w3d_test_x),a
    ld a,c
    ld (w3d_test_y),a
    call w3d_map_read
    ld d,a
    ld a,d
    call w3d_tile_is_clear
    or a
    ret z
    ld a,(w3d_current_tile)
    ld b,a
    ld a,(w3d_target_tile)
    cp b
    jp z,w3d_scan_clear
    ld a,(w3d_major_step)
    add a,b
    ld (w3d_current_tile),a
    ld hl,(w3d_crossing)
    ld de,(w3d_minor_step)
    add.s hl,de
    ld (w3d_crossing),hl
    ld a,(w3d_current_tile)
    jr @loop

w3d_scan_y_boundaries:
    ld a,(w3d_y1+1)
    ld b,a
    ld a,(w3d_y2+1)
    cp b
    jp z,w3d_scan_clear
    ld (w3d_target_tile),a
    jr c,@north

    ld a,1
    ld (w3d_major_step),a
    ld a,(w3d_y1)
    cpl
    ld e,a
    ld d,0
    inc.s de
    jr @direction_ready
@north:
    ld a,0xff
    ld (w3d_major_step),a
    ld a,(w3d_y1)
    ld e,a
    ld d,0
@direction_ready:
    ld (w3d_partial),de

    ld hl,(w3d_y2)
    ld de,(w3d_y1)
    or a
    sbc.s hl,de
    call w3d_abs_hl
    ex de,hl
    ld hl,(w3d_x2)
    ld bc,(w3d_x1)
    or a
    sbc.s hl,bc
    call w3d_slope8
    ld (w3d_minor_step),hl
    ld de,(w3d_partial)
    call w3d_step_partial
    ld de,(w3d_x1)
    add.s hl,de
    ld (w3d_crossing),hl

    ld a,(w3d_y1+1)
    ld b,a
    ld a,(w3d_major_step)
    add a,b
    ld (w3d_current_tile),a
@loop:
    ld c,a
    ld a,(w3d_crossing+1)
    ld b,a
    ld a,b
    ld (w3d_test_x),a
    ld a,c
    ld (w3d_test_y),a
    call w3d_map_read
    ld d,a
    ld a,d
    call w3d_tile_is_clear
    or a
    ret z
    ld a,(w3d_current_tile)
    ld b,a
    ld a,(w3d_target_tile)
    cp b
    jp z,w3d_scan_clear
    ld a,(w3d_major_step)
    add a,b
    ld (w3d_current_tile),a
    ld hl,(w3d_crossing)
    ld de,(w3d_minor_step)
    add.s hl,de
    ld (w3d_crossing),hl
    ld a,(w3d_current_tile)
    jr @loop

w3d_scan_clear:
    ld a,1
    or a
    ret

; Read tile at B=x, C=y. Destroys AF, DE, HL; preserves BC.
w3d_map_read:
    ld a,c
    ld e,a
    ld d,0
    inc de
    dec.s de
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    ld a,e
    add a,b
    ld e,a
    jr nc,@offset_ready
    inc d
@offset_ready:
    ld hl,(w3d_map_ptr)
    add hl,de
    ld a,(hl)
    ret

; A=tile. The tested map coordinate is in w3d_test_x/y. Door geometry is
; resolved from the door's own orientation and the original 16.16 endpoints,
; independent of which DDA boundary first entered the tile.
w3d_tile_is_clear:
    or a
    jp z,w3d_scan_clear
    cp W3D_TILE_DOOR_MIN
    jr c,@blocked
    cp W3D_TILE_DOOR_MAX+1
    jr nc,@blocked
    and W3D_TILE_DOOR_MASK
    ld d,a
    ld e,W3D_DOOR_SIZE
    mlt de
    inc de
    dec.s de
    ld hl,(w3d_doors_ptr)
    add hl,de
    inc hl
    inc hl
    ld a,(hl)
    ld b,a
    inc hl
    inc hl
    inc hl
    ld a,(hl)
    ld (w3d_exact_position),a
    inc hl
    ld a,(hl)
    ld (w3d_exact_position+1),a
    call w3d_door_fraction_exact
    or a
    jp z,w3d_scan_clear
    ld hl,(w3d_exact_fraction)
    ld de,(w3d_exact_position)
    or a
    sbc.s hl,de
    jp c,w3d_scan_clear
    jp z,w3d_scan_clear
@blocked:
    xor a
    ret

; Find the exact tile-relative fraction where the original 16.16 segment
; crosses a door's center plane.
;
; input:  B=door.vertical
; output: A=1 and w3d_exact_fraction set when the center plane crosses the
;         tested door tile; A=0 otherwise
; destroys AF, BC, DE, HL
w3d_door_fraction_exact:
    ld a,b
    ld (w3d_exact_vertical),a
    or a
    jr z,@horizontal

    ld hl,(ix+W3D_SIGHT_ACTOR_X)
    ld (w3d_exact_major1),hl
    ld hl,(iy+W3D_SIGHT_CTX_PLAYER_X)
    ld (w3d_exact_major2),hl
    ld hl,(ix+W3D_SIGHT_ACTOR_Y)
    ld (w3d_exact_minor1),hl
    ld hl,(iy+W3D_SIGHT_CTX_PLAYER_Y)
    ld (w3d_exact_minor2),hl
    ld a,(w3d_test_x)
    jr @plane
@horizontal:
    ld hl,(ix+W3D_SIGHT_ACTOR_Y)
    ld (w3d_exact_major1),hl
    ld hl,(iy+W3D_SIGHT_CTX_PLAYER_Y)
    ld (w3d_exact_major2),hl
    ld hl,(ix+W3D_SIGHT_ACTOR_X)
    ld (w3d_exact_minor1),hl
    ld hl,(iy+W3D_SIGHT_CTX_PLAYER_X)
    ld (w3d_exact_minor2),hl
    ld a,(w3d_test_y)
@plane:
    ld (w3d_exact_plane+2),a
    xor a
    ld (w3d_exact_plane),a
    ld a,0x80
    ld (w3d_exact_plane+1),a

    ; Canonicalize by increasing major coordinate so reversing the segment
    ; cannot change integer rounding.
    ld hl,(w3d_exact_major1)
    ld de,(w3d_exact_major2)
    or a
    sbc hl,de
    jr c,@ordered
    jp z,@not_crossed
    ld hl,(w3d_exact_major1)
    ld de,(w3d_exact_major2)
    ld (w3d_exact_major1),de
    ld (w3d_exact_major2),hl
    ld hl,(w3d_exact_minor1)
    ld de,(w3d_exact_minor2)
    ld (w3d_exact_minor1),de
    ld (w3d_exact_minor2),hl
@ordered:
    ld hl,(w3d_exact_major2)
    ld de,(w3d_exact_major1)
    or a
    sbc hl,de
    ld (w3d_exact_denominator),hl

    ld hl,(w3d_exact_plane)
    ld de,(w3d_exact_major1)
    or a
    sbc hl,de
    jp c,@not_crossed
    ld (w3d_exact_numerator),hl
    ld de,(w3d_exact_denominator)
    or a
    sbc hl,de
    jr c,@plane_in_segment
    jr z,@plane_in_segment
    jp @not_crossed

@plane_in_segment:
    ld hl,(w3d_exact_minor2)
    ld de,(w3d_exact_minor1)
    or a
    sbc hl,de
    jr nc,@positive_minor
    ld hl,(w3d_exact_minor1)
    ld de,(w3d_exact_minor2)
    or a
    sbc hl,de
    ld a,1
    ld (w3d_exact_negative),a
    jr @minor_ready
@positive_minor:
    xor a
    ld (w3d_exact_negative),a
@minor_ready:
    ld (w3d_exact_bits),hl
    call w3d_muldiv_u24

    ld a,(w3d_exact_negative)
    or a
    jr z,@add_offset
    ld a,(w3d_exact_remainder)
    ld b,a
    ld a,(w3d_exact_remainder+1)
    or b
    ld b,a
    ld a,(w3d_exact_remainder+2)
    or b
    jr z,@negative_offset_ready
    ld hl,(w3d_exact_quotient)
    inc hl
    ld (w3d_exact_quotient),hl
@negative_offset_ready:
    ld hl,(w3d_exact_minor1)
    ld de,(w3d_exact_quotient)
    or a
    sbc hl,de
    jr @intercept_ready
@add_offset:
    ld hl,(w3d_exact_minor1)
    ld de,(w3d_exact_quotient)
    add hl,de
@intercept_ready:
    ld (w3d_exact_intercept),hl
    ld a,(w3d_exact_vertical)
    or a
    ld a,(w3d_test_x)
    jr z,@minor_tile_ready
    ld a,(w3d_test_y)
@minor_tile_ready:
    ld b,a
    ld a,(w3d_exact_intercept+2)
    cp b
    jp nz,@not_crossed
    ld a,(w3d_exact_intercept)
    ld (w3d_exact_fraction),a
    ld a,(w3d_exact_intercept+1)
    ld (w3d_exact_fraction+1),a
    ld a,1
    ret
@not_crossed:
    xor a
    ret

; Exact unsigned floor(bits*numerator/denominator), all 24-bit. This
; shift/add division never materializes the possible 44-bit product.
; numerator <= denominator and bits < 64<<16, so the reduction sum fits
; in 24 bits. Quotient and remainder are written to scratch.
w3d_muldiv_u24:
    ld hl,0
    ld (w3d_exact_quotient),hl
    ld (w3d_exact_remainder),hl
    ld c,24
@bit_loop:
    ld hl,(w3d_exact_bits)
    add hl,hl
    ld (w3d_exact_bits),hl
    ld a,0
    adc a,0
    ld (w3d_exact_bit),a

    ld hl,(w3d_exact_quotient)
    add hl,hl
    ld (w3d_exact_quotient),hl
    ld hl,(w3d_exact_remainder)
    add hl,hl
    ld a,(w3d_exact_bit)
    or a
    jr z,@reduce
    ld de,(w3d_exact_numerator)
    add hl,de
@reduce:
    ld de,(w3d_exact_denominator)
@reduce_again:
    or a
    sbc hl,de
    jr c,@reduced
    ld (w3d_exact_remainder),hl
    ld hl,(w3d_exact_quotient)
    inc hl
    ld (w3d_exact_quotient),hl
    ld hl,(w3d_exact_remainder)
    jr @reduce_again
@reduced:
    add hl,de
    ld (w3d_exact_remainder),hl
    dec c
    jr nz,@bit_loop
    ret

w3d_abs_hl:
    bit 7,h
    ret z
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
    ret

; Input A=direction. Destroys AF, DE, HL. Returns boolean A.
w3d_facing_accepts:
    cp W3D_DIR_NODIR
    jp nc,w3d_scan_clear
    cp W3D_DIR_EAST
    jr z,@east
    cp W3D_DIR_NORTHEAST
    jr z,@northeast
    cp W3D_DIR_NORTH
    jr z,@north
    cp W3D_DIR_NORTHWEST
    jr z,@northwest
    cp W3D_DIR_WEST
    jr z,@west
    cp W3D_DIR_SOUTHWEST
    jr z,@southwest
    cp W3D_DIR_SOUTH
    jr z,@south
    ; southeast
    ld hl,(w3d_delta_x)
    ld de,(w3d_delta_y)
    add.s hl,de
    jr @nonnegative
@east:
    ld hl,(w3d_delta_x)
    jr @nonnegative
@northeast:
    ld hl,(w3d_delta_x)
    ld de,(w3d_delta_y)
    or a
    sbc.s hl,de
    jr @nonnegative
@north:
    ld hl,(w3d_delta_y)
    jr @nonpositive
@northwest:
    ld hl,(w3d_delta_x)
    ld de,(w3d_delta_y)
    add.s hl,de
    jr @nonpositive
@west:
    ld hl,(w3d_delta_x)
    jr @nonpositive
@southwest:
    ld hl,(w3d_delta_y)
    ld de,(w3d_delta_x)
    or a
    sbc.s hl,de
    jr @nonnegative
@south:
    ld hl,(w3d_delta_y)
@nonnegative:
    bit 7,h
    jp z,w3d_scan_clear
    xor a
    ret
@nonpositive:
    bit 7,h
    jp nz,w3d_scan_clear
    ld a,h
    or l
    jp z,w3d_scan_clear
    xor a
    ret

; Private non-reentrant scratch. Gameplay is single-threaded on the eZ80.
w3d_map_ptr:          dl 0
w3d_doors_ptr:        dl 0
w3d_x1:               dl 0
w3d_y1:               dl 0
w3d_x2:               dl 0
w3d_y2:               dl 0
w3d_delta_x:          dl 0
w3d_delta_y:          dl 0
w3d_minor_step:       dl 0
w3d_partial:          dl 0
w3d_crossing:         dl 0
w3d_test_x:           db 0
w3d_test_y:           db 0
w3d_current_tile:     db 0
w3d_target_tile:      db 0
w3d_major_step:       db 0
w3d_exact_vertical:   db 0
w3d_exact_negative:   db 0
w3d_exact_bit:        db 0
w3d_exact_position:   dl 0
w3d_exact_fraction:   dl 0
w3d_exact_plane:      dl 0
w3d_exact_major1:     dl 0
w3d_exact_major2:     dl 0
w3d_exact_minor1:     dl 0
w3d_exact_minor2:     dl 0
w3d_exact_numerator:  dl 0
w3d_exact_denominator: dl 0
w3d_exact_bits:       dl 0
w3d_exact_quotient:   dl 0
w3d_exact_remainder:  dl 0
w3d_exact_intercept:  dl 0
