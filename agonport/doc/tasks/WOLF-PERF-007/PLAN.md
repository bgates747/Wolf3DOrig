# WOLF-PERF-007 — Restore the original table-driven ray walk

Smith's direct correction on2026-11-06 selects the original method: "carmack
was a genius. do what he does." The annotated issue is the bespoke port's
replacement of original precomputed tangent/intercept stepping by per-ray
fixed-point divisions. This task takes priority over PERF006-P02 division-
provider tuning. It is not permission to change every rendering subsystem.

The fixed view/projection scale87, pixel-angle table, world wire format, renderer
publication/row ownership/masks, span/background improvements, HUD/weapon/sprite
ordering and local arithmetic provider remain controls. Original ray-bin and
intersection behavior must be identified separately from those controls.
No SDK/firmware extension, ROM import, fastmath, safety relaxation, async renderer,
new carrier or general division-provider change is selected here.

Pi compilation is serial through normal actual checkout with finite child,
80C/512MiB guards and joined-owned cleanup. Emulator work, if needed for visual
qualification, uses Oryx actual checkout, boost off and the existing80C guard;
no Pi emulator diversion. Exact fixture/run selection, source/output/producer/
resource freeze and current component admission precede physical dispatch.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
