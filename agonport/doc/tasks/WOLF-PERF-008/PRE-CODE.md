# Pre-code support and work ledger

| Unit | Original / bespoke method | Current c8f candidate | Selected disposition |
| --- | --- | --- | --- |
| Ray traversal | Original precomputed tangent/intercept walk | Restored by PERF007 | Fixed; its former wide fixed_div callers are gone. Earlier divider domain reports describe older code, not current caller counts. |
| Sprite projection | Bespoke widens trans_y*87 and divides by trans_x | Same one wide signed division expression in transform_point, reached for actors/statics after depth rejection | Preserve expression, truncation and narrowing. Remaining cost is scene dependent; no assertion of another per-ray saving. |
| Division provider | Bespoke historical ELF binds ESP32 ROM helper; original x86 uses its target's arithmetic | Local freestanding fixed 64-iteration unsigned divider wrapped for signed division | Assess existing toolchain provider through supported SDK math option. No ROM-address import or new algorithm substitution. |
| Library selection | Target/toolchain dependent | SDK already supports math=True linking pinned libm/libgcc with PSRAM workaround | Available route. Only needed archive members should be pulled; inspect actual map, do not presume both libraries add runtime work. |
| Section admission | Runtime admits named allocated sections only | Raw libgcc divdi3 object includes 40 allocated .eh_frame bytes | OPEN final-link gate. Existing garbage collection may or may not eliminate metadata. Stop on unsupported final ELF; no workaround. |
| Output / resources | Existing scoped native rows and ordered painter | Original-ray-walk c8f renderer, helpers and O2 source | All geometry, texture/masks, row leases, order, viewport, wire data and observer remain fixed. No new helper API or scratch requirement. |

Source compatibility permits the existing library build attempt; it does not
qualify its resulting ELF or arithmetic execution. VDPlet VDPL033 OBS-003 and
SUPPORT-PROVIDER-REVIEW pin the actual esp32-psram archive and divdi3 object.
VDPL034 LIN-F002 recommends final dependency closure rather than inferring speed
from C++ source. The old fixed_div domain ledger must not be relabeled as the
current transform_point domain proof. Division-by-zero is unreachable at this
caller after trans_x>=kMinDist. The widened signed product fits int64 for every
int32 trans_y and constant87; quotient narrowing remains the retained target
policy. Full provider corner behavior and whole-call-stack remain later gates.
