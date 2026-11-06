# Pre-code compatibility and intended-work review

The selected correction uses operations already exercised by the exact
production module/native pair. It needs no new API, generic fast span helper,
arithmetic support or firmware extension. The change removes redundant work;
it does not substitute a new rendering method.

## Fixed source and target

The control is the measured physical54 module1907/native7593 and retained
renderer aee6ed18, under WOLF-PERF-003's immutable manifests. The target is its
ABI1.6 scoped COLOR_FRAME interface, native RGB222 rows, checked bias0/XOR2,
colour mask3f/preserve maskc0, acquired row pointers expiring at END. Exact
installed board components will be reconciled later; no old physical grant is
reused. The immutable SDK and existing native image remain the control.

| Original unit/method | Exact supported operation | Intended work/disposition |
| --- | --- | --- |
| Bespoke play/view/bevel rectangle fills | Existing production `fill_rect`/`fill_span` on validated direct rows | Preserve existing top200 play/view/bevel calls and their order |
| Bespoke lower40 HUD background clear | Same existing row/span operation for y200–239 | Initialize the lower40 rows before unchanged HUD composition |
| B's initial full320×240 clear, then top320×200 overwrite | Current rows already expose the same full rectangle; no new capability needed | Remove the first top200 writes; initial fill requests fall by64000 |
| Per-pixel mapping/sync preservation | Existing `put_pixel`, XOR2 and masks | Unchanged, including mandatory compiler PSRAM safety policy |
| Row BEGIN/ROW/END and asset leases | Existing module/runtime lifecycle | Unchanged; no persistent pointer or extra service call |
| DDA, arithmetic helpers, wall/sprite/HUD/weapon/palette methods | Existing measured source/providers | Unchanged; helper/library inefficiency is outside this candidate |
| Guest serialization/receipt/counters/presentation | Existing corrected PERF-003 producer | Reuse only after exact component/private-binding reconciliation; no carrier workaround |

The initial top200 clear is unconditionally followed by `fill_rect` across
the complete top200 play area before walls or asset-dependent rendering.
Both writes use the same masked low-six-bit store. Omitting the earlier write
therefore preserves each final low colour value and the original high sync
bits on successful frames. Rows200–239 still receive their dark background,
including pixels not covered by transparent HUD art. Later draw/shift passes
are retained. Failed hidden frames are still not published; no rollback
guarantee is invented for already changed hidden pixels.

Source-level support verdict: **supported for this one change**. No unresolved
API incompatibility is identified. Actual generated code, whole-frame output,
stack/package fit and performance still require the subsequent gates; this
review is not their proof. New hardware context or source mismatches reopen
the affected binding before target operations.
