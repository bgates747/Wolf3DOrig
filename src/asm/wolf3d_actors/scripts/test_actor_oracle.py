#!/usr/bin/env python3
"""Directed regression for :mod:`actor_oracle` and the real E1L1 fixture."""

from __future__ import annotations

from pathlib import Path
import re
import unittest

import actor_oracle as ao


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
        code = line.split(";", 1)[0]
        directive = re.search(r"\bdb\s+(.+)$", code, re.IGNORECASE)
        if directive:
            values.extend(int(item.strip(), 0) for item in directive.group(1).split(","))
    return bytes(values)


def path_actor(
    *,
    actor_class: int = ao.CLASS_GUARD,
    state: int = ao.STATE_GRD_PATH1,
    x: int | None = None,
    y: int | None = None,
    tile_x: int = 11,
    tile_y: int = 10,
    direction: int = ao.DIR_EAST,
    distance: int = ao.TILE_GLOBAL,
    ticcount: int = 0,
    speed: int = 512,
    flags: int = ao.FLAG_SHOOTABLE,
) -> ao.Actor:
    return ao.Actor(
        x=ao.fixed(10) if x is None else x,
        y=ao.fixed(10) if y is None else y,
        tile_x=tile_x,
        tile_y=tile_y,
        direction=direction,
        actor_class=actor_class,
        state=state,
        distance=distance,
        ticcount=ticcount,
        speed=speed,
        flags=flags,
    )


class ClockAndStateContractTests(unittest.TestCase):
    def test_shared_clock_is_exact_223_original_tics(self) -> None:
        world = ao.World()
        self.assertEqual(world.step(9), [2, 2, 3] * 3)
        self.assertEqual(world.actor_clock_phase, 0)
        self.assertEqual(world.door_clock_phase, 0)
        self.assertEqual(sum([2, 2, 3] * 10), 70)

    def test_e1l1_medium_deterministic_initial_phases(self) -> None:
        # Zero-duration map actors occur between the six patrols but consume no
        # random bytes.  This mixed state sequence pins that omission too.
        states = (
            ao.STATE_GRD_STAND,
            ao.STATE_GRD_PATH1,
            ao.STATE_GRD_DEAD,
            ao.STATE_GRD_PATH1,
            ao.STATE_DOG_PATH1,
            ao.STATE_DOG_PATH1,
            ao.STATE_GRD_STAND,
            ao.STATE_GRD_PATH1,
            ao.STATE_GRD_PATH1,
        )
        self.assertEqual(
            ao.initial_ticcounts(states, ao.E1L1_MEDIUM_RANDOM_PREFIX),
            [0, 8, 0, 9, 0, 2, 0, 1, 9],
        )
        self.assertEqual(ao.E1L1_MEDIUM_PATROL_PHASES, (8, 9, 0, 2, 1, 9))

    def test_all_path_chains_keep_original_timing_and_think_pattern(self) -> None:
        starts = (
            ao.STATE_GRD_PATH1,
            ao.STATE_DOG_PATH1,
            ao.STATE_OFC_PATH1,
            ao.STATE_MUT_PATH1,
            ao.STATE_SS_PATH1,
        )
        pause1 = (22, 27, 32, 37, 42)
        path2 = (23, 28, 33, 38, 43)
        path3 = (24, 29, 34, 39, 44)
        pause3 = (25, 30, 35, 40, 45)
        path4 = (26, 31, 36, 41, 46)
        for ids in zip(starts, pause1, path2, path3, pause3, path4):
            states = [ao.STATES[state_id] for state_id in ids]
            self.assertEqual([state.tictime for state in states], [20, 5, 15, 20, 5, 15])
            self.assertEqual(
                [state.think for state in states],
                [ao.THINK_PATH, ao.THINK_NONE, ao.THINK_PATH,
                 ao.THINK_PATH, ao.THINK_NONE, ao.THINK_PATH],
            )
            self.assertEqual([state.next_state for state in states], list(ids[1:]) + [ids[0]])
            self.assertEqual(states[0].shape, states[1].shape)
            self.assertEqual(states[3].shape, states[4].shape)

    def test_actor_record_is_still_exactly_39_bytes(self) -> None:
        actor = path_actor(ticcount=8)
        actor.temp1, actor.temp2, actor.temp3 = -2, 300, -32768
        actor.next_slot, actor.previous_slot = 149, 1
        payload = actor.to_bytes()
        self.assertEqual(len(payload), 39)
        self.assertEqual(ao.Actor.from_bytes(payload), actor)

    def test_zero_ticcount_is_the_original_permanent_latch(self) -> None:
        world = ao.World()
        actor = path_actor(ticcount=0)
        world.add_actor(1, actor)
        self.assertEqual(world.step(3), [2, 2, 3])
        self.assertEqual((actor.state, actor.ticcount), (ao.STATE_GRD_PATH1, 0))
        self.assertEqual(actor.x, ao.fixed(10) + 512 * 7)
        self.assertEqual(actor.distance, ao.TILE_GLOBAL - 512 * 7)

    def test_same_shape_pause_transition_is_not_render_dirty(self) -> None:
        world = ao.World()
        actor = path_actor(ticcount=2, speed=0)
        world.add_actor(1, actor)
        world.step()
        self.assertEqual((actor.state, actor.ticcount), (ao.STATE_GRD_PATH1S, 5))
        self.assertNotIn(1, world.dirty_actors)

    def test_pause_to_new_shape_is_render_dirty(self) -> None:
        world = ao.World()
        actor = path_actor(state=ao.STATE_GRD_PATH1S, ticcount=2, speed=0)
        world.add_actor(1, actor)
        world.step()
        self.assertEqual((actor.state, actor.ticcount), (ao.STATE_GRD_PATH2, 15))
        self.assertIn(1, world.dirty_actors)


class PathMovementTests(unittest.TestCase):
    def test_dog_residual_crosses_center_and_obeys_new_arrow(self) -> None:
        world = ao.World()
        world.set_path(11, 10, ao.DIR_NORTH)
        actor = path_actor(
            actor_class=ao.CLASS_DOG,
            state=ao.STATE_DOG_PATH1,
            x=ao.fixed(11) - 512,
            tile_x=11,
            tile_y=10,
            direction=ao.DIR_EAST,
            distance=512,
            speed=1500,
        )
        world.add_actor(7, actor)
        world.step()  # 2 tics -> 3000; 512 to center, 2488 residual north
        self.assertEqual((actor.tile_x, actor.tile_y, actor.direction), (11, 9, ao.DIR_NORTH))
        self.assertEqual((actor.x, actor.y), (ao.fixed(11), ao.fixed(10) - 2488))
        self.assertEqual(actor.distance, ao.TILE_GLOBAL - 2488)
        self.assertEqual(world.actorat[10 * 64 + 11], 0)
        self.assertEqual(world.actorat[9 * 64 + 11], 7)

    def _door_selection_world(self, actor_class: int, action: int) -> tuple[ao.World, ao.Actor]:
        world = ao.World()
        world.set_path(10, 10, ao.DIR_EAST)
        world.install_door(0, ao.Door(11, 10, action=action,
                                     position=0xFFFF if action == ao.DOOR_OPEN else 0))
        state = ao.STATE_DOG_PATH1 if actor_class == ao.CLASS_DOG else ao.STATE_GRD_PATH1
        actor = path_actor(
            actor_class=actor_class,
            state=state,
            tile_x=10,
            tile_y=10,
            direction=ao.DIR_NODIR,
            distance=0,
            speed=1500 if actor_class == ao.CLASS_DOG else 512,
        )
        world.add_actor(1, actor)
        return world, actor

    def test_dog_rejects_nonopen_door_but_crosses_fully_open_door(self) -> None:
        closed_world, closed_dog = self._door_selection_world(ao.CLASS_DOG, ao.DOOR_CLOSED)
        closed_world.step()
        self.assertEqual((closed_dog.tile_x, closed_dog.tile_y), (10, 10))
        self.assertEqual(closed_dog.direction, ao.DIR_NODIR)
        self.assertEqual(closed_world.doors[0].action, ao.DOOR_CLOSED)

        open_world, open_dog = self._door_selection_world(ao.CLASS_DOG, ao.DOOR_OPEN)
        open_world.step()
        self.assertEqual((open_dog.tile_x, open_dog.tile_y), (11, 10))
        self.assertEqual(open_dog.direction, ao.DIR_EAST)
        self.assertEqual(open_dog.x, ao.fixed(10) + 3000)

    def test_guard_reserves_closed_door_and_waits_while_opening_it(self) -> None:
        world, guard = self._door_selection_world(ao.CLASS_GUARD, ao.DOOR_CLOSED)
        world.step()
        self.assertEqual((guard.x, guard.y), (ao.fixed(10), ao.fixed(10)))
        self.assertEqual((guard.tile_x, guard.tile_y), (11, 10))
        self.assertEqual(guard.distance, -1)  # door zero must encode as -1
        self.assertEqual(world.doors[0].action, ao.DOOR_OPENING)
        self.assertEqual(world.actorat[10 * 64 + 10], 0)
        self.assertEqual(world.actorat[10 * 64 + 11], 1)

    def test_door_opens_before_waiting_guard_runs(self) -> None:
        world = ao.World()
        # 0xf6aa + first 30-Hz door delta 0x0955 == 0xffff exactly.
        world.install_door(0, ao.Door(11, 10, action=ao.DOOR_OPENING, position=0xF6AA))
        guard = path_actor(tile_x=11, tile_y=10, direction=ao.DIR_EAST, distance=-1)
        world.add_actor(1, guard)
        world.step()
        door = world.doors[0]
        self.assertEqual((door.action, door.position, door.timer), (ao.DOOR_OPEN, 0xFFFF, 0))
        self.assertEqual(guard.x, ao.fixed(10) + 1024)
        self.assertEqual(guard.distance, ao.TILE_GLOBAL - 1024)

    def test_noncanonical_negative_wait_does_not_alias_door_zero(self) -> None:
        world = ao.World()
        world.install_door(0, ao.Door(11, 10, action=ao.DOOR_CLOSED))
        guard = path_actor(
            tile_x=11,
            tile_y=10,
            direction=ao.DIR_EAST,
            distance=-257,
        )
        world.add_actor(1, guard)

        world.step()

        self.assertEqual(guard.direction, ao.DIR_NODIR)
        self.assertEqual(guard.distance, -257)
        self.assertEqual(world.doors[0].action, ao.DOOR_CLOSED)
        self.assertEqual(world.doors[0].timer, 0)
        self.assertEqual(world.actorat[10 * 64 + 11], 1)
        # EAST and NODIR/angle-zero resolve to the same wire-facing value.
        self.assertNotIn(1, world.dirty_actors)
        self.assertNotIn(0, world.dirty_doors)

    def test_cardinal_and_diagonal_trywalk_obstacles(self) -> None:
        for obstacle in ("wall", "static"):
            with self.subTest(obstacle=obstacle):
                world = ao.World()
                guard = path_actor(tile_x=10, tile_y=10, direction=ao.DIR_EAST)
                if obstacle == "wall":
                    world.tilemap[10 * 64 + 11] = 1
                else:
                    world.set_static_blocked(11, 10)
                self.assertFalse(world.try_walk(guard))

        world = ao.World()
        diagonal = path_actor(tile_x=10, tile_y=10, direction=ao.DIR_NORTHEAST)
        world.tilemap[10 * 64 + 11] = 1  # clear target, blocked east shoulder
        self.assertFalse(world.try_walk(diagonal))

    def test_shootable_actor_blocks_but_nonshootable_actor_is_passable(self) -> None:
        for flags, expected in ((ao.FLAG_SHOOTABLE, False), (0, True)):
            with self.subTest(flags=flags):
                world = ao.World()
                mover = path_actor(tile_x=10, tile_y=10, direction=ao.DIR_EAST)
                occupant = path_actor(tile_x=11, tile_y=10, flags=flags, speed=0)
                world.add_actor(1, mover)
                world.add_actor(2, occupant)
                self.assertEqual(world.try_walk(mover), expected)


class PlayerAndOccupancyTests(unittest.TestCase):
    def test_player_overlap_is_inclusive_and_does_not_consume_distance(self) -> None:
        for extra, moved in ((0, False), (1, True)):
            with self.subTest(extra=extra):
                world = ao.World()
                actor = path_actor(tile_x=10, tile_y=10, direction=ao.DIR_EAST)
                world.player_x = actor.x + 1024 + ao.MIN_ACTOR_DISTANCE + extra
                world.player_y = actor.y
                world.add_actor(1, actor)
                world.step()
                self.assertEqual(actor.x, ao.fixed(10) + (1024 if moved else 0))
                self.assertEqual(
                    actor.distance,
                    ao.TILE_GLOBAL - (1024 if moved else 0),
                )

    def test_nevermark_and_nonmark_occupancy_rules(self) -> None:
        never_world = ao.World()
        never = path_actor(flags=ao.FLAG_SHOOTABLE | ao.FLAG_NEVERMARK)
        never_world.add_actor(1, never)
        never_world.step()
        self.assertNotIn(1, never_world.actorat)

        nonmark_world = ao.World()
        nonmark = path_actor(
            state=ao.STATE_GRD_STAND,
            tile_x=10,
            tile_y=10,
            flags=ao.FLAG_NONMARK,
            speed=0,
        )
        nonmark_world.add_actor(1, nonmark, claim=False)
        nonmark_world.actorat[10 * 64 + 10] = 2
        nonmark_world.step()
        self.assertEqual(nonmark_world.actorat[10 * 64 + 10], 2)

    def test_invalid_actorat_id_fails_closed(self) -> None:
        world = ao.World()
        actor = path_actor(tile_x=10, tile_y=10, direction=ao.DIR_EAST)
        world.actorat[10 * 64 + 11] = 149
        self.assertFalse(world.try_walk(actor))


class RealE1L1AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_text = FIXTURE.read_text()
        cls.actor_bytes = parse_label_bytes(
            cls.fixture_text, "w3d_fixture_initial_actors", "w3d_fixture_initial_actors_end"
        )
        cls.door_bytes = parse_label_bytes(
            cls.fixture_text, "w3d_fixture_initial_doors", "w3d_fixture_initial_doors_end"
        )
        cls.tilemap = parse_label_bytes(
            cls.fixture_text, "w3d_fixture_tilemap", "w3d_fixture_tilemap_end"
        )
        cls.paths = parse_label_bytes(
            cls.fixture_text, "w3d_fixture_path_directions", "w3d_fixture_path_directions_end"
        )
        cls.areas = parse_label_bytes(
            cls.fixture_text, "w3d_fixture_area_map", "w3d_fixture_area_map_end"
        )

    def test_fixture_has_exact_medium_population_and_timed_order(self) -> None:
        self.assertEqual(len(self.actor_bytes), 21 * ao.ACTOR_RECORD.size)
        actors = [
            ao.Actor.from_bytes(self.actor_bytes[offset:offset + ao.ACTOR_RECORD.size])
            for offset in range(0, len(self.actor_bytes), ao.ACTOR_RECORD.size)
        ]
        timed_states = [actor.state for actor in actors if ao.STATES[actor.state].tictime]
        self.assertEqual(
            timed_states,
            [ao.STATE_GRD_PATH1, ao.STATE_GRD_PATH1,
             ao.STATE_DOG_PATH1, ao.STATE_DOG_PATH1,
             ao.STATE_GRD_PATH1, ao.STATE_DOG_PATH1],
        )
        self.assertEqual(
            ao.initial_ticcounts(timed_states, ao.E1L1_MEDIUM_RANDOM_PREFIX),
            [8, 9, 0, 2, 1, 9],
        )

    def test_real_slot11_reaches_and_crosses_door8_without_drift(self) -> None:
        actor = ao.Actor.from_bytes(self.actor_bytes[10 * 39:11 * 39])
        self.assertEqual(
            (actor.x, actor.y, actor.tile_x, actor.tile_y, actor.area,
             actor.direction, actor.state, actor.distance, actor.speed),
            (0x078000, 0x218000, 6, 33, 5, ao.DIR_WEST,
             ao.STATE_GRD_PATH1, ao.TILE_GLOBAL, 512),
        )
        actor.ticcount = 8  # exact first timed phase, independent of fixture regeneration
        world = ao.World(
            tilemap=bytearray(self.tilemap),
            path_directions=bytearray(self.paths),
            area_map=bytearray(self.areas),
        )
        for index in range(len(self.door_bytes) // 10):
            start = index * 10
            world.doors[index] = ao.Door.from_fixture_bytes(self.door_bytes[start:start + 10])
        world.add_actor(11, actor)

        world.step(63)
        door = world.doors[8]
        self.assertEqual(
            (actor.x, actor.y, actor.tile_x, actor.tile_y, actor.distance,
             actor.state, actor.ticcount),
            (0x068000, 0x218000, 5, 33, -9,
             ao.STATE_GRD_PATH4, 1),
        )
        self.assertEqual((door.action, door.position), (ao.DOOR_OPENING, 0))
        self.assertEqual(world.actorat[33 * 64 + 5], 11)

        world.step(28)  # frame 91: door reaches open, actor is in a no-think pause
        self.assertEqual((door.action, door.position), (ao.DOOR_OPEN, 0xFFFF))
        self.assertEqual((actor.x, actor.distance, actor.state, actor.ticcount),
                         (0x068000, -9, ao.STATE_GRD_PATH3S, 1))

        world.step()  # frame 92: PATH4 thinks and immediately enters the open door
        self.assertEqual(
            (actor.x, actor.y, actor.tile_x, actor.tile_y, actor.distance,
             actor.state, actor.ticcount),
            (0x067C00, 0x218000, 5, 33, 0xFC00,
             ao.STATE_GRD_PATH4, 14),
        )
        self.assertEqual((world.actor_clock_phase, world.door_clock_phase), (2, 2))


if __name__ == "__main__":
    unittest.main()
