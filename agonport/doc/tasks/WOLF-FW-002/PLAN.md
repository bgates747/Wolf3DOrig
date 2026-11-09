# WOLF-FW-002 — Migrate routine preparation to the pinned firmware

Smith directly authorizes completing the audit's migration work without
further input. Implement project-owned preparation, packaging and regression
corrections; keep the optimization goal paused and all existing resource,
hardware, deployment and human-start permissions. Commit this plan before code.

- [x] FW002-01 — Add one project-owned release verifier/selector using the
  audited exact release artifacts and latest owner-bound Olimex selector.
  Reject changed bytes, missing module/backend receipts and private firmware
  substitutions before creating a routine payload/profile.
- [x] FW002-02 — Produce a VDPlet-only routine deployment payload, including
  the exact application/module, assets, firmware identities and source receipts.
  Make the general deployment path verify that payload instead of copying an
  ambiguous target binary. No actual SD or external deployment selected.
- [x] FW002-03 — Prepare a new stopped Alexe profile using the release BIN/ELF
  and Eirene RC3 BIN/map; preserve old profiles/evidence. Accept explicit
  existing emulator executables, never rebuild/install the emulator here.
  No automatic launch or startup RUN.
- [x] FW002-04 — Correct the finite copied-client fixture's current shared
  include, scratch/storage bounds, profile macro and exact producer bindings.
  Keep old accepted artifacts/results separately preserved.
- [x] FW002-05 — Make routine build/staging defaults explicit; prevent old
  Fab, bespoke and retired private-firmware launch paths from silently violating
  the new pin. Inherent exceptions must carry a readable reason and retain
  existing execution permissions. Do not mutate frozen historical cohorts.
- [x] FW002-06 — Qualify file/preparation rejection controls and real assembly
  through the normal serial Pi compiler FIFO. Check module bytes/storage,
  payload completeness, tampering/mismatch refusal, no-RUN profile preparation
  and disabled-profiling invariance as relevant. Preserve failures and correct
  only their concrete causes. No hardware or emulator run selected here.
- [x] FW002-07 — Publish actual results, residual runtime-only boundaries and
  concrete next-use commands. Commit/push logical groups and notify current
  component coordinators of material compatibility/preparation changes.

## Compiler tranche

One finite serial Pi build reservation after the source is reviewable. Expected
under ten minutes, absolute 900 seconds; each child at most 180 seconds;
80°C maximum CPU temperature, missing sensor stop, 512 MiB available-RAM floor.
Assert actual ownership before children, join owned groups and release normally,
notifying the actual next owner. Assembly of the real clients and ordinary
focused Python/file checks only; no emulator, stress run or device process.

The existing verified module packages may be reused without changing renderer
algorithms, compiler flags, providers, SDK or firmware defaults. The maintained
production module remains distinct from the explicitly selected fastest timing
module. New routine packages/profiles use separate output directories and never
overwrite a frozen kit or historical accepted payload.

Completion evidence: [RESULT.md](RESULT.md) and [EVIDENCE.json](EVIDENCE.json).
