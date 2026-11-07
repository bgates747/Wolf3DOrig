# Original ray-walk bindings and defined machine arithmetic

This disposition precedes candidate code. Source inventory freeze b0bb47a and
SOURCE-PINS identify the reference and exact cd429 control. No new firmware/
SDK API is required: the selected unit is integer arithmetic and immutable data.

## Original operations carried over

Generate the900 tangent entries from BuildTables, including PI3.141592657,
float radtoint narrowing, half-bin i+0.5, paired reciprocal assignment and
truncation. Store the resulting int32 table in module rodata; no runtime libm
link or generated floating-point ray code. Historical Borland library byte
identity remains unproved. Independently check the generated values and bounds.

Translate actual entry90/180/270/360, initvars, vertcheck/vertentry/passvert and
horizcheck/horizentry/passhoriz flow. Keep their branch phase and <=/>= tile
comparisons rather than inventing an accumulated distance-DDA equivalent. Initial
partial products truncate magnitude then restore sign; a signed right shift
would round negative values differently and must not be substituted.

Emulate declared original word/long operations with explicit uint16/uint32
conversion and unsigned modulo arithmetic, plus explicit sign/high-word and
arithmetic-right-shift helpers. Original xpartialup/ypartialup narrow65536 to
zero on an exact grid coordinate; preserve and test that original edge case,
not a silent modern correction. Pushwall slope*position uses original low32-bit
product then arithmetic shift6, not a generic widened-divide replacement.
All helpers avoid C++ signed-overflow/negative-left-shift undefined behavior.
Source machine arithmetic is distinguished from valid closed64x64 game-domain
geometry; bounds checks/finite traversal remain for invalid/open input.

Ordinary vertical hits add a tile to the intercept for negative x stepping;
horizontal hits do likewise for negative y. Texture column reflects on negative
x vertical hits and positive y horizontal hits, as HitVertWall/HitHorizWall.
These are intentional original-method numerical/orientation differences from
the modern ray/vector reconstruction; retain current texture bank selection.
The asset exporter documents Smith's earlier single horizontal-art-bank choice;
this task does not add the missing vertical art bank or change assets.

Door plane uses half xstep/ystep, original same-tile rejection and fraction <
opening rejection. Keep the original source hit-side behavior; do not add a
different analytical ray-plane method to broaden synthetic door configurations.
Current real level door orientation/side-wall topology is the intended original
game domain. Record any current host fixture outside that domain separately;
it cannot be silently relabeled equivalent. Jamb IDs bind to existing122 asset,
using current door metadata to reconstruct original adjacent-door flags without
mutating the immutable base tilemap or changing wire records.

## Pushwall state binding

WL_ACT1.C PushWall marks current cell oldtile|0xc0 and reserves the next cell as
oldtile. MovePWalls clears each departed cell, advances current cell and marks
it0xc0; pwallpos=(pwallstate/2)&63. Current WorldMirror validator already proves
active position0..63, texture1..63, cardinal direction0/2/4/6, displacement0..1;
completed records prove cardinal displacement1..2 and texture1..63.

Thus the original logical tile view is available without a new wire field:
apply existing completed-wall overlays first; for an active wall clear its
departed origin-to-current corridor, mark its current cell as moving, and
reserve its current+direction cell as the ordinary wall. This is a data-layout
binding of the original state, not the current analytical slab-intersection
algorithm. Do not copy or mutate the4KiB base map per frame. Negative hit-side
offset/partial-slope/texture logic follows original Hit*PWall. Do not keep a
hidden fixed_div fallback for active walls or disable pushwall support.

Valid renderer input from the actual world/level path is the target domain.
Malformed raw WorldMirror structs bypassing the validated wire path are not
newly promised original gameplay states. Safe map bounds/finite failure handling
must remain; do not introduce original unchecked memory accesses into a module.

## Qualification and limits before a target cohort

The independent geometric checks and actual machine-word arithmetic checks
must be named separately. A second spelling of the candidate is not an
independent original-engine execution. No qualified historical DOS executable
oracle is claimed. Source-backed boundary cases and host exact arithmetic
checks, legal room/door/pushwall geometry and old-output delta records are
required before code/artifact/producer/resource and visual qualification.

Keep current projection87/current angle-offset table, setup_view sine/cosine,
sprites/HUD/weapon/render publication and all optimized row code fixed. This
restores the reviewed ray-walk/intersection method; it does not claim a literal
complete original renderer or blanket personal authorship by Carmack. Native
__divdi3 may remain for actor projection; absence of ray-step division must be
shown at the actual ray unit, not by incorrectly requiring the symbol disappear
from the whole program. No arithmetic-provider experiment is mixed into this.

All original-method incompatibilities found during implementation must stop
that affected change and be recorded. No promotion based only on speed or
mechanical compilation. Candidate output is expected to differ from cd429 at
documented original rounding/orientation boundaries; maintain the original
control oracle intact and report deltas rather than weakening its assertions.
