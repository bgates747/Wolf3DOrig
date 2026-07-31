#!/usr/bin/env python3
"""Directed host regression for :mod:`awareness_oracle`."""

from __future__ import annotations

import unittest

import awareness_oracle as aw


def fixed(tile: int, fraction: int = 0x8000) -> int:
    return (tile << 16) + fraction


def connected(*areas: int) -> bytearray:
    result = bytearray(aw.NUM_AREAS)
    for area in areas:
        result[area] = 1
    return result


class TraceProbe:
    def __init__(self, result: bool) -> None:
        self.result = result
        self.calls: list[tuple[int, int, int, int]] = []

    def __call__(self, actor: aw.Actor, player: aw.Player) -> bool:
        self.calls.append((actor.x, actor.y, player.x, player.y))
        return self.result


def actor(**changes: int | str) -> aw.Actor:
    values: dict[str, int | str] = {
        "x": fixed(20),
        "y": fixed(20),
        "area": 2,
        "direction": aw.DIR_EAST,
        "actor_class": aw.CLASS_GUARD,
        "flags": aw.FLAG_SHOOTABLE,
        "temp2": 0,
        "state": "patrol",
        "ticcount": 7,
        "distance": aw.TILE_GLOBAL,
        "speed": 512,
        "tile_x": 21,
        "tile_y": 20,
    }
    values.update(changes)
    return aw.Actor(**values)  # type: ignore[arg-type]


class AreaAndVisualGateTests(unittest.TestCase):
    def test_disconnected_and_invalid_areas_reject_before_trace(self) -> None:
        player = aw.Player(fixed(24), fixed(20))
        for area in (2, 37, 0xFF):
            with self.subTest(area=area):
                probe = TraceProbe(True)
                self.assertFalse(
                    aw.visual_sight(actor(area=area), player, connected(1), probe)
                )
                self.assertEqual(probe.calls, [])

    def test_reachability_table_has_exact_37_byte_contract(self) -> None:
        for size in (0, 36, 38):
            with self.subTest(size=size):
                with self.assertRaises(aw.AwarenessContractError):
                    aw.area_eligible(0, bytearray(size))

    def test_close_range_is_strict_full_precision_and_skips_trace(self) -> None:
        subject = actor(direction=aw.DIR_EAST)
        probe = TraceProbe(False)
        self.assertTrue(
            aw.visual_sight(
                subject,
                aw.Player(subject.x - aw.MIN_SIGHT + 1, subject.y),
                connected(2),
                probe,
            )
        )
        self.assertEqual(probe.calls, [])

        # At the exact boundary proximity is no longer automatic.  This
        # player is behind an east-facing actor, so facing rejects it.
        self.assertFalse(
            aw.visual_sight(
                subject,
                aw.Player(subject.x - aw.MIN_SIGHT, subject.y),
                connected(2),
                probe,
            )
        )
        self.assertEqual(probe.calls, [])

    def test_all_eight_facing_half_planes_and_nodir(self) -> None:
        positions = {
            aw.DIR_EAST: (24, 20),
            aw.DIR_NORTHEAST: (24, 16),
            aw.DIR_NORTH: (20, 16),
            aw.DIR_NORTHWEST: (16, 16),
            aw.DIR_WEST: (16, 20),
            aw.DIR_SOUTHWEST: (16, 24),
            aw.DIR_SOUTH: (20, 24),
            aw.DIR_SOUTHEAST: (24, 24),
        }
        for direction, (x, y) in positions.items():
            with self.subTest(direction=direction):
                self.assertTrue(
                    aw.visual_sight(
                        actor(direction=direction),
                        aw.Player(fixed(x), fixed(y)),
                        connected(2),
                        TraceProbe(True),
                    )
                )
                opposite = aw.Player(fixed(40 - x), fixed(40 - y))
                probe = TraceProbe(True)
                self.assertFalse(
                    aw.visual_sight(
                        actor(direction=direction), opposite, connected(2), probe
                    )
                )
                self.assertEqual(probe.calls, [])

        self.assertTrue(
            aw.visual_sight(
                actor(direction=aw.DIR_NODIR),
                aw.Player(fixed(16), fixed(20)),
                connected(2),
                TraceProbe(True),
            )
        )

    def test_walls_and_doors_are_replaceable_line_trace_results(self) -> None:
        subject = actor()
        player = aw.Player(fixed(24), fixed(20))
        for obstruction in ("wall", "closed_door"):
            with self.subTest(obstruction=obstruction):
                probe = TraceProbe(False)
                self.assertFalse(
                    aw.visual_sight(subject, player, connected(2), probe)
                )
                self.assertEqual(len(probe.calls), 1)

        open_door = TraceProbe(True)
        self.assertTrue(aw.visual_sight(subject, player, connected(2), open_door))
        self.assertEqual(len(open_door.calls), 1)


class NoiseAndAmbushTests(unittest.TestCase):
    def test_noise_still_requires_a_connected_valid_area(self) -> None:
        player = aw.Player(fixed(24), fixed(20))
        for area in (2, 37, 0xFF):
            with self.subTest(area=area):
                subject = actor(area=area)
                probe = TraceProbe(True)
                rng = aw.SequenceRng([0])
                event = aw.awareness_step(
                    subject,
                    player=player,
                    reachable=connected(1),
                    made_noise=True,
                    original_tics=2,
                    rng=rng,
                    line_of_sight=probe,
                )
                self.assertEqual(event, aw.AwarenessEvent.UNAWARE)
                self.assertEqual((subject.temp2, rng.draws, probe.calls), (0, 0, []))

    def test_ordinary_noise_bypasses_facing_and_line_trace(self) -> None:
        subject = actor(direction=aw.DIR_EAST)
        blocked = TraceProbe(False)
        rng = aw.SequenceRng([0])
        event = aw.awareness_step(
            subject,
            player=aw.Player(fixed(16), fixed(20)),
            reachable=connected(2),
            made_noise=True,
            original_tics=2,
            rng=rng,
            line_of_sight=blocked,
        )
        self.assertEqual(event, aw.AwarenessEvent.DELAY_STARTED)
        self.assertEqual((subject.temp2, rng.draws), (1, 1))
        self.assertEqual(blocked.calls, [])

    def test_ordinary_quiet_actor_requires_visual_sight(self) -> None:
        subject = actor()
        blocked = TraceProbe(False)
        rng = aw.SequenceRng([100])
        event = aw.awareness_step(
            subject,
            player=aw.Player(fixed(24), fixed(20)),
            reachable=connected(2),
            made_noise=False,
            original_tics=2,
            rng=rng,
            line_of_sight=blocked,
        )
        self.assertEqual(event, aw.AwarenessEvent.UNAWARE)
        self.assertEqual((subject.temp2, rng.draws, len(blocked.calls)), (0, 0, 1))

    def test_ambush_ignores_noise_and_stays_armed_when_blocked(self) -> None:
        subject = actor(flags=aw.FLAG_SHOOTABLE | aw.FLAG_AMBUSH)
        blocked = TraceProbe(False)
        rng = aw.SequenceRng([0])
        event = aw.awareness_step(
            subject,
            player=aw.Player(fixed(24), fixed(20)),
            reachable=connected(2),
            made_noise=True,
            original_tics=2,
            rng=rng,
            line_of_sight=blocked,
        )
        self.assertEqual(event, aw.AwarenessEvent.UNAWARE)
        self.assertTrue(subject.flags & aw.FLAG_AMBUSH)
        self.assertEqual((rng.draws, len(blocked.calls)), (0, 1))

    def test_ambush_clears_on_visual_acquisition_before_delay(self) -> None:
        subject = actor(flags=aw.FLAG_SHOOTABLE | aw.FLAG_AMBUSH)
        rng = aw.SequenceRng([20])
        event = aw.awareness_step(
            subject,
            player=aw.Player(fixed(24), fixed(20)),
            reachable=connected(2),
            made_noise=True,
            original_tics=2,
            rng=rng,
            line_of_sight=TraceProbe(True),
        )
        self.assertEqual(event, aw.AwarenessEvent.DELAY_STARTED)
        self.assertFalse(subject.flags & aw.FLAG_AMBUSH)
        self.assertEqual(subject.temp2, 6)

    def test_close_ambush_is_automatic_but_still_area_gated(self) -> None:
        subject = actor(
            direction=aw.DIR_EAST,
            flags=aw.FLAG_SHOOTABLE | aw.FLAG_AMBUSH,
        )
        probe = TraceProbe(False)
        rng = aw.SequenceRng([0])
        event = aw.awareness_step(
            subject,
            player=aw.Player(subject.x - aw.MIN_SIGHT + 1, subject.y),
            reachable=connected(2),
            made_noise=False,
            original_tics=2,
            rng=rng,
            line_of_sight=probe,
        )
        self.assertEqual(event, aw.AwarenessEvent.DELAY_STARTED)
        self.assertEqual(probe.calls, [])

        disconnected = actor(flags=aw.FLAG_SHOOTABLE | aw.FLAG_AMBUSH)
        event = aw.awareness_step(
            disconnected,
            player=aw.Player(disconnected.x, disconnected.y),
            reachable=connected(1),
            made_noise=True,
            original_tics=2,
            rng=aw.SequenceRng([0]),
            line_of_sight=TraceProbe(True),
        )
        self.assertEqual(event, aw.AwarenessEvent.UNAWARE)
        self.assertTrue(disconnected.flags & aw.FLAG_AMBUSH)


class ReactionDelayTests(unittest.TestCase):
    def test_random_delay_extremes_match_all_ordinary_classes(self) -> None:
        cases = {
            aw.CLASS_GUARD: (1, 64),
            aw.CLASS_SS: (1, 43),
            aw.CLASS_DOG: (1, 32),
            aw.CLASS_MUTANT: (1, 43),
        }
        for actor_class, expected in cases.items():
            with self.subTest(actor_class=actor_class):
                self.assertEqual(
                    aw.reaction_delay(actor_class, aw.SequenceRng([0])), expected[0]
                )
                self.assertEqual(
                    aw.reaction_delay(actor_class, aw.SequenceRng([255])), expected[1]
                )

    def test_officer_delay_is_fixed_and_consumes_no_random_byte(self) -> None:
        rng = aw.SequenceRng([])
        self.assertEqual(aw.reaction_delay(aw.CLASS_OFFICER, rng), 2)
        self.assertEqual(rng.draws, 0)

    def test_guard_delay_counts_down_on_shared_223_cadence(self) -> None:
        subject = actor()
        rng = aw.SequenceRng([27])  # 1 + 27//4 == 7 tics
        common = {
            "player": aw.Player(fixed(24), fixed(20)),
            "reachable": connected(2),
            "made_noise": True,
            "rng": rng,
            "line_of_sight": TraceProbe(False),
        }
        self.assertEqual(
            aw.awareness_step(subject, original_tics=2, **common),
            aw.AwarenessEvent.DELAY_STARTED,
        )
        self.assertEqual(subject.temp2, 7)
        self.assertEqual(
            aw.awareness_step(subject, original_tics=2, **common),
            aw.AwarenessEvent.DELAY_WAITING,
        )
        self.assertEqual(subject.temp2, 5)
        self.assertEqual(
            aw.awareness_step(subject, original_tics=2, **common),
            aw.AwarenessEvent.DELAY_WAITING,
        )
        self.assertEqual(subject.temp2, 3)
        self.assertEqual(
            aw.awareness_step(subject, original_tics=3, **common),
            aw.AwarenessEvent.ACTIVATED,
        )
        self.assertEqual(subject.temp2, 0)
        self.assertEqual(rng.draws, 1)

    def test_pending_delay_continues_after_area_disconnects(self) -> None:
        subject = actor(temp2=2)
        rng = aw.SequenceRng([])
        blocked = TraceProbe(False)
        event = aw.awareness_step(
            subject,
            player=aw.Player(fixed(40), fixed(40)),
            reachable=connected(1),
            made_noise=False,
            original_tics=2,
            rng=rng,
            line_of_sight=blocked,
        )
        self.assertEqual(event, aw.AwarenessEvent.ACTIVATED)
        self.assertEqual((rng.draws, blocked.calls), (0, []))

    def test_initial_detection_never_activates_immediately(self) -> None:
        subject = actor()
        rng = aw.SequenceRng([0])  # shortest possible delay is one tic
        args = {
            "player": aw.Player(fixed(24), fixed(20)),
            "reachable": connected(2),
            "made_noise": True,
            "rng": rng,
            "line_of_sight": TraceProbe(False),
        }
        self.assertEqual(
            aw.awareness_step(subject, original_tics=3, **args),
            aw.AwarenessEvent.DELAY_STARTED,
        )
        self.assertFalse(subject.flags & aw.FLAG_ATTACKMODE)
        self.assertEqual(
            aw.awareness_step(subject, original_tics=2, **args),
            aw.AwarenessEvent.ACTIVATED,
        )


class ActivationTests(unittest.TestCase):
    def test_each_ordinary_class_gets_chase_state_speed_and_tics(self) -> None:
        for actor_class, multiplier in aw.SPEED_MULTIPLIER_BY_CLASS.items():
            with self.subTest(actor_class=actor_class):
                subject = actor(
                    actor_class=actor_class,
                    temp2=1,
                    speed=777,
                    flags=aw.FLAG_SHOOTABLE,
                )
                event = aw.awareness_step(
                    subject,
                    player=aw.Player(fixed(24), fixed(20)),
                    reachable=connected(2),
                    made_noise=False,
                    original_tics=2,
                    rng=aw.SequenceRng([]),
                    line_of_sight=TraceProbe(False),
                )
                self.assertEqual(event, aw.AwarenessEvent.ACTIVATED)
                self.assertEqual(subject.state, aw.CHASE_STATE_BY_CLASS[actor_class])
                self.assertEqual(subject.ticcount, aw.CHASE_TICS)
                self.assertEqual(subject.speed, 777 * multiplier)
                self.assertEqual(
                    subject.flags & (aw.FLAG_ATTACKMODE | aw.FLAG_FIRSTATTACK),
                    aw.FLAG_ATTACKMODE | aw.FLAG_FIRSTATTACK,
                )
                self.assertTrue(subject.flags & aw.FLAG_SHOOTABLE)

    def test_negative_door_wait_is_cancelled_but_positive_distance_survives(self) -> None:
        waiting = actor(temp2=1, distance=-9)
        moving = actor(temp2=1, distance=12345)
        for subject in (waiting, moving):
            aw.awareness_step(
                subject,
                player=aw.Player(fixed(24), fixed(20)),
                reachable=connected(2),
                made_noise=False,
                original_tics=2,
                rng=aw.SequenceRng([]),
                line_of_sight=TraceProbe(False),
            )
        self.assertEqual(waiting.distance, 0)
        self.assertEqual(moving.distance, 12345)

    def test_activation_changes_no_pose_or_direction_field(self) -> None:
        subject = actor(
            x=fixed(17, 0x1234),
            y=fixed(31, 0xFEDC),
            tile_x=18,
            tile_y=31,
            direction=aw.DIR_NORTHWEST,
            temp2=1,
            distance=-1,
        )
        pose = (subject.x, subject.y, subject.tile_x, subject.tile_y, subject.direction)
        event = aw.awareness_step(
            subject,
            player=aw.Player(fixed(40), fixed(40)),
            reachable=connected(2),
            made_noise=False,
            original_tics=3,
            rng=aw.SequenceRng([]),
            line_of_sight=TraceProbe(False),
        )
        self.assertEqual(event, aw.AwarenessEvent.ACTIVATED)
        self.assertEqual(
            (subject.x, subject.y, subject.tile_x, subject.tile_y, subject.direction),
            pose,
        )

    def test_attack_mode_actor_is_outside_awareness_contract(self) -> None:
        subject = actor(flags=aw.FLAG_SHOOTABLE | aw.FLAG_ATTACKMODE)
        with self.assertRaises(aw.AwarenessContractError):
            aw.awareness_step(
                subject,
                player=aw.Player(fixed(24), fixed(20)),
                reachable=connected(2),
                made_noise=True,
                original_tics=2,
                rng=aw.SequenceRng([0]),
                line_of_sight=TraceProbe(True),
            )

    def test_unsupported_class_fails_at_delay_or_activation_boundary(self) -> None:
        with self.assertRaises(aw.AwarenessContractError):
            aw.reaction_delay(99, aw.SequenceRng([0]))
        with self.assertRaises(aw.AwarenessContractError):
            aw.activate_without_chase_movement(actor(actor_class=99))


if __name__ == "__main__":
    unittest.main()
