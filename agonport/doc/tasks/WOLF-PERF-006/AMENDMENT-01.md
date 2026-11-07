# Qualify live provider closure instead of requiring unused helpers

Freeze before checker correction. R01-RESULT preserves the first strict gate
failure and exact source/target outputs. Both measured bf7f control and new O2
candidate have no live __udivdi3 symbol: it is an unused local definition removed
by selected --gc-sections. The live signed __divdi3 resolves to the same source
local divide_u64 algorithm; memcpy/memset also remain local, no linked libraries.

Correct the checker to require actual live __divdi3/divide_u64/memory/entry
providers, reject undefined/new foreign providers and compare actual tool argv.
Record optional __udivdi3 presence/absence rather than insisting an unused
function survives. Keep same-source/hash/flags/section/ABI/PSRAM/stack/limits/
output proof; no weaker runtime gate, provider source change or library added.
A fresh finite file-only qualification run on hash-pinned r01 modules is enough;
retain its new receipt separately and never rewrite the failed277 result.

Continue selected per-arm producer assemblies and derived controller/lifecycle
qualification under normal compiler custody. Original O2 module target bytes
must remain unchangedcd429e2f and controlbf7f; a changed artifact requires a new
candidate build/disposition. No full retest/rebuild of passed immutable outputs
merely to fix an overstrict metadata assumption. No new rendering axis/test
scope or extra owner approval pause. Fresh physicalkit/grant/Author hold remain.
