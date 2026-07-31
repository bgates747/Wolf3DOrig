"""Wolfenstein 3-D WL1 static-object metadata.

This is the non-SPEAR ``statinfo[]`` table from ``WL_ACT1.C`` expressed as
durable build-tool data.  Plane-1 values 23 through 71 select these 49 entries
in order.  ``kind`` retains the original ``stat_t`` numeric value from
``WL_DEF.H``; ``bonus`` and ``blocking`` retain the behavior of
``SpawnStatic()`` rather than being inferred from sprite names.

The last entry is the original duplicate SPR_STAT_26/bo_clip2 entry used by
``PlaceItemType()`` for dropped ammunition.  The original ``SpawnStatic()``
switch does not include bo_clip2, so its initial bonus flag is deliberately
false here as well.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .spritenames import STATIC_SHAPENUMS

STATIC_PLANE1_MIN = 23
FL_BONUS = 0x02


class StatKind(IntEnum):
    """Numeric order of the original ``stat_t`` enum in ``WL_DEF.H``."""

    DRESSING = 0
    BLOCK = 1
    BO_GIBS = 2
    BO_ALPO = 3
    BO_FIRSTAID = 4
    BO_KEY1 = 5
    BO_KEY2 = 6
    BO_KEY3 = 7
    BO_KEY4 = 8
    BO_CROSS = 9
    BO_CHALICE = 10
    BO_BIBLE = 11
    BO_CROWN = 12
    BO_CLIP = 13
    BO_CLIP2 = 14
    BO_MACHINEGUN = 15
    BO_CHAINGUN = 16
    BO_FOOD = 17
    BO_FULLHEAL = 18
    BO_25CLIP = 19
    BO_SPEAR = 20


@dataclass(frozen=True)
class StaticInfo:
    shapenum: int
    kind: StatKind
    bonus: bool
    blocking: bool


# Non-SPEAR WL_ACT1.C statinfo[] kinds, including the final bo_clip2 entry.
_KINDS = (
    StatKind.DRESSING,       #  0 puddle
    StatKind.BLOCK,          #  1 green barrel
    StatKind.BLOCK,          #  2 table/chairs
    StatKind.BLOCK,          #  3 floor lamp
    StatKind.DRESSING,       #  4 chandelier
    StatKind.BLOCK,          #  5 hanged man
    StatKind.BO_ALPO,        #  6 bad food
    StatKind.BLOCK,          #  7 red pillar
    StatKind.BLOCK,          #  8 tree
    StatKind.DRESSING,       #  9 skeleton flat
    StatKind.BLOCK,          # 10 sink
    StatKind.BLOCK,          # 11 potted plant
    StatKind.BLOCK,          # 12 urn
    StatKind.BLOCK,          # 13 bare table
    StatKind.DRESSING,       # 14 ceiling light
    StatKind.DRESSING,       # 15 kitchen stuff (non-SPEAR)
    StatKind.BLOCK,          # 16 suit of armor
    StatKind.BLOCK,          # 17 hanging cage
    StatKind.BLOCK,          # 18 skeleton in cage
    StatKind.DRESSING,       # 19 relaxed skeleton
    StatKind.BO_KEY1,        # 20 gold key
    StatKind.BO_KEY2,        # 21 silver key
    StatKind.BLOCK,          # 22 stuff
    StatKind.DRESSING,       # 23 stuff
    StatKind.BO_FOOD,        # 24 good food
    StatKind.BO_FIRSTAID,    # 25 first aid
    StatKind.BO_CLIP,        # 26 ammunition clip
    StatKind.BO_MACHINEGUN,  # 27 machine gun
    StatKind.BO_CHAINGUN,    # 28 chaingun
    StatKind.BO_CROSS,       # 29 cross
    StatKind.BO_CHALICE,     # 30 chalice
    StatKind.BO_BIBLE,       # 31 bible
    StatKind.BO_CROWN,       # 32 crown
    StatKind.BO_FULLHEAL,    # 33 one-up
    StatKind.BO_GIBS,        # 34 gibs
    StatKind.BLOCK,          # 35 barrel
    StatKind.BLOCK,          # 36 full well
    StatKind.BLOCK,          # 37 empty well
    StatKind.BO_GIBS,        # 38 gibs 2
    StatKind.BLOCK,          # 39 flag
    StatKind.BLOCK,          # 40 Call Apogee (non-SPEAR)
    StatKind.DRESSING,       # 41 junk
    StatKind.DRESSING,       # 42 junk
    StatKind.DRESSING,       # 43 junk
    StatKind.DRESSING,       # 44 pots (non-SPEAR)
    StatKind.BLOCK,          # 45 stove
    StatKind.BLOCK,          # 46 spears
    StatKind.DRESSING,       # 47 vines
    StatKind.BO_CLIP2,       # 48 duplicate clip used by PlaceItemType()
)

# These are precisely the cases which set FL_BONUS in SpawnStatic().
_BONUS_KINDS = frozenset(
    {
        StatKind.BO_GIBS,
        StatKind.BO_ALPO,
        StatKind.BO_FIRSTAID,
        StatKind.BO_KEY1,
        StatKind.BO_KEY2,
        StatKind.BO_KEY3,
        StatKind.BO_KEY4,
        StatKind.BO_CROSS,
        StatKind.BO_CHALICE,
        StatKind.BO_BIBLE,
        StatKind.BO_CROWN,
        StatKind.BO_CLIP,
        StatKind.BO_MACHINEGUN,
        StatKind.BO_CHAINGUN,
        StatKind.BO_FOOD,
        StatKind.BO_FULLHEAL,
        StatKind.BO_25CLIP,
        StatKind.BO_SPEAR,
    }
)

assert len(STATIC_SHAPENUMS) == len(_KINDS) == 49

STATIC_INFO = tuple(
    StaticInfo(
        shapenum=shapenum,
        kind=kind,
        bonus=kind in _BONUS_KINDS,
        blocking=kind == StatKind.BLOCK,
    )
    for shapenum, kind in zip(STATIC_SHAPENUMS, _KINDS, strict=True)
)


def from_plane1(value: int) -> StaticInfo | None:
    """Return metadata for a WL1 plane-1 static marker, else ``None``."""

    index = value - STATIC_PLANE1_MIN
    if 0 <= index < len(STATIC_INFO):
        return STATIC_INFO[index]
    return None
