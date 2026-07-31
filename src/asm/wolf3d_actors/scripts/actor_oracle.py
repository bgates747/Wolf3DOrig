#!/usr/bin/env python3
"""Independent host oracle for the first Wolf3D actor/patrol slice.

This is an executable specification of observable gameplay behavior, not a
translation of the eZ80 implementation.  The contracts come from the original
``DoActor``, ``T_Path``, ``SelectPathDir``, ``TryWalk`` and ``MoveObj`` behavior:

* state durations and speed are expressed in original 70-Hz tics;
* a shared 30-Hz frame clock emits exactly ``2, 2, 3`` original tics;
* a zero actor ``ticcount`` takes the non-transitional branch forever;
* patrol actors reserve their cached destination tile in ``actorat``;
* ordinary cardinal walkers can open and wait for doors, while dogs and
  diagonal movement require a fully open door;
* a malformed negative door wait is decoded at full signed width and fails
  closed instead of aliasing a valid door through its low byte;
* door animation advances before actors in each fixed simulation frame.

Coordinates are signed 16.16 integers.  The model deliberately uses plain
Python objects and sparse dispatch rather than mirroring assembly registers or
control flow, so it can serve as an independent source for regression vectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import struct
from typing import Iterable, Mapping


MAP_SIZE = 64
MAP_BYTES = MAP_SIZE * MAP_SIZE
TILE_GLOBAL = 1 << 16
MIN_ACTOR_DISTANCE = TILE_GLOBAL
AREA_NONE = 0xFF
PATH_NONE = 0xFF

TILE_OPEN = 0
TILE_DOOR_MIN = 0x80
TILE_DOOR_MAX = 0xBF
TILE_DOOR_MASK = 0x7F

DIR_EAST = 0
DIR_NORTHEAST = 1
DIR_NORTH = 2
DIR_NORTHWEST = 3
DIR_WEST = 4
DIR_SOUTHWEST = 5
DIR_SOUTH = 6
DIR_SOUTHEAST = 7
DIR_NODIR = 8

DIR_DELTAS = (
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
)

ACTIVE_NO = 0
ACTIVE_YES = 1
ACTIVE_ALWAYS = 2
ACTIVE_FREE = 0xFF

CLASS_INERT = 2
CLASS_GUARD = 3
CLASS_OFFICER = 4
CLASS_SS = 5
CLASS_DOG = 6
CLASS_FAKE = 9
CLASS_MUTANT = 11

FLAG_SHOOTABLE = 0x01
FLAG_NEVERMARK = 0x04
FLAG_NONMARK = 0x80

DOOR_CLOSED = 0
DOOR_OPENING = 1
DOOR_OPEN = 2
DOOR_CLOSING = 3
DOOR_STEP_SEQUENCE = (0x0955, 0x0955, 0x0956)
DOOR_OPEN_TIMER_STEP = 7
DOOR_OPEN_TIMER_LIMIT = 900

THINK_NONE = 0
THINK_PATH = 1
ACTION_NONE = 0

STATE_INVALID = 0
STATE_GRD_STAND = 1
STATE_GRD_PATH1 = 2
STATE_DOG_PATH1 = 3
STATE_OFC_STAND = 4
STATE_OFC_PATH1 = 5
STATE_MUT_STAND = 6
STATE_MUT_PATH1 = 7
STATE_SS_STAND = 8
STATE_SS_PATH1 = 9
STATE_GRD_DEAD = 10
STATE_BLINKY_CHASE1 = 11
STATE_CLYDE_CHASE1 = 12
STATE_PINKY_CHASE1 = 13
STATE_INKY_CHASE1 = 14
STATE_BOSS_STAND = 15
STATE_GRETEL_STAND = 16
STATE_SCHABBS_STAND = 17
STATE_GIFT_STAND = 18
STATE_FAT_STAND = 19
STATE_FAKE_STAND = 20
STATE_MECHA_STAND = 21
STATE_GRD_PATH1S = 22
STATE_GRD_PATH2 = 23
STATE_GRD_PATH3 = 24
STATE_GRD_PATH3S = 25
STATE_GRD_PATH4 = 26
STATE_DOG_PATH1S = 27
STATE_DOG_PATH2 = 28
STATE_DOG_PATH3 = 29
STATE_DOG_PATH3S = 30
STATE_DOG_PATH4 = 31
STATE_OFC_PATH1S = 32
STATE_OFC_PATH2 = 33
STATE_OFC_PATH3 = 34
STATE_OFC_PATH3S = 35
STATE_OFC_PATH4 = 36
STATE_MUT_PATH1S = 37
STATE_MUT_PATH2 = 38
STATE_MUT_PATH3 = 39
STATE_MUT_PATH3S = 40
STATE_MUT_PATH4 = 41
STATE_SS_PATH1S = 42
STATE_SS_PATH2 = 43
STATE_SS_PATH3 = 44
STATE_SS_PATH3S = 45
STATE_SS_PATH4 = 46


@dataclass(frozen=True)
class State:
    shape: int
    rotations: int
    tictime: int
    think: int
    action: int
    next_state: int


def _path_states(base_id: int, shapes: tuple[int, int, int, int]) -> dict[int, State]:
    """Build one six-state original patrol animation cycle."""

    path1, path1s, path2, path3, path3s, path4 = (
        base_id,
        {STATE_GRD_PATH1: STATE_GRD_PATH1S,
         STATE_DOG_PATH1: STATE_DOG_PATH1S,
         STATE_OFC_PATH1: STATE_OFC_PATH1S,
         STATE_MUT_PATH1: STATE_MUT_PATH1S,
         STATE_SS_PATH1: STATE_SS_PATH1S}[base_id],
        {STATE_GRD_PATH1: STATE_GRD_PATH2,
         STATE_DOG_PATH1: STATE_DOG_PATH2,
         STATE_OFC_PATH1: STATE_OFC_PATH2,
         STATE_MUT_PATH1: STATE_MUT_PATH2,
         STATE_SS_PATH1: STATE_SS_PATH2}[base_id],
        {STATE_GRD_PATH1: STATE_GRD_PATH3,
         STATE_DOG_PATH1: STATE_DOG_PATH3,
         STATE_OFC_PATH1: STATE_OFC_PATH3,
         STATE_MUT_PATH1: STATE_MUT_PATH3,
         STATE_SS_PATH1: STATE_SS_PATH3}[base_id],
        {STATE_GRD_PATH1: STATE_GRD_PATH3S,
         STATE_DOG_PATH1: STATE_DOG_PATH3S,
         STATE_OFC_PATH1: STATE_OFC_PATH3S,
         STATE_MUT_PATH1: STATE_MUT_PATH3S,
         STATE_SS_PATH1: STATE_SS_PATH3S}[base_id],
        {STATE_GRD_PATH1: STATE_GRD_PATH4,
         STATE_DOG_PATH1: STATE_DOG_PATH4,
         STATE_OFC_PATH1: STATE_OFC_PATH4,
         STATE_MUT_PATH1: STATE_MUT_PATH4,
         STATE_SS_PATH1: STATE_SS_PATH4}[base_id],
    )
    w1, w2, w3, w4 = shapes
    return {
        path1: State(w1, 8, 20, THINK_PATH, ACTION_NONE, path1s),
        path1s: State(w1, 8, 5, THINK_NONE, ACTION_NONE, path2),
        path2: State(w2, 8, 15, THINK_PATH, ACTION_NONE, path3),
        path3: State(w3, 8, 20, THINK_PATH, ACTION_NONE, path3s),
        path3s: State(w3, 8, 5, THINK_NONE, ACTION_NONE, path4),
        path4: State(w4, 8, 15, THINK_PATH, ACTION_NONE, path1),
    }


STATES: dict[int, State] = {
    STATE_INVALID: State(-1, 0, 0, THINK_NONE, ACTION_NONE, STATE_INVALID),
    STATE_GRD_STAND: State(50, 8, 0, THINK_NONE, ACTION_NONE, STATE_GRD_STAND),
    STATE_OFC_STAND: State(238, 8, 0, THINK_NONE, ACTION_NONE, STATE_OFC_STAND),
    STATE_MUT_STAND: State(187, 8, 0, THINK_NONE, ACTION_NONE, STATE_MUT_STAND),
    STATE_SS_STAND: State(138, 8, 0, THINK_NONE, ACTION_NONE, STATE_SS_STAND),
    STATE_GRD_DEAD: State(95, 0, 0, THINK_NONE, ACTION_NONE, STATE_GRD_DEAD),
    STATE_BLINKY_CHASE1: State(288, 0, 10, THINK_NONE, ACTION_NONE, STATE_BLINKY_CHASE1),
    STATE_CLYDE_CHASE1: State(292, 0, 10, THINK_NONE, ACTION_NONE, STATE_CLYDE_CHASE1),
    STATE_PINKY_CHASE1: State(290, 0, 10, THINK_NONE, ACTION_NONE, STATE_PINKY_CHASE1),
    STATE_INKY_CHASE1: State(294, 0, 10, THINK_NONE, ACTION_NONE, STATE_INKY_CHASE1),
    STATE_BOSS_STAND: State(296, 0, 0, THINK_NONE, ACTION_NONE, STATE_BOSS_STAND),
    STATE_GRETEL_STAND: State(385, 0, 0, THINK_NONE, ACTION_NONE, STATE_GRETEL_STAND),
    STATE_SCHABBS_STAND: State(307, 0, 0, THINK_NONE, ACTION_NONE, STATE_SCHABBS_STAND),
    STATE_GIFT_STAND: State(360, 0, 0, THINK_NONE, ACTION_NONE, STATE_GIFT_STAND),
    STATE_FAT_STAND: State(396, 0, 0, THINK_NONE, ACTION_NONE, STATE_FAT_STAND),
    STATE_FAKE_STAND: State(321, 0, 0, THINK_NONE, ACTION_NONE, STATE_FAKE_STAND),
    STATE_MECHA_STAND: State(334, 0, 0, THINK_NONE, ACTION_NONE, STATE_MECHA_STAND),
}
STATES.update(_path_states(STATE_GRD_PATH1, (58, 66, 74, 82)))
STATES.update(_path_states(STATE_DOG_PATH1, (99, 107, 115, 123)))
STATES.update(_path_states(STATE_OFC_PATH1, (246, 254, 262, 270)))
STATES.update(_path_states(STATE_MUT_PATH1, (195, 203, 211, 219)))
STATES.update(_path_states(STATE_SS_PATH1, (146, 154, 162, 170)))
assert set(STATES) == set(range(47))


# These are the first six values returned after US_InitRndT(false).  The
# original routine increments its index before lookup.  Six timed actors occur
# in row-major E1L1 medium order, and every one begins in a 20-tic path state.
E1L1_MEDIUM_RANDOM_PREFIX = (8, 109, 220, 222, 241, 149)
E1L1_MEDIUM_PATROL_PHASES = tuple(value % 20 for value in E1L1_MEDIUM_RANDOM_PREFIX)
assert E1L1_MEDIUM_PATROL_PHASES == (8, 9, 0, 2, 1, 9)


def initial_ticcounts(
    states: Iterable[int], random_values: Iterable[int]
) -> list[int]:
    """Apply ``SpawnNewObj`` phase rules to a row-major state sequence.

    Zero-duration states neither consume random data nor acquire a phase.
    """

    random_iter = iter(random_values)
    result: list[int] = []
    for state_id in states:
        state = STATES[state_id]
        result.append(next(random_iter) % state.tictime if state.tictime else 0)
    return result


ACTOR_RECORD = struct.Struct("<ii7BhHihhihhhBB")
assert ACTOR_RECORD.size == 39


@dataclass
class Actor:
    x: int
    y: int
    tile_x: int
    tile_y: int
    area: int = 0
    direction: int = DIR_NODIR
    active: int = ACTIVE_YES
    actor_class: int = CLASS_GUARD
    flags: int = FLAG_SHOOTABLE
    ticcount: int = 0
    state: int = STATE_GRD_PATH1
    distance: int = 0
    angle: int = 0
    hitpoints: int = 25
    speed: int = 512
    temp1: int = 0
    temp2: int = 0
    temp3: int = 0
    next_slot: int = 0xFF
    previous_slot: int = 0xFF

    @classmethod
    def from_bytes(cls, payload: bytes) -> "Actor":
        if len(payload) != ACTOR_RECORD.size:
            raise ValueError(f"actor record must be {ACTOR_RECORD.size} bytes")
        values = ACTOR_RECORD.unpack(payload)
        return cls(
            x=values[0], y=values[1], tile_x=values[2], tile_y=values[3],
            area=values[4], direction=values[5], active=values[6],
            actor_class=values[7], flags=values[8], ticcount=values[9],
            state=values[10], distance=values[11], angle=values[12],
            hitpoints=values[13], speed=values[14], temp1=values[15],
            temp2=values[16], temp3=values[17], next_slot=values[18],
            previous_slot=values[19],
        )

    def to_bytes(self) -> bytes:
        return ACTOR_RECORD.pack(
            self.x, self.y, self.tile_x, self.tile_y, self.area,
            self.direction, self.active, self.actor_class, self.flags,
            self.ticcount, self.state, self.distance, self.angle,
            self.hitpoints, self.speed, self.temp1, self.temp2, self.temp3,
            self.next_slot, self.previous_slot,
        )


@dataclass
class Door:
    tile_x: int
    tile_y: int
    vertical: bool = True
    lock: int = 0
    action: int = DOOR_CLOSED
    position: int = 0
    texture_id: int = 121
    area1: int = 0
    area2: int = 0
    timer: int = 0

    def fixture_bytes(self) -> bytes:
        return struct.pack(
            "<BBBBBHBBB",
            self.tile_x, self.tile_y, int(self.vertical), self.lock,
            self.action, self.position, self.texture_id, self.area1, self.area2,
        )

    @classmethod
    def from_fixture_bytes(cls, payload: bytes) -> "Door":
        if len(payload) != 10:
            raise ValueError("door fixture record must be 10 bytes")
        values = struct.unpack("<BBBBBHBBB", payload)
        return cls(
            tile_x=values[0], tile_y=values[1], vertical=bool(values[2]),
            lock=values[3], action=values[4], position=values[5],
            texture_id=values[6], area1=values[7], area2=values[8],
        )


def empty_bordered_map() -> bytearray:
    result = bytearray(MAP_BYTES)
    for coordinate in range(MAP_SIZE):
        result[coordinate] = 1
        result[(MAP_SIZE - 1) * MAP_SIZE + coordinate] = 1
        result[coordinate * MAP_SIZE] = 1
        result[coordinate * MAP_SIZE + MAP_SIZE - 1] = 1
    return result


def fixed(tile: int, fraction: int = 0x8000) -> int:
    return tile * TILE_GLOBAL + fraction


@dataclass
class World:
    tilemap: bytearray = field(default_factory=empty_bordered_map)
    path_directions: bytearray = field(
        default_factory=lambda: bytearray((PATH_NONE,)) * MAP_BYTES
    )
    area_map: bytearray = field(default_factory=lambda: bytearray(MAP_BYTES))
    static_blocked: bytearray = field(default_factory=lambda: bytearray(MAP_BYTES))
    actors: dict[int, Actor] = field(default_factory=dict)
    actorat: bytearray = field(default_factory=lambda: bytearray(MAP_BYTES))
    doors: dict[int, Door] = field(default_factory=dict)
    player_x: int = field(default_factory=lambda: fixed(2))
    player_y: int = field(default_factory=lambda: fixed(2))
    connected_areas: set[int] = field(default_factory=lambda: set(range(37)))
    actor_clock_phase: int = 0
    door_clock_phase: int = 0
    dirty_actors: set[int] = field(default_factory=set)
    dirty_doors: set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        for name in ("tilemap", "path_directions", "area_map", "static_blocked", "actorat"):
            if len(getattr(self, name)) != MAP_BYTES:
                raise ValueError(f"{name} must contain {MAP_BYTES} bytes")
        self.actor_clock_phase %= 3
        self.door_clock_phase %= 3

    @staticmethod
    def _index(x: int, y: int) -> int:
        if not 0 <= x < MAP_SIZE or not 0 <= y < MAP_SIZE:
            raise IndexError((x, y))
        return y * MAP_SIZE + x

    def add_actor(self, slot: int, actor: Actor, *, claim: bool = True) -> None:
        if not 1 <= slot < 150:
            raise ValueError(slot)
        self.actors[slot] = actor
        if claim and not (actor.flags & FLAG_NEVERMARK):
            self.actorat[self._index(actor.tile_x, actor.tile_y)] = slot

    def install_door(self, index: int, door: Door) -> None:
        if not 0 <= index <= (TILE_DOOR_MAX & TILE_DOOR_MASK):
            raise ValueError(index)
        self.doors[index] = door
        self.tilemap[self._index(door.tile_x, door.tile_y)] = TILE_DOOR_MIN | index

    def set_path(self, x: int, y: int, direction: int) -> None:
        self.path_directions[self._index(x, y)] = direction

    def set_static_blocked(self, x: int, y: int, blocked: bool = True) -> None:
        self.static_blocked[self._index(x, y)] = int(blocked)

    def next_tics(self) -> int:
        value = (2, 2, 3)[self.actor_clock_phase]
        self.actor_clock_phase = (self.actor_clock_phase + 1) % 3
        return value

    def step(self, count: int = 1) -> list[int]:
        """Advance complete fixed frames and return their original-tic values."""

        if count < 0:
            raise ValueError(count)
        emitted: list[int] = []
        for _ in range(count):
            tics = self.next_tics()
            emitted.append(tics)
            self._advance_doors()
            for slot in tuple(sorted(self.actors)):
                actor = self.actors.get(slot)
                if actor is not None:
                    self._do_actor(slot, actor, tics)
        return emitted

    def _advance_doors(self) -> None:
        delta = DOOR_STEP_SEQUENCE[self.door_clock_phase]
        self.door_clock_phase = (self.door_clock_phase + 1) % 3
        for index, door in self.doors.items():
            before = (door.action, door.position, door.timer)
            if door.action == DOOR_OPENING:
                position = door.position + delta
                if position >= 0xFFFF:
                    door.position = 0xFFFF
                    door.action = DOOR_OPEN
                    door.timer = 0
                else:
                    door.position = position
            elif door.action == DOOR_OPEN:
                door.timer = min(DOOR_OPEN_TIMER_LIMIT,
                                 door.timer + DOOR_OPEN_TIMER_STEP)
            elif door.action == DOOR_CLOSING:
                door.position = max(0, door.position - delta)
                if door.position == 0:
                    door.action = DOOR_CLOSED
                    door.timer = 0
            if before != (door.action, door.position, door.timer):
                self.dirty_doors.add(index)

    def request_open_door(self, index: int) -> bool:
        door = self.doors.get(index)
        if door is None:
            return False
        before = (door.action, door.timer)
        if door.action == DOOR_OPEN:
            door.timer = 0
        else:
            door.action = DOOR_OPENING
            door.timer = 0
        if before != (door.action, door.timer):
            self.dirty_doors.add(index)
        return True

    def render_signature(self, actor: Actor) -> tuple[int, int, int, int, int]:
        state = STATES[actor.state]
        facing = actor.direction * 45 if 0 <= actor.direction < 8 else actor.angle % 360
        return state.shape, state.rotations, actor.x, actor.y, facing

    def _release_actorat(self, slot: int, actor: Actor) -> None:
        if actor.flags & (FLAG_NONMARK | FLAG_NEVERMARK):
            return
        index = self._index(actor.tile_x, actor.tile_y)
        if self.actorat[index] == slot:
            self.actorat[index] = 0

    def _claim_actorat(self, slot: int, actor: Actor) -> None:
        if actor.flags & FLAG_NEVERMARK:
            return
        index = self._index(actor.tile_x, actor.tile_y)
        if actor.flags & FLAG_NONMARK and self.actorat[index]:
            return
        self.actorat[index] = slot

    def _do_actor(self, slot: int, actor: Actor, tics: int) -> None:
        if actor.active == ACTIVE_NO and actor.area not in self.connected_areas:
            return
        before = self.render_signature(actor)
        self._release_actorat(slot, actor)

        # Exact original quirk: ticcount==0 is the non-transitional path even
        # when the current state's declared duration is nonzero.
        if actor.ticcount == 0:
            self._think(actor, tics)
        else:
            actor.ticcount -= tics
            transitions = 0
            while actor.ticcount <= 0:
                transitions += 1
                if transitions > 16:
                    raise RuntimeError("state transition budget exhausted")
                state = STATES[actor.state]
                if state.action != ACTION_NONE:
                    raise ValueError(f"unsupported action id {state.action}")
                if state.next_state == STATE_INVALID:
                    del self.actors[slot]
                    self.dirty_actors.add(slot)
                    return
                actor.state = state.next_state
                next_state = STATES[actor.state]
                if next_state.tictime == 0:
                    actor.ticcount = 0
                    break
                actor.ticcount += next_state.tictime
            self._think(actor, tics)

        self._claim_actorat(slot, actor)
        if self.render_signature(actor) != before:
            self.dirty_actors.add(slot)

    def _think(self, actor: Actor, tics: int) -> None:
        think = STATES[actor.state].think
        if think == THINK_NONE:
            return
        if think == THINK_PATH:
            self._think_path(actor, tics)
            return
        raise ValueError(f"unsupported think id {think}")

    def _actorat_blocks(self, actor: Actor, x: int, y: int) -> bool:
        occupant_id = self.actorat[self._index(x, y)]
        if occupant_id == 0:
            return False
        occupant = self.actors.get(occupant_id)
        # A corrupt/stale id must fail closed. Nonshootable live occupants are
        # passable, exactly as the original CHECKSIDE/CHECKDIAG macros.
        return occupant is None or bool(occupant.flags & FLAG_SHOOTABLE)

    def _door_at(self, x: int, y: int) -> tuple[int, Door] | None:
        value = self.tilemap[self._index(x, y)]
        if not TILE_DOOR_MIN <= value <= TILE_DOOR_MAX:
            return None
        index = value & TILE_DOOR_MASK
        door = self.doors.get(index)
        if door is None or (door.tile_x, door.tile_y) != (x, y):
            return None
        return index, door

    def _diag_clear(self, actor: Actor, x: int, y: int) -> bool:
        if not 0 <= x < MAP_SIZE or not 0 <= y < MAP_SIZE:
            return False
        index = self._index(x, y)
        if self.static_blocked[index] or self._actorat_blocks(actor, x, y):
            return False
        value = self.tilemap[index]
        if value == TILE_OPEN:
            return True
        if TILE_DOOR_MIN <= value <= TILE_DOOR_MAX:
            resolved = self._door_at(x, y)
            return resolved is not None and resolved[1].action == DOOR_OPEN
        return False

    def _side_clear(self, actor: Actor, x: int, y: int) -> tuple[bool, int | None]:
        if not 0 <= x < MAP_SIZE or not 0 <= y < MAP_SIZE:
            return False, None
        index = self._index(x, y)
        if self.static_blocked[index] or self._actorat_blocks(actor, x, y):
            return False, None
        value = self.tilemap[index]
        if value == TILE_OPEN:
            return True, None
        if TILE_DOOR_MIN <= value <= TILE_DOOR_MAX:
            resolved = self._door_at(x, y)
            if resolved is None:
                return False, None
            door_index, door = resolved
            return (True, None) if door.action == DOOR_OPEN else (True, door_index)
        return False, None

    def try_walk(self, actor: Actor) -> bool:
        if not 0 <= actor.direction < 8:
            return False
        dx, dy = DIR_DELTAS[actor.direction]
        target_x = actor.tile_x + dx
        target_y = actor.tile_y + dy
        door_index: int | None = None

        if actor.actor_class == CLASS_INERT:
            pass
        elif actor.direction & 1:
            if not (
                self._diag_clear(actor, target_x, target_y)
                and self._diag_clear(actor, actor.tile_x + dx, actor.tile_y)
                and self._diag_clear(actor, actor.tile_x, actor.tile_y + dy)
            ):
                return False
        elif actor.actor_class in (CLASS_DOG, CLASS_FAKE):
            if not self._diag_clear(actor, target_x, target_y):
                return False
        else:
            clear, door_index = self._side_clear(actor, target_x, target_y)
            if not clear:
                return False

        actor.tile_x = target_x
        actor.tile_y = target_y
        if door_index is not None:
            self.request_open_door(door_index)
            actor.distance = -door_index - 1
            return True

        area = self.area_map[self._index(target_x, target_y)]
        if area != AREA_NONE:
            actor.area = area
        actor.distance = TILE_GLOBAL
        return True

    def select_path_dir(self, actor: Actor) -> None:
        arrow = self.path_directions[self._index(actor.tile_x, actor.tile_y)]
        if 0 <= arrow < 8:
            actor.direction = arrow
        actor.distance = TILE_GLOBAL
        if not self.try_walk(actor):
            actor.direction = DIR_NODIR

    def _move_obj(self, actor: Actor, move: int) -> bool:
        if not 0 <= actor.direction < 8:
            return False
        dx, dy = DIR_DELTAS[actor.direction]
        old_x, old_y = actor.x, actor.y
        actor.x += dx * move
        actor.y += dy * move
        if actor.area in self.connected_areas:
            delta_x = actor.x - self.player_x
            delta_y = actor.y - self.player_y
            if (
                -MIN_ACTOR_DISTANCE <= delta_x <= MIN_ACTOR_DISTANCE
                and -MIN_ACTOR_DISTANCE <= delta_y <= MIN_ACTOR_DISTANCE
            ):
                actor.x, actor.y = old_x, old_y
                return False
        actor.distance -= move
        return True

    def _think_path(self, actor: Actor, tics: int) -> None:
        if actor.direction == DIR_NODIR:
            self.select_path_dir(actor)
            if actor.direction == DIR_NODIR:
                return

        move = actor.speed * tics
        while move:
            if actor.distance < 0:
                # Decode the complete signed distance.  The eZ80 stores the
                # field as int32 even though valid waits are only -1..-64;
                # truncating here would let -257 masquerade as door zero.
                door_index = -actor.distance - 1
                if not self.request_open_door(door_index):
                    actor.direction = DIR_NODIR
                    return
                if self.doors[door_index].action != DOOR_OPEN:
                    return
                actor.distance = TILE_GLOBAL

            if move < actor.distance:
                self._move_obj(actor, move)
                return

            actor.x = fixed(actor.tile_x)
            actor.y = fixed(actor.tile_y)
            move -= actor.distance
            self.select_path_dir(actor)
            if actor.direction == DIR_NODIR:
                return


def world_from_sparse(
    *,
    cells: Iterable[tuple[int, int, int, int, int, int]] = (),
    doors: Mapping[int, Door] | None = None,
) -> World:
    """Convenience constructor for durable vector generators and tests.

    Each cell is ``(x, y, tile, path, area, static_blocked)``.  Unspecified
    interior cells are ordinary open area zero with no arrow.
    """

    world = World()
    for x, y, tile, path, area, static in cells:
        index = world._index(x, y)
        world.tilemap[index] = tile
        world.path_directions[index] = path
        world.area_map[index] = area
        world.static_blocked[index] = static
    for index, door in (doors or {}).items():
        world.install_door(index, door)
    return world
