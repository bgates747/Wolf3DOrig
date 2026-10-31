# Bounded Wolf3D VDPlet proof

The top-level sources in this directory own G057-WLF-001, the first
deliberately bounded proof of the Wolf3D renderer running as a VDPlet. They are
isolated from the production eZ80 game and preserve the standalone renderer as
their oracle and rollback path.

Production work now lives separately under `production/`. Its generated
schema-1 C++/assembly contract and pure 5,360-byte world mirror implement
exact descriptor validation, bounded atomic full/dirty batches, generation
ownership, and same-batch retry after failed publication. See
`../doc/wolf3d-vdplet-production-contract.md`. Its pure renderer now matches
the standalone oracle for the play surround, DDA, grouped wall assets, moving
doors/jambs, actors, statics, rotation frames, alpha, depth order, and wall
occlusion. HUD/weapon composition and the real module wrapper remain under
construction; the standalone backend remains the default.

## What the proof exercises

`wolf3d_scene.cpp` is a real freestanding ABI 1.3/capability-17 module. CONFIG
copies and releases a 24-byte argument buffer into a compact 28-byte mirror.
RENDER then holds exactly three leases: a 92,160-byte writable workspace, a
4,096-byte tilemap, and an 8,192-byte wall/sprite texture set. It raycasts the
production 256x160 centered view, draws a wall texture and one occluded static
billboard into a complete 320x240 RGB222 frame, performs one synchronous
`pixels_write`, releases every lease, and returns. INIT/FINI retain no external
pointer.

The generated 901-entry quarter-wave sine table replaces the standalone
renderer's two 3,600-entry arrays. DDA columns and software composition retain
the accepted fixed-point formulas. The local `__divdi3`/`__udivdi3` helpers
are intentional: the pinned linker crashed when the otherwise tiny module
pulled the broad libm/libgcc pair, while the renderer needs only bounded
64-by-32 integer division.

## Durable build and host parity

Run from the Wolf3DOrig repository root. The GOLEM-057 proof uses the frozen
ABI 1.6 SDK snapshot rather than Golem's mutable development checkout:

```bash
.venv/bin/python agonport/vdplet/qualification/build.py
```

The build regenerates deterministic tables and scene assets, compiles a host
oracle directly against the standalone production `Wolf3dRenderer`, executes
the exact module source through a mock ABI host, and compares all 76,800 frame
bytes plus 1,792 bytes of DDA column state. It then builds the actual Xtensa
package with the pinned VDPlet SDK and verifies admission, relocations,
undefined symbols, and source stack receipts. Ignored results are written to
`qualification/build/host-evidence.json`.

The same build also runs an 85-check exact-source failure matrix. It covers
malformed CONFIG records, unavailable or incompatible pixel services,
surface-format rejection, failures at each of the three acquisitions and
releases, pixel-publication failure, cleanup, invalid-reconfigure state
preservation, and FINI. `qualification/qualify_errors.py` is the separate
stopped real-Xtensa follow-on for missing and undersized runtime buffers; it
must use the same central Oryx lease procedure as the primary target runner.
The real runtime validates a RUN argument-buffer handle before dispatch, so
even entries which ignore arguments use an existing retained buffer in this
matrix; module error expectations are therefore not masked by parser-level
`VDPL_E_BUFFER` rejection.

The target runner is intentionally separate:

```bash
.venv/bin/python agonport/vdplet/qualification/qualify.py \
  --engine jit --firmware /absolute/esp32-firmware.bin \
  --backend /absolute/flexe-vdp.so
```

It uploads the real package and 90 KiB workspace, selects double-buffered mode
136, records the INFO17 minimum-free stack watermark before and after, times
the complete RENDER reply, proves
the frame is hidden before C3, compares all decoded pixels after C3, unloads,
rejects the stale handle, reloads, unloads again, and verifies the module slot
is empty. This headless emulator command may run only under the central Oryx
lease described in `agon-dev-env/cross-agent/vdplet-rollout/README.md`.

## Evidence boundary

Host parity and package admission are not emulator or hardware evidence. Oryx
proves the exercised uploaded-code/runtime path but not physical scanout,
physical frame time, production-game integration, or allocation under the full
game's retained asset load. Those remain explicit gates in the migration
study.

## Bounded target result

The authorized generation-3 Oryx run passed against the independent-pixels
candidate on 2026-10-30. The uploaded package produced all 76,800 expected
RGB222 pixels, remained hidden until C3, and completed CONFIG/RENDER plus
unload, stale-handle rejection, reload, and final empty-slot checks. The
complete requested RENDER reply measured 3,340,000 emulated VDP cycles and
0.013412 host seconds under the JIT backend. INFO17 reported 2,152 minimum-free
VDP-task stack bytes both before and after the exercised path; the module did
not lower the task's lifetime watermark.

The ignored target receipt is
`qualification/build/target-jit-evidence.json`, SHA-256
`eba7434b664e109d086775ee68f13953ab3825f7954305fe19096796fa64c7d4`.
This is emulator evidence only. Physical scanout, physical performance, and
production-game integration remain open gates.

The separately granted generation-14 error/recovery run also passed on the
same immutable module and runtime. It observed 11 expected module/runtime
errors spanning unconfigured and unsupported entries, malformed CONFIG, and
missing or undersized workspace/map/texture buffers. Successful renders after
the staged resource failures prove cleanup of the previously acquired leases;
an invalid reconfigure preserved the last complete mirror; the final visible
frame matched all 76,800 oracle pixels; normal unload left the slot empty; and
backend failure/unhandled/unregistered/unmapped counts were zero. The ignored
receipt is `qualification/build/target-errors-jit-evidence.json`, SHA-256
`497a6aa95cb37d5485a963dc0f356c362ac6fcf97ab868cec75632e7d9b67d22`.
The preserved first-attempt receipt documents runtime prevalidation of the RUN
argument-buffer handle; it is diagnostic evidence, not a module failure.

## Full-MOS review fixture

`review/` contains the dedicated human-review host and stopped Oryx profile
preparation tools. The host loads the exact qualified package and scene,
checks capability 17, requests CONFIG and RENDER, swaps the completed hidden
frame, waits for one key, unloads, clears its buffers and callback, restores a
single-buffered MOS mode, and re-enables the cursor. It draws no part of the
reviewed scene. See `review/REVIEW.md` for the centrally leased review
procedure and exact module-versus-host ownership boundary.

A no-GUI full-MOS rehearsal passed under central Oryx lease generation 6 on
2026-10-30. The captured live scene matched the preserved oracle's 320x240
RGB image byte for byte, all five requested replies succeeded, the injected
Enter traversed the real `mos_getkey` path, the success text and restored MOS
prompt appeared, and the frontend and backend exited without failures or
unhandled input. The rehearsal receipt is ignored at
`review/build/rehearsal/rehearsal.json`, SHA-256
`0faa05cf710a0efdca80a27ee17db3d49acce28864fbe6f62d31b54bfed44f60`.

This rehearsal proves the assembled host/module lifecycle in the pinned
emulator, not physical hardware. The Author subsequently completed the human
review on 2026-10-30: the expected module-only scene rendered correctly, one
key returned through the cleanup path, the MOS prompt was restored, and `dir`
succeeded. Screenshots preserve both observations. The emulator was then
closed and a fresh whole-host inspection was empty. This accepts the bounded
emulator presentation and keyboard lifecycle only; physical hardware,
full-game integration, commit, and publication remain separate gates.

## Optional direct-colour-row candidate

TODO 8a / G057-WLF-002 adds a separate ABI 1.6 candidate without changing the
accepted copied source, contract, package, or review path. Its frozen plan is
`../doc/wolf3d-vdplet-color-rows-plan.md`. `wolf3d_scene_rows.cpp` acquires the
same map and textures, borrows every independently mapped hidden SBGR2222 row,
caches only those scoped pointers and renderer scratch in caller workspace,
and routes the same DDA/background/sprite final stores through the contract's
masked native-byte operation. It calls neither `surface_info` nor
`pixels_write`, and clears every cached pointer before END.

The ordinary build command also runs this candidate's 1,044-check host suite.
It compares all 76,800 low-six-bit pixels and 1,792 geometry bytes to the same
standalone oracle while using noncontiguous row allocations. It verifies top
sync-bit and row-guard preservation, no writes after END, no retained pointer,
balanced transaction/buffer cleanup, ABI and callback refusal, staged ROW and
ordinary-lease failures, malformed row metadata, END failure, failed-
reconfigure state preservation, and FINI. The full-width rectangle has no
contract group-padding bytes; canaries immediately outside every returned
320-byte group prove that the consumer makes no outside store.

The target workspace minimum is 11,552 bytes, down 80,608 bytes from the
copied candidate's 92,160 bytes, and contains no full-colour dummy frame. The
host equivalent is 12,512 bytes because host pointers are 64-bit. The actual
Xtensa package is 8,296 bytes (344 bytes larger than copied), with 3,300
resident text bytes, 4,200 resident-data bytes, 10 admitted relative
relocations, no unresolved symbols, a largest source frame of 288 bytes, and a
largest module-owned source call-chain sum of 368 bytes. Its package SHA-256 is
`c32381bc659b6e1fcc479eef22168a77eea22da310202da794234f172ccab670`.
The complete ignored receipt is
`qualification/build/rows-host-evidence.json`.

No timing improvement is claimed. The later target comparison confirmed exact
output but measured the direct path as slower in this bounded scene; the target
and review results are recorded below. Physical hardware, full-game behavior,
and publication remain outside this proof.

## Direct-row target and review preparation

TODO 8b / G057-WLF-003 used the frozen plan in
`../doc/wolf3d-vdplet-color-rows-target-plan.md`. Its offline pin and syntax
preparation remains reproducible from the repository root with:

```bash
.venv/bin/python agonport/vdplet/qualification/prepare_rows_target.py
```

The ignored receipt is
`qualification/build/rows-target-readiness.json`. It pins the copied and direct
packages, oracle, rows-r1 firmware/ELF, stable x86 backend, target runner, and
new stopped-review source. The target runner refuses to overwrite an existing
evidence directory and requires explicit firmware, backend, engine, and output
arguments. It must not be invoked until the central Oryx lease procedure grants
the exact frozen cohort.

The later cohort runs JIT and interpreter in separate processes. Each engine
performs matched copied/direct correctness and lifecycle arms, then six
alternating timing rounds with five RENDER RUNs per arm. Only foreground
requested-RUN-to-reply duration and emulated VDP cycles are timed; upload,
load, CONFIG, DDA READ16, capture, C3, and teardown are excluded. This is not
isolated renderer time or a physical-speed claim.

The pinned copied/direct cohort subsequently passed exact pixels, DDA geometry,
hidden-before-C3 ordering, refusal/recovery, lifecycle, and resource/fault
checks in fresh JIT and interpreter processes. The direct arm reduced caller
workspace by 80,608 bytes (87.47%) but its modeled median RENDER transaction
cost was about 32.93% higher than the copied arm in this bounded scene. This is
an explicit memory-versus-time tradeoff, not a universal speed result.

`review-rows/` contains the separate review package/profile preparation. It
fails closed unless both engine receipts exist and pass, stages only into
`.emulator/vdplet-rows-review`, bundles both actual sources and package hashes,
and identifies the direct module as reviewed and the copied module as the
accepted control. Its no-GUI full-MOS rehearsal passed under generation 27.
The Author then accepted the visible direct-row scene and one-key cleanup under
generation 29; MOS returned and `dir` worked. A manual second `run` hit the
review guest's retained one-shot transaction-count assertion after another
valid UNLOAD, which is a fixture rerun limitation rather than a first-run or
renderer failure. Physical hardware, full-game integration, default selection,
commit, and publication remain separate gates.
