# Hardware loading04 — bounded sender observation

Status: PREPARING; no hardware grant. Smith renewed proceed after repository
checkpoint9e52f7f on2026-11-05. This addresses003-16; no wall optimization, new
shared firmware repair or full comparison cohort is selected here.

## Selected source/build

Task copy of hardware03 bespoke paced guest, with unchanged asset transfers,
C3/query bytes and counted RST18 boundaries, existing ten same-pending public41
waits/1200raw-MOS-tick bound and unchanged loader abort/normal shutdown. Remove
the reachable wp_run call: stop after470 loaded assets/setup, before any warmup,
render, PRT ownership or recorder allocation. Normal render-callback install/
shutdown remains as in the donor. UI explicitly says no rotation.

Task-owned RAM trace WPQ3 v1:64B header,128B current record,32x128B completed ring;
4288B file loading3.bin after main, alongside the unchanged48B loading.bin. RAM
is explicitly zeroed before main (assembler DS padding is not trusted). Each
fence retains asset metadata/remaining/block, paint/C3/query/wait MOS timestamps,
query descriptor/MBASE, raw RST18 return AF/HL/BC, mode flags, private UART-enable/
backend RAM and non-atomic EMOS reverse-reply parser state. First failed fence
freezes history. A blocked query/wait leaves current record incomplete. Paint/C3
marks stay in separate RAM until fence entry; a block there requires full RAM,
not an inference from the previous current record.
Observation preserves AF/BC/DE/HL/IX/IY, keeps interrupts enabled and performs no
callback I/O, UART port reads or firmware writes. Mode flags do not identify
queries. Full-call stamps cannot establish inter-byte timing/native parse state.

Preparation: hardware/prepare04.py, loading_trace04.inc. Decoder trace04.py and
three schema checks cover wrap, pending/failure and corrupt evidence. Build uses
one serial eZ80 assembly plus bounded layout/source/decoder checks, Pi FIFO
assert before each child,80C/512MiB guards,120s assembler/60s checks and300s whole
build envelope; no native compile/emulator/hardware. Sources frozen under ignored
build/hardware04; native A is retained unchanged c5cfaaed91a0d294bbe30811ca57ff36a585d070946f0813a469412f57d77fcc.

## Exact binding and unresolved admission

Extender21:14:06EST return identifies EMOS sourcec9c8b6be316b5ebb64da1f16773ec3c886349267,
131072B ROMb5a1f4aa3b9f4527aafb5f48aa29445c3e30962c5b21382729c370944b043b02.
Last verified P4 appa967fac2e1364e5c1d80964ed5e8183feee693e4f63c256a02654dc8482e6eee,
1764128B,source221e6207cc25adab344adb7adffe822ada1fbbda. RST18/Legacy PUTCH, APIs40/41
and reply parser path are unchanged versus5735812. New optional25h admission
contract is not used. Generic parallel carrier repair is separate from this fault.

Private ordinary RAM: serialFlags0xBC35A; backend0xBCB25; sysvars0xBC322 with
clock+0/modeflags+4/mode+0x27; callback0xBC38E3B; EMOS reply parser0xBC378..0xBC38D.
These must match exact ROM/map, not be assumed from historical hardware42.
Native20029942 and startuped403/listener0566 are last verified handoff only:
MechAgon43 remains current owner and may replace native. Reconcile its actual
release, full then-current component identities/rollback/tail and Extender fresh
entry before ready/grant. Do not use old grant or freeze guessed incoming pins.

## Finite physical selection, after preparation/admission

One fresh checkout, up to FOUR explicit LOAD/RUN invocations of this same
loading-only binary, sequential. First unexpected result stops all successors.
Each invocation bounded300s by host; no autoexec or automatic rerun. Stop new dispatch by30min, reserve up to10min for normal restoration/handback;
expected20min overall. An uncertain/hung operation retains custody for reviewed
recovery rather than forcing an unsafe release at a wall-clock limit. No B arm/INFO/render benchmark/audio. Success requires normal
post-RUN MOS return, loading470/error0, trace schema/ring integrity, main-returned
and loading-ready markers, mode0/callback0 after normal shutdown. Four passes
mean no failure observed in this tranche, not a transport fix or performance pass.

Stage into fresh /test/wolf/perf003/load04 using the current owner-bound
transfer procedure; refuse an existing namespace rather than overwrite. Preserve
prior SD evidence/config, verify independent GET bytes. Preserve normal startup/listener, unknown files and journals. No
reset while another application may own storage. Retain existing native A app
installation for all four loads; no intervening native reset/flash. One selected
native-only candidate write and exact restoration of the actual incoming image/
touched tail; no P4/EMOS/startup changes. Rehash retained backups rather than
habitual whole-device reads. Freeze exact image/write spans with current context.

On normal setup failure, capture RAM BEFORE any LOAD and retrieve both diagnostic
files/serial, then restore. On blocked/no-return host deadline, stop dispatch,
retain custody/raw capture and use the already-authorized recovery procedure
only after preserving available evidence and source review; no blind RESET/RUN.
An outer PUTCH/CTS wait can block beyond internal TX_WAIT. Never label host
termination application cancellation or assume the send did not execute.

Finish with exact incoming native app/tail independent readback, normal CLI/
mode0/callback0, original startup/listener fullcompare, neutral input, idle staged
worker/offline listener, joined owned USB readers/reset holders and free ports.
Leave SD mounted. Fresh release through central registry; notify Extender and
actual next owner immediately. Release before offline analysis.

No target calls are authorized by a PREPARING reservation alone. Current
component/source/resource/entry checks and fresh actual token remain mandatory.

## Preparation result

Actual Pi193 checkout/assert completed one assembly and decoder/source/layout
checks, then released at21:18:50EST Nov5, nextnull. Guest314228B
SHA9c07b14240835e121089455bf17809ec7eea8a643d89cd7550f6943b4c67baf5.
WPQ3 is4288B; zero initialization and no reachable wp_run verified in assembled
layout/source. Three decoder and two actual-controller terminal-path host checks
pass. Retained EMOS maps/ROM/P4/nativeA were independently rehashed offline;
private RAM addresses match map. Current incoming native/tail remains unbound,
so candidate-kit.json is ready=false and physical04 refuses construction.
No target call, emulator run or firmware write has occurred.
