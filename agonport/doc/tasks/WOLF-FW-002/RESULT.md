# WOLF-FW-002 — Current-release preparation migration

> Historical b004-release result. The same tag was replaced by async-r1; see
> [the current amendment result](AMENDMENT-01-RESULT.md). Original evidence below is preserved.

The routine Wolf build and deployment preparation now select VDPlet
v0.1.2-alpha and Eirene RC3 where applicable. The plan was frozen/pushed as
`444138e` before implementation. This task changes preparation and the finite
client fixture; the optimization goal remains paused.

## Changes

## Verification

The final r05 tranche passed: actual finite-client assembly, 23 finite-client
wire/storage/ownership checks, and 36 preparation/profile checks (59 total).
The latter cover release/module/payload mismatches, complete asset bindings,
stopped profile preparation, actual legacy-help refusal and all 32 guard paths.
[Compact evidence](EVIDENCE.json) records commands, identities, attempts and
actual compiler cleanup. These Python/model checks do not emulate eZ80 code.
The standalone disabled-profile control is byte-for-byte identical to the
retained binary: 276641 bytes, SHA256
`063f7ab7b9b2df44fe1541871662ce7656c3c28d6693872de824c5bfce40a2e6`.
The earlier normal game, native-profiling game and standalone control assemblies
passed in r01. Four finite-client preparation failures are preserved locally:
forward label in an EQU (r01), source-stem listing filename mismatch (r02),
omitted trailing DS bytes (r03), and the assembler’s FF-filled DS region (r04).
The final source uses explicit generated zero data instead of DS. These
source corrections are separate from runtime outcomes; no emulator/device run followed these failures.

## Prepared local outputs

- `tgt/wolf3d-standard`: maintained production game, all ten levels and module.
- `tgt/wolf3d-optimized-profile`: selected optimized native-profiling game.
- `tgt/wolf-finite-client`: corrected copied-client fixture, 20 declared files;
  its 94704-byte application owns a 92160-byte materialized staging area.
- `tgt/profiles/normal-release-x86`,
  `tgt/profiles/optimized-profile-release-x86` and
  `tgt/profiles/finite-release-x86`: stopped release-firmware profiles.

Each game payload declares 68 files plus its manifest. No accepted historical
payload was overwritten. All compiler children joined and slots were released;
no resource lease is retained. Peak recorded CPU temperature was 52.9°C.

The x86 profiles use existing frontend `c987fafc` and backend `0866265b`, copied
and hashed without execution. Firmware verification does not newly qualify
those executable/backend binaries. Generated assets, firmware and binaries stay
local/ignored; compact identities and results are published with this task.

## Remaining boundaries

Use [the current preparation commands](../../../../tools/README.md) for later
preparation. Never infer a run or deployment authorization from these outputs.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
