#!/usr/bin/env python3
"""Directed synthetic and real-E1L1 tests for :mod:`area_oracle`."""

from __future__ import annotations

from pathlib import Path
import re
import struct
import unittest

import area_oracle as ao


STAGED_ROOT = Path(__file__).resolve().parents[4]
FIXTURE = STAGED_ROOT / "src/asm/wolf3d/src/wolf3d_fixture.inc"


def parse_label_bytes(text: str, start_label: str, end_label: str) -> bytes:
    match = re.search(
        rf"(?ms)^\s*{re.escape(start_label)}:\s*$"
        rf"(.*?)"
        rf"^\s*{re.escape(end_label)}:\s*$",
        text,
    )
    if match is None:
        raise AssertionError(f"cannot find {start_label}..{end_label}")
    values: list[int] = []
    for line in match.group(1).splitlines():
        directive = re.search(r"\bdb\s+([^;]+)", line, re.IGNORECASE)
        if directive:
            values.extend(int(item.strip(), 0) for item in directive.group(1).split(","))
    return bytes(values)


class SyntheticConnectivityTests(unittest.TestCase):
    def test_isolated_root_and_transitive_undirected_chain(self) -> None:
        graph = ao.AreaConnectivity(
            [ao.synthetic_door(1, 2), ao.synthetic_door(2, 3), ao.synthetic_door(4, 3)],
            player_area=1,
        )
        self.assertEqual(graph.reachable_areas, {1})
        graph.set_door_position(0, 1)
        self.assertEqual(graph.reachable_areas, {1, 2})
        graph.set_door_position(1, 0x8000)
        self.assertEqual(graph.reachable_areas, {1, 2, 3})
        graph.set_door_position(2, 0xFFFF)
        self.assertEqual(graph.reachable_areas, {1, 2, 3, 4})

        graph.set_player_area(4)
        self.assertEqual(graph.reachable_areas, {1, 2, 3, 4})
        self.assertEqual(len(graph.reachable), 37)
        self.assertTrue(all(value in (0, 1) for value in graph.reachable))

    def test_position_alone_controls_topology_and_threshold_rebuilds(self) -> None:
        door = ao.synthetic_door(0, 36, position=0, action=ao.DOOR_OPEN)
        graph = ao.AreaConnectivity([door], player_area=0)
        initial_rebuilds = graph.rebuild_count
        self.assertEqual(graph.reachable_areas, {0})  # OPEN label, zero position

        self.assertTrue(graph.set_door_position(0, 1))
        self.assertEqual(graph.reachable_areas, {0, 36})
        self.assertEqual(graph.rebuild_count, initial_rebuilds + 1)

        graph.doors[0].action = ao.DOOR_CLOSED
        self.assertFalse(graph.set_door_position(0, 2))
        self.assertEqual(graph.rebuild_count, initial_rebuilds + 1)
        self.assertEqual(graph.reachable_areas, {0, 36})  # CLOSED label, positive position

        self.assertTrue(graph.set_door_position(0, 0))
        self.assertEqual(graph.reachable_areas, {0})
        self.assertEqual(graph.rebuild_count, initial_rebuilds + 2)

    def test_parallel_doors_keep_edge_until_last_one_closes(self) -> None:
        graph = ao.AreaConnectivity(
            [ao.synthetic_door(5, 7, position=1),
             ao.synthetic_door(7, 5, position=0xFFFF)],
            player_area=5,
        )
        self.assertEqual(graph.reachable_areas, {5, 7})
        graph.set_door_position(0, 0)
        self.assertEqual(graph.reachable_areas, {5, 7})
        graph.set_door_position(1, 0)
        self.assertEqual(graph.reachable_areas, {5})

    def test_self_loops_do_not_expand_or_duplicate_queue(self) -> None:
        doors = [ao.synthetic_door(2, 2, position=1) for _ in range(64)]
        graph = ao.AreaConnectivity(doors, player_area=2)
        self.assertEqual(graph.reachable_areas, {2})
        self.assertEqual(graph.last_queue_peak, 1)
        self.assertEqual(graph.fault_count, 0)

    def test_cycle_marks_before_enqueue_and_stays_bounded(self) -> None:
        doors = [
            ao.synthetic_door(area, (area + 1) % 37, position=1)
            for area in range(37)
        ]
        graph = ao.AreaConnectivity(doors, player_area=0)
        self.assertEqual(graph.reachable_areas, set(range(37)))
        self.assertLessEqual(graph.last_queue_peak, 37)

    def test_invalid_open_endpoints_are_ignored_and_fault_once_per_rebuild(self) -> None:
        graph = ao.AreaConnectivity(
            [ao.synthetic_door(1, 2), ao.synthetic_door(1, 37),
             ao.synthetic_door(255, 2)],
            player_area=1,
        )
        self.assertEqual(graph.fault_count, 0)  # malformed but closed is inert

        graph.doors[0].position = 1
        graph.doors[1].position = 1
        graph.doors[2].position = 1
        graph.force_rebuild()
        self.assertEqual(graph.reachable_areas, {1, 2})
        self.assertEqual(graph.last_invalid_open_doors, (1, 2))
        self.assertEqual(graph.last_rebuild_faults, 2)
        self.assertEqual(graph.fault_count, 2)

        # Faults are per invalid door per rebuild, not per reached BFS node.
        graph.force_rebuild()
        self.assertEqual(graph.last_rebuild_faults, 2)
        self.assertEqual(graph.fault_count, 4)

    def test_invalid_player_root_faults_only_on_transition_and_clears(self) -> None:
        graph = ao.AreaConnectivity([ao.synthetic_door(1, 2, position=1)], 1)
        self.assertEqual(graph.reachable_areas, {1, 2})
        self.assertTrue(graph.set_player_area(ao.AREA_NONE))
        self.assertEqual(graph.reachable_areas, set())
        self.assertEqual((graph.last_rebuild_faults, graph.fault_count), (1, 1))

        self.assertFalse(graph.set_player_area(ao.AREA_NONE))
        graph.force_rebuild()
        self.assertEqual((graph.last_rebuild_faults, graph.fault_count), (0, 1))

        self.assertTrue(graph.set_player_area(37))
        self.assertEqual((graph.last_rebuild_faults, graph.fault_count), (1, 2))
        self.assertEqual(graph.reachable_areas, set())
        self.assertTrue(graph.set_player_area(2))
        self.assertEqual(graph.reachable_areas, {1, 2})
        self.assertEqual(graph.fault_count, 2)

    def test_initial_invalid_root_faults_once(self) -> None:
        graph = ao.AreaConnectivity([], ao.AREA_NONE)
        self.assertEqual(graph.reachable_areas, set())
        self.assertEqual((graph.rebuild_count, graph.fault_count), (1, 1))

    def test_more_than_maximum_doors_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at most 64"):
            ao.AreaConnectivity([ao.synthetic_door(1, 2)] * 65, 1)


class ActorAreaGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reachable = bytearray(37)
        self.reachable[3] = 1

    def test_scheduler_uses_area_only_for_active_no(self) -> None:
        cases = (
            (ao.ACTIVE_NO, 3, True),
            (ao.ACTIVE_NO, 4, False),
            (ao.ACTIVE_NO, ao.AREA_NONE, False),
            (ao.ACTIVE_YES, 4, True),
            (ao.ACTIVE_ALWAYS, ao.AREA_NONE, True),
            (ao.ACTIVE_FREE, 3, False),
            (7, 3, False),
        )
        for active, area, expected in cases:
            with self.subTest(active=active, area=area):
                record = ao.actor_record(area=area, active=active)
                before = bytes(record)
                self.assertEqual(ao.actor_schedulable(record, self.reachable), expected)
                self.assertEqual(record, before)  # eligibility never promotes ACTIVE

    def test_global_phase_is_not_part_of_actor_eligibility(self) -> None:
        actor = ao.actor_record(area=4, active=ao.ACTIVE_NO)
        for _phase_tics in (2, 2, 3, 2, 2, 3):
            self.assertFalse(ao.actor_schedulable(actor, self.reachable))
        self.reachable[4] = 1
        self.assertTrue(ao.actor_schedulable(actor, self.reachable))

    def test_player_overlap_is_inclusive_only_in_connected_area(self) -> None:
        connected = ao.actor_record(area=3, active=ao.ACTIVE_YES)
        disconnected = ao.actor_record(area=4, active=ao.ACTIVE_YES)
        invalid = ao.actor_record(area=ao.AREA_NONE, active=ao.ACTIVE_YES)
        px, py = 0x100000, 0x200000

        for dx, dy, expected_clear in (
            (0, 0, False),
            (ao.TILE_GLOBAL, ao.TILE_GLOBAL, False),
            (-ao.TILE_GLOBAL, -ao.TILE_GLOBAL, False),
            (ao.TILE_GLOBAL + 1, 0, True),
            (0, -ao.TILE_GLOBAL - 1, True),
        ):
            with self.subTest(dx=dx, dy=dy):
                self.assertEqual(
                    ao.actor_candidate_clear_of_player(
                        connected, self.reachable,
                        candidate_x=px + dx, candidate_y=py + dy,
                        player_x=px, player_y=py,
                    ),
                    expected_clear,
                )

        for record in (disconnected, invalid):
            self.assertTrue(
                ao.actor_candidate_clear_of_player(
                    record, self.reachable,
                    candidate_x=px, candidate_y=py,
                    player_x=px, player_y=py,
                )
            )

    def test_actor_and_reachability_sizes_are_enforced(self) -> None:
        with self.assertRaisesRegex(ValueError, "39 bytes"):
            ao.actor_schedulable(bytes(38), self.reachable)
        with self.assertRaisesRegex(ValueError, "37 bytes"):
            ao.actor_schedulable(ao.actor_record(area=3, active=0), bytes(36))


class RealE1L1ConnectivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        text = FIXTURE.read_text()
        door_bytes = parse_label_bytes(
            text, "w3d_fixture_initial_doors", "w3d_fixture_initial_doors_end"
        )
        cls.doors = [
            ao.Door.from_bytes(door_bytes[offset:offset + ao.DOOR_SIZE])
            for offset in range(0, len(door_bytes), ao.DOOR_SIZE)
        ]
        cls.area_map = parse_label_bytes(
            text, "w3d_fixture_area_map", "w3d_fixture_area_map_end"
        )
        cls.player_pose = parse_label_bytes(
            text, "w3d_fixture_initial_player_pose", "w3d_fixture_initial_player_pose_end"
        )
        cls.actor_bytes = parse_label_bytes(
            text, "w3d_fixture_initial_actors", "w3d_fixture_initial_actors_end"
        )

    def fresh_graph(self) -> ao.AreaConnectivity:
        # Round-trip to keep every test's mutable positions independent.
        doors = [ao.Door.from_bytes(door.to_bytes()) for door in self.doors]
        return ao.AreaConnectivity(doors, player_area=2)

    def test_fixture_player_starts_in_area2_with_every_door_closed(self) -> None:
        x, y, _angle = struct.unpack("<iiH", self.player_pose)
        self.assertEqual((x >> 16, y >> 16), (29, 57))
        self.assertEqual(self.area_map[(y >> 16) * 64 + (x >> 16)], 2)
        self.assertEqual(len(self.doors), 22)
        self.assertTrue(all(door.position == 0 for door in self.doors))
        self.assertEqual(self.fresh_graph().reachable_areas, {2})

    def test_exact_player_component_chain_16_7_2(self) -> None:
        graph = self.fresh_graph()
        self.assertEqual((graph.doors[16].area1, graph.doors[16].area2), (1, 2))
        self.assertEqual((graph.doors[7].area1, graph.doors[7].area2), (3, 1))
        self.assertEqual((graph.doors[2].area1, graph.doors[2].area2), (36, 3))

        graph.set_door_position(16, 1)
        self.assertEqual(graph.reachable_areas, {1, 2})
        graph.set_door_position(7, 1)
        self.assertEqual(graph.reachable_areas, {1, 2, 3})
        graph.set_door_position(2, 1)
        self.assertEqual(graph.reachable_areas, {1, 2, 3, 36})

    def test_all_open_reaches_exactly_all_15_used_areas(self) -> None:
        graph = self.fresh_graph()
        for door in graph.doors:
            door.position = 1
        graph.force_rebuild()
        expected = {0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 32, 33, 34, 35, 36}
        self.assertEqual(graph.reachable_areas, expected)
        self.assertEqual(
            set(self.area_map) - {ao.AREA_NONE},
            expected,
        )
        self.assertEqual(graph.fault_count, 0)

    def test_real_parallel_and_self_loop_endpoints(self) -> None:
        self.assertEqual(
            {(self.doors[index].area1, self.doors[index].area2) for index in (0, 1)},
            {(36, 35), (35, 36)},
        )
        self.assertEqual(
            {(self.doors[index].area1, self.doors[index].area2) for index in (8, 11)},
            {(5, 7)},
        )
        self.assertEqual(
            {index for index, door in enumerate(self.doors) if door.area1 == door.area2},
            {12, 15, 18, 19, 20, 21},
        )

    def test_real_actor_scheduler_checkpoints(self) -> None:
        actors = [
            self.actor_bytes[offset:offset + ao.ACTOR_SIZE]
            for offset in range(0, len(self.actor_bytes), ao.ACTOR_SIZE)
        ]
        self.assertEqual(len(actors), 21)
        graph = self.fresh_graph()

        def eligible_slots() -> set[int]:
            return {
                slot for slot, actor in enumerate(actors, start=1)
                if ao.actor_schedulable(actor, graph.reachable)
            }

        # Six patrols are ACTIVE_YES everywhere. Corpse 20 and stander 21 are
        # ACTIVE_NO but begin in the player's area 2.
        self.assertEqual(eligible_slots(), {11, 12, 13, 14, 15, 17, 20, 21})

        for door_index in (16, 7, 2):
            graph.set_door_position(door_index, 1)
        # Areas 36 and 3 add inactive standers 1,2 and 6,8 respectively.
        self.assertEqual(
            eligible_slots(),
            {1, 2, 6, 8, 11, 12, 13, 14, 15, 17, 20, 21},
        )

        for door in graph.doors:
            door.position = 1
        graph.force_rebuild()
        self.assertEqual(eligible_slots(), set(range(1, 22)))


if __name__ == "__main__":
    unittest.main()
