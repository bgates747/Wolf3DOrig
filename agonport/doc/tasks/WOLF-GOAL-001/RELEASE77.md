# Actual77 clean release

Smith’s newer overnight instruction selects MechAgon first and Wolf second,
unattended tests, and no Oryx execution. The idle HOLD77 ended by normal release
at **2026-11-07 09:30:16.578007 UTC**. The old token is invalid; the registry
reported no next request at release. Both MechAgon and Extender received immediate
actual-release notifications after the earlier verbatim priority update.

The accepted paced/uncapped raw results remain unchanged. The exact incoming
1105920-byte native/tail restoration and independent readback from the same
custody remain verified; no firmware or guest operation intervened. Fresh
SAVE-only mode0/callback0/Legacy0, whole startup/listener reads, root CLI/input,
offline listener/worker idle and both USB ports passed. No new LOAD/RUN/reset/
flash occurred during release. All Wolf actors stopped; SD remains mounted.

Receipts: [release](results/release77/released77.json),
[fresh observation](results/release77/observation.json).
The larger raw CLI/file/state receipt set remains in build/release77/.
Wolf has no hardware access until a new actual scheduler grant and handoff.
