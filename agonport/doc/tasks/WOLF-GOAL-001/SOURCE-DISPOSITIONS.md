# Remaining candidates — source dispositions during bench preparation

Current baselinea926, candidate972f changes sprites only. VDPlet source advice
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
