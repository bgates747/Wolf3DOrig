# Wolf conservative post-span domain advice

The proposed checked layout/source predicate is supported consumer logic for
an independent equal-output optimization. The exact7593 runtime preserves
borrowed row mappings through Wolf's ordinary asset callbacks. Two qualifications
matter: a valid native screen may span multiple pools and fail this deliberately
strict predicate; and address checks alone do not make a generic row table,
grouping metadata or source immutable. Retain the scalar path when those
conditions are unproved. No firmware workaround, new API or performance claim
follows from this source assessment.

Reply to `2026-11-07_09-00-55_wolf3dorig_wolf020-67c15b2-post-domain-source-question`,
frozen Wolf67c15b2. [Exact source/BIN/ELF pins](WOLF-POST020-SOURCE-PINS-2026-11-07.json).
This reads the proposed contract and existing control implementation, not a
completed candidate. No build/test/census/target/reviewer was started.

## P20-001 — Exact runtime/provider lifetime

1. color_frame BEGIN pauses Canvas, drains pending primitives, re-resolves the
   current hidden surface, validates actual rows and captures the surface until
   END. It does not allocate/copy a private contiguous framebuffer. Canvas's
   suspension waits for an active primitive executor and prevents ordinary
   background primitive processing; its initial drain completes pending swaps/
   row permutations before the mappings are captured.
2. The native module queries each of240 actual rows, stores those addresses in
   its separately leased workspace and calls render_world_direct before END.
   It clears saved rows and ends the frame even on rendering errors, retaining
   first-error precedence. Addresses expire at END/current RUN cleanup, not at
   an ordinary texture lease release. Never retain them through presentation,
   another RUN or a mode change.
3. acquire_asset/release_asset call only buffer_acquire(READ)/buffer_release.
   The runtime checks/retains BufferStream owners in four ordinary lease slots;
   these calls do not close the frame, resume Canvas, process UART/mode changes
   or swap pages. The frame lease does not consume one of those four slots.
   Other native drawing/line/pixel-copy submissions refuse BUSY while it is
   open. Thus these exact ordinary callbacks preserve row mapping and texture
   lifetime during the texture's read lease under the existing ownership rules.
4. This is not a promise about an arbitrary host AssetProvider that writes rows,
   metadata or texture memory in callbacks, or another actor violating the
   exclusive finite-frame contract. A read lease supplies lifetime and checked
   supported-buffer ownership; the numerical predicate supplies no synchronization.

## P20-002 — Address and source admission

1. For the rows branch, require all240 actual nonnull row bases to equal checked
   base+320*y, x_bias0, pixel_xor<=3 and the admitted320x240 writable extent.
   Because320 is a multiple4, x XOR0..3 permutes0..319 within each row. Distinct
   rows plus this permutation give distinct destination bytes. Check overflow
   before base+76800 and before source+4096. A half-open source/destination
   disjointness test can then conservatively exclude all sampled-source overlap.
   The separate linear branch requires its existing valid76800B backing object;
   its scalar and fill_span paths ignore row XOR/masks.
2. Use uintptr_t checked arithmetic for the numeric predicate on this target;
   do not subtract unrelated pointers or infer C++ array provenance from adjacent
   integer addresses. Continue using each actual returned row pointer for stores.
   Do not flatten rows into row0+320*y, even after the numeric equality check.
   That predicate is not a new public stride guarantee.
3. Concrete applicability limit: exact VGABaseController::allocateViewPort can
   allocate several pools and assigns row pointers pool by pool; scrolling can
   also permute mappings before the frame. The public ABI explicitly allows
   separate pools. All240-rows-contiguous is sufficient but not guaranteed on
   native7593, even with row_bytes320. A failed predicate means unchanged scalar
   fallback, not unsupported firmware or a newly justified relaxed predicate.
   Static identical-column opportunity is separate from actual layout admission.
4. Keep the acquired source alive and unchanged for the whole group. Check its
   actual pointer/length only after the original acquire/null/4096B-size checks.
   Full4096B disjointness from the complete target is conservative and valid;
   unproved/overlapping source must use original scalar sampling/order.
5. Additional generic frontier: row-pointer storage, heights/tiles/U, resolved
   door/texture metadata and masks used during the group must stay stable and
   must not be overwritten by destination writes. Distinct framebuffer pixels
   and texture disjointness alone do not prove that. Native7593 has separate
   VGA allocations, module state and leased workspace; the ordinary callbacks
   above do not mutate them. For generic alias fixtures, retain the stable-
   metadata caller contract or establish the necessary nonalias domain/fallback;
   do not claim the numeric row predicate alone covers arbitrary self-modifying
   row tables/workspace. Do not use a forged provenance flag to assume this.

## P20-003 — Preserve the scalar observation and failure boundaries

1. Group only adjacent logical columns with identical FULL positive height,
   resolved texture ID and valid U in0..63. Preserve original clipped extent,
   fraction/step, source-row clamp, per-ray metadata and width1 behavior. Write
   texel&63 through existing fill_span, retaining byte access/masks/PSRAM flags.
   Overlapping preserve/colour masks do not prevent one equivalent write to
   each distinct pixel; they still prevent unrelated covered-fill assumptions.
2. Stay inside the same texture lease/group. Keep ascending ID acquisition and
   the exact acquire count/stats, refusal/null/short/release-error precedence,
   partial framebuffer effects and release timing. Do not skip an acquisition
   because all its columns clip away: the original needed-ID pass can still
   acquire/release it. Do not move a later potentially failing callback ahead
   of stores or combine groups across a release boundary.
3. Layout/source refusal of the optional fast path should be a side-effect-free
   fallback, not a new renderer error or an early texture read. Keep the original
   validation order and avoid probing an absent row table on the linear branch.
   Group detection needs no new callback/lease; it must not mutate heights or
   choose original height-copy geometry. Texture/painter/HUD/sprite order remains.
4. This is PORT003 work reduction within already-supported byte semantics,
   conditional on those source facts. It is not a substitute for blocked original
   x86/VGA/fractional-height behavior or authority to alter it. The selected
   scalar oracle, actual generated code/stack and later physical evidence remain
   consumer-owned; no new machine work or per-test owner approval is added here.

Primary reading: pinned runtime/frame helper/controller/provider/painter above;
[C++17 pointer arithmetic](https://timsong-cpp.github.io/cppwp/n4659/expr.add)
and [pointer/integer conversions](https://timsong-cpp.github.io/cppwp/n4659/expr.reinterpret.cast).
The standard's conversion mapping is implementation-defined; checked integer
address tests here are specific to the supported target, not universal object
lifetime or allocation-provenance proofs. Public ABI reference sections
Borrowed colour drawing rows and Buffer views retain the normative lifetime.
