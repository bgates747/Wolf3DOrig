# Loading04 hardware result — four passes, fault not reproduced

All four selected loading-only attempts passed under actual Olimex44. Each
loaded470 assets, completed952 fences with zero public-wait timeouts/recoveries,
returned normally to MOS and preserved full app RAM before the next LOAD.
Both diagnostic files matched captured RAM/format checks. No warmup, render,
PRT measurement, retry or recovery ran. This is **not a fix or a frame-rate result**.

| Attempt | Assets | Fences | Timeouts | Maximum fence raw MOS ticks |
| --- | ---: | ---: | ---: | ---: |
| 1 | 470 | 952 | 0 | 14 |
| 2 | 470 | 952 | 0 | 4 |
| 3 | 470 | 952 | 0 | 2 |
| 4 | 470 | 952 | 0 | 4 |

The32 retained final fences per attempt (128 total) show MBASE0, backend0,
serialFlags0x33 before/after query, return A0/BC0/HL=query+3. Query transmit-call
and C3-call timestamp deltas are0 ticks in these retained records, meaning below
nominal8.33ms counter resolution, not zero duration or externally calibrated
wall time. The longest retained wait is14 ticks (~116.7 nominal ms). Sender
status/pointers do not prove per-byte wire delivery or VDP parser state. Reverse
EMOS reply-parser RAM snapshots remain non-atomic. No stray0x86 appeared in any
of the four complete USB serial captures. The ring does not retain timings for
the earlier920 fences in each successful run; WPL2 timeout/max counters cover
all952. Host invocation/listener times around62s include command/observation
work and are not isolated asset-transfer benchmarks.

## Why the original failure remains open

Hardware03 failed on a later load after real CPU/unpaced-render fixtures. These
four invocations exercised loading repeatedly without intervening renders, and
used newly installed experimental EMOS8270 plus observer hooks and different
loading hint text. The relevant Legacy sender/wait/parser sources and private
addresses are independently unchanged, but neither timing perturbation nor
allocation/render history is controlled away by that source check. Four passes
therefore cannot clear003-16 or prove native receiver correctness.

The next useful preparation is to retain the observer in actual benchmark
clients, preserving their measured loops and original loading text, so a failure
after rendering preserves the missing sender evidence. Select/freeze a fresh
finite cohort before any new build/run; do not blindly rerun hardware03 or call
this a repaired transport. The matched A/B/B/A comparison remains incomplete.

## Restoration and preservation

Actual44 released23:51:00EST Nov5 /04:51:00UTC Nov6, next_request:null. Exact
incoming native20029942 app1101408B and necessary touched-sector tail independently
restored/read back. Experimental EMOS8270/P4a967/startuped403/listener0566 preserved;
fresh CLI/mode0/callback0/unchangedfiles/neutralinput/offlinelistener/idleworker/
joined actors/freebothUSB checks passed. Extender received immediate durable mail
and steering handback. No Wolf lease/reservation or target actor remains. SD
stays mounted.

**Span correction:** the actual frozen kit selected1101824B at0x10000, the sector
ceiling of max(incoming1101408B,new1090464B). Earlier plan prose/readiness mail
said1105920B, which is MechAgon's larger retained readback span. Its final4096B
were never touched by Wolf. Both selected write/read spans matched exact kit
bytes; restored span SHA0531885fa1ad2477c021481dbf5537abc6031dc9bd253fa4dd7212ff2f9788a6.
Original frozen plan/kit/selection evidence remains unchanged; this is the
post-release correction. No broader write or fresh full-device backup occurred.

Evidence stays under ignored build/hardware04: final-selection43.json,
rebind43.json, incoming43.json, kit.json, analysis44.json, physical44.log,
release44.json and evidence/{01-loading..04-loading,flash-a-loading,flash-restore,
handback,stopped-restored.json}. Full RAM can contain derived game assets and
machine-custody records remain local. Code/plans through bae8b2e were pushed.
