# Actual uncapped visible rotation under held77

**Uncapped result:30.06 nominal presented frames/s**,600 frames in19.958 PRT
seconds /19.983 MOS seconds. Smith manually started the loaded guest and
confirmed both turns visibly appeared. There was no agent RUN and no synthetic
frame-pacing wait. Each completed render was presented and fenced before its
presentation timestamp was recorded.

| Measure | Previous30Hz-paced run | Uncapped run |
| --- | --- | --- |
| Presented frames | 600 | 600 |
| Nominal whole-run FPS | 30.012 | 30.063 |
| Nominal PRT duration | 19.992s | 19.958s |
| Mean presentation interval | 33.270ms | 33.269ms |
| Median /p95 /max interval | 33 /34 /34ms | 33 /34 /34ms |
| Steady interval rate, excluding first frame | 30.0567/s | 30.0582/s |

The sustained cadence is effectively unchanged. Removing pacing shortened the
whole run by34ms, approximately the initial paced wait; the summed599 intervals
differ by only one nominal millisecond. The30Hz pacing cap was not restricting
ongoing cadence in this fixture. The current complete render/transfer/present
path takes roughly33.3ms per update. This result does not isolate which portion
sets that cadence or establish a different uncapped renderer-only throughput.

The exact latest optimized modulea926b48a24420B is unchanged. New guestc43e7fe7
uses explicit mode4, sequential poses1–600, the same720degree angle table and
the physically qualified per-frame C3/ordered-fence method. The former paced
wait is absent. Both turns take the measured execution time rather than a forced
twenty seconds. This is the existing enemy-free E1L1(34,36) room and viewport;
it does not establish performance for every gameplay scene. PRT/MOS use nominal
clock assumptions and agree within0.13%; no external oscillator or frame-by-frame
optical calibration is claimed.

Previous SD outputs/config were preserved using supported metadata MOVE into
/test/wolf/perf011/r01/paced77-results before active output names were reused.
All previous host binary hashes still match. The immutable original fixture and
30Hz results remain separate. Original accepted deployment/collection failures
were not replayed. The new LOAD-only controller exited with all actors closed;
Smith received the application-question notification and issued RUN . himself.

RESULT.json contains raw-file hashes, source/runtime joins, comparison and final
observation. Small raw outputs, CSV and original decoder/collection/handback
receipts are in results/uncapped77/. Complete serial/transport/flash/RAM evidence
remains in build/hardware01/evidence/.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
