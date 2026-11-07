# PERF022 — actual foreground handler/observer qualification

Frozen source ad14e95, actual compiler395, released16:10:52UTC with no next
request. Three disposable controllers and three observers were real foreground
children of the unchanged app-server1750. No hardware transport was imported or
used. All original tool handles are terminal and all nine exact controller,
wrapper and tracer PIDs were independently absent before release.

Normal exit passed. The actual unchanged host_interrupt08 handler recorded one
controlled SIGTERM, raised HostInterrupted and exited1; its independent observer
exited0 and recorded the known sender1440188/UID1000. Cancelling only the observer
wrapper made its finally path stop/join the tracer. The controller exited0 after
refusing its successor and performing a dummy cleanup callback; it received no
SIGTERM. Observer cancellation's exit1/passed=false records that intentional
interruption, not a failed cancellation control.

Each case also refused five malformed/missing handshakes (15 controls total)
before its first admitted dummy callback. These are actual live process identity
and /proc attachment checks with separate immutable negative-control files.
No device callback or test fixture was dispatched.

Raw trace, original handler receipts, source snapshot, identities, controlled
sender receipts, terminal handles/PIDs, lease and SHA256 manifest are retained in
[results/host01](results/host01). This qualifies the new observer/recorder path,
not the still-pending adapted physical controller. Historical84/91 sender/cause
remains unknown. Simultaneous cancellation of both foreground jobs remains a
limit; tracing can perturb host setup/collection. The full six-arm physical
comparison and normal Mech-first admission remain pending.
