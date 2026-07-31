; =============================================================================
; Door-area connectivity and player-area ownership.
;
; The original keeps a 37x37 byte refcount matrix. This port already retains
; both area endpoints and the exact live position for every runtime door, so
; the observable graph can be rebuilt directly: a door connects its endpoints
; iff position != 0. An iterative breadth-first flood scans those live records
; into the 37-byte table consumed by w3d_CheckSight. Parallel doors and
; self-loops therefore need no separate counter state, and no recursion or
; renderer feedback is involved.
;
; Topology changes are batched across one door-simulation pass. A door becomes
; connected only after its first OPENING step writes a positive position and
; remains connected until its final CLOSING step writes zero. Player area is
; read from the generated area map using the authoritative pose center.
; =============================================================================

; Clear all connectivity state, derive the initial player area, and flood the
; closed-door graph. Doors, pose, and w3d_area_map_ptr must already be seeded.
w3d_initialize_area_state:
    xor a
    ld hl,w3d_area_by_player
    ld (hl),a
    ld de,w3d_area_by_player+1
    ld bc,W3D_NUM_AREAS-1
    ldir
    ld hl,w3d_area_queue
    ld (hl),a
    ld de,w3d_area_queue+1
    ld bc,W3D_NUM_AREAS-1
    ldir
    ld (w3d_area_queue_head),a
    ld (w3d_area_queue_tail),a
    ld (w3d_area_topology_dirty),a
    ld (w3d_area_fault_count+0),a
    ld (w3d_area_fault_count+1),a
    ld a,W3D_SLOT_NONE
    ld (w3d_player_area),a
    ld (w3d_area_last_player_sample),a
    xor a
    ld (w3d_area_player_sample_seen),a
    jp w3d_refresh_player_area

; Re-read the center cell of the authoritative player pose. A changed valid
; root, or a transition from valid to malformed/no-area, rebuilds the flood.
; Repeated invalid samples remain quiet instead of inflating diagnostics.
w3d_refresh_player_area:
    ld a,(w3d_player_pose+3)
    or a
    jr nz,@invalid_coordinate
    ld a,(w3d_player_pose+7)
    or a
    jr nz,@invalid_coordinate
    ld a,(w3d_player_pose+2)
    cp W3D_MAP_SIZE
    jr nc,@invalid_coordinate
    ld (w3d_area_player_tile_x),a
    ld a,(w3d_player_pose+6)
    cp W3D_MAP_SIZE
    jr nc,@invalid_coordinate

    ld hl,0
    ld l,a
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    ld de,0
    ld a,(w3d_area_player_tile_x)
    ld e,a
    add.s hl,de
    ld de,(w3d_area_map_ptr)
    add hl,de
    ld a,(hl)
    jr @sample_ready

@invalid_coordinate:
    ld a,W3D_SLOT_NONE
@sample_ready:
    ld b,a
    ld a,(w3d_area_player_sample_seen)
    or a
    jr z,@new_sample
    ld a,(w3d_area_last_player_sample)
    cp b
    ret z
@new_sample:
    ld a,1
    ld (w3d_area_player_sample_seen),a
    ld a,b
    ld (w3d_area_last_player_sample),a
    cp W3D_NUM_AREAS
    jr nc,@invalid_transition
    ld (w3d_player_area),a
    jp w3d_rebuild_area_connectivity

@invalid_transition:
    call w3d_area_note_fault
    ld a,W3D_SLOT_NONE
    ld (w3d_player_area),a
    jp w3d_rebuild_area_connectivity

; Door motion calls this only at the two position-zero topology boundaries.
; It deliberately does not make the render world dirty.
w3d_mark_area_topology_dirty:
    ld a,1
    ld (w3d_area_topology_dirty),a
    ret

; Batch exactly one flood after all doors have advanced for this fixed frame.
w3d_refresh_areas_if_dirty:
    ld a,(w3d_area_topology_dirty)
    or a
    ret z
    xor a
    ld (w3d_area_topology_dirty),a
    jp w3d_rebuild_area_connectivity

; Rebuild the 37-byte reachability table from live runtime door records.
; All general-purpose and index registers are preserved; AF is scratch.
w3d_rebuild_area_connectivity:
    push bc
    push de
    push hl
    push ix
    push iy

    xor a
    ld hl,w3d_area_by_player
    ld (hl),a
    ld de,w3d_area_by_player+1
    ld bc,W3D_NUM_AREAS-1
    ldir
    ld hl,w3d_area_queue
    ld (hl),a
    ld de,w3d_area_queue+1
    ld bc,W3D_NUM_AREAS-1
    ldir
    ld (w3d_area_queue_head),a
    ld (w3d_area_queue_tail),a

; Count each malformed live door exactly once per rebuild, independently of
; the number of areas the BFS eventually dequeues. The traversal below then
; skips the same bad record without touching the diagnostic again.
    call w3d_area_validate_live_doors

    ld a,(w3d_player_area)
    cp W3D_NUM_AREAS
    jp nc,@done
    ld (w3d_area_scan_current),a
    ld de,0
    ld e,a
    ld hl,w3d_area_by_player
    add hl,de
    ld (hl),1
    ld hl,w3d_area_queue
    ld (hl),a
    ld a,1
    ld (w3d_area_queue_tail),a

@dequeue:
    ld a,(w3d_area_queue_head)
    ld b,a
    ld a,(w3d_area_queue_tail)
    cp b
    jp z,@done
    ld a,b
    inc a
    ld (w3d_area_queue_head),a
    ld de,0
    ld e,b
    ld hl,w3d_area_queue
    add hl,de
    ld a,(hl)
    ld (w3d_area_scan_current),a

    ld ix,(w3d_doors_ptr)
    ld a,W3D_FIXTURE_DOOR_COUNT
    ld (w3d_area_scan_doors_left),a
@door_loop:
    ld a,(w3d_area_scan_doors_left)
    or a
    jr z,@dequeue
    dec a
    ld (w3d_area_scan_doors_left),a

    ld a,(ix+W3D_DOOR_POSITION+0)
    ld b,a
    ld a,(ix+W3D_DOOR_POSITION+1)
    or b
    jr z,@next_door
    ld a,(ix+W3D_DOOR_AREA1)
    cp W3D_NUM_AREAS
    jr nc,@bad_door
    ld b,a
    ld a,(ix+W3D_DOOR_AREA2)
    cp W3D_NUM_AREAS
    jr nc,@bad_door
    ld c,a
    ld a,(w3d_area_scan_current)
    cp b
    jr z,@candidate_c
    cp c
    jr nz,@next_door
    ld a,b
    jr @consider_candidate
@candidate_c:
    ld a,c
@consider_candidate:
    ld (w3d_area_scan_candidate),a
    ld de,0
    ld e,a
    ld hl,w3d_area_by_player
    add hl,de
    ld a,(hl)
    or a
    jr nz,@next_door
    ld (hl),1                         ; mark before enqueue: at most 37 entries
    ld a,(w3d_area_queue_tail)
    cp W3D_NUM_AREAS
    jr nc,@queue_fault
    ld de,0
    ld e,a
    inc a
    ld (w3d_area_queue_tail),a
    ld hl,w3d_area_queue
    add hl,de
    ld a,(w3d_area_scan_candidate)
    ld (hl),a
    jr @next_door

@queue_fault:
    call w3d_area_note_fault
    jr @next_door
@bad_door:
    ; Preflight already recorded this live malformed record once.
@next_door:
    lea ix,ix+W3D_DOOR_SIZE
    jr @door_loop

@done:
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    ret

w3d_area_validate_live_doors:
    ld ix,(w3d_doors_ptr)
    ld a,W3D_FIXTURE_DOOR_COUNT
    ld (w3d_area_scan_doors_left),a
@loop:
    ld a,(w3d_area_scan_doors_left)
    or a
    ret z
    dec a
    ld (w3d_area_scan_doors_left),a
    ld a,(ix+W3D_DOOR_POSITION+0)
    ld b,a
    ld a,(ix+W3D_DOOR_POSITION+1)
    or b
    jr z,@next
    ld a,(ix+W3D_DOOR_AREA1)
    cp W3D_NUM_AREAS
    jr nc,@fault
    ld a,(ix+W3D_DOOR_AREA2)
    cp W3D_NUM_AREAS
    jr c,@next
@fault:
    call w3d_area_note_fault
@next:
    lea ix,ix+W3D_DOOR_SIZE
    jr @loop

w3d_area_note_fault:
    ld a,(w3d_area_fault_count+0)
    inc a
    ld (w3d_area_fault_count+0),a
    ret nz
    ld a,(w3d_area_fault_count+1)
    inc a
    ld (w3d_area_fault_count+1),a
    ret

; ---------------------------------------------------------------------------
; Persistent state and bounded BFS scratch
; ---------------------------------------------------------------------------

w3d_area_by_player:
    ds W3D_NUM_AREAS
w3d_area_queue:
    ds W3D_NUM_AREAS
w3d_player_area:
    db W3D_SLOT_NONE
w3d_area_last_player_sample:
    db W3D_SLOT_NONE
w3d_area_player_sample_seen:
    db 0
w3d_area_queue_head:
    db 0
w3d_area_queue_tail:
    db 0
w3d_area_topology_dirty:
    db 0
w3d_area_fault_count:
    dw 0
w3d_area_player_tile_x:
    db 0
w3d_area_scan_current:
    db 0
w3d_area_scan_candidate:
    db 0
w3d_area_scan_doors_left:
    db 0
