#!/usr/bin/env python3
"""Independent host specification for Wolf3D actor awareness.

This module specifies the narrow boundary between the already-regressed area
and sight predicates and the future actor chase layer.  It intentionally does
not import production assembly, fixture generators, or the DDA oracle.  The
expensive wall/door decision is supplied as a replaceable ``line_of_sight``
callable, while this module owns the ordering of area, proximity, facing,
noise, ambush, reaction-delay, and activation decisions.

The behavior is grounded in ``SightPlayer``, ``CheckSight``, and
``FirstSighting`` from the educational WL1 source.  The eight-direction
facing predicate follows the current eZ80 sight contract, which extends the
four cardinal source checks to all path directions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence


NUM_AREAS = 37
TILE_GLOBAL = 1 << 16
MIN_SIGHT = 0x00018000

DIR_EAST = 0
DIR_NORTHEAST = 1
DIR_NORTH = 2
DIR_NORTHWEST = 3
DIR_WEST = 4
DIR_SOUTHWEST = 5
DIR_SOUTH = 6
DIR_SOUTHEAST = 7
DIR_NODIR = 8

CLASS_GUARD = 3
CLASS_OFFICER = 4
CLASS_SS = 5
CLASS_DOG = 6
CLASS_MUTANT = 11

FLAG_SHOOTABLE = 0x01
FLAG_ATTACKMODE = 0x10
FLAG_FIRSTATTACK = 0x20
FLAG_AMBUSH = 0x40

CHASE_TICS = 10

# These labels are semantic oracle values, not proposed assembly state ids.
# A direct-eZ80 vector generator can translate them after the production
# state-table extension chooses stable numeric ids.
CHASE_STATE_BY_CLASS = {
    CLASS_GUARD: "guard_chase1",
    CLASS_OFFICER: "officer_chase1",
    CLASS_SS: "ss_chase1",
    CLASS_DOG: "dog_chase1",
    CLASS_MUTANT: "mutant_chase1",
}

SPEED_MULTIPLIER_BY_CLASS = {
    CLASS_GUARD: 3,
    CLASS_OFFICER: 5,
    CLASS_SS: 4,
    CLASS_DOG: 2,
    CLASS_MUTANT: 3,
}

RANDOM_DELAY_DIVISOR_BY_CLASS = {
    CLASS_GUARD: 4,
    CLASS_SS: 6,
    CLASS_DOG: 8,
    CLASS_MUTANT: 6,
}


class AwarenessContractError(ValueError):
    """Raised when the awareness routine is called outside its contract."""


class AwarenessEvent(Enum):
    """One externally useful outcome of a single original-tic update."""

    UNAWARE = "unaware"
    DELAY_STARTED = "delay_started"
    DELAY_WAITING = "delay_waiting"
    ACTIVATED = "activated"


class ByteRng(Protocol):
    """Minimal deterministic RNG boundary used by reaction-delay seeding."""

    def next_byte(self) -> int:
        """Return one unsigned byte."""


class LineOfSight(Protocol):
    """Replaceable wall/door trace supplied by the sight implementation."""

    def __call__(self, actor: "Actor", player: "Player") -> bool:
        """Return true when no wall or door blocks the segment."""


@dataclass
class SequenceRng:
    """Finite deterministic byte stream for host and direct-vector tests."""

    values: Sequence[int]
    index: int = 0

    @property
    def draws(self) -> int:
        return self.index

    def next_byte(self) -> int:
        if self.index >= len(self.values):
            raise AwarenessContractError("reaction RNG exhausted")
        value = self.values[self.index]
        self.index += 1
        if not 0 <= value <= 0xFF:
            raise AwarenessContractError(f"reaction RNG returned {value!r}")
        return value


@dataclass(frozen=True)
class Player:
    x: int
    y: int


@dataclass
class Actor:
    """Only durable actor fields observed or changed by this awareness slice."""

    x: int
    y: int
    area: int
    direction: int
    actor_class: int = CLASS_GUARD
    flags: int = FLAG_SHOOTABLE
    temp2: int = 0
    state: str = "patrol"
    ticcount: int = 0
    distance: int = TILE_GLOBAL
    speed: int = 512
    tile_x: int = 0
    tile_y: int = 0


def _check_reachability(reachable: Sequence[int]) -> None:
    if len(reachable) != NUM_AREAS:
        raise AwarenessContractError(
            f"reachability table must contain {NUM_AREAS} bytes"
        )


def area_eligible(area: int, reachable: Sequence[int]) -> bool:
    """Return whether a validated actor area is connected to the player."""

    _check_reachability(reachable)
    return 0 <= area < NUM_AREAS and bool(reachable[area])


def close_range_automatic(actor: Actor, player: Player) -> bool:
    """Apply the original strict full-16.16 1.5-tile proximity square."""

    return (
        abs(player.x - actor.x) < MIN_SIGHT
        and abs(player.y - actor.y) < MIN_SIGHT
    )


def facing_accepts(direction: int, dx: int, dy: int) -> bool:
    """Apply the current eight-direction forward-half-plane contract.

    ``dx`` and ``dy`` are actor-to-player deltas after 8.8 quantization.
    ``nodir`` accepts every bearing, matching the production sight routine.
    """

    if direction == DIR_EAST:
        return dx >= 0
    if direction == DIR_NORTHEAST:
        return dx - dy >= 0
    if direction == DIR_NORTH:
        return dy <= 0
    if direction == DIR_NORTHWEST:
        return dx + dy <= 0
    if direction == DIR_WEST:
        return dx <= 0
    if direction == DIR_SOUTHWEST:
        return dy - dx >= 0
    if direction == DIR_SOUTH:
        return dy >= 0
    if direction == DIR_SOUTHEAST:
        return dx + dy >= 0
    return True


def visual_sight(
    actor: Actor,
    player: Player,
    reachable: Sequence[int],
    line_of_sight: LineOfSight,
) -> bool:
    """Return the visual/proximity result without noise wake-up semantics.

    Gates are deliberately ordered like the production sight contract: area,
    exact close range, 8.8 facing, then the replaceable wall/door trace.
    """

    if not area_eligible(actor.area, reachable):
        return False
    if close_range_automatic(actor, player):
        return True

    dx = (player.x >> 8) - (actor.x >> 8)
    dy = (player.y >> 8) - (actor.y >> 8)
    if not facing_accepts(actor.direction, dx, dy):
        return False
    return bool(line_of_sight(actor, player))


def reaction_delay(actor_class: int, rng: ByteRng) -> int:
    """Seed the original class-specific detection delay in 70-Hz tics."""

    if actor_class == CLASS_OFFICER:
        return 2
    try:
        divisor = RANDOM_DELAY_DIVISOR_BY_CLASS[actor_class]
    except KeyError as exc:
        raise AwarenessContractError(
            f"unsupported awareness actor class {actor_class}"
        ) from exc
    return 1 + rng.next_byte() // divisor


def activate_without_chase_movement(actor: Actor) -> None:
    """Apply FirstSighting's durable ordinary-enemy state changes only."""

    try:
        chase_state = CHASE_STATE_BY_CLASS[actor.actor_class]
        speed_multiplier = SPEED_MULTIPLIER_BY_CLASS[actor.actor_class]
    except KeyError as exc:
        raise AwarenessContractError(
            f"unsupported awareness actor class {actor.actor_class}"
        ) from exc

    actor.state = chase_state
    actor.ticcount = CHASE_TICS
    actor.speed *= speed_multiplier
    if actor.distance < 0:
        actor.distance = 0
    actor.flags |= FLAG_ATTACKMODE | FLAG_FIRSTATTACK


def awareness_step(
    actor: Actor,
    *,
    player: Player,
    reachable: Sequence[int],
    made_noise: bool,
    original_tics: int,
    rng: ByteRng,
    line_of_sight: LineOfSight,
) -> AwarenessEvent:
    """Advance one non-chasing actor's detection state.

    Ordinary noise starts a non-ambush actor's reaction delay anywhere in a
    connected area and does not invoke the line trace.  Ambush actors ignore
    noise and require the visual predicate.  Once a delay starts, it counts
    down before all area/sight tests, just as in the original, so a later door
    closure cannot cancel an already-heard or already-seen reaction.

    Activation updates flags, state, state tics, speed, and a negative door
    wait, but never moves or turns the actor.  Chase movement is intentionally
    outside this slice.
    """

    if not 0 <= original_tics <= 0x7FFF:
        raise AwarenessContractError(f"invalid original tic delta {original_tics}")
    if actor.flags & FLAG_ATTACKMODE:
        raise AwarenessContractError("attack-mode actor called awareness_step")

    if actor.temp2:
        actor.temp2 -= original_tics
        if actor.temp2 > 0:
            return AwarenessEvent.DELAY_WAITING
        actor.temp2 = 0
        activate_without_chase_movement(actor)
        return AwarenessEvent.ACTIVATED

    if not area_eligible(actor.area, reachable):
        return AwarenessEvent.UNAWARE

    if actor.flags & FLAG_AMBUSH:
        if not visual_sight(actor, player, reachable, line_of_sight):
            return AwarenessEvent.UNAWARE
        # The ambush bit clears at first visual acquisition, not after the
        # reaction delay expires.  The pending delay then needs no retrace.
        actor.flags &= ~FLAG_AMBUSH
    elif not made_noise:
        if not visual_sight(actor, player, reachable, line_of_sight):
            return AwarenessEvent.UNAWARE
    # A connected, ordinary noise wake-up deliberately skips visual_sight.

    actor.temp2 = reaction_delay(actor.actor_class, rng)
    return AwarenessEvent.DELAY_STARTED
