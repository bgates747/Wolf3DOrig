# Pre-code support/work review — optimization flag only

Control is exact bf7f2bb038387698464fbb297a437ef98457638a28261dc7f9688044d9b6eb28,
19896B physical67 module. Its qualified source lives in PERF005/build/r02/
candidate; native7593 and all scene/timing/producer qualification remain the
reference. Preserve prior tasks and source/SDK/producer snapshots.

Current frozen SDK builder hardcodes -Os in tools/build_module.py. Bespoke uses
-O2; source reports identify this as policy rather than ABI necessity. For this
single consumer experiment, copy the same SDK into task-only ignored inputs and
replace exactly that compiler flag with -O2 in the candidate copy. Original SDK
copy remains byte-identical. Do not change owner SDK, add an exported SDK option,
select -Ofast/fast-math, change helpers/libraries/source or relax any safety flag.
Retain -fPIC/-mlongcalls/literal policy/-fno-builtin and mandatory
-mfix-esp32-psram-cache-issue, declared ABI1.6/cap257 and all package limits.

All original/candidate native and production source must compare byte-for-byte;
only optimization flags may differ in actual target compilation. Host checks
should exercise the same current source under respective optimization policies
with sanitizers, but cannot qualify excluded Xtensa helpers or actual native
provider code. Actual target ELF/disassembly/provider/section/relocation and
individual-stack changes require inspection; whole-call stack is physical.
Original module must reproduce exact bf7f; any mismatch stops before timing.

Rebuild/bind actual eZ80 package producers to each resulting module length and
strict limit. Check real source/listing/binary MOS read/upload/VDPL LOAD operands,
module file/header and dispatched arm, preserving source/timing loops/clock/
assets/SP observation. The stopped65 producer-length failure is an explicit
negative regression. Match outputs including sync/guards/masks/clipping/lifetime
and retain host oracle/page/provider/native zero-entry limits. No unsupported
operation is worked around. Report a lack of speedup as a valid result.

Compatibility axes unchanged: same direct rows/lease/RUN/frame completion,
metadata/resource/image ceilings and safe bytewriter. Compiler may alter code
shape, literal layout/stack and package length; qualify those before admission.
This is distinct from later provider/memory/loop transformations in the backlog.
