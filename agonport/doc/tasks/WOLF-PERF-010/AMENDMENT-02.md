# Preserve first assembly failure and correct the static guard

First r01/1233bbb attempt compiled the banner into unpaced output; exact-binary
isolation correctly rejected it before any device/emulator run. The assembler
did not evaluate the written `WP_MODE = 1` condition as intended. Preserve r01
outputs, receipt and compiler305 release; do not weaken the unchanged-timed gate.

R02 uses a simple WP_STATIC_TIMER equ0/1 Boolean, derived by exact preparation
parsing of actual source WP_MODE1(control)/2(unpaced). Existing `.if FLAG` syntax
is already used by this toolchain. This equ emits no bytes; both real unpaced
binaries must still reproduce exactly. No timer/provider/render/VDPlet change.
The label data/method/layout remains the same. A separate build/receipt follows
normal Pi compiler custody; no current/old hardware test is replayed.
