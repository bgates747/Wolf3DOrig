# Wolf3DOrig shareware-parity audit and completion checklist

Date: 2026-11-03

This is the source-grounded definition of "duplicate the original shareware
behavior" for Wolf3DOrig.  The active, intentionally promoted work remains in
the repository-root `TODO.md`; this document explains why each item is there,
what original code owns the behavior, and what evidence closes it.

The parity target is the original Episode 1 / WL1 shareware game.  Paid
episodes, Spear of Destiny, their actors, projectiles, maps, and endings are
not prerequisites.  Agon branding/legal presentation and custom-episode
authoring follow parity as separate phases.  VDPlet rollout is an independent
platform track and must not be confused with missing game behavior.

The source oracle is specifically the non-SPEAR `WOLF1VER.H` configuration,
which defines `UPLOAD` and selects the `.WL1` archives. Consequently the
registered-build `NonShareware` warning, copy protection, episode-qualified
high-score labels, total-time verification code, and paid-episode digitized
sound table are not missing shareware behavior. Developer-only `goobers`
debugging, demo recording, profiling, and held-M jukebox entry are likewise
outside the ordinary shipped-game contract. This exclusion does **not** cover
the unconditional M+L+I inventory/score/time chord or B+A+T Commander Keen
message in `WL_PLAY.C::CheckKeys`; those are reachable in an ordinary WL1
process and remain parity requirements.

## Audit baseline: behavior already present

The current port already has the following shareware behavior in production,
with direct-eZ80/host regressions and human emulator or hardware acceptance as
recorded in the dated development logs:

- all ten Episode 1 maps, difficulty-filtered object seeds, ordinary and
  secret-floor routing, and the secret-floor return to E1L2;
- fixed-step player movement, collision/sliding, door wells, keyed doors,
  elevators, door motion/auto-close, blocking decorations, and pickups;
- authoritative health, ammo, keys, weapons, score, extra lives, treasure,
  HUD (including the original random three-frame face animation), attempt
  death/respawn, source-correct game-over high-score handoff, and red fizzle;
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

## Exact outstanding Phase-A acceptance gates

Implementation is not reopened merely because a deterministic review profile
still exists. In particular, Hans and the four Episode 1 ghosts are completed,
accepted actor behavior; their profiles are retained only as regression
coverage. Phase A has the following finite remaining gates:

- [ ] A1 / TODO 11: visually accept the real E1L1 pushwall moving two cells,
  changing collision/DDA ownership, and revealing a traversable passage;
  repeat on hardware when practical.
- [ ] A2 / TODO 12: visually accept ordinary and secret-floor count-up,
  skip-to-final, exact bonuses/ratios, and the resulting E1L2 entry.
- [ ] A3 / TODO 13: visually accept the complete E1L9 BJ sequence, totals,
  two-page shareware ending, high-score handoff, and shell return.
- [ ] A4 / TODO 7: visually accept both qualifying name-entry/persistence and
  non-qualifying timeout/dismissal high-score paths.
- [ ] A5 / TODO 14: visually accept Pause continuity plus F1-F10, M+L+I, and
  B+A+T page/backdrop/music ownership; exercise resume, End Game, and clean
  Quit from the same finite batch.
- [ ] A6 / TODO 15: visually accept ten-slot save/load, overwrite/cancel/file
  interaction, remembered F8/F9, and one clean resumed gameplay frame.
- [ ] A7 / TODO 16: visually review every reachable control-panel page and
  navigate representative first/middle/last pages of the 41-page HELP article.
- [ ] A8 / TODO 17: visually cycle all four canonical demos, abort one with
  local input, and verify return to the control panel without persistent-state
  mutation.
- [ ] A9 / TODO 6: audibly review representative shell, floor, intermission,
  victory, and simultaneous-SFX transitions plus both independent toggles;
  hardware is authoritative for timbre/mix/latency.
- [ ] A10 / TODO 18: visually accept sign-on/PG13/title, ordinary death and
  final-attempt game-over paths, then perform the final emulator plus hardware
  discrepancy-ledger review across an ordinary Episode 1 session.

Every automated or source-grounded prerequisite for these gates is recorded
in the sections below. A failed gate promotes only the observed discrepancy;
it does not reopen an already accepted subsystem wholesale.

## Phase A: exact remaining original shareware behavior

Items are ordered by implementation priority, not by cosmetic visibility.

Residual correction, 2026-11-03: the audit found that the renderer accepted a
HUD face-frame byte but the eZ80 serializer always sent zero. The fixed 30 Hz
simulation now implements `WL_AGENT.C::UpdateFace` with an exact 2/2/3 mapping
of the original 70 Hz `tics`, the strict `facecount > US_RndT()` comparison,
the source's second-draw frame selection and 3-to-1 fold, and the same shared
random stream used by gameplay. `gamestate.faceframe` is persisted in the
reserved save scalar tail; PlayLoop-local count/phase state resets per attempt.
Follow-up correction, 2026-11-03: the packaged `GOTGATLINGPIC` art was never
selected. Every chaingun pickup now publishes a dedicated face sentinel and
freezes ordinary face evolution for the generated 14 fixed ticks covering the
actual 454 ms resident `GETGATLINGSND` sample. The special presentation is
cancelled immediately by damage or successful healing and is deliberately not
save-persistent, matching the source's PlayLoop-local `gotgatgun`. Oryx
generation 159 passes 528 player-combat/face checks, 32 pickup cases, and the
byte-exact full/dirty serializer; the four-scenario production renderer is
pixel-identical to its standalone oracle.

Palette correction, 2026-11-03: `WL_PLAY.C`'s transient damage-red and
pickup-white palette shifts were absent. The eZ80 now preserves the source
damage and bonus counters, red priority, six/three level selection, and exact
2,2,3 conversion from 30 Hz quanta to 70 Hz source tics. Reserved HUD byte 11
now carries the transient level without a schema break. The VDPlet applies the
original 6-bit component formulas to RGB222 through a 64-entry per-frame
lookup while preserving direct-row sync bits; this is the closest exact
representation after the source palette has already been quantized. The same
end-to-end audit corrected the module validator, which still rejected the
already-published face sentinel 3. Oryx generation 160 passes 549
player-combat/palette checks, 32 pickup cases, and byte-exact serialization;
six renderer scenarios remain pixel-identical to the standalone oracle.

Death-transition correction, 2026-11-03: the baseline's red-fizzle claim was
true only for the standalone firmware. The production VDPlet entries remained
an unsupported stub even though the root TODO described them as integrated.
Release 1.2.0 now reproduces the original 17-bit LFSR order over the centered
256x160 viewport in 60 application-paced visible slices, then synchronizes the
other physical surface with one unpresented final step. HUD and surround pixels
remain untouched, only one requested RUN may be active, and Escape stops new
work after the in-flight slice completes. Host exact-retry/error coverage and
the finite Oryx generation-161 ABI 1.6 gate pass five whole-frame oracle
checkpoints, final surface synchronization, RESET/unload/reload, and empty-slot
teardown with INFO17 unchanged at 2,136 free bytes.

Actor-phase correction, 2026-11-03: `WL_GAME.C::SetupGameLevel` calls
`US_InitRndT(false)` only for demo playback/recording and seeds from system
time for ordinary play. The port's packages correctly baked the deterministic
seed-zero spawn phases, but production reused those phases for every normal
level entry and death restart. Production now seeds ordinary play from the MOS
clock and reproduces `SpawnNewObj`'s timed-state draws in row-major live-list
order; zero-duration states consume no draw. The four original demos retain
the package path exactly, and the shared post-spawn RNG position remains part
of the authoritative saved simulation state. Oryx generation 171 passes all
618 direct eZ80 checks. The measured real-E1L1 patrol route remains 0.217 ms
per fixed frame because this correction runs only during attempt seeding.

Quit-flow correction, 2026-11-03: `WL_MENU.C::CP_Quit` does not immediately
terminate. It selects one of nine original prompts using two shared `US_RndT`
draws and the exact source expression `first & (7 + (second & 1))`, then exits
only for Y/y. N/n or Escape cancels with `ESCPRESSEDSND`; acceptance uses
`SHOOTSND`. Main-menu Escape and Quit, the in-game Quit row, and F10 now share
that contract. F10 preserves the source's temporary `WindowH=160` placement by
moving the composed prompt twenty pixels upward. The same audit corrected the
startup RNG seed and the main-menu Episode cancellation path, which returns
locally rather than setting the application exit latch. The follow-up audit
restores Difficulty cancellation to Episode selection, matching `firstpart`.
Oryx generation 172 passes all 559 direct production-shell checks, and the
nine composed prompt assets pass their exact source-string/geometry contract.

New-game-flow correction, 2026-11-03: the in-game control panel now preserves
`CP_NewGame`'s warning that the current game will be erased. The exact
three-line `CURGAME` message is composed from the original WL1 font and window
geometry; N/n or Escape returns to the running game's control panel, while
Y/y proceeds to difficulty selection. Cancelling Difficulty follows the
source's `firstpart` jump back through Episode selection and asks the warning
again after the next valid episode choice. The startup shell deliberately
omits the warning because no game is in progress. F7's temporary
`WindowH=160` confirmation placement is separately pinned. Oryx generation
175 passes all 581 direct production-shell checks, including the complete
accept, cancel, nested-cancel, and prompt-coordinate traces.

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

Status 2026-11-03: implementation passes 135 direct intermission checks and
the expanded 32-case pickup/score regression. The stopped ordinary-transition
profile awaits human count-up/skip/next-floor review; the secret presentation
will be batched with it.

Audio correction, 2026-11-03: the state machine emitted all five original
intermission sound IDs, but their non-digitized source effects were still
marked unavailable. The durable audio builder now decodes the authentic
140 Hz PC-speaker pitch streams for `LEVELDONE`, `ENDBONUS1`, `ENDBONUS2`,
`NOBONUS`, and `PERCENT100`, renders them drift-free to 7 kHz resident PCM,
and plays them through the unchanged buffered runtime path. Oryx generation
154 passes 287/287 audio and 135/135 intermission target checks. Audible
acceptance remains part of the staged presentation gate.

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

Status 2026-11-03: implementation is complete. The BJ run/jump state graph,
E1L9 exit, total-time/eight-floor averages, shareware ending, high-score
handoff, and shell return pass the 5/5 direct victory target. The only open
gate is staged visual acceptance of the complete E1L9 sequence.

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

Status 2026-11-03: implementation is complete. The seven-row table, ordering,
name editor, timed non-qualifying path, game-over/victory handoffs, and
transactional 482-byte persistence image pass 62/62 direct checks. The only
open gate is visual acceptance of qualifying and non-qualifying flows.

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
fresh-key acknowledgment. The foreground drains the renderer, freezes the IMF
cursor and scheduler epoch, plots authentic WL1 `PAUSEDPIC` chunk 137 at
source coordinates (128,64), presents it, and waits for a new key (including a
second callback-only Pause). Resume removes the wall-clock gap without
rewinding the stream. Matching `ID_SD.C::SD_MusicOff`, all OPL key-on shadow
bytes are cleared; a note held across Pause therefore remains silent until a
later IMF key edge rather than being spuriously re-keyed. Both gameplay
buffers are rebuilt authoritatively. Oryx generation 153 passes the expanded
228/228 callback/death checks and both application backends assemble. These
quick keys and Pause are required behavior, not optional DOS hardware
configuration; TODO 14 now retains only the batched visual/input acceptance
gate.

Quick-overlay correction, 2026-11-03: the source copies the stopped play screen
before F7-F10 and the ordinary M+L+I/B+A+T message boxes. Production now
captures the complete VDP 2.6+ RGBA2222 gameplay surface before entering MODE
8, replots it behind those overlays, and releases the transient buffer on every
return/error path. F1-F6 and Escape retain the full control-panel surface and
WONDERIN; F7, remembered F8, F10, M+L+I, and B+A+T preserve floor music; F9
restarts it after the quick-load confirmation. First-use F8/F9 promote to the
full Save/Load page and menu music. The open gate remains the same finite
visual/input batch.

Status 2026-11-03: the latest production shell passes 595/595 checks, the
physical-keymap/player-combat target passes 492/492, and callback/death passes
228/228. The open acceptance gate is one visual/input pass through Pause,
pages, save/load, End Game, and Quit. Remembered-slot F8/F9 now reproduce the
original transient `Saving...` and named-load surfaces; Oryx generation 177
passes 595/595 shell checks.

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

Status 2026-11-03: implementation is complete and all ten transactional
direct-target cases pass. The round-trip case now seeds active combat timing,
a moving door and timer, a mutable static, a fractional pushwall with history,
floor ratios and secrets, and the death score checkpoint. It clears live state,
decodes, rebuilds derived state, re-encodes, and requires the complete image to
be byte-identical. Oryx generation 195 passes, so the remaining human gate is
narrowly the ten-slot menu, overwrite/cancel/file flow, and one visibly clean
resumed gameplay frame rather than separate saves in every dynamic state.

### A7. Remaining control-panel pages — TODO 16

Original oracle: the main-menu tables and `CP_Sound`, `CP_ChangeView`,
`CP_Control`, and `HelpScreens` in `WL_MENU.C`, plus `ShowArticle` and the
page-layout command language in `WL_TEXT.C` and VGAGRAPH chunk 150.

Complete the original-facing menu surface: Sound, Control, Change View, Read
This/help, View Scores/End Game state, and Back to Game.  Unsupported DOS-era
hardware choices may be translated to honest Agon choices or visibly disabled;
they must not be silently represented as functional.  View-size selection may
use the existing viewport hooks and must preserve renderer geometry.

Acceptance: navigation regression for every row/cancel route and visual review
of each reachable page.

Status 2026-11-03: the exact ten-row order, startup/in-game substitutions,
local cancellation, Sound, Control, fixed-view disclosure, View Scores/End
Game, and Back to Game are implemented. The audit rejected the former concise
Read This substitute: a literal offline translation of `WL_TEXT.C` now renders
all 41 original HELP pages from archive chunk 150, including its frame,
embedded pictures, proportional layout, colors, and page numbers. Production
loads the reproducible 2.6 MiB `help.agnb` only on selection, preserves the
original arrow/Page Up/Page Down/Enter/Escape behavior and CORNER music, and
clears all 41 page buffers on success, abort, or failure. Host asset contracts
pass, both application backends assemble, and Oryx generation 185 passes all
683 direct production-shell checks. Remaining gate: visual review of article
navigation and every reachable panel page.

### A8. Attract loop and recorded demos — TODO 17

Original oracle: `WL_MAIN.C::DemoLoop` and `PlayDemo`.

After inactivity, cycle title (15 s), credits (10 s), high scores (10 s), and
the four Episode 1 demos.  Any accepted input opens the control panel, and demo
playback must use deterministic recorded inputs without mutating persistent
game state.

Acceptance: timer/input tests, deterministic demo completion/abort, and a full
visual cycle.

Status 2026-11-03: implementation is complete. Archive extraction and stream
identity are deterministic; the direct demo state target passes 21/21 and the
analog/cadence target passes 48/48. The remaining gate is a visual cycle
through all four demos plus local input abort and control-panel return.

### A9. Music — TODO 6

Original oracle: `WL_PLAY.C::StartMusic`, `WL_MENU.C::StartCPMusic`, the
`MusicGroup` data, and `AUDIOWL1.H` assignments.  Implement the original IMF/
OPL2-derived music assignments for title/menu, all Episode 1 floors,
intermission, victory, and high scores as a subsystem separate from digitized
SFX.  Simultaneous SFX must remain intelligible, simulation must never block
on music, and lifecycle transitions must not leak a previous song.

Acceptance: format/conversion tests, assignment table tests, lifecycle stress,
simultaneous SFX/music hardware review, and clean teardown/relaunch.

Status 2026-11-03: implementation is complete. The nonblocking nine-voice
sequencer and every Episode 1 assignment have direct target coverage;
integrated shell lifecycle, source-correct Pause continuity, quick-key music
ownership, and independent preference coverage are green. The remaining gate
is audible emulator/hardware review of timbre, mix, transitions, and both
toggles. OPL2 timbre is intentionally approximated by native oscillators and
is not an unfinished exact-emulation requirement.

### A10. Residual parity sweep — TODO 18

After A1-A9, replay Episode 1 end-to-end and compare every reachable state to
the original source/shareware executable: scoring, one-ups, inventory,
difficulty, actor counts, secrets, transitions, death/game-over, menus,
audio, and ending.  Record any intentional Agon differences.  Close this only
with a source-linked discrepancy ledger and emulator plus hardware acceptance.

Residual correction, 2026-11-03: `WL_AGENT.C::GiveExtraMan` plays
`BONUS1UPSND` for every award, even when the nine-life cap suppresses the life
increment. Production now does the same for score thresholds and full heal;
the latter has one sound owner so Agon's accepted simultaneous-stream behavior
does not turn the source's effectively monophonic duplicate calls into two
audible samples. Oryx generation 163 passes all 33 direct target records.

Use correction, 2026-11-03: original `Cmd_Use` requests `DONOTHINGSND` when
the facing tile is not an operable pushwall, elevator face, or door. Production
now emits one request per rising edge for those no-action paths, while retaining
the distinct `NOWAYSND` for locks and blocked pushwalls. Logical sound 20 is
the authentic AUDIOT PC-speaker stream rendered offline to 7 kHz PCM. Oryx
generation 164 passes 29/29 direct use/pushwall cases and generation 165 passes
all 287 production-audio checks.

Control-panel audio correction, 2026-11-03: the shell precis correctly listed
the original `HandleMenu` feedback but the implementation and frozen parity
ledger still treated the first shell as intentionally silent. Production now
plays authentic `MOVEGUN1SND`/`MOVEGUN2SND` around the original eight-tic
cursor half-step, `SHOOTSND` on accept, `ESCPRESSEDSND` on cancel, and the
additional `NOWAYSND` after selecting an unavailable paid episode. The four
new effects are rendered offline from their original 140 Hz AUDIOT PC-speaker
streams. The 454,944-byte AGNB container contains 49 records and 452,701 bytes
of resident PCM. It is loaded once beside the application-global shell assets;
session stop resets all three channels while preserving availability, whereas
final shutdown additionally clears it. The final shell proof, including the
SFX-off then SFX-on edge, passes 526/526 checks on Oryx generation 168;
generation 167 passes 306/306 audio/lifecycle checks.
The shell receipt was upgraded from an overflowing one-byte `W3S1` counter to
the 16-bit `W3S2` schema during that proof.

Movement-audio correction, 2026-11-03: `WL_AGENT.C::ClipMove` requests
`HITWALLSND` after the complete X/Y probe fails, before attempting X-only and
Y-only slides. Production had the correct geometry but no sound producer.
Logical sound 0 is now the authentic 57 ms AUDIOT PC-speaker stream at 7 kHz.
A generated two-quantum guard reproduces its no-retrigger intent without
letting an unrelated effect suppress it on Agon's multichannel backend. The
455,388-byte AGNB container now holds 50 records and 453,101 resident PCM
bytes. Oryx generation 169 passes 10,030 production ClipMove records,
including the request edge and cooldown expiry, and both application backends
assemble.

Config-persistence correction, 2026-11-03: `WL_MAIN.C::ReadConfig` and
`WriteConfig` persist sound/music modes across process launches. The translated
Sound page was only process-persistent. Production now uses a narrow 16-byte
Agon config for SFX and music: versioned header/footer, exact-length admission,
Fletcher-16, transactional publication, and safe on/on fallback. DOS device
selection, custom key bindings, mouse sensitivity, and view size remain
unavailable/fixed rather than being encoded as fictitious choices. Oryx
generation 170 passes 30/30 direct eZ80 checks, including all flag combinations
and real MOS save/load plus corruption, truncation, and trailing-data rejection.

Shipped-key-chord correction, 2026-11-03: the residual audit separated two
ordinary `WL_PLAY.C::CheckKeys` chords from the command-line-gated `goobers`
debug block. M+L+I now grants health 100, ammo 99, both keys, chaingun, zero
score, and the source's exact ten-minute level-time penalty before presenting
the original cheater message. B+A+T presents the original Commander Keen
message without changing player state. Both use their physical MOS key-map
locations, require a fresh modal acknowledgment, and remain disabled during
recorded-demo playback just as the source's early return requires. Oryx
generation 198 passes 578/578 direct player/input checks and 699/699 direct
shell checks. The fixture mailbox now records the first failing assertion and
logical subcase, after that instrumentation identified and eliminated a
demo-mode leak between otherwise independent test cases.

Quit-confirmation correction, 2026-11-03: the otherwise functional control
panel bypassed original `CP_Quit` and returned directly to MOS. The complete
nine-message source table is now generated as reusable shell assets, selection
consumes the same two gameplay RNG draws with exact C precedence, and all four
reachable entry routes share Y/N/Escape and sound semantics. Main-menu Episode
Escape is a local cancellation again; the follow-up audit restores Difficulty
Escape to Episode selection. Oryx generation 172
passes 559/559 target checks; standalone is 273,505 bytes, SHA-256
`872aae9c708eddd93fa8f60662035dfaa23127653d36d459c0022c2a6452ba9f`,
and VDPlet-direct is 285,125 bytes, SHA-256
`a2d0b9efdbc3b5c59933ea3f1ab4c06cbff1b8b3baa41c161631daecc571e7e6`,
against the unchanged 18,636-byte module
`266f809ff76e56733251da202e5c4747cd9c12d247d799d486471a262c0404b7`.

Intentional discrepancy ledger, 2026-11-03: the hardware-accepted player
wall/slab radius and actor/static physical clearance remain `0x4800`, versus
the source's `PLAYERSIZE`/`MINDIST` value `0x5800`. The independent original
`0x5800` actor guard for starting a fully-open door close remains intact. The
strict gun targeting cone remains the hardware-accepted 16 projected pixels,
versus the source's 25 pixels at the fixed 256-pixel viewport. These are
deliberate feel corrections with directed boundary regressions, not unfinished
shareware-parity work.

Quick-key presentation correction, 2026-11-03: remembered-slot F8 now plots
the exact original-font `Message("Saving...")` before writing. F9 no longer
redraws the ten-slot page with a generic prompt: it presents the source
`Load Game called` wording and the actual mutable slot name in a source-styled
outlined window over the drained gameplay frame. Mutable names deliberately
use the same Agon text renderer as the full slot page. First-use fallback,
slot identity, I/O, sound, and accept/cancel behavior are unchanged. Oryx
generation 177 passes all 595 direct shell checks.

Actor-visibility correction, 2026-11-03: the write-only renderer split could
leave a previously rendered `ACTIVE_NO` actor dependent on current area
connectivity, allowing it to sleep again after a door disconnected the area.
Production now scans dormant actors only at actual render-submission
boundaries. A valid connected actor with a drawable state is permanently
promoted after its physical center passes the existing player-facing CPU
projection and an unobstructed `CheckLine`. Noise and actor-facing
`CheckSight` are deliberately excluded because either can detect behind the
player and create a false permanent wake-up. Oryx generation 178 passes
624/624 direct-eZ80 checks covering promotion, persistence, behind-player,
wall, and disconnected-area rejection. A deliberately pessimistic 1,000-pass
PRT1 benchmark measured 158 ms total, or 0.158 ms for one complete visible
promotion at a render boundary. Both production backends rebuild.

Closed actor-visibility discrepancy, 2026-11-03:

1. `WL_DRAW.C::DrawScaleds` also accepts an actor when one of its eight
   neighboring tiles is both open and renderer-visible. DOS obtains that fact
   from the per-column raycaster's `spotvis`; the write-only port has no such
   feedback. Production now reconstructs that predicate on the eZ80: after a
   failed center test, it bounds the actor's cached tile, ignores occupied
   neighbors, and requires both player-facing projection and the authoritative
   wall/door trace for each of the eight candidate tile centers. The order is
   adaptive so projected-but-occluded centers trace first while off-screen
   centers project first. Oryx generation 191 passes 629/629 direct checks;
   1,000 fully occluded scans take 533 ms and 1,000 line-clear behind-player
   scans take 421 ms. This closes the prior corner-peek activation difference.

Startup correction, 2026-11-03: the application shell skipped the original
one-time `WL_INTER.C::PG13` presentation even though its archive art was
already inventoried. `PG13PIC` is now admitted as raw shell asset 100, plotted
at the source `(216,110)` anchor over the RGB222 equivalent of VGA index
`0x82`, and held for seven seconds or one fresh dismissing key before the
title. The page runs only on initial process entry, not after demos or gameplay
return, matching `DemoLoop` ownership. Exact VGA fade timing is intentionally
not emulated.

Follow-up startup correction, 2026-11-03: the earlier audit still began one
screen too late. `WL_MAIN.C::SignonScreen/FinishSignon` first presents the
320x200 `introscn` linked into `SIGNON.OBJ`, waits for a fresh local key, then
starts `INTROSONG` before PG13 and carries that same track into the title.
Production now extracts the object's exact gapless 64,000-byte LEDATA segment
with a bounded OMF parser, composes the source `Press a key` state, and retains
the same local-key/music handoff. DOS heap bars and ISA-device checkboxes stay
at their linked defaults because they have no truthful Agon analogue; the
transient `Working...` text is omitted because Agon assets have already loaded
before the shell starts. The raw segment and rendered presentation identities,
malformed-OMF rejection, both application backends, and the direct startup
fixture are pinned; Oryx generation 185 passes the complete 683-check direct
production-shell target. A staged visual sign-on/PG13/title review remains part
of the next human shell batch.

Additional intentional platform substitutions, 2026-11-03:

2. The accepted keyboard contract is W/S forward/back, A/D strafe, arrow keys
   turn, Up use, Space fire, and 1-4 weapon selection. DOS Shift-run,
   Alt-strafe, mouse, joystick, configurable scan codes, and variable movement
   rates are not exposed as fictitious settings. This is the project's
   deliberate modern Agon control surface, not unfinished source behavior.
3. Source calls to `VW_FadeIn`, `VW_FadeOut`, `MenuFadeIn`, and `MenuFadeOut`
   are represented by immediate page changes. Exact VGA palette-ramp timing is
   an accepted presentation difference; page content, ownership, input, and
   lifecycle transitions remain parity requirements.
4. `WL_INTER.C::PreloadGraphics`'s modal `GETPSYCHEDPIC` bar is replaced by the
   Author-requested text breadcrumbs around modern AGNB container loads. Each
   breadcrumb advances only after a complete bitmap is finalized, failures
   remain visible, and Escape retains the common abort path. The original
   hidden cache-fill progress bar and artificial 70-tic hold are not emulated.
5. The shareware DOS `ORDERSCREEN` shown by `Quit(NULL)` is replaced, by prior
   Author decision, with restored caller video mode and a plain-text
   `Thanks for playing Wolf3DOrig!` line above the live MOS prompt. Phase B
   adds Agon identity/legal presentation; it does not silently revive the DOS
   order form.
6. Original 320x200 shell pages are plotted unscaled in Agon's 320x240 mode;
   the spare forty rows carry the visible application version or cleared shell
   background. Gameplay retains the accepted centered 256x160 viewport and
   original 320x40 HUD at y=200.
7. Pickups use authoritative player/static overlap after successful movement
   rather than DOS `spotvis` renderer visibility. This makes collection
   independent of VDP cadence and avoids read-back while preserving refusal,
   scoring, inventory, sound, flash, removal, and respawn behavior.
8. The accepted player/static/actor clearance is `0x4800` instead of the
   source `0x5800`, the target cone is 16 projected pixels instead of 25, and
   door collision follows the rendered sliding slab rather than treating the
   whole tile as solid. These hardware-tested feel corrections retain directed
   boundary regressions and are not unfinished parity work.
9. The common source tree calls `YEAHSND` at BJ's victory yell action, but the
   shareware `AUDIOWL1.H` enum and WL1 audio corpus do not define that sound;
   it exists only in the registered WL6 header/data. The action edge therefore
   remains a successful no-op rather than borrowing a paid-data effect or
   substituting an unrelated sound.

Death-lifecycle acceptance support, 2026-11-03: the durable acceptance cohort
now includes two copied E1L1 applications at the canonical starting pose. Both
begin with one health point; one begins with one displayed life to exercise a
normal death, fizzle, score rollback and fresh attempt, while the other begins
with zero displayed lives to exercise the source's final playable attempt,
game-over high-score handoff and control-panel return. Compile-time selectors
change only those disposable applications and are absent from production.
This closes the reachability problem, not the still-pending human visual gate.

Audio-inventory correction, 2026-11-03: production already requested Hans's
native `GUTENTAGSND`, `BOSSFIRESND`, and `MUTTISND`, and their VSWAP records
made them audible, but the generated catalog incorrectly classified all three
as surplus rather than current producers. The corrected source-to-producer
contract marks 49 effects required and 49 available; only the alternate
UPLOAD guard `DEATHSCREAM3SND` remains native but intentionally unrequested.
This changes requirement metadata, not PCM, buffer IDs, rates, priorities, or
playback behavior.

Command-line-gated `goobers` debug keys, paid-episode content, obsolete DOS
copy protection, VGA palette timing exactness, and unavailable hardware
configuration choices are not required unless separately promoted. The
ordinary shipped M+L+I and B+A+T chords are explicitly not part of that debug
exclusion.

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
