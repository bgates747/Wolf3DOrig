"""Wolfenstein 3-D WL1 plane-1 actor spawn metadata.

This module is the build-time counterpart of the eZ80 actor pool.  It mirrors
``ScanInfoPlane()``, ``SpawnStand()``, ``SpawnPatrol()``, and the non-SPEAR
boss/ghost spawners from the original sources closely enough to construct the
authoritative state at the first simulation tick.  Rendering fields are not
invented here: ``shapenum`` is the current state's base shape, ``rotations``
is the original state's ``rotate`` value (0 or 8 for initial map actors), and
``facing_degrees`` is the effective world-facing angle consumed by the VDP.

The map contains three copies of ordinary enemy markers.  The base copy is
present at every difficulty, the second appears on medium/hard, and the third
only on hard.  This is the exact fall-through behavior in ``WL_GAME.C``;
baby and easy therefore have the same placement count.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from . import spritenames


TILE_GLOBAL = 1 << 16
AREATILE = 107
AMBUSHTILE = 106

FL_SHOOTABLE = 0x01
FL_AMBUSH = 0x40

SPDPATROL = 512
SPDDOG = 1500


class Difficulty(IntEnum):
    BABY = 0
    EASY = 1
    MEDIUM = 2
    HARD = 3


class ActiveType(IntEnum):
    NO = 0
    YES = 1
    ALWAYS = 2


class ActorClass(IntEnum):
    """Numeric ``classtype`` values from non-SPEAR ``WL_DEF.H``."""

    NOTHING = 0
    PLAYER = 1
    INERT = 2
    GUARD = 3
    OFFICER = 4
    SS = 5
    DOG = 6
    BOSS = 7
    SCHABBS = 8
    FAKE = 9
    MECHA_HITLER = 10
    MUTANT = 11
    NEEDLE = 12
    FIRE = 13
    BJ = 14
    GHOST = 15
    REAL_HITLER = 16
    GRETEL = 17
    GIFT = 18
    FAT = 19
    ROCKET = 20


class ActorState(IntEnum):
    """Stable state ids shared with ``wolf3d_world.inc``.

    These are indices into the eZ80 state table, not VSWAP shape ids.  Map
    actors initially use ids 1..21; ids 22..46 complete the ordinary-enemy
    path cycles, ids 47..76 are the stable chase chains, ids 77..100 are the
    ordinary ranged/dog attack animations, and ids 101..129 are the ordinary
    pain/death chains installed by player combat.
    """

    GRD_STAND = 1
    GRD_PATH1 = 2
    DOG_PATH1 = 3
    OFC_STAND = 4
    OFC_PATH1 = 5
    MUT_STAND = 6
    MUT_PATH1 = 7
    SS_STAND = 8
    SS_PATH1 = 9
    GRD_DEAD = 10
    BLINKY_CHASE1 = 11
    CLYDE_CHASE1 = 12
    PINKY_CHASE1 = 13
    INKY_CHASE1 = 14
    BOSS_STAND = 15
    GRETEL_STAND = 16
    SCHABBS_STAND = 17
    GIFT_STAND = 18
    FAT_STAND = 19
    FAKE_STAND = 20
    MECHA_STAND = 21
    GRD_PATH1S = 22
    GRD_PATH2 = 23
    GRD_PATH3 = 24
    GRD_PATH3S = 25
    GRD_PATH4 = 26
    DOG_PATH1S = 27
    DOG_PATH2 = 28
    DOG_PATH3 = 29
    DOG_PATH3S = 30
    DOG_PATH4 = 31
    OFC_PATH1S = 32
    OFC_PATH2 = 33
    OFC_PATH3 = 34
    OFC_PATH3S = 35
    OFC_PATH4 = 36
    MUT_PATH1S = 37
    MUT_PATH2 = 38
    MUT_PATH3 = 39
    MUT_PATH3S = 40
    MUT_PATH4 = 41
    SS_PATH1S = 42
    SS_PATH2 = 43
    SS_PATH3 = 44
    SS_PATH3S = 45
    SS_PATH4 = 46
    GRD_CHASE1 = 47
    DOG_CHASE1 = 48
    OFC_CHASE1 = 49
    MUT_CHASE1 = 50
    SS_CHASE1 = 51
    GRD_CHASE1S = 52
    GRD_CHASE2 = 53
    GRD_CHASE3 = 54
    GRD_CHASE3S = 55
    GRD_CHASE4 = 56
    DOG_CHASE1S = 57
    DOG_CHASE2 = 58
    DOG_CHASE3 = 59
    DOG_CHASE3S = 60
    DOG_CHASE4 = 61
    OFC_CHASE1S = 62
    OFC_CHASE2 = 63
    OFC_CHASE3 = 64
    OFC_CHASE3S = 65
    OFC_CHASE4 = 66
    MUT_CHASE1S = 67
    MUT_CHASE2 = 68
    MUT_CHASE3 = 69
    MUT_CHASE3S = 70
    MUT_CHASE4 = 71
    SS_CHASE1S = 72
    SS_CHASE2 = 73
    SS_CHASE3 = 74
    SS_CHASE3S = 75
    SS_CHASE4 = 76
    GRD_SHOOT1 = 77
    GRD_SHOOT2 = 78
    GRD_SHOOT3 = 79
    DOG_JUMP1 = 80
    DOG_JUMP2 = 81
    DOG_JUMP3 = 82
    DOG_JUMP4 = 83
    DOG_JUMP5 = 84
    OFC_SHOOT1 = 85
    OFC_SHOOT2 = 86
    OFC_SHOOT3 = 87
    MUT_SHOOT1 = 88
    MUT_SHOOT2 = 89
    MUT_SHOOT3 = 90
    MUT_SHOOT4 = 91
    SS_SHOOT1 = 92
    SS_SHOOT2 = 93
    SS_SHOOT3 = 94
    SS_SHOOT4 = 95
    SS_SHOOT5 = 96
    SS_SHOOT6 = 97
    SS_SHOOT7 = 98
    SS_SHOOT8 = 99
    SS_SHOOT9 = 100
    GRD_PAIN = 101
    GRD_PAIN1 = 102
    GRD_DIE1 = 103
    GRD_DIE2 = 104
    GRD_DIE3 = 105
    DOG_DIE1 = 106
    DOG_DIE2 = 107
    DOG_DIE3 = 108
    DOG_DEAD = 109
    OFC_PAIN = 110
    OFC_PAIN1 = 111
    OFC_DIE1 = 112
    OFC_DIE2 = 113
    OFC_DIE3 = 114
    OFC_DIE4 = 115
    OFC_DEAD = 116
    MUT_PAIN = 117
    MUT_PAIN1 = 118
    MUT_DIE1 = 119
    MUT_DIE2 = 120
    MUT_DIE3 = 121
    MUT_DIE4 = 122
    MUT_DEAD = 123
    SS_PAIN = 124
    SS_PAIN1 = 125
    SS_DIE1 = 126
    SS_DIE2 = 127
    SS_DIE3 = 128
    SS_DEAD = 129


# John Carmack's original 256-byte table from ID_US_A.ASM.  ``US_InitRndT
# (false)`` sets the index to zero; ``US_RndT`` increments the index before
# returning the table byte.  Keeping the unused-at-start table[0] entry is
# important because it is returned on the 256th call after the index wraps.
RND_TABLE = (
    0, 8, 109, 220, 222, 241, 149, 107, 75, 248, 254, 140, 16, 66,
    74, 21, 211, 47, 80, 242, 154, 27, 205, 128, 161, 89, 77, 36,
    95, 110, 85, 48, 212, 140, 211, 249, 22, 79, 200, 50, 28, 188,
    52, 140, 202, 120, 68, 145, 62, 70, 184, 190, 91, 197, 152, 224,
    149, 104, 25, 178, 252, 182, 202, 182, 141, 197, 4, 81, 181, 242,
    145, 42, 39, 227, 156, 198, 225, 193, 219, 93, 122, 175, 249, 0,
    175, 143, 70, 239, 46, 246, 163, 53, 163, 109, 168, 135, 2, 235,
    25, 92, 20, 145, 138, 77, 69, 166, 78, 176, 173, 212, 166, 113,
    94, 161, 41, 50, 239, 49, 111, 164, 70, 60, 2, 37, 171, 75,
    136, 156, 11, 56, 42, 146, 138, 229, 73, 146, 77, 61, 98, 196,
    135, 106, 63, 197, 195, 86, 96, 203, 113, 101, 170, 247, 181, 113,
    80, 250, 108, 7, 255, 237, 129, 226, 79, 107, 112, 166, 103, 241,
    24, 223, 239, 120, 198, 58, 60, 82, 128, 3, 184, 66, 143, 224,
    145, 224, 81, 206, 163, 45, 63, 90, 168, 114, 59, 33, 159, 95,
    28, 139, 123, 98, 125, 196, 15, 70, 194, 253, 54, 14, 109, 226,
    71, 17, 161, 93, 186, 87, 244, 138, 20, 52, 123, 251, 26, 36,
    17, 46, 52, 231, 232, 76, 31, 221, 84, 37, 216, 165, 212, 106,
    197, 242, 98, 43, 39, 175, 254, 145, 190, 84, 118, 222, 187, 136,
    120, 163, 236, 249,
)


class DeterministicRandom:
    """Exact table/index behavior of ``US_InitRndT(false)`` + ``US_RndT``."""

    def __init__(self) -> None:
        self.index = 0

    def rndt(self) -> int:
        self.index = (self.index + 1) & 0xFF
        return RND_TABLE[self.index]


# Initial-state durations from the original statetype declarations.  All
# omitted map-spawn states have tictime == 0 and therefore must not consume a
# random byte in SpawnNewObj().
_INITIAL_STATE_TICTIME = {
    ActorState.GRD_PATH1: 20,
    ActorState.DOG_PATH1: 20,
    ActorState.OFC_PATH1: 20,
    ActorState.MUT_PATH1: 20,
    ActorState.SS_PATH1: 20,
    ActorState.BLINKY_CHASE1: 10,
    ActorState.CLYDE_CHASE1: 10,
    ActorState.PINKY_CHASE1: 10,
    ActorState.INKY_CHASE1: 10,
}


def initial_state_tictime(state: ActorState) -> int:
    """Return the original duration of a map actor's initial state."""

    return _INITIAL_STATE_TICTIME.get(ActorState(state), 0)


def initial_ticcounts(actors: list["ActorSeed"]) -> list[int]:
    """Reproduce SpawnNewObj's deterministic initial phase for each actor.

    Actor order matters: SetupGameLevel scans plane 1 row-major.  Zero-time
    states yield zero without advancing the random table.
    """

    random = DeterministicRandom()
    result = []
    for actor in actors:
        tictime = initial_state_tictime(actor.state)
        result.append(random.rndt() % tictime if tictime else 0)
    return result


def random_index_after_initial_ticcounts(actors: list["ActorSeed"]) -> int:
    """Return the exact table index left by the original map spawn pass."""

    return sum(bool(initial_state_tictime(actor.state)) for actor in actors) & 0xFF


@dataclass(frozen=True)
class ActorSeed:
    marker: int
    kind: str
    state: ActorState
    obclass: ActorClass
    shapenum: int
    rotations: int
    x: int
    y: int
    tilex: int
    tiley: int
    area: int
    direction: int
    facing_degrees: int
    angle: int
    hitpoints: int
    flags: int
    distance: int
    speed: int
    active: ActiveType


# Enemy index order from ``enemy_t`` / ``starthitpoints``.  Only non-SPEAR
# map-spawned kinds are named here.
_HITPOINTS = {
    "GRD": (25, 25, 25, 25),
    "OFC": (50, 50, 50, 50),
    "SS": (100, 100, 100, 100),
    "DOG": (1, 1, 1, 1),
    "HANS": (850, 950, 1050, 1200),
    "SCHABBS": (850, 950, 1550, 2400),
    "HTLR-FAKE": (200, 300, 400, 500),
    "HITLER": (800, 950, 1050, 1200),
    "MUT": (45, 55, 55, 65),
    # SpawnGhosts leaves zeroed hitpoints untouched; ghosts are unshootable.
    "BLINKY": (0, 0, 0, 0),
    "CLYDE": (0, 0, 0, 0),
    "PINKY": (0, 0, 0, 0),
    "INKY": (0, 0, 0, 0),
    "GRETEL": (850, 950, 1050, 1200),
    "OTTO": (850, 950, 1050, 1200),
    "FAT": (850, 950, 1050, 1200),
}


# kind, stand marker, patrol marker, class, stand state, path state,
# stand shape, path shape.  The +8 relationship is grounded in WL_DEF.H's
# eight standing rotations immediately followed by eight W1 rotations.
_ORDINARY = (
    (
        "GRD", 108, 112, ActorClass.GUARD,
        ActorState.GRD_STAND, ActorState.GRD_PATH1,
        spritenames.SPR_GRD_S_1, spritenames.SPR_GRD_S_1 + 8,
    ),
    (
        "OFC", 116, 120, ActorClass.OFFICER,
        ActorState.OFC_STAND, ActorState.OFC_PATH1,
        spritenames.SPR_OFC_S_1, spritenames.SPR_OFC_S_1 + 8,
    ),
    (
        "SS", 126, 130, ActorClass.SS,
        ActorState.SS_STAND, ActorState.SS_PATH1,
        spritenames.SPR_SS_S_1, spritenames.SPR_SS_S_1 + 8,
    ),
    # Stock maps contain no dog standing markers.  SpawnStand() likewise has
    # no en_dog arm, so only the patrol range is accepted below.
    (
        "DOG", None, 138, ActorClass.DOG,
        None, ActorState.DOG_PATH1,
        None, spritenames.SPR_DOG_W1_1,
    ),
    (
        "MUT", 216, 220, ActorClass.MUTANT,
        ActorState.MUT_STAND, ActorState.MUT_PATH1,
        spritenames.SPR_MUT_S_1, spritenames.SPR_MUT_S_1 + 8,
    ),
)


# marker -> kind, state, class, shape, initial direction.  Boss states do not
# rotate in the original.  Hitler begins as the Mecha-Hitler actor/state.
_BOSSES = {
    214: ("HANS", ActorState.BOSS_STAND, ActorClass.BOSS, spritenames.SPR_BOSS_W1, 6),
    197: ("GRETEL", ActorState.GRETEL_STAND, ActorClass.GRETEL, spritenames.SPR_GRETEL_W1, 2),
    215: ("OTTO", ActorState.GIFT_STAND, ActorClass.GIFT, spritenames.SPR_GIFT_W1, 2),
    179: ("FAT", ActorState.FAT_STAND, ActorClass.FAT, spritenames.SPR_FAT_W1, 6),
    196: ("SCHABBS", ActorState.SCHABBS_STAND, ActorClass.SCHABBS, spritenames.SPR_SCHABB_W1, 6),
    160: ("HTLR-FAKE", ActorState.FAKE_STAND, ActorClass.FAKE, spritenames.SPR_FAKE_W1, 2),
    178: ("HITLER", ActorState.MECHA_STAND, ActorClass.MECHA_HITLER, spritenames.SPR_MECHA_W1, 6),
}

_GHOSTS = {
    224: ("BLINKY", ActorState.BLINKY_CHASE1, spritenames.SPR_BLINKY_W1),
    225: ("CLYDE", ActorState.CLYDE_CHASE1, spritenames.SPR_CLYDE_W1),
    226: ("PINKY", ActorState.PINKY_CHASE1, spritenames.SPR_PINKY_W1),
    227: ("INKY", ActorState.INKY_CHASE1, spritenames.SPR_INKY_W1),
}


def _required_difficulty(tier: int) -> Difficulty:
    return (Difficulty.BABY, Difficulty.MEDIUM, Difficulty.HARD)[tier]


def area_number_at(plane0: list[list[int]], x: int, y: int) -> int:
    tile = plane0[y][x]
    if tile == AMBUSHTILE:
        # Preserve SpawnStand's four independent assignments and therefore
        # its right/up/down/left overwrite order.
        found = None
        for nx, ny in ((x + 1, y), (x, y - 1), (x, y + 1), (x - 1, y)):
            if not (0 <= ny < len(plane0) and 0 <= nx < len(plane0[ny])):
                continue
            candidate = plane0[ny][nx]
            if candidate >= AREATILE:
                found = candidate
        if found is not None:
            tile = found
    return max(0, tile - AREATILE)


def _ordinary_marker(marker: int):
    for (
        kind, stand_base, patrol_base, obclass,
        stand_state, patrol_state, stand_shape, patrol_shape,
    ) in _ORDINARY:
        tier_step = 18 if kind == "MUT" else 36
        for tier in range(3):
            required = _required_difficulty(tier)
            if stand_base is not None:
                base = stand_base + tier * tier_step
                if base <= marker <= base + 3:
                    return (
                        kind, False, marker - base, required, obclass,
                        stand_state, stand_shape,
                    )
            base = patrol_base + tier * tier_step
            if base <= marker <= base + 3:
                return (
                    kind, True, marker - base, required, obclass,
                    patrol_state, patrol_shape,
                )
    return None


def from_plane1(
    marker: int,
    x: int,
    y: int,
    plane0: list[list[int]],
    difficulty: Difficulty,
) -> ActorSeed | None:
    """Decode one plane-1 value into its initial authoritative actor.

    Returns ``None`` both for non-actor markers and for an actor filtered out
    by the selected difficulty, matching ``ScanInfoPlane()``.
    """

    difficulty = Difficulty(difficulty)
    center_x = x * TILE_GLOBAL + TILE_GLOBAL // 2
    center_y = y * TILE_GLOBAL + TILE_GLOBAL // 2
    area = area_number_at(plane0, x, y)

    if marker == 124:  # SpawnDeadGuard
        return ActorSeed(
            marker, "DEAD-GRD", ActorState.GRD_DEAD, ActorClass.INERT,
            spritenames.SPR_GRD_DEAD, 0, center_x, center_y, x, y, area,
            8, 0, 0, 0, 0, 0, 0, ActiveType.NO,
        )

    ordinary = _ordinary_marker(marker)
    if ordinary is not None:
        kind, patrol, cardinal, required, obclass, state, shape = ordinary
        if difficulty < required:
            return None
        direction = cardinal * 2
        tilex, tiley = x, y
        distance = 0
        active = ActiveType.NO
        if patrol:
            # SpawnPatrol moves actorat's cached destination one tile ahead,
            # while x/y stay at the source marker center until T_Path moves.
            dx_dy = ((1, 0), (0, -1), (-1, 0), (0, 1))[cardinal]
            tilex += dx_dy[0]
            tiley += dx_dy[1]
            distance = TILE_GLOBAL
            active = ActiveType.YES
        flags = FL_SHOOTABLE
        if not patrol and plane0[y][x] == AMBUSHTILE:
            flags |= FL_AMBUSH
        speed = SPDDOG if kind == "DOG" else SPDPATROL
        return ActorSeed(
            marker, kind, state, obclass, shape, 8,
            center_x, center_y, tilex, tiley, area,
            direction, direction * 45, 0, _HITPOINTS[kind][difficulty],
            flags, distance, speed, active,
        )

    boss = _BOSSES.get(marker)
    if boss is not None:
        kind, state, obclass, shape, direction = boss
        return ActorSeed(
            marker, kind, state, obclass, shape, 0,
            center_x, center_y, x, y, area,
            direction, direction * 45, 0, _HITPOINTS[kind][difficulty],
            FL_SHOOTABLE | FL_AMBUSH, 0, SPDPATROL, ActiveType.NO,
        )

    ghost = _GHOSTS.get(marker)
    if ghost is not None:
        kind, state, shape = ghost
        return ActorSeed(
            marker, kind, state, ActorClass.GHOST, shape, 0,
            center_x, center_y, x, y, area,
            # SpawnGhosts leaves the zero-initialized hitpoints field alone;
            # ghosts are not shootable in the original.
            0, 0, 0, 0, FL_AMBUSH,
            0, SPDDOG, ActiveType.NO,
        )

    return None
