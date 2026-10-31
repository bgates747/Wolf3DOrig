# Wolf3D production VDPlet client fixture

This finite fixture is the first production-client integration gate for TODO
8d. It uses the accepted copied-pixel bounded renderer and exact scene, while
issuing discovery, INFO, chunked upload/consolidation, LOAD, CONFIG RUN, RENDER
RUN and acknowledged UNLOAD through the same `wolf3d_vdplet_client.inc` that
the game candidate assembles.

It is not the full game and does not select the VDPlet backend by default. The
scene remains visible until one key arrives; normal teardown then unloads the
owned handle, clears only client-owned ordinary buffers, removes the combined
MOS callback and restores the saved single-buffered mode. A timeout or
ownership ambiguity deliberately retains the callback and referenced storage
instead of claiming cleanup.

Build from the repository root after the durable bounded proof build:

```bash
.venv/bin/python agonport/vdplet/qualification/build.py
.venv/bin/python src/asm/wolf3d/scripts/build.py --backend standalone
.venv/bin/python src/asm/wolf3d_vdplet_client/scripts/build.py
.venv/bin/python src/asm/wolf3d_vdplet_client/scripts/test_client_contract.py -v
```

Ignored outputs land in `src/asm/wolf3d_vdplet_client/tgt/`. Target execution
requires a separately frozen readiness receipt and a fresh central Oryx grant.
No local or graphical emulator is implied by this build.

The host regressions pin the real assembled command templates and model the
conservative mailbox/ownership rules for absent and incompatible runtimes,
fresh handles, stale and malformed replies, runtime errors, timeout ambiguity,
Escape while RUN remains outstanding, INFO2-assisted UNLOAD resolution, and
clean callback/buffer disposal. They are proportional source/wire evidence,
not an eZ80 execution claim.

The first target attempt and its minimal ADL upper-byte correction are frozen
in `gen31-failure-amendment.md`. The failed raw evidence remains ignored under
`tgt/oryx-failure-gen31/`; it is intentionally not replaced by later builds.
The later finite-fixture return-path audit is frozen separately in
`readiness-addendum-r2.md`; it does not alter the generation-31 diagnosis.
Generation 33's exact-scene/failed-UNLOAD evidence and corrected teardown
analysis are frozen in `gen33-unload-amendment.md` and
`gen33-diagnosis-r2.md`.
The resulting final source/application pins are in
`readiness-addendum-r3.md`.
The adjacent error-return flag audit is recorded in
`readiness-addendum-r3-flag-audit.md`.
The reconciled final local pins and exact success tuple are frozen in
`readiness-addendum-r4.md`.

That exact r4 candidate subsequently passed its single granted headless Oryx
generation-35 run: oracle-identical scene, result/status/pending/callback/
handle/native/token/schema `0/0/0/0/0/0/7/1`, restored MOS prompt and zero
backend faults. The ignored raw evidence is preserved under
`tgt/oryx-pass-gen35/`; the maintained result and scope are recorded in
`agonport/doc/devlog_20261030.md` and `agonport/doc/wolf3d-vdplet-migration.md`.
This finite gate does not make the VDPlet backend a gameplay or release
default; that remains TODO 8e.

Golem accepted the automated gate. The same exact candidate subsequently
passed its readable Author review on 2026-10-31 under a finite self-service
Oryx lease: the oracle scene was accepted, Enter requested orderly unload, MOS
returned to a live prompt, `dir` worked, and the generated result matched the
expected hash exactly. The immutable pins, procedure and acceptance record are
in `human-review-readiness-r1.md`. The profile is not authorization for another
run; gameplay integration remains TODO 8e.
