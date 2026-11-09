# Pinned-firmware audit complete

> Historical b004-release result. The same tag was replaced by async-r1; see
> [the current amendment result](../WOLF-FW-002/AMENDMENT-01-RESULT.md). Original evidence below is preserved.

Contract `52a1d8f` was committed and pushed before this audit. No compiler,
emulator, device, deployment or queue operation was performed. WOLF-GOAL-001
remains paused. The findings below describe source/static compatibility and
preparation gaps; none is a new runtime pass on the selected firmware pair.

The VDPlet modules are compatible with the release's declared ABI/capability
and static resource requirements. The main migration work is in old preparation
tools. The bespoke Wolf renderer inherently needs different firmware; the
historical private timing VDP is **not** inherently necessary for the current
VDPlet profiler. No blanket firmware exception is justified for that profiler.

## Verified release identities

| Component | Exact selected identity | Verification |
| --- | --- | --- |
| VDPlet | v0.1.2-alpha; source `b6c7c58331bf4cbbd54dbc4a1301c124e5963622` | All 9 SHA256SUMS entries and 10 GitHub asset digests/sizes match |
| VDP firmware | `vdp-vdplet-0.1.2-alpha.bin`, 1100304B, `b004570b607b45bbd6e87a3c704b65b23d3221981db3aac6cf2578aa22d766e3` | Release asset, not rebuilt |
| Debug ELF/map | Decompressed release `.elf.gz`/`.map.gz` | Exact uncompressed sizes/hashes match release manifest |
| VDP source | Published 46-file source freeze | Each file read from the release commit and independently hashed; 16 exported headers plus build configuration also match released provenance |
| Eirene | 3.1.0_uart0_rc_3, source `97311c437093e416342a6c836cf9914f2ced027d` | ZIP digest/sidecar and all 360 internal checksums match |
| Eirene MOS | ZIP member `mos-rc3.bin`, 100879B, `d7a51147f3381cd68d56f3fbe4605434a897dfae1b049269afeba09ec2b7eb50` | Exact member independently hashed, matching Smith's instruction |
| Olimex EMOS selector | 131072B `a25f1612f4aaa542c5488cf3266d968ad3d1d61e9df3b5ce2c680650f5d7a2ca`; source `2c79c6006d6bcb0c2b3f9d8d6aae3ef4b36c730a` | Read maintained selector; no physical read or installation claim |
| EMOS map selector | `11a296f09e1d2b7125e1a40ce0aea62042f299e93ea85afc6a6459a351866d20` | Reconcile this current retained map in new kits; historical `55b830…` map is not substituted solely because the ROM hash agrees |

Machine-readable proof: [RELEASE-VERIFICATION.json](RELEASE-VERIFICATION.json).
Downloaded binaries/metadata/source remain under ignored `build/releases/` and
`build/vdplet-source/`; firmware binaries are not added to Git.
[verify_releases.py](verify_releases.py) repeats file/hash/source verification
without executing release code. The GitHub connector could read Eirene but
returned 404 for VDPlet; authenticated `gh` retrieved the release and its binary
assets. No fallback to a branch build or private firmware was used.

## Source and interface findings

The release enables lean PCM configuration with legacy base capabilities 15,
pixels 16 and colour rows 256, yielding runtime mask **287**. Its ABI1.6 prefix
retains buffer services, copied pixels and scoped hidden native colour rows.
Wolf's direct modules request **257** (buffers + rows); the copied proof requests
17, and its rows proof 273. All are subsets. No current Wolf module needs the
disabled PCM sink, async worker, counted return or overlap witness.

The released loader admits ABI1.0–1.6, image131072B, data16384B, stack2048B and
text98304B for text96. All **19 distinct retained module images** pass the
audit's static header/ELF/section/import/relocation-kind/resource screen. Full
digests, sizes, resource declarations and every retained path are in
[INVENTORY.json](INVENTORY.json). The screen is not the native allocator/loader
and does not execute relocations, test actual heap fit or prove whole-task stack
headroom. Old measured resource margins do not transfer to this new firmware.

The source-verified colour-row contract retains independently obtained row
pointers, x-bias, XOR2, colour3F/preserveC0, lease lifetime and BEGIN/ROW/END.
The optimized modules' byte-store/mask/lease assumptions remain applicable.
Services may still refuse incompatible modes/layouts; use the normal 320×240
double-buffered mode136 and preserve runtime refusal/cleanup semantics.

Release identity INFO0 remains0100; D8 protocol1 LOAD/RUN/UNLOAD/INFO and READ16
remain supported. INFO17 remains the executing task's stack watermark. WPN1
logging/resetRUN100 is implemented inside `8d3d…` itself, not a private VDP ABI.
It uses buffers and ordinary READ16. The release's UART repair changes the
receiver implementation, not these wire meanings; this audit does not claim it
has cured Wolf's historical Alexe stall.

The exact Eirene ZIP source retains Wolf's used public MOS slots: load01,
sysvars08, file0A/0B/1A/1B, setkbvector1D, kbmap1E, clear/waitVDPflags40/41.
Time offset00 and screen-mode offset27 remain. Its parser accepts a ten-byte
KEY body and passes the payload in DE to the installed callback; Wolf saves DE
and sets IX before reading VDPL. Thus the direct client's callback composition
has no identified source mismatch. Ordinary RST10/RST18 remain synchronous.
Wolf does not call removed RC2 trial42/43 or assume RFC25's A return is status.

Olimex's selected integrated EMOS remains the a25f ROM used in the latest Wolf
physical evidence, with maintained map/provenance to rebind. Its specific
P3DR/VDPL callback constraints and route0 are owner contracts, not properties
inferred from Eirene's generic parser. Any new admission still reconciles the
actual selector and observed state with the owner.

## Candidate-family dispositions

This inventory covers all maintained assembly entrypoints (27), emulator
regression runners (25), production/bounded modules and retained optimization
arms, including paused candidates. Frozen archives and earlier failures are
historical evidence, not newly current candidates or dispatch authority.

| Candidate family / entry point | Compatibility with defaults | Preparation / qualification disposition |
| --- | --- | --- |
| Normal full game, `src/asm/wolf3d`, `--backend vdplet-direct` | Source-compatible D8/ABI1.6/row/MOS use | Prepare exact matched package and current release pair; no new runtime qualification claimed |
| Maintained production module `266f809f…`, 18636B | Static screen passes; buffers/rows257 | Not replaced by optimized code; production source/adoption remains distinct |
| Fastest completed combined021 `8d3d19bb…`, 22572B | Static screen passes; same synchronous API | Retained selected experimental reference, not silent production promotion |
| Other PERF001/004–007/009/013–019/023 module arms | Static screen passes for every distinct retained image | Preserve original controls/results and real per-arm size/limit binding; no need for old private VDP merely to execute a B module |
| Copied/row bounded module proofs `57b635fc…`/`c32381bc…` | Static screen passes; copied pixels/row capabilities supplied | Old staging tools pin b42a/8d98 private images; repin profile and current pair before a new run |
| Old finite `wolf3d_vdplet_client` source fixture | Module/protocol concept compatible | Current builder copies newer client include without its new profile macro/linked package-storage definitions; source composition requires correction before rebuild. Historical accepted binary stays historical; no new assembly attempted |
| Ordinary `--profile`, direct backend | Same public game/MOS API; optional timer remains separately admitted | Timer inactivity/vector/restore, disk/cue and overload paths need retained checks under the selected pair; profiler does not change game scheduling |
| `--profile --profile-native` with exact8d3d module | Source-compatible WPN1/READ16, no inherent firmware exception | Replace old7593 firmware binding and old ELF/map/profile metadata in a new kit; do not reuse retired101/105 |
| PERF011/012 and later visible rotation B fixtures; static timer controls | Same B protocol and public mode/present/fence services | All old kits retired. Static caption remains; visible fixtures stay uncapped, human-start restrictions persist where applicable |
| Default `standalone` game, `wolf3d_hello`, bespoke A performance controls | **Incompatible with ordinary release**: private BUFFERED_WOLF3D4A and W3DV/W3DR protocol | Inherent bespoke comparison exception only for its stated selected purpose; not a routine fallback. Do not run tracked default binary on release firmware |
| Host/compiler/decoder/oracle regressions | No target firmware execution | No firmware exception required for host-only checks; modeled services/arithmetic do not prove new target behavior |
| Remaining normal eZ80 logic, gameplay, shell, audio, save/config, demo and lifecycle fixtures | Public-MOS/VDU portions have no identified pin-specific mismatch; some fixtures use bespoke integration | All 27 entrypoints/25 runners are listed individually. Existing runners select old `mos_console8.bin` and often bespoke Fab `.so`; inspect each listed path and replace its preparation or justify the actual integration exception. Not blanket runtime-qualified |
| Fab source-model A/B visual adapters | **Not execution of the release BIN** | Inherent host-model visual exception if specifically selected; A requires bespoke source, B bridge is consumer model. Cannot qualify release UART repair or Xtensa timing |
| Old Alexe full-game/profile/performance profiles | Applications/modules as above; profiles are stale | `.runtime.sha256`, firmware BIN/ELF and MOS BIN/map all need a new matching release profile. Alexe executable naming does not select firmware |
| Current generic deployment bundle / SD staging | Assets are reusable, application selection is ambiguous | `deploy.toml` and generic SD tool copy `tgt/wolf3d.bin` without selecting backend or including `wolf3d.vdpl`; must prepare explicit VDPlet payload before routine deployment. No SD writes occurred |
| PERF008 libgcc arm | Still unqualified/incompatible package composition | Previously rejected allocated44B.eh_frame is still outside release loader's sections; no emitted candidate to migrate, no guard/strip exception |
| WOLF-PIPE-001 newest-pose worker design | Draft, not an executable candidate | Optional async worker is **off** in the pinned release. Cannot presume ABI1.7 worker availability from published SDK source; missing design support stays explicit, paused goal not resumed |

The inventory screen found modules of ABI1.3 or1.6, all at most24620B packaged,
15724B resident text and13348B resident data (see exact individual values in the
JSON; no resource sums are treated as measurements). All use supported static image
sections and relative relocation kinds. Module execution and actual task/heap
fit on each target remain untested in this audit.

## Required exceptions and gaps

1. **Bespoke compatibility comparison:** justify exact alternate A firmware,
   private4A/notification services and the comparison purpose in its scheduling
   request. Bind restoration to the scheduler's current standard. A's private
   timer recorder can be part of this same explicitly selected exception.
2. **Fab userspace visual model:** name the source adapter/version, why it
   cannot execute ESP32 release firmware and the visual-only scope. This does
   not authorize substituting the model for Alexe/Olimex/Console8 release runs.
3. **Historical exact-version diagnosis:** preserving an old failure is not a
   new test. A specifically selected reproduction would need its exact-version
   purpose, explicit alternate tuple and current-standard cleanup in the request.
4. **No B timing exception:** do not keep7593 merely because old host code
   asserts its hash. B's timing is module-owned. Migrate that host binding instead.
5. **Preparation gap:** legacy profiles, callback/observer private-map literals,
   transitive reset/bootstrap files and fixed restore extents need current
   explicit pins before declaring a new kit READY. Binary-equal a25f does not
   justify ignoring the owner's current map/provenance. No old lease is revived.
6. **Standard reuse/handback:** old controllers unconditionally install7593 and
   restore incoming85f9. That sequence is obsolete for routine work. Reuse
   verified standard firmware, skip unchanged backup/reflash, and restore any
   authorized nonstandard write to current standards. The new standard's
   application length1100304 differs from old full touched span1105920; actual
   write/tail/cleanup extent must be owner-bound, never assumed from BIN size.

No exception, deployment, new package build or test is selected by this audit.
Future selected migration can reuse the 19 screened images while preparing
fresh current pairs and finite qualification. Existing workload/resource and
human-start permissions remain. SD stays mounted; old evidence is unchanged.

## Published evidence and remaining limits

- [Inventory and exact module/source identities](INVENTORY.json), generated by
  [inventory.py](inventory.py); source HEAD is the frozen audit contract.
- [Verified release artifacts/source and maintained EMOS selector](RELEASE-VERIFICATION.json).
- [Source/interface evidence](SOURCE-EVIDENCE.json) pins the files used for the
  conclusions above. Release source is read at its exact published commit.
- [Current project operating pins](../../../../FIRMWARE.md), with persistent
  reference in the root AGENTS.md.

Prior actual95 performance, actual105 profiling and all partial/interrupted
cohorts retain their original platform limits. This audit neither retests the
RX fix nor relabels those results as release0.1.2 measurements. No Console8
runtime case is claimed. The audit is complete; candidate migration and first
release-pair execution are explicit future work rather than missing checksum
or compatibility analysis.
