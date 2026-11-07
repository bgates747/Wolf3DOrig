# Remaining candidates — source dispositions during bench preparation

Independent baselinea926; all later candidates remain separate arms unless an
explicit combination is qualified. VDPlet source advice
is retained at agon-vdplet/docs/tasks/VDPL-034/WOLF-ADVICE-2026-11-07.md (WAD001–003).
These are offline dispositions, not performance measurements.

| Candidate | Current evidence | Disposition |
| --- | --- | --- |
| Sprite-column decisions | LIN-F003; independent68704cases/whole output/actual producer gates pass | First finite physical candidate PERF013. Setup/storage overhead may outweigh savings; measure room and sprite-rich cases. |
| Texture-group scans | draw_walls discovers needed IDs then scans256columns per needed texture, recalculating wall_texture_id | Next local candidate: cache per-column ID once, retain exact acquisition order/column order/error behavior and metadata. Inspect actual code and bounded local storage first. Potential gain is smaller than pixel filling; no speed estimate from source. |
| Library division | WAD002 confirms no admitted libgcc-only alternative; final44allocated .eh_frame bytes correctly rejected | Dependency unresolved. Do not strip metadata or relax SDK/runtime guards. No blind rebuild. Original ray restoration removed former512axis-division count; current wide projection is in transform_point, not every wall ray. Provider impact should be ranked on current inputs. |
| Full sine table | kWolfSinQuarter[901] is int32,3604B; full3600entry table14400B adds10796B to current13348resident data =>24144B, over16384limit | Reject this literal full-table arm under current policy before build. sin/cos are evaluated in setup_view twice per frame, not per wall column; little plausible payoff for a substantial data increase. A different representation needs its own numerical/footprint disposition. setup_view uses integer degrees multiplied by10: a360-entry table of the exact existing degree samples could instead save2164B (3604→1440) while preserving both call sites; investigate separately after current arm. |
| Original wall-post reuse/generated scaling | Original WL_DRAW.C HitVertWall/HitHorizWall copies previous height when widening a post | Exact literal restoration can change output/geometry; do not slip it into an output-identical hoist. Conservative same-height/same-texture-column grouping is a distinct possible future method with pixel/metadata/resource proof; harder and uncertain payoff. Original x86 generated scalers also have explicit cached-CPU caveats in the audited source. |
| Presentation cadence | WAD003 traces nominal60Hz mode136, queued C3 swap/notification; ordered CA drain is not unconditional extraVBlank | 33/34ms uncapped cadence is consistent with missing alternate16.7ms slots; cause/timing shares remain unproved. Preserve C3/fence/accounting. No automatic VSYNC bypass, drain removal or firmware axis. |

The full-table rejection disposes only the literal3600entry int32 expansion;
it does not close every possible trig or post-scaling investigation. Arithmetic,
stack and presentation observations cannot substitute for end-to-end uncapped
completed-frame results.

## Reached milestones after this initial ranking

The table above preserves the original selection rationale. Current evidence
advances several items without changing their scope:

- PERF013 sprite hoisting completed actual78. Native draw differences were
  small and scene-dependent with unchanged presented rate. Smith explicitly
  reopened its resource-value decision in PERF013/REVISIT.md; retain the source
  and results for that discussion, without automatic rejection or adoption.
- PERF014's ID cache and PERF015's exact360-degree representation pass source,
  independent host/600-pose and target/real-producer qualification. H02/actual84
  stopped on host SIGTERM before first room LOAD/RUN. They remain unmeasured
  physically; no result or retry is implied by the successful preparation.
- PERF016's cyan-clear extent correction completed actual81:13.7% lower pooled
  inclusive draw, unchanged ~30.06fps; +84B. It retains a useful measured result
  despite the presentation threshold.
- PERF017's guarded local32-bit helper completed actual85:2.125% lower pooled
  draw with3.111% control drift, unchanged ~30.06fps; +4B. This qualifies the
  local subset/fallback arm, not a generic libgcc-only provider. The44B allocated
  metadata guard remains blocked and was not relaxed.
- PERF018 caches identical full-height scaling setup while keeping scalar
  texture/pixel order.5376 scalar/alias cases,600-pose parity, target/producers
  and73.85% canonical-room host setup-reuse count pass; +60B. Hardware package
  completed actual87: no established gain (+0.438% pooled draw against3.134%
  control drift), unchanged ~30.06fps; retained qualified arm, exact restoration
  and normal release. See PERF018/RESULT87.md.
- PERF019 is a separately frozen true membership-scan reduction: ascending
  per-ID column chains, retaining original scalar order and leases. This goes
  beyond PERF014's cached ID resolution; nominal local storage adds384B.
  6272 scalar/alias cases,600-pose parity, target/producers and canonical-room
  work count pass; +172B package, selected task path1936B. No physical timing
  yet; a separate six-case contract now selects chains and exact-degree015
  with shared controls, normal Mech-first scheduling and fresh admission.
- Presentation analysis now includes4792 existing steady intervals. Render
  reply arrives23–30 nominal guest ms after the previous completed presentation,
  already beyond one nominal60Hz interval before C3. This is a sequential-path
  budget limit, not proof of an extra VBlank, hidden cap or exclusive CPU time.
  Keep PRESENTATION-SOURCE.md's timing, source and observer limits intact.

No optimization is combined into the production default by these milestones.
Original post-height replacement, fractional/generated scaler and row-major
aliasing boundaries remain in WALL-POST-DESIGN.md; arithmetic caching and column
chains do not silently restore those incompatible original methods.

PERF020 source gate resolves supported conditional byte-span logic but defers
implementation for the canonical room: only4.392% potential wall texture-read
reduction, no pixel-store reduction, largest identical run3, additional admission
work and unknown native strict-layout applicability. No measured speed verdict;
retain near-wall/larger-viewport follow-up. See PERF020/CENSUS-RESULT.md.
