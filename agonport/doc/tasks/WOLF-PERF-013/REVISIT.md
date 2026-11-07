# Revisit sprite-column hoisting with Smith after he has slept

- [ ] WOLF-PERF-013-07 — Discuss whether to keep the qualified sprite-column
  hoist for its reduction in repeated work, even without a measured FPS gain.
  Smith explicitly requested this review later today after getting some sleep.

Smith's point: removing redundant work from an inner loop can be worthwhile
without an immediately visible framerate win; other resource use in a concurrent
system and presentation cadence can obscure that benefit. Keep this distinction
in the acceptance discussion. Do not treat FPS as the only acceptance criterion.

Preserve both exact modules, all source and actual78 measurements. Candidate
972f3597 is correct in the qualified output tests and reduces repeated decisions.
Its measured sprite-rich inclusive draw interval is0.80% shorter, ordinary-room
interval2.05% longer (less replication), presentation rate unchanged in both;
package+200B and outlined sprite frame368B. Local CCOUNT is not an exclusive CPU
profile. No causal cache/scheduling/other-task resource attribution was measured.

The earlier no-promotion result records the decision at the time. Its tradeoff
is now explicitly reopened for human discussion. Keep a926 as the current
comparison control while continuing the independent background-fill arm; do not
silently discard972f or blend it into that separate frozen comparison. This
follow-up selects discussion and preservation, not an extra run or immediate
production/default adoption.
