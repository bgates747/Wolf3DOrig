# WOLF-PERF-003 progress

Plan frozen/pushed as5599f43 on2026-11-05. Implementation remains local pending
later review. Production source and prior benchmark evidence are preserved.

r04 compiles all eight guests and the safe-SDK module; both native02 diagnostic
firmware builds pass. Generated-input/decoder/recorder host checks pass. Actual
AGNB-derived canonical room pixels and geometry match at eight headings across
standalone oracle/copied/direct production paths, with independent-row guards,
sync bits and balanced asset leases. Quiet runtime provenance and compiler/
completion limits are recorded in the runtime owner's VDPL-024 provenance note.

q01 passes both CPU arms, both600-completion unpaced arms and bespoke pacing.
VDPlet pacing times out before the first render, partway through its diagnostic
zero upload. Its raw failure is preserved; underlying transport cause is not
claimed. Controls7/8 were not run. Oryx302 released with fresh whole-host idle;
465raw/guest hashes verify. Exact q01 harness is retained under build/r04/harness.

r05 replaces only that setup upload with native CLEAR/CREATE, matching A's setup.
All guest builds/host checks pass; module and both firmware images are unchanged.
Fresh failure-first q02 ran under Oryx303. Its VDPlet paced case passes, but
the unchanged bespoke CPU guest then times out loading sfx.agnb before the
benchmark starts. All four bespoke guest binaries are byte-identical r04/r05;
the CPU guest had passed q01. This points to an intermittent shared setup/
emulator transfer issue, not a measured drawing failure. Both raw failures
are retained. Controls and remaining cases were not run after first failure.
Oryx303 released at17:41:34UTC with fresh empty whole-host inspection and no
successor; all94 retrieved hashes verify. No compiler/emulator/hardware lease
is held. The exact q02 schedule remains RUN-QUALIFY-02.md.

Flexe owner consulted through substantive mail
2026-11-05_12-45-07_wolf3dorig_wolf-perf003-setup-stalls-advice-one and immediate
accepted Pi steer. FX-152's existing producer/TX observer may distinguish an
idle producer from queued UART work; artifact compatibility advice is pending.
No repair, blind repeat, observer performance equivalence or completed paired
cohort is claimed.

Owner advice confirms retained FX-152 compatibility. Separately frozen s01
runs unchanged bespoke CPU then conditional original r04 VDPlet paced setup,
with only the private diagnostic frontend changed. Both finish normally in
29.182/53.443whole-process seconds, Quit0 and zero final backend faults. The
observer finalizes/shuts down with zero samples and incomplete windows; neither
stall reproduces. This is no live stall diagnosis or performance result.
All32retrieved hashes verify. Actual Oryx304 released17:52:30UTC,nextnull after
fresh whole-host idle. Substantive evidence returned to Flexe at12:53:13EST
with immediate accepted Pi steer. No resource remains held. Original setup
failures remain unresolved; remaining unrun timer-restoration controls can
qualify their independent failure path without repeating a failed speed test.

Review of those unrun controls found their old deliberate abort restored the
vector but held instead of returning to MOS. controls01-r02 corrects only
that path: explicit expected-abort flag, saved-vector verification, ISS/control
readback, saved entry-frame unwind and ordinary game shutdown. Both assemble
under Pi148 (3.089s guarded job, peak50.15C); no timed guest/native image changes.
The first build attempt had a PATH-only assembler lookup failure, preserved
under build/controls01; the fresh attempt uses the frozen production resolver.

Fresh Oryx305 runs the bespoke control on the original7e7d/086 baseline. It
times out300.264s loading shell.agnb BEFORE wp_run/PRT/the control. All1,030,018
transmitted bytes exactly match the successful s01 CPU trace's prefix. VDP
output equals delivery343B; final backend faults zero. This leaves restoration
qualification unexecuted, not failed restoration. Second control not launched.
All12retrieval hashes verify; actual305release18:04:45UTC,nextnull after fresh
empty whole-host inspection. No resource remains held.

The setup blocker now prevents qualification/comparison. Saved-prefix evidence
and a request for existing-evidence/component advice sent to Flexe in
2026-11-05_13-05-55_wolf3dorig_wolf-perf003-control-setup-blocker-one, followed
by immediate accepted Pi steer. No further replay, emulator repair, firmware
operation or physical benchmark is selected. Paired ranking/physical FPS remain
unqualified while that advice is pending.
No paired performance cohort or physical/ordinary-game speed conclusion yet.

Flexe's13:08:36reply independently confirms the prefix match. Its source review
finds625d republishes retained15-word TX state/history on every phase publication;
scheduling perturbation is plausible but not shown causal. No qualified repair
for this exact composition is established. WOLF-PERF-003-09 now owns the
component-dependent design review. Consumer requirements are in
STALL-DIAGNOSTIC-REQUIREMENTS.md: reduced repeated TX publication with coherent
phase/batch snapshots, persistent CTS history, bounded unavailable semantics
and real-path qualification requirements. Design review only is selected;
no implementation/build/run/firmware/hardware/adoption follows automatically.
Design request published as
2026-11-05_13-10-57_wolf3dorig_wolf-perf003-less-intrusive-design-one and sent by
immediate accepted Pi steer. Awaiting the component proposal; no lease held.

FX-153 design returned13:15:11; exact design/record hashes and all five base
source pins verify. Actual retained Writer/Progress source reviewed. The single
version/two-publication-path design preserves blocked-call visibility, tagged
batch coherence, CTS history and null semantics; no design changes requested.
STALL-DIAGNOSTIC-REVIEW.md selects component-owned implementation and one
bounded serial host/build tranche, with real-path tests and release-only
identity/footprint audit. Required x86_64 artifact needs a qualified compiler
route; unavailable tooling must be returned as a concrete blocker. No emulator
cohort, hardware/firmware action or runtime adoption is selected. Wolf holds no
resource. WOLF-PERF-003-09 remains open through returned evidence/disposition.
Disposition sent as
2026-11-05_13-17-46_wolf3dorig_wolf-perf003-fx153-host-implementation-one with
immediate accepted Pi steer. Await the component host/artifact or tooling return.

FX-153 native host return13:23:56 independently audited: all228source hashes,
eight evidence hashes, exact one-file diff and strict reader verify.57 checks
pass (15observer/28UART-library-machine/14reader); no x86_64 executable exists.
FX153-HOST-REVIEW.md accepts technical source/host results with original
pre-assert sequencing defect retained and a required sequential successful
assert before any future launch. No rerun is selected to replace that history.
Pi149 released,nextnull. Missing qualified x86 target/linker route is the next
blocker; offline Oryx build preparation and environment-owner route advice are
requested before any compiler routing exception or new execution.
Offline package request sent to Flexe as
2026-11-05_13-27-22_wolf3dorig_wolf-perf003-fx153-offline-build-prep-one;
existing-route/policy-evidence question sent to environment owner as
2026-11-05_13-27-39_wolf3dorig_wolf-fx153-x86-route-question-one. Both received
immediate accepted Pi steers. No compiler/emulator/bench work or lease selected.
Environment owner's13:28:41reply finds no existing qualified Pi x86 Rust/SDL
route or standing human Oryx compiler fallback. Actual Nov5 routing remains;
a concrete one-build exception must be presented to Smith after offline build
preparation. NEXT-OBSERVER-COHORT.md records intended later consumer cases only;
it invents no artifact hash and selects no reservation/execution.
Flexe's stopped one-build package returned13:30:09. Archivecc8fc6e1 and all228
archived source/script/runbook/manifest hashes independently verify. Guarded
one-off native Oryx build is concrete and statically reviewed; no compiler/test
or emulator executed. Await Smith's one-build routing exception decision
(normal FIFO,one serial offline release build,max20minutes). No resource held.
Smith directly approved "oryx compile approved." in this chat on2026-11-05.
The concrete one-build/max20minute routing exception is now approved; Flexe
may obtain its own fresh normal FIFO checkout and execute the reviewed package
once. General routing and separate emulator/bench/adoption gates remain intact.
Original human message01a1ad0a-8b2d-7683-91b8-e12baaaaf935 verified by
read_thread. Approval/scope sent to Flexe at13:49:13EST by durable mail plus
immediate accepted Pi steer. Await the component's actual build/cleanup return;
Wolf does not reserve a competing slot or execute peer-owned compiler work.
Prepared syntax-checked but unexecuted batch_probe.py/batch_probe_prepare.py
and copied exact strict FX-153 reader691e2b98 under ignored consumer preparation.
Frontend path/SHA and x86_64 ELF identity are mandatory inputs; no artifact hash
is invented and no profile/tranche is frozen or launched by this preparation.
Environment owner's13:53:15standing-policy update supersedes the earlier
no-fallback answer: compiler work may use Oryx when the required build cannot
be performed on Pi, with the documented limitation and normal FIFO/guards.
No further per-build routing question is needed for that case. The existing
specific one-build approval remains valid; scope/target gates are unchanged.
Approved Oryx306build passes39.037s; artifactc987fafc/1968256B and all8returned
evidence hashes independently verify. Peak70.875C,boost1unchanged,normal release
18:52:25UTC,nextnull. Recursive cache-only dependency audit stops on private
PulseAudio lookup; postbuild source rehash not reached, so not target-qualified.
Passive review finds the helper exists and parent RUNPATH names its directory.
Wolf wrapper also selects HOME/.local SDL3.2.18 before system build SDL3.4.2.
Selected bounded read-only audit-r02(max5min/128ELFs), actual wrapper resolution/
symbol evidence plus postbuild228source rehash; preserve original failed audit.
Sent13:55:12mail plus immediate accepted Pi steer. No rebuild/target selected.
Audit-r02 returned13:57:48; graph22e5e262 and all8evidence hashes verify.
Actual wrapper closure6ELFs/11edges/448strong imports available; local SDL3.2.18
selected, dynamic plugins/runtime still unqualified. All228actual postbuild
source files match and artifactc987fafc unchanged. Selected/froze s02 two-case
consumer diagnostic in RUN-STALL-02.md and build/s02 manifests; static libraries
pinned before each launch, unchanged input shim explicit. Fresh request16c92a5baa94
receives Oryx307 after empty-host checkout; sequential asserts precede children.
Observer results remain diagnostic only. No hardware or performance cohort.
Both s02cases complete29.743/55.652s,normal MOS return/Quit0/zero final faults.
Both observers finalize/shutdown with zero samples/incomplete window: no live
stall diagnosis or repair.32raw hashes verified and actual307release19:02:04UTC,
nextnull after fresh whole-host idle. Returned substantive evidence to Flexe
14:03:03EST plus accepted immediate Pi steer. WOLF-PERF-003-09 coordination/
diagnostic delivery complete; -04/-05 main qualification remains unfinished.
Next matrix explicitly repins both arms to privatec987 with observation disabled,
preserving all previous failures and excluding observer timings from comparison.
Fresh q03 matrix now frozen in RUN-QUALIFY-03.md/build/q03 and owns Oryx308,
request5fea56be8147. Same privatec987 on both backends with observation disabled;
corrected timer/register/MOS-return controls first, then CPU/unpaced/paced arms.
Eightcases,max300s each,firstfailure stop,initial/1s80C/RAM guards. No new build,
native/module/guest changes,shared runtime adoption or physical qualification.
All8q03cases pass, including both corrected actual-MOS-return controls,
both600-pose CPU/hidden arms and both closed720degree paced arms.259retrieval
hashes verify; positive entry/exit stacks balance; actual render wire packets
match all completed pose rows (24bytesA/65bytesB,6bytepacedpresent/fence).
Literal q03 harness retained. Actual308release19:13:02UTC,nextnull after joined
workers/fresh idle. WOLF-PERF-003-04 complete; separately frozen p01 comparison
may now proceed under a fresh lease. No physical/general-game speed claim.
Saved-SP verification uses listing-addressed fields in after.bin; stack.bin
is a256-byte memory window, not a6-byte pair. Initial inspection's incorrect
assumption is retained in verification-correction.json; corrected all6positive
SP checks and all4render wire checks pass. No guest failure was inferred.
Fresh p01 freezes12capture-free A/B/B/A cases across CPU/hidden/paced with
identical q03private composition; actual Oryx309 requestfe4e061f9570 owns it.
No observer/capture timings pooled; first failure stops the matrix. Source,
firmware,SDK,guest and assets stay unchanged; no physical contact.
HARDWARE-PREPARATION.md records candidate exact images/proposed14guest suite
and required scope/clock/restoration questions. Existing-evidence-only advice
requested from Extender at14:17:12EST plus immediate accepted Pi steer. No
bench reservation/access/live inspection/flash/run selected by this preparation.
p01stops on first A CPU case: Tctl82.625C at30.077s exceeds frozen80C guard;
initial56.75C/ampleRAM,console still shell assets before benchmark. No matched
results or later cases. Ordinary Quit/join,23retrieval hashes verify, actual309
release19:18:22UTC,nextnull with fresh idle. Boost1 preserved; no raised bound
or automatic replay. q03's full functional pass remains valid (peaks<=79.625C).
Retained thermal/policy/passive-state advice requested from Oryx-manager in
14:19:11ESTmail plus immediate accepted Pi steer. No host change/newload given.
Comparison -05 remains open; hardware preparation awaits Extender advice.

The separate spoken notification hardware test passed Olimex37; Smith confirms
clear speech. Full handback/release completed and Extender notified. Its sources,
package and scope are independent of this benchmark; no hardware slot remains
owned. See ../WOLF-PERF-002/voice/HARDWARE-RESULTS.md.

Owner dispositions received 14:19/14:20EST: Extender's eight-point source-only
advice is reconciled in HARDWARE-PREPARATION.md; neither exact image is physically
qualified and no reservation/access is selected. Oryx POWER-001 confirms Smith
explicitly re-enabled boost on Oct16; boost1 is intended, not a configuration
fault. Passive post-run Tctl54.375C is not loaded cooling qualification. Keep
80C guard/boost1 and p01 blocked; no automatic retry or relocation. Owner proposes
only a separately human-approved finite boost-off variant, exact restoration and
new host-state baseline, never pooled with boost-on. No host mutation performed.

Smith's new standing boost-off instruction verified in owner14:38:09mail and
canonical rollout policy. It supersedes temporary boost-off/restore proposal:
keep global/all24policy0 through cleanup. Fresh stopped p02 same12cases frozen
with new host baseline; actual Oryx310/request73c5f3a83eec checkout obtained
after fresh whole-host idle. Controller asserts ownership and boost0 before
every case; frozen80C guard retained, no compiler/guest/native/source changes.

p02 first A CPU case times out300.232s loadingSFX before benchmark; remaining11
NOTRUN. Peak61.25C across301guard samples (initial58.375/final58.625),boost0
preserved. Local controller independently exits143 before deadline; causeunknown,
remote original bounded runner continues to timeout/ordinaryQuit/join.23raw
hashes verify, allownedPIDsgone, freshidle/actual310release19:45:29UTC,nextnull.
No paired timingresult or retry/repairclaim; see RUN-PAIRED-02-RESULT.md.

Exact B source-owner review received14:46:46EST: artifacts rehashed, no generic
ABI/rows incompatibility; physical memory/wholetaskstack/callback0/clock/CLI
gates remain. Hardware preparation corrected READ16 request/reply terminology
and current9c44a666 retained-rollback/no-redundant-device-backup policy.
Requested MechAgon source-only timing consultation answered14:47:05EST; no
generic stock mode-query fence asserted as Canvas draw completion. Existing
source-only Flexe followup requested14:47:06EST on p02stall; no new run/build.

Smith requested Fab comparison of asset-loading stall. ActualOryx311 acquired
under ordinaryFIFO/e1447e1311ef. Exactr05 A CPU guest/assets/MOS retained,
existing officialFab1.2.5+nativeuserspaceWolf5c4e4b9 replaceFlexe/ESPimage;
asset-loadingonly boundaryfreshbefore.bin atwp_runentry, not benchmark result.
Single300s/80C/boost0 trial. fab01 wrapper caught missing runtime manifest
beforeFab/guest started; preservedfailure, corrected freshfab02 nowrunning
under samefinitecustody with freshassert. No new compiler/firmware/hardware.

WOLF-PERF-003-10 complete: Smith-requested one Fab loading trial passes
24.846s to freshwp_run/before.bin boundary,normalQuit0/whole25.661s,peak61.375C.
Same exactAguest/assets/MOS; officialFab/nativeuserspaceWolf replaces BOTH
Flexe/ESPimage,not host-only isolation or benchmarkperformance. fab01missing
manifest rejectedbeforeemulator; preserved/correctedfreshfab02.15retrieval
hashesverify; freshwholehostidle/actual311release19:54:58UTC,nextnull,boost0
preserved. FAB-LOADING-RESULT.md retains limits; no furthercohortselected.

Human-review checkout requested bySmith: actualOryx312/request34cca66cd4b1,
lease df1d50335a1a454e8fd06f193c406f0b held20:00:07UTC. Freshstoppedhuman01
pacedA/B copies verified; visible_run.py retains300s/80Cguards/normalcleanup.
NoagentGUIlaunch; custody remainshelduntilSmithfinishes/ownedcleanup/release.
HUMAN-REVIEW-01.md recordscurrenthandoff.

Smith requests a note for loading breadcrumbs: WOLF-PERF-003-11 added open
in TODO.md. Reuse game's existing per-asset/per-data-chunk progress, outside
measured intervals, with clear transition to animated fixture. No current
fixture changed. Bespoke interrupted logs preserved in human01/01-bespoke-
paced/review-history/attempt01-interrupted; same profile reset/verified for
Smith's rerun. Explicit human instruction: retain Oryx312 until Smith tells
us to release, even if emulator windows close.

Root cause found for human A/B scene discrepancy: A task warmup replay omitted
INIT_LEVEL, leaving native m_world.tilemapBufferId0. GetTile missing-buffer
fallback returns solidwall. Correct camera packets did not qualify scene.
Previous A runtime timing/visual claims therefore do NOT establish intended
canonical workload; keep raw evidence but exclude from matched comparison.
r06 changes firstAsetup to ordinary submit_level_reset+completion/present fence,
then secondnormalwarmup. Future standalone_bench generator corrected too.
Bothapps' existing finalizedimage/audio dotcallbacks now present/fence hidden
page during setup; timerbrackets remain unchanged. Sevenassemblies pass under
Pi153, released20:35:36UTC,nextnull. Initialprepare anchor mismatch and wrong
x86assembler invocation preserved; reused existing native ARM assembler, no
toolinstallation. FabA visual-only variant omits unsupported taskCCOUNT dump;
no timingclaim. HeadlessFab r06a underheldOryx312 nowcapturesloading/rotation.

WOLF-PERF-003-11/-12 implemented/verified: A mapbindingfixed via first
submit_level_reset; both finalizedassetcallbacks present/fence visible dots
outside timing. Fab correctedA600poses/twoturns/normalQuit0,peak63.875C,
62retrievalhashesverify; screenshotsresults/r06. SevenARMguestassembliespass,
all6timedloops/assetsunchanged. Old A workloadtimingsdisqualified; -04reopened
for corrected nativecohort, -05stillopen. B rendererunchanged/native8heading
parityretained; no existingFabXtensamoduleadapter, no BfullFabclaim. Freshfixed-
reviewprofilesstopped; Oryx312HELD untilSmithexplicitrelease. R06-RESULT.md.

WOLF-PERF-003-11 r07doublebuffer refinement complete: authoritativephase/count
reconstructsbothpages, including assetdescription. SevenassembliespassPi157;
sharedsixUIcopies/benchsource/assetsunchanged. Fab deliberatelyholds eachpage
atcount5; captures004/006identical. Originalafter.bin excludesUIstate; wrong
inspectionpreserved,notguestfailure. SeparateFabonlyPi159stateprobe thenproves
actual470total/00470digits/error0 matchescontainer180+50+16+135+89.
BothFabchecks600poses/normalQuit; finalwhole59.530s,peak60.5C,68hashesverified.
Freshloading-reviewprofilesstopped; noGUIlaunch. Allownedemulatorsgone; Oryx312
HELDuntilSmithsaysrelease. R07-RESULT.md/results/r07/loading.png.

Smith now explicitly authorizes allfour combinations and headless tests,
including newFabnativeproduction-sourceBbridge. Flexe perbackendfirstpass
requires>=5trials; firstfailureretried. End-of-arc reminderWOLF-PERF-003-15:
remainingemulatorissuesgotoFlexe whileWolfdoesotherusefulwork; hardwareis
primarygameplatform. RetainOryx312untilSmithexplicitrelease; noGUIlaunch.

Four-way implementation: private Fab bridge compiles the pinned production
VDPlet renderer source with the existing native-pointer shim, actual buffered
assets and live hidden VGA rows. Exact uploaded package is checked in full;
this is not an Xtensa loader. Oryx fallback build22.764s, peak61.25C/boost0;
contract checks report0failures. Retrieved SO/selftest hashes match the build
receipt. Separate Fab B guest assembly passed under Pi161, then released.

Initial detached controller699208 disappeared before any trial started (empty
log, no run directory or remote emulator). Preserved those facts; normal tool
session69164 now owns the finite cohort. First Fab B trial PASS:600poses plus
2warmups, loads/unloads1, errors/residuals0, normalQuit0, whole55.722s. Captured
room is the intended large room, rather than the former solid-wall fallback.
Fab A and conditional Flexe repeats continue; Oryx312 remains held.

MOS RFC final r03 source review read: Wolf's corrected r07/map-binding exclusion,
24-byte A versus65-wire-byte B packet lifetimes, receiver ownership and distinct
paced/capacity workloads are retained. No substantive correction to return;
final owner message explicitly requests no acknowledgement or further round.
No RFC implementation or target work selected here.

WOLF-PERF-003-13/-14 complete: all12four-way headless trials pass. Fab A/B1each,
Flexe A/B5each because both firsttrials passed. No loading stalls thisbatch;
prior intermittentfault remains unresolved, not a demonstrated transportrepair.
Fab600records each; FlexeA600each; pacedFlexeB438/432/439/437/443records, all
finalstep600/twoturns. Tenactualwirechecks and338retrievedhashes pass; native
sample identity/backendzero-fault/normalMOS/Quit checks pass. Bridge clean
602renders/load1/unload1/errors0/residual0; bothFabfinalcaptures showMOSprompt.
Peak62.375C/boost0, allownedchildren stopped, freshwholehostidle. Actual312HELD,
no release/hardware/firmware operations. FOUR-WAY-RESULT.md records evidence.
Smith reminder -15: if faults return, hand evidence toFlexe and moveWolf to
otherusefulwork;hardware primary. No new Flexe workload selected by reminder.
Substantive result returns published to Flexe/VDPlet16:44:26EST as
wolf-four01-results-{flexe,vdplet}-one; immediate chat notifications accepted,
not read-confirmed. No acknowledgement or additional owner work requested.

Smith next explicitly orders Oryxrelease/Olimexreserve/executewhenavailable.
Actual312 released22:45:31UTC after freshidle; Jukeboxadb522f22a0b notified.
Olimex753d29504ecf first/only, no grant yet. HARDWARE-RUN-01.md supersedes old
no-booking/no-run selection; finite14fixture/8INFO observations, ABBA per mode,
four app-only writes including exact incoming/touched-tail restoration.

Exact installed EMOS5735812 source review caught old A W3DR/W3DT reply rejection:
only ten-byte P3DR/VDPL accepted. Extender confirmed task-owned P3DR render1/2,
control80/81 adaptation. NewnativeA85c520a1/1090400B, allA callback/foreground
validators fixed; source delta only replyglue, renderer/world and six timed
loops unchanged. B7593b9cf/module1907ce retained. Eight guests plus563Bresource
observer compile; native121.35s, Pi163peak58.95C then released23:00:01UTC,
MechAgon164 notified. Prelaunchx86assembler and observerfilename/branch errors
preserved before successful nativeARMbuild. Device-free controller order/stop
checks pass.402pins/20files/1105920Bflashspan bound inbuild/hardware01/kit.json;
source-review.json retains callback/nominalclock/whole-task stack limits.
READY sent18:04:51EST; awaiting Extender fresh physical admission/newtoken.
No target contact yet, no native source substitution under old qualification.

ACTUAL Olimex40 granted23:06:29UTC/request753d29504ecf/token
18d3babcf0c348d9af60909d1538634f. Extender stopped alltargetaccess and handed
exclusive direct operation toWolf; grant copiedbuild/hardware01/grant.json,
current ignoredcontext.json bound to maintained URL/port config. Selected suite
running in retained toolsession69059 via hardware/physical.py. Own entrypassed
actualCLI/mode0/callback0/startup/listener;20files stage/GETcompare proceeds.
No concurrent root/other-agent target calls while this controller ownswork.
All subsequent phase receipts underbuild/hardware01/evidence. It stops first
unexpectedfailure, retains custody and never auto-replays. Normal success must
restoreexactincoming1105920Bspan, rawmode0/callback0/CLI/input/idle/freeports,
then release40with fresh handbackproof and notifyExtender/nextqueue agent.

Hardware01 firstcontrol failsbeforewp_run: HUD28/total409, explicitAGNBerror/MOS
return. Stopownedcontroller725782/SIGINT; readerjoined, no subsequentdispatch.
NoLOAD RAMpreserved308506B, agnb_error14/wp_loading_error1/owned0/abort0;
HUD fullGETstillmatches. Breadcrumb first-page ingresswait failure, not proved
asset corruption or receiver cause. Exact incoming1105920B app/tail restored/
independent fullspanreadback; freshhandback passes. Actual40released23:23:05UTC,
nextnull, Extendernotified. NoB/otherguest/probe/timing result. Hardware01 evidence
immutable; HARDWARE-R01-RESULT.md. Newsetup-onlysame-fence wait diagnosis needed,
not blind replay or a changed measuredrenderloop.

### Hardware02 preparation after clean40 release

Prepared a new loading-only candidate in build/hardware02, preserving hardware01.
Installed-source reply `wolf-perf003-same-flag-wait-source-return-one` confirms
MOS0x41 can observe the same pending flag repeatedly without query resubmission.
New loading_wait.inc clears/queries once, permits at most ten public waits and
checks a1200-MOS-tick elapsed deadline after each, with the independent300s host
invocation bound. Both-page reconstruction remains. New48B loading.bin is written
only after main returns, outside AGNB callbacks/timing. The native images,
module, all timed harness/audio/render source remain unchanged.

Pi build requestbe322a5a3aa1 is queued normally; new Olimex reservation524c52a90a76
is PREPARING under HARDWARE-RUN-02.md, not granted. Extender notified with finite
scope and no preemption request. The new controller recognizes early AGNB return
only after the actual post-RUN MOS prompt, preserves RAM before any LOAD, reuses
known assets with independent reads and resets only task-owned generated config
between independent guests. Old generation40 token remains invalid.

Hardware02 READY: eight serial Pi assemblies and actual delayed-MOS-return
controller fake-serial check pass, all eight compiled48B layouts match and
all timed sources equal hardware01. Peak50.7C. Pi168 released23:40:07UTC and
actual automatic Extender169 notified. Frozen kit792pins rechecked unchanged.
Extender fresh Olimex41 grant for524c52a90a76 accepted/asserted; incoming component
identities unchanged and no NET004 firmware installed. Entry checks passed;
independent reused-file verification/new executable staging is active. No
benchmark dispatched or new timing claimed at this point.

### Hardware02 stopped and cleanly released

Acontrol, CPU600 and unpaced600 pass. CPU676PRTticks/80MOSticks (~888poses/s);
unpaced19794/2380 (~30.31 completed renders/s), mean native draw7361728.2CCOUNT
(~30.674ms at source240MHz). One pass only; all470assets loaded with zero loading
wait timeouts in each of four invocations. Old loading fault did not recur;
continuation was not exercised and root cause remains unproved.

Fourth guest A paced failed its FIRST map-binding warmup completion wait before
sampling (n0/count0/PRTstart0/inflight1/ready0/callbackerror0/sequenceuninitialized,
PRT2026ms). Existing failure loop held after reporting timer restored. Runner
stopped; no B or successor. One standing Agon reset recovered CLI after exact
startup/init review; saved309014B app RAM before any LOAD and verified codeprefix.
Retrieved available failure files, restored/read back incoming app/tail and
freshly verified normal handback. Clean41 release00:04:56UTC Nov6, nextnull;
Extender substantive release notice accepted. No hardware custody remains.
HARDWARE-R02-RESULT.md and build/hardware02/physical-summary.json retain partial
results/limits. New immutable003-17 tracks warmup completion localization before
another identified selection. Do not conflate it with an in-timed-loop paced
failure or old Flexe asset stall. Central ESP32 digest invitation read; owner-only
mailbox contribution policy retained, no shared digest edit or new audit begun.

### Hardware03: concrete recorder lifetime defect

Source resolves003-17's first-warmup signature: nativeA recorder pointer/count
survives0xf000 deletion. Previous unpaced600 leaves count600; next warmup finish
returnsfalse before completion publication. Previous CPU0 instead leaves a stale
borrowed pointer capable of writing freed/reused storage. Treat hardware02
unpaced speed as provisional until repeated after defined lifetime. This is our
task instrumentation, not an EMOS/production renderer defect or Flexe asset stall.

Prepared hardware03: private acknowledged242/offset0 disarm before log replacement
and before deletion, pointer/count/error released; strict overflow checks and
native drawing/brackets/measured waits unchanged. Four A guests/new nativeA,
unchanged B after per-call acquire/release+INIT counter review. Exact native
control method extracted for sanitizer CPU0/full600/paced-subset lifecycle tests.
Pi buildc3d46fdf6534 queued; Olimex8c05f263c2b5 PREPARING under HARDWARE-RUN-03.md,
not granted. Extender notified. No target custody or contact after clean41 release.

Hardware03 build READY: Pi177 actual checkout/assert, exact native-control
ASan/UBSan regression reproduces full-recorder refusal then passes six repeated
CPU0/full600/subset/release-before-free lifecycles, invalid offset/stale read/
failed arm/overflow/reply binding. Four A assemblies and native compile109.10s
pass. New nativec5cfaaed91a0d294bbe30811ca57ff36a585d070946f0813a469412f57d77fcc.
Source check proves measured instructions, renderer/draw brackets and overflow
guard unchanged. B artifacts retained after per-call view/INIT review. Kit1052pins
frozen. Pi177 released00:31:58UTC Nov6, actual automatic Jukebox178 notified.
Extender received final readiness for Olimex8c05f263c2b5; fresh grant pending.
No target access/held lease. Source localization003-17 complete; physical
qualification/comparison still open. Retained old timing remains provisional.

Hardware03 actual Olimex42 received/asserted for8c05f263c2b5; Extender stopped
exclusive operator handoff, same incoming6565/ad1e/20029942/ed403/0566 and noNET004
adoption. Fresh entry/reused-asset full reads and four changed A executable
readbacks pass. New nativec5cfaaed app-only/tail write independently read back;
Acontrol passes with470assets/zero loading timeouts. Remaining selected suite is
active under hardware/physical03.py (host session91753); custody retained through
restoration. No B result or completed paired comparison yet.

### Hardware03 stopped; recurring physical setup fault diagnosed further

Acontrol/CPU600/unpaced600 pass. Clean-lifetime A unpaced30.2755renders/s,
native draw mean30.714ms/p9532.846/max33.146 at240MHz; full frame cycle mean33.023,
p9535/max36ms, no steady30Hz presentation claim. CPU887.57poses/s, pose+pack1.113ms.
Fourthguest A paced fails BEFOREwp_run atHUD37/total418, same phase1 postC3
mode-query fence. Ten wait-only calls all return15, zero recovery, first28MOS
ticks/whole294ticks (~2.45nomsec). ExactlyONE nonASCII byte0x86 atserialoffset99474;
saved query170086@0x8b6c3 intact. Loss/parser/receiver layer remains unseparated.
No B/probes/successors; no reset/replay. Sourceonly advice to Extender andVDPlet.

RAM saved beforeanyLOAD; exact incoming app/tail restored/readback and fresh
normal handback passed. Clean42 RELEASE00:50:55UTC Nov6; actualnextMechAgon52187060d50a
and Extender notified immediately. No Wolf target custody/actors remain.
HARDWARE-R03-RESULT.md retains partial result/clock/budget/lifecycle limits.
No further cohort/reservation selected pending source disposition; this is a
physical loading-query issue, separate from recorder lifetime and oldFlexe stall.

Native parser source return19:59:22EST received/read; all four supplied exact
source pins match. Normal VDU2 does not mirror valid consumed query86. Loose86
can be printed; finite200ms parameter waits can discard partial command state
and leave a later86 printable. C3 does not intentionally split/discard contiguous
query bytes. These are compatible source paths, not proved received timing/loss.
Installed EMOS synchronousPUTCH blocks/retries TX, and ADLexec clearsMBASE;
no simplistic single-TX-timeout-drop or runtime-pointer claim. Need actualTX/RX/
parser-state discriminants. Extender installed-source reply received and reconciled below; no new build/test/
reservation selected. Details appended to HARDWARE-R03-RESULT.md.


Extender20:19:16EST exact5735812 source review confirms wait41 iteration bound,
flag-only semantics/no query identity, unsolicited same-type reply possibility,
and synchronous PUTCH retry contract. Raw USB mirroring does not establish UART
order. Guest callback source is after complete stream/consolidate/bitmap-create
returns; no intended mid-payload callback found, receiver consumption unproved.
LOADING-DIAGNOSTIC-DESIGN.md records bounded unchanged-sender timing/history
proposal under003-16, not an implemented or selected run. Bench43 has independently
changed EMOS/P4 under Extender/MechAgon; generic carrier repair ongoing. Need full
fresh context/rollback/API binding and grant before future Wolf target work.
No Wolf lease, reservation, compiler job or target actor remains.


### Wall-column optimization investigation003-18

Smith selected per-column scratch/bitmap/completion overhead for investigation.
Read exact retained nativeA/framework and production B sources; no code changed.
A allocates up to256 PSRAM-preferred scratch buffers/frame, samples then blits
pixels; Bitmap wrapper itself is stack-local/noncopying. Framework double-buffer
DrawBitmap executes immediately. waitCompletion(false) processes primitives
with suspend/resume/Refresh, not a vsync wait or proved scheduler sleep. This
corrects the earlier simplified queued-draw explanation. B already samples
directly into framebuffer rows, grouped by used texture. WALL-RENDER-INVESTIGATION.md
pins nine inspected sources and proposes disjoint phase/count profiling, then
separate scratch-reuse and mode-specific flush candidates. No claimed speedup,
implementation/build/run/deployment.003-18 open; preserve matched baseline and
current003-16 loading blocker/component reconciliation before physical work.
