# Exact independent texture-cache baseline

Pin the output-qualified a926b48ab3207b59773cc8283d59cc687f274ef2af00017451567449a4c69656 module and matched production/native source. Source pins are recorded alongside this note before candidate code. PERF013/78 has completed and cleanly released. Smith separately reopened its acceptance for discussion; its972f candidate and all results remain intact.

Use a926 as the independent comparison control. PERF01622ef background arm is frozen and awaits hardware, so do not mix it into this candidate or edit its kit. This is not a permanent rejection of013 or a promotion of016. Later combination of independently useful changes must have its own exact predecessor/qualification.

Current wall grouping visits positive-height columns, resolves door/static texture IDs into needed[128], then re-resolves IDs during ascending-group membership scans. The new bounded256-byte local ID table is supported by existing scalar C++/row APIs. Keep column order, positive-height short circuit, door metadata, invalid-ID behavior, all acquire/bounds/release/error order, row lifetimes and wall sampler untouched. No caller mutates the const WorldMirror during a synchronous render; this is the existing renderer ownership contract, not an assumed new callback service.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
