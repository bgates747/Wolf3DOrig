# FX-153 native host return review

Reviewed return2026-11-05_13-23-56_flexe_wolf-perf003-fx153-host-return-109.
Receipt SHA412a99c6eb0655d99eada396a8c256fe052757bac22eac5e960fc9222f32ee5a
matches. Independently verified all228 source hashes, all eight host evidence
hashes, reader691e2b98 and source-diff hash. Comparing actual base/current files
confirms exactly src/uart_progress.rs changed;227 other files remain identical.

Actual source follows the reviewed split: phase publishes six values, full
batch writes retain the same version boundary, entered publication closes
before original calls, and Snapshot passes by reference. Actual store-site
hooks are cfg(test), as are their counters; release-binary audit remains open.
Real-path tests cover zero phase TX/batch writes, new equal-value tags, None/
epoch transitions and concurrent tagged records; existing blocked-call/history/
accounting/forwarding tests remain. The strict reader requires fx153-tx-v1 and
the owner_batch metadata marker.

Retained logs confirm15 observer,28 library/UART/machine and14 strict reader
checks passed. Progress/Snapshot208B are asserted. Unchanged TxState120B is
source evidence, not a separately measured result from this tranche. Actual
serializer output is schema-valid/finalized but timing-incomplete; it is
synthetic host evidence, not a live stall sample. No repeated tests were run
by this review. Compiler was native ARM64 rustc1.85.1, unlike the old Oryx
artifact's compiler; native host passes do not qualify an Oryx executable.

Preserve the reported sequencing defect: the first sandbox assert-owner failed,
but the runner began before successful native assert completed. A valid auto-
grant existed and the later assert confirmed unchanged ownership. This does
not erase the preflight defect or turn later validation into prior admission.
Before any future compiler/test launch, the actual successful assertion must
be a sequential prerequisite; failed assertion must prevent child creation.
Retain this original receipt. No rerun is selected merely to replace its history.

Technical source/native-host results are accepted for the dependency's next
preparation step, with those limitations. Pi149 released18:22:54UTC,nextnull.
No x86_64 artifact exists. Verified Pi has no ~/.cargo/bin or ~/.rustup, only
native /usr/bin rustc/cargo and ARM target libraries; no qualified x86 linker/
target route is established. No installation or compiler route substitution
has been performed.

Request offline preparation of one exact stopped Oryx release build and a
read-only environment-owner check for an existing qualified route/policy
disposition. Source/host review does not itself authorize Oryx compilation:
Smith's actual2026-11-05routing message assigns compiler work to Pi. No build,
emulator, hardware, runtime adoption or publication is selected here.

## Concrete routing decision ready

Environment owner's13:28:41reply found no already-qualified Pi x86 Rust/SDL
route or actual standing human Oryx compiler fallback. Original routing is
unchanged. Flexe's13:30:09offline return supplies a stopped one-build package
cc8fc6e1aaf28fb306a7a35bb2df4f0bf9817f1cee54ae09b01155c69e123b78.
Independently checked its archive hash, all228 archived source hashes and
build-script8aea1cbf/runbook1b19b2af/source-manifeste1d3186b identities. No
compiler, unit test or emulator was run during this package review.

Read the actual unexecuted driver. It synchronously asserts a fresh flexe
Oryx lease before child creation, verifies source and existing native toolchain
pins, checks initial/one-second Tctl80C/unavailable-sensor/512MiB limits, uses
one serial offline/locked x86_64 release build and bounds it at1200seconds.
It leaves boost settings unchanged, joins only owned groups and inspects
ELF/symbols without executing the frontend. Full linked-library resolution,
source/cfg(test) audit, retrieval/hash, fresh idle/release and successor steer
remain required owner post-build steps in the runbook. Its guard is statically
reviewed, not execution-qualified; first unexpected failure stops the attempt.

Only remaining pre-build decision: Smith's approval for this one native Oryx
compiler-routing exception under normal FIFO, maximum20minutes. The actual
source/guarded command/resources/cleanup are reviewable at
flexe-agon-emulator/docs/tasks/FX-153/ORYX-BUILD-RUNBOOK.md. No reservation,
transfer, build, target cohort, installation or deployment has been selected.

## Direct human routing approval

Smith replies in this Wolf chat on2026-11-05: "oryx compile approved."
This answers the concrete one-build exception question: Flexe compiles the
reviewed diagnostic once on Oryx under normal FIFO, maximum20minutes. Package
cc8fc6e1, source228-file receipt412a99c6, guarded script8aea1cbf and runbook
1b19b2af remain the selected inputs. Proceed through fresh reservation/idle/
checkout and successful sequential assert before any compiler child. Preserve
first failure and normal retrieval/cleanup/release/successor notification.

This exception does not change general compiler routing or select emulator
execution, another build, hardware/firmware work, adoption or publication.

Original source verified via read_thread: Wolf thread
01a1a67f-c3b5-76a2-9eef-66047be3dea3, turn
01a1ad0a-8ac5-7b70-b578-5b3457da55e8, human message
01a1ad0a-8b2d-7683-91b8-e12baaaaf935. Approval/scope relayed to Flexe in
2026-11-05_13-49-13_wolf3dorig_wolf-perf003-fx153-human-oryx-build-approved-one
with immediate accepted Pi steer including those original IDs.
