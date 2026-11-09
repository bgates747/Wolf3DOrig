# WOLF-FW-002 — Current-release preparation migration

> Historical b004-release result. The same tag was replaced by async-r1; see
> [the current amendment result](AMENDMENT-01-RESULT.md). Original evidence below is preserved.

The routine Wolf build and deployment preparation now select VDPlet
v0.1.2-alpha and Eirene RC3 where applicable. The plan was frozen/pushed as
`444138e` before implementation. This task changes preparation and the finite
client fixture; the optimization goal remains paused.

## Changes

- One release verifier checks the pinned VDP SHA256SUMS and every listed asset,
  the exact VDP BIN/decompressed ELF, and the Eirene ZIP/exact MOS member.
- The game CLI defaults to `vdplet-direct` with the retained maintained
  production module `266f809f`. A separately selected native-profiling build
  uses optimized module `8d3d`; it is not a production-default promotion.
- Each assembled application has its own module copy and receipt. Complete
  payloads include all ten levels, shared assets, module and build identities.
  Generic and SD deployment paths require the verified standard payload.
- New Alexe profiles include the actual release BIN/ELF and MOS BIN/map and
  record the explicit existing frontend/backend hashes. Startup loads the
  application without RUN. Preparation never executes the emulator.
- The finite copied-client fixture supports the current profiling include and
  owns staging sized for its module, largest uploaded file and zero-buffer
  scratch. The builder checks actual linked addresses and materialized bytes.
- Thirty-two maintained historical Fab/stage/rehearsal entrypoints require an
  explicit firmware/model exception reason. Existing scope and normal scheduling
  remain required; the flag itself grants no workload. Frozen cohorts are intact.
- The Olimex selector helper reads the owner's current desired selection and
  explicitly does not claim installed state, admission or a grant.

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

No firmware was flashed, emulator run, SD written or hardware contacted. The
new combinations still need an actually selected runtime test on the target,
normal current-state/resource admission and existing human-start boundaries.
Static ELF checks do not prove allocator fit, whole-task stack or runtime
controller compatibility. Olimex resolves its approved integrated EMOS at
admission and reuses verified standard firmware; historical private7593 and
incoming85f9 controllers are not revived. No async feature or new optimization
is selected. SD remains unchanged and mounted as found.

Use [the current preparation commands](../../../../tools/README.md) for later
preparation. Never infer a run or deployment authorization from these outputs.
