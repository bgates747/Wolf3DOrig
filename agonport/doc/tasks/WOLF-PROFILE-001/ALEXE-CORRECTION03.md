# Full-game package storage correction

Before code: actual corrected guest9777 spans040000–0893BF. Its package MOS
LOAD writes22572 bytes at060000–06582B, which contains executable shell,
intermission and audio code. This is a confirmed linked-image collision;
356 causality remains unproved. Fab source rendering bypassed this native
package path and did not qualify it. Reduced benchmark clients were smaller.

Use the existing MOS LOAD, upload and VDPL LOAD interfaces unchanged. Replace
only the fixed CPU staging address with a forward label for owned writable
storage appended to the maintained application, conditional on VDPlet backend,
the larger of the selected package length and4096 bytes. The existing zero-
upload helper reuses a full4096-byte scratch page after LOAD. Preserve strict nonzero/<128KiB package
validation, buffer IDs, ordering, renderer, profiling and default selectors.
This is supported ordinary eZ80 storage; no firmware/service/API change or
workaround. The standalone backend emits no staging storage.

The durable builder must verify actual listing labels, exact reserved extent,
zero initial bytes, emitted MOS LOAD address/length and upload/address operands,
and full image end below0A0000 (leaving existing stack/scratch region alone).
Reject old060000 artifacts and forged address operands. Reserve max(package size,4096)
rather than a128KiB maximum. Refuse builds too large for the existing
application memory bound instead of silently overlapping another region.

Finite normal Pi FIFO: build standalone off/on, VDPlet off/on/native and a
separate hardware-guest03; verify disabled standalone baseline identity,
unchanged native module, real producer fields, INFO17 and allocator-free
storage bounds. Run existing six ownership/result checks plus decoder checks
and focused staging negative controls. Preserve old guests, logs and kits.
Join all owned children/release with immediate next notification.

Then ONE separate Oryx Alexe03 profile via normal fresh FIFO/assert/idle.
Same pinned runtime/firmware/module/assets/250-frame game/300s bound/guards,
normal owned Quit/teardown/retrieve/hash/release as ALEXE-PLAN. Only the client
storage correction differs from02. No physical access, automatic replay,
emulator repair, renderer optimization or paused-goal resumption selected.
