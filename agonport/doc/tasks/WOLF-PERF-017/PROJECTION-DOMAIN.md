# Source bound for the current projection helper call

Source argument, not a native counter or timing result. Applies to the current
validated WorldMirror path: player and actor coordinates pass valid_position,
0 <= value <64*65536; static tile coordinates are below64. Accepted player
angles are below360. The retained901-entry sine table has exact range0..65536;
sign/quadrant lookup therefore bounds each sine/cosine by65536 in magnitude.

Let M=64*65536=4194304 and F=0x5700=22272. setup_view offsets the validated
player by fixed_mul(F, cosine/sine), so each camera axis lies between -F and
M-1+F. A validated projected object coordinate lies inside0..M-1 (static tile
centres are a narrower subset). Thus |gx|,|gy| <=G=M-1+F=4216575.

Existing fixed_mul(a,b) is floor(a*b/65536) on this pinned implementation.
With integer |a|<=G and |b|<=65536, every product result lies in[-G,G].
Consequently |trans_y| <=2G=8433150 and |trans_x| <=2G+0x4000=8449534,
including the existing actor-size subtraction. All intermediates fit int32;
the existing widened products fit int64. Preserve widening in candidate code.

Only trans_x >=0x5800 reaches the signed64 division. Therefore the denominator
is positive and at most8449534. The numerator magnitude |int64(trans_y)*87|
is at most **733684050**, below2^32. After the unchanged signed wrapper forms
unsigned magnitudes, **both high words are zero for every such validated
projection call**, so PERF017's guarded unsigned32 subset applies. The generic
helper's wider-domain fallback/exceptional behavior still must remain intact.
Height projection subsequently uses a distinct32-bit division; do not count it
as another avoided64-iteration helper call.

This bound covers accepted coordinate domains, not arbitrary corrupt mirrors,
new future map extents/providers, arbitrary whole-helper inputs, or a change in
fixed-point/table/camera arithmetic. The separate retained-room/eight-static
host diagnostic checks actual input populations and exact helper output on
these poses; it will supply observed counts/ranges, not prove native branch
hit timing. Final ELF long-call/relative-literal joins support native use;
physical common-input execution/timing remains a separate selected cohort.

VDPlet independently confirmed this source bound and pinned-compiler rounding
limits in PRJ-001 of the [source advice](../WOLF-GOAL-001/results/source-advice-07/WOLF-PROJECTION-POST-ADVICE-2026-11-07.md). No native branch count or measured gain follows.
