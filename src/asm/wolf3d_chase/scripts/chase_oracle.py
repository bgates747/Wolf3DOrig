#!/usr/bin/env python3
"""Independent host specification for ordinary Wolf3D chase movement.

The model begins after awareness has installed an ordinary actor's first
chase state.  It specifies the source-faithful direction selectors and one
``T_Chase``/``T_DogChase`` think call while composing with the already-settled
eZ80 TryWalk, MoveObj, door, occupancy, area, and 2,2,3 clock contracts.

Attacks are deliberately a seam.  A successful ranged roll returns
``AttackRequest.RANGED``; projected dog-jump range returns
``AttackRequest.DOG_JUMP_REQUESTED`` (meaning "install s_dogjump1", not an
immediate bite).  Both stop movement for that call without changing state or
player health.  The future combat layer owns those state transitions and
damage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Protocol, Sequence


MAP_SIZE = 64
MAP_BYTES = MAP_SIZE * MAP_SIZE
NUM_AREAS = 37
TILE_GLOBAL = 1 << 16
MIN_ACTOR_DISTANCE = TILE_GLOBAL
AREA_NONE = 0xFF

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
OPPOSITE = (
    DIR_WEST,
    DIR_SOUTHWEST,
    DIR_SOUTH,
    DIR_SOUTHEAST,
    DIR_EAST,
    DIR_NORTHEAST,
    DIR_NORTH,
    DIR_NORTHWEST,
    DIR_NODIR,
)

CLASS_INERT = 2
CLASS_GUARD = 3
CLASS_OFFICER = 4
CLASS_SS = 5
CLASS_DOG = 6
CLASS_FAKE = 9
CLASS_MUTANT = 11
ORDINARY_RANGED_CLASSES = frozenset(
    (CLASS_GUARD, CLASS_OFFICER, CLASS_SS, CLASS_MUTANT)
)

FLAG_SHOOTABLE = 0x01
FLAG_NEVERMARK = 0x04
FLAG_FIRSTATTACK = 0x20
FLAG_NONMARK = 0x80

DOOR_CLOSED = 0
DOOR_OPENING = 1
DOOR_OPEN = 2
DOOR_CLOSING = 3


class ChaseContractError(ValueError):
    """Raised when a caller or deterministic fixture violates the contract."""


class AttackRequest(IntEnum):
    """Production-facing action seam returned by one chase think call."""

    NONE = 0
    RANGED = 1
    DOG_JUMP_REQUESTED = 2
    CORRUPT = 0xFF


class ByteRng(Protocol):
    def next_byte(self) -> int:
        """Return one deterministic unsigned byte."""


LineOfSight = Callable[["Actor", "World"], bool]


@dataclass
class SequenceRng:
    values: Sequence[int]
    index: int = 0
    history: list[int] = field(default_factory=list)

    @property
    def draws(self) -> int:
        return self.index

    def next_byte(self) -> int:
        if self.index >= len(self.values):
            raise ChaseContractError("chase RNG exhausted")
        value = self.values[self.index]
        self.index += 1
        if not 0 <= value <= 0xFF:
            raise ChaseContractError(f"chase RNG returned {value!r}")
        self.history.append(value)
        return value


@dataclass
class Actor:
    x: int
    y: int
    tile_x: int
    tile_y: int
    area: int = 0
    direction: int = DIR_NODIR
    actor_class: int = CLASS_GUARD
    flags: int = FLAG_SHOOTABLE
    distance: int = 0
    speed: int = 1536


@dataclass
class Door:
    tile_x: int
    tile_y: int
    action: int = DOOR_CLOSED
    position: int = 0
    timer: int = 0


@dataclass(frozen=True)
class ChaseOutcome:
    attack_request: AttackRequest = AttackRequest.NONE
    moved: bool = False
    blocked: bool = False
    waiting_for_door: bool = False
    player_blocked: bool = False
    attack_chance: int | None = None
    attack_roll: int | None = None


def fixed(tile: int, fraction: int = 0x8000) -> int:
    return tile * TILE_GLOBAL + fraction


def empty_bordered_map() -> bytearray:
    result = bytearray(MAP_BYTES)
    for coordinate in range(MAP_SIZE):
        result[coordinate] = 1
        result[(MAP_SIZE - 1) * MAP_SIZE + coordinate] = 1
        result[coordinate * MAP_SIZE] = 1
        result[coordinate * MAP_SIZE + MAP_SIZE - 1] = 1
    return result


def _diagonal(first: int, second: int) -> int:
    # The original diagonal[9][9] table is symmetric.  SelectDodgeDir may
    # present its horizontal/vertical components in either order after the
    # distance and RNG swaps, so a one-way mapping would silently suppress
    # valid diagonal choices.
    if first in (DIR_NORTH, DIR_SOUTH):
        first, second = second, first
    return {
        (DIR_EAST, DIR_NORTH): DIR_NORTHEAST,
        (DIR_WEST, DIR_NORTH): DIR_NORTHWEST,
        (DIR_WEST, DIR_SOUTH): DIR_SOUTHWEST,
        (DIR_EAST, DIR_SOUTH): DIR_SOUTHEAST,
    }.get((first, second), DIR_NODIR)


@dataclass
class World:
    tilemap: bytearray = field(default_factory=empty_bordered_map)
    area_map: bytearray = field(default_factory=lambda: bytearray(MAP_BYTES))
    static_blocked: bytearray = field(default_factory=lambda: bytearray(MAP_BYTES))
    actors: dict[int, Actor] = field(default_factory=dict)
    actorat: bytearray = field(default_factory=lambda: bytearray(MAP_BYTES))
    doors: dict[int, Door] = field(default_factory=dict)
    player_x: int = field(default_factory=lambda: fixed(2))
    player_y: int = field(default_factory=lambda: fixed(2))
    connected_areas: set[int] = field(default_factory=lambda: set(range(NUM_AREAS)))
    clock_phase: int = 0
    try_log: list[int] = field(default_factory=list)
    door_request_log: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name in ("tilemap", "area_map", "static_blocked", "actorat"):
            if len(getattr(self, name)) != MAP_BYTES:
                raise ChaseContractError(f"{name} must contain {MAP_BYTES} bytes")
        self.clock_phase %= 3

    @property
    def player_tile_x(self) -> int:
        return self.player_x >> 16

    @property
    def player_tile_y(self) -> int:
        return self.player_y >> 16

    @staticmethod
    def index(x: int, y: int) -> int:
        if not 0 <= x < MAP_SIZE or not 0 <= y < MAP_SIZE:
            raise IndexError((x, y))
        return y * MAP_SIZE + x

    def next_tics(self) -> int:
        value = (2, 2, 3)[self.clock_phase]
        self.clock_phase = (self.clock_phase + 1) % 3
        return value

    def add_actor(self, slot: int, actor: Actor, *, claim: bool = True) -> None:
        if not 1 <= slot < 150:
            raise ChaseContractError(f"invalid actor slot {slot}")
        self.actors[slot] = actor
        if claim and not actor.flags & (FLAG_NONMARK | FLAG_NEVERMARK):
            self.actorat[self.index(actor.tile_x, actor.tile_y)] = slot

    def install_door(self, index: int, door: Door) -> None:
        if not 0 <= index <= (TILE_DOOR_MAX & TILE_DOOR_MASK):
            raise ChaseContractError(f"invalid door index {index}")
        self.doors[index] = door
        self.tilemap[self.index(door.tile_x, door.tile_y)] = TILE_DOOR_MIN | index

    def set_wall(self, x: int, y: int, value: int = 1) -> None:
        if not 1 <= value < TILE_DOOR_MIN:
            raise ChaseContractError(f"invalid wall byte {value}")
        self.tilemap[self.index(x, y)] = value

    def set_static_blocked(self, x: int, y: int, blocked: bool = True) -> None:
        self.static_blocked[self.index(x, y)] = int(blocked)

    def _release(self, slot: int, actor: Actor) -> None:
        if actor.flags & (FLAG_NONMARK | FLAG_NEVERMARK):
            return
        index = self.index(actor.tile_x, actor.tile_y)
        if self.actorat[index] == slot:
            self.actorat[index] = 0

    def _claim(self, slot: int, actor: Actor) -> None:
        # The settled eZ80 scheduler keeps both exceptional flag classes
        # wholly unreserved.  (The DOS DoActor source conditionally reclaimed
        # NONMARK actors, but that behavior is intentionally outside the
        # already-established port contract this layer composes with.)
        if actor.flags & (FLAG_NONMARK | FLAG_NEVERMARK):
            return
        index = self.index(actor.tile_x, actor.tile_y)
        self.actorat[index] = slot

    def _occupant_blocks(self, x: int, y: int) -> bool:
        slot = self.actorat[self.index(x, y)]
        if slot == 0:
            return False
        occupant = self.actors.get(slot)
        return occupant is None or bool(occupant.flags & FLAG_SHOOTABLE)

    def _door_at(self, x: int, y: int) -> tuple[int, Door] | None:
        value = self.tilemap[self.index(x, y)]
        if not TILE_DOOR_MIN <= value <= TILE_DOOR_MAX:
            return None
        door_index = value & TILE_DOOR_MASK
        door = self.doors.get(door_index)
        if door is None or (door.tile_x, door.tile_y) != (x, y):
            return None
        return door_index, door

    def _diag_clear(self, x: int, y: int) -> bool:
        if not 0 <= x < MAP_SIZE or not 0 <= y < MAP_SIZE:
            return False
        index = self.index(x, y)
        if self.static_blocked[index] or self._occupant_blocks(x, y):
            return False
        value = self.tilemap[index]
        if value == TILE_OPEN:
            return True
        if TILE_DOOR_MIN <= value <= TILE_DOOR_MAX:
            resolved = self._door_at(x, y)
            return resolved is not None and resolved[1].action == DOOR_OPEN
        return False

    def _side_clear(self, x: int, y: int) -> tuple[bool, int | None]:
        if not 0 <= x < MAP_SIZE or not 0 <= y < MAP_SIZE:
            return False, None
        index = self.index(x, y)
        if self.static_blocked[index] or self._occupant_blocks(x, y):
            return False, None
        value = self.tilemap[index]
        if value == TILE_OPEN:
            return True, None
        if TILE_DOOR_MIN <= value <= TILE_DOOR_MAX:
            resolved = self._door_at(x, y)
            if resolved is None:
                return False, None
            door_index, door = resolved
            if door.action == DOOR_OPEN:
                return True, None
            return True, door_index
        return False, None

    def request_open_door(self, index: int) -> bool:
        self.door_request_log.append(index)
        door = self.doors.get(index)
        if door is None:
            return False
        if door.action == DOOR_OPEN:
            door.timer = 0
        else:
            door.action = DOOR_OPENING
            door.timer = 0
        return True

    def try_walk(self, actor: Actor) -> bool:
        """Apply the settled TryWalk contract for one proposed direction."""

        self.try_log.append(actor.direction)
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
                self._diag_clear(target_x, target_y)
                and self._diag_clear(actor.tile_x + dx, actor.tile_y)
                and self._diag_clear(actor.tile_x, actor.tile_y + dy)
            ):
                return False
        elif actor.actor_class in (CLASS_DOG, CLASS_FAKE):
            if not self._diag_clear(target_x, target_y):
                return False
        else:
            clear, door_index = self._side_clear(target_x, target_y)
            if not clear:
                return False

        actor.tile_x = target_x
        actor.tile_y = target_y
        if door_index is not None:
            self.request_open_door(door_index)
            actor.distance = -door_index - 1
            return True

        area = self.area_map[self.index(target_x, target_y)]
        if area != AREA_NONE and area < NUM_AREAS:
            actor.area = area
        actor.distance = TILE_GLOBAL
        return True

    def move_obj(self, actor: Actor, move: int) -> bool:
        """Apply MoveObj, including connected-area inclusive rollback."""

        if move < 0 or not 0 <= actor.direction < 8:
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

    def select_chase_dir(self, actor: Actor, rng: ByteRng) -> bool:
        """Select the source's direct, old, then randomized search direction."""

        if not 0 <= actor.direction <= DIR_NODIR:
            actor.direction = DIR_NODIR
            return False
        old_direction = actor.direction
        turnaround = OPPOSITE[old_direction]
        delta_x = self.player_tile_x - actor.tile_x
        delta_y = self.player_tile_y - actor.tile_y

        first = DIR_NODIR
        second = DIR_NODIR
        if delta_x > 0:
            first = DIR_EAST
        elif delta_x < 0:
            first = DIR_WEST
        if delta_y > 0:
            second = DIR_SOUTH
        elif delta_y < 0:
            second = DIR_NORTH
        if abs(delta_y) > abs(delta_x):
            first, second = second, first

        if first == turnaround:
            first = DIR_NODIR
        if second == turnaround:
            second = DIR_NODIR

        for direction in (first, second):
            if direction == DIR_NODIR:
                continue
            actor.direction = direction
            if self.try_walk(actor):
                return True

        if old_direction != DIR_NODIR:
            actor.direction = old_direction
            if self.try_walk(actor):
                return True

        # This intentionally preserves the source's surprising N,NW,W or
        # W,NW,N scan and its strict >128 threshold.
        roll = rng.next_byte()
        search = (
            (DIR_NORTH, DIR_NORTHWEST, DIR_WEST)
            if roll > 128
            else (DIR_WEST, DIR_NORTHWEST, DIR_NORTH)
        )
        for direction in search:
            if direction == turnaround:
                continue
            actor.direction = direction
            if self.try_walk(actor):
                return True

        if turnaround != DIR_NODIR:
            actor.direction = turnaround
            if self.try_walk(actor):
                return True

        actor.direction = DIR_NODIR
        return False

    def select_dodge_dir(self, actor: Actor, rng: ByteRng) -> bool:
        """Select diagonal/cardinal dodge order with exact FIRSTATTACK rules."""

        if not 0 <= actor.direction <= DIR_NODIR:
            actor.direction = DIR_NODIR
            return False
        if actor.flags & FLAG_FIRSTATTACK:
            turnaround = DIR_NODIR
            actor.flags &= ~FLAG_FIRSTATTACK
        else:
            turnaround = OPPOSITE[actor.direction]

        delta_x = self.player_tile_x - actor.tile_x
        delta_y = self.player_tile_y - actor.tile_y
        first = DIR_EAST if delta_x > 0 else DIR_WEST
        third = DIR_WEST if delta_x > 0 else DIR_EAST
        second = DIR_SOUTH if delta_y > 0 else DIR_NORTH
        fourth = DIR_NORTH if delta_y > 0 else DIR_SOUTH

        if abs(delta_x) > abs(delta_y):
            first, second = second, first
            third, fourth = fourth, third
        if rng.next_byte() < 128:
            first, second = second, first
            third, fourth = fourth, third

        diagonal = _diagonal(first, second)
        for direction in (diagonal, first, second, third, fourth):
            if direction in (DIR_NODIR, turnaround):
                continue
            actor.direction = direction
            if self.try_walk(actor):
                return True

        if turnaround != DIR_NODIR:
            actor.direction = turnaround
            if self.try_walk(actor):
                return True

        actor.direction = DIR_NODIR
        return False

    def chase_step(
        self,
        slot: int,
        *,
        original_tics: int,
        rng: ByteRng,
        line_of_sight: LineOfSight,
    ) -> ChaseOutcome:
        """Run one ordinary ``T_Chase`` think with attacks exposed as a seam."""

        actor = self.actors[slot]
        if actor.actor_class not in ORDINARY_RANGED_CLASSES:
            return ChaseOutcome(attack_request=AttackRequest.CORRUPT)
        if not 0 <= original_tics <= 0xFF:
            raise ChaseContractError(f"invalid original tic count {original_tics}")
        if not 0 <= actor.direction <= DIR_NODIR:
            return ChaseOutcome(attack_request=AttackRequest.CORRUPT)

        old_pose = (actor.x, actor.y)
        self._release(slot, actor)
        try:
            dodge = False
            attack_chance: int | None = None
            attack_roll: int | None = None
            if line_of_sight(actor, self):
                distance = max(
                    abs(actor.tile_x - self.player_tile_x),
                    abs(actor.tile_y - self.player_tile_y),
                )
                if distance == 0 or (distance == 1 and actor.distance < 0x4000):
                    attack_chance = 300
                else:
                    attack_chance = (original_tics << 4) // distance
                attack_roll = rng.next_byte()
                if attack_roll < attack_chance:
                    return ChaseOutcome(
                        attack_request=AttackRequest.RANGED,
                        attack_chance=attack_chance,
                        attack_roll=attack_roll,
                    )
                dodge = True

            if actor.direction == DIR_NODIR:
                selected = (
                    self.select_dodge_dir(actor, rng)
                    if dodge
                    else self.select_chase_dir(actor, rng)
                )
                if not selected:
                    return ChaseOutcome(
                        blocked=True,
                        attack_chance=attack_chance,
                        attack_roll=attack_roll,
                    )

            move = actor.speed * original_tics
            while move:
                if actor.distance < 0:
                    door_index = -actor.distance - 1
                    if not self.request_open_door(door_index):
                        actor.direction = DIR_NODIR
                        return ChaseOutcome(attack_request=AttackRequest.CORRUPT)
                    if self.doors[door_index].action != DOOR_OPEN:
                        return ChaseOutcome(
                            waiting_for_door=True,
                            moved=(actor.x, actor.y) != old_pose,
                            attack_chance=attack_chance,
                            attack_roll=attack_roll,
                        )
                    actor.distance = TILE_GLOBAL

                if move < actor.distance:
                    moved = self.move_obj(actor, move)
                    return ChaseOutcome(
                        moved=moved and (actor.x, actor.y) != old_pose,
                        player_blocked=not moved,
                        attack_chance=attack_chance,
                        attack_roll=attack_roll,
                    )

                actor.x = fixed(actor.tile_x)
                actor.y = fixed(actor.tile_y)
                move -= actor.distance
                selected = (
                    self.select_dodge_dir(actor, rng)
                    if dodge
                    else self.select_chase_dir(actor, rng)
                )
                if not selected:
                    return ChaseOutcome(
                        moved=(actor.x, actor.y) != old_pose,
                        blocked=True,
                        attack_chance=attack_chance,
                        attack_roll=attack_roll,
                    )

            return ChaseOutcome(
                moved=(actor.x, actor.y) != old_pose,
                attack_chance=attack_chance,
                attack_roll=attack_roll,
            )
        finally:
            self._claim(slot, actor)

    def dog_chase_step(
        self,
        slot: int,
        *,
        original_tics: int,
        rng: ByteRng,
    ) -> ChaseOutcome:
        """Run one ``T_DogChase`` think through the dog-jump request seam."""

        actor = self.actors[slot]
        if actor.actor_class != CLASS_DOG:
            return ChaseOutcome(attack_request=AttackRequest.CORRUPT)
        if not 0 <= original_tics <= 0xFF:
            raise ChaseContractError(f"invalid original tic count {original_tics}")
        if not 0 <= actor.direction <= DIR_NODIR:
            return ChaseOutcome(attack_request=AttackRequest.CORRUPT)

        old_pose = (actor.x, actor.y)
        self._release(slot, actor)
        try:
            if actor.direction == DIR_NODIR:
                if not self.select_dodge_dir(actor, rng):
                    return ChaseOutcome(blocked=True)

            move = actor.speed * original_tics
            while move:
                if actor.distance < 0:
                    # A dog cannot acquire a door wait through TryWalk.  The
                    # settled port fails an injected impossible state closed
                    # before even exposing a projected jump request.
                    return ChaseOutcome(attack_request=AttackRequest.CORRUPT)

                if (
                    abs(self.player_x - actor.x) - move <= MIN_ACTOR_DISTANCE
                    and abs(self.player_y - actor.y) - move <= MIN_ACTOR_DISTANCE
                ):
                    return ChaseOutcome(
                        attack_request=AttackRequest.DOG_JUMP_REQUESTED
                    )

                if move < actor.distance:
                    moved = self.move_obj(actor, move)
                    return ChaseOutcome(
                        moved=moved and (actor.x, actor.y) != old_pose,
                        player_blocked=not moved,
                    )

                actor.x = fixed(actor.tile_x)
                actor.y = fixed(actor.tile_y)
                move -= actor.distance
                if not self.select_dodge_dir(actor, rng):
                    return ChaseOutcome(
                        moved=(actor.x, actor.y) != old_pose,
                        blocked=True,
                    )

            return ChaseOutcome(moved=(actor.x, actor.y) != old_pose)
        finally:
            self._claim(slot, actor)
