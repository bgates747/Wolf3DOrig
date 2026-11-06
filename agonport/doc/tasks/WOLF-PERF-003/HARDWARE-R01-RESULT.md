# Hardware01 — setup failure, no benchmark result

Olimex40 was granted23:06:29UTC and cleanly released23:23:05UTC on2026-11-05.
All20 staged files passed independent full GET comparisons. The new bespoke
A85c520a1 application and affected sector tail were written at0x10000 and the
entire1105920B written span independently read back and compared. Boot returned
to actual CLI, mode0 and callbackzero. P4/EMOS/startup were retained.

The first A restoration-control fixture failed during HUD loading, after28
HUD records and409 total assets. It printed `AGNB texture load failed; render
not submitted.` and returned to the actual MOS prompt. The control never
reached wp_run, PRT initialization or timing. No performance result, B-image
test or subsequent fixture/probe is claimed.

The runner initially kept observing because its terminal-error matcher omitted
this early-return path. Only the owned host controller was interrupted; its
passive reader closed and further dispatch stopped. No target input, reset or
test replay occurred in stopping observation.

Before any LOAD or collector, current app RAM was saved through MOS and
retrieved. The HUD container was independently retrieved and still matches
the original. RAM SHA256:
`c7275a1e1d78838b8b6ec7f3b3d1bddd186fb1feb0b36a039afd0d8d5a5faf59`.

| Saved field | Value | Meaning |
| --- | ---: | --- |
| agnb_last_error | 14 | Application callback aborted loading |
| wp_loading_error | 1 | Breadcrumb ingress fence failed |
| wp_loading_count / total | 28 / 409 | HUD phase / complete assets |
| wp_owned / wp_expected_abort | 0 / 0 | Timer/control never entered |

The final count28 appears on only the first page's print stream: the first
post-presentation ingress wait failed before the second page was reconstructed.
This does not prove corrupt assets, exhausted texture memory, a lost packet or
a particular receiver defect. The current helper uses one public MOS0x41 wait.
Exact installed5735812 implements that wait as a250000-iteration volatile polling
loop described as approximately one second, rather than a clock deadline.

Recovery preserved the failed RAM without LOAD, then restored the exact original
native app and touched tail from locally rehashed retained rollback. Independent
readback, fresh CLI/mode0/callbackzero, startup/listener comparisons, neutral
input, offline idle services and free serial ports passed. The SD card remains
mounted. No broad device backup/reread, P4/EMOS/partition/NVS/other-slot write or
automatic replay occurred. Extender received substantive failure and clean
release mail; next_request was null.

Evidence: `build/hardware01/evidence/{01-bespoke-control,failure-collection,
flash-a1,flash-restore,handback}` and `release-complete.json`. The first release
attempt's relative evidence path was rejected before mutation; status confirmed
custody, and the absolute fresh path then released normally.

Next owner correction: keep both-page breadcrumbs and their parser ordering,
but diagnose and finitely continue waiting for the SAME already-issued setup
fence instead of aborting on the first approximate wait-loop expiry. Record
timeouts/elapsed/phase outside timing; never resend a timed render or silently
extend its deadline. Recognize early setup failure immediately in the controller.
Preserve this failed tranche; identify changed guests and a new finite reservation.
