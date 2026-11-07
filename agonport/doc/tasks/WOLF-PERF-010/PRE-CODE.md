# Caption support and lifetime ledger

The static control deliberately aborts immediately after wp_prt_init, before
wp_create_log or either warm-up frame. It proves failure-path timer/interrupt
restoration and MOS return, not raycast/render speed. Its existing loading hint
incorrectly promises later rotation. Fix that message at the same time as the
large persistent caption.

The3D view occupies x32..287/y20..179; HUD begins at y200. A5x7 capital font
scaled2x2 gives14pixel height; the25-character primary line fits within300pixels.
Center it in the20pixel strip y180..199. Use high-contrast opaque pixels so the
caption does not depend on previous page contents. The normal HUD and view bounds
remain unchanged; no renderer or world field is altered.

Existing application VDU helpers already upload byte buffers, select a16bit
bitmap ID, create a bitmap from the buffer and draw it at native coordinates.
A task-owned small caption bitmap is uploaded once for a static-control run,
then selected/drawn during each page reconstruction. Do not send thousands of
individual pixel commands for every loading update. Current public buffer clear
also removes registered bitmap users. Fence queued draws before retiring the
owned caption, and never clear an unknown production ID. Close the selected
fixture-ID collision check and exact initialization/exit placement before coding.
No font replacement or private native/firmware import is required.

Only WP_MODE1 should contain caption code/data and revised hint. Unpaced inputs
must assemble byte-identically to the frozen producer controls. Both loading
pages must carry the same label/count. Reusing this existing display method is
supported; source compatibility does not establish actual Fab/native pixels.
Physical75 is not a caption test and must not be resumed for this change.

Gate closure before implementation: actual wolf3d.asm defines control WP_MODE=1
and unpaced WP_MODE=2 (initial plan's mode0 shorthand corrected). Reserve caption
ID0xf1b0 outside actual wall/sprite/HUD/staging/audio/diagnostic ranges; none of
the fixed source constants or generated asset IDs use it. This is an explicitly
owned fixture-only ID, not a public allocation policy. Upload once, draw after
normal text in each page reconstruction, then flush Canvas using existing public
VDU23,0,0xca before buffer clear. An ordered ingress acknowledgement follows
retirement; initialization/cleanup error must be visible and retained. Hook
cleanup in normal main exit before restoring the old display mode, including
loading-abort exits. The existing buffer clear removes bitmap users as well.
Static caption code/data and hint are conditional on mode1; mode2 binary remains
identical. Source/method compatibility closed, actual assembly and visual gates
remain. No current75 application or unpaced rendering change.
