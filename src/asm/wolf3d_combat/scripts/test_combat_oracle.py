#!/usr/bin/env python3
"""Directed host regression for :mod:`combat_oracle`."""

from __future__ import annotations

import unittest

import combat_oracle as co


def player(**changes: object) -> co.Player:
    values: dict[str, object] = {
        "x": co.fixed(10),
        "y": co.fixed(10),
        "tile_x": 10,
        "tile_y": 10,
        "heading": 0,
        "thrustspeed": 0,
        "health": 100,
    }
    values.update(changes)
    return co.Player(**values)  # type: ignore[arg-type]


def actor(**changes: int) -> co.Actor:
    values = {
        "actor_id": 7,
        "actor_class": co.CLASS_GUARD,
        "x": co.fixed(12),
        "y": co.fixed(10),
        "tile_x": 12,
        "tile_y": 10,
        "area": 0,
    }
    values.update(changes)
    return co.Actor(**values)


def reachable(*areas: int) -> bytearray:
    result = bytearray(co.NUM_AREAS)
    for area in areas:
        result[area] = 1
    return result


class LineSequence:
    def __init__(self, *values: bool):
        self.values = list(values)
        self.calls = 0

    def __call__(self, _actor: co.Actor, _player: co.Player) -> bool:
        if self.calls >= len(self.values):
            raise AssertionError("line sequence exhausted")
        result = self.values[self.calls]
        self.calls += 1
        return result


class AttackStateTests(unittest.TestCase):
    def test_all_24_attack_records_match_source(self) -> None:
        expected = {
            77: (96, 0, 20, 0, 78),
            78: (97, 0, 20, 1, 79),
            79: (98, 0, 20, 0, 47),
            80: (135, 0, 10, 0, 81),
            81: (136, 0, 10, 2, 82),
            82: (137, 0, 10, 0, 83),
            83: (135, 0, 10, 0, 84),
            84: (99, 0, 10, 0, 48),
            85: (285, 0, 6, 0, 86),
            86: (286, 0, 20, 1, 87),
            87: (287, 0, 10, 0, 49),
            88: (234, 0, 6, 1, 89),
            89: (235, 0, 20, 0, 90),
            90: (236, 0, 10, 1, 91),
            91: (237, 0, 20, 0, 50),
            92: (184, 0, 20, 0, 93),
            93: (185, 0, 20, 1, 94),
            94: (186, 0, 10, 0, 95),
            95: (185, 0, 10, 1, 96),
            96: (186, 0, 10, 0, 97),
            97: (185, 0, 10, 1, 98),
            98: (186, 0, 10, 0, 99),
            99: (185, 0, 10, 1, 100),
            100: (186, 0, 10, 0, 51),
        }
        actual = {
            state_id: (
                state.shape,
                state.rotations,
                state.tictime,
                state.action,
                state.next_state,
            )
            for state_id, state in co.ATTACK_STATES.items()
        }
        self.assertEqual(actual, expected)

    def test_exact_source_action_and_return_tics(self) -> None:
        cases = {
            co.CLASS_GUARD: ([40], 60),
            co.CLASS_OFFICER: ([26], 36),
            co.CLASS_MUTANT: ([6, 36], 56),
            co.CLASS_SS: ([40, 60, 80, 100], 110),
            co.CLASS_DOG: ([20], 50),
        }
        for actor_class, (expected_actions, expected_return) in cases.items():
            with self.subTest(actor_class=actor_class):
                runtime = co.start_attack(actor_class)
                action_tics: list[int] = []
                returned = None
                for elapsed in range(1, expected_return + 1):
                    result = co.advance_attack(runtime, 1)
                    action_tics.extend(elapsed for _action in result.actions)
                    if result.entered_chase:
                        returned = elapsed
                        break
                self.assertEqual(action_tics, expected_actions)
                self.assertEqual(returned, expected_return)
                self.assertEqual(runtime.state_id, co.TERMINAL_CHASE_STATE[actor_class])
                self.assertEqual(runtime.ticcount, 10)

    def test_action_observes_expiring_state_before_next(self) -> None:
        runtime = co.start_attack(co.CLASS_MUTANT)
        observed: list[tuple[int, int, int]] = []

        def handler(action_id: int, state_id: int) -> None:
            observed.append((action_id, state_id, runtime.state_id))

        result = co.advance_attack(runtime, 36, handler)
        self.assertEqual(
            observed,
            [
                (co.ACTION_SHOOT, co.STATE_MUT_SHOOT1, co.STATE_MUT_SHOOT1),
                (co.ACTION_SHOOT, co.STATE_MUT_SHOOT3, co.STATE_MUT_SHOOT3),
            ],
        )
        self.assertEqual(result.actions, ((1, 88), (1, 90)))
        self.assertEqual((runtime.state_id, runtime.ticcount), (91, 20))

    def test_large_overshoot_executes_all_due_ss_actions_in_order(self) -> None:
        runtime = co.start_attack(co.CLASS_SS)
        result = co.advance_attack(runtime, 100)
        self.assertEqual(result.actions, ((1, 93), (1, 95), (1, 97), (1, 99)))
        self.assertEqual((runtime.state_id, runtime.ticcount), (100, 10))
        self.assertFalse(result.entered_chase)
        result = co.advance_attack(runtime, 10)
        self.assertTrue(result.entered_chase)
        self.assertEqual((runtime.state_id, runtime.ticcount), (51, 10))

    def test_223_fixed_clock_carries_signed_overshoot(self) -> None:
        expected = {
            co.CLASS_GUARD: ([(42, 78)], 60, 10),
            co.CLASS_OFFICER: ([(28, 86)], 37, 9),
            co.CLASS_MUTANT: ([(7, 88), (37, 90)], 56, 10),
            co.CLASS_SS: ([(42, 93), (60, 95), (81, 97), (100, 99)], 112, 8),
            co.CLASS_DOG: ([(21, 81)], 51, 9),
        }
        for actor_class, (wanted_actions, wanted_elapsed, wanted_count) in expected.items():
            with self.subTest(actor_class=actor_class):
                runtime = co.start_attack(actor_class)
                elapsed = 0
                actions: list[tuple[int, int]] = []
                for frame in range(64):
                    tics = (2, 2, 3)[frame % 3]
                    elapsed += tics
                    result = co.advance_attack(runtime, tics)
                    actions.extend((elapsed, state_id) for _action, state_id in result.actions)
                    if result.entered_chase:
                        break
                self.assertEqual((actions, elapsed, runtime.ticcount),
                                 (wanted_actions, wanted_elapsed, wanted_count))

    def test_combat_oracle_rejects_overshoot_into_chase_graph(self) -> None:
        runtime = co.start_attack(co.CLASS_GUARD)
        with self.assertRaises(co.CombatContractError):
            co.advance_attack(runtime, 70)


class ThrustspeedTests(unittest.TestCase):
    def test_every_translation_key_combination_has_exact_axis_sum(self) -> None:
        expected = {
            0x0: 0,
            0x1: 0x1000,
            0x2: 0x1000,
            0x3: 0,
            0x4: 0x1000,
            0x5: 0x2000,
            0x6: 0x2000,
            0x7: 0x1000,
            0x8: 0x1000,
            0x9: 0x2000,
            0xA: 0x2000,
            0xB: 0x1000,
            0xC: 0,
            0xD: 0x1000,
            0xE: 0x1000,
            0xF: 0,
        }
        self.assertEqual(
            {controls: co.produce_thrustspeed(controls) for controls in range(16)},
            expected,
        )

    def test_rotation_and_use_do_not_contribute(self) -> None:
        modifiers = co.CONTROL_LEFT | co.CONTROL_RIGHT | co.CONTROL_USE | 0x80
        self.assertEqual(co.produce_thrustspeed(modifiers), 0)
        self.assertEqual(co.produce_thrustspeed(modifiers | co.CONTROL_W), 0x1000)
        self.assertEqual(
            co.produce_thrustspeed(modifiers | co.CONTROL_W | co.CONTROL_A),
            0x2000,
        )

    def test_running_boundary_is_preserved(self) -> None:
        self.assertLess(co.produce_thrustspeed(co.CONTROL_W), co.RUN_SPEED)
        self.assertGreaterEqual(
            co.produce_thrustspeed(co.CONTROL_W | co.CONTROL_A), co.RUN_SPEED
        )


class VisibilityTests(unittest.TestCase):
    @staticmethod
    def projected(relative_x_q8: int, relative_y_q8: int, heading: int) -> co.Projection:
        subject = player(heading=heading)
        target = actor(
            x=subject.x + (relative_x_q8 << 8),
            y=subject.y + (relative_y_q8 << 8),
        )
        return co.cpu_visibility_projection(target, subject)

    def test_cardinal_front_and_back_vectors(self) -> None:
        cases = (
            ((512, 0, 0), (512, 0, 535, 127, True)),
            ((-512, 0, 0), (-512, 0, -489, None, False)),
            ((0, -512, 90), (512, 0, 535, 127, True)),
            ((0, 512, 90), (-512, 0, -489, None, False)),
        )
        for inputs, wanted in cases:
            with self.subTest(inputs=inputs):
                result = self.projected(*inputs)
                self.assertEqual(
                    (result.forward_q8, result.lateral_q8, result.nx_q8,
                     result.screen_x, result.visible),
                    wanted,
                )

    def test_near_plane_is_inclusive_at_0x58(self) -> None:
        outside = self.projected(64, 0, 0)
        edge = self.projected(65, 0, 0)
        self.assertEqual((outside.nx_q8, outside.screen_x, outside.visible),
                         (0x57, None, False))
        self.assertEqual((edge.nx_q8, edge.screen_x, edge.visible),
                         (0x58, 127, True))

    def test_projected_screen_edges_are_inclusive(self) -> None:
        cases = (
            ((233, -374, 0), (0, True)),
            ((233, -377, 0), (-1, False)),
            ((233, 377, 0), (255, True)),
            ((233, 380, 0), (256, False)),
        )
        for inputs, wanted in cases:
            with self.subTest(inputs=inputs):
                result = self.projected(*inputs)
                self.assertEqual((result.screen_x, result.visible), wanted)

    def test_q12_diagonal_basis_matches_motion_table(self) -> None:
        self.assertEqual(co.motion_basis_q12(45), (2896, -2896))
        self.assertEqual(co.motion_basis_q12(315), (2896, 2896))
        northeast = self.projected(512, -512, 45)
        southeast = self.projected(512, 512, 315)
        self.assertEqual(
            (northeast.forward_q8, northeast.lateral_q8,
             northeast.nx_q8, northeast.screen_x, northeast.visible),
            (724, 0, 747, 127, True),
        )
        self.assertEqual(
            (southeast.forward_q8, southeast.lateral_q8,
             southeast.nx_q8, southeast.screen_x, southeast.visible),
            (724, 0, 747, 127, True),
        )

    def test_negative_q12_products_truncate_toward_zero(self) -> None:
        # Arithmetic >>12 would make lateral=-139 and project to -1.  The
        # original signed-magnitude FixedByFrac contract yields -138 and keeps
        # this exact center on visible column zero.
        result = self.projected(70, -140, 1)
        self.assertEqual(
            (result.motion_x_q12, result.motion_y_q12,
             result.forward_q8, result.lateral_q8,
             result.nx_q8, result.screen_x, result.visible),
            (4095, -71, 71, -138, 94, 0, True),
        )

    def test_full_fixed_negative_lsb_borrows_into_reduced_q8(self) -> None:
        subject = player(heading=30)
        target = actor(
            x=subject.x - 1,
            y=subject.y + (-200 << 8),
        )
        result = co.cpu_visibility_projection(target, subject)
        self.assertEqual(
            (result.relative_x_q8, result.relative_y_q8,
             result.motion_x_q12, result.motion_y_q12,
             result.forward_q8, result.lateral_q8,
             result.nx_q8, result.screen_x, result.visible),
            (-1, -200, 3547, -2048, 100, -173, 123, 5, True),
        )

    def test_projection_uses_current_pose_not_a_renderer_latch(self) -> None:
        subject = player(heading=0)
        target = actor()
        self.assertTrue(co.cpu_visibility_projection(target, subject).visible)
        subject.heading = 180
        self.assertFalse(co.cpu_visibility_projection(target, subject).visible)


class TakeDamageTests(unittest.TestCase):
    def test_normal_damage_and_death_side_effects(self) -> None:
        subject = player(health=10, got_gat_gun=True)
        outcome = co.take_damage(12, subject, 7)
        self.assertEqual((outcome.health_before, outcome.health_after,
                          outcome.applied_damage, outcome.killed),
                         (10, 0, 10, True))
        self.assertEqual(
            (subject.last_attacker_id, subject.killer_actor_id, subject.dead,
             subject.got_gat_gun, subject.damage_flashes,
             subject.health_redraws, subject.face_redraws),
            (7, 7, True, False, [12], 1, 1),
        )
        self.assertTrue(subject.hud_dirty & co.HUD_DIRTY_HEALTH)

    def test_only_baby_difficulty_quarters_points(self) -> None:
        for difficulty, expected in (
            (co.Difficulty.BABY, 94),
            (co.Difficulty.EASY, 75),
            (co.Difficulty.MEDIUM, 75),
            (co.Difficulty.HARD, 75),
        ):
            with self.subTest(difficulty=difficulty):
                subject = player(difficulty=difficulty)
                outcome = co.take_damage(25, subject, 7)
                self.assertEqual((subject.health, outcome.reduced_points),
                                 (expected, 6 if difficulty == 0 else 25))

    def test_zero_damage_still_runs_presentation_and_reset_effects(self) -> None:
        subject = player(got_gat_gun=True)
        outcome = co.take_damage(0, subject, 8)
        self.assertEqual((subject.health, outcome.applied_damage), (100, 0))
        self.assertEqual(
            (subject.last_attacker_id, subject.got_gat_gun,
             subject.damage_flashes, subject.health_redraws, subject.face_redraws),
            (8, False, [0], 1, 1),
        )

    def test_god_mode_preserves_health_but_not_other_effects(self) -> None:
        subject = player(health=40, god_mode=True, got_gat_gun=True)
        outcome = co.take_damage(63, subject, 9)
        self.assertEqual((subject.health, outcome.applied_damage), (40, 0))
        self.assertEqual((subject.last_attacker_id, subject.damage_flashes,
                          subject.health_redraws, subject.face_redraws),
                         (9, [63], 1, 1))

    def test_victory_returns_after_last_attacker_only(self) -> None:
        subject = player(health=40, victory=True, got_gat_gun=True)
        outcome = co.take_damage(63, subject, 9)
        self.assertTrue(outcome.victory_suppressed)
        self.assertEqual(
            (subject.health, subject.last_attacker_id, subject.got_gat_gun,
             subject.damage_flashes, subject.hud_dirty),
            (40, 9, True, [], 0),
        )

    def test_later_same_pass_hit_can_overwrite_killer(self) -> None:
        subject = player(health=1)
        co.take_damage(1, subject, 7)
        co.take_damage(0, subject, 8)
        self.assertEqual(
            (subject.health, subject.dead, subject.last_attacker_id,
             subject.killer_actor_id),
            (0, True, 8, 8),
        )


class ShootTests(unittest.TestCase):
    def test_disconnected_area_fails_before_line_rng_sound(self) -> None:
        line = LineSequence(True)
        rng = co.SequenceRng([])
        result = co.shoot(actor(area=0), player(), reachable(1), line, rng)
        self.assertEqual((result.eligible_area, result.line_clear,
                          result.sound, result.events),
                         (False, None, co.Sound.NONE, ()))
        self.assertEqual((line.calls, rng.draws), (0, 0))

    def test_invalid_area_is_corrupt_before_line_or_rng(self) -> None:
        for area in (-1, co.NUM_AREAS):
            with self.subTest(area=area):
                line = LineSequence(True)
                rng = co.SequenceRng([])
                with self.assertRaises(co.CombatContractError):
                    co.shoot(actor(area=area), player(), reachable(0), line, rng)
                self.assertEqual((line.calls, rng.draws), (0, 0))

    def test_blocked_line_fails_before_projection_rng_and_sound(self) -> None:
        line = LineSequence(False)
        rng = co.SequenceRng([])
        result = co.shoot(actor(), player(), reachable(0), line, rng)
        self.assertEqual(
            (result.line_clear, result.visible, result.sound, result.events),
            (False, None, co.Sound.NONE, ("check_line",)),
        )
        self.assertEqual((line.calls, rng.draws), (1, 0))

    def test_visible_stationary_chance_and_strict_boundary(self) -> None:
        for roll, hit in ((223, True), (224, False)):
            with self.subTest(roll=roll):
                subject = player()
                rng = co.SequenceRng([roll, 0] if hit else [roll])
                result = co.shoot(
                    actor(), subject, reachable(0), LineSequence(True), rng
                )
                self.assertEqual(
                    (result.raw_distance, result.effective_distance,
                     result.visible, result.hitchance, result.hit),
                    (2, 2, True, 224, hit),
                )
                self.assertEqual(rng.draws, 2 if hit else 1)
                self.assertEqual(result.sound, co.Sound.NAZI_FIRE)

    def test_thrustspeed_boundary_changes_hitchance_at_exact_6000(self) -> None:
        chances = []
        for speed in (5999, 6000):
            result = co.shoot(
                actor(), player(thrustspeed=speed), reachable(0),
                LineSequence(True), co.SequenceRng([255]),
            )
            chances.append(result.hitchance)
        self.assertEqual(chances, [224, 128])

    def test_invisible_projection_uses_eight_point_distance_slope(self) -> None:
        target = actor(x=co.fixed(8), tile_x=8)
        result = co.shoot(
            target, player(), reachable(0), LineSequence(True),
            co.SequenceRng([239, 0]),
        )
        self.assertEqual(
            (result.visible, result.raw_distance, result.hitchance, result.hit),
            (False, 2, 240, True),
        )

    def test_unclamped_chance_extremes_still_consume_hit_byte(self) -> None:
        subject = player()
        close = actor(
            x=subject.x + (65 << 8), y=subject.y,
            tile_x=subject.tile_x, tile_y=subject.tile_y,
        )
        rng = co.SequenceRng([255, 255])
        always = co.shoot(close, subject, reachable(0), LineSequence(True), rng)
        self.assertEqual(
            (always.visible, always.hitchance, always.hit,
             always.raw_damage, rng.draws),
            (True, 256, True, 63, 2),
        )

        far = actor(x=co.fixed(30), tile_x=30)
        rng = co.SequenceRng([0])
        never = co.shoot(far, player(), reachable(0), LineSequence(True), rng)
        self.assertEqual(
            (never.visible, never.hitchance, never.hit, rng.draws, never.sound),
            (True, -64, False, 1, co.Sound.NAZI_FIRE),
        )

    def test_all_three_damage_distance_bands(self) -> None:
        cases = (
            (1, 255, 63),
            (2, 255, 31),
            (4, 255, 15),
        )
        for distance, roll, wanted in cases:
            with self.subTest(distance=distance):
                target = actor(x=co.fixed(10 + distance), tile_x=10 + distance)
                result = co.shoot(
                    target, player(), reachable(0), LineSequence(True),
                    co.SequenceRng([0, roll]),
                )
                self.assertEqual(result.raw_damage, wanted)

    def test_ss_reduced_distance_drives_both_chance_and_damage_band(self) -> None:
        target = actor(
            actor_class=co.CLASS_SS,
            x=co.fixed(15),
            tile_x=15,
        )
        result = co.shoot(
            target, player(), reachable(0), LineSequence(True),
            co.SequenceRng([0, 255]),
        )
        self.assertEqual(
            (result.raw_distance, result.effective_distance, result.hitchance,
             result.raw_damage, result.sound),
            (5, 3, 208, 31, co.Sound.SS_FIRE),
        )

    def test_hit_damage_and_sound_event_order_is_exact(self) -> None:
        result = co.shoot(
            actor(), player(), reachable(0), LineSequence(True),
            co.SequenceRng([0, 64]),
        )
        self.assertEqual(
            result.events,
            ("check_line", "project_visibility", "hit_rng", "damage_rng",
             "take_damage", "nazi_fire"),
        )
        miss = co.shoot(
            actor(), player(), reachable(0), LineSequence(True),
            co.SequenceRng([255]),
        )
        self.assertEqual(
            miss.events,
            ("check_line", "project_visibility", "hit_rng", "nazi_fire"),
        )

    def test_zero_damage_hit_still_calls_take_damage(self) -> None:
        subject = player(got_gat_gun=True)
        result = co.shoot(
            actor(), subject, reachable(0), LineSequence(True),
            co.SequenceRng([0, 0]),
        )
        self.assertTrue(result.hit)
        self.assertEqual((result.raw_damage, subject.health,
                          subject.damage_flashes, subject.got_gat_gun),
                         (0, 100, [0], False))

    def test_each_multishot_action_rechecks_line_and_advances_anyway(self) -> None:
        target = actor(actor_class=co.CLASS_MUTANT, x=co.fixed(14), tile_x=14)
        subject = player()
        line = LineSequence(True, False)
        rng = co.SequenceRng([0, 64])
        outcomes: list[co.ShotOutcome] = []
        runtime = co.start_attack(co.CLASS_MUTANT)

        def dispatch(action_id: int, _state_id: int) -> None:
            self.assertEqual(action_id, co.ACTION_SHOOT)
            outcomes.append(co.shoot(target, subject, reachable(0), line, rng))

        result = co.advance_attack(runtime, 56, dispatch)
        self.assertTrue(result.entered_chase)
        self.assertEqual((line.calls, rng.draws, len(outcomes)), (2, 2, 2))
        self.assertEqual(
            [(outcome.line_clear, outcome.sound) for outcome in outcomes],
            [(True, co.Sound.NAZI_FIRE), (False, co.Sound.NONE)],
        )
        self.assertEqual(subject.health, 96)


class BiteTests(unittest.TestCase):
    def test_sound_precedes_range_and_out_of_range_consumes_no_rng(self) -> None:
        target = actor(
            actor_class=co.CLASS_DOG,
            x=player().x + 2 * co.TILE_GLOBAL + 1,
            y=player().y,
        )
        rng = co.SequenceRng([])
        result = co.bite(target, player(), rng)
        self.assertEqual(
            (result.in_range, result.sound, result.events, rng.draws),
            (False, co.Sound.DOG_ATTACK, ("dog_attack",), 0),
        )

    def test_two_tile_square_boundary_is_inclusive_on_both_axes(self) -> None:
        subject = player()
        for dx, dy, expected in (
            (2 * co.TILE_GLOBAL, 2 * co.TILE_GLOBAL, True),
            (-2 * co.TILE_GLOBAL, -2 * co.TILE_GLOBAL, True),
            (2 * co.TILE_GLOBAL + 1, 0, False),
            (0, -2 * co.TILE_GLOBAL - 1, False),
        ):
            with self.subTest(dx=dx, dy=dy):
                target = actor(
                    actor_class=co.CLASS_DOG,
                    x=subject.x + dx,
                    y=subject.y + dy,
                )
                rng = co.SequenceRng([180] if expected else [])
                result = co.bite(target, subject, rng)
                self.assertEqual((result.in_range, rng.draws),
                                 (expected, 1 if expected else 0))

    def test_hit_threshold_is_strict_and_damage_draw_is_conditional(self) -> None:
        target = actor(actor_class=co.CLASS_DOG)
        for roll, hit, draws in ((179, True, 2), (180, False, 1)):
            with self.subTest(roll=roll):
                subject = player()
                rng = co.SequenceRng([roll, 255] if hit else [roll])
                result = co.bite(target, subject, rng)
                self.assertEqual((result.hit, rng.draws), (hit, draws))
                self.assertEqual(result.raw_damage, 15 if hit else None)

    def test_bite_event_order_and_baby_damage(self) -> None:
        subject = player(difficulty=co.Difficulty.BABY)
        result = co.bite(
            actor(actor_class=co.CLASS_DOG),
            subject,
            co.SequenceRng([0, 255]),
        )
        self.assertEqual(
            result.events,
            ("dog_attack", "hit_rng", "damage_rng", "take_damage"),
        )
        self.assertEqual(
            (result.raw_damage, result.damage.reduced_points, subject.health),
            (15, 3, 97),
        )

    def test_victory_does_not_suppress_bite_rng_or_sound(self) -> None:
        subject = player(victory=True)
        rng = co.SequenceRng([0, 255])
        result = co.bite(actor(actor_class=co.CLASS_DOG), subject, rng)
        self.assertEqual(
            (result.hit, rng.draws, result.sound, subject.health,
             subject.last_attacker_id, subject.damage_flashes),
            (True, 2, co.Sound.DOG_ATTACK, 100, 7, []),
        )


if __name__ == "__main__":
    unittest.main()
