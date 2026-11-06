# p02: asset-loading timeout; no paired timing result

Standing boost0 baseline, actual Oryx310/request73c5f3a83eec. First A CPU
case hit its original 300s guest/MOS-return timeout (whole process300.232s),
while loading sfx.agnb before wp_run and PRT/native measurement. Remaining11
cases NOT RUN. No performance comparison, thermal-repair or transport-repair
claim. All8earlier q03 functional passes remain their separate baseline.

Host guards:301samples, initial58.375C, peak61.25C, final58.625C;
ample memory throughout, no80C violation. Boost0 preserved. The local controller
also terminated unexpectedly with143 before the remote deadline; this cause is
unknown. Inspection found only our remote bounded runner and emulator still
active. The original runner reached its300s bound, ordinary Quit/join completed,
and all identified owned PIDs were gone. No next case/retry was launched.

Retained23retrieval hashes verify. Raw stats:1,196,980request bytes,
340reply bytes/delivered, zero backend failed/unhandled/unregistered/unmapped.
TX comparison with successful s02/q03 A CPU is NOT an exact whole-prefix match:
first difference at386, so do not reuse the earlier exact-prefix conclusion.
Native/guest/source/artifact inputs unchanged. No observer enabled.

Fresh whole-host idle and actual release19:45:29UTC,nextnull. Raw evidence and
machine-readable disposition:build/p02/oryx and build/p02/disposition.json.
Original upload stalls remain unresolved; no automatic replay selected.
