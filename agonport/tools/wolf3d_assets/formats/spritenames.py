"""Wolf3D VSWAP sprite "shapenum" constants used to render real sprite art
in place of category-colored placeholders (see toolchain.cli.extract's
plane1 tileset).

A VSWAP sprite chunk's index is ``spritestart + shapenum``, where
``shapenum`` is the 0-based position of a name in a single large C enum
(``orig/src/WOLFSRC/WL_DEF.H``, non-SPEAR/WL1-WL6 branch only -- this
project doesn't target Spear of Destiny). That source file is external,
git-ignored reference material (see the repo's licensing boundary notes),
so rather than parsing it at runtime, the handful of shapenum values this
project actually needs were computed once with a small local script that
resolves the enum's ``#ifndef SPEAR``/``#else``/``#endif`` branches and
counts entries in order, then transcribed here as plain integers -- the
same "ground against the source once, then hard-code an independent
constant" pattern already used by palette.py.

Only a small subset of the ~435-entry enum is covered: the 49 static-item
shapenums (a direct 1:1 table, mirroring WL_ACT1.C's ``statinfo[]``) and one
representative "standing" frame per enemy/boss/ghost type. This is
real decoded pixel art, but not full per-facing/per-animation-frame
fidelity -- every dispatch code for a given creature type (any of its 4
facings, patrol vs. stand, any difficulty tier) renders the same single
representative frame. Full animation-frame accuracy would require also
grounding each creature's `statetype` state-machine tables
(WL_ACT1.C/WL_ACT2.C's `s_*stand`/`s_*walk1` chains), which is out of
scope for this pass.

Forked 2026-07-31 from src/toolchain/formats/spritenames.py (verbatim at
fork time) into agonport/tools/wolf3d_assets/, per Author decision to
vendor canonical decoders rather than import across project boundaries.
See sprite_kinds.py in this same package for how this project's asset
pipeline builds on these anchors to cover EVERY animation frame per
creature type (not just one representative frame) -- required per Author
decision 2026-07-31 ("we need to build the animation system from the jump
so that we don't corner ourselves later").
"""

# Index 0 == plane1 tile 23 (SpawnStatic's tile-23 offset, WL_GAME.C), and
# each value is that static item's shapenum (SPR_STAT_N == 2+N, since the
# enum starts SPR_DEMO=0, SPR_DEATHCAM=1, then SPR_STAT_0=2 with no gaps up
# to SPR_STAT_47=49). Mirrors WL_ACT1.C's statinfo[] table order exactly,
# including its trailing duplicate "Clip" entry (SPR_STAT_26 again) at
# index 48 -- see extract.py's STATIC_NAMES for the matching name list.
STATIC_SHAPENUMS = [2 + i for i in range(48)] + [2 + 26]

SPR_GRD_S_1 = 50
SPR_GRD_DEAD = 95
SPR_DOG_W1_1 = 99
SPR_SS_S_1 = 138
SPR_MUT_S_1 = 187
SPR_OFC_S_1 = 238
SPR_BLINKY_W1 = 288
SPR_PINKY_W1 = 290
SPR_CLYDE_W1 = 292
SPR_INKY_W1 = 294
SPR_BOSS_W1 = 296       # Hans Grosse
SPR_SCHABB_W1 = 307     # Dr. Schabbs
SPR_FAKE_W1 = 321       # fake Hitler (precedes Mecha Hitler in WL_DEF.H)
SPR_MECHA_W1 = 334      # fake/robot Hitler
SPR_HITLER_W1 = 345     # real Hitler
SPR_GIFT_W1 = 360       # Otto Giftmacher
SPR_GRETEL_W1 = 385     # Gretel Grosse
SPR_FAT_W1 = 396        # General Fettgesicht

# One representative shapenum per creature type, keyed to match
# extract.py's ENEMY_KINDS/MUTANT names.
ENEMY_STAND_SHAPENUMS = {
    "GRD": SPR_GRD_S_1,
    "OFC": SPR_OFC_S_1,
    "SS": SPR_SS_S_1,
    "DOG": SPR_DOG_W1_1,  # dogs have no idle "stand" state -- first walk frame stands in
    "MUT": SPR_MUT_S_1,
}

BOSS_SHAPENUMS = {
    "HANS": SPR_BOSS_W1,
    "GRETEL": SPR_GRETEL_W1,
    "OTTO": SPR_GIFT_W1,
    "FAT": SPR_FAT_W1,
    "SCHABBS": SPR_SCHABB_W1,
    "HTLR-FAKE": SPR_FAKE_W1,
    "HITLER": SPR_HITLER_W1,
}

GHOST_SHAPENUMS = {
    "BLINKY": SPR_BLINKY_W1,
    "PINKY": SPR_PINKY_W1,
    "CLYDE": SPR_CLYDE_W1,
    "INKY": SPR_INKY_W1,
}
