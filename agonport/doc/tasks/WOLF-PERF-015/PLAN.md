# WOLF-PERF-015 — Exact whole-degree view trig representation

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

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
