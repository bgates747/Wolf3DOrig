# Next observer cohort: preparation only

This records the intended consumer experiment after an FX-153 x86_64 release
artifact exists and its source/host/release evidence is reviewed. It is not an
input freeze, reservation or execution selection. Current blocker is compiler
routing; no artifact SHA is invented and no profile is ready to run.

Retain all native firmware/ELF, backend0866265b, MOS, assets, guest bytes,
wrapper, input shim and setup history; replace only a new private profile's
frontend with the reviewed FX-153 artifact and record the changed compiler/
artifact lineage. Use only FLEXE_TX_BATCH_OBSERVER_OUTPUT, a fresh absolute
output, and exact strict fx153-tx-v1 reader691e2b98. Unset both old diagnostic
output variables. Source/native host checks do not supply a live stall sample.

Keep fixed50s trigger/100ms poll/0,250,500ms samples/630s observer lifetime,
four attempts and five-line/20KiB output ceiling. At most two sequential JIT
processes,300seconds each plus bounded ordinary teardown, no captures/audio/
GUI. End early on a complete observer stasis series or normal guest/MOS return.
Preserve null/late/interrupted/no-sample outcomes, backend totals and exact raw
wire/delivery/console/events; intentional silence is not automatically a fault.
Observer work remains intrusive; none of these timings enter the comparison.

Before selection, fill actual release/reader/source/linked-dependency hashes,
qualify execution permissions/canonical naming, preserve old frozen harnesses,
and freeze the exact new scripts/profile manifests/schedule. Any changed cases
or bounds need an explicit identified revision. Use fresh normal Oryx FIFO/
whole-host idle checkout and successful sequential assert before each child.
Retrieve/hash, join only owned trees, fresh idle, release and immediately notify
the actual successor. No firmware/hardware, repair, adoption or public release.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
