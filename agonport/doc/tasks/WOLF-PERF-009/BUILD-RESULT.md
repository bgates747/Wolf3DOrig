# Wall-column candidate qualifies offline

Exact c8f control reproduces. Candidate a926b48a preserves all six compared whole
outputs: renderer frame/geometry, module frame,600-pose frames/states and spans.
Address/undefined sanitizers, existing renderer/module/lifecycle error matrix and
67,072 independent scalar wall-column cases pass. The latter covers all65,536
mask pairs, overlap masks, source-column edges, clipping/near walls, separate
permuted rows/lane XOR/bias, linear output and whole storage guards.

Actual target package grows24,276→24,420 bytes (+144). Text15,216→15,360; resident
data13,348 unchanged, largest individual static frame768 unchanged. ABI1.6,
cap257, stack2048/text65536/data16384/image131072 allowances, O2/PIC/PSRAM flags
and local arithmetic providers remain fixed. No new library/import/section.
This is individual-frame analysis, not a proof of whole-call-stack headroom.

The target compiler inlines the private sampling specialization into the
renderer; generic put_pixel remains for other units. Source moves native lane
x mapping, representation decision and mask loads to column setup; actual
texture fraction/read/store order remains equivalent. No speed claim follows
from that alone. Physical timing is pending.

Serial Pi compiler298 finished in119.37 seconds, peak55.65C; all children exited
and normal release has no next request. BUILD-RESULT.json links the immutable
input snapshot, actual compiler commands/sections/symbols/disassembly and logs.
Current Extender source handback confirms unchanged actual74 tuple and the
supported fresh-session collection procedure; old73 remains partial/unresolved.
