; Direct real-eZ80 regression for the production Wolf3D area graph.
;
; This fixture calls the public/internal production labels directly. Expected
; reachability is listed explicitly at each checkpoint; there is deliberately
; no second graph traversal or copied BFS in the test program.

    assume adl=1
    org 0x040000
    jp start
    align 64
    db "MOS",0,1

mos_getkbmap:       equ 0x1e
mos_fopen:          equ 0x0a
mos_fclose:         equ 0x0b
mos_fwrite:         equ 0x1b
fa_write:           equ 0x02
fa_create_always:   equ 0x08

    macro MOSCALL function
        ld a,function
        rst.lil 08h
    endmacro

    include "wolf3d_sight.inc"
    include "wolf3d_fixture.inc"
    include "wolf3d_actors.inc"
    include "wolf3d_areas.inc"
    include "wolf3d_actor_sim.inc"
    include "wolf3d_motion.inc"

case_initial:           equ 1
case_real_e1l1:         equ 2
case_parallel:          equ 3
case_partial_reverse:   equ 4
case_player_area:       equ 5
case_malformed:         equ 6
case_self_loop:         equ 7
case_abi:               equ 8

reason_reachability:    equ 1
reason_player_area:     equ 2
reason_topology_dirty:  equ 3
reason_fault_count:     equ 4
reason_queue_state:     equ 5
reason_door_state:      equ 6
reason_abi:             equ 7

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
    call test_initial_state
    call test_real_e1l1_topology
    call test_parallel_thresholds
    call test_partial_close_and_reverse
    call test_player_area_transitions
    call test_malformed_edges_and_batching
    call test_self_loop
    call test_rebuild_abi
    call write_result
    call print_report
    ret

; ---------------------------------------------------------------------------
; Case 1: initialization derives a valid root and a closed graph.
; ---------------------------------------------------------------------------

test_initial_state:
    ld a,case_initial
    ld (test_case),a
    ld a,1
    ld (test_checkpoint),a
    call reset_synthetic_world
    xor a
    ld (test_area_map+650),a          ; tile (10,10) is area 0
    call w3d_initialize_area_state
    call expected_clear
    xor a
    call expected_set
    xor a                             ; player area 0
    ld b,1                            ; one queued/reached area
    ld c,0                            ; topology clean
    ld d,0                            ; fault low
    ld e,0                            ; fault high
    call check_area_checkpoint
    xor a                             ; door 0
    ld b,W3D_DOOR_ACTION_CLOSED
    ld c,0
    ld d,0
    ld e,0
    call check_door_state

; A first malformed/no-area sample is itself one transition; initialization
; must clear reachability and charge it once, then leave repeats quiet.
    call reset_synthetic_world
    call w3d_initialize_area_state
    ld a,2
    ld (test_checkpoint),a
    call expected_clear
    ld a,W3D_SLOT_NONE
    ld b,0
    ld c,0
    ld d,1
    ld e,0
    call check_area_checkpoint
    call w3d_refresh_player_area
    ld a,3
    ld (test_checkpoint),a
    call expected_clear
    ld a,W3D_SLOT_NONE
    ld b,0
    ld c,0
    ld d,1
    ld e,0
    call check_area_checkpoint
    ret

; ---------------------------------------------------------------------------
; Case 2: exact generated E1L1 graph checkpoints from independent oracle.
; ---------------------------------------------------------------------------

test_real_e1l1_topology:
    ld a,case_real_e1l1
    ld (test_case),a
    call reset_synthetic_world
    ld hl,w3d_fixture_initial_doors
    ld de,w3d_doors
    ld bc,w3d_fixture_initial_doors_end-w3d_fixture_initial_doors
    ldir
    ld hl,w3d_fixture_initial_player_pose
    ld de,w3d_player_pose
    ld bc,w3d_fixture_initial_player_pose_end-w3d_fixture_initial_player_pose
    ldir
    ld hl,w3d_fixture_area_map
    ld de,test_area_map
    ld bc,w3d_fixture_area_map_end-w3d_fixture_area_map
    ldir
    call w3d_initialize_area_state

    ld a,1
    ld (test_checkpoint),a
    call expected_clear
    ld a,2
    call expected_set
    ld a,2
    ld b,1
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint
    ld a,16
    ld b,W3D_DOOR_ACTION_CLOSED
    ld c,0
    ld d,0
    ld e,0
    call check_door_state

; A nonzero position is authoritative even when the action remains CLOSED.
    ld a,16
    ld hl,1
    call set_door_position
    call w3d_mark_area_topology_dirty
    call w3d_refresh_areas_if_dirty
    ld a,2
    ld (test_checkpoint),a
    call expected_clear
    ld a,1
    call expected_set
    ld a,2
    call expected_set
    ld a,2
    ld b,2
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint
    ld a,16
    ld b,W3D_DOOR_ACTION_CLOSED
    ld c,1
    ld d,0
    ld e,0
    call check_door_state

    ld a,7
    ld hl,1
    call set_door_position
    call w3d_mark_area_topology_dirty
    call w3d_refresh_areas_if_dirty
    ld a,3
    ld (test_checkpoint),a
    call expected_clear
    ld a,1
    call expected_set
    ld a,2
    call expected_set
    ld a,3
    call expected_set
    ld a,2
    ld b,3
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint

    ld a,2
    ld hl,1
    call set_door_position
    call w3d_mark_area_topology_dirty
    call w3d_refresh_areas_if_dirty
    ld a,4
    ld (test_checkpoint),a
    call expected_clear
    ld a,1
    call expected_set
    ld a,2
    call expected_set
    ld a,3
    call expected_set
    ld a,36
    call expected_set
    ld a,2
    ld b,4
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint

; This literal 15-area set includes cycles, endpoint extremes, parallel doors,
; and the fixture's self-loop records without deriving anything in the test.
    call set_all_door_positions_one
    call w3d_mark_area_topology_dirty
    call w3d_refresh_areas_if_dirty
    ld a,5
    ld (test_checkpoint),a
    call expected_clear
    ld a,0
    call expected_set
    ld a,1
    call expected_set
    ld a,2
    call expected_set
    ld a,3
    call expected_set
    ld a,4
    call expected_set
    ld a,5
    call expected_set
    ld a,6
    call expected_set
    ld a,7
    call expected_set
    ld a,10
    call expected_set
    ld a,11
    call expected_set
    ld a,32
    call expected_set
    ld a,33
    call expected_set
    ld a,34
    call expected_set
    ld a,35
    call expected_set
    ld a,36
    call expected_set
    ld a,2
    ld b,15
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint
    ld a,12                          ; fixture self-loop 1 -> 1
    ld b,W3D_DOOR_ACTION_CLOSED
    ld c,1
    ld d,0
    ld e,0
    call check_door_state
    ret

; ---------------------------------------------------------------------------
; Case 3: parallel doors and exact zero/nonzero topology boundaries.
; ---------------------------------------------------------------------------

test_parallel_thresholds:
    ld a,case_parallel
    ld (test_case),a
    call reset_synthetic_world
    xor a
    ld (test_area_map+650),a
    xor a
    ld b,0
    ld c,1
    ld d,W3D_DOOR_ACTION_OPENING
    ld hl,0
    call configure_door
    ld a,1
    ld b,0
    ld c,1
    ld d,W3D_DOOR_ACTION_OPENING
    ld hl,0
    call configure_door
    call w3d_initialize_area_state

    ld a,1
    ld (test_checkpoint),a
    call expected_clear
    xor a
    call expected_set
    xor a
    ld b,1
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint

; Both first OPENING steps cross zero in one simulation pass. The refresh is
; batched at the end and the edge becomes observable only after position>0.
    call w3d_simulate_doors
    ld a,2
    ld (test_checkpoint),a
    call expected_clear
    xor a
    call expected_set
    ld a,1
    call expected_set
    xor a
    ld b,2
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint
    xor a
    ld b,W3D_DOOR_ACTION_OPENING
    ld c,055h
    ld d,09h
    ld e,1
    call check_door_state
    ld a,1
    ld b,W3D_DOOR_ACTION_OPENING
    ld c,055h
    ld d,09h
    ld e,1
    call check_door_state

; Closing one of two parallel doors must retain the live edge.
    call clear_all_door_dirty
    xor a
    ld b,W3D_DOOR_ACTION_CLOSING
    ld hl,1
    call set_door_action_position
    call w3d_simulate_doors
    ld a,3
    ld (test_checkpoint),a
    call expected_clear
    xor a
    call expected_set
    ld a,1
    call expected_set
    xor a
    ld b,2
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint
    xor a
    ld b,W3D_DOOR_ACTION_CLOSED
    ld c,0
    ld d,0
    ld e,1
    call check_door_state
    ld a,1
    ld b,W3D_DOOR_ACTION_OPENING
    ld c,0aah                         ; 0955 + 0955 = 12aa
    ld d,012h
    ld e,1
    call check_door_state

; The edge disappears only after the last parallel panel writes zero.
    call clear_all_door_dirty
    ld a,1
    ld b,W3D_DOOR_ACTION_CLOSING
    ld hl,1
    call set_door_action_position
    call w3d_simulate_doors
    ld a,4
    ld (test_checkpoint),a
    call expected_clear
    xor a
    call expected_set
    xor a
    ld b,1
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint
    ld a,1
    ld b,W3D_DOOR_ACTION_CLOSED
    ld c,0
    ld d,0
    ld e,1
    call check_door_state
    ret

; ---------------------------------------------------------------------------
; Case 4: a partial close remains connected and reversal cannot flap it.
; ---------------------------------------------------------------------------

test_partial_close_and_reverse:
    ld a,case_partial_reverse
    ld (test_case),a
    call reset_synthetic_world
    xor a
    ld (test_area_map+650),a
    xor a
    ld b,0
    ld c,1
    ld d,W3D_DOOR_ACTION_CLOSING
    ld hl,0956h
    call configure_door
    call w3d_initialize_area_state

    ld a,1
    ld (test_checkpoint),a
    call expected_areas_zero_one
    xor a
    ld b,2
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint

; 0956 - 0955 leaves the smallest live position, 0001.
    call w3d_simulate_doors
    ld a,2
    ld (test_checkpoint),a
    call expected_areas_zero_one
    xor a
    ld b,2
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint
    xor a
    ld b,W3D_DOOR_ACTION_CLOSING
    ld c,1
    ld d,0
    ld e,1
    call check_door_state

; Actor-side reversal changes the action, never the already-live topology.
    call clear_all_door_dirty
    xor a
    call w3d_request_open_door
    ld a,3
    ld (test_checkpoint),a
    call expected_areas_zero_one
    xor a
    ld b,2
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint
    xor a
    ld b,W3D_DOOR_ACTION_OPENING
    ld c,1
    ld d,0
    ld e,1
    call check_door_state

    call clear_all_door_dirty
    call w3d_simulate_doors
    ld a,4
    ld (test_checkpoint),a
    call expected_areas_zero_one
    xor a
    ld b,2
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint
    xor a
    ld b,W3D_DOOR_ACTION_OPENING
    ld c,056h                         ; 0001 + 0955 = 0956
    ld d,09h
    ld e,1
    call check_door_state

; A later final close writes zero and disconnects exactly then.
    call clear_all_door_dirty
    xor a
    ld b,W3D_DOOR_ACTION_CLOSING
    ld hl,1
    call set_door_action_position
    call w3d_simulate_doors
    ld a,5
    ld (test_checkpoint),a
    call expected_clear
    xor a
    call expected_set
    xor a
    ld b,1
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint
    xor a
    ld b,W3D_DOOR_ACTION_CLOSED
    ld c,0
    ld d,0
    ld e,1
    call check_door_state
    ret

; ---------------------------------------------------------------------------
; Case 5: valid component changes and invalid-player transition accounting.
; ---------------------------------------------------------------------------

test_player_area_transitions:
    ld a,case_player_area
    ld (test_case),a
    call reset_synthetic_world
    xor a
    ld (test_area_map+650),a          ; (10,10) -> area 0
    ld a,2
    ld (test_area_map+651),a          ; (11,10) -> area 2
    ld a,W3D_SLOT_NONE
    ld (test_area_map+652),a          ; (12,10) -> malformed/no area
    xor a
    ld b,0
    ld c,1
    ld d,W3D_DOOR_ACTION_CLOSED
    ld hl,1
    call configure_door
    ld a,1
    ld b,2
    ld c,3
    ld d,W3D_DOOR_ACTION_CLOSED
    ld hl,1
    call configure_door
    call w3d_initialize_area_state

    ld a,1
    ld (test_checkpoint),a
    call expected_areas_zero_one
    xor a
    ld b,2
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint

    ld b,11
    ld c,10
    call set_player_tile
    call w3d_refresh_player_area
    ld a,2
    ld (test_checkpoint),a
    call expected_clear
    ld a,2
    call expected_set
    ld a,3
    call expected_set
    ld a,2
    ld b,2
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint

; First transition into invalid faults once and clears the whole table.
    ld b,12
    ld c,10
    call set_player_tile
    call w3d_refresh_player_area
    ld a,3
    ld (test_checkpoint),a
    call expected_clear
    ld a,W3D_SLOT_NONE
    ld b,0
    ld c,0
    ld d,1
    ld e,0
    call check_area_checkpoint

; Repeated invalid samples are quiet.
    call w3d_refresh_player_area
    ld a,4
    ld (test_checkpoint),a
    call expected_clear
    ld a,W3D_SLOT_NONE
    ld b,0
    ld c,0
    ld d,1
    ld e,0
    call check_area_checkpoint

; Returning to a valid root rebuilds without another diagnostic.
    ld b,10
    ld c,10
    call set_player_tile
    call w3d_refresh_player_area
    ld a,5
    ld (test_checkpoint),a
    call expected_areas_zero_one
    xor a
    ld b,2
    ld c,0
    ld d,1
    ld e,0
    call check_area_checkpoint
    ret

; ---------------------------------------------------------------------------
; Case 6: malformed live edge containment and one batched flood per pass.
; ---------------------------------------------------------------------------

test_malformed_edges_and_batching:
    ld a,case_malformed
    ld (test_case),a
    call reset_synthetic_world
    xor a
    ld (test_area_map+650),a
; Both endpoints are invalid, but this is one malformed live-door record and
; therefore one diagnostic per rebuild, not one per endpoint or BFS dequeue.
    xor a
    ld b,W3D_SLOT_NONE
    ld c,W3D_NUM_AREAS
    ld d,W3D_DOOR_ACTION_OPENING
    ld hl,0
    call configure_door
; A second simultaneous zero crossing is a valid self-loop. If the simulation
; rebuilt eagerly after each door instead of once at the end, the bad live
; record above would be charged twice during this pass.
    ld a,1
    ld b,0
    ld c,0
    ld d,W3D_DOOR_ACTION_OPENING
    ld hl,0
    call configure_door
    call w3d_initialize_area_state

    ld a,1
    ld (test_checkpoint),a
    call expected_clear
    xor a
    call expected_set
    xor a
    ld b,1
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint

    call w3d_simulate_doors
    ld a,2
    ld (test_checkpoint),a
    call expected_clear
    xor a
    call expected_set
    xor a
    ld b,1
    ld c,0
    ld d,1
    ld e,0
    call check_area_checkpoint
    xor a
    ld b,W3D_DOOR_ACTION_OPENING
    ld c,055h
    ld d,09h
    ld e,1
    call check_door_state
    ld a,1
    ld b,W3D_DOOR_ACTION_OPENING
    ld c,055h
    ld d,09h
    ld e,1
    call check_door_state

; Ordinary motion while already live does not dirty topology or rebuild.
    call clear_all_door_dirty
    call w3d_simulate_doors
    ld a,3
    ld (test_checkpoint),a
    call expected_clear
    xor a
    call expected_set
    xor a
    ld b,1
    ld c,0
    ld d,1
    ld e,0
    call check_area_checkpoint
    xor a
    ld b,W3D_DOOR_ACTION_OPENING
    ld c,0aah
    ld d,012h
    ld e,1
    call check_door_state

; An explicit rebuild observes the same bad record once more.
    call w3d_mark_area_topology_dirty
    ld a,(w3d_area_topology_dirty)
    ld b,1
    ld c,reason_topology_dirty
    ld hl,39
    call set_test_index_hl
    call assert_equal
    call w3d_refresh_areas_if_dirty
    ld a,4
    ld (test_checkpoint),a
    call expected_clear
    xor a
    call expected_set
    xor a
    ld b,1
    ld c,0
    ld d,2
    ld e,0
    call check_area_checkpoint
    ret

; ---------------------------------------------------------------------------
; Case 7: a live self-loop neither expands nor duplicates the root enqueue.
; ---------------------------------------------------------------------------

test_self_loop:
    ld a,case_self_loop
    ld (test_case),a
    call reset_synthetic_world
    ld a,2
    ld (test_area_map+650),a
    xor a
    ld b,2
    ld c,2
    ld d,W3D_DOOR_ACTION_CLOSED
    ld hl,1
    call configure_door
    call w3d_initialize_area_state
    ld a,1
    ld (test_checkpoint),a
    call expected_clear
    ld a,2
    call expected_set
    ld a,2
    ld b,1
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint
    xor a
    ld b,W3D_DOOR_ACTION_CLOSED
    ld c,1
    ld d,0
    ld e,0
    call check_door_state
    ret

; ---------------------------------------------------------------------------
; Case 8: the documented rebuild ABI preserves every GP/index register.
; ---------------------------------------------------------------------------

test_rebuild_abi:
    ld a,case_abi
    ld (test_case),a
    ld a,1
    ld (test_checkpoint),a
    call reset_synthetic_world
    xor a
    ld (test_area_map+650),a
    xor a
    ld b,0
    ld c,1
    ld d,W3D_DOOR_ACTION_CLOSED
    ld hl,1
    call configure_door
    call w3d_initialize_area_state

    ld bc,0123456h
    ld de,0234567h
    ld hl,0345678h
    ld ix,0456789h
    ld iy,056789ah
    call w3d_rebuild_area_connectivity
    ld (abi_actual+0),bc
    ld (abi_actual+3),de
    ld (abi_actual+6),hl
    ld (abi_actual+9),ix
    ld (abi_actual+12),iy
    ld ix,abi_actual
    ld iy,abi_expected
    ld de,abi_expected_end-abi_expected
    ld c,reason_abi
    xor a
    ld (test_index+0),a
    ld (test_index+1),a
    call assert_memory

    call expected_areas_zero_one
    xor a
    ld b,2
    ld c,0
    ld d,0
    ld e,0
    call check_area_checkpoint
    ret

; ---------------------------------------------------------------------------
; Test-world setup helpers
; ---------------------------------------------------------------------------

reset_synthetic_world:
    xor a
    ld hl,w3d_actorat
    ld (hl),a
    ld de,w3d_actorat+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,w3d_doors
    ld (hl),a
    ld de,w3d_doors+1
    ld bc,W3D_FIXTURE_DOOR_COUNT*W3D_DOOR_SIZE-1
    ldir
    ld hl,w3d_door_timers
    ld (hl),a
    ld de,w3d_door_timers+1
    ld bc,W3D_FIXTURE_DOOR_COUNT*2-1
    ldir
    ld hl,w3d_door_dirty
    ld (hl),a
    ld de,w3d_door_dirty+1
    ld bc,W3D_FIXTURE_DOOR_COUNT-1
    ldir
    ld hl,test_tilemap
    ld (hl),a
    ld de,test_tilemap+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,test_static_bits
    ld (hl),a
    ld de,test_static_bits+1
    ld bc,511
    ldir
    ld a,W3D_SLOT_NONE
    ld hl,test_area_map
    ld (hl),a
    ld de,test_area_map+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,test_path_directions
    ld (hl),a
    ld de,test_path_directions+1
    ld bc,W3D_MAP_BYTES-1
    ldir

    ld hl,test_tilemap
    ld (w3d_map_ptr),hl
    ld hl,test_static_bits
    ld (w3d_static_blocking_ptr),hl
    ld hl,test_area_map
    ld (w3d_area_map_ptr),hl
    ld hl,test_path_directions
    ld (w3d_path_directions_ptr),hl
    ld hl,w3d_doors
    ld (w3d_doors_ptr),hl

    ld a,W3D_SLOT_NONE
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
    xor a
    ld (w3d_actor_count),a
    ld (w3d_world_dirty),a
    ld (w3d_player_dirty),a
    ld (w3d_door_motion_phase),a
    ld (w3d_area_topology_dirty),a
    ld b,10
    ld c,10
    call set_player_tile
    ret

; B=x, C=y. Install the authoritative pose at the tile center.
set_player_tile:
    xor a
    ld (w3d_player_pose+0),a
    ld a,080h
    ld (w3d_player_pose+1),a
    ld a,b
    ld (w3d_player_pose+2),a
    xor a
    ld (w3d_player_pose+3),a
    ld (w3d_player_pose+4),a
    ld a,080h
    ld (w3d_player_pose+5),a
    ld a,c
    ld (w3d_player_pose+6),a
    xor a
    ld (w3d_player_pose+7),a
    ld (w3d_player_pose+8),a
    ld (w3d_player_pose+9),a
    ret

; A=index, B=area1, C=area2, D=action, HL=position.
configure_door:
    ld (door_setup_index),a
    ld a,d
    ld (door_setup_action),a
    ld (door_setup_position),hl
    ld a,(door_setup_index)
    call w3d_door_pointer_from_index
    ld a,(door_setup_index)
    add a,20
    ld (ix+W3D_DOOR_TILEX),a
    ld a,20
    ld (ix+W3D_DOOR_TILEY),a
    ld a,1
    ld (ix+W3D_DOOR_VERTICAL),a
    xor a
    ld (ix+W3D_DOOR_LOCK),a
    ld a,(door_setup_action)
    ld (ix+W3D_DOOR_ACTION),a
    ld hl,(door_setup_position)
    ld (ix+W3D_DOOR_POSITION+0),l
    ld (ix+W3D_DOOR_POSITION+1),h
    ld a,121
    ld (ix+W3D_DOOR_TEXTURE_ID),a
    ld (ix+W3D_DOOR_AREA1),b
    ld (ix+W3D_DOOR_AREA2),c
    ret

; A=index, B=action, HL=position. Endpoints and immutable fields remain intact.
set_door_action_position:
    ld (door_setup_index),a
    ld a,b
    ld (door_setup_action),a
    ld (door_setup_position),hl
    ld a,(door_setup_index)
    call w3d_door_pointer_from_index
    ld a,(door_setup_action)
    ld (ix+W3D_DOOR_ACTION),a
    ld hl,(door_setup_position)
    ld (ix+W3D_DOOR_POSITION+0),l
    ld (ix+W3D_DOOR_POSITION+1),h
    ret

; A=index, HL=position.
set_door_position:
    ld (door_setup_index),a
    ld (door_setup_position),hl
    call w3d_door_pointer_from_index
    ld hl,(door_setup_position)
    ld (ix+W3D_DOOR_POSITION+0),l
    ld (ix+W3D_DOOR_POSITION+1),h
    ret

set_all_door_positions_one:
    ld ix,w3d_doors
    ld b,W3D_FIXTURE_DOOR_COUNT
@loop:
    ld (ix+W3D_DOOR_POSITION+0),1
    ld (ix+W3D_DOOR_POSITION+1),0
    lea ix,ix+W3D_DOOR_SIZE
    djnz @loop
    ret

clear_all_door_dirty:
    xor a
    ld hl,w3d_door_dirty
    ld (hl),a
    ld de,w3d_door_dirty+1
    ld bc,W3D_FIXTURE_DOOR_COUNT-1
    ldir
    ld (w3d_world_dirty),a
    ret

; ---------------------------------------------------------------------------
; Literal expected reachability and checkpoint comparators
; ---------------------------------------------------------------------------

expected_clear:
    xor a
    ld hl,expected_areas
    ld (hl),a
    ld de,expected_areas+1
    ld bc,W3D_NUM_AREAS-1
    ldir
    ret

; A=area id. Out-of-contract values are ignored by the expectation builder.
expected_set:
    cp W3D_NUM_AREAS
    ret nc
    ld de,0
    ld e,a
    ld hl,expected_areas
    add hl,de
    ld (hl),1
    ret

expected_areas_zero_one:
    call expected_clear
    xor a
    call expected_set
    ld a,1
    jp expected_set

; A=expected player, B=expected head/tail/reachable count,
; C=expected dirty, DE=expected fault low/high respectively.
check_area_checkpoint:
    ld (expected_player),a
    ld a,b
    ld (expected_queue_count),a
    ld a,c
    ld (expected_dirty),a
    ld a,d
    ld (expected_fault+0),a
    ld a,e
    ld (expected_fault+1),a
    ld ix,w3d_area_by_player
    ld iy,expected_areas
    ld a,W3D_NUM_AREAS
    ld (area_compare_left),a
    xor a
    ld (test_index+0),a
    ld (test_index+1),a
@areas:
    ld a,(ix+0)
    ld b,(iy+0)
    ld c,reason_reachability
    call assert_equal
    inc ix
    inc iy
    ld hl,test_index
    inc (hl)
    ld hl,area_compare_left
    dec (hl)
    jr nz,@areas

    ld hl,37
    call set_test_index_hl
    ld a,(expected_player)
    ld b,a
    ld a,(w3d_player_area)
    ld c,reason_player_area
    call assert_equal
    ld hl,38
    call set_test_index_hl
    ld a,(expected_dirty)
    ld b,a
    ld a,(w3d_area_topology_dirty)
    ld c,reason_topology_dirty
    call assert_equal
    ld hl,39
    call set_test_index_hl
    ld a,(expected_fault+0)
    ld b,a
    ld a,(w3d_area_fault_count+0)
    ld c,reason_fault_count
    call assert_equal
    ld hl,40
    call set_test_index_hl
    ld a,(expected_fault+1)
    ld b,a
    ld a,(w3d_area_fault_count+1)
    ld c,reason_fault_count
    call assert_equal
    ld hl,41
    call set_test_index_hl
    ld a,(expected_queue_count)
    ld b,a
    ld a,(w3d_area_queue_head)
    ld c,reason_queue_state
    call assert_equal
    ld hl,42
    call set_test_index_hl
    ld a,(expected_queue_count)
    ld b,a
    ld a,(w3d_area_queue_tail)
    ld c,reason_queue_state
    jp assert_equal

; A=index, B=action, C=position low, D=position high, E=dirty.
check_door_state:
    ld (expected_door_index),a
    ld a,b
    ld (expected_door_action),a
    ld a,c
    ld (expected_door_position+0),a
    ld a,d
    ld (expected_door_position+1),a
    ld a,e
    ld (expected_door_dirty),a
    ld a,(expected_door_index)
    call w3d_door_pointer_from_index
    ld hl,0
    call set_test_index_hl
    ld a,(expected_door_action)
    ld b,a
    ld a,(ix+W3D_DOOR_ACTION)
    ld c,reason_door_state
    call assert_equal
    ld hl,1
    call set_test_index_hl
    ld a,(expected_door_position+0)
    ld b,a
    ld a,(ix+W3D_DOOR_POSITION+0)
    ld c,reason_door_state
    call assert_equal
    ld hl,2
    call set_test_index_hl
    ld a,(expected_door_position+1)
    ld b,a
    ld a,(ix+W3D_DOOR_POSITION+1)
    ld c,reason_door_state
    call assert_equal
    ld hl,3
    call set_test_index_hl
    ld de,0
    ld a,(expected_door_index)
    ld e,a
    ld hl,w3d_door_dirty
    add hl,de
    ld a,(expected_door_dirty)
    ld b,a
    ld a,(hl)
    ld c,reason_door_state
    jp assert_equal

set_test_index_hl:
    push af
    ld a,l
    ld (test_index+0),a
    ld a,h
    ld (test_index+1),a
    pop af
    ret

; IX actual, IY expected, DE byte count, C reason. One check per byte.
assert_memory:
@loop:
    ld a,d
    or e
    ret z
    ld a,(ix+0)
    ld b,(iy+0)
    call assert_equal
    inc ix
    inc iy
    ld hl,test_index
    inc (hl)
    jr nz,@index_done
    inc hl
    inc (hl)
@index_done:
    dec.s de
    jr @loop

; A=actual, B=expected, C=reason. Preserve the first compact diagnostic.
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
    ld a,(test_case)
    or a
    jr z,@first
    dec a
    cp 8
    jr nc,@first
    ld de,0
    ld e,a
    ld hl,result_case_errors
    add hl,de
    inc (hl)
@first:
    ld a,(result_first_reason)
    or a
    jr nz,@return
    ld a,(test_case)
    ld (result_first_case),a
    ld a,(test_checkpoint)
    ld (result_first_checkpoint),a
    ld a,c
    ld (result_first_reason),a
    ld a,(assert_expected)
    ld (result_first_expected),a
    ld a,(assert_actual)
    ld (result_first_actual),a
    ld a,(test_index+0)
    ld (result_first_index+0),a
    ld a,(test_index+1)
    ld (result_first_index+1),a
@return:
    pop hl
    ret

; ---------------------------------------------------------------------------
; Result mailbox and console breadcrumb
; ---------------------------------------------------------------------------

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
    ld a,0
    rst.lil 18h
    pop bc
    ret

; Required by the interactive motion include, not exercised here.
w3d_mark_render_submitted:
    ret
w3d_elapsed_ticks:
    dl 0
w3d_exit_requested:
    db 0

result_filename:            asciz "area_result.bin"
report_banner:              asciz "\r\nWolf3D eZ80 area regression: "
report_pass:                asciz "PASS\r\n"
report_fail:                asciz "FAIL\r\n"

output_handle:              db 0
test_case:                  db 0
test_checkpoint:            db 0
test_index:                 dw 0
area_compare_left:          db 0
door_setup_index:           db 0
door_setup_action:          db 0
door_setup_position:        dl 0
expected_player:            db 0
expected_queue_count:       db 0
expected_dirty:             db 0
expected_fault:             dw 0
expected_door_index:        db 0
expected_door_action:       db 0
expected_door_position:     dw 0
expected_door_dirty:        db 0
assert_expected:            db 0
assert_actual:              db 0

abi_actual:
    ds 15
abi_expected:
    dl 0123456h
    dl 0234567h
    dl 0345678h
    dl 0456789h
    dl 056789ah
abi_expected_end:

result_data:
    db "W3A1"
result_checks:              dw 0
result_errors:              dw 0
result_first_case:          db 0
result_first_checkpoint:    db 0
result_first_reason:        db 0
result_first_expected:      db 0
result_first_actual:        db 0
result_first_index:         dw 0
                            db 0
result_case_errors:         ds 8
                            ds 8
result_end:

expected_areas:
    ds W3D_NUM_AREAS
test_tilemap:
    ds W3D_MAP_BYTES
test_path_directions:
    ds W3D_MAP_BYTES
test_area_map:
    ds W3D_MAP_BYTES
test_static_bits:
    ds 512
