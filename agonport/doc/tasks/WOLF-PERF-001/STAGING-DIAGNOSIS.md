# Package staging overlap found during qualification

R02, R03 and R04 completed the CPU recorder but panicked at normal gameplay
shutdown's first `w3d_audio_stop_channels` call. None is a performance baseline.
R03's register preservation did not change the failure.

R04 captured loaded application memory before and after the benchmark. At
`0x0626E6`, the expected audio prologue is:

```text
DD E5 CD EF 26 06 DD E1 C9 CD 4F 24 06 AF 32 4A
```

Both guest snapshots instead contain:

```text
87 40 40 F4 1C 66 47 36 02 06 A9 00 0C 3A 46 C7
```

These bytes match the diagnostic Xtensa package at offset `0x26E6`, proving
that the package load to the source client's fixed `0x060000` staging address
overwrote eZ80 executable code. This happened before the fixture's timer and
pose loop. The entry and exit stack pointers both equal `0x0BFEE5`; the audio
bytes do not change during measurement. The main shutdown code at `0x086562`
remains intact, explaining why it reaches the overwritten audio target.

The package-staging page is also reused by the production zero-buffer helper.
It must remain disjoint from all live application code/data, not merely fit
the module upload length. The current production source still declares the
fixed address; this task does not modify that shared source or claim anything
about an older deployed build.

R05 changes only its copied client include to stage at `0x0A0000`, and reduces
the accepted package limit to the known package length plus one. The builder
rejects an application reaching that address or a package reaching `0x0B0000`,
leaving the upper 64 KiB reserved for MOS stack use. Each mode emits a memory
layout receipt. Snapshot capture stays outside timing to verify the repair.

Raw rejected evidence is retained in ignored `build/evidence/r04-cpu/`, including
`before.bin`, `after.bin`, `stack.bin`, the exact application, assembly listing,
timing file and UART logs. Oryx generation 275 was released after owned process
shutdown and retrieval; there was no queued successor.
