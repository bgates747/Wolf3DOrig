# Separate observer qualifies controlled direct and group attribution

Actual compiler391 passed four real Linux process cases in **1.723s**. The
observed child remained on Extender Python3.14; installed system Python3.13
owned the child and its separate foreground strace process. Actual /proc
TracerPid was verified before input; native pidfd independently proved child
exit and both Popen children were reaped. No app-server or real controller was
attached, and no device/serial/HTTP/reset/firmware action occurred.

|Controlled case|Observed child|Observer|Evidence|
|---|---|---|---|
|Normal exit|exit0|exit0|No false SIGTERM record|
|Direct child SIGTERM|signal15|exit0|Exact sender PID1436455/UID1000|
|Child-group SIGTERM|signal15|exit0|Same exact sender; observer's different group survives|
|Observer-only SIGTERM|Still alive after actual detach; then explicit owned cleanup|signal15|Observer cancellation did not terminate the observed child|

`--interruptible=1` preserved fatal-signal behavior. No fatal-signal blocking,
daemonizing, alternate Codex process API, private ABI, new installed package or
service/lifetime policy change was used. This arrangement observes only its
exact assigned PID, not descendants or other jobs. Unlike r02's launch tracer,
it does not become the target's parent or share its process group.

All owned children stopped/joined, compiler391 released normally at
**2026-11-07T15:54:49.831762UTC**, no next request. The source/input/tool archive,
actual commands/ready/attachment/signal/exit records and raw traces are in
[r03 evidence](results/r03/SHA256.json). Original failed388 and direct-only389
remain separate evidence; neither was overwritten or relabelled.

This qualifies these prospective controlled cases, **not the actual84/91 signal
sender or root cause**. Simultaneous cancellation of both independent foreground
jobs, a real controller's custom handler, other signal types, target-specific
ptrace refusal, process/thread changes and performance effects are not proved
by the disposable default-handler cases. No hardware replay or controller
adoption follows automatically.

A real integration needs its own frozen contract: preserve the actual controller
parent/group and original foreground handle; attach the second foreground job
only after exact controller identity is recorded; prohibit device I/O until
positive attachment; check observer identity/liveness before new submissions;
allow safe in-flight completion and preserve first failures/available RAM;
terminate/join both actors before release. Qualify the existing host recorder
and those admission/refusal paths before selecting that physical trial. These
are source coordination requirements, not an implemented runtime change.
