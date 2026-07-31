; Generated-vector regression for w3d_CheckLine and w3d_CheckSight.
;
; dda_vectors.bin:
;   +0 uint32 record count
;   repeated 32-byte records, see scripts/generate_dda_vectors.py
;
; dda_result.bin (34 bytes):
;   +0 "W3R1"
;   +4 uint24 records
;   +7 uint24 errors
;  +10 uint24 CheckLine errors
;  +13 uint24 CheckSight errors
;  +16 uint24 first failing record index (0xffff when none)
;  +19 expected A, actual A, opcode, actual carry
;  +23 uint24 first failing sequence id
;  +26 uint24 CheckLine mixed-loop milliseconds
;  +29 uint24 CheckSight mixed-loop milliseconds
;  +32 uint16 reserved

    assume adl=1
    org 0x040000
    jp start
    align 64
    db "MOS",0,1

    include "wolf3d_sight.inc"

mos_fopen:          equ 0x0a
mos_fclose:         equ 0x0b
mos_fread:          equ 0x1a
mos_fwrite:         equ 0x1b
fa_read:            equ 0x01
fa_write:           equ 0x02
fa_create_always:   equ 0x08

    macro MOSCALL function
    ld a,function
    rst.lil 08h
    endmacro

record_size:        equ 32
records_per_batch:  equ 2048
prt_reload_1ms:     equ 72
TMR1_CTL:           equ 0x83
TMR_REG_CTL:        equ 0
TMR_RES_LOW:        equ 1
TMR_RES_HIGH:       equ 2
PRT_OFF:            equ %00001110
PRT_ON:             equ %01011111

rec_opcode:         equ 0
rec_expected:       equ 1
rec_door_position:  equ 2
rec_door_vertical:  equ 4
rec_actor_dir:      equ 5
rec_actor_area:     equ 6
rec_area_connected: equ 7
rec_madenoise:      equ 8
rec_patch_x:        equ 9
rec_patch_y:        equ 10
rec_patch_value:    equ 11
rec_actor_x:        equ 12
rec_actor_y:        equ 16
rec_player_x:       equ 20
rec_player_y:       equ 24
rec_sequence:       equ 28

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
    ld hl,result_records
    ld (hl),a
    ld de,result_records+1
    ld bc,result_end-result_records-1
    ldir
    ld hl,0xffff
    ld (result_first_index),hl
    ld (result_first_sequence),hl
    xor a
    ld (vector_handle),a
    ld (previous_patch_valid),a
    ld a,0xff
    ld (timed_op),a

    call initialize_context
    call prt_irq_install
    call load_map
    or a
    jp z,@fatal
    call run_abi_regression
    or a
    jr nz,@abi_ok
    ld a,0xfe
    ld (result_first_opcode),a
    ld a,(abi_opcode)
    ld (result_first_sequence),a
    xor a
    ld (result_first_sequence+1),a
    ld (result_first_sequence+2),a
    ld a,(abi_failure_reason)
    ld (result_first_actual),a
    ld a,(abi_return_a)
    ld (result_first_expected),a
    ld a,(tilemap+1301)
    ld (result_first_carry),a
    jp @fatal
@abi_ok:

    ld hl,vector_filename
    ld c,fa_read
    MOSCALL mos_fopen
    or a
    jp z,@fatal
    ld (vector_handle),a
    ld c,a
    ld hl,io_header
    ld de,4
    MOSCALL mos_fread
    ld hl,4
    or a
    sbc hl,de
    jp nz,@fatal
    ld a,(io_header+2)
    or a
    jp nz,@fatal
    ld a,(io_header+3)
    or a
    jp nz,@fatal
    ld hl,(io_header)
    ld (remaining),hl
    call read_batch

@record_loop:
    ld hl,(remaining)
    ld a,h
    or l
    jp z,@complete

    ld (record_ptr),iy
    ld a,(iy+rec_opcode)
    ld b,a
    ld a,(timed_op)
    cp b
    ld a,b
    call nz,timing_switch
    call prepare_record
    ld ix,actor
    ld iy,sight_context
    ld a,(current_opcode)
    or a
    jr nz,@check_sight
    di
    call w3d_CheckLine
    jr @capture
@check_sight:
    di
    call w3d_CheckSight
@capture:
    ld (actual_result),a
    ld a,0
    adc a,0
    ld (actual_carry),a
    ei

    ld iy,(record_ptr)
    ld a,(actual_carry)
    or a
    jr nz,@failed
    ld a,(actual_result)
    ld b,a
    ld a,(iy+rec_expected)
    cp b
    jr z,@checked
@failed:
    call record_failure
@checked:
    ld hl,(result_records)
    inc.s hl
    ld (result_records),hl
    lea iy,iy+record_size
    ld hl,(remaining)
    dec.s hl
    ld (remaining),hl
    ld hl,(batch_remaining)
    dec.s hl
    ld (batch_remaining),hl
    ld a,h
    or l
    jp nz,@record_loop
    ld hl,(remaining)
    ld a,h
    or l
    jp z,@record_loop
    call read_batch
    jp @record_loop

@complete:
    call timing_finish
    call prt_irq_restore
    call close_vector
    call restore_previous_patch
    call write_result
    call print_report
    ret

@fatal:
    call prt_irq_restore
    call close_vector
    ld hl,0xffff
    ld (result_errors),hl
    call write_result
    call print_report
    ret

initialize_context:
    ld hl,tilemap
    ld (sight_context+W3D_SIGHT_CTX_TILEMAP),hl
    ld hl,doors
    ld (sight_context+W3D_SIGHT_CTX_DOORS),hl
    ld hl,areas
    ld (sight_context+W3D_SIGHT_CTX_AREAS),hl
    xor a
    ld hl,doors
    ld (hl),a
    ld de,doors+1
    ld bc,W3D_MAX_DOORS*W3D_DOOR_SIZE-1
    ldir
    ld hl,areas
    ld (hl),a
    ld de,areas+1
    ld bc,255
    ldir
    ret

; Untimed public-ABI preflight for both entry points.
run_abi_regression:
    ; Actor and player share open tile (20.5,20.5), so both calls return 1.
    xor a
    ld (actor+W3D_SIGHT_ACTOR_X+0),a
    ld (actor+W3D_SIGHT_ACTOR_X+3),a
    ld (actor+W3D_SIGHT_ACTOR_Y+0),a
    ld (actor+W3D_SIGHT_ACTOR_Y+3),a
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_X+0),a
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_X+3),a
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_Y+0),a
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_Y+3),a
    ld (actor+W3D_SIGHT_ACTOR_AREA),a
    ld (actor+W3D_SIGHT_ACTOR_DIR),a
    ld (sight_context+W3D_SIGHT_CTX_MADENOISE),a
    ld a,0x80
    ld (actor+W3D_SIGHT_ACTOR_X+1),a
    ld (actor+W3D_SIGHT_ACTOR_Y+1),a
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_X+1),a
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_Y+1),a
    ld a,20
    ld (actor+W3D_SIGHT_ACTOR_X+2),a
    ld (actor+W3D_SIGHT_ACTOR_Y+2),a
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_X+2),a
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_Y+2),a
    ld a,1
    ld (areas),a

    xor a
    call verify_one_abi
    or a
    ret z
    ld a,1
    call verify_one_abi
    or a
    ret z

    ; Block both routines with a temporary wall one tile east of the actor.
    ld a,(tilemap+1301)       ; row-major tile (21,20)
    ld (abi_saved_tile),a
    ld a,W3D_TILE_WALL_MIN
    ld (tilemap+1301),a
    ld a,22
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_X+2),a
    ld a,2
    call verify_one_abi
    or a
    jr z,@blocked_failed
    ld a,3
    call verify_one_abi
    ld b,a
    ld a,(abi_saved_tile)
    ld (tilemap+1301),a
    ld a,b
    ret
@blocked_failed:
    ld a,(abi_saved_tile)
    ld (tilemap+1301),a
    xor a
    ret

; bit 0 of A selects CheckSight; bit 1 expects a blocked return.
verify_one_abi:
    ld (abi_opcode),a
    xor a
    ld (abi_failure_reason),a
    ld bc,0x123456
    ld de,0x234567
    ld hl,0x345678
    exx
    ld bc,0x456789
    ld de,0x56789a
    ld hl,0x6789ab
    exx
    ld ix,actor
    ld iy,sight_context

    di
    ld a,(abi_opcode)
    and 1
    jr nz,@sight
    call w3d_CheckLine
    jr @capture
@sight:
    call w3d_CheckSight
@capture:
    ld (abi_return_a),a
    ld a,0
    jr nz,@zero_captured
    inc a
@zero_captured:
    ld (abi_return_zero),a
    ld a,0
    adc a,0
    ld (abi_return_carry),a

    ld (abi_actual+0),bc
    ld (abi_actual+3),de
    ld (abi_actual+6),hl
    ld (abi_actual+9),ix
    ld (abi_actual+12),iy
    exx
    ld (abi_actual+15),bc
    ld (abi_actual+18),de
    ld (abi_actual+21),hl
    exx
    ei

    ld a,(abi_opcode)
    bit 1,a
    jr nz,@expect_blocked
    ld a,(abi_return_a)
    cp 1
    jr nz,@failed_a
    ld a,(abi_return_zero)
    or a
    jr nz,@failed_zero
    jr @return_flags_ok
@expect_blocked:
    ld a,(abi_return_a)
    or a
    jr nz,@failed_a
    ld a,(abi_return_zero)
    cp 1
    jr nz,@failed_zero
@return_flags_ok:
    ld a,(abi_return_carry)
    or a
    jr nz,@failed_carry
    ld hl,abi_actual
    ld de,abi_expected
    ld b,abi_expected_end-abi_expected
@compare:
    ld a,(de)
    ld c,a
    ld a,(hl)
    cp c
    jr nz,@failed_register
    inc hl
    inc de
    djnz @compare
    ld a,1
    ret
@failed_a:
    ld a,1
    jr @record_failure
@failed_zero:
    ld a,2
    jr @record_failure
@failed_carry:
    ld a,3
    jr @record_failure
@failed_register:
    ld a,4
@record_failure:
    ld (abi_failure_reason),a
@failed:
    xor a
    ret

load_map:
    ld hl,map_filename
    ld c,fa_read
    MOSCALL mos_fopen
    or a
    ret z
    ld (map_handle),a
    ld c,a
    ld hl,tilemap
    ld de,W3D_MAP_BYTES
    MOSCALL mos_fread
    push de
    ld a,(map_handle)
    ld c,a
    MOSCALL mos_fclose
    xor a
    ld (map_handle),a
    pop de
    ld hl,W3D_MAP_BYTES
    or a
    sbc hl,de
    jr nz,@failed
    ld a,1
    ret
@failed:
    xor a
    ret

read_batch:
    call prt_pause
    ld hl,(remaining)
    ld de,records_per_batch
    or a
    sbc.s hl,de
    jr c,@use_remaining
    jr z,@use_remaining
    ld hl,records_per_batch
    jr @count_ready
@use_remaining:
    ld hl,(remaining)
@count_ready:
    ld (batch_remaining),hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ex de,hl
    ld (expected_bytes),de
    ld a,(vector_handle)
    ld c,a
    ld hl,filedata
    MOSCALL mos_fread
    ld hl,(expected_bytes)
    or a
    sbc hl,de
    jr nz,@short_read
    ld iy,filedata
    call prt_resume
    ret
@short_read:
    ld hl,0xffff
    ld (result_errors),hl
    ld a,0xfd
    ld (result_first_opcode),a
    ld hl,0
    ld (remaining),hl
    ld (batch_remaining),hl
    ld iy,filedata
    call prt_resume
    ret

timing_switch:
    push af
    call timing_finish
    pop af
    ld (timed_op),a
    call prt_start
    ret

timing_finish:
    ld a,(timed_op)
    cp 0xff
    ret z
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_irq_counter)
    ei
    ld a,(timed_op)
    ld e,a
    add a,a
    add a,e
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld ix,result_times
    add ix,de
    ld (ix),hl
    ret

prt_pause:
    ld a,(timed_op)
    cp 0xff
    ret z
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    in0 a,(TMR1_CTL+TMR_REG_CTL)
    ei
    ret

prt_resume:
    ld a,(timed_op)
    cp 0xff
    ret z
    di
    ld hl,prt_reload_1ms
    out0 (TMR1_CTL+TMR_RES_LOW),l
    out0 (TMR1_CTL+TMR_RES_HIGH),h
    ld a,PRT_ON
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ei
    ret

prt_start:
    di
    ld hl,0
    ld (prt_irq_counter),hl
    ld hl,prt_reload_1ms
    out0 (TMR1_CTL+TMR_RES_LOW),l
    out0 (TMR1_CTL+TMR_RES_HIGH),h
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld a,PRT_ON
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ei
    ret

prt_irq_install:
    di
    ld hl,0
    ld a,($10c)
    ld l,a
    ld a,($10d)
    ld h,a
    inc hl
    ld hl,(hl)
    ld (prt_vector),hl
    ld a,(hl)
    ld (prt_saved_vector+0),a
    inc hl
    ld a,(hl)
    ld (prt_saved_vector+1),a
    inc hl
    ld a,(hl)
    ld (prt_saved_vector+2),a
    inc hl
    ld a,(hl)
    ld (prt_saved_vector+3),a
    ld hl,(prt_vector)
    ld (hl),0xc3
    inc hl
    ld de,prt_irq_handler
    ld (hl),de
    ei
    ret

prt_irq_restore:
    di
    ld a,PRT_OFF
    out0 (TMR1_CTL+TMR_REG_CTL),a
    ld hl,(prt_vector)
    ld a,(prt_saved_vector+0)
    ld (hl),a
    inc hl
    ld a,(prt_saved_vector+1)
    ld (hl),a
    inc hl
    ld a,(prt_saved_vector+2)
    ld (hl),a
    inc hl
    ld a,(prt_saved_vector+3)
    ld (hl),a
    ei
    ret

prt_irq_handler:
    di
    push af
    push hl
    in0 a,(TMR1_CTL+TMR_REG_CTL)
    ld hl,(prt_irq_counter)
    inc hl
    ld (prt_irq_counter),hl
    pop hl
    pop af
    ei
    reti.l

prepare_record:
    call restore_previous_patch

    ld a,(iy+rec_patch_x)
    cp 0xff
    jr z,@no_patch
    ld b,a
    ld a,(iy+rec_patch_y)
    ld c,a
    call map_address
    ld a,(hl)
    ld (previous_patch_value),a
    ld a,b
    ld (previous_patch_x),a
    ld a,c
    ld (previous_patch_y),a
    ld a,(iy+rec_patch_value)
    ld (hl),a
    ld a,1
    ld (previous_patch_valid),a
@no_patch:
    ; Canonical slot zero is always live in the shared map. A patched door
    ; configures its encoded slot as well, making every record independent
    ; of door state left by the preceding record.
    xor a
    call configure_record_door
    ld a,(iy+rec_patch_x)
    cp 0xff
    jr z,@doors_ready
    ld a,(iy+rec_patch_value)
    cp W3D_TILE_DOOR_MIN
    jr c,@doors_ready
    cp W3D_TILE_DOOR_MAX+1
    jr nc,@doors_ready
    and W3D_TILE_DOOR_MASK
    or a
    jr z,@doors_ready
    call configure_record_door
@doors_ready:

    ld a,(iy+rec_actor_dir)
    ld (actor+W3D_SIGHT_ACTOR_DIR),a
    ld a,(iy+rec_actor_area)
    ld (actor+W3D_SIGHT_ACTOR_AREA),a
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,areas
    add hl,de
    ld a,(iy+rec_area_connected)
    ld (hl),a
    ld a,(iy+rec_madenoise)
    ld (sight_context+W3D_SIGHT_CTX_MADENOISE),a

    ld a,(iy+rec_actor_x+0)
    ld (actor+W3D_SIGHT_ACTOR_X+0),a
    ld a,(iy+rec_actor_x+1)
    ld (actor+W3D_SIGHT_ACTOR_X+1),a
    ld a,(iy+rec_actor_x+2)
    ld (actor+W3D_SIGHT_ACTOR_X+2),a
    ld (actor+W3D_SIGHT_ACTOR_TILEX),a
    ld a,(iy+rec_actor_x+3)
    ld (actor+W3D_SIGHT_ACTOR_X+3),a
    ld a,(iy+rec_actor_y+0)
    ld (actor+W3D_SIGHT_ACTOR_Y+0),a
    ld a,(iy+rec_actor_y+1)
    ld (actor+W3D_SIGHT_ACTOR_Y+1),a
    ld a,(iy+rec_actor_y+2)
    ld (actor+W3D_SIGHT_ACTOR_Y+2),a
    ld (actor+W3D_SIGHT_ACTOR_TILEY),a
    ld a,(iy+rec_actor_y+3)
    ld (actor+W3D_SIGHT_ACTOR_Y+3),a

    ld a,(iy+rec_player_x+0)
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_X+0),a
    ld a,(iy+rec_player_x+1)
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_X+1),a
    ld a,(iy+rec_player_x+2)
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_X+2),a
    ld a,(iy+rec_player_x+3)
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_X+3),a
    ld a,(iy+rec_player_y+0)
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_Y+0),a
    ld a,(iy+rec_player_y+1)
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_Y+1),a
    ld a,(iy+rec_player_y+2)
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_Y+2),a
    ld a,(iy+rec_player_y+3)
    ld (sight_context+W3D_SIGHT_CTX_PLAYER_Y+3),a

    ld a,(iy+rec_opcode)
    ld (current_opcode),a
    ret

; A=door index. Configure that production runtime slot from the current
; record. The first eight bytes are the VDP wire prefix; area endpoints may
; follow it locally.
configure_record_door:
    ld d,a
    ld e,W3D_DOOR_SIZE
    mlt de
    inc de
    dec.s de
    ld hl,doors
    add hl,de
    inc hl
    inc hl
    ld a,(iy+rec_door_vertical)
    ld (hl),a
    inc hl
    inc hl
    inc hl
    ld a,(iy+rec_door_position)
    ld (hl),a
    inc hl
    ld a,(iy+rec_door_position+1)
    ld (hl),a
    ret

restore_previous_patch:
    ld a,(previous_patch_valid)
    or a
    ret z
    ld a,(previous_patch_x)
    ld b,a
    ld a,(previous_patch_y)
    ld c,a
    call map_address
    ld a,(previous_patch_value)
    ld (hl),a
    xor a
    ld (previous_patch_valid),a
    ret

; B=x, C=y -> HL=&tilemap[y*64+x]. Preserves BC.
map_address:
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
    jr nc,@ready
    inc d
@ready:
    ld hl,tilemap
    add hl,de
    ret

record_failure:
    ld hl,(result_errors)
    ld a,h
    or l
    jr nz,@not_first
    ld hl,(result_records)
    ld (result_first_index),hl
    ld a,(iy+rec_expected)
    ld (result_first_expected),a
    ld a,(actual_result)
    ld (result_first_actual),a
    ld a,(iy+rec_opcode)
    ld (result_first_opcode),a
    ld a,(actual_carry)
    ld (result_first_carry),a
    ld a,(iy+rec_sequence)
    ld (result_first_sequence),a
    ld a,(iy+rec_sequence+1)
    ld (result_first_sequence+1),a
@not_first:
    ld hl,(result_errors)
    inc.s hl
    ld (result_errors),hl
    ld a,(iy+rec_opcode)
    or a
    ld hl,result_line_errors
    jr z,@increment_op
    ld hl,result_sight_errors
@increment_op:
    ld e,(hl)
    inc hl
    ld d,(hl)
    dec hl
    inc.s de
    ld (hl),e
    inc hl
    ld (hl),d
    ret

close_vector:
    ld a,(vector_handle)
    or a
    ret z
    ld c,a
    MOSCALL mos_fclose
    xor a
    ld (vector_handle),a
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
    ld hl,(result_errors)
    ld a,h
    or l
    ld hl,report_pass
    jr z,@emit
    ld hl,report_fail
@emit:
    call print_string
    ret

print_string:
    push bc
    ld bc,0
    ld a,0
    rst.lil 18h
    pop bc
    ret

vector_filename:        asciz "dda_vectors.bin"
map_filename:           asciz "dda_smoke_test_map.bin"
result_filename:        asciz "dda_result.bin"
report_banner:          asciz "\r\nWolf3D eZ80 sight regression: "
report_pass:            asciz "PASS\r\n"
report_fail:            asciz "FAIL\r\n"

vector_handle:          db 0
map_handle:             db 0
output_handle:          db 0
actual_result:          db 0
actual_carry:           db 0
current_opcode:         db 0
timed_op:               db 0xff
previous_patch_valid:   db 0
previous_patch_x:       db 0
previous_patch_y:       db 0
previous_patch_value:   db 0
abi_opcode:             db 0
abi_failure_reason:     db 0
abi_return_a:           db 0
abi_return_zero:        db 0
abi_return_carry:       db 0
abi_saved_tile:         db 0
abi_actual:             blkb 24,0
abi_expected:
                        dl 0x123456
                        dl 0x234567
                        dl 0x345678
                        dl actor
                        dl sight_context
                        dl 0x456789
                        dl 0x56789a
                        dl 0x6789ab
abi_expected_end:
record_ptr:             dl 0
remaining:              dl 0
batch_remaining:        dl 0
expected_bytes:         dl 0
prt_vector:             dl 0
prt_saved_vector:       blkb 4,0
prt_irq_counter:        dl 0
io_header:              dl 0
                        db 0

result_data:
    db "W3R1"
result_records:         dl 0
result_errors:          dl 0
result_line_errors:     dl 0
result_sight_errors:    dl 0
result_first_index:     dl 0xffff
result_first_expected:  db 0
result_first_actual:    db 0
result_first_opcode:    db 0
result_first_carry:     db 0
result_first_sequence:  dl 0xffff
result_times:           blkb 6,0
                        dw 0
result_end:

actor:
    blkb W3D_SIGHT_ACTOR_SIZE,0
sight_context:
    blkb W3D_SIGHT_CTX_SIZE,0
doors:
    blkb W3D_MAX_DOORS*W3D_DOOR_SIZE,0
areas:
    blkb 256,0
tilemap:
    blkb W3D_MAP_BYTES,0

    align 256
filedata: equ $
