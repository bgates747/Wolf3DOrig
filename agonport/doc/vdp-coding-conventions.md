# VDP style guide and coding conventions (working notes)

Companion to [devlog_20260730.md](devlog_20260730.md). This is a dedicated,
running collection of `agon-vdp` community standards and conventions,
gathered as evidence so a future Wolf3D VDP extension has a reasonable
chance of fitting in well with how things are already done in that codebase
(see devlog item 19). It is deliberately separate from the devlog so it can
grow into a real reference doc rather than staying buried in a
chronological log.

Like the devlog, numbering here is durable: entries keep their number even
if others are added, removed, or reordered above/below them.

## Status

Just started (devlog item 19/T7 in progress). Nothing below should be taken
as complete or authoritative yet — it's what's been confirmed so far, not a
finished style guide.

## Confirmed facts

- **1.** No `CONTRIBUTING.md`, style guide, or `.clang-format` exists
  anywhere in the `agon-vdp` repo (checked to depth 2 at minimum;
  devlog item 2). Whatever conventions exist are unwritten and must be
  mined from commits and review comments, not read off a document.
- **2.** `video/` is overwhelmingly one person's code (Steve Sims,
  "ss7"/"sims" — an estimated 90%+ of that directory per the Author;
  devlog item 19). His commits are therefore the primary convention
  source, not a sample among many equally-weighted contributors.
- **2a.** Convention-fit isn't Steve's only bar. He's also weighed
  additions by whether they're likely to see broad use versus serving one
  person's niche project — a real constraint given how tight the Agon's
  memory budget already is (devlog item 26), not just a style preference.
  Worth keeping in mind alongside convention-mining, not just after it.
- **3.** Jeroen Venema ("evenomater") is a second prominent contributor
  worth checking specifically, alongside Steve's commits (devlog item 19).
- **4.** Buffered-command macro naming follows a flat, verbose,
  `BUFFERED_<VERB>[_<QUALIFIER>]` pattern in `video/agon.h` (e.g.
  `BUFFERED_SPLIT_BY_FROM`, `BUFFERED_COPY_AND_CONSOLIDATE`) — descriptive
  over terse, no abbreviation of the verb itself.
- **5.** New large subsystems (Pingo being the only real precedent so far)
  are integrated by claiming exactly one top-level buffered opcode and
  multiplexing everything else as subcommands underneath it, rather than
  spreading across many top-level opcodes (devlog item 4).
- **6.** tomm8086 is another project standout worth mining: owner/
  maintainer of `fab-agon-emulator` and its `fab-vdp` VDP fork, with
  contributions to MOS and VDP proper as well (devlog item 27) — worth
  including alongside Steve and Jeroen when sampling commits.
- **7.** T4 done: sampled five recent, non-fork-only upstream feature
  commits — `5a82ead` (flood fill/ellipse, Steve Sims), `e80588d`
  (keyboard/mouse event queue, Steve Sims), `bbf4d91` (VDP-packet
  suppression, Steve Sims), `9166e28` (full ymodem, Jeroen Venema), and
  `66e74af` (four tile banks, Julian Regel — a third contributor, not
  otherwise tracked yet). Findings below (items 8-13).
- **8.** Header guards follow `#ifndef NAME_H` / `#define NAME_H` /
  `#endif // NAME_H`, all-caps matching the filename, with the closing
  `#endif` always commented with the macro name (seen in
  `thread_safe_variant_deque.h`).
- **9.** Core `video/` files (Steve's realm) use tab indentation, camelCase
  function/member names, and opening braces on the same line. Files
  contributed by others can keep the contributor's own micro-style even
  after merging — Jeroen's `ymodem.h` uses 2-space indentation and
  snake_case (`serialRx_byte_t`, `send_ack`) throughout, unchanged from
  upstream. Consistent with item 1 (no `.clang-format`/enforced style):
  nothing normalizes contributed files to match the surrounding codebase.
- **10.** `debug_log(...)` calls are used liberally for diagnostics, and
  format strings consistently end in `\n\r` (not just `\n`), matching
  serial-console line-ending conventions.
- **11.** VDP protocol variables follow `VDPVAR_<CATEGORY>_<NAME>` (or
  `TESTFLAG_<NAME>` for experimental/gated features) as explicit 16-bit
  hex constants in `video/agon.h`, grouped into numeric ranges by
  subsystem (e.g. `0x0100`s protocol, `0x0200`s system, `0x0300`s tile
  engine, `0x0400`s sprites). Each `#define` still carries an inline `//`
  comment restating the hex value and a short description, even though
  the value is already visible in the line.
- **12.** Existing callback dispatch is invoked at call sites via a small
  macro-combination, e.g. `bufferCallCallbacks(CALLBACK_SENDING_VDPP |
  PACKET_AUDIO)`, not a bespoke per-subsystem call shape. If a general
  completion-notify mechanism gets built (devlog items 25-26), mimicking
  this call-site shape is the path of least resistance for fitting in.
- **13.** Forward-looking `// TODO: ...` comments are left in shipped,
  merged code (e.g. `vdu_audio.h`'s `sendAudioStatus`) rather than being
  resolved before merge, and commented-out alternate implementations are
  sometimes left in place as a documented candidate rather than deleted
  (`thread_safe_variant_deque.h`'s commented-out `pushUniqueValue`). Not
  necessarily to be imitated deliberately, but shows this isn't held to a
  strict "no dead code" bar.

## Still to do

- ~~Mine 3-5 recent *upstream* (not fork-only) feature commits from Steve
  Sims for naming, header-guard style, `debug_log` vs `force_debug_log`
  usage, error-handling idioms, and comment tone (devlog items 10, T4).~~
  Done — see items 7-13. `force_debug_log` specifically wasn't seen in the
  sampled commits; still worth a targeted look before treating item 10 as
  fully closed.
- ~~Do the same, narrower, for Jeroen Venema's contributions specifically
  beyond the one commit sampled in item 7 (devlog item 19, T7).~~ Marked
  done as redundant — T4's 3 Steve Sims commits already answer T7's
  underlying question (style varies by contributor, nothing enforced).
- Read maintainer review comments on merged upstream PRs for de facto
  standards that never made it into a written doc (devlog item 12).
- Spelunk agon-vdp issues/PRs and Steve's own commentary on feature
  direction, last ~3 months only, once that work starts (devlog items
  22, T8 — explicitly deferred for now, not yet begun).
