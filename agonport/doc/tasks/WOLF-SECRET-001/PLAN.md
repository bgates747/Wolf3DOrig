# WOLF-SECRET-001 — Make secret pushwalls easy to find and test

Prepared November 18, 2026 for Smith’s review. This task supports the Episode 1
pushwall acceptance item. Investigation and implementation begin after review.
The regular game keeps its stock secret walls. Special textures, lettering,
and spawn changes belong only in the test fixture.

1. **Locate the real walls.** Inspect the Episode 1 level data for secret
   pushwall markers and match each marker to its wall and usable approach.
   Record floor, tile coordinates, coordinate convention, approachable side,
   and simple directions from a recognizable landmark. Start with E1L1. The
   November 3 devlog records an earlier staged E1L1 visual and collision review
   with human acceptance pending. Use that record to locate the fixture and
   confirm its setup against the map. Reuse its room, pushwall, spawn setup and
   supporting inputs wherever they suit the modified fixture. [Earlier review](../../devlog_20261103.md#shareware-parity-tranche-a1-pushwalls)
2. **Investigate a distinct wall texture.** Try the design of an original wood
   panel with large, readable **PUSH ME** lettering in a test fixture. Check
   whether the existing tile and texture assignments can select it per marked
   wall without changing ordinary walls or the logic that makes the wall pushable.
   Trace how the texture is selected before activation, while the wall moves, and
   at its final position. Check texture ID capacity, asset loading, face orientation
   and readability at the proposed spawn distance. Document any renderer or level
   package change that would be required before choosing an implementation.
3. **Design the test spawn.** Prefer a test-only spawn in an existing E1L1 room
   with a usable pushwall. Place the player a short walk from it, facing the
   lettering from the side that pushes it, with a clear approach and enough space
   to observe the motion. If the existing room is unsuitable, propose a small
   dedicated room. Keep the ordinary episode’s maps, textures and spawn intact for
   this fixture. Give the reviewer the exact start command and Use control.
4. **Define what the test must show.** The marked wall is obvious from spawn.
   Use starts a continuous slide, the moving wall still blocks movement, the
   original tile becomes traversable when clear, and the final wall position is
   solid. Check that the secret counts once, repeated Use does not award it
   again, nearby normal walls are unaffected, and a fresh start restores the wall.
   Use an unmodified E1L1 wall as a comparison before closing the Episode 1 item.
5. **Run on the latest accepted engine.** Build and run the adapted fixture
   through the normal production game and its matching VDPlet renderer. The
   current reference is WOLF-PROD-001 with renderer `7490d81c`. At execution,
   confirm the latest accepted game revision and module and record both in the
   fixture receipt. Use the target’s firmware defaults from `FIRMWARE.md`.
   Treat the old fixture as a source of setup and assets. Its staged executable,
   renderer and firmware belong to the earlier review. Confirm the marked spawn
   and pushwall behavior on the accepted engine before handing it to Smith.
   [Production qualification](../WOLF-PROD-001/RESULT.md)

Return a location list, texture feasibility findings, and the proposed spawn and
test sequence. This review copy authorizes documentation only. Any later Olimex
run follows the [canonical bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
