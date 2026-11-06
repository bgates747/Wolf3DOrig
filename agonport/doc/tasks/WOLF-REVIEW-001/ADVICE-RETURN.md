# VDPlet advice received

All four questions received substantive answers in owner mail
`2026-11-06_13-52-29_vdplet_wolf-review001-four-advice-return-one`.
The [full owner advice](/Agon/mystuff/agon-vdplet/docs/tasks/VDPL-032/WOLF-REVIEW-001-ADVICE.md)
and its provenance are pinned in [ADVICE-PROVENANCE.json](ADVICE-PROVENANCE.json).
The document SHA-256 matches the owner's mail. This is a response to the
completed self-review, not a new task or an implementation selection.

## Q-001 — Span implementation

There is no already-qualified optimized arbitrary-mask word-span routine.
The existing rectangle example is compile-checked byte-store illustration;
generic row tests qualify the stated service behavior, not a fast consumer
kernel. Hoist validated layout/masks/XOR/row pointer and span bounds where
possible. Preserve each destination's sync bits and writable edges; never infer
the next row by stride. Uniform fills are invariant under XOR lane permutation,
whereas variable pixels require the actual permutation. Aligned word candidates
need explicit bounds, access/alias/endian and generated safe-store evidence.
No safety-workaround removal or unconditional overwrite is supported.

## Q-002 — Arithmetic support

The supported builder route is still `--math` with pinned libm/libgcc and the
matching PSRAM-safe multilib. There is no separately qualified libgcc-only or
per-helper option. An intended replacement must stop defining the local helper
in its separately selected candidate, or that implementation may still satisfy
references. Archive linking does not guarantee a particular closure/layout;
generic success does not resolve Wolf's old linker failure.

Define arithmetic domains/results/refusals for zero and MIN/-1 without an
undefined host oracle. Exact target provider, signed/unsigned edge cases,
relocations, size and complete stack remain consumer qualification. Source
`.su` alone omits library/callback frames. A new narrow builder feature would
be SDK-owned work; no ROM import or default change follows from this advice.

## Q-003 — Conversion record

The six Wolf cases are retained as concrete supporting examples in the owner's
conversion discussion. The owner agrees that execution-environment substitutions
and oracle provenance should be explicit alongside required adaptation versus
optional rewrite. A host suite cannot qualify code compiled out of that suite;
an oracle can prove final pixels without independently accounting for work.
The frozen one-item brainstorm remains completed and unchanged. No general
protocol has been adopted or new task added by this exchange.

## Q-004 — First observer controls

Keep the first phase observation on the same B helper, implementation and
placement. Retain the original and, if feasible, an instrumented-disabled arm
alongside observer-on so layout/cache effects can be seen. Pin sections,
providers/flags and available placement evidence; report missing evidence.
Keep all poses/order/warmup/allocation history equivalent. Phase costs include
their asset services and current divider; no isolated helper share follows.

Bound record storage, counters/core/wrap and stack, keep records out of live
framebuffer/scratch and expired leases, use stopped readback and verify cleanup
through next use. No per-pixel or per-division timing or UART logging in the
primary arm. Helper and placement experiments are later independent axes,
not prerequisites added to the first observation proposal.

## Disposition

Advice is received and retained; the finite self-review and exchange are
complete. It strengthens the proposed detection/correction methods without
claiming a qualified fast span or replacement divider exists. No build,
benchmark, reservation, renderer change, SDK feature or protocol adoption is
selected. Individual drawing costs and the historical loading cause remain
unresolved. No acknowledgment-only reply is sent.
