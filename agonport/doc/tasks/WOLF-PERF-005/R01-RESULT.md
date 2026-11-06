# Span qualification01 stopped at test-source warning

Actual compiler270 ran the original signed arithmetic, renderer/error,
module/lifecycle and600-frame equivalence checks successfully. The new direct-
span test then failed compilation under unchanged -Werror due to misleading
indentation of the statement following a one-line for loop. No candidate code
or target module was built/run. This was a test-source formatting defect, not a
renderer or sanitizer failure. The source was corrected with explicit braces;
no warning suppression, oracle weakening, target/mechanism change or retry in
the old output tree is selected. A fresh r02 preserves all r01 logs/inputs.
All owned children joined and compiler270 released; nextnone. Raw receipts are
retained under ignored build/r01. No hardware or emulator action occurred.
