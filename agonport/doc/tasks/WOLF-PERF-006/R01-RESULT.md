# First build: modules/output pass, provider checker refuses an unused symbol

Actual compiler277 runs all selected Os/O2 sanitizer/renderer/module/lifecycle/
600frame/span checks and six output pairs successfully. Original target package
reproduces bf7f exactly. O2 packagecd429e2f is20928B,15516B executable/9748B data/
38relocations versus19896/14344/9732/51 control. No physical speed result yet.

Final code_check requires __udivdi3 to remain present. Both the exact qualified
control and candidate omit that unused function through existing --gc-sections.
Both retain local __divdi3 and divide_u64, memcpy/memset and public vdplet_entry;
no replacement library was linked. The same-source original code itself is
counterevidence to that checker assumption. All prior steps passed; original
failed checker/log/source hash/argv/modules preserved in ignored build/r01 and
frozen-inputs. No module/source/SDK/safety/correctness change is selected.

All children stopped; compiler277 released2026-11-07T02:35:21.604825UTC (Nov6
21:35EST),nextnone. Total85.996s/peak56.75C. Bench reservation remains PREPARING,
no token/contact/test. A separately recorded checker-contract correction must
verify actual live provider closure and permit GC of unused definitions; target
bytes remain pinned and need no rebuild merely to repeat identical compilation.
