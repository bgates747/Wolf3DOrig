# First controller check stopped before test

Actualcompiler325, first Python import failed because the dev-env interpreter
lacks serial. No check assertion, target access or listener host compilation
ran. Receipt/log and exact scripts are preserved in build/composition01/.
The source correction in run_composition03 uses the actual Extender interpreter,
as required for the imported physical adapter. New composition02 output preserves
the original failure. Scope, guards, controller behavior and selected cohort do
not change; no dependency installation or target retry is selected.
