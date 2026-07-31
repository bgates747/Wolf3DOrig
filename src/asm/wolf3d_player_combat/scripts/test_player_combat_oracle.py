#!/usr/bin/env python3
"""Directed regression for the independent ordinary player-combat oracle."""

from __future__ import annotations

import os
from pathlib import Path
import re
import unittest

import player_combat_oracle as pc


_root_override = os.environ.get("W3D_REPO_ROOT")
ROOT = (
    Path(_root_override)
    if _root_override
    else Path(__file__).resolve().parents[4]
)
WOLFSRC = ROOT / "orig/src/WOLFSRC"


def actor(
    actor_id: int = 1,
    actor_class: pc.ActorClass = pc.ActorClass.GUARD,
    **changes: object,
) -> pc.Actor:
    values: dict[str, object] = {
        "actor_id": actor_id,
        "actor_class": actor_class,
        "hitpoints": 100,
        "x": 2 << 16,
        "y": 0,
        "tile_x": 2,
        "tile_y": 0,
        "shootable": True,
        "attack_mode": True,
        "state": pc.CHASE_STATES[actor_class],
        "ticcount": 10,
        "visible": True,
        "center_delta": 0,
        "depth_q8": 0x200,
        "line_clear": True,
    }
    values.update(changes)
    return pc.Actor(**values)  # type: ignore[arg-type]


class LineProbe:
    def __init__(self, clear_ids: set[int]):
        self.clear_ids = clear_ids
        self.calls: list[int] = []

    def __call__(self, target: pc.Actor) -> bool:
        self.calls.append(target.actor_id)
        return target.actor_id in self.clear_ids


class SourceGroundingTests(unittest.TestCase):
    def test_attackinfo_rows_are_parsed_from_bundled_wl_agent_c(self) -> None:
        text = (WOLFSRC / "WL_AGENT.C").read_text(encoding="latin-1")
        match = re.search(
            r"attackinfo\[4\]\[14\]\s*=\s*\{(.*?)\n\};",
            text,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        source_rows = tuple(
            (int(tics), int(action), int(frame))
            for tics, action, frame in re.findall(
                r"\{\s*(\d+)\s*,\s*(-?\d+)\s*,\s*(\d+)\s*\}",
                match.group(1),  # type: ignore[union-attr]
            )
        )
        oracle_rows = tuple(
            (record.tics, int(record.action), record.frame)
            for weapon in pc.Weapon
            for record in pc.ATTACK_INFO[weapon]
        )
        self.assertEqual(source_rows, oracle_rows)

    def test_all_30_injury_records_are_parsed_from_bundled_wl_act2_c(self) -> None:
        text = (WOLFSRC / "WL_ACT2.C").read_text(encoding="latin-1")
        pattern = re.compile(
            r"statetype\s+"
            r"(s_(?:grd|dog|ofc|mut|ss)(?:pain1?|die[1-5]|dead))"
            r"\s*=\s*\{\s*(false|2)\s*,\s*(SPR_[A-Z0-9_]+)\s*,"
            r"\s*(\d+)\s*,\s*NULL\s*,\s*(NULL|A_DeathScream)\s*,"
            r"\s*&([a-z0-9_]+)\s*\};"
        )
        parsed: dict[str, pc.InjuryState] = {}
        for name, rotate, shape, tics, action, next_state in pattern.findall(text):
            parsed[name] = pc.InjuryState(
                0 if rotate == "false" else int(rotate),
                shape,
                int(tics),
                None if action == "NULL" else "death_scream",
                next_state,
            )
        self.assertEqual(len(parsed), 30)
        self.assertEqual(parsed, pc.INJURY_STATES)

    def test_kill_points_and_drop_symbols_are_present_in_source_branches(self) -> None:
        text = (WOLFSRC / "WL_STATE.C").read_text(encoding="latin-1")
        section = text[text.index("void KillActor"):text.index("void DamageActor")]
        expected = {
            "guardobj": (100, ("bo_clip2",)),
            "officerobj": (400, ("bo_clip2",)),
            "mutantobj": (700, ("bo_clip2",)),
            "ssobj": (500, ("bo_machinegun", "bo_clip2")),
            "dogobj": (200, ()),
        }
        for class_name, (points, drops) in expected.items():
            with self.subTest(actor_class=class_name):
                start = section.index(f"case {class_name}:")
                end = section.index("break;", start)
                branch = section[start:end]
                self.assertRegex(branch, rf"GivePoints\s*\(\s*{points}\s*\)")
                self.assertEqual(tuple(re.findall(r"PlaceItemType\s*\((bo_\w+)", branch)), drops)

    def test_port_precision_policy_uses_reduced_depth_and_clear_line(self) -> None:
        # The DOS candidate used full transx plus renderer FL_VISABLE.  The
        # write-only port deliberately compares reduced Q8 depth and replaces
        # FL_VISABLE occlusion with synchronous CheckLine.
        first = actor(1, depth_q8=0x200)
        second = actor(2, depth_q8=0x200)
        probe = LineProbe({1, 2})
        self.assertIs(pc.select_attack_target([first, second], probe), first)
        self.assertEqual(probe.calls, [1, 2])


class WeaponTimelineTests(unittest.TestCase):
    @staticmethod
    def begin(weapon: pc.Weapon, ammo: int = 20) -> pc.WeaponRuntime:
        player = pc.Player(
            ammo=ammo,
            weapon=weapon,
            chosen_weapon=weapon,
            best_weapon=weapon,
        )
        runtime = pc.WeaponRuntime(player)
        runtime.step(2, True)
        return runtime

    @staticmethod
    def advance_sixes(
        runtime: pc.WeaponRuntime,
        count: int,
        held: bool,
    ) -> tuple[tuple[int, pc.AttackAction], ...]:
        events: list[tuple[int, pc.AttackAction]] = []
        for step in range(1, count + 1):
            for action in runtime.step(6, held):
                events.append((step * 6, action))
        return tuple(events)

    def test_all_four_tap_timelines_and_ammo_counts(self) -> None:
        expected = {
            pc.Weapon.KNIFE: (((12, pc.AttackAction.KNIFE),), 20),
            pc.Weapon.PISTOL: (((12, pc.AttackAction.GUN),), 19),
            pc.Weapon.MACHINEGUN: (((12, pc.AttackAction.GUN),), 19),
            pc.Weapon.CHAINGUN: (
                ((12, pc.AttackAction.GUN), (18, pc.AttackAction.GUN)),
                18,
            ),
        }
        for weapon, wanted in expected.items():
            with self.subTest(weapon=weapon):
                runtime = self.begin(weapon)
                events = self.advance_sixes(runtime, 4, held=False)
                self.assertEqual((events, runtime.player.ammo), wanted)
                self.assertFalse(runtime.active)
                self.assertEqual(runtime.weapon_frame, 0)
                self.assertEqual(
                    runtime.weapon_shape,
                    pc.WEAPON_SHAPE_BASE[runtime.player.weapon],
                )

    def test_machinegun_hold_repeats_every_twelve_source_tics(self) -> None:
        runtime = self.begin(pc.Weapon.MACHINEGUN)
        events = self.advance_sixes(runtime, 6, held=True)
        self.assertEqual(
            events,
            ((12, pc.AttackAction.GUN), (24, pc.AttackAction.GUN),
             (36, pc.AttackAction.GUN)),
        )
        self.assertTrue(runtime.active)
        self.assertEqual(runtime.player.ammo, 17)

    def test_chaingun_hold_repeats_every_six_tics_after_windup(self) -> None:
        runtime = self.begin(pc.Weapon.CHAINGUN)
        events = self.advance_sixes(runtime, 6, held=True)
        self.assertEqual(
            events,
            tuple((tic, pc.AttackAction.GUN) for tic in (12, 18, 24, 30, 36)),
        )
        self.assertEqual(runtime.player.ammo, 15)

    def test_knife_and_pistol_do_not_repeat_while_held(self) -> None:
        for weapon in (pc.Weapon.KNIFE, pc.Weapon.PISTOL):
            with self.subTest(weapon=weapon):
                runtime = self.begin(weapon)
                self.advance_sixes(runtime, 4, held=True)
                self.assertFalse(runtime.active)
                runtime.step(6, True)
                self.assertFalse(runtime.active)
                runtime.step(0, False)
                runtime.step(2, True)
                self.assertTrue(runtime.active)

    def test_release_repress_during_machinegun_animation_does_not_loop(self) -> None:
        runtime = self.begin(pc.Weapon.MACHINEGUN)
        runtime.step(6, True)       # frame 0 -> 1
        runtime.step(0, False)      # remember release without consuming time
        self.assertEqual(runtime.step(6, True), (pc.AttackAction.GUN,))
        self.assertEqual(runtime.step(6, True), ())
        self.assertEqual(runtime.attack_frame, 3)
        runtime.step(6, True)
        self.assertFalse(runtime.active)
        runtime.step(2, True)
        self.assertTrue(runtime.active)  # held repress is a new edge after finish

    def test_machinegun_empty_ammo_finishes_and_falls_back_to_knife(self) -> None:
        runtime = self.begin(pc.Weapon.MACHINEGUN, ammo=2)
        events = self.advance_sixes(runtime, 6, held=True)
        self.assertEqual(events, ((12, pc.AttackAction.GUN), (24, pc.AttackAction.GUN)))
        self.assertFalse(runtime.active)
        self.assertEqual((runtime.player.ammo, runtime.player.weapon), (0, pc.Weapon.KNIFE))

    def test_chaingun_empty_ammo_uses_source_extra_frame_skip(self) -> None:
        runtime = self.begin(pc.Weapon.CHAINGUN, ammo=2)
        events = self.advance_sixes(runtime, 5, held=True)
        self.assertEqual(events, ((12, pc.AttackAction.GUN), (18, pc.AttackAction.GUN)))
        self.assertFalse(runtime.active)
        self.assertEqual(runtime.player.weapon, pc.Weapon.KNIFE)

    def test_exact_223_fixed_clock_reaches_pistol_shot_on_fifth_advance(self) -> None:
        runtime = self.begin(pc.Weapon.PISTOL)
        events = [runtime.step(tics, True) for tics in (2, 3, 2, 2, 3)]
        self.assertEqual(events[:-1], [(), (), (), ()])
        self.assertEqual(events[-1], (pc.AttackAction.GUN,))
        self.assertEqual(pc.fixed_tic_quanta(7), (2, 2, 3, 2, 2, 3, 2))

    def test_weapon_selection_lowest_available_and_idle_only(self) -> None:
        player = pc.Player(best_weapon=pc.Weapon.CHAINGUN)
        runtime = pc.WeaponRuntime(player)
        runtime.step(0, False, (pc.Weapon.CHAINGUN, pc.Weapon.KNIFE))
        self.assertEqual(player.weapon, pc.Weapon.KNIFE)
        runtime.step(0, True)
        runtime.step(0, True, (pc.Weapon.CHAINGUN,))
        self.assertEqual(player.weapon, pc.Weapon.KNIFE)

    def test_weapon_selection_rejects_unowned_and_all_keys_at_zero_ammo(self) -> None:
        player = pc.Player(ammo=8, best_weapon=pc.Weapon.PISTOL)
        runtime = pc.WeaponRuntime(player)
        runtime.choose_weapon((pc.Weapon.CHAINGUN,))
        self.assertEqual(player.weapon, pc.Weapon.PISTOL)
        player.ammo = 0
        runtime.choose_weapon((pc.Weapon.KNIFE,))
        self.assertEqual(player.weapon, pc.Weapon.PISTOL)

    def test_give_ammo_restores_chosen_only_at_attack_frame_zero(self) -> None:
        player = pc.Player(
            ammo=0,
            weapon=pc.Weapon.KNIFE,
            chosen_weapon=pc.Weapon.MACHINEGUN,
            best_weapon=pc.Weapon.MACHINEGUN,
        )
        pc.give_ammo(player, 4, attack_frame=1)
        self.assertEqual((player.ammo, player.weapon), (4, pc.Weapon.KNIFE))
        player.ammo = 0
        pc.give_ammo(player, 4, attack_frame=0)
        self.assertEqual((player.ammo, player.weapon), (4, pc.Weapon.MACHINEGUN))

    def test_weapon_shape_invariant_survives_ammo_and_weapon_pickups(self) -> None:
        player = pc.Player(
            ammo=0,
            weapon=pc.Weapon.KNIFE,
            chosen_weapon=pc.Weapon.MACHINEGUN,
            best_weapon=pc.Weapon.MACHINEGUN,
        )
        runtime = pc.WeaponRuntime(player)
        runtime.give_ammo(4)
        self.assertEqual(runtime.weapon_shape, 426)
        runtime.weapon_frame = 2
        runtime.give_weapon(pc.Weapon.CHAINGUN)
        self.assertEqual(runtime.weapon_shape, 433)


class TargetAndRngTests(unittest.TestCase):
    def test_target_filters_nonshootable_projection_and_strict_cone_edge(self) -> None:
        candidates = [
            actor(1, shootable=False, depth_q8=0x100),
            actor(2, visible=False, depth_q8=0x110),
            actor(3, center_delta=25, depth_q8=0x120),
            actor(4, center_delta=-25, depth_q8=0x130),
            actor(5, center_delta=24, depth_q8=0x140),
        ]
        probe = LineProbe({1, 2, 3, 4, 5})
        self.assertEqual(pc.select_attack_target(candidates, probe).actor_id, 5)
        self.assertEqual(probe.calls, [5])

    def test_nearest_clear_target_wins_independent_of_list_position(self) -> None:
        far = actor(1, depth_q8=0x300)
        near = actor(2, depth_q8=0x180)
        middle = actor(3, depth_q8=0x240)
        self.assertIs(pc.select_attack_target([far, near, middle], LineProbe({1, 2, 3})), near)

    def test_equal_reduced_depth_retains_linked_list_order(self) -> None:
        first = actor(1, depth_q8=0x200)
        second = actor(2, depth_q8=0x200)
        self.assertIs(pc.select_attack_target([first, second], LineProbe({1, 2})), first)
        self.assertIs(pc.select_attack_target([second, first], LineProbe({1, 2})), second)

    def test_near_occluded_target_does_not_mask_far_clear_target(self) -> None:
        near = actor(1, depth_q8=0x100, tile_x=1)
        far = actor(2, depth_q8=0x300, tile_x=3)
        probe = LineProbe({2})
        outcome = pc.gun_attack(
            [near, far], pc.Player(), pc.StaticPool(), pc.SequenceRng([0]), probe
        )
        self.assertEqual((outcome.target_id, outcome.hit, probe.calls), (2, True, [1, 2]))

    def test_knife_cannot_cross_an_opaque_line(self) -> None:
        target = actor(1, depth_q8=pc.KNIFE_RANGE_Q8)
        rng = pc.SequenceRng([])
        probe = LineProbe(set())
        outcome = pc.knife_attack([target], pc.Player(), pc.StaticPool(), rng, probe)
        self.assertEqual((outcome.hit, rng.draws, probe.calls), (False, 0, [1]))

    def test_knife_range_is_inclusive_and_uses_exactly_one_draw(self) -> None:
        player = pc.Player()
        target = actor(1, hitpoints=100, depth_q8=pc.KNIFE_RANGE_Q8)
        rng = pc.SequenceRng([255])
        outcome = pc.knife_attack([target], player, pc.StaticPool(), rng)
        self.assertEqual((outcome.hit, outcome.damage, target.hitpoints, rng.draws),
                         (True, 15, 85, 1))

    def test_knife_one_q8_beyond_range_consumes_no_rng(self) -> None:
        target = actor(1, depth_q8=pc.KNIFE_RANGE_Q8 + 1)
        rng = pc.SequenceRng([])
        outcome = pc.knife_attack([target], pc.Player(), pc.StaticPool(), rng)
        self.assertEqual((outcome.target_id, outcome.hit, rng.draws), (1, False, 0))

    def test_near_and_medium_gun_damage_divisors(self) -> None:
        cases = ((1, 63), (2, 42), (3, 42))
        for distance, damage in cases:
            with self.subTest(distance=distance):
                target = actor(1, tile_x=distance, x=distance << 16)
                rng = pc.SequenceRng([255])
                outcome = pc.gun_attack(
                    [target], pc.Player(), pc.StaticPool(), rng
                )
                self.assertEqual((outcome.damage, rng.draws), (damage, 1))

    def test_far_accuracy_threshold_is_inclusive_and_damage_draw_conditional(self) -> None:
        miss_target = actor(1, tile_x=4, x=4 << 16)
        miss_rng = pc.SequenceRng([47])
        miss = pc.gun_attack(
            [miss_target], pc.Player(), pc.StaticPool(), miss_rng
        )
        self.assertEqual((miss.hit, miss_rng.draws, miss_target.hitpoints), (False, 1, 100))

        hit_target = actor(1, tile_x=4, x=4 << 16)
        hit_rng = pc.SequenceRng([48, 255])
        hit = pc.gun_attack([hit_target], pc.Player(), pc.StaticPool(), hit_rng)
        self.assertEqual((hit.hit, hit.damage, hit_rng.draws), (True, 42, 2))

    def test_far_distance_21_can_hit_but_22_always_misses(self) -> None:
        target21 = actor(1, tile_x=21, x=21 << 16)
        rng21 = pc.SequenceRng([252, 0])
        self.assertTrue(pc.gun_attack([target21], pc.Player(), pc.StaticPool(), rng21).hit)
        target22 = actor(2, tile_x=22, x=22 << 16)
        rng22 = pc.SequenceRng([255])
        self.assertFalse(pc.gun_attack([target22], pc.Player(), pc.StaticPool(), rng22).hit)
        self.assertEqual((rng21.draws, rng22.draws), (2, 1))

    def test_no_target_or_blocked_target_consumes_no_gun_rng(self) -> None:
        for targets in ([], [actor(1, line_clear=False)]):
            with self.subTest(targets=len(targets)):
                rng = pc.SequenceRng([])
                outcome = pc.gun_attack(
                    targets, pc.Player(), pc.StaticPool(), rng
                )
                self.assertFalse(outcome.hit)
                self.assertEqual(rng.draws, 0)

    def test_zero_damage_is_a_hit_and_wakes_a_dormant_actor(self) -> None:
        target = actor(1, hitpoints=25, attack_mode=False, tile_x=1, x=1 << 16)
        rng = pc.SequenceRng([0])
        player = pc.Player()
        outcome = pc.gun_attack([target], player, pc.StaticPool(), rng)
        self.assertEqual(
            (outcome.hit, outcome.damage, target.hitpoints, target.attack_mode,
             target.first_sightings, player.made_noise),
            (True, 0, 25, True, 1, True),
        )


class DamageDeathScoreTests(unittest.TestCase):
    def test_dormant_damage_doubles_then_wakes_and_selects_pain_parity(self) -> None:
        target = actor(1, hitpoints=25, attack_mode=False)
        outcome = pc.damage_actor(target, 5, pc.Player(), pc.StaticPool())
        self.assertEqual(
            (outcome.result, outcome.applied_damage, target.hitpoints,
             target.attack_mode, target.first_sightings, target.state),
            (pc.DamageResult.PAIN, 10, 15, True, 1, "s_grdpain"),
        )

    def test_all_four_humanoid_classes_choose_both_pain_parities(self) -> None:
        for actor_class, pair in pc.PAIN_STATES.items():
            with self.subTest(actor_class=actor_class, parity="odd"):
                odd = actor(1, actor_class, hitpoints=20)
                pc.damage_actor(odd, 1, pc.Player(), pc.StaticPool())
                self.assertEqual((odd.hitpoints, odd.state, odd.ticcount), (19, pair[0], 10))
            with self.subTest(actor_class=actor_class, parity="even"):
                even = actor(1, actor_class, hitpoints=20)
                pc.damage_actor(even, 2, pc.Player(), pc.StaticPool())
                self.assertEqual((even.hitpoints, even.state, even.ticcount), (18, pair[1], 10))

    def test_dog_survives_without_a_pain_state(self) -> None:
        dog = actor(1, pc.ActorClass.DOG, hitpoints=5)
        original_state = dog.state
        outcome = pc.damage_actor(dog, 1, pc.Player(), pc.StaticPool())
        self.assertEqual((outcome.result, dog.hitpoints, dog.state),
                         (pc.DamageResult.PAIN, 4, original_state))

    def test_every_ordinary_class_kill_score_state_flags_and_drop(self) -> None:
        expected = {
            pc.ActorClass.GUARD: (100, "s_grddie1", pc.ITEM_CLIP2),
            pc.ActorClass.OFFICER: (400, "s_ofcdie1", pc.ITEM_CLIP2),
            pc.ActorClass.MUTANT: (700, "s_mutdie1", pc.ITEM_CLIP2),
            pc.ActorClass.SS: (500, "s_ssdie1", pc.ITEM_MACHINEGUN),
            pc.ActorClass.DOG: (200, "s_dogdie1", None),
        }
        for actor_class, wanted in expected.items():
            with self.subTest(actor_class=actor_class):
                player = pc.Player(best_weapon=pc.Weapon.PISTOL)
                pool = pc.StaticPool()
                target = actor(
                    1, actor_class, hitpoints=1,
                    x=12 << 16, y=9 << 16, tile_x=20, tile_y=20,
                )
                outcome = pc.damage_actor(target, 1, player, pool)
                drop_item = pool.slots[outcome.drop.index].item if outcome.drop else None
                self.assertEqual(
                    (outcome.result, player.score, player.kill_count, target.state,
                     target.tile_x, target.tile_y, target.shootable,
                     target.occupied, target.nonmark, drop_item),
                    (pc.DamageResult.KILLED, wanted[0], 1, wanted[1],
                     12, 9, False, False, True, wanted[2]),
                )

    def test_ss_drop_switches_to_clip_after_machinegun_is_owned(self) -> None:
        player = pc.Player(best_weapon=pc.Weapon.MACHINEGUN)
        pool = pc.StaticPool()
        outcome = pc.damage_actor(
            actor(1, pc.ActorClass.SS, hitpoints=1), 1, player, pool
        )
        self.assertEqual(pool.slots[outcome.drop.index].item, pc.ITEM_CLIP2)

    def test_second_damage_after_kill_cannot_score_count_or_drop_twice(self) -> None:
        player = pc.Player()
        pool = pc.StaticPool()
        target = actor(1, hitpoints=1)
        first = pc.damage_actor(target, 1, player, pool)
        second = pc.damage_actor(target, 1, player, pool)
        self.assertEqual((first.result, second.result),
                         (pc.DamageResult.KILLED, pc.DamageResult.REJECTED))
        self.assertEqual((player.score, player.kill_count, len(pool.slots)), (100, 1, 1))

    def test_class_score_carries_and_exact_extra_life_threshold(self) -> None:
        player = pc.Player(score=39_950, lives=3, next_extra=40_000)
        pc.damage_actor(actor(1, hitpoints=1), 1, player, pc.StaticPool())
        self.assertEqual((player.score, player.lives, player.next_extra),
                         (40_050, 4, 80_000))
        player = pc.Player(score=65_500, next_extra=100_000)
        pc.damage_actor(
            actor(1, pc.ActorClass.MUTANT, hitpoints=1),
            1, player, pc.StaticPool(),
        )
        self.assertEqual(player.score, 66_200)

    def test_multiple_thresholds_advance_even_when_lives_are_capped(self) -> None:
        player = pc.Player(score=39_900, lives=9, next_extra=40_000)
        pc.give_points(player, 80_100)
        self.assertEqual((player.score, player.lives, player.next_extra),
                         (120_000, 9, 160_000))

    def test_drop_allocation_failure_does_not_cancel_kill_or_score(self) -> None:
        seed = [pc.StaticSlot(index, 0, 1, "decor", False) for index in range(2)]
        pool = pc.StaticPool(seed, capacity=2)
        player = pc.Player()
        outcome = pc.damage_actor(actor(1, hitpoints=1), 1, player, pool)
        self.assertEqual((outcome.result, outcome.drop, player.score, player.kill_count),
                         (pc.DamageResult.KILLED, None, 100, 1))

    def test_pain_state_returns_to_class_chase_after_ten_tics(self) -> None:
        target = actor(1, hitpoints=20)
        pc.damage_actor(target, 1, pc.Player(), pc.StaticPool())
        advance = pc.advance_injury_state(target, 10)
        self.assertEqual(target.state, "s_grdchase1")
        self.assertEqual(advance.transitions, (("s_grdpain", "s_grdchase1"),))

    def test_every_death_chain_reaches_terminal_and_screams_once(self) -> None:
        expected = {
            pc.ActorClass.GUARD: (45, "s_grddie4", 0),
            pc.ActorClass.OFFICER: (44, "s_ofcdie5", 0),
            pc.ActorClass.MUTANT: (28, "s_mutdie5", 0),
            pc.ActorClass.SS: (45, "s_ssdie4", 0),
            pc.ActorClass.DOG: (45, "s_dogdead", 15),
        }
        for actor_class, (tics, terminal, countdown) in expected.items():
            with self.subTest(actor_class=actor_class):
                target = actor(1, actor_class, hitpoints=1)
                pc.damage_actor(target, 1, pc.Player(), pc.StaticPool())
                advance = pc.advance_injury_state(target, tics)
                self.assertEqual(
                    (target.state, target.ticcount, target.death_screams,
                     advance.actions),
                    (terminal, countdown, 1, ("death_scream",)),
                )

    def test_zero_tic_corpses_latch_and_dog_dead_self_loops(self) -> None:
        guard = actor(1, hitpoints=1)
        pc.damage_actor(guard, 1, pc.Player(), pc.StaticPool())
        pc.advance_injury_state(guard, 45)
        self.assertEqual(pc.advance_injury_state(guard, 100).transitions, ())

        dog = actor(2, pc.ActorClass.DOG, hitpoints=1)
        pc.damage_actor(dog, 1, pc.Player(), pc.StaticPool())
        pc.advance_injury_state(dog, 45)
        advance = pc.advance_injury_state(dog, 30)
        self.assertEqual(
            advance.transitions,
            (("s_dogdead", "s_dogdead"), ("s_dogdead", "s_dogdead")),
        )
        self.assertEqual(dog.death_screams, 1)


class StaticPoolTests(unittest.TestCase):
    def test_first_removed_slot_is_reused_before_append(self) -> None:
        seed = [
            pc.StaticSlot(0, 0, 1, "decor", False),
            pc.StaticSlot(0, 0, -1, "old"),
            pc.StaticSlot(0, 0, -1, "old"),
        ]
        pool = pc.StaticPool(seed)
        first = pool.place_item(pc.ITEM_CLIP2, 5, 6)
        second = pool.place_item(pc.ITEM_MACHINEGUN, 7, 8)
        self.assertEqual((first.index, first.reused, second.index, second.reused),
                         (1, True, 2, True))
        self.assertEqual(len(pool.slots), 3)

    def test_append_preserves_stable_high_water_identity(self) -> None:
        pool = pc.StaticPool([pc.StaticSlot(0, 0, 1, "decor", False)])
        placement = pool.place_item(pc.ITEM_CLIP2, 9, 10)
        self.assertEqual((placement.index, placement.reused, len(pool.slots)),
                         (1, False, 2))
        self.assertTrue(pool.slots[1].dirty)

    def test_capacity_boundaries_and_full_pool_behavior(self) -> None:
        for capacity in (254, 255, 256, 399, 400):
            with self.subTest(capacity=capacity):
                seed = [pc.StaticSlot(i, 0, 1, "decor", False) for i in range(capacity)]
                pool = pc.StaticPool(seed, capacity=capacity)
                self.assertIsNone(pool.place_item(pc.ITEM_CLIP2, 1, 1))
                pool.slots[-1].shapenum = -1
                placement = pool.place_item(pc.ITEM_CLIP2, 1, 1)
                self.assertEqual((placement.index, placement.reused),
                                 (capacity - 1, True))

    def test_unsupported_item_does_not_mutate_pool(self) -> None:
        pool = pc.StaticPool()
        self.assertIsNone(pool.place_item("bo_key1", 1, 2))
        self.assertEqual(pool.slots, [])

    def test_clip_collection_refusal_then_free_and_reuse(self) -> None:
        pool = pc.StaticPool()
        placement = pool.place_item(pc.ITEM_CLIP2, 1, 2)
        player = pc.Player(ammo=99)
        self.assertFalse(pool.collect(placement.index, player))
        self.assertNotEqual(pool.slots[placement.index].shapenum, -1)
        player.ammo = 98
        self.assertTrue(pool.collect(placement.index, player))
        self.assertEqual((player.ammo, pool.slots[placement.index].shapenum), (99, -1))
        replacement = pool.place_item(pc.ITEM_MACHINEGUN, 3, 4)
        self.assertEqual((replacement.index, replacement.reused),
                         (placement.index, True))

    def test_machinegun_drop_adds_ammo_and_equips_only_when_better(self) -> None:
        pool = pc.StaticPool()
        first = pool.place_item(pc.ITEM_MACHINEGUN, 1, 2)
        player = pc.Player(ammo=95, best_weapon=pc.Weapon.PISTOL)
        self.assertTrue(pool.collect(first.index, player))
        self.assertEqual(
            (player.ammo, player.weapon, player.chosen_weapon, player.best_weapon),
            (99, pc.Weapon.MACHINEGUN, pc.Weapon.MACHINEGUN, pc.Weapon.MACHINEGUN),
        )
        second = pool.place_item(pc.ITEM_MACHINEGUN, 1, 2)
        player.best_weapon = pc.Weapon.CHAINGUN
        player.weapon = player.chosen_weapon = pc.Weapon.CHAINGUN
        self.assertTrue(pool.collect(second.index, player))
        self.assertEqual(player.weapon, pc.Weapon.CHAINGUN)

    def test_reseed_discards_runtime_drops_and_restores_seed_prefix(self) -> None:
        seed = [
            pc.StaticSlot(1, 2, 5, "decor", False),
            pc.StaticSlot(3, 4, 7, "pickup", True),
        ]
        pool = pc.StaticPool(seed)
        pool.slots[1].shapenum = -1
        pool.place_item(pc.ITEM_CLIP2, 9, 9)
        pool.place_item(pc.ITEM_MACHINEGUN, 10, 10)
        self.assertEqual(len(pool.slots), 3)
        pool.reseed()
        self.assertEqual(pool.slots, seed)
        self.assertTrue(all(not slot.dirty for slot in pool.slots))


if __name__ == "__main__":
    unittest.main()
