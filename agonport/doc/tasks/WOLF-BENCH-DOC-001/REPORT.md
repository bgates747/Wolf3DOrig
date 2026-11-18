# WOLF-BENCH-DOC-001 — Documentation consolidation

Completed November17,2026. The sole bench procedure authority is
[/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).

## Work performed

Inventoried456 tracked Markdown/reStructuredText/text documents, including
historical task archives and nested saved-source documentation. Searched bench,
Olimex, scheduling, admission, restoration, recovery and procedure references.
Removed obsolete procedural passages rather than retaining their instructions
under a historical warning. Procedure-only runbooks now point to the authority;
mixed documents retain separable factual results and application information.

Removed competing descriptions of scheduling/admission, old reservation helpers
and authorities, incoming-image restoration recipes, recovery/cleanup sequences,
old holds and release rules. Updated AGENTS.md, the repository README, firmware
and preparation entry points to direct operators to the canonical guide. Network
access instructions and application/firmware technical facts remain local;
bench operation is governed by the canonical guide alone.

AUDIT.json maps each changed tracked path to before/after SHA256 identities.
The removed instructions are deliberately not reproduced in this silo. Git
history retains the previous documentation if historical provenance is needed.
Historical byte manifests were not rewritten to pretend their old document
hashes still match. Old test packets need fresh preparation under the current
guide before reuse; retained experimental observations are not current permits.

## Verification and scope

Checked the diff for whitespace errors. Searched remaining documentation for
obsolete helper names, previous canonical bench-guide paths and prospective
Extender-grant requirements; competing instructions from those matches were
removed. Retained past-tense experimental observations describe what happened,
not a procedure to repeat. The canonical guide exists and was read in full.

Only repository documentation changed. No Python/controller, binary, raw test
result, firmware image, device, FIFO, reservation or live bench state was changed.
No application tests were run for this documentation-only task. The paused
optimization goal and viewport investigation remain unchanged.
