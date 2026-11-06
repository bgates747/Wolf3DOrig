# r06 fixture correction and loading visibility

Smith authorizes both fixture fixes and Fab visual correctness on Nov5.
Seven eZ80 assemblies, one compiler at a time,120s each. No native/module change
or hardware contact. Inputs are copied frozen r05; retain partial preparation01
(anchor mismatch before any compile). Source r06 correct_fixture.py adds A
first INIT_LEVEL before replay/warmup, both finalized-asset callbacks present
and ordered fence outside timing, and a visible setup transition. Fab visual
variant alone omits diagnostic native CCOUNT reset/dump, unsupported by retained
userspace library. No performance equivalence claimed for that variant.

Reserve/assert Pi build; ordinary finite assembly and source/hash/layout checks,
retain logs and outputs; stop first failure; stop/join owned compiler before
release. Emulator tests use held Oryx312,boost0/80C/finite scope, no GUI launch
on Smith's behalf. Keep lease until Smith explicitly authorizes release.
