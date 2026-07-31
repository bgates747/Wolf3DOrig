"""Per-creature-kind contiguous VSWAP shapenum block boundaries, derived
from spritenames.py's known first-frame anchors -- used to cover EVERY
animation frame for a creature kind (not just spritenames.py's single
representative "standing" frame), per Author decision 2026-07-31 ("we need
to build the animation system from the jump so that we don't corner
ourselves later in a rush to get a test fixture shipped before the sun
comes up").

Derivation and assumption (new reasoning, not present in spritenames.py or
extract.py): real Wolf3D VSWAP sprite chunks are laid out in one big C enum
(WL_DEF.H, non-SPEAR branch), grouped by creature type in a fixed order,
with every one of a creature's states/facings/difficulty-tier duplicates
packed contiguously before the next creature type begins -- e.g.
SPR_GRD_S_1=50 (guard's first frame) through SPR_DOG_W1_1-1=98 (right
before the dog's first frame) are ALL guard frames (stand/path/pain/
shoot/die, every facing). This module sorts spritenames.py's known
first-frame anchors by shapenum and treats each anchor as a block start,
the next anchor (in sorted order) minus one as that block's end, and the
final block's end as the last real VSWAP sprite shapenum.

This is a derived heuristic, not independently grounded against WL_DEF.H's
full enum text (unlike spritenames.py's anchors themselves, which WERE
individually computed against that source -- see spritenames.py's
docstring). Per Author decision 2026-07-31 ("keep it simple, pick one and
run with it, revisit if it doesn't look right"): visually verify exported
per-kind blocks with the Stage E viewer against real gameplay footage/
screenshots, and narrow a block's bounds here if it turns out to include
frames from an adjacent, wrong creature type.

Only creature kinds are covered here -- static items need no block/heuristic
at all, since STATIC_SHAPENUMS is already an exact 1:1 mapping (statics
don't animate or have facing variants).
"""

from . import spritenames

# (kind name, first-frame shapenum), matching extract.py's ENEMY_KINDS/
# MUTANT/BOSS_NAMES/GHOST_NAMES vocabulary.
_KIND_FIRST_SHAPENUM = {
    "GRD": spritenames.SPR_GRD_S_1,
    "DOG": spritenames.SPR_DOG_W1_1,
    "SS": spritenames.SPR_SS_S_1,
    "MUT": spritenames.SPR_MUT_S_1,
    "OFC": spritenames.SPR_OFC_S_1,
    "BLINKY": spritenames.SPR_BLINKY_W1,
    "PINKY": spritenames.SPR_PINKY_W1,
    "CLYDE": spritenames.SPR_CLYDE_W1,
    "INKY": spritenames.SPR_INKY_W1,
    "HANS": spritenames.SPR_BOSS_W1,
    "SCHABBS": spritenames.SPR_SCHABB_W1,
    "HTLR-FAKE": spritenames.SPR_FAKE_W1,
    # The plane-1 HITLER marker first spawns Mecha-Hitler, then transitions
    # into the real-Hitler frames. Keep both contiguous ranges in one asset
    # block beginning at the Mecha anchor.
    "HITLER": spritenames.SPR_MECHA_W1,
    "OTTO": spritenames.SPR_GIFT_W1,
    "GRETEL": spritenames.SPR_GRETEL_W1,
    "FAT": spritenames.SPR_FAT_W1,
}


def kind_shapenum_block(kind: str, max_shapenum: int) -> tuple[int, int]:
    """Return (first_shapenum, last_shapenum) inclusive for a creature kind,
    e.g. kind_shapenum_block("GRD", 435) -> (50, 98). ``max_shapenum`` is the
    real VSWAP file's highest valid shapenum (soundstart - spritestart - 1),
    used as the last kind's block end."""
    ordered = sorted(_KIND_FIRST_SHAPENUM.items(), key=lambda item: item[1])
    names = [name for name, _ in ordered]
    starts = [start for _, start in ordered]
    index = names.index(kind)
    start = starts[index]
    end = (starts[index + 1] - 1) if index + 1 < len(starts) else max_shapenum
    return start, end
