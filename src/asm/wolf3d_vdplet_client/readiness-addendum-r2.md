# Production-client readiness addendum r2

This addendum supersedes only the corrected target-readiness pins in
`gen31-failure-amendment.md`. That first amendment and its SHA remain immutable
as the diagnosis of generation 31.

After freezing the client-side HLU correction, a widened manual audit found the
same ADL class in the finite test fixture's return path. After `mos_save`, the
fixture copied its result into L and cleared H but not HLU, then stored and
returned all 24 bits of HL to MOS. A successful result could therefore be
reported as a false autoexec failure even after valid module cleanup. This path
was not reached in generation 31, which correctly returned failure in L; it is
a preemptive fixture-only correction, not a reinterpretation of that evidence.

The fixture now executes `ld hl,0` before copying the one-byte result into L.
No production client include, wire command, runtime, module, scene, cleanup or
standalone code changed in this second amendment.

## Final stopped candidate pins

- client fixture: 2,292 bytes, SHA-256
  `b65883fd8d7293430b3384ea1e5484fd04b72c4dd72abb6a5a6f8bfb96ca71d3`
- fixture source SHA-256:
  `9987cbce02cd781f5252c6e3bbfe60e6efb2e65fa91a7646eab624707c9e89ea`
- production client include: unchanged
  `e857fd548466f33fc07e35efe9583e78a0245351156548711620c5e7bf7a179e`
- accepted copied module: unchanged
  `57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be`
- standalone default: unchanged
  `2dee8b17ac83b8e7a43d7e1dcbd6962b1d24274ca489c145ef44a5fd1c0ea258`
- proportional host regressions: 17 passed, now pinning both u16 reply and
  MOS return zero-extension
- ADL audit: zero definite hazards; two reviewed 24-bit MOS clock reads

The package/profile must be rebuilt and verified stopped against these pins
before any new central request. No target result is claimed by this addendum.
