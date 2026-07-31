#!/usr/bin/env python3
"""Independent host specification for ordinary Wolfenstein player combat.

The model is intentionally expressed as Python domain objects, not as eZ80
registers, byte offsets, or a transcription of the production assembly's
control flow.  Its source contracts are the bundled shareware sources:

* ``WL_AGENT.C``: ``attackinfo``, ``CheckWeaponChange``, ``Cmd_Fire``,
  ``KnifeAttack``, ``GunAttack``, ``T_Attack``, and ``GivePoints``;
* ``WL_STATE.C``: ``DamageActor`` and ``KillActor``;
* ``WL_ACT1.C``: ``PlaceItemType``; and
* ``WL_ACT2.C``: ordinary pain and death state records.

Only the five ordinary classes implemented by the current port are in scope.
Bosses, projectiles, victory behavior, audio playback, and menus are not.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum, IntEnum
from typing import Callable, Iterable, Sequence


EXTRA_POINTS = 40_000
MAX_LIVES = 9
MAX_STATICS = 400
SHOOT_DELTA = 25
KNIFE_RANGE_Q8 = 0x180

ITEM_CLIP2 = "bo_clip2"
ITEM_MACHINEGUN = "bo_machinegun"
DROP_SHAPES = {
    ITEM_CLIP2: 28,          # SPR_STAT_26
    ITEM_MACHINEGUN: 29,    # SPR_STAT_27
}


class CombatContractError(ValueError):
    """Raised when a caller supplies state outside the ordinary-combat ABI."""


class Weapon(IntEnum):
    KNIFE = 0
    PISTOL = 1
    MACHINEGUN = 2
    CHAINGUN = 3


class AttackAction(IntEnum):
    NONE = 0
    GUN = 1
    KNIFE = 2
    REPEAT = 3
    CHAIN = 4
    FINISH = -1


@dataclass(frozen=True)
class AttackRecord:
    tics: int
    action: AttackAction
    frame: int


# WL_AGENT.C attackinfo[4][14].  Only four entries in each partially-filled C
# row are reachable; the remaining zero-filled records are not attack frames.
ATTACK_INFO: dict[Weapon, tuple[AttackRecord, ...]] = {
    Weapon.KNIFE: (
        AttackRecord(6, AttackAction.NONE, 1),
        AttackRecord(6, AttackAction.KNIFE, 2),
        AttackRecord(6, AttackAction.NONE, 3),
        AttackRecord(6, AttackAction.FINISH, 4),
    ),
    Weapon.PISTOL: (
        AttackRecord(6, AttackAction.NONE, 1),
        AttackRecord(6, AttackAction.GUN, 2),
        AttackRecord(6, AttackAction.NONE, 3),
        AttackRecord(6, AttackAction.FINISH, 4),
    ),
    Weapon.MACHINEGUN: (
        AttackRecord(6, AttackAction.NONE, 1),
        AttackRecord(6, AttackAction.GUN, 2),
        AttackRecord(6, AttackAction.REPEAT, 3),
        AttackRecord(6, AttackAction.FINISH, 4),
    ),
    Weapon.CHAINGUN: (
        AttackRecord(6, AttackAction.NONE, 1),
        AttackRecord(6, AttackAction.GUN, 2),
        AttackRecord(6, AttackAction.CHAIN, 3),
        AttackRecord(6, AttackAction.FINISH, 4),
    ),
}

WEAPON_SHAPE_BASE = {
    Weapon.KNIFE: 416,
    Weapon.PISTOL: 421,
    Weapon.MACHINEGUN: 426,
    Weapon.CHAINGUN: 431,
}


class ActorClass(Enum):
    GUARD = "guardobj"
    OFFICER = "officerobj"
    MUTANT = "mutantobj"
    SS = "ssobj"
    DOG = "dogobj"


class DamageResult(Enum):
    PAIN = "pain"
    KILLED = "killed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class InjuryState:
    rotations: int
    shape: str
    tics: int
    action: str | None
    next_state: str


# Exact ordinary records from WL_ACT2.C.  Symbolic shapes and state names keep
# this host contract independent of the port's compact numeric state ids.
INJURY_STATES: dict[str, InjuryState] = {
    "s_grdpain": InjuryState(2, "SPR_GRD_PAIN_1", 10, None, "s_grdchase1"),
    "s_grdpain1": InjuryState(2, "SPR_GRD_PAIN_2", 10, None, "s_grdchase1"),
    "s_grddie1": InjuryState(0, "SPR_GRD_DIE_1", 15, "death_scream", "s_grddie2"),
    "s_grddie2": InjuryState(0, "SPR_GRD_DIE_2", 15, None, "s_grddie3"),
    "s_grddie3": InjuryState(0, "SPR_GRD_DIE_3", 15, None, "s_grddie4"),
    "s_grddie4": InjuryState(0, "SPR_GRD_DEAD", 0, None, "s_grddie4"),

    "s_dogdie1": InjuryState(0, "SPR_DOG_DIE_1", 15, "death_scream", "s_dogdie2"),
    "s_dogdie2": InjuryState(0, "SPR_DOG_DIE_2", 15, None, "s_dogdie3"),
    "s_dogdie3": InjuryState(0, "SPR_DOG_DIE_3", 15, None, "s_dogdead"),
    "s_dogdead": InjuryState(0, "SPR_DOG_DEAD", 15, None, "s_dogdead"),

    "s_ofcpain": InjuryState(2, "SPR_OFC_PAIN_1", 10, None, "s_ofcchase1"),
    "s_ofcpain1": InjuryState(2, "SPR_OFC_PAIN_2", 10, None, "s_ofcchase1"),
    "s_ofcdie1": InjuryState(0, "SPR_OFC_DIE_1", 11, "death_scream", "s_ofcdie2"),
    "s_ofcdie2": InjuryState(0, "SPR_OFC_DIE_2", 11, None, "s_ofcdie3"),
    "s_ofcdie3": InjuryState(0, "SPR_OFC_DIE_3", 11, None, "s_ofcdie4"),
    "s_ofcdie4": InjuryState(0, "SPR_OFC_DIE_4", 11, None, "s_ofcdie5"),
    "s_ofcdie5": InjuryState(0, "SPR_OFC_DEAD", 0, None, "s_ofcdie5"),

    "s_mutpain": InjuryState(2, "SPR_MUT_PAIN_1", 10, None, "s_mutchase1"),
    "s_mutpain1": InjuryState(2, "SPR_MUT_PAIN_2", 10, None, "s_mutchase1"),
    "s_mutdie1": InjuryState(0, "SPR_MUT_DIE_1", 7, "death_scream", "s_mutdie2"),
    "s_mutdie2": InjuryState(0, "SPR_MUT_DIE_2", 7, None, "s_mutdie3"),
    "s_mutdie3": InjuryState(0, "SPR_MUT_DIE_3", 7, None, "s_mutdie4"),
    "s_mutdie4": InjuryState(0, "SPR_MUT_DIE_4", 7, None, "s_mutdie5"),
    "s_mutdie5": InjuryState(0, "SPR_MUT_DEAD", 0, None, "s_mutdie5"),

    "s_sspain": InjuryState(2, "SPR_SS_PAIN_1", 10, None, "s_sschase1"),
    "s_sspain1": InjuryState(2, "SPR_SS_PAIN_2", 10, None, "s_sschase1"),
    "s_ssdie1": InjuryState(0, "SPR_SS_DIE_1", 15, "death_scream", "s_ssdie2"),
    "s_ssdie2": InjuryState(0, "SPR_SS_DIE_2", 15, None, "s_ssdie3"),
    "s_ssdie3": InjuryState(0, "SPR_SS_DIE_3", 15, None, "s_ssdie4"),
    "s_ssdie4": InjuryState(0, "SPR_SS_DEAD", 0, None, "s_ssdie4"),
}

PAIN_STATES = {
    ActorClass.GUARD: ("s_grdpain", "s_grdpain1"),
    ActorClass.OFFICER: ("s_ofcpain", "s_ofcpain1"),
    ActorClass.MUTANT: ("s_mutpain", "s_mutpain1"),
    ActorClass.SS: ("s_sspain", "s_sspain1"),
}

CHASE_STATES = {
    ActorClass.GUARD: "s_grdchase1",
    ActorClass.OFFICER: "s_ofcchase1",
    ActorClass.MUTANT: "s_mutchase1",
    ActorClass.SS: "s_sschase1",
    ActorClass.DOG: "s_dogchase1",
}

DEATH_STATES = {
    ActorClass.GUARD: "s_grddie1",
    ActorClass.OFFICER: "s_ofcdie1",
    ActorClass.MUTANT: "s_mutdie1",
    ActorClass.SS: "s_ssdie1",
    ActorClass.DOG: "s_dogdie1",
}

CLASS_SCORES = {
    ActorClass.GUARD: 100,
    ActorClass.OFFICER: 400,
    ActorClass.MUTANT: 700,
    ActorClass.SS: 500,
    ActorClass.DOG: 200,
}


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
        if not 0 <= value <= 0xFF:
            raise CombatContractError(f"RNG byte is outside 0..255: {value!r}")
        self.index += 1
        self.history.append(value)
        return value


@dataclass
class Player:
    ammo: int = 8
    weapon: Weapon = Weapon.PISTOL
    chosen_weapon: Weapon = Weapon.PISTOL
    best_weapon: Weapon = Weapon.PISTOL
    score: int = 0
    next_extra: int = EXTRA_POINTS
    lives: int = 3
    kill_count: int = 0
    made_noise: bool = False
    tile_x: int = 0
    tile_y: int = 0


@dataclass
class Actor:
    actor_id: int
    actor_class: ActorClass
    hitpoints: int
    x: int = 0
    y: int = 0
    tile_x: int = 0
    tile_y: int = 0
    shootable: bool = True
    attack_mode: bool = True
    occupied: bool = True
    nonmark: bool = False
    state: str = "s_grdchase1"
    ticcount: int = 10
    first_sightings: int = 0
    death_screams: int = 0
    visible: bool = True
    center_delta: int = 0
    depth_q8: int = 0x200
    line_clear: bool = True


LineOfSight = Callable[[Actor], bool]


@dataclass
class StaticSlot:
    tile_x: int
    tile_y: int
    shapenum: int
    item: str
    bonus: bool = True
    dirty: bool = False


@dataclass(frozen=True)
class Placement:
    index: int
    reused: bool


class StaticPool:
    """Original high-water static list with stable index identities."""

    def __init__(self, seed: Iterable[StaticSlot] = (), capacity: int = MAX_STATICS):
        if capacity < 0:
            raise CombatContractError("static capacity must be non-negative")
        self.capacity = capacity
        self._seed = [replace(slot, dirty=False) for slot in seed]
        if len(self._seed) > capacity:
            raise CombatContractError("static seed exceeds capacity")
        self.slots = [replace(slot) for slot in self._seed]

    def place_item(self, item: str, tile_x: int, tile_y: int) -> Placement | None:
        try:
            shape = DROP_SHAPES[item]
        except KeyError:
            return None

        for index, slot in enumerate(self.slots):
            if slot.shapenum == -1:
                self.slots[index] = StaticSlot(
                    tile_x, tile_y, shape, item, bonus=True, dirty=True
                )
                return Placement(index, True)

        if len(self.slots) >= self.capacity:
            return None
        index = len(self.slots)
        self.slots.append(StaticSlot(tile_x, tile_y, shape, item, True, True))
        return Placement(index, False)

    def collect(self, index: int, player: Player) -> bool:
        if not 0 <= index < len(self.slots):
            raise CombatContractError("static index is outside the high-water list")
        slot = self.slots[index]
        if slot.shapenum == -1 or not slot.bonus:
            return False

        if slot.item == ITEM_CLIP2:
            if player.ammo >= 99:
                return False
            give_ammo(player, 4, attack_frame=0)
        elif slot.item == ITEM_MACHINEGUN:
            give_weapon(player, Weapon.MACHINEGUN, attack_frame=0)
        else:
            raise CombatContractError(f"unsupported runtime drop {slot.item!r}")

        slot.shapenum = -1
        slot.dirty = True
        return True

    def reseed(self) -> None:
        """Model SetupGameLevel's attempt reset without touching textures."""

        self.slots = [replace(slot, dirty=False) for slot in self._seed]


def give_points(player: Player, points: int) -> None:
    if points < 0:
        raise CombatContractError("ordinary score increments cannot be negative")
    player.score += points
    while player.score >= player.next_extra:
        player.next_extra += EXTRA_POINTS
        if player.lives < MAX_LIVES:
            player.lives += 1


def give_ammo(player: Player, amount: int, *, attack_frame: int) -> None:
    """WL_AGENT.C GiveAmmo, including its attack-frame-zero restore guard."""

    if amount < 0:
        raise CombatContractError("ammo increment cannot be negative")
    was_empty = player.ammo == 0
    if was_empty and attack_frame == 0:
        player.weapon = player.chosen_weapon
    player.ammo = min(99, player.ammo + amount)


def give_weapon(player: Player, weapon: Weapon, *, attack_frame: int) -> None:
    """WL_AGENT.C GiveWeapon for ordinary machine-gun/chaingun pickups."""

    give_ammo(player, 6, attack_frame=attack_frame)
    if player.best_weapon < weapon:
        player.best_weapon = weapon
        player.weapon = weapon
        player.chosen_weapon = weapon


def _drop_for(actor_class: ActorClass, player: Player) -> str | None:
    if actor_class in (ActorClass.GUARD, ActorClass.OFFICER, ActorClass.MUTANT):
        return ITEM_CLIP2
    if actor_class == ActorClass.SS:
        return (
            ITEM_MACHINEGUN
            if player.best_weapon < Weapon.MACHINEGUN
            else ITEM_CLIP2
        )
    return None


@dataclass(frozen=True)
class DamageOutcome:
    result: DamageResult
    requested_damage: int
    applied_damage: int
    drop: Placement | None = None


def kill_actor(actor: Actor, player: Player, statics: StaticPool) -> DamageOutcome:
    """Apply the ordinary subset of WL_STATE.C KillActor exactly once."""

    if not actor.shootable:
        return DamageOutcome(DamageResult.REJECTED, 0, 0)

    actor.tile_x = actor.x >> 16
    actor.tile_y = actor.y >> 16
    actor.state = DEATH_STATES[actor.actor_class]
    actor.ticcount = INJURY_STATES[actor.state].tics
    actor.shootable = False
    actor.occupied = False
    actor.nonmark = True
    player.kill_count += 1
    give_points(player, CLASS_SCORES[actor.actor_class])

    item = _drop_for(actor.actor_class, player)
    drop = statics.place_item(item, actor.tile_x, actor.tile_y) if item else None
    return DamageOutcome(DamageResult.KILLED, 0, 0, drop)


def damage_actor(
    actor: Actor,
    damage: int,
    player: Player,
    statics: StaticPool,
) -> DamageOutcome:
    """Apply WL_STATE.C DamageActor for one ordinary actor."""

    if damage < 0:
        raise CombatContractError("damage cannot be negative")
    if not actor.shootable:
        return DamageOutcome(DamageResult.REJECTED, damage, 0)

    player.made_noise = True
    was_active = actor.attack_mode
    applied = damage if was_active else damage * 2
    actor.hitpoints -= applied
    if actor.hitpoints <= 0:
        outcome = kill_actor(actor, player, statics)
        return DamageOutcome(outcome.result, damage, applied, outcome.drop)

    if not was_active:
        actor.attack_mode = True
        actor.first_sightings += 1
        actor.state = CHASE_STATES[actor.actor_class]
        actor.ticcount = 10

    pain_pair = PAIN_STATES.get(actor.actor_class)
    if pain_pair is not None:
        # C chooses the first pain state for odd remaining HP and pain1 for even.
        actor.state = pain_pair[0] if actor.hitpoints & 1 else pain_pair[1]
        actor.ticcount = INJURY_STATES[actor.state].tics
    return DamageOutcome(DamageResult.PAIN, damage, applied)


@dataclass(frozen=True)
class StateAdvance:
    transitions: tuple[tuple[str, str], ...]
    actions: tuple[str, ...]


def advance_injury_state(actor: Actor, tics: int) -> StateAdvance:
    """Advance pain/death records with action-before-next source ordering."""

    if tics < 0:
        raise CombatContractError("state tics cannot be negative")
    if actor.state not in INJURY_STATES:
        return StateAdvance((), ())
    if INJURY_STATES[actor.state].tics == 0:
        return StateAdvance((), ())

    actor.ticcount -= tics
    transitions: list[tuple[str, str]] = []
    actions: list[str] = []
    while actor.ticcount <= 0:
        current_name = actor.state
        current = INJURY_STATES[current_name]
        if current.action:
            actions.append(current.action)
            if current.action == "death_scream":
                actor.death_screams += 1
        actor.state = current.next_state
        transitions.append((current_name, actor.state))

        following = INJURY_STATES.get(actor.state)
        if following is None:
            actor.ticcount += 10       # all ordinary chase1 states use 10 tics
            break
        if following.tics == 0:
            actor.ticcount = 0
            break
        actor.ticcount += following.tics
    return StateAdvance(tuple(transitions), tuple(actions))


def select_attack_target(
    actors: Iterable[Actor],
    line_of_sight: LineOfSight | None = None,
) -> Actor | None:
    """Choose the first nearest projected and CPU-line-clear target.

    ``visible`` represents the synchronous projection replacement for source
    ``viewx``/``transx``.  The source's renderer-owned ``FL_VISABLE`` also
    carried raycast occlusion.  The port policy replaces that unavailable bit
    by applying current ``CheckLine`` to every projected candidate.  This lets
    a farther clear target win over a nearer occluded one and prevents the
    knife from crossing opaque geometry.
    """

    closest: Actor | None = None
    best_depth: int | None = None
    for actor in actors:
        if not actor.shootable or not actor.visible:
            continue
        if abs(actor.center_delta) >= SHOOT_DELTA:
            continue
        if line_of_sight is not None and not line_of_sight(actor):
            continue
        if best_depth is None or actor.depth_q8 < best_depth:
            closest = actor
            best_depth = actor.depth_q8
    return closest


@dataclass(frozen=True)
class AttackOutcome:
    target_id: int | None
    hit: bool
    damage: int | None
    damage_result: DamageResult | None
    sound: str
    line_checked: bool


def knife_attack(
    actors: Iterable[Actor],
    player: Player,
    statics: StaticPool,
    rng: SequenceRng,
    line_of_sight: LineOfSight | None = None,
) -> AttackOutcome:
    checked = False

    def clear(actor: Actor) -> bool:
        nonlocal checked
        checked = True
        return line_of_sight(actor) if line_of_sight else actor.line_clear

    target = select_attack_target(actors, clear)
    if target is None or target.depth_q8 > KNIFE_RANGE_Q8:
        return AttackOutcome(
            target.actor_id if target else None,
            False,
            None,
            None,
            "knife",
            checked,
        )
    damage = rng.next_byte() >> 4
    result = damage_actor(target, damage, player, statics)
    return AttackOutcome(
        target.actor_id,
        result.result not in (DamageResult.REJECTED,),
        damage,
        result.result,
        "knife",
        checked,
    )


def gun_attack(
    actors: Iterable[Actor],
    player: Player,
    statics: StaticPool,
    rng: SequenceRng,
    line_of_sight: LineOfSight | None = None,
) -> AttackOutcome:
    """Apply source GunAttack targeting, trace order, and RNG consumption."""

    player.made_noise = True
    checked = False

    def clear(actor: Actor) -> bool:
        nonlocal checked
        checked = True
        return line_of_sight(actor) if line_of_sight else actor.line_clear

    target = select_attack_target(actors, clear)
    sound = {
        Weapon.PISTOL: "pistol",
        Weapon.MACHINEGUN: "machinegun",
        Weapon.CHAINGUN: "chaingun",
    }.get(player.weapon)
    if sound is None:
        raise CombatContractError("GunAttack requires a firearm")
    if target is None:
        return AttackOutcome(None, False, None, None, sound, checked)

    distance = max(
        abs(target.tile_x - player.tile_x),
        abs(target.tile_y - player.tile_y),
    )
    if distance < 2:
        damage = rng.next_byte() // 4
    elif distance < 4:
        damage = rng.next_byte() // 6
    else:
        if rng.next_byte() // 12 < distance:
            return AttackOutcome(target.actor_id, False, None, None, sound, True)
        damage = rng.next_byte() // 6

    result = damage_actor(target, damage, player, statics)
    return AttackOutcome(
        target.actor_id,
        result.result not in (DamageResult.REJECTED,),
        damage,
        result.result,
        sound,
        True,
    )


@dataclass
class WeaponRuntime:
    """Fixed-step adaptation of T_Player/Cmd_Fire/T_Attack button semantics."""

    player: Player
    active: bool = False
    attack_frame: int = 0
    attack_count: int = 0
    weapon_frame: int = 0
    attack_was_down: bool = False
    repeat_down: bool = False

    @property
    def weapon_shape(self) -> int:
        """Presentation invariant: current base plus current animation frame."""

        return WEAPON_SHAPE_BASE[self.player.weapon] + self.weapon_frame

    def give_ammo(self, amount: int) -> None:
        give_ammo(self.player, amount, attack_frame=self.attack_frame)

    def give_weapon(self, weapon: Weapon) -> None:
        give_weapon(self.player, weapon, attack_frame=self.attack_frame)

    def choose_weapon(self, number_keys: Iterable[Weapon]) -> None:
        if self.active or self.player.ammo == 0:
            return
        for weapon in sorted(set(number_keys)):
            if weapon <= self.player.best_weapon:
                self.player.weapon = weapon
                self.player.chosen_weapon = weapon
                self.weapon_frame = 0
                return

    def begin_attack(self) -> None:
        self.active = True
        self.attack_frame = 0
        self.attack_count = ATTACK_INFO[self.player.weapon][0].tics
        self.weapon_frame = ATTACK_INFO[self.player.weapon][0].frame

    def _finish_attack(self) -> None:
        self.active = False
        self.attack_frame = 0
        self.attack_count = 0
        self.weapon_frame = 0
        self.player.weapon = (
            Weapon.KNIFE if self.player.ammo == 0 else self.player.chosen_weapon
        )

    def step(
        self,
        tics: int,
        attack_down: bool,
        number_keys: Iterable[Weapon] = (),
    ) -> tuple[AttackAction, ...]:
        if tics < 0:
            raise CombatContractError("fixed-step tics cannot be negative")

        self.repeat_down = False
        if not attack_down:
            self.attack_was_down = False

        if not self.active:
            self.choose_weapon(number_keys)
            if attack_down and not self.attack_was_down:
                self.attack_was_down = True
                self.begin_attack()
            return ()

        if attack_down and self.attack_was_down:
            self.repeat_down = True

        self.attack_count -= tics
        emitted: list[AttackAction] = []
        while self.attack_count <= 0:
            table = ATTACK_INFO[self.player.weapon]
            if not 0 <= self.attack_frame < len(table):
                raise CombatContractError("attack frame escaped attackinfo")
            current = table[self.attack_frame]

            if current.action == AttackAction.FINISH:
                self._finish_attack()
                return tuple(emitted)
            if current.action == AttackAction.KNIFE:
                emitted.append(AttackAction.KNIFE)
            elif current.action == AttackAction.GUN:
                if self.player.ammo == 0:
                    # Source's chain-gun empty-ammo skip advances one extra row.
                    self.attack_frame += 1
                else:
                    emitted.append(AttackAction.GUN)
                    self.player.ammo -= 1
            elif current.action == AttackAction.REPEAT:
                if self.player.ammo and self.repeat_down:
                    self.attack_frame -= 2
            elif current.action == AttackAction.CHAIN:
                if self.player.ammo:
                    if self.repeat_down:
                        self.attack_frame -= 2
                    emitted.append(AttackAction.GUN)
                    self.player.ammo -= 1

            self.attack_count += current.tics
            self.attack_frame += 1
            table = ATTACK_INFO[self.player.weapon]
            if not 0 <= self.attack_frame < len(table):
                raise CombatContractError("attack frame escaped after action")
            self.weapon_frame = table[self.attack_frame].frame

        return tuple(emitted)


def fixed_tic_quanta(count: int, phase: int = 0) -> tuple[int, ...]:
    """Return the port's exact repeating 2,2,3 original-tic cadence."""

    if count < 0 or phase not in (0, 1, 2):
        raise CombatContractError("invalid fixed-tic request")
    cycle = (2, 2, 3)
    return tuple(cycle[(phase + index) % 3] for index in range(count))
