# Whole-degree setup callers and exact representation boundary

Frozen a926 control stays independent of sprite972f, cyan22ef and cache8c126c;
none of those changes are silently combined. Source pins include the full
original wolf3d_tables.inc, renderer copies, native providers and module.

All sine/cosine callers in this renderer are setup_view: player.angle is uint16,
converted to int32 and multiplied by10; sin_fine normalizes modulo3600 and uses
the901-entry quarter table, cos_fine calls it with+900. Maximum original fine
input656250 fits int32. All65536 uint16 angles must agree, even though normal
wire input is canonical degrees. View.x/y retain exact fixed_mul, focal and
sign/rounding behavior, including arbitrary selected player positions.

**normalize_fine is also used by the original ray walk. Keep it.** The new
whole-degree setup lookup replaces only sin_fine/cos_fine and their two setup
calls. No other fine angle, tangent, pixel-angle or ray table changes. Generate
360 exact signed int32 samples from the retained quarter reconstruction, no
floating point or new angle quantization. Degree index is angle%360; cosine
index(degree+90)%360 uses wide arithmetic before any narrowing.

Supported ordinary scalar lookup, no runtime/SDK/compiler/provider change.
Potential2164B resident-data saving is a hypothesis until actual ELF sections
and absent quarter-table symbol prove it. Reproduce exact control first; retain
an independent original-quarter reconstruction oracle across all65536 angles
plus complete renderer/module outputs. Two lookups/frame are unlikely to move
FPS much. Current controller/bench016 remains untouched; Mech first, no Oryx.
