# Defined scaling checks pass; host wrapper include path stops build

The actual-source fixed_div regression passes all16 signed/boundary cases under
ASan/UBSan. The original renderer's existing parity/error/capacity/pushwall
fixture also passes with defined scaling. The next host-module compile fails
because the new controller omitted the immutable SDK include directory:
`vdplet_protocol.h: No such file or directory`. This is a host-controller
configuration error, not a renderer, compiler or ABI defect. Candidate and
target builds have not run, so no full qualification or timing is claimed.

Preserve r02 source/logs/receipt. All children exited; compiler260 released
2026-11-06T20:38:38.842982UTC, nextnone. Fresh r03 explicitly supplies the same
SDK include directory already used by the production builder. No source
algorithm, helper, sanitizer or safety-policy relaxation is part of that fix.

Owner advice independently confirms the int64 scaling range and supports the
original-package identity gate. Its source-derived coverage correction is also
retained: the600 scripted poses span two turns at300 distinct integer-degree
headings, missing60 headings congruent5 mod6. "All-angle" in the frozen plan
means a full rotation, not exhaustive360-heading coverage. Updated result text
uses the precise coverage; no matched hardware pose set or count is expanded.
The clear-extent equivalence argument is independent of heading.
