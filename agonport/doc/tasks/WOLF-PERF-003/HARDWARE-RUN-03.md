# Hardware03 — explicit native recorder lifetime

Continue Smith's existing corrected physical comparison authorization after
clean41 release. Hardware02 stopped before first paced sample. Source now
identifies a task instrumentation lifetime bug: nativeA retains its recorder
pointer/count after the host log buffer is cleared. After an unpaced600-run,
the next warmup's finish rejects count>=600 and render_frame returns before
publishing completion. After CPU mode, a non-full stale pointer can instead
write freed/reused storage on the next warmup. This is task code, not a
production renderer or EMOS defect. Earlier native timings remain provisional
pending a repeat with defined recorder lifetime.

New task-only command242 (offset0) releases recorder ownership: null pointer,
zero count, cleared error. A guests obtain its normal token-bound P3DR80/81
ack before creating/replacing the log and again before deleting it after all
readout. No draw request/reply replay, no longer measured wait, no renderer or
CCOUNT bracket change. Existing recorder overflow/core/interval checks remain.
B module recorder is instance-owned and reinitialized on load; inspect its
retained source/lifecycle before readiness. B native/module stay unchanged
unless that review finds a separate concrete defect; no silent substitution.

Build on normal Pi FIFO: four A eZ80 assemblies (120s each), serial nativeA
ESP32 build (900s), bounded native host regression compilation/execution with
ASan/UBSan (120s each). One compiler/child at a time,80C/512MiB guard, owned
cleanup/self-release. Host tests extract the exact native command method and
exercise CPU0/render600/paced-subset repeated lifecycles, release-before-free,
failed/invalid release and strict overflow. Reproduce old full-recorder refusal
without undefined access. No emulator or hardware inside compiler checks.

Freeze changed A image/guests plus unchanged B/rollback and source diffs, then
reserve a new Olimex slot and obtain actual fresh admission. Same canonical
room, actors suppressed,720degrees/600quanta and separate CPU/unpaced/paced
contracts. Same14fixture/eight B INFO schedule as hardware01, with first changed
Acontrol as setup gate. Four app-only/tail writes including exact restoration,
each independently read back; preserve startup/P4/EMOS/partitions/other slot.
Reuse stable /test/wolf/perf003, preserve known prior RAM/results and unknown
files/journals, replace only identified guests, archive/reset task config.
Each guest/probe300s, first unexpected failure stops all successors; budget
provisional100minutes as hardware01 (prior two tranches stopped early, not
proof of whole-suite duration). No auto replay or test startup. Fresh recovery
and RAM SAVE before LOAD on a failure; exact incoming restore/fresh normal
CLI/mode0/callbackzero/input/idle/freeports handback and release. SD mounted.
