# Same-source Os/O2 package and producer qualification

All source files match exactly between arms and the physical67 bf7f overlay.
Only candidate task-private SDK builder changes its optimization flag -Os→-O2;
owner SDK/default, local math/memory algorithms, ABI1.6/cap257/ceilings/PSRAM
workaround/PIC/literal/fno-builtin/ffp-contract flags stay selected identically.
Target wrapper records actual compiler/linker/strip/inspection argv and compares
it after arm-path/optimization normalization. No math library/helper selection.

Actual Pi277 completes original/candidate respective Os/O2 ASan/UBSan actual-source
fixed-div/renderer/module/error/lifecycle/600frame/98727span-rectangle checks;
all six output pairs match exactly, including frame/geometry/state/page sync/
guards. Original package reproduces bf7f byte-for-byte. Initial final gate wrongly
requires unused __udivdi3, absent in both original and candidate through GC;
coordinator fails honestly and releases27702:35:21UTC. R01-RESULT, original input
snapshot and full logs remain unchanged. Amendment29ee6a8 precedes correction.
Fresh q02 on immutable modules checks actual live __divdi3/divide_u64/memcpy/
memset/entry, no undefined imports/libraries and exact flag/section constraints;
no module rebuild/source patch/failed-output overwrite. It passes under Pi278.

| Arm | Package bytes | Executable bytes | Resident data | Relative relocations | Max individual static stack |
| --- | ---: | ---: | ---: | ---: | ---: |
| Os controlbf7f |19896|14344|9732|51|736B|
| O2 cd429e2f |20928|15516|9748|38|768B|

Actual linked compiler flags retain -mfix-esp32-psram-cache-issue; the direct
fill loop retains masked L8UI/S8I and mapping setup outside the loop. O2 generated
code puts MEMW after each store and at loop exit, versus Os's prior placement;
this is generated behavior under the same required compiler workaround, not a
manual barrier removal or a promise of identical instruction layout. Private
native span callers remain positive-count; host/source zero guard is not a
new exported native zero-entry guarantee. Helpers are same source but their
compiled code/inlining/literal/relocation/stack organization changes with the
selected flag. Recorder source/brackets also match, no per-pixel logging.

Four actual eZ80 producers built under Pi278 bind Os19896/LIMIT19897 and
O220928/LIMIT20929. Original guests reproduce physical67 candidate producers
exactly. Candidate source changes only two equates, all actual immediate bytes
joined to listing/binary/header/read/upload/LOAD; entry/exit-SP addresses match.
The actual stopped65 mismatched producer is rejected. High-RAM staging fit
requires package<65536B. Compiler278 code+four assemblies+binding checks PASS
3.184s, all children joined/released02:37:50UTC,nextnone. Original full build
85.996s/peak56.75C; no target/compiler custody remains here.

Coverage/provider/page/oracle limits remain as earlier reports: sampled600frames
are300distinct scene-heading pairs, synthetic provider/clock/math host macros
are not native helper execution or physical pixels. Individual .su entries are
not whole-command stack; physical INFO minimum>=512B and completed-counter/
output protocol gates remain. This qualifies the selected candidate for the
separately frozen real suite, not a speedup/default adoption. The finite
controller/lifecycle composition/current incoming exacttuple/grant still gate
execution. After tests restore full native/tail and idle state, HOLD actual lease
for Smith even if queued; no automatic release or further test/probing.
