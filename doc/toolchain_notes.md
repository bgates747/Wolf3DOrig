# Toolchain Investigation — Compiling the Original WOLFSRC

Dev notes on what it would take to actually compile/modify id's original
Wolfenstein 3D source (`orig/src/WOLFSRC/`) with modern tooling, and
whether sourcing the real period toolchain is a viable alternative. Not
acted on yet — research/options only.

## What we know (grounded facts from `orig/src`)

- `README.rst` (id's own release notes) confirms: **Borland C++ 3.0/3.1**,
  16-bit real-mode DOS target. "This version will compile under BORLAND
  C++ 3.0/3.1 and compiled perfectly before it was uploaded."
- The codebase mixes C with hand-written assembly tied specifically to
  Borland's toolchain, not portable inline asm:
  - `C0.ASM` — this **is Borland's own C runtime startup code** (its
    header literally reads "Turbo C++ Run Time Library, Copyright (c)
    1987, 1991 by Borland International Inc."), not id's code.
  - `H_LDIV.ASM`, `RULES.ASI` — also Borland runtime helper/rules files.
  - `ID_SD_A.ASM`, `ID_US_A.ASM`, `ID_VH_A.ASM`, `ID_VL_A.ASM`,
    `WL_ASM.ASM`, `WL_DR_A.ASM`, `WHACK_A.ASM`, `JABHACK.ASM` — id's own
    hand-written performance-critical routines (sound, input, video,
    rendering), written for TASM/MASM-style Intel syntax against
    Borland's segment/memory-model conventions.
- Original project files are present: `WOLF.IDE` (Borland IDE project),
  `WOLF3D.PRJ` (older Turbo/Borland project format), `WOLF.DSW`
  (workspace), and a prebuilt `OBJ/` directory of object files — plus
  prebuilt `WOLF.EXE`/`WOLF3D.EXE` binaries already sitting in the source
  tree, useful as a reference to diff against if we ever get a rebuild
  working.
- Input handling (`ID_IN.C`, movement/turning in `WL_AGENT.C`/
  `WL_PLAY.C`) is plain C, not assembly — relevant if a future hack (e.g.
  a real controls change in the game's own code, not just a DOSBox
  mapper trick) only needs to touch `.C` files.

## Option A — Open Watcom (open-source, modern, actively maintained)

- **Pros:** free/open-source, no licensing ambiguity; still maintained
  (Open Watcom V2 on GitHub); genuinely supports 16-bit real-mode DOS
  `.exe` targets (large/huge memory models); ships its own integrated
  assembler (WASM) and can work with OMF object files, which is the
  object format this era of tools generally used.
- **Cons / unknowns:**
  - The `.ASM` files are written in TASM/MASM-style syntax tied to
    Borland's own segment/group conventions — porting to WASM's dialect
    is a real translation job, not a drop-in recompile.
  - `C0.ASM` is Borland's proprietary runtime startup. Watcom has its own
    incompatible startup/runtime — this file would need to be **replaced
    outright** with Watcom's equivalent, not ported, which can shift
    memory-layout assumptions the rest of the code may lean on.
  - No Watcom-native build file exists — `WOLF.IDE`/`WOLF3D.PRJ` aren't
    understood by Watcom, so a `wmake`-based build would need to be
    reconstructed from scratch by reading the original project files for
    compiler flags/memory model.
- **Verdict:** plausible, but a real porting project, not a toolchain
  swap. This matches Carmack's own suggested project idea in
  `RELEASE.TXT`: "Convert to a 32 bit compiler... a fair amount of work."

## Option B — DJGPP (GCC targeting 32-bit protected-mode DOS via CWSDPMI)

- **Pros:** modern GCC, free, well-documented, popular in the DOS
  homebrew/retro community for from-scratch DOS projects.
- **Cons:**
  - Targets 32-bit protected mode — a different memory model entirely
    from the 16-bit real-mode huge/large model this code assumes (far
    pointers, segment:offset tricks throughout `WL_DEF.H` and friends).
  - GNU assembler (GAS) is AT&T syntax by default, incompatible with the
    Intel-syntax `.ASM` sources without translation.
  - Effectively the same category of rewrite as Option A, arguably more
    invasive since the whole memory model changes.
- **Verdict:** closer to what actual community source ports (Wolf4SDL,
  ECWolf) did — full modernization/rewrite targeting SDL, not a
  like-for-like recompile of the original DOS binary. Good prior art to
  study, not a shortcut for preserving original binary behavior.

## Option C — Source real Borland C++ 3.x + TASM, run under DOSBox

- **Pros:** byte-for-byte the intended original environment.
  `WOLF.IDE`/`WOLF3D.PRJ` would presumably load and build with **zero**
  porting work. Safest way to confirm that a source-level hack (e.g. a
  real edit to `ID_IN.C` for controls) builds correctly without
  introducing subtle behavior changes from a different toolchain.
- **Cons / open questions:**
  - Not yet researched where to *legitimately* source Borland C++
    3.0/3.1 + Turbo Assembler today. Embarcadero (current rights holder)
    has at times offered older Turbo/Borland compilers for free personal
    use, but whether 3.0/3.1 specifically is covered, and under what
    terms, is unverified.
  - Abandonware sites carry old Borland installers, but their legal
    status is murky — same class of concern already flagged for id's own
    source release in the handoff doc. Old age alone doesn't make
    redistribution clean; shouldn't be treated as automatically fine.
  - **Not yet researched:** whether Embarcadero has an official
    legacy/museum distribution program that covers this exact version.
- **Verdict:** mechanically the cleanest option *if* a legitimate copy
  can be sourced. The open question is licensing/sourcing, not technical
  feasibility — this needs a real answer before pursuing, not a download
  from an unverified site.
- **Lead:** [ ] Ask Mark (old high-school hacker friend, now a
  professional coder/airline pilot) whether he still has his original
  Borland C++ 3.x suite — he's the one who urged the Author to buy their
  own (student-licensed) copy back in the day, and likely has the full
  professional license. Own copy would settle Option C's licensing
  question outright.

## Open items / next research steps

- [ ] Verify whether Embarcadero has any official legacy/museum
      distribution of Borland C++ 3.x we could legitimately use.
- [ ] If pursuing Open Watcom: check whether anyone has already
      documented porting Borland-`C0.ASM`-based DOS projects to Watcom,
      so we're not reinventing that from scratch.
- [ ] Confirm actual scope needed: if a given hack only touches `.C`
      files (e.g. `ID_IN.C` for controls), we may be able to keep the
      prebuilt `OBJ/` object files for the untouched `.ASM` routines and
      only recompile+relink the changed `.C` files — potentially
      sidestepping the ASM-porting problem entirely for many hacks.
- [ ] Read `WOLF.IDE`/`WOLF3D.PRJ` closely for the exact compiler
      flags/memory model in use, needed regardless of which toolchain we
      end up on.
