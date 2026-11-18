# Preserve first assembly failure and correct the static guard

First r01/1233bbb attempt compiled the banner into unpaced output; exact-binary
isolation correctly rejected it before any device/emulator run. The assembler
did not evaluate the written `WP_MODE = 1` condition as intended. Preserve r01
outputs, receipt and compiler305 release; do not weaken the unchanged-timed gate.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
