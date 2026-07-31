#!/usr/bin/env python3
"""Independent host specification for ordinary Wolf3D enemy combat.

This module owns the D2.2 boundary after chase has selected an attack.  It
models the original guard/officer/mutant/SS shoot animations, the dog jump
animation, ``T_Shoot``, ``T_Bite``, and the relevant ``TakeDamage`` effects.
It also specifies two port-owned producer contracts needed by ``T_Shoot``:

* the fixed-step player's original-style ``thrustspeed`` signal; and
* a synchronous CPU projection predicate replacing renderer-latched
  ``FL_VISABLE`` on a write-only VDP.

The implementation intentionally uses ordinary Python data and callbacks,
not an emulation of eZ80 registers or production control flow.  It therefore
serves as an independent source for directed assembly vectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
import math
from typing import Callable, Protocol, Sequence


NUM_AREAS = 37
TILE_GLOBAL = 1 << 16
RUN_SPEED = 6000
PLAYER_MOTION_STEP = 0x1000

CONTROL_W = 0x01
CONTROL_S = 0x02
CONTROL_A = 0x04
CONTROL_D = 0x08
CONTROL_LEFT = 0x10
CONTROL_RIGHT = 0x20
CONTROL_USE = 0x40
CONTROL_TRANSLATION_MASK = CONTROL_W | CONTROL_S | CONTROL_A | CONTROL_D

CLASS_GUARD = 3
CLASS_OFFICER = 4
CLASS_SS = 5
CLASS_DOG = 6
CLASS_MUTANT = 11
ORDINARY_SHOOTERS = frozenset(
    (CLASS_GUARD, CLASS_OFFICER, CLASS_SS, CLASS_MUTANT)
)

HUD_DIRTY_HEALTH = 0x01

# Stable ids already allocated by the awareness/chase layers.
STATE_GRD_CHASE1 = 47
STATE_DOG_CHASE1 = 48
STATE_OFC_CHASE1 = 49
STATE_MUT_CHASE1 = 50
STATE_SS_CHASE1 = 51

STATE_GRD_SHOOT1 = 77
STATE_GRD_SHOOT2 = 78
STATE_GRD_SHOOT3 = 79
STATE_DOG_JUMP1 = 80
STATE_DOG_JUMP2 = 81
STATE_DOG_JUMP3 = 82
STATE_DOG_JUMP4 = 83
STATE_DOG_JUMP5 = 84
STATE_OFC_SHOOT1 = 85
STATE_OFC_SHOOT2 = 86
STATE_OFC_SHOOT3 = 87
STATE_MUT_SHOOT1 = 88
STATE_MUT_SHOOT2 = 89
STATE_MUT_SHOOT3 = 90
STATE_MUT_SHOOT4 = 91
STATE_SS_SHOOT1 = 92
STATE_SS_SHOOT2 = 93
STATE_SS_SHOOT3 = 94
STATE_SS_SHOOT4 = 95
STATE_SS_SHOOT5 = 96
STATE_SS_SHOOT6 = 97
STATE_SS_SHOOT7 = 98
STATE_SS_SHOOT8 = 99
STATE_SS_SHOOT9 = 100

ACTION_NONE = 0
ACTION_SHOOT = 1
ACTION_BITE = 2

# CPU visibility replacement.  Coordinates are first reduced from signed
# 16.16 to signed 8.8.  The constants are correspondingly reduced versions of
# FOCALLENGTH 0x5700, ACTORSIZE 0x4000, and MINDIST 0x5800, plus the current
# 256-wide port projection (center x 127, scale 87).
PROJECTION_Q = 1 << 12
PROJECTION_FOCAL_MINUS_ACTOR = 0x17
PROJECTION_MIN_DISTANCE = 0x58
PROJECTION_CENTER_X = 127
PROJECTION_SCALE = 87
PROJECTION_LEFT = 0
PROJECTION_RIGHT = 255


class CombatContractError(ValueError):
    """Raised when a fixture violates the combat layer's input contract."""


class Difficulty(IntEnum):
    BABY = 0
    EASY = 1
    MEDIUM = 2
    HARD = 3


class Sound(IntEnum):
    NONE = 0
    NAZI_FIRE = 1
    SS_FIRE = 2
    DOG_ATTACK = 3


@dataclass(frozen=True)
class State:
    shape: int
    rotations: int
    tictime: int
    action: int
    next_state: int


ATTACK_STATES: dict[int, State] = {
    STATE_GRD_SHOOT1: State(96, 0, 20, ACTION_NONE, STATE_GRD_SHOOT2),
    STATE_GRD_SHOOT2: State(97, 0, 20, ACTION_SHOOT, STATE_GRD_SHOOT3),
    STATE_GRD_SHOOT3: State(98, 0, 20, ACTION_NONE, STATE_GRD_CHASE1),
    STATE_DOG_JUMP1: State(135, 0, 10, ACTION_NONE, STATE_DOG_JUMP2),
    STATE_DOG_JUMP2: State(136, 0, 10, ACTION_BITE, STATE_DOG_JUMP3),
    STATE_DOG_JUMP3: State(137, 0, 10, ACTION_NONE, STATE_DOG_JUMP4),
    STATE_DOG_JUMP4: State(135, 0, 10, ACTION_NONE, STATE_DOG_JUMP5),
    STATE_DOG_JUMP5: State(99, 0, 10, ACTION_NONE, STATE_DOG_CHASE1),
    STATE_OFC_SHOOT1: State(285, 0, 6, ACTION_NONE, STATE_OFC_SHOOT2),
    STATE_OFC_SHOOT2: State(286, 0, 20, ACTION_SHOOT, STATE_OFC_SHOOT3),
    STATE_OFC_SHOOT3: State(287, 0, 10, ACTION_NONE, STATE_OFC_CHASE1),
    STATE_MUT_SHOOT1: State(234, 0, 6, ACTION_SHOOT, STATE_MUT_SHOOT2),
    STATE_MUT_SHOOT2: State(235, 0, 20, ACTION_NONE, STATE_MUT_SHOOT3),
    STATE_MUT_SHOOT3: State(236, 0, 10, ACTION_SHOOT, STATE_MUT_SHOOT4),
    STATE_MUT_SHOOT4: State(237, 0, 20, ACTION_NONE, STATE_MUT_CHASE1),
    STATE_SS_SHOOT1: State(184, 0, 20, ACTION_NONE, STATE_SS_SHOOT2),
    STATE_SS_SHOOT2: State(185, 0, 20, ACTION_SHOOT, STATE_SS_SHOOT3),
    STATE_SS_SHOOT3: State(186, 0, 10, ACTION_NONE, STATE_SS_SHOOT4),
    STATE_SS_SHOOT4: State(185, 0, 10, ACTION_SHOOT, STATE_SS_SHOOT5),
    STATE_SS_SHOOT5: State(186, 0, 10, ACTION_NONE, STATE_SS_SHOOT6),
    STATE_SS_SHOOT6: State(185, 0, 10, ACTION_SHOOT, STATE_SS_SHOOT7),
    STATE_SS_SHOOT7: State(186, 0, 10, ACTION_NONE, STATE_SS_SHOOT8),
    STATE_SS_SHOOT8: State(185, 0, 10, ACTION_SHOOT, STATE_SS_SHOOT9),
    STATE_SS_SHOOT9: State(186, 0, 10, ACTION_NONE, STATE_SS_CHASE1),
}

FIRST_ATTACK_STATE = {
    CLASS_GUARD: STATE_GRD_SHOOT1,
    CLASS_OFFICER: STATE_OFC_SHOOT1,
    CLASS_MUTANT: STATE_MUT_SHOOT1,
    CLASS_SS: STATE_SS_SHOOT1,
    CLASS_DOG: STATE_DOG_JUMP1,
}

TERMINAL_CHASE_STATE = {
    CLASS_GUARD: STATE_GRD_CHASE1,
    CLASS_OFFICER: STATE_OFC_CHASE1,
    CLASS_MUTANT: STATE_MUT_CHASE1,
    CLASS_SS: STATE_SS_CHASE1,
    CLASS_DOG: STATE_DOG_CHASE1,
}

# All five destination chase1 states have a ten-tic duration.
TERMINAL_STATE_TICTIME = {state_id: 10 for state_id in TERMINAL_CHASE_STATE.values()}


class ByteRng(Protocol):
    def next_byte(self) -> int:
        """Return one deterministic unsigned byte."""


LineOfSight = Callable[["Actor", "Player"], bool]
ActionHandler = Callable[[int, int], None]


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
            raise CombatContractError("combat RNG exhausted")
        value = self.values[self.index]
        self.index += 1
        if not 0 <= value <= 0xFF:
            raise CombatContractError(f"combat RNG returned {value!r}")
        self.history.append(value)
        return value


@dataclass
class Actor:
    actor_id: int
    actor_class: int
    x: int
    y: int
    tile_x: int
    tile_y: int
    area: int = 0


@dataclass
class Player:
    x: int
    y: int
    tile_x: int
    tile_y: int
    heading: int = 0
    thrustspeed: int = 0
    health: int = 100
    difficulty: Difficulty = Difficulty.MEDIUM
    god_mode: bool = False
    victory: bool = False
    dead: bool = False
    last_attacker_id: int | None = None
    killer_actor_id: int | None = None
    got_gat_gun: bool = False
    hud_dirty: int = 0
    damage_flashes: list[int] = field(default_factory=list)
    health_redraws: int = 0
    face_redraws: int = 0


@dataclass
class AttackRuntime:
    actor_class: int
    state_id: int
    ticcount: int


@dataclass(frozen=True)
class AttackAdvance:
    actions: tuple[tuple[int, int], ...]
    transitions: tuple[tuple[int, int], ...]
    entered_chase: bool


@dataclass(frozen=True)
class Projection:
    relative_x_q8: int
    relative_y_q8: int
    motion_x_q12: int
    motion_y_q12: int
    forward_q8: int
    lateral_q8: int
    nx_q8: int
    screen_x: int | None
    visible: bool


@dataclass(frozen=True)
class DamageOutcome:
    raw_points: int
    reduced_points: int
    health_before: int
    health_after: int
    applied_damage: int
    killed: bool
    victory_suppressed: bool


@dataclass(frozen=True)
class ShotOutcome:
    eligible_area: bool
    line_clear: bool | None
    visible: bool | None
    raw_distance: int | None
    effective_distance: int | None
    hitchance: int | None
    hit_roll: int | None
    hit: bool
    damage_roll: int | None
    raw_damage: int | None
    damage: DamageOutcome | None
    sound: Sound
    events: tuple[str, ...]


@dataclass(frozen=True)
class BiteOutcome:
    in_range: bool
    hit_roll: int | None
    hit: bool
    damage_roll: int | None
    raw_damage: int | None
    damage: DamageOutcome | None
    sound: Sound
    events: tuple[str, ...]


def fixed(tile: int, fraction: int = 0x8000) -> int:
    return tile * TILE_GLOBAL + fraction


def _trunc_div(numerator: int, denominator: int) -> int:
    """C-style signed integer division, truncating toward zero."""

    if denominator == 0:
        raise ZeroDivisionError
    quotient = abs(numerator) // abs(denominator)
    return -quotient if (numerator < 0) != (denominator < 0) else quotient


def _round_away(value: float) -> int:
    """Round a generated trigonometric table entry to its nearest integer."""

    if value >= 0:
        return math.floor(value + 0.5)
    return math.ceil(value - 0.5)


def motion_basis_q12(heading: int) -> tuple[int, int]:
    """Return the current motion-table basis: east=0, north=90, +Y south."""

    if not isinstance(heading, int):
        raise CombatContractError("heading must be an integer degree value")
    if not 0 <= heading < 360:
        raise CombatContractError("heading must already be normalized to 0..359")
    angle = math.radians(heading)
    return (
        _round_away(math.cos(angle) * PROJECTION_Q),
        _round_away(-math.sin(angle) * PROJECTION_Q),
    )


def _mul_q12_toward_zero(value: int, fraction: int) -> int:
    # Original FixedByFrac truncates each signed-magnitude product before the
    # transformed components are added.  Preserve that ordering here.
    return _trunc_div(value * fraction, PROJECTION_Q)


def cpu_visibility_projection(actor: Actor, player: Player) -> Projection:
    """Project one actor center with the deterministic CPU visibility rule.

    Full position differences are arithmetically reduced to signed 8.8.  The
    360-degree Q12 motion basis then reproduces TransformActor's forward and
    lateral products.  The result is visible only after the actor-size/focal
    offset clears the near plane and its projected center lies in inclusive
    screen columns 0..255.  Wall/door line of sight is deliberately separate;
    ``shoot`` evaluates that earlier, exactly like the original action.
    """

    relative_x = (actor.x - player.x) >> 8
    relative_y = (actor.y - player.y) >> 8
    for name, value in (("relative x", relative_x), ("relative y", relative_y)):
        if not -0x8000 <= value <= 0x7FFF:
            raise CombatContractError(f"{name} is outside signed 8.8 map range")

    motion_x, motion_y = motion_basis_q12(player.heading)
    forward = (
        _mul_q12_toward_zero(relative_x, motion_x)
        + _mul_q12_toward_zero(relative_y, motion_y)
    )
    lateral = (
        _mul_q12_toward_zero(relative_x, -motion_y)
        + _mul_q12_toward_zero(relative_y, motion_x)
    )
    nx = forward + PROJECTION_FOCAL_MINUS_ACTOR
    if nx < PROJECTION_MIN_DISTANCE:
        return Projection(
            relative_x,
            relative_y,
            motion_x,
            motion_y,
            forward,
            lateral,
            nx,
            None,
            False,
        )

    screen_x = PROJECTION_CENTER_X + _trunc_div(
        lateral * PROJECTION_SCALE, nx
    )
    return Projection(
        relative_x,
        relative_y,
        motion_x,
        motion_y,
        forward,
        lateral,
        nx,
        screen_x,
        PROJECTION_LEFT <= screen_x <= PROJECTION_RIGHT,
    )


def produce_thrustspeed(controls: int) -> int:
    """Publish the fixed-step input signal consumed by ``T_Shoot``.

    Opposing keys cancel on each signed control axis.  One unopposed W/S axis
    or A/D axis contributes the current 0x1000 requested motion before
    collision; a diagonal contributes 0x2000.  Rotation/use do not contribute.
    Consequently the only legal outputs are 0, 4096, and 8192, and the
    original RUNSPEED=6000 comparison classifies only a diagonal as running.
    """

    if not isinstance(controls, int) or not 0 <= controls <= 0xFF:
        raise CombatContractError("controls must be one byte")
    speed = 0
    forward = controls & (CONTROL_W | CONTROL_S)
    strafe = controls & (CONTROL_A | CONTROL_D)
    if forward in (CONTROL_W, CONTROL_S):
        speed += PLAYER_MOTION_STEP
    if strafe in (CONTROL_A, CONTROL_D):
        speed += PLAYER_MOTION_STEP
    return speed


def start_attack(actor_class: int) -> AttackRuntime:
    """Apply NewState's full-duration initialization for one attack chain."""

    try:
        state_id = FIRST_ATTACK_STATE[actor_class]
    except KeyError as exc:
        raise CombatContractError(f"class {actor_class} has no ordinary attack") from exc
    return AttackRuntime(actor_class, state_id, ATTACK_STATES[state_id].tictime)


def advance_attack(
    runtime: AttackRuntime,
    tics: int,
    action_handler: ActionHandler | None = None,
) -> AttackAdvance:
    """Advance one attack chain with DoActor's action-before-NEXT ordering.

    The function stops as soon as the chain enters its destination chase1
    state.  Normal 2/2/3 fixed updates cannot overshoot through that ten-tic
    destination.  A synthetic call that would do so is rejected because the
    surrounding chase graph, think calls, and movement are outside this oracle.
    """

    if not isinstance(tics, int) or tics < 0:
        raise CombatContractError("tics must be a non-negative integer")
    if runtime.state_id not in ATTACK_STATES:
        raise CombatContractError("runtime is not in an ordinary attack state")
    if runtime.ticcount <= 0:
        raise CombatContractError("attack runtime requires a positive ticcount")
    if TERMINAL_CHASE_STATE.get(runtime.actor_class) is None:
        raise CombatContractError(f"class {runtime.actor_class} has no terminal state")

    runtime.ticcount -= tics
    actions: list[tuple[int, int]] = []
    transitions: list[tuple[int, int]] = []
    terminal = TERMINAL_CHASE_STATE[runtime.actor_class]

    while runtime.ticcount <= 0:
        current_id = runtime.state_id
        current = ATTACK_STATES[current_id]
        if current.action != ACTION_NONE:
            actions.append((current.action, current_id))
            if action_handler is not None:
                # The original action observes the expiring state; NEXT is
                # installed only after the callback returns.
                action_handler(current.action, current_id)

        next_id = current.next_state
        transitions.append((current_id, next_id))
        runtime.state_id = next_id
        if next_id == terminal:
            runtime.ticcount += TERMINAL_STATE_TICTIME[next_id]
            if runtime.ticcount <= 0:
                raise CombatContractError(
                    "synthetic tics overshoot beyond the combat/chase seam"
                )
            return AttackAdvance(tuple(actions), tuple(transitions), True)

        try:
            runtime.ticcount += ATTACK_STATES[next_id].tictime
        except KeyError as exc:
            raise CombatContractError(f"attack chain escaped to state {next_id}") from exc

    return AttackAdvance(tuple(actions), tuple(transitions), False)


def take_damage(points: int, player: Player, attacker_id: int) -> DamageOutcome:
    """Apply the source-relevant effects of the original TakeDamage."""

    if not isinstance(points, int) or points < 0:
        raise CombatContractError("damage points must be a non-negative integer")
    if not 0 <= player.health <= 100:
        raise CombatContractError("player health must be in 0..100")

    before = player.health
    player.last_attacker_id = attacker_id
    if player.victory:
        return DamageOutcome(points, points, before, before, 0, False, True)

    reduced = points >> 2 if player.difficulty == Difficulty.BABY else points
    if not player.god_mode:
        player.health -= reduced

    killed = player.health <= 0
    if killed:
        player.health = 0
        player.dead = True
        player.killer_actor_id = attacker_id

    # StartDamageFlash, gotgatgun=0, DrawHealth, DrawFace all happen even when
    # reduced damage is zero or god mode prevented health loss.
    player.damage_flashes.append(reduced)
    player.got_gat_gun = False
    player.hud_dirty |= HUD_DIRTY_HEALTH
    player.health_redraws += 1
    player.face_redraws += 1
    return DamageOutcome(
        points,
        reduced,
        before,
        player.health,
        before - player.health,
        killed,
        False,
    )


def _area_eligible(area: int, reachable: Sequence[int]) -> bool:
    if len(reachable) != NUM_AREAS:
        raise CombatContractError(
            f"reachability table must contain {NUM_AREAS} bytes"
        )
    # The DOS source indexes without validation.  The port treats malformed
    # actor state as corrupt rather than aliasing or indexing past the table.
    if not 0 <= area < NUM_AREAS:
        raise CombatContractError(f"actor area {area} is outside 0..{NUM_AREAS - 1}")
    return bool(reachable[area])


def shoot(
    actor: Actor,
    player: Player,
    reachable: Sequence[int],
    line_of_sight: LineOfSight,
    rng: ByteRng,
) -> ShotOutcome:
    """Execute one source-ordered ordinary ``T_Shoot`` muzzle action."""

    if actor.actor_class not in ORDINARY_SHOOTERS:
        raise CombatContractError(f"class {actor.actor_class} is not an ordinary shooter")

    events: list[str] = []
    eligible = _area_eligible(actor.area, reachable)
    if not eligible:
        return ShotOutcome(
            False, None, None, None, None, None, None, False,
            None, None, None, Sound.NONE, tuple(events),
        )

    events.append("check_line")
    line_clear = bool(line_of_sight(actor, player))
    if not line_clear:
        return ShotOutcome(
            True, False, None, None, None, None, None, False,
            None, None, None, Sound.NONE, tuple(events),
        )

    raw_distance = max(
        abs(actor.tile_x - player.tile_x),
        abs(actor.tile_y - player.tile_y),
    )
    effective_distance = (
        (raw_distance * 2) // 3
        if actor.actor_class == CLASS_SS
        else raw_distance
    )
    events.append("project_visibility")
    visible = cpu_visibility_projection(actor, player).visible

    moving = player.thrustspeed >= RUN_SPEED
    base = 160 if moving else 256
    slope = 16 if visible else 8
    hitchance = base - effective_distance * slope

    events.append("hit_rng")
    hit_roll = rng.next_byte()
    hit = hit_roll < hitchance
    damage_roll: int | None = None
    raw_damage: int | None = None
    damage: DamageOutcome | None = None
    if hit:
        events.append("damage_rng")
        damage_roll = rng.next_byte()
        if effective_distance < 2:
            raw_damage = damage_roll >> 2
        elif effective_distance < 4:
            raw_damage = damage_roll >> 3
        else:
            raw_damage = damage_roll >> 4
        events.append("take_damage")
        damage = take_damage(raw_damage, player, actor.actor_id)

    sound = Sound.SS_FIRE if actor.actor_class == CLASS_SS else Sound.NAZI_FIRE
    events.append("ss_fire" if sound == Sound.SS_FIRE else "nazi_fire")
    return ShotOutcome(
        True,
        True,
        visible,
        raw_distance,
        effective_distance,
        hitchance,
        hit_roll,
        hit,
        damage_roll,
        raw_damage,
        damage,
        sound,
        tuple(events),
    )


def bite(actor: Actor, player: Player, rng: ByteRng) -> BiteOutcome:
    """Execute one source-ordered dog ``T_Bite`` action."""

    if actor.actor_class != CLASS_DOG:
        raise CombatContractError(f"class {actor.actor_class} is not a dog")

    events = ["dog_attack"]
    in_range = (
        abs(player.x - actor.x) <= 2 * TILE_GLOBAL
        and abs(player.y - actor.y) <= 2 * TILE_GLOBAL
    )
    if not in_range:
        return BiteOutcome(
            False, None, False, None, None, None,
            Sound.DOG_ATTACK, tuple(events),
        )

    events.append("hit_rng")
    hit_roll = rng.next_byte()
    if hit_roll >= 180:
        return BiteOutcome(
            True, hit_roll, False, None, None, None,
            Sound.DOG_ATTACK, tuple(events),
        )

    events.append("damage_rng")
    damage_roll = rng.next_byte()
    raw_damage = damage_roll >> 4
    events.append("take_damage")
    damage = take_damage(raw_damage, player, actor.actor_id)
    return BiteOutcome(
        True,
        hit_roll,
        True,
        damage_roll,
        raw_damage,
        damage,
        Sound.DOG_ATTACK,
        tuple(events),
    )
