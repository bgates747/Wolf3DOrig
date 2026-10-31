# Wolf3D renderer VDPlet migration

## Decision

**Conditional go.** The Wolf3D renderer can plausibly move from a dedicated
Wolf3D firmware image into a loadable VDPlet without adding a Wolf-specific
service to the shared runtime. The promoted VDPlet ABI 1.3 buffer and generic
pixel services provide the necessary ownership, input, output, and completion
boundaries.

The migration is not yet proven shippable. The current renderer keeps far more
than the VDPlet static-memory allowance, the new full-frame software path has
not been timed on physical hardware, and the generic pixel path still needs
physical mode-8/double-buffer qualification. Those are bounded engineering and
qualification tasks rather than architectural blockers.

This document is the completed feasibility study and the implementation map
for TODO 8. It does not authorize implementation. Work stops at the review
gate at the end of this document.

## Study baseline and evidence labels

The study was completed on 2026-10-30 against these local baselines:

| Component | Baseline | Role |
| --- | --- | --- |
| Wolf3DOrig | `feature/standardized-deployment` at `7e899cf` | eZ80 application, assets, build, tests |
| agon-vdp-wolf3d | `wolf3d/vdp-extension` at `1dc462e` | accepted standalone renderer oracle |
| agon-vdplet | `codex/initial-runtime` at `2541f10a1f8b06688bcecbc6d22eeae607da2b63` | shared runtime, SDK, ABI 1.3 |
| golem | current local checkout | proven eZ80 VDPL mailbox/token idioms and historical qualification evidence |

Statements below use these meanings:

- **Demonstrated** means it follows directly from current source, build
  artifacts, or recorded tests.
- **Derived** means it is an arithmetic bound calculated from demonstrated
  layouts or contracts.
- **Proposed** means it is the recommended later design and still needs an
  implementation receipt or measurement.
- **Unmeasured** means no physical-hardware result is currently claimed.

## Objective and scope

The objective is to preserve the accepted Wolf3DOrig game, renderer output,
assets, maps, 30 Hz fixed simulation, asynchronous frame ownership, and clean
MOS exit while replacing its mandatory Wolf-only firmware with an
independently built `wolf3d.vdpl` module. The eZ80 application will upload,
load, invoke, and unload that module through a reusable VDPlet-enabled
firmware.

This is not a conversion of the renderer to the Golem language. The renderer
is already hand-written C++ and should remain a freestanding, single-
translation-unit C/C++ VDPlet. Golem is useful here for its client examples
and qualification history.

The result will require a **VDPlet-capable shared firmware**, so it will not run
on a truly stock VDP. It will no longer require a complete firmware build
containing Wolf3D-specific code.

## Existing systems

### Standalone Wolf renderer

The current extension is approximately 1,551 lines across its control, world,
renderer, HUD, and fizzle headers. It uses custom buffered subcommand `0x4A`
and maintains one `Wolf3dControl` for each control-buffer ID. Its protocol has
commands for level initialization, player pose, doors, actors, statics,
rendering, view weapon, fizzle, HUD fields, and notifications. Render
completion is returned as a `W3DR` packet carrying event, token, and sequence.

The accepted standalone firmware artifact is 1,089,680 bytes. Symbol evidence
from that artifact attributes 2,335 bytes to the main subcommand dispatcher
and 6,833 bytes to `render_frame`, with additional inline helpers elsewhere.
This strongly suggests that executable text can fit the VDPlet 64 KiB limit,
but only a real VDPlet link receipt can prove it.

### eZ80 application

`wolf3d_render_async.inc` already supplies the most important concurrency
property: only one render/fizzle producer is in flight. It validates token and
sequence, records the request purpose, allows the eZ80 simulation and input
loop to continue, swaps with VDU command C3 only after successful completion,
and drains the outstanding operation during global exit.

That structure maps closely to asynchronous VDPlet RUN requests. The VDPlet
native function itself executes synchronously in the VDP command task, while
the eZ80 continues independently and receives the requested runtime reply only
after the native function returns.

### Shared VDPlet runtime

The current full VDPlet firmware artifact is 1,104,304 bytes, 14,624 bytes
larger than the standalone Wolf image. Firmware size is not the migration's
primary benefit; the benefit is that one reusable runtime can admit Wolf3D and
other modules without rebuilding or reflashing application-specific firmware.

The relevant promoted ABI 1.3 contract is:

- one active trusted native module slot;
- Xtensa classic ESP32 GCC 8.4 windowed ABI;
- one C/C++ translation unit, with no heap, exceptions, RTTI, constructors,
  thread-local storage, or imported C++ runtime;
- maximum package size 128 KiB;
- maximum executable `.text` 65,536 bytes;
- maximum combined `.rodata + .data + .bss + .data.rel.ro` 16,384 bytes;
- declared module stack at most 2,048 bytes within the VDP command task's 4 KiB
  stack;
- contiguous application buffer access with at most four simultaneous leases;
- argument buffers of at most 32 bytes, protected from module writes;
- optional pinned `libm`/`libgcc`, whose code and stack still count against the
  limits; and
- module pointer and lease validity ending at each RUN return.

The required capabilities are buffer access (`1`) and generic pixel output
(`16`), or requirement mask `17`, with ABI minor 3. Discovery tests that mask
as a subset of the runtime's advertised capabilities rather than requiring an
exact mask match. A lean runtime profile may omit pixels and is therefore not
sufficient for Wolf3D.

## Portability analysis

### Renderer logic that can be retained

The following algorithms are firmware-independent and can be adapted with
little conceptual change:

- fixed-point DDA and projection;
- compact world records and their update semantics;
- wall texture selection and sampling;
- sprite projection, depth ordering, transparency, and wall occlusion;
- HUD arithmetic and layout; and
- the fizzle LFSR and pixel order.

### Firmware-private dependencies that must be removed

| Current dependency | Why it cannot be imported | VDPlet replacement |
| --- | --- | --- |
| global `buffers` map and `getBitmap` | private firmware objects | ABI buffer leases by explicit buffer ID |
| `Canvas`, `drawBitmap`, and rectangle fills | private renderer API | software composition into RGB222 workspace |
| `BufferStream` and `Bitmap` | heap/runtime-owning classes | fixed-width records and leased byte spans |
| `waitPlotCompletion` | private graphics synchronization | synchronous `pixels_write`, then VDPL reply |
| `_VGAController`, scanlines, `createRawPixel` | controller internals | ABI 1.3 generic pixel service |
| `switchBuffer`, `canvasW`, `canvasH` | firmware globals | eZ80-owned C3 swap and explicit dimensions |
| `VDUStreamProcessor` parser/event pumping | firmware event loop | finite native calls and application state machine |
| `send_packet` | private serial return path | runtime-owned VDPL DONE/ERROR reply |
| `std::map` of control objects | multiple firmware control streams | one module instance and one compact state block |

No private Canvas or VGA pointer should cross into the module, and no new
Wolf-specific runtime service is necessary for the first prototype.

## Proposed ownership and lifecycle

| Owner | Persistent responsibilities |
| --- | --- |
| eZ80 application | simulation, input, authoritative game state, dirty-record batching, asset loading, module upload/load/unload, RUN tokens and timeouts, buffer swap, error presentation, MOS restoration |
| shared VDPlet runtime | package validation, active-slot lifecycle, buffer leases, generic pixel copy, reply framing, handle and capability enforcement |
| Wolf VDPlet | compact render mirror, update validation/application, DDA and sprite rendering, HUD composition, fizzle state, one-frame RGB222 production |
| application-owned VDP buffers | module package staging, arguments, update batch, tilemap/assets, frame workspace, render scratch |

The lifecycle should be:

1. The application discovers the VDPL runtime and checks ABI minor 3 plus
   capability subset 17.
2. It uploads `wolf3d.vdpl` into a contiguous staging buffer and requests
   LOAD, saving the fresh handle from the reply.
3. It allocates and initializes application-owned argument, update, tilemap,
   asset, and workspace buffers.
4. A CONFIG call copies and releases its argument-buffer lease before it
   acquires workspace, map, or texture leases, then validates buffer IDs,
   sizes, dimensions, schema, and module build identity. LOAD INIT itself
   receives no arguments.
5. Each accepted frame uploads one compact dirty-update batch and issues one
   requested APPLY_AND_RENDER RUN.
6. The module validates the complete batch before mutating its state, applies
   it atomically, renders into the workspace, calls `pixels_write`, and
   returns.
7. The runtime emits DONE. Only then does the application swap the hidden
   drawing surface into view. Withholding the swap preserves the currently
   displayed frame after ERROR, but neither runtime nor module provides general
   rollback for already changed hidden pixels or module state.
8. Escape during RUN latches shutdown but retains the callback until DONE or
   ERROR is drained. The application unloads only its own live handle, clears
   its module buffers, restores the user's original single-buffered video
   mode, and returns to MOS.

If the one module slot is already occupied, Wolf3D must report a clear busy
error and exit; it must not unload an unknown owner's module. A stale handle
must be treated as a fatal application/session error. A native module hang is
not recoverable inside the VDP command task, which is the same failure class as
a hang in the current custom renderer handler.

## Drawing architecture

ABI 1.3 `pixels_write` accepts one-byte RGB222 (`00BBGGRR`) or indexed source
pixels, uses physical coordinates, validates all rows and bounds, drains the
Canvas once, and synchronously copies to the current drawing surface. In mode
136 (double-buffered mode 8), that surface is the hidden buffer. The module
must confirm the 320x240 direct-RGB222 double-buffered surface using
`surface_info`. The service neither swaps nor waits for vblank and retains no
pointer after return.

The proposed renderer therefore composes the complete 320x240 physical frame
in an application-owned RGB222 workspace and performs one `pixels_write` per
successful frame. This preserves the application's ownership of C3 swaps and
makes the requested VDPL DONE reply an unambiguous completion fence. Mixing
queued VDU bitmap draws after `pixels_write` would weaken that fence and is not
recommended.

The existing layout is retained:

- 320x200 game area;
- default 256x160 3D viewport at `(32,20)`, retaining viewport-scaling hooks;
- HUD at `y=200..239`; and
- RGB222 software fills for the ceiling, floor, borders, and bevels.

Existing wall and sprite assets are fixed 64x64 RGBA2222 buffers. The two high
bits are alpha; sprite pixels whose high bits are zero are skipped, while an
opaque pixel's low six bits are copied as RGB222. Existing consolidated stock
asset buffers survive module unload and can be leased by ID. HUD images can be
software-composited from the same buffers using a small generated metadata
table.

## Resource feasibility

### Static module memory

The VDPlet limit is 16,384 bytes for all read-only and writable static data
combined. A host layout probe of the existing code produced:

| Item | Existing size/evidence |
| --- | ---: |
| `Wolf3dWorldState` | 7,984 bytes |
| existing renderer object (host proxy) | 41,192 bytes |
| sine table, 3,600 x `int32_t` | 14,400 bytes |
| cosine table, 3,600 x `int32_t` | 14,400 bytes |
| pixel-angle table, 320 x `int32_t` | 1,280 bytes |
| wall height table, 320 x `int32_t` | 1,280 bytes |
| wall tile/U/side arrays | 960 bytes |
| visible sprites, 550 x 16 bytes | 8,800 bytes |

The existing object is therefore an immediate **no-fit** and cannot simply be
relinked as a VDPlet.

The proposed fit is nevertheless credible:

- keep only a compact, explicitly aligned render-world mirror in module BSS,
  targeting approximately 5–8 KiB;
- replace full sine and cosine arrays with one exact quarter-wave sine table
  of 901 `int32_t` values (3,604 bytes), deriving quadrants and cosine phase;
- generate or upload viewport projection data into the application workspace;
- move column metadata, sprite lists, framebuffer, and all other large scratch
  arrays into application-owned VDP buffers; and
- remove the per-control `std::map`, heap objects, and duplicate render scratch
  from persistent state.

This is a design estimate, not a pass. The linked ELF/JSON receipt must prove
that combined static data remains below 16 KiB.

### Workspace and leases

| Workspace region | Proposed upper estimate |
| --- | ---: |
| 320x240 RGB222 frame | 76,800 bytes |
| per-column wall metadata | about 2,240 bytes |
| 550 visible-sprite records | about 8,800 bytes |
| projection/configuration data | about 512–1,280 bytes |
| header/alignment margin | about 1 KiB |
| **Total** | **about 89–90 KiB** |

Stock buffers and service offsets use 32-bit sizes, so a 76,800-byte frame is
not constrained by a 16-bit length. The frame workspace consumes one lease,
the tilemap a second, and one texture at a time a third, leaving the fourth
lease free after the argument lease has been copied and released. Large wire
uploads remain u16 chunks followed by consolidation; peak setup memory must
allow both temporary blocks and the consolidated destination. Projection data
should be copied into the workspace during CONFIG rather than held under
another lease during rendering.

Future VDPlet-owned buffer IDs must be centralized in one eZ80 include and
allocated from an audited unused range. Current significant ranges include
control/tilemap IDs 1 and 2, walls at `0x1000+`, sprites at `0x2000+`, HUD and
shell assets near `0x4000`, samples at `0x5000`, and audio command buffers at
`0x6000`. This study intentionally does not invent final IDs.

### Code and stack

The standalone symbols make a sub-64-KiB text image plausible. C++ must be
built freestanding with exceptions and RTTI disabled and no static
constructors. Header-only `min`, `max`, and sort operations may compile without
runtime imports, but sprite sorting must be inspected and replaced with a
small local implementation if it introduces forbidden relocations or excessive
stack.

The module build must emit and inspect its JSON admission record, ELF section
sizes, relocations, and GCC `.su` stack-usage files. `.su` covers source frames
only and is not a whole-call-stack proof. Every reachable call path, including
runtime service frames and any linked integer helpers, must fit the declared
2 KiB module stack and leave a safe margin in the 4 KiB host task; target INFO17
high-water evidence must cover the complete exercised workload. Optional
`libm` is not part of the initial plan; fixed/generated tables avoid its
uncertain text and stack cost.

## Update and wire protocol

Mapping every old Wolf subcommand to a direct RUN would add a 17-byte VDPL
envelope to every individual change. Instead, the eZ80 should retain its
dirty-only policy and write one compact, application-owned update buffer per
frame.

The proposed buffer has a magic, schema version, generation, byte count, and
bounded length-delimited records for reset, player pose, doors, actor
set/remove, statics, HUD, and view weapon. A fixed argument buffer no larger
than 32 bytes supplies buffer IDs and configuration, not the update data
itself. APPLY_AND_RENDER must first validate the entire header and every record
boundary without changing state, then apply the batch atomically.

A level reset is only a few KiB and fits the same mechanism. Per-frame upload
can clear and rewrite a small contiguous buffer; there is no need to transmit
a full world snapshot each simulation tick.

An otherwise unchanged render becomes a 17-byte requested RUN rather than the
current 7-byte render command, an additional 10 bytes or roughly 300 bytes per
second at 30 Hz. Batching should reduce overhead whenever several state records
change. These are wire-size calculations, not measured frame timings.

The application should use a monotonically changing runtime token for each
request and match the standard `VDPL` reply mailbox. The assembly mailbox and
token validation in Golem's GOLEM-041/042 qualification guests are suitable
source patterns. A resident six-byte RUN can be considered later, but the
direct requested form gives clearer initial ownership and token behavior.

## Fizzle transition

The current firmware fizzle handler performs 60 swaps, pumps input inside the
VDP, and sends one final `W3DR` completion. VDPlets deliberately have no
swap/vblank/input-pump service and must return in finite time.

The recommended migration is application-paced fizzle:

1. FIZZLE_BEGIN initializes the exact existing LFSR order and cumulative red
   state.
2. Each FIZZLE_STEP advances a bounded share of pixels, writes the resulting
   frame, and returns DONE.
3. The eZ80 swaps, remains globally responsive to Escape, and submits the next
   step while the death simulation is frozen.

This changes lifecycle ownership but can retain the accepted visual order and
duration. It does not justify a new presentation service in the shared runtime.

## Compatibility and failure behavior

- A non-VDPlet or insufficient runtime must fail discovery/capability checking
  with a readable message before assets or gameplay begin.
- Package admission verifies ABI, capabilities, code/data/stack declarations,
  and package integrity. The application additionally verifies its own update
  schema and module build identity.
- All buffer IDs, sizes, viewport bounds, texture availability, update lengths,
  and record values must be checked before use.
- Missing or invalid buffers return `VDPL_E_BUFFER`; the application must not
  swap a failed frame.
- The module stores copied state only. No leased pointer survives RUN return.
- The module sends no raw serial packets. Runtime DONE/ERROR is the only native
  completion path.
- App-owned asset buffers may outlive module unload, but module staging,
  workspace, argument, and update buffers are cleared during orderly exit.
- The accepted standalone renderer and current client protocol remain
  buildable behind an explicit legacy option until visual, timing, and hardware
  acceptance is complete. They are the rollback path and comparison oracle.

## Feasibility gates

The recommendation becomes an unconditional go only after all four gates pass:

1. **Module admission gate.** A real module link proves text at or below 64
   KiB, combined read-only/writable static data at or below 16 KiB, package at
   or below 128 KiB, no forbidden relocations/imports, and worst reachable
   stack at or below the declared 2 KiB with safe runtime headroom.
2. **Generic-pixel hardware gate.** ABI 1.3 RGB222 output is qualified on
   physical hardware in mode 8 double buffering, with correct hidden-buffer
   selection, exact colors, completion ordering, and no tearing.
3. **Performance gate.** Physical measurements show acceptable submit-to-DONE
   latency and input responsiveness in representative dense scenes. The full-
   frame software-composition path is currently unmeasured; its median and
   high-percentile cost must be compared to the standalone renderer. A target
   of no more than 10% regression is proposed unless the Author accepts another
   budget.
4. **Lifecycle gate.** Discovery, busy slot, LOAD, CONFIG, RUN, ERROR, stale
   handle, Escape while RUN is outstanding, orderly UNLOAD, repeated launch,
   fizzle, and MOS restoration all pass emulator and hardware tests.

Existing runtime tests include uploaded execution across representative pixel
formats and double-buffer behavior in the VDPlet development environment.
This study does **not** promote that evidence to a physical-hardware claim.

### Bounded proof disposition — 2026-10-30

The separately released GOLEM-057 tranche now supplies concrete evidence for
the smallest representative path:

- a real capability-17/ABI-1.3 package is 7,952 bytes, with 3,024 bytes of
  resident text, 4,144 bytes of combined resident data, nine admitted
  symbol-zero relative relocations, no undefined symbols, and a largest
  source `.su` frame of 256 bytes;
- the exact module source matches the standalone renderer oracle for all
  76,800 frame bytes and 1,792 DDA geometry bytes;
- an uploaded Xtensa package on the pinned independent-pixels Oryx runtime
  preserved the visible frame before C3 and matched every decoded pixel after
  C3;
- CONFIG/RENDER, normal unload, stale-handle rejection, reload/unload, and an
  empty final slot all passed without backend failures or unmapped/unhandled
  accesses;
- the complete requested RENDER reply measured 3,340,000 emulated VDP cycles
  and 0.013412 host seconds under the JIT backend; and
- INFO17 reported 2,152 minimum-free VDP-task stack bytes before and after the
  complete exercised path, so the module did not lower the existing lifetime
  watermark.
- a separately granted real-Xtensa error/recovery matrix observed all 11 named
  unconfigured, unsupported, malformed-config, missing-resource, and
  short-resource errors; recovered to exact 76,800-pixel output after staged
  acquisition failures; preserved the previous mirror after invalid
  reconfigure; and unloaded to an empty slot without backend errors.

This closes the bounded module-admission, exact fixed-scene, generic-pixel
ordering, and orderly-teardown questions in the emulator. It does not close
the physical generic-pixel/performance gates, full-game retained-allocation
and lifecycle gates, fizzle, eZ80 integration, or cutover approval.

### Optional direct colour-row preparation — 2026-10-30

The generic runtime's separately qualified ABI 1.6 hidden-colour-row service
made it possible to prepare an additive direct-store version of the same
representative scene. This candidate does not supersede the accepted copied
path. It retains the same oracle and math, caches 240 independently mapped row
pointers in caller workspace only for the active transaction, protects native
sync bits, and contains no 76,800-byte software colour frame.

Host qualification matches all 76,800 oracle pixels and 1,792 geometry bytes
and covers row noncontiguity, guards, pointer lifetime, service and ordinary-
lease failures, and cleanup. The real package is admitted at 8,296 bytes,
3,300 resident text bytes, 4,200 resident-data bytes, and a 368-byte largest
module-owned source call-chain sum. Target workspace falls from 92,160 to
11,552 bytes. These are size and correctness results, not a speed prediction.
The source/host/package tranche is complete and stopped; target execution and
timing require a later explicit release.

The separately frozen target plan is
`wolf3d-vdplet-color-rows-target-plan.md`. Its prepared runner keeps copied and
direct packages in one matched two-engine cohort, performs exact pixel/DDA and
finite lifecycle/error checks before timing, and alternates bounded batches
while timing only foreground requested RUN-to-reply intervals. A distinct
review package/profile preparation is gated on passing JIT and interpreter
receipts and cannot replace the accepted copied review. No backend execution,
profile staging, or lease request occurred during preparation.

## Implementation map

The Author released production integration work on 2026-10-30 after accepting
the copied-pixel and direct-row bounded reviews. TODO 8d and 8e are the single
actionable tracker; the stages below remain the durable architecture and
evidence sequence rather than a second checklist. The completed seam audit was
moved from TODO 8c into this document and the dated development log.

### Production seam audit — 2026-10-30

The accepted game already has the correct high-level concurrency boundary.
`w3d_async_owner` permits one render or fizzle producer, simulation continues
at fixed 30 Hz while rendering is busy, and foreground code alone presents C3
after a validated completion. VDPlet RUN can therefore replace the current
`W3DR` producer without changing simulation cadence or presentation ownership.

The replacement is not merely a different render command. The current dirty
bridge emits one private `0x4A` command per changed door, actor, static, HUD
field, weapon and player pose, clears each dirty flag after its synchronous VDU
write, then sends `render_frame`. Production VDPlet mode instead needs one
bounded application-owned update buffer with a versioned header, generation
and length-delimited records, followed by one requested APPLY_AND_RENDER RUN.
The module must validate the entire batch before mutating its compact mirror.
The client must not present an ERROR frame; the first implementation may treat
a RUN error as terminal while retaining the eZ80's authoritative state.

The current `W3DR` callback and ten-byte mailbox are structurally reusable but
not wire-compatible. A VDPlet build must recognize runtime `VDPL` replies,
validate reply version/kind/token/value or fresh handle, and turn the record
into a null key-up before MOS resumes. Escape remains a foreground shutdown
latch. If a RUN is in flight, exit waits for its finite DONE/ERROR reply before
unloading the application's own live handle; a malformed reply or timeout is a
fatal session error and must never unload an unknown handle.

Existing asset ownership is suitable. The eZ80 continues to load the tilemap,
wall textures at `0x1000+`, sprites at `0x2000+`, HUD/shell buffers around
`0x4000`, samples at `0x5000+`, and audio procedures at `0x6000+`. The VDPlet
reconstructs checked offsets and acquires/releases only the map, current asset,
update/config and workspace resources needed by one finite RUN. The first
production client owns module staging `0xEA77`, workspace `0x7100`, update
`0x7101`, config `0x7102`, and argument `0x7103`; resident game and audio asset
buffers remain under their existing loaders.

The bounded modules are exact architecture proofs, not drop-in game renderers:
they contain one static scene, one wall texture and one sprite. Production work
must add the real compact world mirror, per-asset lookup, HUD and weapon paths,
dirty schema and fizzle lifecycle before the VDPlet backend can render gameplay.
The standalone backend therefore remains the default and oracle throughout
TODO 8d and 8e.

Build selection will be durable and reproducible rather than a hand-edited
source constant. A project-local build driver will assemble the unchanged
standalone default or a named VDPlet candidate into distinct outputs, bundle
only the corresponding module for that candidate, and record the selected
backend. The first client foundation may compile without being selected at
runtime; no default, deployment or firmware requirement changes until its
separate gates pass.

### Frozen production client contract and first gate

Golem revision 2 is the current loader/lifecycle authority:
`/Agon/mystuff/golem/docs/tasks/GOLEM-057/wolf-production-client-contract-v1-r02.md`,
SHA-256 `efeb2e352156e8bf67b17120b0dc976ca4659a3e897dae7a161e24d471e6a65b`.
It selects copied pixels first (ABI 1.3, capability subset `0x0011`) and keeps
direct rows as a later selectable variant. Discovery is the operand-free
`23,0,0xD9` probe. INFO0 is identity `0x0100`, INFO1 is a capability subset
check, and INFO2 must show an empty slot before LOAD. LOAD/RUN/UNLOAD retain
their existing 19/17/13-byte full wire forms. Consolidate-14 has no reply;
LOAD or RUN is the authoritative contiguous-buffer check.

The client now enforces one requested transaction and one nonwrapping token at
a time, accepts only the expected kind and token, publishes only a fresh
nonzero LOADED handle, and never converts timeout into cancellation authority.
Escape stops new work and drains a matching RUN before requested UNLOAD.
UNLOAD ERROR preserves the native value and uses INFO2 to distinguish release,
the same live handle, and foreign ownership ambiguity. Callback and referenced
storage remain alive after any unresolved timeout or ownership result.

The default standalone backend still assembles to 106,434 bytes with SHA-256
`2dee8b17ac83b8e7a43d7e1dcbd6962b1d24274ca489c145ef44a5fd1c0ea258`,
byte-identical to the accepted pre-switch build. The named copied candidate is
separate and bundles the accepted 7,952-byte module
`57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be`.
The final finite production-client fixture is 2,295 bytes, SHA-256
`1096669ce659a744b4cb95ac53dc3c9881fd6578d646645c9eb0a541f149f230`.

Twenty-one proportional host tests pin the assembled packets and model unavailable
and incompatible runtimes, LOAD rejection/fresh ownership, ordinary keys and
stale tokens, malformed replies, native errors, timeout ownership, Escape
draining, all INFO2-assisted UNLOAD outcomes, and clean MOS return. The ADL
audit reports no definite width hazards or unresolved items; all four detected
wide memory accesses are annotated 24-bit storage. A source-visible canonical
Oryx profile is staged and stopped at `.emulator/vdplet-client`.

The first target client (`9657fdb2...`) cleanly but incorrectly rejected a
valid INFO0 identity during generation 31. Its u16 reply path loaded L and H
without clearing HLU, then performed an ADL-mode 24-bit identity comparison.
The exact result/wire evidence proves that IDENT and INFO0 succeeded, no INFO1
was sent, no handle was acquired, owned buffers and MOS mode were restored, and
the backend fault counters stayed zero. The one-line `ld hl,0` correction and
new structural regression are frozen in
`src/asm/wolf3d_vdplet_client/gen31-failure-amendment.md`. Generation 31 was
released before diagnosis. A subsequent wider audit found and preemptively
fixed the same upper-byte class in the finite fixture's 24-bit MOS return
status; that second correction does not change production client code and is
frozen in `readiness-addendum-r2.md`. No corrected target execution is yet
claimed.

Generation 33 then passed the exact scene and key path but exposed two teardown
defects. The client stored the handle high byte after an `or b` zero test,
sending `0x0101` instead of owned handle `0x0001`; after the correct HANDLE 8
and INFO2 value 1 replies, close performed another `or b` and returned with
carry accidentally clear. The verifier rejected result zero paired with status
3 and retained handle 1. The exact wire evidence and corrected outcome are
frozen in `gen33-unload-amendment.md` and `gen33-diagnosis-r2.md`.

The correction stores the original high byte before OR and explicitly
reasserts carry whenever a live handle makes cleanup unsafe. It does not relax
pending/ownership protections. The neighboring `cp ...; ret nz` path was also
audited: its only reachable non-runtime inputs are timeout 1 and protocol 2,
so its carry return remains correct and unchanged. The reconciled full pins
and focused regressions are in `readiness-addendum-r4.md`; no r4 target
execution is yet claimed.

The separately granted final r4 target execution then passed once as Oryx
generation 35. The displayed 76,800-pixel scene matched the frozen oracle at
SHA-256 `42e227e80bba3cd7d65dc1bc1bee0b87e5d233e1cd8d3a1dd4f26805499bb4a2`.
After the real key event, the client reported exactly result 0, status 0,
pending 0, callback error 0, handle 0, native error 0, token 7 and schema 1.
It returned to the MOS prompt, exited normally and recorded zero backend
failure/unhandled/unregistered/unmapped counts. The passing receipt is
`974a205396efab72fd7797a9724b672b0a64f9330e49a5005a94a2f459be247b`;
the raw result is `de684fe97a8737e448113faf2b5efbac7c45a93195471ecc6882087f60822ddb`.
Raw evidence was preserved before a fresh empty-host inspection and explicit
generation-35 release. This closes the finite client lifecycle gate only;
stage 8e still owns the real world mirror, update protocol and gameplay
renderer.

Golem accepted this as closure of the finite automated production-client gate.
TODO 8d is complete and has been moved to the dated development log. The exact
same candidate then passed its readable Author review on 2026-10-31 under a
finite self-service Oryx lease: the oracle scene was accepted, Enter requested
orderly unload, MOS returned to a live prompt, `dir` worked, and the generated
result matched the expected SHA-256 exactly. The actual normalized
`flexe-agon-emulator` launcher, accepted pins, procedure and acceptance record
are frozen in
`src/asm/wolf3d_vdplet_client/human-review-readiness-r1.md`. Oryx was empty
after normal close and the lease was released with no queued successor. The
gameplay renderer remains TODO 8e.

### Stage 0 — freeze the oracle and measurements

Preserve the standalone Wolf build, renderer/client protocol, relevant firmware
hashes, deterministic fixtures, representative scene captures, and existing
eZ80/VDP frame timings. Define the build switch that keeps this oracle
available throughout migration.

### Stage 1 — freeze the module contract

Specify CONFIG, APPLY_AND_RENDER, FIZZLE_BEGIN, FIZZLE_STEP, RESET, and optional
SELFTEST entry IDs; the argument layout; update record schema; workspace
layout; buffer-ID allocation; module build identity; capability requirements;
and exact error semantics. Keep the argument block at or below 32 bytes and
version wire schema independently from module release version.

Schema 1 was frozen on 2026-10-31 in
`agonport/doc/wolf3d-vdplet-production-contract.md`. A single generator owns
both the C++ and eZ80 constants. The 24-byte descriptor, 16-byte batch header,
eight record types, 6,912-byte/617-record bounds, full-snapshot coverage,
generation discipline, publication-failure replay, 5,500-byte mirror ceiling,
copied workspace layout, entry state machine, asset formulas, and error mapping
are now explicit. The pure two-pass parser validates every batch before
mutation and passes maximal/invalid/retry host regression. Stage 2 owns the
renderer which consumes this mirror; none of this changes the default backend.

### Stage 2 — extract a pure software renderer

Create a single freestanding Wolf VDPlet translation unit and durable generated
tables. Replace all firmware-private objects with fixed-width state, leased
byte spans, and an RGB222 framebuffer. Implement the compact world mirror,
quarter-wave trigonometry, local sprite ordering if needed, software HUD, and
strictly bounded parsing without changing accepted render math.

The playfield portion was extracted on 2026-10-31. It uses the frozen compact
mirror and caller-owned map/workspace plus finite asset leases; implements the
accepted wall, moving-door/jamb, actor, static, rotation, alpha, depth and
occlusion paths; composes the unoccluded first-person weapon and original HUD;
and matches the standalone oracle for 230,400 frame bytes and 5,376 DDA bytes
across three scenes. The single freestanding entry translation unit and real
service wiring remain before Stage 2 can close. The standalone backend remains
unchanged and selected by default.

### Stage 3 — prove module admission before integration

Build with the VDPlet SDK using capability mask 17, ABI minor 3, 65,536-byte
text, 16,384-byte static data, 2,048-byte stack, and 131,072-byte package
limits. Inspect JSON, ELF, map, relocation, and `.su` receipts. Stop and revise
the design rather than weakening runtime limits if any receipt fails.

### Stage 4 — add deterministic host regression

Exercise pure DDA, wall columns, sprite ordering/occlusion/transparency, HUD,
fizzle order, malformed batches, boundary values, missing assets, lease errors,
and exact RGB222 captures. Compare known scenes to the preserved standalone
oracle wherever the two implementations can share inputs.

### Stage 5 — qualify the real package in the runtime emulator

Load the produced Xtensa package into the owned VDPlet emulator profile and
test discovery, capabilities, LOAD/RUN/UNLOAD, slot busy, stale handle,
double-buffer generic pixels, errors, repeated sessions, and runtime stack/heap
information. Do not add a Wolf-specific runtime API to make this pass.

### Stage 6 — integrate the eZ80 loader and mailbox

Adapt the proven Golem VDPL assembly pattern for discovery, file upload,
contiguous staging, LOAD reply, fresh handle, direct requested RUN tokens,
timeouts, DONE/ERROR parsing, orderly UNLOAD, and clear user-facing failure.
Retain the legacy renderer path behind the build switch.

### Stage 7 — integrate dirty batching and rendering

Generate one validated dirty-update batch after the previous render completes
and issue one APPLY_AND_RENDER per accepted frame. Preserve fixed 30 Hz
simulation, one in-flight producer, callback-purpose ownership, and C3 swap
only after DONE. Do not swap or discard authoritative state on ERROR.

### Stage 8 — migrate the fizzle lifecycle

Implement the app-paced begin/step protocol while retaining the exact LFSR
sequence, accepted duration, frozen death-state behavior, and global Escape
semantics. Add deterministic and integration regression for aborts at every
step boundary.

### Stage 9 — integrate packaging and deployment

Teach durable build and deployment tools to place `wolf3d.vdpl` beside the
game, upload it at startup, and record module/runtime hashes. A VDPlet-mode
release no longer bundles mandatory `vdpwolf.bin`; documentation names the
minimum compatible shared runtime. A generic runtime image may be offered
separately, but it is not branded as Wolf-only firmware.

### Stage 10 — run complete emulator qualification

Run automated suites, deterministic navigation and combat paths, level and
death transitions, actors, doors, pickups, HUD, audio coexistence, Escape from
every loading/render state, failure injection, repeated launch/unload, and
legacy-versus-module frame captures. Obtain Author visual acceptance.

### Stage 11 — measure performance

Instrument eZ80 PRT submit-to-DONE time and runtime/module stack and heap
telemetry. Compare identical dense scenes, updates, viewport sizes, and fizzle
workloads between standalone and VDPlet paths. Record median and tail latency,
wire bytes, missed render opportunities, simulation cadence, and input
responsiveness.

### Stage 12 — qualify physical hardware

First qualify the shared runtime's generic pixel service independently on the
target Agon hardware. Then test Wolf3D long play, dense actors/statics, doors,
HUD, audio, death/fizzle, level transitions, Escape during in-flight work,
unload/relaunch, and MOS restoration. Repeat performance measurements on
hardware rather than extrapolating from the emulator.

### Stage 13 — cut over with rollback

After all gates and Author acceptance, make VDPlet loading the default, update
release/version/deployment documentation, and retain the tagged standalone
firmware/client path for at least the first VDPlet release as an explicit
rollback and diagnostic oracle.

## Review-gate disposition

The feasibility stop was observed. On 2026-10-30 the Author explicitly
released only the bounded GOLEM-057 prototype tranche described in TODO 8.
That tranche may prove compact static-state admission, exact fixed-scene
parity, a caller-owned approximately-90-KiB workspace, full-frame generic pixel
copy, requested completion, and teardown in the serialized headless Oryx
environment.

The bounded host and Oryx proof passed under the released tranche. Coupled
changes remain uncommitted pending Author review. A dedicated full-MOS review
host and stopped Oryx profile were subsequently prepared. Its no-GUI rehearsal
matched the oracle frame byte for byte and exercised capability discovery,
load/config/render/unload replies, one-key dismissal, cleanup, video/cursor
restoration, and return to the MOS prompt without backend errors. This is
rehearsal evidence, not human acceptance; the central coordinator still owns
the Author review slot. The Author deferred that review and requested continued
headless work. The resulting bounded error/recovery matrix passed against the
unchanged module and runtime; the candidate and review profile are now stopped
as directed. The Author subsequently completed the stopped review: the
module-only scene, one-key dismissal, MOS restoration, and `dir` all passed.
This closes the bounded emulator human-review gate, not any physical or
full-game gate. The release does **not**
authorize full production-game integration, fizzle
migration, default cutover, physical flashing, or removal of the accepted
standalone path. Those later stages and their hardware gates remain pending.

The optional ABI 1.6 direct-colour-row candidate completed its bounded gate.
Its copied/direct target cohort passed under both fresh JIT and interpreter
processes in generation 26. Exact pixels, DDA geometry, hidden-before-C3
ordering, refusal/recovery behavior, lifecycle, and backend fault gates passed;
evidence SHA-256 values are `5f1e00ff...` for JIT and `554cfe74...` for
interpreter. The direct candidate reduces caller workspace from 92,160 to
11,552 bytes, but its 4.40-million-cycle median RENDER transaction is about
32.93% above the copied candidate's 3.31 million in this bounded scene. This is
emulator transaction evidence, not physical or full-game throughput.

The separate direct-row full-MOS profile is pinned and stopped at
`.emulator/vdplet-rows-review`. Its guest identifies the actual direct C
renderer and the measured memory/speed tradeoff, draws no scene pixels, and
uses one key to enter the normal unload and MOS restoration path. Central
request `761a33fa1480` supplied one finite headless scene/keyboard/cleanup
rehearsal. It passed under generation 27: the scene matched the oracle byte for
byte, the real key wait and normal unload/restoration path completed, the MOS
prompt returned, the frontend exited normally, and all backend fault counters
remained zero. Raw evidence was preserved, the Oryx profile was reset and
reverified stopped, and the lease was released before audit.

The Author then completed the bounded direct-row visual/keyboard review under
generation 29. The scene was accepted visually; one key completed UNLOAD and
cleanup; MOS returned; and `dir` worked. A subsequent manual second `run` hit a
known review-only diagnostic because the one-shot guest retains the first
run's five-transaction count and therefore observes ten rather than five. The
second invocation still produced valid replies through UNLOAD, so this does
not invalidate the accepted first run. Generation 29 was released after raw
evidence retrieval, profile reset, and an empty-host check. This closes the
optional bounded direct-row gate while leaving production game integration,
physical qualification, and default selection open under TODO 8.
