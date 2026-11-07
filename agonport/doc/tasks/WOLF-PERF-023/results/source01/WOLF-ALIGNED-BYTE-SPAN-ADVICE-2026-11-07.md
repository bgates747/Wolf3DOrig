# Wolf aligned constant-byte span: pre-code source advice

The proposed within-span address permutation is compatible with the current
scoped-row ABI and its exclusive hidden-page drawing contract. No logical-X
store-order requirement was found for this private constant-colour helper.
The stated complete-quad predicate gives identical distinct destination bytes;
retaining span/row/painter order avoids the earlier cross-row reorder problem.
This is source compatibility, not a candidate audit, measured improvement or
new concurrency permission.

Reply to2026-11-07_11-42-18_wolf3dorig_wolf023-aligned-byte-span-precode-advice;
frozen Wolfab94798. [Exact control/runtime/proposal pins](WOLF-ALIGNED-BYTE-SPAN-PINS-2026-11-07.json).
No implementation, test/census, build, reviewer, target operation or change to
current022 was performed.

## BSP-001 — ABI and concurrency boundary

1. The API lends bytes of an admitted hidden drawing rectangle for a finite
   synchronous RUN. It specifies address mapping, protected masks, bounds and
   expiry, not a per-pixel logical-X visitation order. fill_span is consumer-
   private, not a public service whose callback observes every store.
2. Retained BEGIN pauses/drains/re-resolves mappings; frame END/current RUN
   cleanup expires pointers and resumes Canvas. The ordinary graphics/line/
   copied-pixel submission guards refuse while a frame is live. No page/mode/
   sprite/context mutation is allowed during the lease. The selected controller
   separates hidden drawing and visible DMA mappings. No supported concurrent
   reader of a partially completed hidden fill or concurrent writer is being
   added here. Arbitrary observers violating that ownership cannot be assumed
   equivalent; future threading needs its own explicit contract.
3. Keep the existing safe compiler policy and actual byte operations/barriers.
   A masked load/store is not an atomic read-modify-write; MEMW orders memory,
   not exclusive ownership. Do not use this proof to remove PSRAM workarounds,
   weaken synchronization or claim concurrent XOR updates are safe. No extra
   API, lock or barrier insertion is indicated by this reorder alone.

## BSP-002 — Exact predicate and equivalence

1. Let s be the same uint32(x_bias+x) computed by the baseline. For cached
   pixel_xor p<=3, aligned s and positive count divisible by4, each complete
   group4k..4k+3 is permuted onto itself. XOR2 visits2,3,0,1 instead of0,1,2,3
   relative to that group; the address set is identical and every byte distinct.
   With count<=UINT32_MAX-s, the range/end computation is conservatively non-
   wrapping. This does not separately reject the original unsigned addition's
   defined wrap; it uses exactly its resulting s, as proposed.
2. Each address receives exactly one function F(v)=(v&P)|(C&M), with P/M and
   colour already captured by value. Operations on distinct bytes commute even
   if P and M overlap. No external texture/source read changes with the order.
   The baseline caches row, mapping and masks before its stores; candidate must
   do likewise, without reloading possibly aliased metadata mid-span.
3. Rows may alias each other and metadata may be affected by stores, but the
   same span finishes with the same bytes before the next span/row call. Keeping
   those call boundaries/order makes that an induction over the original painter.
   Do not generalize to row-major grouping, span coalescing, per-pixel varying
   colours, source-dependent writes or another changed callback/read sequence.

## BSP-003 — Preserve existing refusal and early-exit behaviour

1. Leave the linear branch intact and retain the native count0 return BEFORE
   fetching target.rows[y] or forming a new row+start pointer. Evaluating an
   optional predicate must not make a formerly unused row pointer observable
   in the zero case. Unaligned, non-multiple4, p>3 or excluded wrapping cases
   take the exact existing scalar branch, with no new error or mutation.
2. Integer alignment/overflow checks are not a proof of writable allocation
   extent. Keep the caller's admitted x/count/y and actual returned row span;
   group-rounded prefix/suffix context bytes remain protected. Use actual
   per-row pointers; no frame flattening or adjacency inference is needed.
   A forward byte pointer stays within the same row's original accessed range.
3. Keep one byte read and masked byte store per addressed pixel, unchanged
   preserve/colour semantics, row/call order, buffer/frame lifetimes and
   acquire/release/error/presentation boundaries. Changed code generation can
   alter footprint/stack/barrier placement; the consumer's selected actual code
   and scalar/output checks remain necessary, without an added owner approval.
4. Source compatibility identifies no new ABI obstacle for the stated subset.
   It does not establish eligibility frequency, lowered instruction savings,
   cycles, task headroom or physical speed. No new candidate/helper/service,
   runtime workaround or retroactive Canvas-conversion endorsement follows.

Primary sources read: exact control fill_span and frozen plan; current API
Scoped colour drawing rows; retained frame/runtime/Canvas/controller guards;
and [Cadence ISA §8.3.164 MEMW](https://www.cadence.com/content/dam/cadence-www/global/en_US/documents/tools/silicon-solutions/compute-ip/isa-summary.pdf#page=490)
for ordering scope, not a cycle/atomicity guarantee. The predicate proof concerns
ordinary owned RAM under this existing contract, not device-I/O side effects.
