# controls01: restored timer, registers and actual MOS return

The originally generated, unrun cpu-fail controls restored their owned vector
then held forever. That verified a narrower boundary than the plan's normal
guest return. Revise only these two controls, preserving all timed r05 guests,
native images, successful traces and original setup failures.

Under the Pi serial compiler FIFO, copy r05's two cpu-fail source/payload trees
into build/controls01. Immediately after successful PRT initialization, mark
the selected deliberate abort and enter the existing restoration path. After
the old vector's idempotent exchange has verified restoration, verify ISS and
readable control bits match their saved values. Only that deliberately selected
restored path unwinds the saved wp_run frame and returns through ordinary game
shutdown. Unexpected failures still hold/fail. The host must see both restored
messages, normal game teardown and the actual MOS prompt before normal Quit.
No timing result or native rendering claim comes from this control.

Build attempt controls01 stopped before any assembler because ez80asm was not
on the tool PATH; original source/error/guard receipt retained and Pi147
released. Fresh attempt controls01-r02 uses the frozen production builder's
assembler resolver (/Agon/agon-ez80asm/bin/ez80asm), with the same selected
control behavior. Both builds pass under Pi148 and its guarded one-second
sampler; no timed guest or native/module binary changes.

Compile exactly two serial assembler invocations, at most120s each/300s total;
retain compiler commands/logs and actual source/output hashes. No native/module
rebuild, shared source changes, emulator or upload in the compiler reservation.
Normal thermal/RAM guards remain80C/512MiB and unavailable-sensor stop.

Freeze the resulting source/payload manifests, scripts and two new stopped
profile manifests before a fresh Oryx reservation. Use old matched baseline
frontend7e7d0e1b/backend0866265b, exact original native02 BIN/ELFs and MOS3.0.2;
the FX-152 observer is not used. Execute bespoke then VDPlet, once each, at
most300s/case, no screenshots/audio/GUI. Stop on first unexpected failure;
preserve upload stalls separately from restoration failure. No automatic replay
or performance cohort is selected by this document. Verify normal Quit/zero
backend faults, retrieve/hash all output, fresh whole-host idle, release and
notify the actual successor before further analysis.
