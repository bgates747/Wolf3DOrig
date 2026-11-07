# Linked staging qualification

Compiler469 completed five maintained build configurations, the real corrected
guest and one tiny-package layout check. Six ownership/result tests and17
decoder checks passed. Old executable overlap and forged emitted destination
are rejected. Peak57.3C; all children joined and compiler released22:40:41UTC.

Standalone disabled remains SHA063f7ab7b9b2df44fe1541871662ce7656c3c28d6693872de824c5bfce40a2e6.
VDPlet binaries intentionally change to correct pre-existing code corruption;
this is distinct from profiling-disabled byte identity in the earlier task.
Native22572B module8d3d remains unchanged.

|Backend|Profile|Native|Bytes|SHA256|
|---|---|---|---:|---|
|standalone|False|False|276641|063f7ab7b9b2df44fe1541871662ce7656c3c28d6693872de824c5bfce40a2e6|
|standalone|True|False|287437|b77cc3dd372ceb5a88248b03e9fa81597c078f5cea0539267296c9885f01ae08|
|vdplet-direct|False|False|310816|6322d8c7771c3b186ad55a8edbaace41591cca8045239079326c1f8d1f64c3f3|
|vdplet-direct|True|False|321616|1e63f1bd343166403d1421973155bcafa9bb00c72a77937b0ad06ecd45bfae7d|
|vdplet-direct|True|True|322137|01c2819700e5792244015ca3db4aed0a9916b639fa967a78def1dd3844a1c2bf|

Corrected diagnostic guest322539B SHA49c9355f570e58d0b2665df24a161155db3827cea8057740db9ac5781c5a2a6c.
Reserved package extent089245–08EA71 (end exclusive),22572bytes; the test
fixture follows it without overlap. MOS read/upload and zero-scratch operands
all point to that linked extent. The normal maintained app has no test fixture.

Original storage03 forward-EQU assembler rejection is preserved separately.
Storage04 used ordinary linked labels and passed. No emulator or physical
timing result follows from these offline checks. Alexe03 is separately selected
under the original300s bound and unchanged runtime/module/assets/guards.
