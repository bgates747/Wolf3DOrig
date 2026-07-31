#!/usr/bin/env python3
"""Directed host regression for :mod:`chase_oracle`."""

from __future__ import annotations

import unittest

import chase_oracle as ch


def actor(**changes: int) -> ch.Actor:
    values = {
        "x": ch.fixed(10),
        "y": ch.fixed(10),
        "tile_x": 10,
        "tile_y": 10,
        "area": 0,
        "direction": ch.DIR_NODIR,
        "actor_class": ch.CLASS_GUARD,
        "flags": ch.FLAG_SHOOTABLE,
        "distance": 0,
        "speed": 512,
    }
    values.update(changes)
    return ch.Actor(**values)


def east_leg(**changes: int) -> ch.Actor:
    values = {
        "x": ch.fixed(10),
        "y": ch.fixed(10),
        "tile_x": 11,
        "tile_y": 10,
        "area": 0,
        "direction": ch.DIR_EAST,
        "actor_class": ch.CLASS_GUARD,
        "flags": ch.FLAG_SHOOTABLE,
        "distance": ch.TILE_GLOBAL,
        "speed": 512,
    }
    values.update(changes)
    return ch.Actor(**values)


def block_neighbors_except(
    world: ch.World,
    subject: ch.Actor,
    allowed: set[int] | frozenset[int] = frozenset(),
) -> None:
    for direction, (dx, dy) in enumerate(ch.DIR_DELTAS):
        if direction not in allowed:
            world.set_wall(subject.tile_x + dx, subject.tile_y + dy)


def no_line(_actor: ch.Actor, _world: ch.World) -> bool:
    return False


def clear_line(_actor: ch.Actor, _world: ch.World) -> bool:
    return True


def pose(subject: ch.Actor) -> tuple[int, ...]:
    return (
        subject.x,
        subject.y,
        subject.tile_x,
        subject.tile_y,
        subject.area,
        subject.direction,
        subject.actor_class,
        subject.flags,
        subject.distance,
        subject.speed,
    )


class ClockTests(unittest.TestCase):
    def test_shared_clock_is_exact_repeating_223_original_tics(self) -> None:
        world = ch.World()
        self.assertEqual([world.next_tics() for _ in range(9)], [2, 2, 3] * 3)
        self.assertEqual(world.clock_phase, 0)


class DirectionSelectionTests(unittest.TestCase):
    def test_chase_prefers_larger_axis_without_rng(self) -> None:
        cases = (
            (ch.fixed(14), ch.fixed(12), ch.DIR_EAST, (11, 10)),
            (ch.fixed(12), ch.fixed(15), ch.DIR_SOUTH, (10, 11)),
        )
        for player_x, player_y, expected_dir, expected_tile in cases:
            with self.subTest(expected_dir=expected_dir):
                world = ch.World(player_x=player_x, player_y=player_y)
                subject = actor()
                rng = ch.SequenceRng([])
                self.assertTrue(world.select_chase_dir(subject, rng))
                self.assertEqual(subject.direction, expected_dir)
                self.assertEqual((subject.tile_x, subject.tile_y), expected_tile)
                self.assertEqual((rng.draws, world.try_log), (0, [expected_dir]))

    def test_chase_tries_old_direction_before_rng_fallback(self) -> None:
        world = ch.World(player_x=ch.fixed(14), player_y=ch.fixed(10))
        subject = actor(direction=ch.DIR_NORTH)
        world.set_wall(11, 10)
        rng = ch.SequenceRng([])
        self.assertTrue(world.select_chase_dir(subject, rng))
        self.assertEqual(subject.direction, ch.DIR_NORTH)
        self.assertEqual((rng.draws, world.try_log), (0, [ch.DIR_EAST, ch.DIR_NORTH]))

    def test_chase_suppresses_reversal_until_last_resort(self) -> None:
        world = ch.World(player_x=ch.fixed(14), player_y=ch.fixed(10))
        subject = actor(direction=ch.DIR_WEST)
        block_neighbors_except(world, subject, {ch.DIR_EAST})
        rng = ch.SequenceRng([200])
        self.assertTrue(world.select_chase_dir(subject, rng))
        self.assertEqual(subject.direction, ch.DIR_EAST)
        self.assertEqual(
            world.try_log,
            [
                ch.DIR_WEST,
                ch.DIR_NORTH,
                ch.DIR_NORTHWEST,
                ch.DIR_WEST,
                ch.DIR_EAST,
            ],
        )
        self.assertEqual(rng.history, [200])

    def test_chase_fallback_has_source_enum_order_and_strict_threshold(self) -> None:
        for roll, expected_log in (
            (
                129,
                [ch.DIR_EAST, ch.DIR_NORTH, ch.DIR_NORTHWEST, ch.DIR_WEST],
            ),
            (128, [ch.DIR_EAST, ch.DIR_WEST]),
        ):
            with self.subTest(roll=roll):
                world = ch.World(player_x=ch.fixed(14), player_y=ch.fixed(10))
                subject = actor()
                world.set_wall(11, 10)  # direct east
                world.set_wall(10, 9)   # north and NW's north shoulder
                rng = ch.SequenceRng([roll])
                self.assertTrue(world.select_chase_dir(subject, rng))
                self.assertEqual(subject.direction, ch.DIR_WEST)
                self.assertEqual(world.try_log, expected_log)
                self.assertEqual(rng.history, [roll])

    def test_chase_trapped_result_consumes_one_fallback_byte(self) -> None:
        world = ch.World(player_x=ch.fixed(14), player_y=ch.fixed(10))
        subject = actor()
        block_neighbors_except(world, subject)
        rng = ch.SequenceRng([200])
        self.assertFalse(world.select_chase_dir(subject, rng))
        self.assertEqual(subject.direction, ch.DIR_NODIR)
        self.assertEqual(
            world.try_log,
            [ch.DIR_EAST, ch.DIR_NORTH, ch.DIR_NORTHWEST, ch.DIR_WEST],
        )
        self.assertEqual(rng.draws, 1)

    def test_dodge_symmetric_diagonal_survives_vertical_first_swap(self) -> None:
        world = ch.World(player_x=ch.fixed(14), player_y=ch.fixed(8))
        subject = actor()
        rng = ch.SequenceRng([200])
        self.assertTrue(world.select_dodge_dir(subject, rng))
        self.assertEqual(subject.direction, ch.DIR_NORTHEAST)
        self.assertEqual((subject.tile_x, subject.tile_y), (11, 9))
        self.assertEqual((world.try_log, rng.history), ([ch.DIR_NORTHEAST], [200]))

    def test_dodge_symmetric_table_covers_both_southern_diagonals(self) -> None:
        for player_x, expected in (
            (ch.fixed(14), ch.DIR_SOUTHEAST),
            (ch.fixed(6), ch.DIR_SOUTHWEST),
        ):
            with self.subTest(expected=expected):
                world = ch.World(player_x=player_x, player_y=ch.fixed(12))
                subject = actor()
                rng = ch.SequenceRng([200])
                self.assertTrue(world.select_dodge_dir(subject, rng))
                self.assertEqual(subject.direction, expected)
                self.assertEqual(rng.draws, 1)

    def test_dodge_random_swap_is_strictly_below_128(self) -> None:
        for roll, expected in ((127, ch.DIR_NORTH), (128, ch.DIR_EAST)):
            with self.subTest(roll=roll):
                world = ch.World(player_x=ch.fixed(12), player_y=ch.fixed(8))
                subject = actor()
                world.set_wall(11, 9)  # reject the common NE diagonal only
                rng = ch.SequenceRng([roll])
                self.assertTrue(world.select_dodge_dir(subject, rng))
                self.assertEqual(subject.direction, expected)
                self.assertEqual(world.try_log, [ch.DIR_NORTHEAST, expected])
                self.assertEqual(rng.history, [roll])

    def test_firstattack_clears_flag_and_allows_early_reversal(self) -> None:
        expected = (
            (0, [ch.DIR_NORTHEAST, ch.DIR_NORTH, ch.DIR_SOUTH, ch.DIR_WEST, ch.DIR_EAST]),
            (ch.FLAG_FIRSTATTACK, [ch.DIR_NORTHEAST, ch.DIR_NORTH, ch.DIR_EAST]),
        )
        for first_flag, expected_log in expected:
            with self.subTest(first_flag=first_flag):
                world = ch.World(player_x=ch.fixed(14), player_y=ch.fixed(10))
                subject = actor(
                    direction=ch.DIR_WEST,
                    flags=ch.FLAG_SHOOTABLE | first_flag,
                )
                block_neighbors_except(world, subject, {ch.DIR_EAST})
                rng = ch.SequenceRng([200])
                self.assertTrue(world.select_dodge_dir(subject, rng))
                self.assertEqual(subject.direction, ch.DIR_EAST)
                self.assertEqual(world.try_log, expected_log)
                self.assertFalse(subject.flags & ch.FLAG_FIRSTATTACK)
                self.assertEqual(rng.draws, 1)

    def test_dodge_zero_deltas_keep_source_west_north_bias(self) -> None:
        world = ch.World(player_x=ch.fixed(10), player_y=ch.fixed(10))
        subject = actor()
        rng = ch.SequenceRng([200])
        self.assertTrue(world.select_dodge_dir(subject, rng))
        self.assertEqual(subject.direction, ch.DIR_NORTHWEST)
        self.assertEqual(world.try_log, [ch.DIR_NORTHWEST])
        self.assertEqual(rng.draws, 1)


class TryWalkCompositionTests(unittest.TestCase):
    def test_shootable_actor_blocks_but_nonshootable_actor_is_passable(self) -> None:
        for flags, expected in ((ch.FLAG_SHOOTABLE, False), (0, True)):
            with self.subTest(flags=flags):
                world = ch.World()
                blocker = actor(tile_x=11, flags=flags)
                world.add_actor(2, blocker)
                subject = actor(direction=ch.DIR_EAST)
                self.assertEqual(world.try_walk(subject), expected)
                self.assertEqual(
                    (subject.tile_x, subject.tile_y),
                    (11, 10) if expected else (10, 10),
                )

        stale_world = ch.World()
        stale_world.actorat[stale_world.index(11, 10)] = 149
        stale_subject = actor(direction=ch.DIR_EAST)
        self.assertFalse(stale_world.try_walk(stale_subject))
        self.assertEqual((stale_subject.tile_x, stale_subject.tile_y), (10, 10))

    def test_diagonal_requires_both_orthogonal_corner_cells(self) -> None:
        for obstruction in ("wall", "static"):
            with self.subTest(obstruction=obstruction):
                world = ch.World()
                subject = actor(direction=ch.DIR_NORTHEAST)
                if obstruction == "wall":
                    world.set_wall(11, 10)
                else:
                    world.set_static_blocked(11, 10)
                self.assertFalse(world.try_walk(subject))
                self.assertEqual((subject.tile_x, subject.tile_y), (10, 10))
                self.assertEqual(subject.distance, 0)

    def test_ordinary_closed_door_commits_wait_but_dog_rejects_it(self) -> None:
        ordinary_world = ch.World()
        ordinary_world.install_door(3, ch.Door(11, 10, action=ch.DOOR_CLOSED))
        ordinary = actor(direction=ch.DIR_EAST)
        self.assertTrue(ordinary_world.try_walk(ordinary))
        self.assertEqual((ordinary.tile_x, ordinary.tile_y, ordinary.distance), (11, 10, -4))
        self.assertEqual(ordinary_world.doors[3].action, ch.DOOR_OPENING)
        self.assertEqual(ordinary_world.door_request_log, [3])

        dog_world = ch.World()
        dog_world.install_door(3, ch.Door(11, 10, action=ch.DOOR_CLOSED))
        dog = actor(direction=ch.DIR_EAST, actor_class=ch.CLASS_DOG)
        self.assertFalse(dog_world.try_walk(dog))
        self.assertEqual((dog.tile_x, dog.tile_y, dog.distance), (10, 10, 0))
        self.assertEqual(dog_world.doors[3].action, ch.DOOR_CLOSED)
        self.assertEqual(dog_world.door_request_log, [])

    def test_dog_can_enter_only_a_fully_open_door(self) -> None:
        world = ch.World()
        world.install_door(6, ch.Door(11, 10, action=ch.DOOR_OPEN))
        subject = actor(direction=ch.DIR_EAST, actor_class=ch.CLASS_DOG)
        self.assertTrue(world.try_walk(subject))
        self.assertEqual((subject.tile_x, subject.tile_y, subject.distance), (11, 10, ch.TILE_GLOBAL))
        self.assertEqual(world.door_request_log, [])

    def test_area_update_accepts_only_valid_port_area_ids(self) -> None:
        for destination_area, expected_area in ((5, 5), (ch.NUM_AREAS, 7), (ch.AREA_NONE, 7)):
            with self.subTest(destination_area=destination_area):
                world = ch.World()
                world.area_map[world.index(11, 10)] = destination_area
                subject = actor(direction=ch.DIR_EAST, area=7)
                self.assertTrue(world.try_walk(subject))
                self.assertEqual(subject.area, expected_area)

    def test_closing_door_request_reverses_it_to_opening(self) -> None:
        world = ch.World()
        world.install_door(9, ch.Door(11, 10, action=ch.DOOR_CLOSING, timer=77))
        self.assertTrue(world.request_open_door(9))
        self.assertEqual((world.doors[9].action, world.doors[9].timer), (ch.DOOR_OPENING, 0))


class OrdinaryChaseTests(unittest.TestCase):
    def _ranged_world(self, roll: int) -> tuple[ch.World, ch.Actor, ch.SequenceRng]:
        world = ch.World(player_x=ch.fixed(15), player_y=ch.fixed(10))
        subject = east_leg()
        world.add_actor(1, subject)
        return world, subject, ch.SequenceRng([roll])

    def test_scaled_attack_roll_uses_strict_less_than_boundary(self) -> None:
        requested_world, requested_actor, requested_rng = self._ranged_world(7)
        requested_pose = pose(requested_actor)
        requested = requested_world.chase_step(
            1, original_tics=2, rng=requested_rng, line_of_sight=clear_line
        )
        self.assertEqual(requested.attack_request, ch.AttackRequest.RANGED)
        self.assertEqual((requested.attack_chance, requested.attack_roll), (8, 7))
        self.assertEqual(pose(requested_actor), requested_pose)
        self.assertEqual(requested_rng.history, [7])

        failed_world, failed_actor, failed_rng = self._ranged_world(8)
        old_x = failed_actor.x
        failed = failed_world.chase_step(
            1, original_tics=2, rng=failed_rng, line_of_sight=clear_line
        )
        self.assertEqual(failed.attack_request, ch.AttackRequest.NONE)
        self.assertEqual((failed.attack_chance, failed.attack_roll), (8, 8))
        self.assertTrue(failed.moved)
        self.assertEqual(failed_actor.x, old_x + 1024)
        self.assertEqual(failed_rng.history, [8])

    def test_close_special_chance_300_still_consumes_one_byte(self) -> None:
        world = ch.World(player_x=ch.fixed(12), player_y=ch.fixed(10))
        subject = east_leg(distance=0x3FFF)
        world.add_actor(1, subject)
        rng = ch.SequenceRng([255])
        result = world.chase_step(
            1, original_tics=2, rng=rng, line_of_sight=clear_line
        )
        self.assertEqual(result.attack_request, ch.AttackRequest.RANGED)
        self.assertEqual((result.attack_chance, result.attack_roll), (300, 255))
        self.assertEqual(rng.history, [255])

    def test_exact_quarter_tile_uses_scaled_chance_not_close_special(self) -> None:
        for roll, expected in ((31, ch.AttackRequest.RANGED), (32, ch.AttackRequest.NONE)):
            with self.subTest(roll=roll):
                world = ch.World(player_x=ch.fixed(12), player_y=ch.fixed(10))
                subject = east_leg(distance=0x4000, speed=0)
                world.add_actor(1, subject)
                rng = ch.SequenceRng([roll])
                result = world.chase_step(
                    1, original_tics=2, rng=rng, line_of_sight=clear_line
                )
                self.assertEqual(result.attack_request, expected)
                self.assertEqual(result.attack_chance, 32)
                self.assertEqual(rng.history, [roll])

    def test_negative_door_wait_also_matches_source_close_comparison(self) -> None:
        world = ch.World(player_x=ch.fixed(12), player_y=ch.fixed(10))
        subject = east_leg(distance=-1)
        world.add_actor(1, subject)
        rng = ch.SequenceRng([255])
        result = world.chase_step(
            1, original_tics=2, rng=rng, line_of_sight=clear_line
        )
        self.assertEqual(result.attack_request, ch.AttackRequest.RANGED)
        self.assertEqual(result.attack_chance, 300)
        self.assertEqual(world.door_request_log, [])

    def test_blocked_line_consumes_no_attack_rng(self) -> None:
        world = ch.World(player_x=ch.fixed(20), player_y=ch.fixed(10))
        subject = east_leg()
        world.add_actor(1, subject)
        rng = ch.SequenceRng([])
        old_x = subject.x
        result = world.chase_step(
            1, original_tics=2, rng=rng, line_of_sight=no_line
        )
        self.assertTrue(result.moved)
        self.assertEqual(subject.x, old_x + 1024)
        self.assertEqual(rng.draws, 0)

    def test_failed_attack_with_nodir_consumes_dodge_rng_and_firstattack(self) -> None:
        world = ch.World(player_x=ch.fixed(14), player_y=ch.fixed(10))
        subject = actor(flags=ch.FLAG_SHOOTABLE | ch.FLAG_FIRSTATTACK, speed=0)
        world.add_actor(1, subject)
        rng = ch.SequenceRng([8, 200])
        result = world.chase_step(
            1, original_tics=2, rng=rng, line_of_sight=clear_line
        )
        self.assertEqual(result.attack_request, ch.AttackRequest.NONE)
        self.assertEqual((result.attack_chance, result.attack_roll), (8, 8))
        self.assertEqual(subject.direction, ch.DIR_NORTHEAST)
        self.assertEqual((subject.tile_x, subject.tile_y), (11, 9))
        self.assertFalse(subject.flags & ch.FLAG_FIRSTATTACK)
        self.assertEqual(rng.history, [8, 200])

    def test_failed_attack_keeps_dodge_mode_at_center_crossing(self) -> None:
        world = ch.World(player_x=ch.fixed(15), player_y=ch.fixed(10))
        subject = east_leg(x=ch.fixed(11) - 1024, distance=1024)
        world.add_actor(1, subject)
        rng = ch.SequenceRng([8, 200])
        result = world.chase_step(
            1, original_tics=2, rng=rng, line_of_sight=clear_line
        )
        self.assertEqual(result.attack_request, ch.AttackRequest.NONE)
        self.assertEqual((subject.x, subject.y), (ch.fixed(11), ch.fixed(10)))
        self.assertEqual(subject.direction, ch.DIR_NORTHEAST)
        self.assertEqual((subject.tile_x, subject.tile_y), (12, 9))
        self.assertEqual(rng.history, [8, 200])

    def test_unlatched_repeated_ranged_requests_deliberately_pause_pose(self) -> None:
        world = ch.World(player_x=ch.fixed(12), player_y=ch.fixed(10))
        subject = east_leg(distance=0x3FFF)
        world.add_actor(1, subject)
        original_pose = pose(subject)
        rng = ch.SequenceRng([255, 255])
        for _ in range(2):
            result = world.chase_step(
                1, original_tics=2, rng=rng, line_of_sight=clear_line
            )
            self.assertEqual(result.attack_request, ch.AttackRequest.RANGED)
            self.assertEqual(pose(subject), original_pose)
        self.assertEqual(rng.history, [255, 255])

    def test_corrupt_class_or_direction_fails_before_line_rng_or_mutation(self) -> None:
        def forbidden_line(_actor: ch.Actor, _world: ch.World) -> bool:
            raise AssertionError("corrupt input reached line trace")

        cases = (
            east_leg(actor_class=ch.CLASS_DOG),
            east_leg(direction=9),
        )
        for subject in cases:
            with self.subTest(actor_class=subject.actor_class, direction=subject.direction):
                world = ch.World()
                world.add_actor(1, subject)
                before = pose(subject)
                rng = ch.SequenceRng([])
                result = world.chase_step(
                    1, original_tics=2, rng=rng, line_of_sight=forbidden_line
                )
                self.assertEqual(result.attack_request, ch.AttackRequest.CORRUPT)
                self.assertEqual(pose(subject), before)
                self.assertEqual(rng.draws, 0)

    def test_223_budget_accumulates_without_hidden_rng(self) -> None:
        world = ch.World(player_x=ch.fixed(30), player_y=ch.fixed(10))
        subject = east_leg()
        world.add_actor(1, subject)
        start_x = subject.x
        rng = ch.SequenceRng([])
        for _ in range(3):
            result = world.chase_step(
                1,
                original_tics=world.next_tics(),
                rng=rng,
                line_of_sight=no_line,
            )
            self.assertTrue(result.moved)
        self.assertEqual(subject.x, start_x + 3584)
        self.assertEqual(subject.distance, ch.TILE_GLOBAL - 3584)
        self.assertEqual(rng.draws, 0)

    def test_residual_budget_crosses_center_and_continues_on_new_leg(self) -> None:
        world = ch.World(player_x=ch.fixed(11), player_y=ch.fixed(5))
        subject = east_leg(x=ch.fixed(11) - 512, distance=512, speed=1500)
        world.add_actor(1, subject)
        result = world.chase_step(
            1, original_tics=2, rng=ch.SequenceRng([]), line_of_sight=no_line
        )
        residual = 3000 - 512
        self.assertTrue(result.moved)
        self.assertEqual(subject.direction, ch.DIR_NORTH)
        self.assertEqual((subject.tile_x, subject.tile_y), (11, 9))
        self.assertEqual((subject.x, subject.y), (ch.fixed(11), ch.fixed(10) - residual))
        self.assertEqual(subject.distance, ch.TILE_GLOBAL - residual)

    def test_exact_budget_equality_still_selects_and_reserves_next_leg(self) -> None:
        world = ch.World(player_x=ch.fixed(11), player_y=ch.fixed(5))
        subject = east_leg(x=ch.fixed(11) - 1024, distance=1024)
        world.add_actor(1, subject)
        result = world.chase_step(
            1, original_tics=2, rng=ch.SequenceRng([]), line_of_sight=no_line
        )
        self.assertTrue(result.moved)
        self.assertEqual((subject.x, subject.y), (ch.fixed(11), ch.fixed(10)))
        self.assertEqual((subject.tile_x, subject.tile_y), (11, 9))
        self.assertEqual((subject.direction, subject.distance), (ch.DIR_NORTH, ch.TILE_GLOBAL))
        self.assertEqual(world.actorat[world.index(11, 9)], 1)
        self.assertEqual(world.actorat[world.index(11, 10)], 0)

    def test_connected_overlap_is_inclusive_but_one_lsb_outside_moves(self) -> None:
        for extra, connected, expected_move in ((0, {0}, False), (1, {0}, True), (0, set(), True)):
            with self.subTest(extra=extra, connected=bool(connected)):
                subject = east_leg()
                projected_x = subject.x + 1024
                world = ch.World(
                    player_x=projected_x + ch.TILE_GLOBAL + extra,
                    player_y=subject.y,
                    connected_areas=connected,
                )
                world.add_actor(1, subject)
                old_x, old_distance = subject.x, subject.distance
                result = world.chase_step(
                    1, original_tics=2, rng=ch.SequenceRng([]), line_of_sight=no_line
                )
                self.assertEqual(result.moved, expected_move)
                self.assertEqual(result.player_blocked, not expected_move)
                self.assertEqual(subject.x, old_x + (1024 if expected_move else 0))
                self.assertEqual(
                    subject.distance,
                    old_distance - (1024 if expected_move else 0),
                )

    def test_scheduler_releases_self_during_think_then_reclaims_destination(self) -> None:
        world = ch.World(player_x=ch.fixed(30), player_y=ch.fixed(10))
        subject = east_leg()
        world.add_actor(1, subject)
        claimed_index = world.index(11, 10)
        observations: list[int] = []

        def inspect_release(_actor: ch.Actor, current_world: ch.World) -> bool:
            observations.append(current_world.actorat[claimed_index])
            return False

        world.chase_step(
            1, original_tics=2, rng=ch.SequenceRng([]), line_of_sight=inspect_release
        )
        self.assertEqual(observations, [0])
        self.assertEqual(world.actorat[claimed_index], 1)

    def test_trapped_selector_reclaims_original_cached_tile(self) -> None:
        world = ch.World(player_x=ch.fixed(14), player_y=ch.fixed(10))
        subject = actor()
        block_neighbors_except(world, subject)
        world.add_actor(1, subject)
        result = world.chase_step(
            1, original_tics=2, rng=ch.SequenceRng([200]), line_of_sight=no_line
        )
        self.assertTrue(result.blocked)
        self.assertEqual(subject.direction, ch.DIR_NODIR)
        self.assertEqual(world.actorat[world.index(10, 10)], 1)

    def test_ordinary_chase_waits_for_then_crosses_door(self) -> None:
        world = ch.World(player_x=ch.fixed(14), player_y=ch.fixed(10))
        world.install_door(3, ch.Door(11, 10, action=ch.DOOR_CLOSED))
        subject = actor()
        world.add_actor(1, subject)
        rng = ch.SequenceRng([])

        waiting = world.chase_step(
            1, original_tics=2, rng=rng, line_of_sight=no_line
        )
        self.assertTrue(waiting.waiting_for_door)
        self.assertFalse(waiting.moved)
        self.assertEqual((subject.tile_x, subject.tile_y, subject.distance), (11, 10, -4))
        self.assertEqual(world.doors[3].action, ch.DOOR_OPENING)
        self.assertEqual(world.door_request_log, [3, 3])

        world.doors[3].action = ch.DOOR_OPEN
        crossed = world.chase_step(
            1, original_tics=2, rng=rng, line_of_sight=no_line
        )
        self.assertTrue(crossed.moved)
        self.assertFalse(crossed.waiting_for_door)
        self.assertEqual(subject.x, ch.fixed(10) + 1024)
        self.assertEqual(subject.distance, ch.TILE_GLOBAL - 1024)
        self.assertEqual(world.door_request_log, [3, 3, 3])

    def test_missing_ordinary_wait_door_is_corrupt_and_reclaimed(self) -> None:
        world = ch.World(player_x=ch.fixed(20), player_y=ch.fixed(10))
        subject = east_leg(distance=-4)
        world.add_actor(1, subject)
        result = world.chase_step(
            1, original_tics=2, rng=ch.SequenceRng([]), line_of_sight=no_line
        )
        self.assertEqual(result.attack_request, ch.AttackRequest.CORRUPT)
        self.assertEqual(world.door_request_log, [3])
        self.assertEqual(world.actorat[world.index(11, 10)], 1)


class DogChaseTests(unittest.TestCase):
    def _dog_leg(self, **changes: int) -> ch.Actor:
        return east_leg(actor_class=ch.CLASS_DOG, **changes)

    def test_projected_exact_range_requests_jump_without_move_or_rng(self) -> None:
        subject = self._dog_leg()
        budget = subject.speed * 2
        world = ch.World(
            player_x=subject.x + budget + ch.MIN_ACTOR_DISTANCE,
            player_y=subject.y,
        )
        world.add_actor(1, subject)
        old_pose = pose(subject)
        rng = ch.SequenceRng([])
        result = world.dog_chase_step(1, original_tics=2, rng=rng)
        self.assertEqual(result.attack_request, ch.AttackRequest.DOG_JUMP_REQUESTED)
        self.assertEqual(pose(subject), old_pose)
        self.assertEqual(rng.draws, 0)

    def test_projected_one_lsb_outside_range_moves_normally(self) -> None:
        subject = self._dog_leg()
        budget = subject.speed * 2
        world = ch.World(
            player_x=subject.x + budget + ch.MIN_ACTOR_DISTANCE + 1,
            player_y=subject.y,
        )
        world.add_actor(1, subject)
        old_x = subject.x
        result = world.dog_chase_step(
            1, original_tics=2, rng=ch.SequenceRng([])
        )
        self.assertEqual(result.attack_request, ch.AttackRequest.NONE)
        self.assertTrue(result.moved)
        self.assertEqual(subject.x, old_x + budget)

    def test_unlatched_repeated_dog_jump_requests_pause_without_rng(self) -> None:
        subject = self._dog_leg()
        budget = subject.speed * 2
        world = ch.World(
            player_x=subject.x + budget + ch.MIN_ACTOR_DISTANCE,
            player_y=subject.y,
        )
        world.add_actor(1, subject)
        original_pose = pose(subject)
        rng = ch.SequenceRng([])
        for _ in range(2):
            result = world.dog_chase_step(1, original_tics=2, rng=rng)
            self.assertEqual(result.attack_request, ch.AttackRequest.DOG_JUMP_REQUESTED)
            self.assertEqual(pose(subject), original_pose)
        self.assertEqual(rng.draws, 0)

    def test_nodir_dog_uses_one_dodge_byte_then_moves(self) -> None:
        world = ch.World(player_x=ch.fixed(20), player_y=ch.fixed(10))
        subject = actor(actor_class=ch.CLASS_DOG, speed=512)
        world.add_actor(1, subject)
        rng = ch.SequenceRng([200])
        result = world.dog_chase_step(1, original_tics=2, rng=rng)
        self.assertTrue(result.moved)
        self.assertEqual(subject.direction, ch.DIR_NORTHEAST)
        self.assertEqual((subject.tile_x, subject.tile_y), (11, 9))
        self.assertEqual((subject.x, subject.y), (ch.fixed(10) + 1024, ch.fixed(10) - 1024))
        self.assertEqual(subject.distance, ch.TILE_GLOBAL - 1024)
        self.assertEqual(rng.history, [200])

    def test_projected_jump_requires_both_axes_within_threshold(self) -> None:
        subject = self._dog_leg()
        budget = subject.speed * 2
        world = ch.World(
            player_x=subject.x + budget + ch.MIN_ACTOR_DISTANCE,
            player_y=subject.y + budget + ch.MIN_ACTOR_DISTANCE + 1,
        )
        world.add_actor(1, subject)
        old_x = subject.x
        result = world.dog_chase_step(
            1, original_tics=2, rng=ch.SequenceRng([])
        )
        self.assertEqual(result.attack_request, ch.AttackRequest.NONE)
        self.assertTrue(result.moved)
        self.assertEqual(subject.x, old_x + budget)

    def test_injected_negative_distance_fails_closed_before_near_jump(self) -> None:
        subject = self._dog_leg(distance=-1)
        world = ch.World(player_x=subject.x, player_y=subject.y)
        world.add_actor(1, subject)
        rng = ch.SequenceRng([])
        result = world.dog_chase_step(1, original_tics=2, rng=rng)
        self.assertEqual(result.attack_request, ch.AttackRequest.CORRUPT)
        self.assertEqual(rng.draws, 0)
        self.assertEqual(world.actorat[world.index(11, 10)], 1)

    def test_non_dog_or_invalid_direction_fails_without_rng(self) -> None:
        for subject in (east_leg(), self._dog_leg(direction=9)):
            with self.subTest(actor_class=subject.actor_class, direction=subject.direction):
                world = ch.World()
                world.add_actor(1, subject)
                original_pose = pose(subject)
                rng = ch.SequenceRng([])
                result = world.dog_chase_step(1, original_tics=2, rng=rng)
                self.assertEqual(result.attack_request, ch.AttackRequest.CORRUPT)
                self.assertEqual(pose(subject), original_pose)
                self.assertEqual(rng.draws, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
