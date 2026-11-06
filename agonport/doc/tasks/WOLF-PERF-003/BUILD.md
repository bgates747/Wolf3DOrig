# Finite Pi build and host qualification

Compile task-owned sources for WOLF-PERF-003 under the Pi build FIFO. One serial
compiler/linker child at a time; at most 15 minutes for firmware and guest/module
builds together, with ordinary bounded host qualification afterward. No emulator,
GUI, flash, startup edit or hardware contact. The script must never upload.
Keep stdout/stderr and commands, stop on first unexpected failure, and retain
partial output. A necessary retry uses a fresh identified revision. Release
only after all owned build children have joined; immediately notify any actual
next build owner. Oryx execution has a separate checkout and finite run matrix
in PLAN.md, and must use qualified inputs.

Use the retained text96 SDK, including its safe classic-ESP32 PSRAM compiler
policy; do not silently use the old PERF-001 SDK or current mutable HEAD.
Freeze resolved standalone graphics/libraries rather than resolving floating
PlatformIO dependencies during compilation. Preserve compiler differences as
comparison factors. Native timing spans complete draw/drain; module-only timing
must not be described as the entire native dispatcher interval.
