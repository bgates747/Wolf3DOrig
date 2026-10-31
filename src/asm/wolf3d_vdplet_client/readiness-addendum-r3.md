# Production-client readiness addendum r3

This addendum supersedes the target-readiness pins in r2 after the preserved
generation-33 teardown failure. It does not alter either failed run or the
accepted copied renderer/module/runtime evidence.

Generation 33 displayed the exact oracle scene and exercised the real key path,
but the client patched owned handle `0x0001` into UNLOAD as `0x0101`. Runtime
HANDLE 8 and INFO2 value 1 were correct. A separate carry-loss in
`w3d_vdplet_close` then let the fixture report result zero despite status 3 and
retained handle 1. The exact trace and corrected interpretation are frozen in
`gen33-unload-amendment.md` and `gen33-diagnosis-r2.md`.

The final local correction:

1. stores the original handle high byte into the UNLOAD packet before the
   nonzero `or b` test; and
2. explicitly sets carry before returning from close when a live handle remains
   after an unload failure.

No packet layout, timeout, token, INFO2, callback/storage protection, runtime,
module, scene, or standalone code changed. Result zero remains valid only after
completed UNLOAD, zero handle and owned-buffer cleanup.

## Final r3 candidate pins

- finite client fixture: 2,295 bytes, SHA-256
  `1096669ce659a744b4cb95ac53dc3c9881fd6578d646645c9eb0a541f149f230`
- fixture source: unchanged
  `9987cbce02cd781f5252c6e3bbfe60e6efb2e65fa91a7646eab624707c9e89ea`
- production client include:
  `3a2d83c639cd1e4e5c84729cb89bda61d02c55beebc3e4392c2b41ce89c4ab79`
- full copied-backend candidate:
  `c0578fe8a4e0b3441aade250a18ce19fd1630f7444a1088747b0d762fe8beccf`
- accepted copied module: unchanged `57b635fc...`
- standalone default: unchanged `2dee8b17...`
- focused host regressions: 19 passed, including both generation-33 teardown
  fixes and all prior zero-extension/ownership cases
- ADL audit: zero definite hazards; two reviewed 24-bit MOS clock reads

The package/profile must be rebuilt, pin-verified and stopped before any new
central request. No r3 target execution is claimed here.
