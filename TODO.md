# Wolf3DOrig TODO

This is the project's single authoritative list of intentionally promoted,
unfinished work. IDs are stable references and are not reused. When an item is
accepted, rejected, or superseded, record its ID, evidence, and rationale in
the current dated development log, then remove it from this file.

# Phase A — original Episode 1 shareware parity

[ ] 11. Implement original pushwalls and secret discovery: preserve/count
plane-1 marker 98 in W3L packages; prioritize facing-adjacent pushwalls in Use;
reproduce busy/blocked rejection, cardinal fractional motion through at most
two cells, collision/DDA ownership changes, sounds, secret count, and complete
attempt/level reset. Implementation, host tests, 28-case direct-eZ80 behavior,
schema-2 serialization, and all four directions are complete. Remaining close
gate: accept the staged real E1L1 secret-wall visual/collision review and, when
practical, repeat it on hardware.

[ ] 12. Complete `WL_INTER.C::LevelCompleted` behavior atop the accepted
nonblocking transition lifecycle: visible time/ratio count-up, skip-to-final,
500-point par seconds, 10,000-point 100% awards, the secret-floor 15,000-point
award, original tally sounds, final score/life effects, and persistent
per-floor `LevelRatios`. Escape must retain priority while destination loading
and presentation overlap. Implementation and the 135-check intermission plus
32-case score regressions pass on the direct target. The original non-digitized
`LEVELDONE`, count tick, stage-complete, zero-ratio, and perfect-ratio sounds
are rendered offline from their authentic PC-speaker streams; the production
audio target passes 287 checks. Remaining close gate:
accept staged ordinary
count-up/skip/next-floor and secret-floor score presentation.

[ ] 13. Replace the generic Episode 1 victory acknowledgment with the original
shareware path: in-world victory/BJ sequence, total time and eight-floor ratio
averages, Episode 1 ending/shareware text, acknowledgment, high-score handoff,
and shell return. Paid-episode death cameras/endings are out of scope. The BJ
state graph, totals arithmetic, shareware-text handoff, and target regression
are complete. Remaining close gate: staged visual acceptance of the complete
E1L9 sequence and return to the shell.

[ ] 7. Implement the original seven-entry high-score table, qualification and
name entry, score/floor display, control-panel view, game-over/victory handoff,
and a versioned, corruption-safe Agon persistence file. The table, ordering,
name editor, timed non-qualifying path, screen, handoffs, and transactional
482-byte persistence image pass 62/62 direct-target checks. Remaining close
gate: visual acceptance of qualifying and non-qualifying flows. Two disposable
acceptance builds now enter those exact production paths immediately after the
real shell/SFX bootstrap, supplying only a guaranteed candidate score; they
are prepared locally and await the next Oryx batch.

[ ] 14. Restore the original in-game control-panel and pause flow in place of
temporary gameplay-Escape-to-MOS behavior. Support resume, end game, and an
explicit clean Quit to MOS while preserving the common asynchronous Escape,
mode-restoration, and VDPlet-teardown guarantees. The in-game panel, source
row substitutions, resume, confirmed End Game, New Game, and clean Quit paths
pass their direct shell fixture. The residual `WL_PLAY.C::CheckKeys` /
`WL_MENU.C::CP_CheckQuick` routes are now implemented for F1 help, F2/F3
save/load, F4 sound, F5 view, F6 controls, F7 end game, F8/F9 remembered-slot
quick save/load, and F10 quit. The callback-only FabGL Pause key now reproduces
`CheckPause`: authentic PAUSED art over the drained gameplay frame, music
off, fresh-key acknowledgment, floor-music resume, and authoritative buffer
rebuild. Direct production evidence passes 559/559 shell, 492/492
physical-keymap/player-combat, and 228/228 callback/death checks.
Remaining close gate: one batched visual pause/resume/page/save/load/end-game/
quit review, including callback-time F keys and F8/F9 reuse of the selected
slot. Remembered-slot F8/F9 now also reproduce the original transient
`Saving...` and named `Load Game called` surfaces; Oryx generation 177 passes
595/595 shell checks.

[ ] 15. Implement the ten-slot save/load menu and a versioned Agon save format
which reconstructs VDP state from complete authoritative eZ80 simulation state
and rejects truncated/incompatible files safely. The transactional state image,
exact-length ten-slot MOS wrapper, 32-byte descriptions, control-panel flow,
deferred canonical-level restore, and direct eZ80 corruption/round-trip fixture
are implemented. The image also preserves the original level-entry score
checkpoint used by death/restart, and rejects checksum-consistent tile maps
whose door references could escape the staged door table. All ten transactional
direct-target save-image cases pass. Remaining gates are staged visual
save/load and continuation checks during combat, doors,
pushwalls, floor transitions, and death.

[ ] 16. Complete the original-facing control-panel pages: Sound, Control,
Change View, Read This/help, View Scores/End Game state, and Back to Game.
Translate or visibly disable DOS-only choices rather than misrepresent them.
The exact ten-row source order, startup/in-game substitutions, local Escape,
in-game New Game, persistent SFX toggle, real key guide, fixed-view disclosure,
and ordinary control pages are implemented. A residual archive/source audit
corrected the stale claim that the concise resident Read This page was enough:
production now renders all 41 canonical `HELPART` pages from VGAGRAPH chunk
150 with the original font, frame art, embedded graphics, wrapping, colors,
and page numbers. `ShowArticle` navigation, CORNER music, local Escape, damaged
container fallback, and complete on-exit VDP-buffer reclamation are integrated;
the 2.6 MiB page container loads only while the article is open. Host contracts
pass and both application backends assemble. The expanded production-shell
fixture passes 683/683 on Oryx generation 185. Remaining close gate: visually
review the complete article plus the other control-panel pages in the next
batched Oryx lease.

[ ] 17. Implement the original attract loop—15-second title, 10-second
credits, 10-second high scores, and four deterministic Episode 1 demos—with
input entering the control panel and no persistent-state mutation. The three
source-timed pages, authentic credits art, input handoff, and live Back to Demo
row are implemented with direct-fixture coverage. Archive audit corrected the
stale loose-file assumption: the four canonical streams are Huffman-compressed
VGAGRAPH chunks 151-154, for maps 0/2/4/6. Deterministic extraction, generated
assembly assets, exact four-original-tic record cadence, button/weapon mapping,
local input abort, shell/gameplay lifecycle, magnitude-preserving analog motion,
and direct-target state fixtures are implemented and qualified. Remaining
close gate: a staged visual pass through all four demos, including local input
abort and return to the control panel.

[ ] 6. Implement music playback as a separate subsystem from the accepted
sound-effects implementation, preserving original Episode 1 title/menu,
floor, intermission, victory, and high-score assignments without coupling
simulation to playback. The canonical WL1 IMF streams are now extracted
deterministically, retimed cumulatively from 700 Hz to MOS's 120 Hz clock, and
played by a nonblocking nine-voice sequencer on VDP channels 3-11 while SFX
retain channels 0-2. Original title, menu, Read This, score, ten-floor,
intermission, victory, game-over, and return assignments are integrated;
Sound independently controls SFX and music preferences. The residual source
audit found that this persistence was process-local despite
`WL_MAIN.C::ReadConfig/WriteConfig`; item 18 now supplies durable cross-launch
persistence for the two meaningful Agon preferences.
The direct sequencer fixture passes 48/48 and the integrated production-shell
fixture passes 559/559 on real eZ80 emulation. Remaining close gate: one
audible emulator/hardware review of representative gameplay, menu,
intermission, and victory transitions, including timbre/mix and both toggles.

[ ] 18. Perform a source-linked, end-to-end Episode 1 residual parity sweep
after items 11-17 and 6: scoring, inventory, difficulty, actors, secrets,
transitions, death/game-over, menus, audio, and ending. Record every intentional
Agon difference and require emulator plus hardware acceptance. The sweep has
already corrected a silently static HUD face: production now reproduces
`WL_AGENT.C::UpdateFace`, including its shared `US_RndT` consumption, strict
threshold, three-frame selection, save persistence, and VDPlet wire byte. The
follow-up sweep also restored `GOTGATLINGPIC`: every chaingun pickup now sends
a dedicated wire sentinel, holds it for the generated duration of the selected
resident `GETGATLINGSND` sample, resumes the ordinary random face transition,
and cancels it immediately on damage or successful healing. The special state
is attempt-local, while the ordinary `faceframe` remains the saved value.
The residual sweep also restored `WL_PLAY.C`'s transient palette feedback:
successful pickups start the original three-level white flash, scaled damage
accumulates through the six red levels with red priority, and both counters
decay on the exact 2,2,3 source-tic cadence. Reserved HUD byte 11 carries the
effect schema-compatibly; the RGB222 VDPlet renderer preserves direct-row sync
bits and uses a 64-color lookup for the source palette formula. The same
end-to-end gate fixed the packaged module's stale rejection of face sentinel
3. Oryx generation 160 passes 549 player-combat/palette checks, all 32 pickup
cases, and byte-exact serialization; the six-scene renderer/oracle gate is
exact.
The same source pass corrected `WL_AGENT.C::GiveExtraMan`: every award now
requests `BONUS1UPSND`, including score awards and awards suppressed by the
nine-life cap. Full heal routes through that one owner so the Agon multi-stream
backend does not double the effect. Direct eZ80 coverage pins four thresholds
crossed in one score addition and the capped-life case; Oryx generation 163
passes all 33/33 pickup/state/sound records. Both application backends rebuild.
`WL_AGENT.C::Cmd_Use` no longer falls silent when no operable object is found:
ordinary walls, wrong-face elevators, malformed door references, and unmarked
walls request the source's `DONOTHINGSND` once per press. Its authentic 140 Hz
PC-speaker stream is rendered offline at 7 kHz. Oryx generations 164-165 pass
29/29 direct use/pushwall cases and all 287 production-audio checks.
The reachable `WL_MENU.C::HandleMenu` audio contract is restored as well:
cursor motion preserves `MOVEGUN1SND` -> eight source tics -> `MOVEGUN2SND`,
accept uses `SHOOTSND`, cancel uses `ESCPRESSEDSND`, and an unavailable paid
episode adds `NOWAYSND`. The four newly admitted effects use their authentic
AUDIOT PC-speaker streams. SFX are now loaded once beside the application-global
shell assets; gameplay teardown stops channels but preserves resident samples,
while final application shutdown clears them. The completed shell proof,
including SFX-off then SFX-on behavior, passes 526/526 checks on Oryx
generation 168; generation 167 passes 306/306 audio/lifecycle checks.
`WL_AGENT.C::ClipMove` now restores the missing `HITWALLSND` request whenever
the complete X/Y probe collides, including a successful X-only or Y-only
slide. Its authentic 57 ms PC-speaker stream uses a generated two-quantum
self-retrigger guard while Agon's independent sound channels remain available
to unrelated events. Oryx generation 169 passes all 10,030 production
ClipMove/sound/cooldown records; both application backends rebuild.
`WL_MAIN.C::ReadConfig/WriteConfig` also exposed a stale claim: the translated
Sound page retained SFX/music selections only until return to MOS. Production
now loads and saves a versioned, exact-length, Fletcher-guarded `wolf3d.cfg`
containing those two meaningful Agon preferences, with on/on fallback for
missing, truncated, trailing, corrupt, or future-version files. Unavailable
DOS devices, fixed Agon controls, and the accepted fixed viewport are not
serialized as fictitious choices. Oryx generation 170 passes all 30/30 direct
eZ80 format and real-MOS-file checks; both application backends rebuild.
The actor audit found and corrected a subtler deterministic-port artifact in
`WL_GAME.C::SetupGameLevel`: package generation had baked the seed-zero demo
actor phases and production reused them for every ordinary level entry and
death restart. Production now preserves that exact path for the four original
demos, but seeds ordinary play from MOS time and rebuilds every timed actor's
initial ticcount in the original row-major spawn order. Oryx generation 171
passes 618/618 direct eZ80 checks, pinning deterministic demos, ordinary seeded
starts, zero-duration states, and the resulting shared RNG position; both
application backends rebuild.
The shell audit then restored `WL_MENU.C::CP_Quit` and F10's randomized
confirmation instead of exiting immediately. Production consumes the same two
shared `US_RndT` bytes and preserves the source expression
`first & (7 + (second & 1))`, selecting all nine original humorous prompts.
Main-menu Escape, Quit, pause-menu Quit, and F10 now require Y/N confirmation;
F10 reproduces the source's 160-pixel control-panel window by shifting its
prompt twenty pixels upward. Episode cancellation now returns to its parent;
the follow-up audit restores Difficulty cancellation to the Episode page.
Oryx generation 172 passes
559/559 shell checks, including exact prompt selection/coordinates, Y/N/Escape
semantics, sound feedback, and exit-latch ownership; both application backends
rebuild.
The next source pass restored `CP_NewGame`'s in-progress-game warning and its
nested cancellation contract. The exact original `CURGAME` window appears
only from the in-game panel; cancel returns to that panel, accept enters
Difficulty, and cancelling Difficulty returns through Episode selection and
the warning again. F7's source `WindowH=160` prompt placement is now covered
separately. Oryx generation 175 passes all 581/581 production-shell checks;
both application backends rebuild.
The actor-visibility pass now restores the important persistent half of
`WL_DRAW.C::DrawScaleds`: at actual render-submission boundaries, a dormant
actor in a connected area is permanently promoted after its drawable center
passes the same CPU projection used by gameplay and an unobstructed
`CheckLine`. Sound, actor-facing sight, walls, behind-player actors, and
disconnected areas cannot cause false promotion. Oryx generation 178 passes
624/624 direct eZ80 checks and measures the deliberately pessimistic visible
case at 158 ms for 1,000 complete passes (0.158 ms per render boundary). Both
application backends rebuild. The follow-up closes the remaining source edge:
if the actor center fails, production now probes the eight bounded open
neighbors around its cached tile with the same projection and authoritative
wall/door trace, reproducing `spotvis` corner wake-up without VDP read-back.
Predicate order is adaptive: trace-first after a projected-but-occluded center,
projection-first after an off-screen center. Oryx generation 191 passes 629/629
checks and measures 0.533 ms per fully occluded scan and 0.421 ms per line-clear
behind-player scan; the WL1 starting-area census has at most five dormant
actors even on Death Incarnate.
The remembered-slot F8/F9 presentation difference recorded in item 14 is
closed.
The startup sweep restored `WL_MAIN.C::DemoLoop`'s call to
`WL_INTER.C::PG13`: the bundled `PG13PIC` now appears
once per process at its original `(216,110)` anchor on the source blue field,
waits seven seconds, and accepts one fresh key only to dismiss that page before
the title/attract loop. Exact VGA fade timing remains an intentional platform
difference. The fixed Agon W/S/A/D plus arrows control scheme, fixed movement
rates, and absence of DOS mouse/joystick/run-modifier configuration are also
explicit platform substitutions rather than hidden Phase-A work. Host asset
contracts pass, both application backends rebuild, and Oryx generation 185
passes all 683 direct production-shell checks. One staged visual startup review
remains the close gate for this correction.
The follow-up audit restored the preceding executable-linked sign-on as well:
a strict OMF extractor reconstructs the exact 64,000-byte `SIGNON.OBJ` image,
the shell presents `FinishSignon`'s fresh-key prompt, and `INTROSONG` now begins
before PG13 and continues into the title. DOS-only memory/device overlays remain
at their linked defaults as an explicit platform substitution. Host contracts,
both backends, and the corrected 683/683 direct shell rerun pass; the same
batched visual startup review remains the close gate.

# Phase B — Agon identity and legal presentation

[ ] 3b. Add the reserved Agon-specific splash and presentation hook without
changing the accepted original-facing startup flow.

[ ] 19. Present application and compatible renderer identities, educational/
noncommercial and third-party-rights disclaimers, the Author's no-rights and
no-liability statement, and accurate project/handwritten-assembly/LLM credits.

# Phase C — custom episodes

[ ] 20. Replace the five disabled paid-episode menu slots with `YOUR EPISODE
HERE`; define and validate a versioned custom-episode manifest and durable
map/asset build-install path; ship one minimal example while leaving original
Episode 1 immutable.

# Independent platform track

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
matched. Gameplay integration, update batching, and production fizzle
migration are now implemented under item 8e; default cutover and physical
qualification remain gated work. See
`agonport/doc/wolf3d-vdplet-migration.md`.

[ ] 8e. Replace the bounded static scene with the production render contract.
Schema 2, synchronized C++/assembly constants, the 5,448-byte compact mirror,
validated atomic full/dirty batches (including live/completed pushwalls),
complete pure renderer, real ABI 1.6
CONFIG/APPLY_AND_RENDER/FIZZLE/RESET wrapper, host lifecycle/retry matrix, and linked
Xtensa package admission are complete. The exact package also passes its real
runtime-emulator gate with two oracle-exact frames, native error/retry,
INFO17, timing, teardown, stale-handle, reload, and empty-slot evidence.
The production eZ80 descriptor/full/dirty serializer passes its direct MOS
target regression: byte-identical frozen retry, in-flight dirty-state
preservation, exact generation-2 delta, dirty consumption, and empty-batch
refusal. CONFIG, update-buffer upload, requested RUN completion, C3
presentation, exact retry, app-paced fizzle, and the production direct-row
renderer are integrated in the app while retaining the copied-pixel oracle.
The earlier “app-paced fizzle” claim was audited and found stale because the
production module still returned UNSUPPORTED. Release 1.2.0 now implements the
exact original 17-bit LFSR over 60 app-presented slices plus one unpresented
second-surface synchronization step. Host exact-retry/lifecycle tests and the
finite Oryx generation-161 ABI 1.6 gate compare five whole-frame transition
checkpoints, preserve the HUD/surround, leave INFO17 at 2,136 free bytes, and
finish with an empty module slot.
Complete performance/physical gates and removal of rollback paths remain later
work. The first Console8 run under stock MOS Arthur
loaded the complete level/assets but intermittently returned to MOS before the
first frame; the same exact cohort was playable in Flexe. A no-protocol-change
diagnostic build reproduced the failure on the Olimex bench and localized it to
application ordering: asynchronous mode 136 had completed in the VDP, but the
first discovery command was issued before MOS had consumed the corresponding
mode packet, never reached the VDP, and left later VDU bytes stranded while the
eZ80 and MOS remained alive. The application now clears and waits on MOS's
canonical mode-reply flag around VDU 22 before discovery. Five consecutive
physical starts reached the production runtime and unloaded cleanly; four
complete startup traces measured 12 ms from VDP mode completion to discovery,
while the capture boundary retained the fifth run's live-runtime/unload evidence.
Focused tests pass. A final Console8 stock-MOS Arthur acceptance remains required
before default-cutover or physical-release claims.

[ ] 8g. Replace production Wolf3D's copied full-frame publication with true
ABI 1.6 scoped direct-row rendering. The production implementation and its
generation-79 human visual gate now pass: the complete renderer—not merely the
bounded proof scene—uses `BEGIN / ROW / END` access to the hidden native drawing
surface, the former wall-edge black-pixel noise is absent, and the target
workspace fell from 92,160 to 11,552 bytes. The copied 76,800-byte RGB222 path
remains explicitly named as a host-qualified fallback/oracle.
Write each final background, wall, sprite, weapon, and HUD pixel directly to
its native scanline while retaining only necessary mirror, DDA, depth, texture,
and sprite scratch state. Preserve native lane ordering and sync bits, bound
all row access, discard every row pointer before ending the surface lease or
swapping, and never publish a partial frame after any render or asset failure.
Exact host regressions cover complete-frame parity, direct/copied equivalence,
lease and mid-row failure cleanup, pointer destruction, sync-bit preservation,
hidden-buffer mapping, retry behavior, and repeated-frame operation. Benchmark the
same production fixture across copied workspace + `pixels_write`, true direct
rows, and any already-real bitmap baseline using complete render/presentation
boundaries; report workspace and speed separately, and presume no speed benefit
until measured. A physical gate is still required before physical or
default-cutover claims.
