# Current-release Wolf preparation

These commands prepare local files. They do not grant or perform an emulator
run, SD deployment or hardware operation. Use the normal compiler FIFO for
assembly/checks, and the existing target checkout and scope for later execution.
The paused optimization goal stays paused.

## Firmware cache

The amended `0.1.2-alpha-async-r1` audited cache is the default. The tag was
replaced in place: old b004 images/profiles are superseded and retained only
as historical evidence. New preparation selects dc43ecb8 and rejects old
checksums/build-receipt pins. Ordinary firmware async support is enabled; Wolf
remains synchronous in these preparations.

On another checkout, fetch exact
release assets into a **fresh** cache directory, then verify them:

```bash
.venv/bin/python tools/wolf_prepare.py --cache /absolute/new/cache fetch-releases
.venv/bin/python tools/wolf_prepare.py --cache /absolute/new/cache verify-release
```

The command uses authenticated `gh`, verifies the pinned SHA256SUMS and every
listed VDP asset, and extracts the exact Eirene ZIP members in memory for
preparation. It neither rebuilds firmware nor installs tools. Missing/changed
bytes refuse preparation. `--cache` is a global option, before the subcommand.

## Normal game and complete payload

Under the normal compiler checkout:

```bash
.venv/bin/python src/asm/wolf3d/scripts/build.py
```

The default is now `vdplet-direct`, explicitly using the retained maintained
production module `7490d81c`, now containing the completed combined021 renderer
without its diagnostic timing wrapper. Build/qualify the module first with
`.venv/bin/python agonport/vdplet/production/build.py` under the compiler lease. The application and receipt are isolated under
`src/asm/wolf3d/tgt/pinned/`. Each application owns its matching module copy, so
building a profiling variant cannot overwrite the normal application's module.
The ordinary standalone source remains a separately buildable historical
compatibility control; it is not the routine deployment path.

Prepare the complete game payload (all ten levels, shell/help/end/HUD/audio,
application, matching module and receipts) into a fresh output:

```bash
.venv/bin/python tools/wolf_prepare.py package \
  --receipt src/asm/wolf3d/tgt/pinned/wolf3d-vdplet-direct.json
.venv/bin/python tools/wolf_prepare.py verify-payload
```

Default output is `tgt/wolf3d-production-optimized-async-r1`. Existing directories are refused rather
than replaced. For a new preparation use `--output /absolute/new/payload`.
`deploy.py plan/deploy` verifies the standard payload before entering the shared
deployment engine. Its declared bundle now includes the module and manifest;
the SD-specific tool uses the same verified payload and compares readback after
sync. Actual deployment and any autoexec selection retain their existing
permissions. The card is left mounted.

An explicitly selected optimized native-profiling review build remains possible:

```bash
.venv/bin/python src/asm/wolf3d/scripts/build.py --profile --profile-native \
  --module agonport/doc/tasks/WOLF-PERF-021/results/build01/candidate/module/wolf_perf.vdpl
.venv/bin/python tools/wolf_prepare.py package \
  --receipt src/asm/wolf3d/tgt/pinned/wolf3d-vdplet-direct-pn.json \
  --output tgt/wolf3d-optimized-profile-async-r1
```

That uses the qualified `8d3d` module. Its own WPN1 recording and ordinary READ16
work with the selected release contract; no private `7593` VDP is selected.
Normal game's existing simulation/render scheduling is unchanged. This command
does not create a new uncapped performance fixture or a runtime pass.

## Stopped Alexe profile

Provide the exact existing frontend/backend binaries for the intended machine;
preparation records their SHA256. Their qualification is not inferred from
firmware verification. No new emulator compilation/installation is attempted.

```bash
.venv/bin/python tools/wolf_prepare.py profile \
  --payload tgt/wolf3d-production-optimized-async-r1 --output /absolute/new/profile \
  --frontend /absolute/existing/flexe-agon-emulator \
  --backend /absolute/existing/flexe-vdp.so
```

The profile includes release VDP BIN/ELF and RC3 MOS BIN/map. Its autoexec only
sets the keyboard, selects the directory and **loads** the entry; there is no
RUN. Its launcher checks the runtime manifest and refuses firmware/MOS/VDP/SD
argument overrides. Preparation does not launch that executable. Existing
human-start constraints remain. Old accepted/failed profiles are untouched.

## Corrected finite copied-client fixture

Under the compiler checkout:

```bash
.venv/bin/python src/asm/wolf3d_vdplet_client/scripts/build.py
.venv/bin/python src/asm/wolf3d_vdplet_client/scripts/test_client_contract.py -v
```

Fresh outputs live in that fixture's `tgt/pinned/`. Shared profiling macros are
disabled and the image owns linked scratch storage covering the largest uploaded
file, module and 4096 B zero-buffer page; the builder checks the real listing and
binary storage extent. Original accepted fixture binaries remain separate.

```bash
.venv/bin/python tools/wolf_prepare.py fixture --output tgt/wolf-finite-client-async-r1
.venv/bin/python tools/wolf_prepare.py profile \
  --payload tgt/wolf-finite-client-async-r1 --output /absolute/new/client-profile \
  --frontend /absolute/existing/flexe-agon-emulator \
  --backend /absolute/existing/flexe-vdp.so
```

The finite fixture waits for a key after showing its scene. It is not the full
game or a gameplay performance test. Preparation does not start it.

## Olimex and historical methods

```bash
.venv/bin/python tools/wolf_prepare.py olimex-binding
```

This reads the scheduler's current selection, records its hash and reports
that no installed state or grant has been checked. It does not reserve, install,
reset or touch a device. The scheduler supplies actual current-state admission,
standard reuse and current-standard cleanup for a later selected job; the old
7593/incoming85f9 controllers are retired and are not relaunched by this tool.

The 32 maintained legacy Fab/stage/rehearsal entrypoints now refuse default use.
A specifically authorized source-model or version-compatibility exception can
be invoked with `--firmware-exception "specific purpose"`, with the same reason
and exact identities in its existing scheduling request. This flag supplies
neither workload approval nor a resource checkout. `--help` explains the
exception path without entering the old program. Frozen task archives remain
unchanged; do not treat them as new routine launchers.
