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

## Why the original failure remains open

Hardware03 failed on a later load after real CPU/unpaced-render fixtures. These
four invocations exercised loading repeatedly without intervening renders, and
used newly installed experimental EMOS8270 plus observer hooks and different
loading hint text. The relevant Legacy sender/wait/parser sources and private
addresses are independently unchanged, but neither timing perturbation nor
allocation/render history is controlled away by that source check. Four passes
therefore cannot clear003-16 or prove native receiver correctness.

## Restoration and preservation

Actual44 released23:51:00EST Nov5 /04:51:00UTC Nov6, next_request:null. Exact
incoming native20029942 app1101408B and necessary touched-sector tail independently
restored/read back. Experimental EMOS8270/P4a967/startuped403/listener0566 preserved;
fresh CLI/mode0/callback0/unchangedfiles/neutralinput/offlinelistener/idleworker/
joined actors/freebothUSB checks passed. Extender received immediate durable mail
and steering handback. No Wolf lease/reservation or target actor remains. SD
stays mounted.

Evidence stays under ignored build/hardware04: final-selection43.json,
rebind43.json, incoming43.json, kit.json, analysis44.json, physical44.log,
release44.json and evidence/{01-loading..04-loading,flash-a-loading,flash-restore,
handback,stopped-restored.json}. Full RAM can contain derived game assets and
machine-custody records remain local. Code/plans through bae8b2e were pushed.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
