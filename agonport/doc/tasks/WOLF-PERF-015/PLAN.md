# WOLF-PERF-015 — Exact whole-degree view trig representation

Lower-priority follow-up under WOLF-GOAL-001, after easier sprite/grouping arms.
Contract before code; no change to the active PERF013/78 cohort. Oryx down,
MechAgon first/Wolf second, normal Pi compiler and actual Olimex checkout.

- [x] WOLF-PERF-015-01 — Pin the selected predecessor after its disposition;
  verify every sine/cosine caller and angle domain before representation change.
- [x] WOLF-PERF-015-02 — Generate360 exact degree samples from the existing
 901-entry int32 quarter table; use them only for setup_view’s degree domain.
- [x] WOLF-PERF-015-03 — Prove exact view results across all65536uint16 player
  angles and full renderer/module/600pose output/state equality. Preserve original
  fine-angle table reference/oracle independently; actual ELF must establish that
  unused original quarter storage is absent before claiming footprint savings.
- [ ] WOLF-PERF-015-04 — Qualify actual native flags/providers/sections/stack/
  resource/package/guest identities; freeze a finite uncapped matched cohort if
  the reached candidate is useful. No assumed timing win from two lookups/frame.
- [ ] WOLF-PERF-015-05 — Normal fresh gap grant, first fault stop, RAM beforeLOAD,
  exact restoration/readback/fullcleanup/release and actual-next notice.
- [ ] WOLF-PERF-015-06 — Publish positive/negative timing and footprint result;
  no hidden geometry correction/default adoption or changed ray stepping.

PRE-CODE: current setup_view multiplies uint16 player.angle by10, then calls
sin_fine and cos_fine(+900). These are the only renderer sine/cosine call sites.
The projected view therefore needs integer-degree samples, although the original
ray walk’s fine tangent/pixel-angle data remains essential and unchanged.
Current quarter table901×4=3604B;360degree samples×4=1440B could save2164B.
This is a distinct supported scalar-table representation; literal3600-entry
int32 expansion was rejected on data fit. No floating-point regeneration,
rounding/projection correction, compressed approximation, SDK service or provider
change. All values must derive exactly from the existing quarter reconstruction.

Check the full uint16 source domain, not just360canonical wire angles: existing
normalization of angle*10 and cosine offset must produce identical signs and
quadrant endpoints. Keep private fine-angle helpers/reference as needed for an
independent oracle; do not assume the compiler removes unused tables. Two setup
calls/frame make CPU payoff likely small; footprint may be the useful outcome.
