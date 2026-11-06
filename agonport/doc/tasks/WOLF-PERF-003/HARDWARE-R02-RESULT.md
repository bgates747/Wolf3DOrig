# Hardware02 — one completed bespoke measurement, suite stopped

Olimex41 was cleanly released at00:04:56UTC Nov6 (19:04:56EST Nov5).
Incoming native20029942 application and touched tail were restored exactly and
independently read back. Fresh CLI/mode0/callbackzero/startup/listener/input/
idle/freeports checks passed; SD remains mounted. No target custody remains.

The new loading-only candidates assembled and passed offline checks on Pi168,
then staged through independent full-file readbacks on fresh Olimex41. Native
A85c520a1/B7593b9cf/module1907ce17 and all timed source remained unchanged.
Four applications were invoked once: three passed, the fourth stopped before
its measurement. No B image or B guest/probe was invoked. No paired comparison,
paced throughput, optical correctness or external clock calibration is claimed.

| Completed case | Work | Result |
| --- | --- | --- |
| A restoration control | Intentional owned-timer abort | Restored and returned to MOS |
| A CPU | 600 scripted poses/packing | 676 PRT ticks; 80 MOS ticks; about888 poses/s |
| A unpaced | 600 completed hidden renders | 19794 PRT ticks; 2380 MOS ticks; about30.31 completed renders/s |

CPU pose+packing averages1.12 nominal ms; this excludes populated-world game
simulation. Native unpaced draw averages7361728.2 CCOUNT, or30.674ms at the
source-configured240MHz; the corresponding complete-frame cycle averages32.990ms.
PRT is nominal1ms/tick, MOS120units/s. These are one-pass results, not a completed
A/B/B/A cohort. The VDP draw interval and completed-frame rate are distinct.
The failed fourth case supplies no paced timing record.

All four applications finished loading all470assets with loading-error0 and
zero recorded loading wait timeouts. The three completed loading records each
cover952 ordered fences. The fourth's fields survive in saved RAM. Thus the
old HUD409 failure did not recur, but no delayed reply exercised continuation;
this does not prove the cause of the earlier loading failure or a permanent fix.
Both-page progress bookkeeping is retained.

The fourth guest, A paced, printed `WOLF-PERF-003 FAILED TIMER-RESTORED`. Its
failure routine deliberately holds; the host stopped dispatch/closed its reader,
with no automatic successor. Reviewed installed5735812 init.asm warmboot path,
verified unchanged setup-only startup and performed one standing ordinary Agon
recovery. No P4 reset, test replay or collector LOAD. Saved309014B app RAM through
MOS before any LOAD, checked the executable prefix remained intact and retrieved
available before.bin. The reset reinitializes MOS/VDP state; retained app fields
are evidence, not a live CPU/VDP snapshot.

Saved state narrows the failure to the FIRST map-binding warmup completion wait:

| Field | Saved value |
| --- | ---: |
| wp_n / wp_count / wp_prt_start | 0 / 0 / 0 |
| wp_ticks / wp_owned / wp_restored | 2026 / 0 / 1 |
| wp_loading_total / error / timeouts | 470 / 0 / 0 |
| render_in_flight / async_owner | 1 / 1 |
| completion_ready / callback_error | 0 / 0 |
| sequence_initialized / expected_sequence | 0 / 0 |
| completion_record / snapshot | Ten0xff bytes each |
| task control cookie | 0 |

No completion was captured before the existing240-MOS-tick wait expired.
Paced sampling and its presentation loop never began. This does not identify
whether the render request, renderer, return transport, EMOS admission or
callback capture failed; no native-side trace survived the recovery reset.
Do not turn it into evidence that paced drawing itself is slow or broken.

Evidence is under `build/hardware02`: frozen792-pin kit, eight build/layout
checks, individual passed case receipts/rawCSV/native counters, fourth guest
serial/failure record, `paced-failure-collection/{ram.bin,decoded-fields.json,
receipt.json}`, exact restore readback, fresh handback and release.json.
`physical-summary.json` explicitly says complete=false. Initial fake-serial
check setup omitted its remote attribute; corrected check passed before readiness.
The report02 draft initially pointed to hardware01; its path was corrected and
hardware02's saved raw results regenerated without target action.

Next task is source localization of the initial warmup completion loss, with
phase-specific diagnostics and a finite identified qualification plan before
another reservation. Do not blindly replay the stopped suite, alter measured
wait semantics, or treat this as the previously observed Flexe asset stall.

## Subsequent source finding — recorder lifetime

NativeA's task recorder retains a raw pointer/count after the guest clears
buffer0xf000. Its unchanged finish method rejects count>=600; render_frame
returns false before send_render_complete. The preceding unpaced case fills
exactly600 records and clears that buffer. The next first warmup therefore
cannot publish completion. A preceding CPU case leaves count0 plus a dangling
pointer, potentially writing freed/reused storage during the next warmup.
This is task instrumentation, not an established production or EMOS defect.

This also makes the earlier unpaced timing PROVISIONAL until repeated with a
defined lifetime; record correctness alone does not prove prior heap ownership.
HARDWARE-RUN-03.md selects explicit acknowledged release before log replacement
and deletion, with repeated real-control-method sanitizer regressions before
qualification. No new hardware result or completed fix claim yet.
