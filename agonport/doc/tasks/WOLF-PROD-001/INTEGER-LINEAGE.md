# Original integer pipeline: source verification

The promoted renderer follows the original Wolfenstein integer/fixed-point hot
path. That design predates both Agon ports. It is not a new conversion from a
floating-point renderer. The read-only original reference is under `orig/src/`;
its file identities are in ORIGINAL-SOURCE-PINS.json. Original source remains
under its own license and is not republished here.

| Work | Original source evidence | Maintained port and differences |
| --- | --- | --- |
| Positions and angles | `WL_DEF.H:97–106`: GLOBAL1=1<<16, TILESHIFT=16, 360 headings and 3600 fine angles; fixed is long at480 | World coordinates remain signed32 Q16.16 and heading u16 degrees. The wire format and eZ80's signed24 movement deltas are port-specific. |
| View transform | `WL_DRAW.C:131–183,210–260,1298–1318`: FixedByFrac, translated coordinate products, degree sine/cosine lookup, focal offset | Same fixed-point/view-transform method. Original sine values use signed magnitude; our table is two's complement and multiplication widens to int64 then shifts. This is not a blanket bit-identical arithmetic claim. |
| Ray traversal | `WL_DR_A.ASM:198–367` quadrant tangent setup and subsequent integer grid/intercept crossing loops | `production/original_raywalk.h` restores the table/intercept method with explicit unsigned word wrapping, signed high-word comparisons and integer products. It replaces our earlier port's reciprocal-DDA setup divisions. Original door/pushwall and texture-face distinctions are retained under PERF007's documented finite coverage. |
| Table construction | `WL_MAIN.C:586–625,640–688`: floating-point tan/sin/atan during BuildTables/CalcProjection | This is an exception to "integer everywhere": original setup used floating point, then the frame hot path used integer tables. Our tables are generated offline, so those transcendental calls are absent from the running VDP renderer. Whole-degree sine reduction preserves the qualified port values; it does not regenerate original compiler floating-point results. |
| Projection | `WL_DRAW.C:210–260,287–343,359–384`: fixed camera-space coordinates and integer perspective division, minimum depth and shifted height denominator | Same broad method; port scale/view size/height units differ. Widened C++ products and guarded u32/full-width divider are modern implementation choices. We have not adopted the original height quantization wholesale. |
| Texture sampling | `WL_DRAW.C:400–460,476–605`, `WL_SCALE.C`: integer/scaled wall posts and sprites, texture-column selection, grouped posts | Sampling remains integer. VGA's generated scaler code, planar writes and original post grouping are not copied literally into the RGB222 borrowed-row implementation. Our byte-span loop, lease-aware texture chains and equal-height setup cache are separately qualified port optimizations. |
| Game motion and time | Original `WL_AGENT.C` uses integer movement/clipping; `WL_DRAW.C:1234–1266` computes adaptive integer tics | eZ80 collision/motion remains integer, but MOS120Hz/four-tick updates and bounded catch-up are port scheduling decisions. They are not Carmack's original adaptive70Hz scheduling. This promotion does not introduce an independent async physics/render pipeline. |

PERF007's retained qualification includes all900 tangent values, explicit word/
shift/partial-product fixtures, selected quadrant/grid transcripts and visual/
geometry comparisons. Its report explicitly stops short of independent execution
of the historical DOS binary or exhaustive rounding/corner/game-state proof.
The new promotion additionally checks exact output against completed combined021;
that establishes preservation of our qualified implementation, not equivalence
to every original DOS frame.

There is no runtime sin/cos/tan, half/float/radians wire conversion or target
floating-point texture sampler in these reviewed paths. Original setup-time
floating point and host table generation must be kept separate from that claim.
