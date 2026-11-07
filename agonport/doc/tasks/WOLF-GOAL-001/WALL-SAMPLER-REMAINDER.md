# Remaining wall-sampler clamp — source-only priority assessment

This is follow-up to the authorized inner-loop work while PERF022's unchanged
full comparison waits behind Mech-first hardware dependencies. No renderer,
selected kit, package, guest, build or physical experiment changed.

The exact combined021 wall sampler already hoists mapped x, masks and texture
column address. The remaining `source_y >= 64` clamp is not a branch in the
retained target ELF: it lowers to one signed `min` instruction per texture
sample. Retained final disassembly has `movi.n a14,63` at111c, the linear-loop
`min a10,a10,a14` at11be and native-row-loop `min a4,a4,a14` at122b. The map's
draw_walls section starts0fcc, with entry after its literals at0fd4. This is
actual target code, not an assumption based on the C++ spelling.

The private helper has only the wall-column wrapper as caller; that wrapper is
only used by draw_walls. Positive-height chain membership ensures H>0. With
Q=64*65536, step=floor(Q/H), top=80-floor(H/2), clipped top=max(top,0) and clipped
bottom=min(top+H,160), a sampled row has original wall-relative coordinate j
between0 and H-1. Its fraction is step*j, so

    0 <= step*j <= floor(Q/H)*(H-1) < Q

and source_y=floor(fraction/65536) is0..63. If H>Q then step=0 and the same bound
holds. The final unused increment is at mostQ; the products do not overflow
int32 under these formulas. top and top+H also fit for positive int32 H. Reusing
cached setup for the same FULL height preserves these arguments. This is a
source proof for this private call domain, not permission to remove bounds
from a general sampler or change projection, clipping or fractional stepping.

Thus an exact private-domain clamp removal is a possible supported cleanup.
Its potential saving is small compared with removing a pixel call or a branch:
one min per wall sample if other lowering stays unchanged. The existing020
600-pose census counts4368126 samples, about7280 per pose. This is a static
instruction opportunity, not measured cycles, an exclusive CPU profile, a
physical hit count or an estimated framerate win. Register allocation/layout
could change after editing and would need inspection. Current combined timing
is still unmeasured, so that full matched comparison takes precedence.

Disposition: retain as a low-priority possible local cleanup; no implementation
or new hardware matrix selected here. Before any later candidate, freeze its
own exact control/pre-code contract, qualify the complete H/clipping/fraction
domain and real output/order/resource paths, inspect actual emitted loops, then
use normal finite resource admission. No row reordering, wider stores, service
extension, approximation or generic pointer/PSRAM assumptions follow from this
proof. Sprite013's separately requested human discussion remains pending.

Exact local source/ELF/map/disassembly and prior census pins are retained in
WALL-SAMPLER-REMAINDER-PINS.json. No compiler or hardware custody was needed.
