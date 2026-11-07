# Column-chain qualification: no hardware timing yet

The bounded ascending chains pass **6272 independent scalar cases**, existing
renderer/module checks and exact600-pose frame/state/span parity. The target
control reproduces exact a926. The source change removes repeated inner
membership scans; it does not change the scalar sampler, pixel order or geometry.

| Arm | Package bytes | SHA256 | Resident data |
|---|---:|---|---:|
|Original|24420|a926b48ab3207b59773cc8283d59cc687f274ef2af00017451567449a4c69656|13348|
|Chains|24592|0e4ee86eb10c07d54933fc06c550fe1e871942d197090b20604674ec959b9f32|13348|

Package cost is **172B**. Actual target frames differ from a nominal local-array
estimate: draw_walls becomes a separate608B frame; renderer frame336B remains
live underneath. The selected module wall/acquire chain is1488B against2048B;
adding the matched native384B prefix and64B acquire frame gives **1936B against
4096B**, versus original1344B. The selected path increases592B, not just the384B
array-storage delta. This is not a universal ISR/error/foreign-callback peak;
actual cumulative INFO watermark and the unchanged512B floor still gate runs.

Scalar coverage includes empty groups, singleton column0, singleton column255,
head0/tail255, all127 IDs, repeated groups, invalid/door/nonpositive domains,
arbitrary masks/mapping/guards, aliases between rows or source/frame storage,
null statistics and acquire/null/short/release-error paths. Pixel output,
ascending acquisition/release, error precedence, statistics and metadata agree.
The byte self-link terminator is tested with255 as a valid column, not a sentinel.

The unchanged control raycast on the canonical E1L1 W3L map/doors/camera and
600-angle script finds1199104 original inner membership visits, versus153600
chain-column visits: **1045504 avoided,87.19% fewer inner visits**. Each pose saves
1024–2560 such visits. The256-column discovery/construction pass, head/link
initialization, outer ID traversal, source loads and pixel writes still cost
work. This is a source/host census, not native instruction/branch counts or a
timing result. PERF014 cached IDs alone leave these inner scans in place.

Both actual uncapped eZ80 producers qualify. Original reproduces accepted c43e7;
candidate's twelve changed bytes are exactly the six linked package-size/limit
operands,24592/24593, with unchanged SP and presentation-call addresses. No
stale24420-byte producer is selected. Actual resident RAM must still verify
those operands after any future run.

Actual serial compiler365 completed in106.008s, all children joined and normal
release **2026-11-07T13:34:19.404198UTC**, no next request.96 exact source inputs
were archived before checklist disposition. Actual guest compiler366 completed
in2.443s, children joined, release **13:37:43.212856UTC**, no next.
[Source/target/host evidence](results/build01/SHA256.json),
[nested-stack proof](results/build01/nested-stack-source.json) and
[real producer receipt](results/guests01/receipt.json) retain the evidence.

No hardware case, new firmware/API/helper, production default or arm combination
is selected by this result. Keep queued PERF018 immutable and MechAgon first.
A useful matched physical contract requires its own current tuple, exact rollback,
host/controller/listener lifecycle freeze and normal fresh admission.
