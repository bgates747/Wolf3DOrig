#!/usr/bin/env python3
"""Independent oracle for Wolf3D player-area connectivity and actor gating.

The production contract intentionally keeps only the externally useful result
of the original area graph: one byte per area saying whether that area is in
the player's current connected component.  A rebuild performs an iterative
BFS that scans the authoritative door records directly.  A door contributes
an undirected edge exactly when its 0.16 position is nonzero; action labels do
not affect topology.

This module does not mirror eZ80 register flow and does not import production
asset code.  It is therefore suitable as the host-side expected-value source
for direct assembly regressions.
"""

from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Iterable, Sequence


NUM_AREAS = 37
MAX_DOORS = 64
AREA_NONE = 0xFF
TILE_GLOBAL = 1 << 16

ACTIVE_NO = 0
ACTIVE_YES = 1
ACTIVE_ALWAYS = 2
ACTIVE_FREE = 0xFF

DOOR_CLOSED = 0
DOOR_OPENING = 1
DOOR_OPEN = 2
DOOR_CLOSING = 3

DOOR_RECORD = struct.Struct("<BBBBBHBBB")
DOOR_SIZE = DOOR_RECORD.size
assert DOOR_SIZE == 10

ACTOR_SIZE = 39
ACTOR_AREA = 10
ACTOR_ACTIVE = 12


@dataclass
class Door:
    tile_x: int
    tile_y: int
    vertical: bool
    lock: int
    action: int
    position: int
    texture_id: int
    area1: int
    area2: int

    @classmethod
    def from_bytes(cls, payload: bytes) -> "Door":
        if len(payload) != DOOR_SIZE:
            raise ValueError(f"door record must be {DOOR_SIZE} bytes")
        values = DOOR_RECORD.unpack(payload)
        return cls(
            tile_x=values[0], tile_y=values[1], vertical=bool(values[2]),
            lock=values[3], action=values[4], position=values[5],
            texture_id=values[6], area1=values[7], area2=values[8],
        )

    def to_bytes(self) -> bytes:
        if not 0 <= self.position <= 0xFFFF:
            raise ValueError(self.position)
        return DOOR_RECORD.pack(
            self.tile_x, self.tile_y, int(self.vertical), self.lock,
            self.action, self.position, self.texture_id, self.area1, self.area2,
        )

    @property
    def contributes_edge(self) -> bool:
        return self.position != 0


def synthetic_door(
    area1: int,
    area2: int,
    *,
    position: int = 0,
    action: int = DOOR_CLOSED,
    tile_x: int = 10,
    tile_y: int = 10,
) -> Door:
    """Return a compact directed-test door with otherwise inert metadata."""

    return Door(tile_x, tile_y, True, 0, action, position, 121, area1, area2)


class AreaConnectivity:
    """Lean 37-area connectivity state with transition-aware fault counts.

    Invalid open endpoints are ignored and faulted once per rebuild.  An
    invalid player root clears reachability and faults only when the root
    transitions into that invalid value; a later forced topology rebuild does
    not repeatedly charge the unchanged bad root.
    """

    def __init__(self, doors: Iterable[Door], player_area: int) -> None:
        self.doors = list(doors)
        if len(self.doors) > MAX_DOORS:
            raise ValueError(f"at most {MAX_DOORS} doors are supported")
        self.reachable = bytearray(NUM_AREAS)
        self.player_area: int | None = None
        self.fault_count = 0
        self.last_rebuild_faults = 0
        self.rebuild_count = 0
        self.last_invalid_open_doors: tuple[int, ...] = ()
        self.last_queue_peak = 0
        self.set_player_area(player_area)

    @staticmethod
    def valid_area(area: int | None) -> bool:
        return area is not None and 0 <= area < NUM_AREAS

    @property
    def reachable_areas(self) -> frozenset[int]:
        return frozenset(index for index, value in enumerate(self.reachable) if value)

    def set_player_area(self, area: int) -> bool:
        """Update the root and rebuild only on a numeric transition.

        Returns true when a transition occurred.  The first assignment counts
        as a transition, including an initially invalid/0xff root.
        """

        if self.player_area == area:
            return False
        self.player_area = area
        self.rebuild(root_transition_fault=not self.valid_area(area))
        return True

    def set_door_position(self, index: int, position: int) -> bool:
        """Update one position, rebuilding only across the zero threshold."""

        if not 0 <= index < len(self.doors):
            raise IndexError(index)
        if not 0 <= position <= 0xFFFF:
            raise ValueError(position)
        door = self.doors[index]
        old_live = door.contributes_edge
        door.position = position
        changed = old_live != door.contributes_edge
        if changed:
            self.rebuild()
        return changed

    def force_rebuild(self) -> None:
        """Rebuild after bulk load or a batched set of door transitions."""

        self.rebuild()

    def rebuild(self, *, root_transition_fault: bool = False) -> None:
        self.rebuild_count += 1
        self.reachable[:] = bytes(NUM_AREAS)
        rebuild_faults = int(root_transition_fault)

        valid_edges: list[tuple[int, int]] = []
        invalid_open_doors: list[int] = []
        for index, door in enumerate(self.doors):
            if not door.contributes_edge:
                continue
            if not (self.valid_area(door.area1) and self.valid_area(door.area2)):
                invalid_open_doors.append(index)
                rebuild_faults += 1
                continue
            valid_edges.append((door.area1, door.area2))

        self.last_invalid_open_doors = tuple(invalid_open_doors)
        self.last_rebuild_faults = rebuild_faults
        self.fault_count += rebuild_faults

        if not self.valid_area(self.player_area):
            self.last_queue_peak = 0
            return

        assert self.player_area is not None
        queue = bytearray(NUM_AREAS)
        queue[0] = self.player_area
        self.reachable[self.player_area] = 1
        head = 0
        tail = 1
        peak = 1

        while head < tail:
            area = queue[head]
            head += 1
            for area1, area2 in valid_edges:
                if area1 == area:
                    neighbor = area2
                elif area2 == area:
                    neighbor = area1
                else:
                    continue
                if self.reachable[neighbor]:
                    continue
                self.reachable[neighbor] = 1  # mark before enqueue
                if tail >= NUM_AREAS:
                    raise AssertionError("37-entry area queue overflow")
                queue[tail] = neighbor
                tail += 1
                peak = max(peak, tail - head)

        self.last_queue_peak = peak


def _check_reachability(reachable: Sequence[int]) -> None:
    if len(reachable) != NUM_AREAS:
        raise ValueError(f"reachability table must contain {NUM_AREAS} bytes")


def actor_schedulable(actor_record: bytes, reachable: Sequence[int]) -> bool:
    """Return the original DoActor scheduling gate without mutating ACTIVE."""

    if len(actor_record) != ACTOR_SIZE:
        raise ValueError(f"actor record must be {ACTOR_SIZE} bytes")
    _check_reachability(reachable)
    active = actor_record[ACTOR_ACTIVE]
    if active in (ACTIVE_YES, ACTIVE_ALWAYS):
        return True
    if active != ACTIVE_NO:
        return False
    area = actor_record[ACTOR_AREA]
    return area < NUM_AREAS and bool(reachable[area])


def actor_candidate_clear_of_player(
    actor_record: bytes,
    reachable: Sequence[int],
    *,
    candidate_x: int,
    candidate_y: int,
    player_x: int,
    player_y: int,
) -> bool:
    """Return whether MoveObj may retain a candidate position.

    The original inclusive one-tile player square applies only when the
    actor's area belongs to the player's connected component.  Disconnected
    or malformed actor areas bypass this proximity rejection.
    """

    if len(actor_record) != ACTOR_SIZE:
        raise ValueError(f"actor record must be {ACTOR_SIZE} bytes")
    _check_reachability(reachable)
    area = actor_record[ACTOR_AREA]
    if area >= NUM_AREAS or not reachable[area]:
        return True
    return (
        abs(candidate_x - player_x) > TILE_GLOBAL
        or abs(candidate_y - player_y) > TILE_GLOBAL
    )


def actor_record(*, area: int, active: int, x: int = 0, y: int = 0) -> bytes:
    """Build a minimal 39-byte actor record for host/direct test scenarios."""

    payload = bytearray(ACTOR_SIZE)
    struct.pack_into("<ii", payload, 0, x, y)
    payload[ACTOR_AREA] = area & 0xFF
    payload[ACTOR_ACTIVE] = active & 0xFF
    return bytes(payload)
