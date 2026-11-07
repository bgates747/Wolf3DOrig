# Prospective launch-tracer: direct coverage, group gap

Actual compiler389 completed all three finite host-only cases in0.637s. The
ordinary-exit negative control emitted no SIGTERM record. A direct signal to
the traced child recorded the exact known parent PID1434918/UID1000 and the
child terminated normally by SIGTERM. A signal to the owned tracer/child group
terminated both, but produced no sender record. Tracee exit was independently
observed with native pidfd; all owned tracer children joined and normal release
completed15:46:07.672263UTC, no next request.

This qualifies that particular direct-signal observation only. It does **not**
identify actual84/91's sender, prove a fixed timeout, qualify group attribution,
or justify a hardware retry. No target, app-server attachment, service/lifetime
change, detach or signal blocking occurred. Explicit interruptible=1 preserved
fatal-signal behavior rather than using strace's potentially blocking default.

Initial compiler388 failed before the direct/group qualification on missing
os.pidfd_open in Extender Python3.14. That original attempt, sources and release
remain separate. The corrected parent is installed system Python3.13; actual
traced children still use the original Extender interpreter. No packages or
private ABI were introduced.

The remaining concrete question is whether an observer attached from a separate
owned group can record a controller-group signal without becoming its parent
or swallowing that signal. A tracer-only cancellation also needs qualification:
it must detach without altering the observed child's normal lifetime. Those
are a separately selected source check, not claims established by r02.

See [exact r02 evidence](results/r02/SHA256.json),
[first failure](results/failed01/SHA256.json) and [next contract](R03.md).
