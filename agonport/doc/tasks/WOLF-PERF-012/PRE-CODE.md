# Supported uncapped presentation method

The actual PERF011 paced guest is the source. Its render completion→C3→ordered
mode fence→post-presentation timestamp path is already physically qualified and
visually confirmed. Remove only @pace through pose selection, using the existing
PERF009 sequential pose selection, and keep the per-frame presentation. This is
supported by current public APIs; no firmware helper workaround is needed.

Keep600 records/poses and two turns, preserving existing buffer/log bounds. The
run duration is measured rather than fixed20s. Mode4 explicitly identifies the
uncapped visible fixture; record1..600 headings and all presentation times. This
is distinct from hidden throughput and distinct from fixed-duration paced30Hz.
Vertical-refresh/actual render/fence waits remain part of the real presentation
path; no synthetic frame delay remains. Renderer/package itself stays unchanged.

Actual77 is restored/idle after accepted PERF011, exclusively held by Wolf.
Retain immutable original kit/current component evidence and new extension
bindings. Source-owned normal metadata MOVE preserves original on-card outputs
and generated config into a unique archive before their active names are reused.
Original host raw files/RAM are also retained. Reuse only unchanged asset files
whose previous full readbacks match source and whose content was not written by
the guest or sole owner. Fresh guest/module readbacks and metadata inventory
join that retained provenance. No source, renderer, carrier or SDK redesign.
