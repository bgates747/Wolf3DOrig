# First host qualification stopped in the original control

The first sanitizer run found existing undefined arithmetic before any candidate
test or target build. No correctness or speed result is claimed for the fill
candidate. The original failure is retained; this attempt will not be rerun.

Pi compiler generation259/request5cafe992e5c6 was asserted before each child.
Original renderer compilation succeeded. Its ordinary renderer/error fixture
then stopped with UndefinedBehaviorSanitizer at original renderer.cpp:118:
`left shift of negative value -32768`. The fixed-point numerator expression
is `static_cast<int64_t>(a) << 16`; the C++17 negative signed shift is undefined.
The candidate never executed, and neither target module was built.

Both children exited and the guarded controller returned failure after5.22s.
No signal/thermal/resource interruption occurred. Logs, source snapshots and
build receipts remain under ignored build/r01. Compiler259 released
2026-11-06T20:33:38.467846UTC; no successor. No device/emulator/bench contact.

This is not a row-service incompatibility or proof of wrong physical pixels.
It is a source-language correctness gap exposed by the stronger host check.
Do not disable the sanitizer or hide a modified helper in the fill candidate.
A separately identified, frozen prerequisite must make the intended scaling
defined while preserving the target control and counter boundaries. If exact
original target bytes cannot be retained, stop that comparison for a new
disposition instead of treating a different binary as module1907.
