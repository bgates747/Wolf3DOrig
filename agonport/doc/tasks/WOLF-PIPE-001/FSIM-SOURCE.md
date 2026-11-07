# Fsim consultation — verified pipeline precedent

Source-only response received 2026-11-07; no compilation, tests or device contact.
Fsim checkout reference supplied by owner: `80590249f1ef0c8d03201f09d52d645840a19cc0`.
All paths below are relative to `/Agon/mystuff/agon-fsim`. Exact referenced file
bytes were independently read/rehashed, rather than assuming repository HEAD
alone establishes their contents.

## Working bespoke Agon pipeline

`agon/corsair-flight/src/main.cpp:service()` is repeatedly called from the
foreground loop. It services keyboard/controller input and elapsed-time physics.
`pose()` sends pose fields followed by a commit marker, without waiting for
render completion. Transmission is synchronous MOS output and can backpressure;
this is cooperative eZ80 scheduling, not another eZ80 thread or cost-free TX.

`utilities/corsair-backdrop-target/prepare_scanout.py` installs `f49::service()`
before `processor->processNext()` and intercepts pose commands with `f49::stage()`.
This hook is essential: UART receipt alone does not prove the parser can stage
new poses during rendering.

`utilities/corsair-backdrop-target/scanout.h` implements the actual ESP32 path:

1. `stage()` replaces pending pose fields by operation/object key. `readCommit()`
   snapshots the latest complete committed generation, including related camera
   and status state. The active render scene is not mutated by later receipt.
2. `startWorker()` creates a core-1 render worker and core-0 compositor. One
   immutable job renders at a time; finite slot/ready backpressure is explicit.
3. `service()` retires completed work, samples the latest commit and admits the
   next render BEFORE waking the higher-priority compositor. Intermediate
   unrendered pose generations coalesce; unchanged poses do not force new draws.
4. Two cropped colour/HUD output slots have explicit Free/Rendering/Ready/Copying
   ownership. `compose()` copies a finished output into the hidden VGA page and
   calls `canvas->waitCompletion(false)` before marking that output slot Free.
5. Only then does the compositor call `canvas->swapBuffers()`. Scanout uses the
   copied VGA page; the released intermediate is available to the render worker
   during the flip wait. A dedicated compositor semaphore avoids consuming the
   stock swap notification. Resource/mode/destructive changes drain ownership.

`docs/decisions/ADR-0009-composed-aircraft-presentation.md` records this accepted
architecture and its physical acceptance. The compositor presents completed
views in order with a bounded ready mailbox; it is not an unlimited queue or a
latest-ready-image-dropping policy. Wolf may need a different explicitly defined
completed-image policy; do not conflate newest input selection with frame dropping.

## Current VDPlet port does less

`utilities/pingo-vdplet-flight/client.py` substitutes an eZ80 `native_latest`
snapshot and runs both `service()` and `native_service()` each loop pass.
`backend.inc:native_service()` freezes `native_frame` through PREPARE, RENDER and
C3/ordered query phases, while newer local eZ80 snapshots can replace latest.
It admits the next snapshot after presentation. Thus input/physics can progress
during a remote reply wait, but VDP rendering and presentation are serialized.
Its finite inline RUN does not establish parser/worker concurrency; do not reuse
the historical private GP polling method as Wolf's public reply contract.

The direct-row port has no independent colour output. With one VGA page scanned
out and the other complete/pending flip, neither is free for the next unrelated
frame. Wolf needs supported image staging AND scheduling/ownership support to
overlap that next draw. Extra RAM alone or removing the eZ80 wait does not supply
those methods. Do not delete the double-buffer admission guard, keep borrowed
rows across finite calls, or install a bespoke worker inside arbitrary RUN.

Two cropped intermediate images plus two VGA pages suffice for Fsim's particular
copy-before-flip design. A third full framebuffer is not universally required.
Wolf's full-image cost and static-HUD/viewport alternatives require their own
memory, copy-bandwidth, resource and correctness analysis before selection.

## Time and rate semantics

Fsim's producer currently creates new simulation state at a FIXED 30 Hz:
`common/rc-flight/session.cpp:rc_advance()` accumulates elapsed clock credit and
advances one fixed physics step per four units. `main.cpp:service()` caps large
elapsed values and records dropped units. At its selected 60 Hz video mode the
MOS clock increments twice per refresh; this is not 120 independent update
instants per second. Do not copy those constants as a high-resolution Wolf clock.

The bespoke renderer has no 30 fps sleep, but cannot show more distinct simulated
poses than its producer supplies. Host preview caps and USERSPACE stress delays
are separate. Wolf's requirement remains fastest practical input service and
newest-state production, preserving gameplay time through an explicitly chosen
clock/step policy; Fsim's 30 Hz producer does not impose a new Wolf limit.
Optional even 30 Hz presentation must remain separate from input/physics service.

## Independent content verification

| File | SHA-256 |
| --- | --- |
| `utilities/corsair-backdrop-target/scanout.h` | `c97adb4a88091aee7396759a265ea209440be7178fbae1961f1037652722e44a` |
| `utilities/corsair-backdrop-target/prepare_scanout.py` | `c493746f37c7f042cc1e557570ff5a4bf45e7b8d4dc88d82ceee5667f150dda3` |
| `utilities/pingo-vdplet-flight/backend.inc` | `2bfb657b219f0ce258a3e0c4449bd39d1c141df411f0bddcc2cb2d14cec8aeb0` |
| `utilities/pingo-vdplet-flight/client.py` | `f70c3ac23dd2248d8a9bdd9f87d3f0f00499add251878c065840d04da6e6951c` |
| `common/rc-flight/session.cpp` | `df30c2d9d944d21eb5b1c5642527100a7d3ce10593207916cc10378b1fd211ca` |

These establish source identity, not Wolf compatibility or a new performance
measurement. Remaining pre-code questions belong to WOLF-PIPE-001-02/03; the
previous optimization goal stays paused and no resource lease is held.
