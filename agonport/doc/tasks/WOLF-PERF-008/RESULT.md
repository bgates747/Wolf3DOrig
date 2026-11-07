# Existing provider route: admission blocked

The unchanged SDK rejects the candidate with `.eh_frame: allocated section is
unsupported by the runtime`. This confirms VDPlet OBS-003’s compatibility concern
for this exact composition. No module package is emitted and nothing ran on a
device. The original control reproduces c8f99354 exactly.

The selected esp32-psram libgcc `_divdi3.o` is actually pulled into the final link;
its 682-byte text is present and the retained final ELF has 44 allocated bytes of
.eh_frame, including linker contributions. The raw-object report’s 40 bytes and
the final link’s 44 bytes are different scopes. No libm object was pulled.
No section stripping, linker-script change, private ROM import or loader
relaxation was attempted. The compiler slot296 was cleanly released with no next
request. Build elapsed2.73 seconds; peak49.05C.

RESULT.json pins every local input/output/log, the rejected ELF and actual tool
commands. The current renderer has only the sprite/static projection wide divide
expression after the original ray-walk restoration; old per-ray divider counts
are obsolete. No timing or arithmetic-provider qualification is claimed.

This compatibility finding goes to VDPlet for supported-path advice. Meanwhile
PERF006-P03 can proceed independently from unchanged c8f with its existing local
helper: hoist textured-wall destination invariants without changing sampling.
