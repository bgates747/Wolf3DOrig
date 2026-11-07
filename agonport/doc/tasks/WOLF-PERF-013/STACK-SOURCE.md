# Selected target nesting and stack disposition

Actual final candidate .su and instructions expose the outlined368-byte sprite
frame, rather than incorrectly treating the local table as only256extra bytes.
The selected module nested path is128+304+48+352+368+64=**1264bytes** through
acquire_asset. It is under the admitted2048module stack budget; all frames are
static and no recursive sprite calls occur. Unchanged validation is a separate
branch, not simultaneously live with the sprite kernel.

The exact retained native firmware.bin rehashes7593, the selected timing app.
Its matched ELF yields processLoop32→processNext48→vdu32→vdu_sys48→
vdu_sys_vdplet160→runtime.call64=384bytes upstream of module entry. The ordinary
read acquisition has64bytes. Valid immutable asset buffers are still owned by
the global bank, so ordinary shared-pointer lease release is not the last-owner
allocation/destructor branch. getBuffer/size are inlined. Selected chain total
**1712bytes** versus the source-configured4096-byte processLoop task.

This is a source/disassembly bound for the selected ordinary branch, not a
universal exception/foreign-callback/ISR proof. The existing ESP32 port interrupt
mechanism and native task setup are unchanged. No asynchronous/reentrant render
or new callback is introduced. Do not subtract256from an old cumulative watermark
and call it an exact per-arm margin. Entry/after-case resource probes retain the
existing512-byte minimum and stop on first unexpected state; report those as
cumulative observations. Other command/setup/error paths retain their original
policy and safety limits. Full task peak attribution remains explicitly limited.

[Native/package identities and frames](results/build01/nested-stack-source.json).
