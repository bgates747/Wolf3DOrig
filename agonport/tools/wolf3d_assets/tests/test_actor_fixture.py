from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(TOOLS_ROOT))

from formats import actorinfo, mapfile, sprite_kinds, spritenames
from scripts.gen_render_fixture import (
    BUFFERED_WOLF3D,
    SUB_INIT_LEVEL,
    SUB_RENDER_FRAME,
    SUB_SET_ACTOR,
    SUB_SET_PLAYER_POSE,
    W3D_ACTOR_SIZE,
    build_actors,
    build_area_map,
    build_command_stream,
    build_path_directions,
    build_tilemap_and_doors,
    pack_actor_runtime,
)


class RealLevelActorFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        maphead = mapfile.read_maphead((REPO_ROOT / "orig/data/MAPHEAD.WL1").read_bytes())
        cls.level = mapfile.read_level(
            (REPO_ROOT / "orig/data/GAMEMAPS.WL1").read_bytes(),
            maphead,
            0,
            maphead.magic,
        )

    def actors(self, difficulty: actorinfo.Difficulty):
        return build_actors(self.level.plane0, self.level.plane1, difficulty)

    def test_e1l1_exact_original_difficulty_counts(self) -> None:
        expected = {
            actorinfo.Difficulty.BABY: (12, 11, 3),
            actorinfo.Difficulty.EASY: (12, 11, 3),
            actorinfo.Difficulty.MEDIUM: (21, 20, 6),
            actorinfo.Difficulty.HARD: (38, 37, 9),
        }
        for difficulty, (records, kills, active) in expected.items():
            actors = self.actors(difficulty)
            self.assertEqual(len(actors), records)
            self.assertEqual(sum(actor.kind != "DEAD-GRD" for actor in actors), kills)
            self.assertEqual(
                sum(actor.active == actorinfo.ActiveType.YES for actor in actors),
                active,
            )

    def test_medium_row_major_types_and_ambush_markers(self) -> None:
        actors = self.actors(actorinfo.Difficulty.MEDIUM)
        coordinates = [(actor.x >> 16, actor.y >> 16) for actor in actors]
        self.assertEqual(coordinates, sorted(coordinates, key=lambda xy: (xy[1], xy[0])))
        self.assertEqual(
            {(actor.x >> 16, actor.y >> 16) for actor in actors if actor.flags & actorinfo.FL_AMBUSH},
            {(31, 22), (23, 48)},
        )
        self.assertEqual(sum(actor.kind == "GRD" for actor in actors), 17)
        self.assertEqual(sum(actor.kind == "DOG" for actor in actors), 3)
        self.assertEqual(sum(actor.kind == "DEAD-GRD" for actor in actors), 1)

    def test_patrol_position_stays_at_marker_but_cached_tile_is_ahead(self) -> None:
        actors = self.actors(actorinfo.Difficulty.MEDIUM)
        guard = next(actor for actor in actors if actor.marker == 114 and actor.x >> 16 == 7)
        self.assertEqual((guard.x, guard.y), ((7 << 16) + 0x8000, (33 << 16) + 0x8000))
        self.assertEqual((guard.tilex, guard.tiley), (6, 33))
        self.assertEqual(guard.direction, 4)  # west
        self.assertEqual(guard.facing_degrees, 180)
        self.assertEqual(guard.distance, 1 << 16)
        self.assertEqual(guard.shapenum, spritenames.SPR_GRD_S_1 + 8)
        self.assertEqual(guard.rotations, 8)

        dog = next(actor for actor in actors if actor.marker == 177)
        self.assertEqual((dog.x >> 16, dog.y >> 16), (54, 35))
        self.assertEqual((dog.tilex, dog.tiley), (54, 36))
        self.assertEqual(dog.direction, 6)  # south
        self.assertEqual(dog.speed, actorinfo.SPDDOG)

    def test_medium_patrols_get_exact_original_deterministic_phases(self) -> None:
        actors = self.actors(actorinfo.Difficulty.MEDIUM)
        ticcounts = actorinfo.initial_ticcounts(actors)
        timed = [
            ticcount
            for actor, ticcount in zip(actors, ticcounts)
            if actorinfo.initial_state_tictime(actor.state)
        ]
        self.assertEqual(timed, [8, 9, 0, 2, 1, 9])
        untimed = [
            ticcount
            for actor, ticcount in zip(actors, ticcounts)
            if not actorinfo.initial_state_tictime(actor.state)
        ]
        self.assertEqual(untimed, [0] * len(untimed))
        self.assertEqual(actorinfo.random_index_after_initial_ticcounts(actors), 6)

    def test_dead_guard_is_a_nonrotating_inert_actor(self) -> None:
        corpse = next(actor for actor in self.actors(actorinfo.Difficulty.MEDIUM) if actor.marker == 124)
        self.assertEqual((corpse.x >> 16, corpse.y >> 16), (31, 57))
        self.assertEqual(corpse.obclass, actorinfo.ActorClass.INERT)
        self.assertEqual(corpse.state, actorinfo.ActorState.GRD_DEAD)
        self.assertEqual(corpse.shapenum, spritenames.SPR_GRD_DEAD)
        self.assertEqual(corpse.rotations, 0)
        self.assertEqual(corpse.flags, 0)

    def test_e1l1_preserves_area_and_path_metadata(self) -> None:
        areas = build_area_map(self.level.plane0)
        paths = build_path_directions(self.level.plane1)
        self.assertEqual(len(areas), 4096)
        self.assertEqual(len(paths), 4096)
        self.assertEqual(sum(value != 0xFF for value in paths), 18)
        self.assertEqual(paths[33 * 64 + 6], 0xFF)  # destination need not itself be an arrow
        self.assertEqual(areas[22 * 64 + 31], 3)  # ambush tile inherits adjacent area

        _tilemap, doors = build_tilemap_and_doors(self.level.plane0)
        self.assertEqual(doors[0], (28, 11, True, 0, 121, 36, 35))
        self.assertEqual(doors[2], (34, 15, False, 0, 121, 36, 3))
        for tilex, tiley, vertical, _lock, _texture, area1, area2 in doors:
            expected = area2 if vertical else area1
            self.assertEqual(areas[tiley * 64 + tilex], expected)

    def test_door_area_endpoints_reject_nonareas_and_out_of_range_areas(self) -> None:
        for bad_tile in (1, actorinfo.AREATILE + 37):
            with self.subTest(bad_tile=bad_tile):
                plane0 = [
                    [actorinfo.AREATILE for _x in range(mapfile.MAP_WIDTH)]
                    for _y in range(mapfile.MAP_HEIGHT)
                ]
                plane0[10][10] = 90       # vertical door
                plane0[10][11] = bad_tile # east endpoint
                with self.assertRaisesRegex(ValueError, "area endpoint"):
                    build_tilemap_and_doors(plane0)

    def test_actor_seed_rejects_nonareas_and_out_of_range_areas(self) -> None:
        for bad_tile in (1, actorinfo.AREATILE + 37):
            with self.subTest(bad_tile=bad_tile):
                plane0 = [
                    [actorinfo.AREATILE for _x in range(mapfile.MAP_WIDTH)]
                    for _y in range(mapfile.MAP_HEIGHT)
                ]
                plane1 = [
                    [0 for _x in range(mapfile.MAP_WIDTH)]
                    for _y in range(mapfile.MAP_HEIGHT)
                ]
                plane0[10][10] = bad_tile
                plane1[10][10] = 108  # baby/easy standing guard
                with self.assertRaisesRegex(ValueError, "area endpoint"):
                    build_actors(plane0, plane1, actorinfo.Difficulty.MEDIUM)

    def test_fixture_rejects_more_than_64_doors(self) -> None:
        plane0 = [
            [actorinfo.AREATILE for _x in range(mapfile.MAP_WIDTH)]
            for _y in range(mapfile.MAP_HEIGHT)
        ]
        coordinates = [
            (x, y)
            for y in (2, 4, 6)
            for x in range(2, 63, 2)
        ][:65]
        self.assertEqual(len(coordinates), 65)
        for x, y in coordinates:
            plane0[y][x] = 90
        with self.assertRaisesRegex(ValueError, "more than 64 doors"):
            build_tilemap_and_doors(plane0)

    def test_ghosts_retain_zero_initialized_hitpoints(self) -> None:
        plane0 = [[107 for _x in range(64)] for _y in range(64)]
        ghost = actorinfo.from_plane1(
            224, 12, 9, plane0, actorinfo.Difficulty.HARD
        )
        self.assertIsNotNone(ghost)
        assert ghost is not None
        self.assertEqual(ghost.obclass, actorinfo.ActorClass.GHOST)
        self.assertEqual(ghost.hitpoints, 0)
        self.assertEqual(ghost.flags & actorinfo.FL_SHOOTABLE, 0)


class ActorWireAndRuntimeTests(unittest.TestCase):
    @staticmethod
    def empty_plane() -> list[list[int]]:
        return [[107 for _x in range(64)] for _y in range(64)]

    def sample_actor(self) -> actorinfo.ActorSeed:
        plane0 = self.empty_plane()
        actor = actorinfo.from_plane1(
            109, 5, 7, plane0, actorinfo.Difficulty.MEDIUM
        )
        assert actor is not None
        return actor

    def test_set_actor_packet_is_exact_and_precedes_player(self) -> None:
        actor = self.sample_actor()
        stream = build_command_stream(0x1234, 0x4567, [], [], 1, 2, 90, actors=[actor])
        prefix = bytes((23, 0, 0xA0, 0x34, 0x12, BUFFERED_WOLF3D))
        self.assertEqual(stream[:7], prefix + bytes((SUB_INIT_LEVEL,)))
        actor_offset = 9
        self.assertEqual(stream[actor_offset:actor_offset + 7], prefix + bytes((SUB_SET_ACTOR,)))
        expected_payload = (
            struct.pack("<HhiiHB", 1, actor.shapenum, actor.x, actor.y,
                        actor.facing_degrees, actor.rotations)
        )
        self.assertEqual(stream[actor_offset + 7:actor_offset + 22], expected_payload)
        player_offset = actor_offset + 22
        render_offset = player_offset + 17
        self.assertEqual(stream[player_offset:player_offset + 7], prefix + bytes((SUB_SET_PLAYER_POSE,)))
        self.assertEqual(stream[render_offset:render_offset + 7], prefix + bytes((SUB_RENDER_FRAME,)))
        self.assertEqual(len(stream), render_offset + 7)

    def test_runtime_record_matches_39_byte_sight_prefix_layout(self) -> None:
        actor = self.sample_actor()
        record = pack_actor_runtime(
            actor, next_slot=9, previous_slot=3, ticcount=0x1234
        )
        self.assertEqual(len(record), W3D_ACTOR_SIZE)
        self.assertEqual(struct.unpack_from("<ii", record, 0), (actor.x, actor.y))
        self.assertEqual(record[8:12], bytes((actor.tilex, actor.tiley, actor.area, actor.direction)))
        self.assertEqual(record[12], actor.active)
        self.assertEqual(record[13], actor.obclass)
        self.assertEqual(record[14], actor.flags)
        self.assertEqual(struct.unpack_from("<h", record, 15)[0], 0x1234)
        self.assertEqual(struct.unpack_from("<H", record, 17)[0], actor.state)
        self.assertEqual(struct.unpack_from("<i", record, 19)[0], actor.distance)
        self.assertEqual(struct.unpack_from("<h", record, 23)[0], actor.angle)
        self.assertEqual(struct.unpack_from("<h", record, 25)[0], actor.hitpoints)
        self.assertEqual(struct.unpack_from("<i", record, 27)[0], actor.speed)
        self.assertEqual(record[31:37], b"\x00" * 6)
        self.assertEqual(record[37:39], bytes((9, 3)))

    def test_original_random_increments_before_lookup_and_wraps(self) -> None:
        random = actorinfo.DeterministicRandom()
        values = [random.rndt() for _ in range(256)]
        self.assertEqual(len(actorinfo.RND_TABLE), 256)
        self.assertEqual(values[:6], [8, 109, 220, 222, 241, 149])
        self.assertEqual(values[-1], 0)
        self.assertEqual(random.index, 0)
        self.assertEqual(random.rndt(), 8)

    def test_actor_state_ids_match_the_assembly_contract(self) -> None:
        world_inc = (
            REPO_ROOT / "src/asm/wolf3d/src/wolf3d_world.inc"
        ).read_text().splitlines()
        constants = {}
        for line in world_inc:
            if not line.startswith("W3D_STATE_") or ":" not in line or " equ " not in line:
                continue
            label, value = line.split(":", 1)
            constants[label] = int(value.split("equ", 1)[1].split()[0])
        for state in actorinfo.ActorState:
            self.assertEqual(constants[f"W3D_STATE_{state.name}"], int(state))

    def test_zero_duration_actors_do_not_consume_random_values(self) -> None:
        plane0 = self.empty_plane()
        markers = (109, 112, 124, 113)
        actors = [
            actorinfo.from_plane1(
                marker, 5 + index, 7, plane0, actorinfo.Difficulty.MEDIUM
            )
            for index, marker in enumerate(markers)
        ]
        self.assertNotIn(None, actors)
        self.assertEqual(actorinfo.initial_ticcounts(actors), [0, 8, 0, 9])

    def test_fake_hitler_block_starts_at_real_fake_art(self) -> None:
        self.assertEqual(spritenames.SPR_FAKE_W1, 321)
        self.assertNotEqual(spritenames.SPR_FAKE_W1, spritenames.SPR_MECHA_W1)
        self.assertEqual(sprite_kinds.kind_shapenum_block("HTLR-FAKE", 435), (321, 333))
        self.assertEqual(sprite_kinds.kind_shapenum_block("HITLER", 435), (334, 359))

    def test_bad_plane_dimensions_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "64x64"):
            build_actors([[0]], [[0]], actorinfo.Difficulty.MEDIUM)
        with self.assertRaisesRegex(ValueError, "64x64"):
            build_area_map([[0]])
        with self.assertRaisesRegex(ValueError, "64x64"):
            build_path_directions([[0]])


if __name__ == "__main__":
    unittest.main()
