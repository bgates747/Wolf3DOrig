# Fab asset-loading comparison — 2026-11-05

WOLF-PERF-003-10 [x] Smith requested a reserved Oryx trial in Fab.
One actual guest trial passed the asset-loading boundary in24.846 seconds.

Same r05 A CPU guest9e3e7522a70f7b254db18365406adaab92ab0029c6995ee1b3a4dd6e5a4474b4,
all payload assets and MOSd5642432 as failed p02. Existing official Fab1.2.5
executable aec5f8c266117d5bf864c6124d3c8986d042802ed5cbaaf8813e04a9fb8d0bea,
native userspace Wolf library5c4e4b9bf6b58ade665b1d19f87697b54d08113a0962b3fe946bf899a1d49e2f.
This replaces BOTH Flexe host and ESP32-executed native VDP with Fab/native
userspace VDP. It isolates neither host alone nor one UART implementation.
No compiler or source change to guest/assets/native library. Full pins,
script freeze and raw outputs in build/fab02.

Success is a fresh before.bin at wp_run entry after shell/audio/level assets
and initialization, before task-specific native recorder operations. Retained
293942-byte before.bin SHA68b2eeffd7778f8e1823a159ee0bc45e6c586dc1c353bb13a36e5067f5ebe779.
No benchmark render, CCOUNT comparison or full gameplay qualification claimed.
Capture/normal SDL Quit completed; return0, whole25.661s. Peak61.375C across26
host samples, unchanged80C/300s/RAM guard and standing boost0. The same guest
was allowed up to300s, not forced to match25s.

The first setup fab01 was rejected by the strict wrapper because preparation
omitted .runtime.sha256, before Fab or guest execution. Preserved raw failure;
fresh fab02 corrected only that host manifest. No failed guest replay hidden.
One successful run cannot rule out an intermittent Fab issue or establish a
Flexe root cause. Original p02 upload stall remains unresolved.

Actual Oryx311/requeste1447e1311ef, ownership asserted before each launch.
Fifteen retrieval hashes verify, ordinary workers joined, fresh whole-host idle,
release19:54:58UTC,nextnull. Boost stays off; no hardware/firmware operation.
