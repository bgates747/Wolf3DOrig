# Wolf3DOrig TODO

This is the project's single authoritative list of intentionally promoted,
unfinished work. IDs are stable references and are not reused. When an item is
accepted, rejected, or superseded, record its ID, evidence, and rationale in
the current dated development log, then remove it from this file.

[ ] 1. Requalify the current collision and aiming changes, reproduce the two
direct-eZ80 patrol/door-obstruction mismatches that kept commit `4facefe` out
of the first packaged release, and correct any remaining regressions.

[ ] 3. Add the first application shell: a future Agon-splash hook, original
title and control-panel presentation, visible game version, original shareware
episode and difficulty selection, and a clean start/quit flow.

[ ] 2. Implement level completion and the transition into a general
level-loading and world-reinitialization path.

[ ] 4. Widen or remap the byte-sized actor-state dispatcher before importing
the remaining original actor states, avoiding the current 254-ID ceiling.

[ ] 5. Implement bosses, projectiles, ghosts, and other special actor
behaviors from the original game.

[ ] 6. Implement music playback as a separate subsystem from the accepted
sound-effects implementation.

[ ] 7. Add high-score entry and remaining presentation polish after the core
game progression is established.
