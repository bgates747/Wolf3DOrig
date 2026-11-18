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

### Hardware03: concrete recorder lifetime defect

Source resolves003-17's first-warmup signature: nativeA recorder pointer/count
survives0xf000 deletion. Previous unpaced600 leaves count600; next warmup finish
returnsfalse before completion publication. Previous CPU0 instead leaves a stale
borrowed pointer capable of writing freed/reused storage. Treat hardware02
unpaced speed as provisional until repeated after defined lifetime. This is our
task instrumentation, not an EMOS/production renderer defect or Flexe asset stall.

Hardware03 actual Olimex42 received/asserted for8c05f263c2b5; Extender stopped
exclusive operator handoff, same incoming6565/ad1e/20029942/ed403/0566 and noNET004
adoption. Fresh entry/reused-asset full reads and four changed A executable
readbacks pass. New nativec5cfaaed app-only/tail write independently read back;
Acontrol passes with470assets/zero loading timeouts. Remaining selected suite is
active under hardware/physical03.py (host session91753); custody retained through
restoration. No B result or completed paired comparison yet.

### Hardware03 stopped; recurring physical setup fault diagnosed further

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

### Loading04 prepared after pushed checkpoint9e52f7f

Smith requested commit/push and proceed; reviewed checkpoint9e52f7f pushed to
feature/standardized-deployment. Explicit local ignores retain26 RAM/custody
files without rewriting/deleting evidence.73 Python sources parse; timing decoder
accept/corrupt regression passes. Frozen serial whitespace retained as evidence.

Extender21:14:06 source return: c9c8b6b ROMb5a1f4aa/P4a967fac2 retained and
independently rehashed with both maps/nativeA. Private RAM bindings verified.
Legacy serial/handlers/reply parser and clear/wait bodies unchanged versus5735812;
new25h unused. Parallel carrier descriptor fix is not a Wolf UART repair.
MechAgon43 remains operator; last native20029942 is historical entry, not promised
current/restored state. No Wolf target contact.

Loading04 task-owned guest removes reachable wp_run, retains asset/C3/query
sends and existing ten same-pending waits; no warmup/render/PRT. WPQ3 RAM ring32
completed fences+current,4288B after-main file and oldWPL2 retained. Hooks preserve
application registers/IRQ enabled, read only pinned ordinary RAM, no callback
I/O/VDU or UART status ports. Paint/C3 stamps live separately until fence entry;
blocked query/wait leaves current incomplete. Nominal full-call time/non-atomic
reverse-reply state cannot establish native parse/inter-byte arrival.

### Actual43 release and loading04 offline binding

MechAgon43 actually released23:29:03EST after incoming20029942 app/tail restored
full1105920B span5fbf82c4 independently read back; startup/listener/input/CLI/
mode0/callback0/idle/freeports pass. Extender confirmed Wolf first, not granted.
New current diagnosticEMOS8270/source71552879 retained, ordinary7d16 not installed.
Rehashed diagnostic ROM and maps; all loading04 private RAM addresses unchanged.
Five complete Legacy sender/reply/handler/wait source files byte-identical to
priorc9c8b6b. Existing9c07 guest unchanged; no compiler/emulator/device action.
Bound rollback to actual owner app/tail readback instead of assumed historical
state. kit04 now selects exact8270/map pins with rebind43 receipt; plan READY for
fresh scheduler grant, same finite four loading-only runs/no timed renders.

### Loading04 hardware44 completed and released

Actual44 granted/asserted after exact immutable107-pin reconciliation. All four
loading-only cases pass:470assets/952fences, zero timeouts/recoveries, normal MOS
return; RAM saved before successorLOAD and both diagnostics verified. Final32
fences each retain MBASE0/backend0/serialFlags0x33, senderA0/BC0/HLquery+3; transmit
deltas0rawMOS ticks are below resolution, not zero time. No stray0x86 serial.
No render/warmup/PRT/performance run. Loading-only history/observer/newROM differ
from prior failed render-bearing history;003-16 unresolved, no transport fix.

Hardware05 preparation selects observed real benchmark/render history after44's
loading-only non-reproduction.8clients preserve exact measured/backends/asset-send
code and original loading text; add same setup observer/final-fence failclosed.
Pi215 assembled8/source/layout/decoder pass and released05:00:28UTC nextnull;
actual-controller barrier/14case8probe/full-firstfailure tests pass. NativeA/B/
module unchanged; full rollback span1105920 bound to actual44/Mech43 evidence.
No hardware/renderer optimization; freeze normal package before fresh admission.

### Actual47 host entry stop and corrected06 preparation

Actual47 admitted frozen e6efa09 after46 clean pinwalk/restoration. Controller
stopped on host Path-vs-bytes hash TypeError at entry startup GET; zero guest
LOAD/RUN/stage/namespace/nativewrite/reset. Preserve original05 selection/code/
logs. Normal files/state/CLI/readEXIT/neutralidle/freeports cleanup passed and
actual47 released06:22:51UTC nextnull, scheduler notified immediately.
HARDWARE-ENTRY-R05-RESULT.md records no benchmark measurements. New physical06
fixes entry hash bytes and uses fresh host output; retained pair05 was not yet
created. Actual entry success/corrupt-file/collision/SAVE-only checks pass with
existing prompt/full14case8probe/first-failure checks. All8clients/assets/module/
native images unchanged; no rebuild. Separately identified HARDWARE-RUN-06.md
retains exact finite comparison scope; freeze before fresh admission.003-16
and paired comparison remain open; no automatic replay or oldtoken use.

### Actual49 control/CPU return and host listing-path stop

Control passed; CPU completed600poses/676nominalPRTms/80MOS ticks, alloutputs
retrieved. Runtime listing lookup still assumed hardware06 adjacent source
instead of reused hardware05 listing. Firstfailure stopped before unpaced/
paced/B; no asset failure. Offline actual listing qualifies saved SP0xBFF71
equal at entry/exit. Exact native/full1105920span restoration/readback and normal
fullhandback passed; released49 at06:56:59UTC, nextVDPlet8452a3009de2 notified.
Original06 code/kit/evidence preserved; no replay. See HARDWARE-R06-RESULT.md.

Hardware07 explicitly maps/pins all8assembler listings and verifies runtime
inputs before target operations. Reuses pair05 in place: known directory/level
inventory, unchanged staged input GET comparisons; preserve generated config
before normalization, reject unknown files/asset mismatch. Same assembled8apps/
module/native images, no build. Six device-free actual-controller test methods
exercise entry/stage/all8backend-mode case codec+stack paths,512B resource
threshold/handback, invocation and complete14/8/first-failure sequence. Synthetic
render records only qualify host code, not target timing.1502inputpins including
all listings verified. Same finite HARDWARE-RUN-07 scope needs fresh admission.

### Actual51 terminated during verification; exact original GET reconciled

Frozen090cfee entry passed,14retained files verified; host session72475 returned
143 during b-cpuGET, no traceback/failurehandler. No guestLOAD/RUN/flash/reset.
Cause/signal sender unestablished; ~178s interval does not itself prove tool
limit. Actual originalGET192087320/boot164110695 resumed/delivered/matched and
retired from samejournal, no resubmit or sequence continuation. Normalfiles/
rawmode0/callback0/CLI/neutralofflineidle/freeUSB/actorsjoined cleanup passed;
all firmware/app/tail/featureabsence retained unchanged, noflash needed.
Released51 at07:58:18UTC nextnull; scheduler notified. Originalcode/frozenkit/
log/journal retained; HARDWARE-R07-RESULT.md. Read-only Pi manager source/log
consult requested; no new reservation/reproduction before host disposition.

### Existing host logs exhausted; signal-stop receipt qualified offline

Pi manager read-only source/journal/rollout audit found no confirmed supervisor
kill/persistent mainhostrestart or outertimeout. Alive07:54:35/firstdead07:55:29
are observation bounds;~178s until discovery not exact signaltime/180stimeout.
New SSHserver presence not cause evidence, signal sender remains unknown.
Corrected report preserves those limits. New08 host-only launch+TERM/INT/HUP
receipt records PID/parent/time/stack then exits via normal unwinding, no signal
ignore/detach/bypass/replay. Isolated ownedchild tests3signals prove receipt,
finally cleanup/no continuation. Six controller tests pass. No compiled/timed
change. Fresh HARDWARE-RUN-08 identifies same14/8 finite suite with usefulhost
interruption evidence if it recurs, not a repair claim; source disposition
complete but originalcause remains unknown. Freeze before normal fresh grant.

All20retained inputs verified, A full written span readbackmatched, then45s
boot inputready bound failed before any guest. No hostsignal interruption.
Status P4alive/neutralreadyfalse/offlineidle and empty2s nativeUSB retained.
One standing Agon-only reset failed; one P4currentbuild/PADrelease/display then
Agon paired recovery passed actualCLI/files/rawstate. No replay or new tests.
Original native20029942/full1105920span5fbf restored/readback, finalrawmode0/
callback0/Legacy0/CLI/files/inputneutral/offlineidle/freeUSB/actorsjoined passed.
Released52 at08:26:06UTC; nextVDPlet25f6e811c787 notified. Source-only bootstrap
review requested from Extender before concrete continuation, no newrun selected.
HARDWARE-R08-RESULT.md retains honest lack of newrender/assetmeasurements.

### Source disposition and explicit clean-bootstrap preparation09

### Actual54 complete physical comparison and clean release

Frozen9e191aa/1537inputs admitted under actual54. All fourteen guests and eight
outside-timing B resource probes pass; four explicit clean preparation pairs
remain outside measurement. Every asset load completes470records/952fences,
zero timeouts/recoveries. Corrected native map/recorder lifecycle passes the
full600-to-next-warmup transitions. Prior intermittent loading cause is still
unresolved; no repair attribution. Minimum B stack headroom1956B remains above
the512B guard. All record/angle/count/return/stack/timer checks pass.

Unpaced pooled1200draws/backend: A30.700994ms, B91.560165ms at configured240MHz,
ratio2.982319. Broader command return30.705259/92.143890ms; most of the gap is
inside drawing. Unpaced whole-path30.270925/10.522255frames/s; paced two20s runs
24.409115/10.004480frames/s,978/402completed of1200quanta. Scripted CPU-only
active1.120833/2.163333ms; shared pose+pack1.116667/1.101667ms, B extra bucket
serializer lifecycle work, not UART. Source clocks only; MOS crosscheck retained.
RawPRID0xCDCD explicitly maps PRO/core0 in installed SDK xtensa_context.h; not an
invalid numeric core index. No optical scanout or ordinary-game FPS claim.

Original20029942/full1105920span5fbf independently restored/readback; current
P4/EMOS/startup/listener retained. Final mode0/callback0/Legacy0/CLI/readEXIT/
neutralofflineidle/freeUSB/joinedactors pass. Extra prompt-mirroring/journal
host mistakes corrected without repeating SAVE/guest/measurement; all originals
preserved. Actual54 released09:31:19UTC, scheduler/actual next Extender notified
before offline analysis; Wolf no custody, SD mounted. HARDWARE-R09-RESULT.md and
results/hardware09 retain curated samples/reports/rawhashes; build/hardware09
retains private full evidence. No renderer optimization included.003-04/-06/-07
complete; human acceptance003-08, corrected matched emulator timing003-05,
historical loading cause003-16 and parked column investigation003-18 remain open.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
