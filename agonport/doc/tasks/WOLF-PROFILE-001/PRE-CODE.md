# Profiling implementation selection

Normal maintained client: `src/asm/wolf3d/src`, built through its existing
disposable-source `scripts/build.py`. Add `--profile` (eZ80 observations) and
`--profile-native` (also collect the explicitly pinned WPN1 module log).
Tracked defaults remain off. Hooks compile to zero bytes when disabled; compare
both disabled backend binaries against pre-change builds under the build FIFO.

The supported native reference is the fastest completely measured combined021
module22572B/SHA8d3d19bb74e1f2ea862b2154c038dfd23de2fd741fd1831d1880d849b5ad838b.
Its existing optional diagnostic uses buffer F000, WPN1 header16B, capacity602
records of20B, reset RUN100 and documented READ16. Bind this exact interface and
package identity rather than modifying generic firmware or pretending ordinary
modules expose timing. Read and reset only after a completed render/idle owner.
No new worker, loader policy, runtime service, renderer algorithm or ordinary
default adoption. Native collection gaps count as profiling overhead.

Use the retained nominal1ms PRT0 donor (72-count reload, /256 at18.432MHz), only
when its control register shows it inactive. Preserve selector/vector/control
and restore on final exit. Never steal an active timer; disable profiling with
an explicit status if unavailable. ISR only increments a24-bit counter. This
clock has1ms resolution and wraps modulo2^24; configured clocks remain nominal,
and interrupt masking/overload may delay/coalesce ticks. Do not claim calibration.

Fixed64B records, capacity128, flush after120 completed renders or5nominal
seconds at the next eligible normal completed-frame boundary. Record frame ID,
prepare/submitted/callback/consumed/present/fence timestamps, maximum input
service gap, cumulative measured foreground simulation cost/steps, purpose,
pose, optional native render/scope/dispatch cycles and explicit validity flags.
Failure/partial records cannot be counted as completed frames. One in-flight
record is stable; input/physics aggregate counters can continue independently.

Profiling observes existing simulation scheduling; no quantum/rate change.
Foreground hooks preserve registers/flags. IRQ hook only snapshots a timer
value after routing the existing reply; it performs no MOS/VDU/disk operation.
The extra ordered fence and timer/record overhead belong to the instrumented
build and are not claimed free or subtracted as an assumed constant.

Flush only at a supported frame/idle boundary. Overlay an opaque24x32 disk
bitmap at the existing BJ portrait rectangle (136,204), on the already finished
hidden page BEFORE its ordinary C3. Fence the swap before retrieval/write.
Exclude cue/collection/write intervals from throughput windows while preserving
them as logging gaps and retaining real wall-time accounting. Force a later
ordinary render so both HUD pages are reconstructed from current game state;
never patch the scanned-out page or restore a stale saved expression.
Do not intercept fizzle, death-target synchronization or other special frame
ownership to flash a cue. Their pending samples may wait for a safe boundary.

Batch file format has explicit magic/version/record-size/count/length metadata
and logging gap timestamps. Check actual MOS fwrite byte counts, close each
batch, fail visibly/disable recording on disk error without retry loops, retain
uncertain/truncated tails for decoder diagnostics. Existing save/config files
are untouched; a profiling run uses its dedicated file in the game's directory.
Final safe shutdown drains remaining complete records; unsafe ownership records
are retained in RAM and explicitly reported rather than issuing a new query.

Qualification: serial Pi compiler lease; baseline two-backend assembly, then
profile off/on/native real assembly/listing checks, decoder malformed/truncated/
wrap/gap tests and actual-source error/ownership qualification. Ordinary compiler
checks finite10minutes, no emulator launched from the Pi build queue. A separate
finite Oryx correctness plan will exercise disk cue, flushes, normal gameplay and
exit with exact current emulators/firmware; hardware timing is not inferred from
that. Any missing supported method is recorded before selecting an alternative.
