# Original ray-walk method improves the collected physical timings

The original tangent-table/intercept method draws the same600pose room fixture
in26.97ms and26.67ms per pose, versus32.24ms for the existing ray walker. These
are actual ESP32 draw brackets at configured240MHz, including any preemption.
Completed fixture throughput is32.83/33.15FPS versus28.01. The candidate's
900entry lookup table replaces per-ray reciprocal-division setup; general
arithmetic providers, O2/PIC/PSRAM-safe flags, projection/compositor, native7593,
assets, player tile34,36 and suppressed enemy population remain fixed.

| Collected observation | Poses | Mean VDP draw | Draw p95 | Draw maximum | Completed fixture FPS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current ray walker, baseline03 |600|32.2366ms|33.1179ms|33.3683ms|28.0099|
| Original method, candidate04 |600|26.9676ms|27.4053ms|27.5646ms|32.8335|
| Original method repeat05, salvaged |600|26.6716ms|27.0927ms|27.2784ms|33.1528|

Candidate mean across1200records is26.8196ms:5.4170ms/16.80% less draw time
than the one600record baseline. This is a descriptive unbalanced comparison;
scripted frames are correlated and the reverse-order baseline06 was not run.
The original-method change intentionally alters some rounding, corner ownership
and texture-column orientation; this does not isolate dispatch/provider cost or
require identical old-port pixels. The native draw bracket is distinct from
whole-fixture throughput. Candidate whole-command means are27.5592/27.2436ms;
nominal PRT elapsed includes the complete fixture path. Neither establishes
universal gameplay FPS, paced30Hz guarantees, external clock or optical timing.

## Why the full comparison is incomplete

The two untimed controls and baseline03/candidate04 pass complete collection,
actual source/listing/binary/RAM producer operands, eZ80 entry/exit SP,470assets/
952fences with no loading errors/timeouts, actual CLI return and cleanup. Five
resource probes pass with zero active module slots/render leases, cumulative
command-task watermark minimum2020B. Five module replacement chains verify
previous/selected/backup bytes and supported state1→9/RECOVER3→1 retirement.
Watermarks are cumulative endpoint observations, not per-arm whole-call peaks;
resource memory halves are non-atomic. No post-repeat05 probe was run.

Repeat05 returns COMPLETE/UNLOAD0/CLI, and loading/trace/before RAM snapshot
collect. The following GET after.bin fails with P4Protocol3 after230256 of
305873bytes, records1069, exactboot2910473983/job3215372350. The controller stops
before baseline06 and does not retry the failed GET or replay a fixture. Exact
retained source plus counters narrows rejection to READ reply body length or
advertised file size; rejected raw response is absent, so cause remains unknown.
No renderer, media, UART corruption or filesystem cause is established.

The strict complete-cohort decoder still rejects missing complete.json. No
completed ABBA/pass marker is manufactured. Actual72's earlier host-interpreter
import failure is preserved separately and contributes no rendering timings.

## Artifact, restoration and handoff

Control cd429e2f is20928B; candidate c8f99354 is24276B, an increase of3348B.
Executable text shrinks300B and resident data grows3600B for the tangent table;
four extra relative relocations account for the remaining48B. Both retain the
same safety policy/providers/ABI1.6 and maximum individual static768Bframe.
This is a qualified task candidate; the production/default module is unchanged.

Actual73 used frozen5eb6d84/0528ed13 with486input hashes. All486selected inputs
were rehashed and snapshotted byte-for-byte after release before task status
edits.135binary evidence files plus original failed journal, fresh terminal/idle
status, metadata and raw serial receipts are retained under build/hardware02.
PARTIAL73-RESULT.json and report_partial73.py recheck the raw1800records,
producer/module/lifecycle/guard/resource/source joins and full restoration.

The implementation and offline/visual boundaries pass; physical observations
support a useful improvement. Full balanced confirmation remains unresolved by
the collection failure. Preserve that dependency with Extender before selecting
any further target cohort; no blind full replay or default adoption is inferred.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
