# Original method inventory before implementation

Baseline is the exact qualified physical69 O2 module cd429e2f, not the stale
production/default tree. SOURCE-PINS.json identifies its source and the local
original PC reference. This ledger follows Smith's pre-code/no-workaround gate.
The original is method evidence; per-function personal authorship or exact
historical compiler-produced table bytes are not established by that alone.

| Unit | Original method | Current port | Compatibility / disposition |
| --- | --- | --- | --- |
| Table setup | WL_MAIN.C BuildTables:900 int32 tangent entries, half-bin i+0.5, tangent/reciprocal paired entries, fixed-point truncation; FINEANGLES3600 | Quarter sine table plus column angle offsets | Pure setup/data supported. Record exact original PI3.141592657 and float radtoint narrowing. Source-equivalent generation is not proof of historical Borland libm bytes.900 entries cost3600bytes before actual package/resource checks. |
| Quadrant setup | WL_DR_A.ASM entry90/180/270/360 selects signed xstep/ystep from the tangent table | sin/cos ray vector and up to two wide fixed_div calls per column | Integer operations/data supported by current module ABI. Carry method over; no new service or private import. Preserve normalization/index boundaries and original signed quadrant decisions. |
| First crossings | Original partial-tile distance multiplied by slope, then intercept setup | Distance-to-boundary parameters computed from reciprocal ray components | Pure integer supported. Original half-bin slopes differ numerically from current exact-angle sin/cos rays. This is an intentional original-method distinction to report, not a promise of byte-identical old geometry. |
| Grid traversal | Compare crossing tile coordinates in quadrant-dependent order, add slope on each crossed grid line | Compare accumulated side-distance parameters | Supported. Port actual original tie/order rules, not a new guessed geometric DDA. Original map[x][y] binds to existing row-major map[y*64+x]; no world-wire change. |
| Ordinary wall hit | Original hit-side coordinate correction then CalcHeight and texture selection | Reconstruct intercept from traveled distance and ray vector | Supported compute/data boundary; exact negative-step adjustment and texture orientation must be cross-checked against HitVertWall/HitHorizWall before candidate code. Keep existing projection/view constants and compositor outside this unit. |
| Door hit | Add half xstep/ystep, reject if intersection leaves tile; original aperture comparison | Additional fixed_div against door plane, then fraction <= position rejection | Supported operations. Equality differs (original continues only for fraction < position); record original behavior rather than silently inheriting a port predicate. Door tile/orientation/index binding and jamb selection require explicit source disposition. |
| Moving pushwall | Original flagged moving cell plus solid next-cell reservation; partial-step slope multiplication and Hit*PWall offset | Cleared active corridor plus separate slab-intersection ray cast using up to four wide divides | Original state topology differs. OPEN: prove mapping from WorldMirror status/current/origin/direction/position/completions to original logical cells and hit semantics before implementation. No analytic replacement/fallback or loss of active-pushwall support may be slipped in. |
| Arithmetic/safety | Original assembly word arithmetic and signed-high-word comparisons | Defined widened fixed multiply, local64-step divider, O2/safe SDK | Pure arithmetic is available, but literal C++ signed overflow/negative shifts are not an acceptable translation. Close domains and explicit integer behavior. Keep providers unchanged; eliminating ray-walk calls is distinct from replacing their provider. |
| Visibility/painter | Original spotvis/post batching and sprite methods belong to other units | Existing sprite/texture grouping/output machinery | Not selected here; retain current behavior and explicitly limit the original-method claim to reviewed ray-walk/intersection units. |

Source compatibility is not output/performance qualification. Original-method
checks need independently derived crossing/intersection expectations, quadrant/
cardinal/corner/grid-boundary cases, near-axis and map bounds, both door
orientations/aperture boundaries/jambs, moving pushwalls in four directions and
completion states. Existing old-renderer output is a useful difference report,
not an oracle that can reject every intended restoration of original rounding.
Retain guards, world immutability, asset leases, page/sync masks, inactive page,
HUD/weapon/sprite ordering and all failure-path checks independently.

Pre-code implementation gate is presently OPEN on moving-wall state binding,
negative hit adjustment/texture orientation and defined arithmetic domains.
Resolve from exact original/current source or ask for a concrete disposition;
do not substitute a newly invented method. No production candidate code has
been changed by this initial inventory. This corrects the earlier review's
failure to account for the original algorithm, not just the bespoke→module gap.
