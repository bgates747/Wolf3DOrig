# Wolf3DOrig TODO

This is the project's single authoritative list of intentionally promoted,
unfinished work. IDs are stable references and are not reused. When an item is
accepted, rejected, or superseded, record its ID, evidence, and rationale in
the current dated development log, then remove it from this file.

[ ] 2c. Present the original-style floor-completion intermission before each
ordinary or secret floor transition, using the bundled level-end artwork and
the completed floor's authoritative time, kill, secret, and treasure state.
Draw it immediately, begin loading the destination without an acknowledgment
pause, and use finalized-asset callbacks to animate/poll input while loading.
An acknowledgment may be latched during loading; Escape must instead converge
on the common clean application-exit path from every shell, load, intermission,
and gameplay phase.

[ ] 3b. Add the reserved Agon-specific splash and presentation hook without
changing the accepted original-facing startup flow.

[ ] 4. Widen or remap the byte-sized actor-state dispatcher before importing
the remaining original actor states, avoiding the current 254-ID ceiling.

[ ] 5. Implement bosses, projectiles, ghosts, and other special actor
behaviors from the original game.

[ ] 6. Implement music playback as a separate subsystem from the accepted
sound-effects implementation.

[ ] 7. Add high-score entry and remaining presentation polish after the core
game progression is established.

[ ] 8. Replace the requirement for a dedicated Wolf3D VDP firmware with a
loadable Wolf3D VDPlet running on the shared VDPlet runtime. The completed
feasibility study is a conditional go. Under GOLEM-057, implement and qualify
only the released bounded proof: one real freestanding module, compact mirror,
representative static DDA/sprite scene, application-owned full-frame workspace,
generic pixel publication, requested completion, and orderly teardown. Preserve
the standalone renderer as the exact oracle and rollback path. The bounded
host, pinned Oryx target proof, full-MOS headless rehearsals, bounded
error/recovery matrices, and human visual/keyboard reviews passed on
2026-10-30 for both the copied-pixel proof and the optional ABI 1.6
direct-colour-row proof. Both returned cleanly to MOS and accepted `dir` after
unload. The direct-row proof preserves exact pixels while reducing caller
workspace by 80,608 bytes (87.47%), at a measured cost of about 32.93% more
modeled RENDER transaction cycles in the bounded scene. This emulator evidence
does not imply physical acceptance or establish a production winner. The full
eZ80 production-client lifecycle also passed generation 35 with exact scene,
teardown and MOS-return evidence. Its readable Author review passed on
2026-10-31: the oracle scene rendered correctly, Enter requested orderly
unload, MOS returned to a live prompt, `dir` worked, and the exact result hash
matched. Gameplay integration, update batching, fizzle migration, default
cutover, and physical qualification remain later gated work. See
`agonport/doc/wolf3d-vdplet-migration.md`.

[ ] 8e. Replace the bounded static scene with the production render contract.
Schema 1, synchronized C++/assembly constants, the 5,360-byte compact mirror,
validated atomic full/dirty batches, complete pure renderer, real ABI 1.3
CONFIG/APPLY_AND_RENDER/RESET wrapper, host lifecycle/retry matrix, and linked
Xtensa package admission are complete. The exact package also passes its real
runtime-emulator gate with two oracle-exact frames, native error/retry,
INFO17, timing, teardown, stale-handle, reload, and empty-slot evidence. Next
The production eZ80 descriptor/full/dirty serializer now also passes its direct
MOS target regression: byte-identical frozen retry, in-flight dirty-state
preservation, exact generation-2 delta, dirty consumption, and empty-batch
refusal. Next connect CONFIG, update-buffer upload, requested RUN completion,
C3 presentation, and exact retry to the app's existing one-in-flight render
handoff while retaining the standalone default. App-paced fizzle, complete
human/performance/physical gates, default cutover, and removal of the standalone
rollback path remain later work. The first Console8 run under stock MOS Arthur
loaded the complete level/assets but returned to MOS before the first frame;
the same exact cohort was playable in Flexe. A no-protocol-change diagnostic
build now reports the failing startup stage, client status, native reply value,
and callback-overlap flag. Obtain that physical diagnostic before changing the
runtime, firmware, timeout, transport, or renderer.

[ ] 8f. Diagnose and resolve the severe gameplay-audio latency observed during
the generation-64 production-VDPlet review. Preserve the accepted application,
module, assets, firmware, sample data, rates, mixer behavior, renderer pacing,
and queue policy while measuring the delay chain before proposing a repair.
Flexe preparation is limited to the accepted ten-host-second, 8,192-event,
one-MiB host-ring range observer derived from the exact production backend. It
may measure producer-enqueue to real-sample dequeue residence, ring depth,
fill, and existing drops; it cannot establish gameplay-event, parser, mixer,
SDL-device, DAC, or speaker latency. Require pinned provenance, unchanged-PCM
and forwarding tests, finite stopped-profile staging, one manually reviewed
session if later authorized, and a separate human hardware comparison before
assigning a cause or changing behavior.
The isolated generation-64 consumer profile, exact pins, real-PulseAudio finite
runner, structural gameplay oracle, stopped staging receipt, and no-launch
checks are now ready under `agonport/vdplet/audio-ring/`. The reviewed-but-never-
run `r01` preparation was superseded after finite-supervision defects were found;
fresh `r02` bounds capture acceptance, final-file waits, reader execution, and
owned TERM/KILL cleanup inside the whole-session ceiling. Eleven device-free
tests pass, including real timeout and process-group cleanup cases. No diagnostic
session had run at preparation time. The subsequently selected single generation-
71 run completed normally and found a stable 5,065–5,543-sample backlog. Its
158,563 fully observed samples had a 325.774095–325.774559 ms bounded mean
extracted-U8 enqueue-to-dequeue residence; 5,277 samples at each window edge
retain unknown censored ages. No fills or drops occurred in the recorded window.
This identifies a substantial host-ring component,
not shot identity or command/parser/mixer/device/speaker latency. Coordinate the
next diagnosis or repair tranche before changing queue policy or audio behavior.
The generation-71 record also carries a separate observer-initialization
publication-race limitation; it cannot establish how the preserved backlog
formed. A race-fixed backend and fresh SETUP+0..10-second STARTUP profile are now
staged and stopped under `agonport/vdplet/audio-ring-startup/`. Its eligibility
requires a first-row empty-ring witness and expected shot non-overlap while
retaining all functional and cleanup gates. No startup capture or repeat has
been selected.
The subsequently selected single generation-75 startup run qualified and began
with zero production/depth. Its 155,702 known samples averaged
19.286677–19.287097 ms residence with maximum depth 529 samples; 8,171 fill
samples documented intermittent startup underflow, and no drops occurred. The
late 5K-sample bank was not present in this run's first ten seconds. This does
not locate its later formation or justify pooling the two runs as a matched
comparison. Coordinate the next source discriminator before another run or fix.
A Pi-only corrected late-window preparation is now ready under
`agonport/vdplet/audio-ring-late-corrected/`. It selects backend `943f...` with
the exact accepted original late runner/oracle and SETUP+90..100-second overlap
semantics; seven device-free checks pass. No target profile, Oryx contact,
staging, build, reservation, emulator, audio device, or run occurred. Await
central review before any target action.
The later selected generation-78 invocation produced no measurement: the exact
old runner expected `PROFILE/ring-output`, while the fresh profile created only
`ring-output-late-corrected`. It failed before emulator/audio startup and Oryx
was released cleanly without retry. Any path correction and successor require a
new central selection.

[ ] 8g. Replace production Wolf3D's copied full-frame publication with true
ABI 1.6 scoped direct-row rendering. The current production module composes a
76,800-byte RGB222 workspace frame, validates the whole source, and then copies
it through `pixels_write`; this is not the intended zero-copy framebuffer
optimization. Migrate the complete production renderer—not merely the bounded
proof scene—to `BEGIN / ROW / END` access to the hidden native drawing surface.
Write each final background, wall, sprite, weapon, and HUD pixel directly to
its native scanline while retaining only necessary mirror, DDA, depth, texture,
and sprite scratch state. Preserve native lane ordering and sync bits, bound
all row access, discard every row pointer before ending the surface lease or
swapping, and never publish a partial frame after any render or asset failure.
Keep the existing copied path only as an explicitly named diagnostic/fallback
until parity and rollback requirements are settled. Add exact host regressions
for complete-frame pixel parity, lease/failure cleanup, hidden-buffer selection,
no-partial-publication behavior, and repeated-frame operation. Benchmark the
same production fixture across copied workspace + `pixels_write`, true direct
rows, and any already-real bitmap baseline using complete render/presentation
boundaries; report workspace and speed separately, and presume no benefit until
measured. Finish with stopped emulator staging and explicit human visual review
of the formerly observed flickering black-pixel corruption before physical or
default-cutover claims.
