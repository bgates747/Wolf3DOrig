# Selected implementation and support gate

Use PERF009 actual candidate/unpaced producer as physical source, retaining all
current a25f ROM/P3DR reply, loading, callback, package24420/limit24421 and enemy-
free E1L1 state bindings. Module a926b48a remains byte-identical. It contains the
clear-extent correction, byte-span invariant hoisting, O2 build, restored original
ray stepping and wall-column invariant hoisting. Blocked libgcc candidate is not
included. This is the latest completed optimized candidate, not an adopted game
default or a balanced physical performance verdict.

The physical PERF003 hardware05/vdplet/paced bench differs from PERF009 unpaced
only in three loop changes: elapsed-time selection of next pose, C3 plus ordered
ingress fence after each render, and removal of final-only present after stop.
Copy that exact paced bench, set WP_MODE3. Keep fixed33+600*27 timing format and
native diagnostic log; record actual completed pose indices/angles, post-render
and post-presentation ticks. The existing decoder validates monotonic timestamps,
final step600, native-count equality, timer/vector restoration and computes
presentation intervals. Coalescing can reduce visible updates without changing
the twenty-second two-turn motion schedule. No hidden throughput/FPS substitution.

Existing public present/fence APIs already support this method. No compatibility
gap or firmware/helper workaround is required. Select the already qualified
native7593 diagnostic application-only/touched-tail install with full independent
readback and incoming85f9 exact restoration/readback after review. Current76 full
EMOSa25f rollback and unchanged P4/mainboard context supplied by Extender. No
P4/EMOS/carrier/startup/listener changes. Source-only comparison plus actual linked
producer/presentation verification qualifies the known paced method; no additional
emulator run is required before this explicitly human-started physical selection.

Host preparation must have a terminal LOAD-only branch: stage/readback, install
and setup, actual CLI CD/LOAD then ready receipt, close all owned input/readers,
and STOP. No probe or guest RUN precedes readiness. A separate collection mode
does not dispatch RUN either; it observes Smith's execution and collects after
an actual return. Human wait retains lease without reset/restore/automatic release.
The application question is sent only after this ready receipt exists.
