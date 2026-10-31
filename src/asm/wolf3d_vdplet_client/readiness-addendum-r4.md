# Production-client final readiness addendum r4

This addendum supersedes the candidate pins in r3 after Golem reconciled the
generation-33 diagnosis and requested a focused review of the adjacent unload
error return. It does not alter either preserved failed run.

The final production-client correction remains limited to the two proven
generation-33 defects:

1. copy the untouched owned-handle high byte into the UNLOAD packet before
   using `or b` to test whether the handle is zero; and
2. explicitly set carry when close still owns a live handle, so unresolved
   ownership cannot be reported as successful cleanup.

The adjacent `cp W3D_VDPLET_STATUS_RUNTIME; ret nz` path was audited rather
than changed. Its only reachable non-runtime inputs are timeout 1 and protocol
2, both below runtime 3, so the comparison preserves carry. Statuses 4 through
7 are created outside the reply-wait/unload path and cannot reach it. The
detailed audit is frozen in `readiness-addendum-r3-flag-audit.md`.

## Final local evidence

- finite client fixture: 2,295 bytes, SHA-256
  `1096669ce659a744b4cb95ac53dc3c9881fd6578d646645c9eb0a541f149f230`
- fixture source:
  `9987cbce02cd781f5252c6e3bbfe60e6efb2e65fa91a7646eab624707c9e89ea`
- production client include:
  `3a2d83c639cd1e4e5c84729cb89bda61d02c55beebc3e4392c2b41ce89c4ab79`
- accepted copied module: 7,952 bytes, SHA-256
  `57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be`
- complete copied-backend application: 107,959 bytes, SHA-256
  `c0578fe8a4e0b3441aade250a18ce19fd1630f7444a1088747b0d762fe8beccf`
- standalone default and rollback: 106,434 bytes, byte-identical SHA-256
  `2dee8b17ac83b8e7a43d7e1dcbd6962b1d24274ca489c145ef44a5fd1c0ea258`
- focused host regressions: 21 passed, including the exact rejected
  generation-33 tuple, both teardown corrections, both ADL zero-extension
  corrections, and all prior mailbox/ownership cases
- ADL-width audit: zero definite hazards and zero unresolved review items;
  all four detected wide memory accesses are annotated 24-bit storage

A successful target result must be exactly result 0, status 0, pending 0,
callback error 0, handle 0, native error 0, token 7 and schema 1. Any retained
handle, nonzero status or contradictory result remains a failure. The stopped
profile and its generated manifest/receipt are pinned separately after this
document enters the package. No target execution is claimed here.
