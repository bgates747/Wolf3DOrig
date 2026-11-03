# Wolf3DOrig shareware-parity audit and completion checklist

Date: 2026-11-02

This is the source-grounded definition of "duplicate the original shareware
behavior" for Wolf3DOrig.  The active, intentionally promoted work remains in
the repository-root `TODO.md`; this document explains why each item is there,
what original code owns the behavior, and what evidence closes it.

The parity target is the original Episode 1 / WL1 shareware game.  Paid
episodes, Spear of Destiny, their actors, projectiles, maps, and endings are
not prerequisites.  Agon branding/legal presentation and custom-episode
authoring follow parity as separate phases.  VDPlet rollout is an independent
platform track and must not be confused with missing game behavior.

## Audit baseline: behavior already present

The current port already has the following shareware behavior in production,
with direct-eZ80/host regressions and human emulator or hardware acceptance as
recorded in the dated development logs:

- all ten Episode 1 maps, difficulty-filtered object seeds, ordinary and
  secret-floor routing, and the secret-floor return to E1L2;
- fixed-step player movement, collision/sliding, door wells, keyed doors,
  elevators, door motion/auto-close, blocking decorations, and pickups;
- authoritative health, ammo, keys, weapons, score, extra lives, treasure,
  HUD, attempt death/respawn, game-over placeholder, and red fizzle;
- guards, officers, mutants, SS, dogs, Episode 1 ghosts, Hans Grosse, their
  original state timing, awareness, chase, attacks, damage, drops, death,
  sounds, and relevant area/door interaction;
- knife, pistol, machine gun, and chaingun timing and target selection;
- digitized gameplay sound effects, 30 Hz simulation independent of render
  cadence, the accepted renderer, and clean return to MOS;
- original-facing title, main menu, shareware episode selection, all four
  difficulty choices, ordinary/secret floor loading, and a functional
  floor-completion screen with authoritative time/kill/treasure values,
  abortable background loading, acknowledgment latching, and global Escape.

This audit therefore retires stale TODO 4 (paid-actor dispatcher expansion)
and TODO 5 (the now-complete WL1 special-actor tranche).  TODO 2c's lifecycle
and loading contract is also complete.  Its remaining *original presentation
and scoring* is narrower and is promoted separately below.

## Phase A: exact remaining original shareware behavior

Items are ordered by implementation priority, not by cosmetic visibility.

### A1. Pushwalls and secret discovery — TODO 11

Original oracle:

- `WL_AGENT.C::Cmd_Use`
- `WL_ACT1.C::PushWall` and `MovePWalls`
- `WL_GAME.C::SetupGameLevel` secret-total scan

Required behavior:

1. Preserve plane-1 marker 98 in each runtime level package and count it in
   `secrettotal`.
2. Give a facing-adjacent pushwall priority over doors/elevators in Use.
3. Reject a second simultaneous pushwall and a blocked destination, with the
   original refusal sound.
4. On success, increment `secretcount`, clear the marker, play the pushwall
   sound, and move the original wall texture in the facing cardinal direction
   at the original rate for at most two complete cells.
5. Update authoritative collision/DDA cells at the same boundaries as the
   original while rendering the fractional moving slab consistently.
6. Preserve pushwall state across render lag, but reset it on level/attempt
   reseed.

Acceptance: package/toolchain tests for all Episode 1 secret markers; direct
eZ80 tests for four directions, blocked/no-marker/busy rejection, both cell
crossings, stop-after-two, collision and count state; a staged E1 secret-room
visual/control test on Flexe and hardware when practical.

Status 2026-11-03: implementation and automated acceptance are complete. The
28-case direct-eZ80 behavior regression and schema-2 full/dirty serializer pass;
the stopped real-E1L1 review profile awaits human visual/collision acceptance.

### A2. Original floor-completion arithmetic and count-up — TODO 12

Original oracle: `WL_INTER.C::LevelCompleted`.

The current screen and asynchronous destination-loading lifecycle stay in
place.  Add the original visible time-bonus and kill/secret/treasure count-up,
the 500-points-per-par-second award, each 10,000-point 100% award, zero/partial
ratio sound choices, the secret-floor 15,000-point award, final score/HUD
update, and per-floor `LevelRatios` persistence.  A key may skip animation to
the exact final values; Escape must still win globally.  Loading callbacks and
animation ticks must remain nonblocking and deterministic rather than
serializing I/O behind the presentation.

Acceptance: direct-eZ80 boundary cases for zero totals, 0/partial/100 ratios,
par under/over, secret floor, skipped and unskipped animation, exact bonus and
score/life thresholds, plus staged ordinary and secret transitions.

Status 2026-11-03: implementation passes 128 direct intermission checks and
the expanded 32-case pickup/score regression. The stopped ordinary-transition
profile awaits human count-up/skip/next-floor review; the secret presentation
will be batched with it.

### A3. Episode 1 victory path and ending — TODO 13

Original oracle:

- `WL_AGENT.C::VictoryTile` and `VictorySpin`
- `WL_ACT2.C::SpawnBJVictory`, `T_BJRun`, `T_BJJump`, and `T_DeathCam`
- `WL_INTER.C::Victory` and `EndText`
- `WL_GAME.C` `ex_victorious` handling

Replace the generic victory acknowledgment with the original Episode 1
sequence: in-world victory trigger/weapon suppression and BJ run/jump ending,
then the Episode 1 total-time and eight-floor average ratios using persisted
`LevelRatios`, original Episode 1 ending/shareware text assets, acknowledgment,
and return to the shell.  Preserve clean Escape at every wait boundary.

Acceptance: direct state/lifecycle tests plus staged boss-exit-to-shell visual
review.  Paid-episode death cameras/endings are explicitly out of scope.

### A4. High-score table and entry — TODO 7

Original oracle: `WL_INTER.C::DrawHighScores` and `CheckHighScore`, and
`WL_MENU.C::CP_ViewScores`.

Implement the original seven-entry table, qualification/insertion, name
entry/editing, score and completed-floor display, viewing from the control
panel, and invocation after game over or Episode 1 victory.  Persist scores in
an Agon-side file with a documented versioned format; corrupt or absent files
must fail to the original defaults without threatening MOS/file-system state.

Acceptance: ordering/tie/no-qualification boundaries, name editing, file
round-trip/corruption recovery, game-over and victory integration, and visual
review.

### A5. In-game control panel, pause, and original key flow — TODO 14

Original oracle: `WL_PLAY.C::CheckKeys`, `WL_MENU.C::US_ControlPanel`,
`CP_CheckQuick`, and `CheckPause`.

Replace the temporary gameplay-Escape-to-MOS behavior with the original
in-game control panel and resume/end-game/quit decisions.  Restore Pause and
the original quick-key entry points where the Agon keyboard can represent
them.  Keep an explicit, reliable "Quit to MOS" action and retain the common
mode-restoration/VDPlet-teardown route.  Escape during loading or an
unrecoverable error may still use the global clean-exit path.

Acceptance: deterministic input/state tests, resume without reseed, end-game
to shell, quit to MOS, and Escape from every asynchronous boundary.

Residual audit correction, 2026-11-03: the source's direct F1-F10 routes were
missing even though the in-game panel and Escape flow were present. `CheckKeys`
sends F1 help, F2 save, F3 load, F4 sound, F5 view, and F6 controls directly
into their pages; `CP_CheckQuick` owns F7 end game, remembered-slot F8/F9 quick
save/load, and F10 quit. The production polling path, interrupt-time FabGL
callback path, dispatcher, and remembered-slot lifecycle now implement those
routes. Oryx generation 152 passes 255/255 shell, 492/492 keymap/player-combat,
and 224/224 callback/death checks.

Pause correction, 2026-11-03: FabGL `VK_PAUSE` has no MOS keymap bit, so the
interrupt callback now owns an explicit Pause request and a separately armed
fresh-key acknowledgment. The foreground drains the renderer, stops music,
plots authentic WL1 `PAUSEDPIC` chunk 137 at source coordinates (128,64),
presents it, waits for a new key (including a second callback-only Pause), and
then resumes floor music while rebuilding both gameplay buffers. Oryx
generation 153 passes the expanded 228/228 callback/death checks and both
application backends assemble. These quick keys and Pause are required
behavior, not optional DOS hardware configuration; TODO 14 now retains only
the batched visual/input acceptance gate.

### A6. Save/load game — TODO 15

Original oracle: `WL_MAIN.C::SaveTheGame` / `LoadTheGame` and
`WL_MENU.C::CP_SaveGame` / `CP_LoadGame`.

Implement ten menu-visible slots and a versioned Agon save format containing
all simulation state required for exact continuation: episode/floor/
difficulty, player inventory and score/lives, elapsed time and ratios, mutable
map/pushwall/door/static/actor/RNG state, and the current music selection when
music exists.  Loading must reconstruct VDP state from authoritative eZ80
state, never trust serialized VDP handles, and reject incompatible/truncated
files safely.

Acceptance: round trips during movement/combat/door/pushwall states, all ten
slots, overwrite/cancel, corrupt/version mismatch, and continuation through a
floor transition and death.

### A7. Remaining control-panel pages — TODO 16

Original oracle: the main-menu tables and `CP_Sound`, `CP_ChangeView`,
`CP_Control`, and `HelpScreens` in `WL_MENU.C`.

Complete the original-facing menu surface: Sound, Control, Change View, Read
This/help, View Scores/End Game state, and Back to Game.  Unsupported DOS-era
hardware choices may be translated to honest Agon choices or visibly disabled;
they must not be silently represented as functional.  View-size selection may
use the existing viewport hooks and must preserve renderer geometry.

Acceptance: navigation regression for every row/cancel route and visual review
of each reachable page.

### A8. Attract loop and recorded demos — TODO 17

Original oracle: `WL_MAIN.C::DemoLoop` and `PlayDemo`.

After inactivity, cycle title (15 s), credits (10 s), high scores (10 s), and
the four Episode 1 demos.  Any accepted input opens the control panel, and demo
playback must use deterministic recorded inputs without mutating persistent
game state.

Acceptance: timer/input tests, deterministic demo completion/abort, and a full
visual cycle.

### A9. Music — TODO 6

Original oracle: `WL_PLAY.C::StartMusic`, `WL_MENU.C::StartCPMusic`, the
`MusicGroup` data, and `AUDIOWL1.H` assignments.  Implement the original IMF/
OPL2-derived music assignments for title/menu, all Episode 1 floors,
intermission, victory, and high scores as a subsystem separate from digitized
SFX.  Simultaneous SFX must remain intelligible, simulation must never block
on music, and lifecycle transitions must not leak a previous song.

Acceptance: format/conversion tests, assignment table tests, lifecycle stress,
simultaneous SFX/music hardware review, and clean teardown/relaunch.

### A10. Residual parity sweep — TODO 18

After A1-A9, replay Episode 1 end-to-end and compare every reachable state to
the original source/shareware executable: scoring, one-ups, inventory,
difficulty, actor counts, secrets, transitions, death/game-over, menus,
audio, and ending.  Record any intentional Agon differences.  Close this only
with a source-linked discrepancy ledger and emulator plus hardware acceptance.

Debug cheats, paid-episode content, obsolete DOS copy protection, VGA palette
timing exactness, and unavailable hardware configuration choices are not
required unless separately promoted.

## Phase B: Agon identity and legal presentation

After Phase A, add the reserved Agon splash hook, visible application and
compatible VDPlet/firmware identities, educational/noncommercial disclaimer,
third-party-rights statement, no-rights/no-liability Author statement, and
project credits without delaying or obscuring the original-facing flow.
This is TODO 3b plus TODO 19 in the root ledger.

## Phase C: custom episodes

After branding, replace the five unavailable paid-episode slots with clear
"YOUR EPISODE HERE" entries.  Define a versioned episode manifest, validate
maps/assets before launch, document the durable build/install path, and make a
minimal example episode.  Original Episode 1 remains immutable and selectable.
This is TODO 20.

## Independent platform track

TODO 8, 8e, and 8g retain the VDPlet migration, production contract, and
direct-row physical/default-cutover gates.  They affect deployment and
performance, not the definition of Wolfenstein shareware behavior above.
