# Wolf3DOrig application-shell précis

## Purpose and proposed first slice

TODO 3 should precede level completion. It establishes the application
lifecycle into which a completed level, a dead game, or an aborted game will
eventually return.

The first implementation should be intentionally smaller than the original
control panel:

1. Retain a hook for a future Agon-specific splash, but currently begin on the
   original title screen carrying the Wolf3DOrig application version.
2. Enter a main menu with **New Game** and **Quit**.
3. Reproduce the original shareware episode menu: Episode 1 is selectable and
   Episodes 2-6 remain visibly disabled. Then offer the original four
   difficulty levels.
4. Start the existing level-00 game using the selected difficulty.
5. For now, make Escape during play exit the application cleanly rather than
   returning to the menu. Restore the caller's original video mode first,
   print a plain-text thanks-for-playing message terminated by a line feed so
   the MOS prompt appears beneath it, and return to MOS. Menu **Quit** uses the
   same exit path.

This preserves room for later **High Scores**, **Sound**, **Controls**,
**Load Game**, **Save Game**, **Change View**, **Read This**, and the original
attract/demo loop without making them prerequisites for a usable shell.

## Original lifecycle

The authoritative source paths for this review are:

- `orig/src/WOLFSRC/WL_MAIN.C`: startup, sign-on, PG-13 screen, attract loop,
  new-game state, and entry into `GameLoop`;
- `orig/src/WOLFSRC/WL_MENU.C` and `WL_MENU.H`: control panel, menu drawing,
  selection handling, new episode, difficulty, confirmation, and menu audio;
- `orig/src/WOLFSRC/WL_INTER.C`: high scores and intermission screens;
- `orig/src/WOLFSRC/GFXE_WL1.H`, `GFXV_WL1.H`, and `AUDIOWL1.H`: generated
  historical asset identifiers;
- `orig/data/VGADICT.WL1`, `VGAHEAD.WL1`, `VGAGRAPH.WL1`, `AUDIOHED.WL1`,
  `AUDIOT.WL1`, and `VSWAP.WL1`: the actual bundled v1.4 shareware data.

The DOS program first displays an executable-linked sign-on image, offers a
PG-13 screen, and then enters an attract loop: title for 15 seconds, credits
for 10 seconds, high scores for 10 seconds, and one of four recorded demos.
Any input enters `US_ControlPanel`. Starting or loading a game calls
`GameLoop`; returning from it resumes intro music and the attract loop.

For the Agon port, a static title leading to the main menu is the useful core.
The timed attract loop and recorded demos are independent presentation work.

## Graphics inventory

### Opening and attract-loop art

- **Sign-on screen:** `introscn`, a 320x200 image linked into the original DOS
  executable rather than stored as an ordinary `VGAGRAPH` picture. It is not
  required for the first shell and is awkward to treat as canonical data.
- **PG-13 notice:** `PG13PIC`, drawn over a solid background.
- **Title:** `TITLEPIC`, a complete 320x200 screen.
- **Credits:** `CREDITSPIC`, a complete 320x200 screen.
- **High-score heading:** `HIGHSCORESPIC`, combined with small heading art and
  a font by `DrawHighScores`.
- The shareware order/purchase screens and help/read-this art are outside the
  first shell.

In the bundled v1.4 archive, the tested picture sequence around the shell is:

| Chunk | Dimensions | Role |
|---:|---:|---|
| 98 | 320x40 | status bar, already staged by the HUD pipeline |
| 99 | 320x200 | title screen |
| 100 | 88x64 | PG-13 picture |
| 101 | 320x200 | credits screen |
| 102 | 224x56 | high-score heading |

These values were read from the archive's decoded `STRUCTPIC` table and
cross-checked against each chunk's expanded byte count.

### Main-menu and new-game art

The original control panel composes screens from a background plus reusable
pieces rather than requiring a unique full-screen bitmap for every state.
Relevant named pictures are:

- `C_OPTIONSPIC`: OPTIONS heading;
- `C_CURSOR1PIC`, `C_CURSOR2PIC`: animated menu-gun cursor;
- `C_MOUSELBACKPIC`: mouse/back legend;
- `C_EPISODE1PIC` through `C_EPISODE6PIC`: episode illustrations;
- `C_BABYMODEPIC`, `C_EASYPIC`, `C_NORMALPIC`, `C_HARDPIC`: four difficulty
  portraits;
- `C_HOWTOUGHPIC`: difficulty prompt;
- `C_MRETGAMEPIC`, `C_MENDGAMEPIC`, `C_MRETDEMOPIC`, and `C_MSCORESPIC` in
  versions of the data that provide replacement menu labels;
- font chunk 1 for ordinary printed menu text, with font chunk 2 used by some
  control-panel paths;
- screen/backdrop resources used by `S_OPTIONSPIC`, `S_EPISODEPIC`, and
  `S_SKILLPIC`, or an equivalent backdrop reconstructed using the original
  border colors and drawing primitives.

Only episode 1 is present in the shareware game data. Preserve the original
shareware episode menu exactly for now: Episode 1 is active and Episodes 2-6
are shown disabled. Future custom maps may replace this episode presentation.

### Important catalog warning

The historical `GFXE_WL1.H`/`GFXV_WL1.H` files do **not** number every picture
the same way as the bundled v1.4 `VGAGRAPH.WL1`. For example, the actual
archive's status bar is chunk 98, while historical headers assign other values
to `STATUSBARPIC`. The current HUD builder correctly uses the data-driven
v1.4 mapping.

The shell must extend `formats/vgagraph.py` with a tested v1.4 shell catalog
and dimension assertions. It must not import the old header values verbatim.
Generated manifests should retain both semantic names and actual chunk IDs so
the mapping remains auditable.

## Sound and music inventory

The menu uses only a small subset of the logical sound catalog:

- `MOVEGUN1SND`: move the selection cursor;
- `MOVEGUN2SND`: secondary cursor movement/erase path;
- `SHOOTSND`: accept/confirm;
- `ESCPRESSEDSND`: cancel/back;
- `NOWAYSND`: unavailable selection or refused action;
- `HITWALLSND` and `SHOOTDOORSND`: control-customization feedback, not needed
  by the first shell.

Of these, only `NOWAYSND` is currently built, using the accepted explicit
fallback. The generated manifest records the other six as unavailable and
outside current scope: the shareware VSWAP digitized-sound map does not provide
them, and the current builder does not synthesize the original PC-speaker or
AdLib forms. The first shell can therefore be silent, reuse a restrained
existing click, or add explicit fallbacks; implementing old-device synthesis
is not a prerequisite. No new playback mechanism is required: any selected UI
effects can use the accepted buffered path non-spatially at fixed gain.

Original music assignments are:

- `NAZI_NOR_MUS`: intro/title sequence (`INTROSONG`);
- `WONDERIN_MUS`: control panel (`MENUSONG`);
- `ROSTER_MUS`: high-score screen;
- `CORNER_MUS`: temporary episode-selection cue in one path.

Music remains TODO 6. The shell must work silently except for sound effects;
its state machine should expose enter/leave hooks so music can be attached
later without restructuring it.

## Agon-side architecture

The current program performs asset loading and immediately enters gameplay.
It already captures the caller's video mode, forces mode 8 double buffering,
and restores the caller's base single-buffered mode on exit. That lifecycle
should be retained but moved around an explicit top-level state machine:

```text
startup -> optional Agon splash hook -> original title -> main menu
                                                      |          |
                                                      |          +-> quit
                                                      +-> input      |
                                                             clean exit

main menu -> new game -> episode -> difficulty -> load gameplay assets
          -> gameplay -> Escape -> clean exit

clean exit -> restore original mode -> print farewell + LF -> MOS
```

Recommended implementation boundaries:

- `wolf3d_shell.inc`: top-level state machine and transitions;
- `wolf3d_menu.inc`: faithful original control-panel rendering, input repeat,
  and selection;
- generated `shell.agnb` plus `wolf3d_shell_assets.inc`: shell graphics only;
- durable `build_shell_assets.py`: v1.4 extraction, conversion, override
  selection, manifest generation, and AGNB packing;
- `agonport/assets/overrides/wolf3d/shell/`: optional hand-edited originals,
  following the existing HUD/wall/sprite override convention.

Shell assets should load once at startup. Level-specific wall and sprite
containers should remain separate so TODO 2 can replace them between levels.
The HUD and SFX containers are also global and need not be reloaded.

The first shell should use the existing 320x240 mode. Original 320x200 screens
fit exactly above the 40-pixel status-panel region, but the shell does not need
the gameplay HUD; the remaining 40 pixels can be filled with a deliberate
border/background color rather than vertically stretching original art.

## State that must survive the shell boundary

Even before save games exist, the shell/game contract should explicitly carry:

- selected episode (episode 0 is the only currently available value);
- selected difficulty, preserving all four original choices;
- application version string;
- whether a playable game is active;
- caller video mode for final return to MOS;
- later: score/high-score table, save slots, audio preferences, and controls.

Difficulty must not be cosmetic. The current actor setup and combat constants
need a single selected-difficulty input so later level loading can apply the
original thing-plane difficulty filters and combat behavior consistently.

## Recommended implementation phases

1. Add a tested shell-asset extractor and inspect the generated title/menu/
   episode/difficulty images in the existing tkinter viewer.
2. Add title and main-menu states with New Game and Quit.
3. Add episode and difficulty selection; feed difficulty into game startup.
4. Route gameplay Escape and menu Quit through one clean exit path: restore the
   caller's original video mode, print the plain-text thanks-for-playing line
   with a terminating line feed, and return to MOS.
5. Human-validate the emulator lifecycle before committing emulator-coupled
   changes.
6. Defer high scores, save/load, settings, help, demos, and music into their
   appropriate TODOs rather than expanding TODO 3 silently.

## Settled shell decisions

1. Leave an explicit hook for a future Agon-specific splash, but jump directly
   to the original title screen for now.
2. Preserve the original control-panel appearance rather than introducing an
   Agon-native menu design.
3. Escape during gameplay exits cleanly for now. After restoring the original
   video mode, print a plain-text thanks-for-playing message with a line feed
   so the MOS prompt appears on the following line.
4. Preserve the original shareware episode menu exactly: Episode 1 is active
   and Episodes 2-6 are disabled. Custom maps may eventually replace them.
