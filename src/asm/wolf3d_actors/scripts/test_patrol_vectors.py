#!/usr/bin/env python3
"""Format and golden-value checks for the durable patrol vector generator."""

from __future__ import annotations

from pathlib import Path
import re
import tempfile
import unittest

import actor_oracle as ao
import generate_patrol_vectors as pv


FIXTURE = Path(__file__).resolve().parents[4] / "src/asm/wolf3d/src/wolf3d_fixture.inc"


def actor_at(payload: bytes, offset: int) -> ao.Actor:
    return ao.Actor.from_bytes(payload[offset:offset + ao.ACTOR_RECORD.size])


class PatrolVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = pv.build_vectors(FIXTURE)
        cls.by_id = {vector.case_id: vector for vector in cls.vectors}
        cls.blob = pv.build_blob(cls.vectors)

    def test_header_and_every_fixed_record_are_stable(self) -> None:
        self.assertEqual(pv.HEADER_SIZE, 16)
        self.assertEqual(pv.RECORD_SIZE, 192)
        self.assertEqual([vector.case_id for vector in self.vectors], list(range(1, 12)))
        self.assertEqual(len(self.blob), 16 + 11 * 192)
        self.assertEqual(
            pv.HEADER.unpack_from(self.blob),
            (pv.MAGIC, pv.VERSION, pv.RECORD_SIZE, 11, pv.SEED),
        )
        for vector in self.vectors:
            with self.subTest(vector=vector.name):
                self.assertEqual(len(vector.payload), pv.RECORD_SIZE)
                self.assertEqual(vector.payload[124:128], bytes(4))
                patch_count = vector.payload[pv.OFF_PATCH_COUNT]
                self.assertLessEqual(patch_count, pv.PATCH_CAPACITY)
                unused = pv.OFF_PATCHES + patch_count * pv.PATCH_SIZE
                self.assertEqual(vector.payload[unused:], bytes(pv.RECORD_SIZE - unused))

    def test_cadence_zero_latch_and_dirty_shape_boundaries(self) -> None:
        cadence = self.by_id[1].payload
        self.assertEqual(actor_at(cadence, pv.OFF_INITIAL_ACTOR).ticcount, 20)
        self.assertEqual(actor_at(cadence, pv.OFF_EXPECTED_ACTOR).ticcount, 13)
        self.assertEqual((cadence[pv.OFF_FINAL_ACTOR_PHASE], cadence[pv.OFF_EXPECTED_ACTOR_DIRTY]),
                         (0, 0))

        latched = actor_at(self.by_id[2].payload, pv.OFF_EXPECTED_ACTOR)
        self.assertEqual((latched.state, latched.ticcount), (ao.STATE_GRD_PATH1, 0))
        self.assertEqual(latched.x, ao.fixed(10) + 3584)

        pause = self.by_id[3].payload
        self.assertEqual(actor_at(pause, pv.OFF_EXPECTED_ACTOR).state, ao.STATE_GRD_PATH1S)
        self.assertEqual(pause[pv.OFF_EXPECTED_ACTOR_DIRTY], 0)
        changed = self.by_id[4].payload
        self.assertEqual(actor_at(changed, pv.OFF_EXPECTED_ACTOR).state, ao.STATE_GRD_PATH2)
        self.assertEqual(changed[pv.OFF_EXPECTED_ACTOR_DIRTY], 1)

    def test_dog_residual_vector_carries_complete_occupancy_move(self) -> None:
        payload = self.by_id[5].payload
        actor = actor_at(payload, pv.OFF_EXPECTED_ACTOR)
        self.assertEqual(
            (actor.x, actor.y, actor.tile_x, actor.tile_y,
             actor.direction, actor.distance),
            (ao.fixed(11), ao.fixed(10) - 2488, 11, 9,
             ao.DIR_NORTH, ao.TILE_GLOBAL - 2488),
        )
        patches = payload[pv.OFF_PATCHES:pv.OFF_PATCHES + 16]
        self.assertEqual(patches[0:2], bytes((11, 10)))
        self.assertEqual(patches[6:8], bytes((7, 0)))
        self.assertEqual(patches[8:10], bytes((11, 9)))
        self.assertEqual(patches[14:16], bytes((0, 7)))

    def test_dog_block_guard_wait_and_door_first_are_distinct(self) -> None:
        dog = self.by_id[6].payload
        dog_actor = actor_at(dog, pv.OFF_EXPECTED_ACTOR)
        self.assertEqual((dog_actor.tile_x, dog_actor.direction), (10, ao.DIR_NODIR))
        self.assertEqual(dog[pv.OFF_EXPECTED_DOOR_DIRTY], 0)

        guard = self.by_id[7].payload
        guard_actor = actor_at(guard, pv.OFF_EXPECTED_ACTOR)
        guard_door = ao.Door.from_fixture_bytes(
            guard[pv.OFF_EXPECTED_DOOR:pv.OFF_EXPECTED_DOOR + 10]
        )
        self.assertEqual((guard_actor.tile_x, guard_actor.distance), (11, -1))
        self.assertEqual(guard_door.action, ao.DOOR_OPENING)
        self.assertEqual(guard[pv.OFF_EXPECTED_DOOR_DIRTY], 1)

        ordered = self.by_id[8].payload
        ordered_actor = actor_at(ordered, pv.OFF_EXPECTED_ACTOR)
        ordered_door = ao.Door.from_fixture_bytes(
            ordered[pv.OFF_EXPECTED_DOOR:pv.OFF_EXPECTED_DOOR + 10]
        )
        self.assertEqual((ordered_door.action, ordered_door.position),
                         (ao.DOOR_OPEN, 0xFFFF))
        self.assertEqual((ordered_actor.x, ordered_actor.distance),
                         (ao.fixed(10) + 1024, 0xFC00))

    def test_player_boundary_and_real_e1l1_golden(self) -> None:
        overlap = self.by_id[9].payload
        before = actor_at(overlap, pv.OFF_INITIAL_ACTOR)
        after = actor_at(overlap, pv.OFF_EXPECTED_ACTOR)
        self.assertEqual((after.x, after.distance), (before.x, before.distance))
        self.assertEqual(overlap[pv.OFF_EXPECTED_ACTOR_DIRTY], 0)

        real = self.by_id[10].payload
        real_initial = actor_at(real, pv.OFF_INITIAL_ACTOR)
        actor = actor_at(real, pv.OFF_EXPECTED_ACTOR)
        door = ao.Door.from_fixture_bytes(
            real[pv.OFF_EXPECTED_DOOR:pv.OFF_EXPECTED_DOOR + 10]
        )
        self.assertEqual(int.from_bytes(real[pv.OFF_STEPS:pv.OFF_STEPS + 2], "little"), 92)
        self.assertEqual(real[pv.OFF_DOOR_INDEX], 8)
        self.assertEqual((real_initial.next_slot, real_initial.previous_slot),
                         (0xFF, 0xFF))
        self.assertEqual((actor.next_slot, actor.previous_slot), (0xFF, 0xFF))
        self.assertEqual(
            (actor.x, actor.y, actor.tile_x, actor.tile_y, actor.distance,
             actor.state, actor.ticcount),
            (0x067C00, 0x218000, 5, 33, 0xFC00,
             ao.STATE_GRD_PATH4, 14),
        )
        self.assertEqual((door.action, door.position), (ao.DOOR_OPEN, 0xFFFF))
        self.assertEqual((real[pv.OFF_FINAL_ACTOR_PHASE], real[pv.OFF_FINAL_DOOR_PHASE]),
                         (2, 2))

    def test_malformed_wait_cannot_alias_door_zero(self) -> None:
        payload = self.by_id[11].payload
        before = actor_at(payload, pv.OFF_INITIAL_ACTOR)
        after = actor_at(payload, pv.OFF_EXPECTED_ACTOR)
        door = ao.Door.from_fixture_bytes(
            payload[pv.OFF_EXPECTED_DOOR:pv.OFF_EXPECTED_DOOR + 10]
        )
        self.assertEqual(before.distance, -257)
        self.assertEqual((before.direction, after.direction),
                         (ao.DIR_EAST, ao.DIR_NODIR))
        self.assertEqual(after.distance, -257)
        self.assertEqual((door.action, door.timer), (ao.DOOR_CLOSED, 0))
        self.assertEqual(payload[pv.OFF_EXPECTED_ACTOR_DIRTY], 0)
        self.assertEqual(payload[pv.OFF_EXPECTED_DOOR_DIRTY], 0)

    def test_binary_and_include_outputs_are_byte_identical(self) -> None:
        self.assertEqual(self.blob, pv.build_blob(pv.build_vectors(FIXTURE)))
        with tempfile.TemporaryDirectory(prefix="w3pv-") as temporary:
            include = Path(temporary) / "vectors.inc"
            pv.emit_include(include, self.vectors, self.blob)
            values: list[int] = []
            for line in include.read_text().splitlines():
                directive = re.search(r"\bdb\s+([^;]+)", line, re.IGNORECASE)
                if directive:
                    values.extend(int(item.strip()) for item in directive.group(1).split(","))
            self.assertEqual(bytes(values), self.blob)
            text = include.read_text()
            for vector in self.vectors:
                self.assertIn(f"case {vector.case_id}: {vector.name}", text)


if __name__ == "__main__":
    unittest.main()
