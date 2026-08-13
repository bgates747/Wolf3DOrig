#!/usr/bin/env python3
"""Directed and deterministic randomized regression for Wolf3D gameplay."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import random
import re
import struct
import unittest

import gameplay_oracle as go


SEED = 0x574F4C46
RANDOM_CASES = int(os.environ.get("W3D_RANDOM_CASES", "10000"))
_root_override = os.environ.get("W3D_STAGED_ROOT")
_installed_root = (
    Path(__file__).resolve().parents[4]
    if len(Path(__file__).resolve().parents) > 4
    else Path.cwd()
)
STAGED_ROOT = (
    Path(_root_override)
    if _root_override
    else _installed_root
)
FIXTURE = STAGED_ROOT / "src/asm/wolf3d/src/wolf3d_fixture.inc"
GENERATOR = (
    STAGED_ROOT
    / "agonport/tools/wolf3d_assets/scripts/gen_render_fixture.py"
)
CLIP_GENERATOR = Path(__file__).resolve().with_name("generate_clip_vectors.py")


def brute_position_clear(
    tilemap: bytes | bytearray,
    doors: list[go.Door],
    pose: go.Pose,
    static_bits: bytes | bytearray | None = None,
) -> bool:
    x_low, x_high, y_low, y_high = go.player_bounds(pose)
    fixed_x_low = pose.x - go.PLAYER_RADIUS
    fixed_x_high = pose.x + go.PLAYER_RADIUS
    fixed_y_low = pose.y - go.PLAYER_RADIUS
    fixed_y_high = pose.y + go.PLAYER_RADIUS
    for y in range(y_low, y_high + 1):
        for x in range(x_low, x_high + 1):
            if not 0 <= x < go.MAP_SIZE or not 0 <= y < go.MAP_SIZE:
                return False
            value = tilemap[y * go.MAP_SIZE + x]
            if value == go.TILE_OPEN:
                if (
                    go.static_tile_blocked(static_bits, x, y)
                    and abs(pose.x - go.fixed(x)) <= go.PHYSICAL_OBJECT_CLEARANCE
                    and abs(pose.y - go.fixed(y)) <= go.PHYSICAL_OBJECT_CLEARANCE
                ):
                    return False
                continue
            if not go.TILE_DOOR_MIN <= value <= go.TILE_DOOR_MAX:
                return False
            index = value & go.TILE_DOOR_MASK
            if index >= len(doors):
                return False

            # Deliberately spell out the renderer geometry instead of calling
            # the optimized oracle predicate. This scans every AABB-covered
            # tile and remains an independent randomized reference.
            door = doors[index]
            if door.position == 0xFFFF:
                continue
            if door.vertical:
                plane = door.tile_x * go.TILE_GLOBAL + 0x8000
                panel_start = door.tile_y * go.TILE_GLOBAL + door.position + 1
                panel_end = door.tile_y * go.TILE_GLOBAL + 0xFFFF
                overlaps = (
                    fixed_x_low <= plane <= fixed_x_high
                    and fixed_y_high >= panel_start
                    and fixed_y_low <= panel_end
                )
            else:
                plane = door.tile_y * go.TILE_GLOBAL + 0x8000
                panel_start = door.tile_x * go.TILE_GLOBAL + door.position + 1
                panel_end = door.tile_x * go.TILE_GLOBAL + 0xFFFF
                overlaps = (
                    fixed_y_low <= plane <= fixed_y_high
                    and fixed_x_high >= panel_start
                    and fixed_x_low <= panel_end
                )
            if overlaps:
                return False
    return True


def brute_clip(
    tilemap: bytes | bytearray,
    doors: list[go.Door],
    pose: go.Pose,
    dx: int,
    dy: int,
    static_bits: bytes | bytearray | None = None,
) -> tuple[go.Pose, str]:
    attempts = (
        (go.Pose(pose.x + dx, pose.y + dy, pose.angle), "xy"),
        (go.Pose(pose.x + dx, pose.y, pose.angle), "x"),
        (go.Pose(pose.x, pose.y + dy, pose.angle), "y"),
    )
    for candidate, path in attempts:
        if brute_position_clear(tilemap, doors, candidate, static_bits):
            return candidate, path
    return pose, "blocked"


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
        db = re.search(r"\bdb\s+(.+)$", code, re.IGNORECASE)
        if db:
            values.extend(int(item.strip(), 0) for item in db.group(1).split(","))
    return bytes(values)


def load_generator():
    spec = importlib.util.spec_from_file_location("staged_fixture_generator", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_clip_generator():
    spec = importlib.util.spec_from_file_location(
        "staged_clip_vector_generator", CLIP_GENERATOR
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {CLIP_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CollisionDirectedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tilemap = go.empty_bordered_map()
        self.doors: list[go.Door] = []

    def test_radius_matches_tuned_contract(self) -> None:
        self.assertEqual(go.PLAYER_RADIUS, 0x4800)

    def test_touching_wall_fraction_threshold(self) -> None:
        self.tilemap[10 * 64 + 11] = 1
        just_clear = go.Pose(go.fixed(10, 0xB7FF), go.fixed(10))
        touching = go.Pose(go.fixed(10, 0xB800), go.fixed(10))
        self.assertTrue(go.player_position_clear(self.tilemap, self.doors, just_clear))
        self.assertFalse(go.player_position_clear(self.tilemap, self.doors, touching))

    def test_outside_map_blocks_even_without_border(self) -> None:
        open_map = bytes(64 * 64)
        self.assertFalse(
            go.player_position_clear(open_map, [], go.Pose(0x1000, go.fixed(20)))
        )

    def install_door(self, *, vertical: bool = True) -> go.Door:
        door = go.Door(11, 10, vertical, 0)
        self.doors.append(door)
        self.tilemap[10 * 64 + 11] = 0x80
        return door

    def test_vertical_closed_plane_contact_from_both_sides(self) -> None:
        self.install_door()
        plane = go.fixed(11)
        panel_y = go.fixed(10)
        cases = (
            (plane - go.PLAYER_RADIUS - 1, True, "left one unit clear"),
            (plane - go.PLAYER_RADIUS, False, "left inclusive contact"),
            (plane + go.PLAYER_RADIUS + 1, True, "right one unit clear"),
            (plane + go.PLAYER_RADIUS, False, "right inclusive contact"),
        )
        for x, expected, label in cases:
            with self.subTest(label=label):
                self.assertEqual(
                    go.player_position_clear(
                        self.tilemap, self.doors, go.Pose(x, panel_y)
                    ),
                    expected,
                )

    def test_horizontal_closed_plane_contact_from_both_sides(self) -> None:
        door = self.install_door(vertical=False)
        # A horizontal door occupies y=tile_y+0.5 and its panel runs along X.
        plane = go.fixed(door.tile_y)
        panel_x = go.fixed(door.tile_x)
        cases = (
            (plane - go.PLAYER_RADIUS - 1, True, "north one unit clear"),
            (plane - go.PLAYER_RADIUS, False, "north inclusive contact"),
            (plane + go.PLAYER_RADIUS + 1, True, "south one unit clear"),
            (plane + go.PLAYER_RADIUS, False, "south inclusive contact"),
        )
        for y, expected, label in cases:
            with self.subTest(label=label):
                self.assertEqual(
                    go.player_position_clear(
                        self.tilemap, self.doors, go.Pose(panel_x, y)
                    ),
                    expected,
                )

    def test_closed_door_well_is_not_a_solid_tile(self) -> None:
        self.install_door()
        y = go.fixed(10)
        for fraction in (0x1000, 0xF000):
            with self.subTest(fraction=fraction):
                self.assertTrue(
                    go.player_position_clear(
                        self.tilemap, self.doors, go.Pose(go.fixed(11, fraction), y)
                    )
                )
        self.assertFalse(
            go.player_position_clear(
                self.tilemap, self.doors, go.Pose(go.fixed(11), y)
            )
        )

    def test_partial_vertical_gap_and_first_panel_fraction_threshold(self) -> None:
        door = self.install_door()
        door.position = 0xC000
        plane = go.fixed(11)
        # Radius 0x4800 makes these upper AABB edges exactly C000/C001.
        last_gap = go.Pose(plane, go.fixed(10, 0x7800))
        first_panel = go.Pose(plane, go.fixed(10, 0x7801))
        self.assertTrue(go.player_position_clear(self.tilemap, self.doors, last_gap))
        self.assertFalse(
            go.player_position_clear(self.tilemap, self.doors, first_panel)
        )

    def test_partial_horizontal_gap_and_first_panel_fraction_threshold(self) -> None:
        door = self.install_door(vertical=False)
        door.position = 0xC000
        plane = go.fixed(door.tile_y)
        last_gap = go.Pose(go.fixed(door.tile_x, 0x7800), plane)
        first_panel = go.Pose(go.fixed(door.tile_x, 0x7801), plane)
        self.assertTrue(go.player_position_clear(self.tilemap, self.doors, last_gap))
        self.assertFalse(
            go.player_position_clear(self.tilemap, self.doors, first_panel)
        )

    def test_position_ffff_is_clear_independent_of_action(self) -> None:
        door = self.install_door()
        endpoint_contact = go.Pose(go.fixed(11), go.fixed(10, 0xB7FF))
        door.position = 0xFFFE
        self.assertFalse(
            go.player_position_clear(self.tilemap, self.doors, endpoint_contact)
        )
        door.position = 0xFFFF
        for action in (
            go.DOOR_CLOSED,
            go.DOOR_OPENING,
            go.DOOR_OPEN,
            go.DOOR_CLOSING,
        ):
            with self.subTest(action=action):
                door.action = action
                self.assertTrue(
                    go.player_position_clear(
                        self.tilemap, self.doors, endpoint_contact
                    )
                )

    def test_missing_and_reserved_door_slots_block(self) -> None:
        pose = go.Pose(go.fixed(11), go.fixed(10))
        for value in (0x80, 0x81, 0xBF, 0xC0, 0xFF):
            with self.subTest(value=value):
                self.tilemap[10 * 64 + 11] = value
                self.assertFalse(go.player_position_clear(self.tilemap, [], pose))


class ClipMoveDirectedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tilemap = go.empty_bordered_map()
        self.pose = go.Pose(go.fixed(10), go.fixed(10), 17)

    def test_full_vector_wins(self) -> None:
        result, path = go.clip_move(self.tilemap, [], self.pose, 0x1000, -0x0800)
        self.assertEqual(path, "xy")
        self.assertEqual(result, go.Pose(self.pose.x + 0x1000, self.pose.y - 0x0800, 17))

    def test_x_slide_wins_before_y(self) -> None:
        # Candidate's Y crosses the wall row; X alone remains clear.
        self.tilemap[11 * 64 + 10] = 1
        self.tilemap[11 * 64 + 11] = 1
        result, path = go.clip_move(self.tilemap, [], self.pose, 0x2000, 0x4000)
        self.assertEqual(path, "x")
        self.assertEqual((result.x, result.y), (self.pose.x + 0x2000, self.pose.y))

    def test_y_slide_when_x_blocked(self) -> None:
        self.tilemap[10 * 64 + 11] = 1
        self.tilemap[11 * 64 + 11] = 1
        result, path = go.clip_move(self.tilemap, [], self.pose, 0x4000, 0x2000)
        self.assertEqual(path, "y")
        self.assertEqual((result.x, result.y), (self.pose.x, self.pose.y + 0x2000))

    def test_fully_blocked_preserves_pose(self) -> None:
        self.tilemap[10 * 64 + 11] = 1
        self.tilemap[11 * 64 + 10] = 1
        self.tilemap[11 * 64 + 11] = 1
        result, path = go.clip_move(self.tilemap, [], self.pose, 0x4000, 0x4000)
        self.assertEqual(path, "blocked")
        self.assertEqual(result, self.pose)


class ClipVectorGeneratorTests(unittest.TestCase):
    def test_packed_door_geometry_cases_keep_40_byte_abi(self) -> None:
        generator = load_clip_generator()
        records = generator.build_vectors(0, include_zero_delta=False)
        self.assertEqual(generator.RECORD.size, 40)
        self.assertEqual(len(records), 27)
        for sequence, record in enumerate(records):
            self.assertEqual(len(record), 40)
            self.assertEqual(int.from_bytes(record[32:36], "little"), sequence)
            self.assertEqual(record[37:40], b"\0\0\0")

        # Directed door records begin after eleven wall/static records. They
        # retain the patched cell and carry orientation in former pad byte 36.
        door_records = records[11:]
        self.assertTrue(all(record[1:4] == bytes((11, 10, 0x80))
                            for record in door_records))
        self.assertTrue(all(record[36] == 1 for record in records[11:22]))
        self.assertTrue(all(record[36] == 0 for record in records[22:27]))

        def expected(index: int) -> tuple[int, int]:
            unpacked = generator.RECORD.unpack(records[index])
            return unpacked[6], unpacked[14]  # moved/A, starting-position clear

        self.assertEqual(expected(11), (0, 1))  # vertical left contact blocks
        self.assertEqual(expected(12), (1, 0))  # can escape existing contact
        self.assertEqual(expected(13), (0, 1))  # vertical right contact blocks
        self.assertEqual(expected(15), (1, 1))  # left well entry passes
        self.assertEqual(expected(16), (1, 1))  # right well entry passes
        self.assertEqual(expected(17), (0, 0))  # closed center is occupied
        self.assertEqual(expected(18), (1, 1))  # q=C000 gap endpoint passes
        self.assertEqual(expected(19), (0, 1))  # q=C001 panel start blocks
        self.assertEqual(expected(20), (0, 1))  # p=FFFE leaves q=FFFF panel
        self.assertEqual(expected(21), (1, 1))  # p=FFFF is entirely clear
        self.assertEqual(expected(22), (0, 1))  # horizontal north contact
        self.assertEqual(expected(23), (0, 1))  # horizontal south contact
        self.assertEqual(expected(24), (1, 1))  # horizontal gap endpoint
        self.assertEqual(expected(25), (0, 1))  # horizontal panel start
        self.assertEqual(expected(26), (1, 1))  # horizontal well entry


class StaticCollisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tilemap = go.empty_bordered_map()
        self.bits = go.empty_static_blocking_bits()

    def test_exact_contact_matches_wall_semantics(self) -> None:
        go.set_static_blocked(self.bits, 11, 10)
        just_clear = go.Pose(go.fixed(11, 0x37FF), go.fixed(10))
        touching = go.Pose(go.fixed(11, 0x3800), go.fixed(10))
        self.assertTrue(go.player_position_clear(
            self.tilemap, [], just_clear, static_blocking_bits=self.bits
        ))
        self.assertFalse(go.player_position_clear(
            self.tilemap, [], touching, static_blocking_bits=self.bits
        ))

    def test_static_bit_does_not_poison_map_or_door_semantics(self) -> None:
        go.set_static_blocked(self.bits, 11, 10)
        self.assertEqual(self.tilemap[10 * 64 + 11], go.TILE_OPEN)
        self.assertTrue(go.tile_is_clear(self.tilemap, [], 12, 10, self.bits))
        self.assertFalse(go.tile_is_clear(self.tilemap, [], 11, 10, self.bits))

    def test_static_bit_is_only_consulted_for_an_open_map_byte(self) -> None:
        door = go.Door(11, 10, True, 0, position=0xFFFF)
        self.tilemap[10 * 64 + 11] = 0x80
        go.set_static_blocked(self.bits, 11, 10)
        pose = go.Pose(go.fixed(11), go.fixed(10))
        self.assertTrue(
            go.player_position_clear(
                self.tilemap, [door], pose, static_blocking_bits=self.bits
            )
        )

    def test_static_blocker_participates_in_clipmove_sliding(self) -> None:
        go.set_static_blocked(self.bits, 10, 11)
        pose = go.Pose(go.fixed(10), go.fixed(10))
        result, path = go.clip_move(
            self.tilemap, [], pose, 0x2000, 0xB800, self.bits
        )
        self.assertEqual(path, "x")
        self.assertEqual((result.x, result.y), (pose.x + 0x2000, pose.y))


class PickupStateTests(unittest.TestCase):
    @staticmethod
    def pickup(item: int, *, x: int = 10, y: int = 10) -> go.StaticObject:
        return go.StaticObject(x, y, 20, go.STATIC_FLAG_BONUS, item)

    def test_contact_uses_player_aabb_and_removed_sentinel(self) -> None:
        pose = go.Pose(go.fixed(10, 0xB800), go.fixed(10))
        pickup = self.pickup(go.ITEM_CROSS, x=11)
        dressing = go.StaticObject(11, 10, 3, 0, 0)
        player = go.PlayerState()
        self.assertEqual(
            go.collect_overlapping_pickups([dressing, pickup], pose, player), [1]
        )
        self.assertEqual(pickup.shapenum, -1)
        self.assertTrue(pickup.dirty)
        self.assertEqual(player.score, 100)

    def test_capacity_rejections_leave_pickup_active(self) -> None:
        cases = (
            (go.ITEM_ALPO, go.PlayerState(health=100)),
            (go.ITEM_FIRSTAID, go.PlayerState(health=100)),
            (go.ITEM_FOOD, go.PlayerState(health=100)),
            (go.ITEM_GIBS, go.PlayerState(health=11)),
            (go.ITEM_CLIP, go.PlayerState(ammo=99)),
            (go.ITEM_CLIP2, go.PlayerState(ammo=99)),
        )
        for item, player in cases:
            with self.subTest(item=item):
                pickup = self.pickup(item)
                self.assertFalse(go.apply_pickup(pickup, player))
                self.assertEqual(pickup.shapenum, 20)
                self.assertFalse(pickup.dirty)

    def test_health_ammo_key_and_weapon_effects(self) -> None:
        player = go.PlayerState(health=50, ammo=90)
        self.assertTrue(go.apply_pickup(self.pickup(go.ITEM_FIRSTAID), player))
        self.assertEqual(player.health, 75)
        self.assertTrue(go.apply_pickup(self.pickup(go.ITEM_CLIP), player))
        self.assertEqual(player.ammo, 98)
        self.assertTrue(go.apply_pickup(self.pickup(go.ITEM_KEY3), player))
        self.assertEqual(player.key_flags, 4)
        self.assertTrue(go.apply_pickup(self.pickup(go.ITEM_MACHINEGUN), player))
        self.assertEqual((player.ammo, player.weapon, player.best_weapon), (99, 2, 2))
        self.assertEqual(
            player.hud_dirty,
            go.HUD_DIRTY_HEALTH | go.HUD_DIRTY_AMMO |
            go.HUD_DIRTY_KEYS | go.HUD_DIRTY_WEAPON,
        )

    def test_ammo_from_empty_restores_chosen_weapon(self) -> None:
        player = go.PlayerState(ammo=0, weapon=0, best_weapon=3,
                                chosen_weapon=3)
        self.assertTrue(go.apply_pickup(self.pickup(go.ITEM_CLIP), player))
        self.assertEqual((player.ammo, player.weapon), (8, 3))
        self.assertEqual(player.hud_dirty,
                         go.HUD_DIRTY_AMMO | go.HUD_DIRTY_WEAPON)

    def test_treasure_threshold_and_fullheal(self) -> None:
        player = go.PlayerState(health=1, ammo=80, score=39_900)
        self.assertTrue(go.apply_pickup(self.pickup(go.ITEM_CROSS), player))
        self.assertEqual((player.score, player.lives, player.next_extra),
                         (40_000, 4, 80_000))
        self.assertEqual(player.treasure_count, 1)
        self.assertTrue(go.apply_pickup(self.pickup(go.ITEM_FULLHEAL), player))
        self.assertEqual((player.health, player.ammo, player.lives), (100, 99, 5))
        self.assertEqual(player.treasure_count, 2)
        self.assertTrue(player.hud_dirty & go.HUD_DIRTY_SCORE)
        self.assertTrue(player.hud_dirty & go.HUD_DIRTY_LIVES)

    def test_extra_lives_cap_at_nine_but_thresholds_and_treasure_advance(self) -> None:
        player = go.PlayerState(score=39_900, lives=9)
        self.assertTrue(go.apply_pickup(self.pickup(go.ITEM_CROSS), player))
        self.assertEqual((player.score, player.next_extra, player.lives),
                         (40_000, 80_000, 9))
        self.assertEqual(player.treasure_count, 1)
        self.assertFalse(player.hud_dirty & go.HUD_DIRTY_LIVES)

        self.assertTrue(go.apply_pickup(self.pickup(go.ITEM_FULLHEAL), player))
        self.assertEqual(player.lives, 9)
        self.assertEqual(player.treasure_count, 2)

    def test_gibs_and_food_saturate_by_original_rules(self) -> None:
        low = go.PlayerState(health=10)
        self.assertTrue(go.apply_pickup(self.pickup(go.ITEM_GIBS), low))
        self.assertEqual(low.health, 11)
        hungry = go.PlayerState(health=95)
        self.assertTrue(go.apply_pickup(self.pickup(go.ITEM_FOOD), hungry))
        self.assertEqual(hungry.health, 100)


class RandomCollisionAndClipTests(unittest.TestCase):
    def test_random_against_brute_reference(self) -> None:
        rng = random.Random(SEED)
        for sequence in range(RANDOM_CASES):
            tilemap = go.empty_bordered_map()
            static_bits = go.empty_static_blocking_bits()
            for _ in range(rng.randrange(0, 20)):
                x, y = rng.randrange(1, 63), rng.randrange(1, 63)
                tilemap[y * 64 + x] = rng.randrange(1, 0x80)
            for _ in range(rng.randrange(0, 10)):
                go.set_static_blocked(
                    static_bits, rng.randrange(1, 63), rng.randrange(1, 63)
                )
            doors: list[go.Door] = []
            for index in range(rng.randrange(0, 5)):
                x, y = rng.randrange(2, 62), rng.randrange(2, 62)
                door = go.Door(
                    x,
                    y,
                    bool(rng.getrandbits(1)),
                    rng.randrange(6),
                    rng.randrange(4),
                    rng.randrange(0x10000),
                    121,
                )
                if rng.randrange(5) == 0:
                    door.action, door.position = go.DOOR_OPEN, 0xFFFF
                doors.append(door)
                tilemap[y * 64 + x] = 0x80 | index
            pose = go.Pose(
                go.fixed(rng.randrange(1, 63), rng.randrange(0x10000)),
                go.fixed(rng.randrange(1, 63), rng.randrange(0x10000)),
                rng.randrange(360),
            )
            dx, dy = rng.randrange(-0x6000, 0x6001), rng.randrange(-0x6000, 0x6001)
            with self.subTest(sequence=sequence):
                self.assertEqual(
                    go.player_position_clear(
                        tilemap, doors, pose, static_blocking_bits=static_bits
                    ),
                    brute_position_clear(tilemap, doors, pose, static_bits),
                )
                self.assertEqual(
                    go.clip_move(tilemap, doors, pose, dx, dy, static_bits),
                    brute_clip(tilemap, doors, pose, dx, dy, static_bits),
                )


class DoorTimingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.player_away = go.Pose(go.fixed(20), go.fixed(20))

    def test_global_step_cycle_is_exact_rational_average(self) -> None:
        simulation = go.DoorSimulation([])
        deltas = [simulation._next_delta() for _ in range(12)]
        self.assertEqual(deltas, [0x955, 0x955, 0x956] * 4)
        self.assertEqual(sum(deltas), 4 * 7168)

    def test_full_open_travel_and_saturation(self) -> None:
        door = go.Door(10, 10, True, 0, action=go.DOOR_OPENING)
        simulation = go.DoorSimulation([door])
        for frame in range(1, 28):
            simulation.tick(self.player_away)
            self.assertEqual(door.action, go.DOOR_OPENING, frame)
            self.assertLess(door.position, 0xFFFF)
        simulation.tick(self.player_away)
        self.assertEqual(door.action, go.DOOR_OPEN)
        self.assertEqual(door.position, 0xFFFF)
        self.assertEqual(door.timer, 0)

    def test_exact_ffff_sum_after_close_reversal_is_immediately_open(self) -> None:
        door = go.Door(
            10, 10, True, 0, action=go.DOOR_OPEN, position=0xFFFF
        )
        simulation = go.DoorSimulation([door], phase=0)
        self.assertTrue(go.operate_door(door, self.player_away))
        simulation.tick(self.player_away)  # phase 0: subtract 0955
        self.assertEqual((door.action, door.position), (go.DOOR_CLOSING, 0xF6AA))
        self.assertTrue(go.operate_door(door, self.player_away))
        simulation.tick(self.player_away)  # phase 1: add 0955 -> exactly FFFF
        self.assertEqual((door.action, door.position), (go.DOOR_OPEN, 0xFFFF))
        self.assertEqual(door.timer, 0)

    def test_open_wait_is_129_frames_then_closing(self) -> None:
        door = go.Door(10, 10, True, 0, action=go.DOOR_OPEN, position=0xFFFF)
        simulation = go.DoorSimulation([door])
        for frame in range(1, 129):
            simulation.tick(self.player_away)
            self.assertEqual(door.action, go.DOOR_OPEN, frame)
        self.assertEqual(door.timer, 896)
        simulation.tick(self.player_away)
        self.assertEqual(door.timer, 900)
        self.assertEqual(door.action, go.DOOR_CLOSING)

    def test_complete_cycle_frames(self) -> None:
        door = go.Door(10, 10, True, 0, action=go.DOOR_OPENING)
        simulation = go.DoorSimulation([door])
        states = []
        for frame in range(1, 220):
            simulation.tick(self.player_away)
            states.append((frame, door.action, door.position))
            if door.action == go.DOOR_CLOSED:
                break
        self.assertEqual(states[-1][0], 185)  # 28 open + 129 wait + 28 close
        self.assertEqual(states[-1][1:], (go.DOOR_CLOSED, 0))

    def test_fully_open_position_has_no_slab_to_defer_close(self) -> None:
        door = go.Door(
            10,
            10,
            True,
            0,
            action=go.DOOR_OPEN,
            position=0xFFFF,
            timer=896,
        )
        simulation = go.DoorSimulation([door])
        in_door = go.Pose(go.fixed(10), go.fixed(10))
        simulation.tick(in_door)
        self.assertEqual(door.action, go.DOOR_CLOSING)
        self.assertEqual(door.timer, 900)

    def test_closing_obstruction_reopens_without_position_jump(self) -> None:
        door = go.Door(10, 10, False, 0, action=go.DOOR_CLOSING, position=0x8000)
        simulation = go.DoorSimulation([door])
        in_door = go.Pose(go.fixed(10), go.fixed(10))
        simulation.tick(in_door)
        self.assertEqual((door.action, door.position, door.timer), (go.DOOR_OPENING, 0x8000, 0))

    def test_closing_uses_exact_gap_and_first_panel_threshold(self) -> None:
        plane = go.fixed(10)
        last_gap = go.Pose(go.fixed(10, 0x3800), plane)
        first_panel = go.Pose(go.fixed(10, 0x3801), plane)

        clear_door = go.Door(
            10, 10, False, 0, action=go.DOOR_CLOSING, position=0x8000
        )
        self.assertFalse(go.player_obstructs(clear_door, last_gap))
        simulation = go.DoorSimulation([clear_door])
        simulation.tick(last_gap)
        self.assertEqual(clear_door.action, go.DOOR_CLOSING)
        self.assertLess(clear_door.position, 0x8000)

        blocked_door = go.Door(
            10, 10, False, 0, action=go.DOOR_CLOSING, position=0x8000
        )
        self.assertTrue(go.player_obstructs(blocked_door, first_panel))
        simulation = go.DoorSimulation([blocked_door])
        simulation.tick(first_panel)
        self.assertEqual(
            (blocked_door.action, blocked_door.position, blocked_door.timer),
            (go.DOOR_OPENING, 0x8000, 0),
        )

    def test_dirty_tracks_only_wire_visible_changes(self) -> None:
        closed = go.Door(10, 10, True, 0)
        simulation = go.DoorSimulation([closed])
        simulation.tick(self.player_away)
        self.assertFalse(closed.dirty)
        closed.action = go.DOOR_OPENING
        simulation.tick(self.player_away)
        self.assertTrue(closed.dirty)


class UseAndLockTests(unittest.TestCase):
    def test_exact_angle_sector_boundaries(self) -> None:
        pose = go.Pose(go.fixed(20), go.fixed(30))
        expectations = {
            0: (21, 30),
            44: (21, 30),
            45: (20, 29),
            134: (20, 29),
            135: (19, 30),
            224: (19, 30),
            225: (20, 31),
            315: (20, 31),
            316: (21, 30),
            359: (21, 30),
        }
        for angle, expected in expectations.items():
            with self.subTest(angle=angle):
                self.assertEqual(go.adjacent_tile(go.Pose(pose.x, pose.y, angle)), expected)

    def test_lock_matrix(self) -> None:
        for lock in range(1, 5):
            for flags in range(16):
                with self.subTest(lock=lock, flags=flags):
                    self.assertEqual(
                        go.lock_allows(lock, flags), bool(flags & (1 << (lock - 1)))
                    )
        self.assertTrue(go.lock_allows(0, 0))
        self.assertTrue(go.lock_allows(5, 0))
        self.assertFalse(go.lock_allows(6, 0xFF))
        self.assertFalse(go.lock_allows(255, 0xFF))

    def test_operate_action_matrix(self) -> None:
        player = go.Pose(go.fixed(20), go.fixed(20))
        expected = {
            go.DOOR_CLOSED: go.DOOR_OPENING,
            go.DOOR_OPENING: go.DOOR_OPENING,
            go.DOOR_OPEN: go.DOOR_CLOSING,
            go.DOOR_CLOSING: go.DOOR_OPENING,
        }
        for action, result in expected.items():
            door = go.Door(10, 10, True, 0, action=action, position=0x8000)
            changed = go.operate_door(door, player)
            with self.subTest(action=action):
                self.assertEqual(door.action, result)
                self.assertEqual(changed, action != go.DOOR_OPENING)

    def test_fully_open_door_can_start_closing_with_player_in_well(self) -> None:
        door = go.Door(10, 10, True, 0, action=go.DOOR_OPEN, position=0xFFFF)
        player = go.Pose(go.fixed(10), go.fixed(10))
        self.assertTrue(go.operate_door(door, player))
        self.assertEqual(door.action, go.DOOR_CLOSING)

    def test_use_edge_is_one_shot_until_sampled_release(self) -> None:
        edge = go.UseEdge()
        self.assertEqual(
            [edge.sample(value) for value in (False, True, True, True, False, False, True)],
            [False, True, False, False, False, False, True],
        )

    def test_open_current_cell_uses_original_adjacent_lookup(self) -> None:
        tilemap = go.empty_bordered_map()
        player = go.Pose(go.fixed(20), go.fixed(20), 0)
        door = go.Door(21, 20, True, 0)
        tilemap[20 * 64 + 21] = 0x80
        self.assertEqual(go.use_adjacent_door(tilemap, [door], player), 0)
        self.assertEqual(door.action, go.DOOR_OPENING)

    def test_adjacent_lookup_rejects_invalid_index(self) -> None:
        tilemap = go.empty_bordered_map()
        player = go.Pose(go.fixed(20), go.fixed(20), 0)
        door = go.Door(21, 20, True, 0)
        tilemap[20 * 64 + 21] = 0x81
        self.assertIsNone(go.use_adjacent_door(tilemap, [door], player))
        self.assertEqual(door.action, go.DOOR_CLOSED)

    def test_door_is_usable_from_both_wells(self) -> None:
        tilemap = go.empty_bordered_map()
        tilemap[20 * 64 + 21] = 0x80
        cases = (
            (go.fixed(21, 0x2000), 0, "near well facing through"),
            (go.fixed(21, 0xE000), 180, "far well facing back"),
        )
        for x, angle, label in cases:
            with self.subTest(label=label):
                door = go.Door(21, 20, True, 0)
                player = go.Pose(x, go.fixed(20), angle)
                self.assertEqual(go.use_adjacent_door(tilemap, [door], player), 0)
                self.assertEqual(door.action, go.DOOR_OPENING)

    def test_door_is_usable_immediately_outside_both_sides(self) -> None:
        tilemap = go.empty_bordered_map()
        tilemap[20 * 64 + 21] = 0x80
        cases = (
            (go.fixed(20, 0xFFFF), 0, "west side facing east"),
            (go.fixed(22, 0), 180, "east side facing west"),
        )
        for x, angle, label in cases:
            with self.subTest(label=label):
                door = go.Door(21, 20, True, 0)
                player = go.Pose(x, go.fixed(20), angle)
                self.assertEqual(go.use_adjacent_door(tilemap, [door], player), 0)
                self.assertEqual(door.action, go.DOOR_OPENING)

    def test_current_door_lookup_is_orientation_independent(self) -> None:
        tilemap = go.empty_bordered_map()
        tilemap[20 * 64 + 21] = 0x80
        for angle in (0, 44, 45, 90, 135, 180, 225, 270, 315, 316, 359):
            with self.subTest(angle=angle):
                door = go.Door(21, 20, True, 0)
                player = go.Pose(go.fixed(21, 0x2000), go.fixed(20), angle)
                self.assertEqual(go.use_adjacent_door(tilemap, [door], player), 0)
                self.assertEqual(door.action, go.DOOR_OPENING)

    def test_valid_current_door_takes_precedence_over_adjacent_door(self) -> None:
        tilemap = go.empty_bordered_map()
        current = go.Door(21, 20, True, 0)
        adjacent = go.Door(22, 20, True, 0)
        tilemap[20 * 64 + 21] = 0x80
        tilemap[20 * 64 + 22] = 0x81
        player = go.Pose(go.fixed(21, 0xE000), go.fixed(20), 0)
        self.assertEqual(go.use_adjacent_door(tilemap, [current, adjacent], player), 0)
        self.assertEqual(current.action, go.DOOR_OPENING)
        self.assertEqual(adjacent.action, go.DOOR_CLOSED)

    def test_invalid_current_door_index_fails_closed_without_fallback(self) -> None:
        tilemap = go.empty_bordered_map()
        adjacent = go.Door(21, 20, True, 0)
        tilemap[20 * 64 + 20] = 0x81
        tilemap[20 * 64 + 21] = 0x80
        player = go.Pose(go.fixed(20, 0xE000), go.fixed(20), 0)
        self.assertIsNone(go.use_adjacent_door(tilemap, [adjacent], player))
        self.assertEqual(adjacent.action, go.DOOR_CLOSED)


@unittest.skipUnless(FIXTURE.exists() and GENERATOR.exists(), "staged fixture unavailable")
class GeneratorAndWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = FIXTURE.read_text()
        cls.initial_doors = parse_label_bytes(
            cls.text, "w3d_fixture_initial_doors", "w3d_fixture_initial_doors_end"
        )
        cls.initial_statics = parse_label_bytes(
            cls.text, "w3d_fixture_initial_statics", "w3d_fixture_initial_statics_end"
        )
        cls.initial_actors = parse_label_bytes(
            cls.text, "w3d_fixture_initial_actors", "w3d_fixture_initial_actors_end"
        )
        cls.tilemap = parse_label_bytes(
            cls.text, "w3d_fixture_tilemap", "w3d_fixture_tilemap_end"
        )
        cls.commands = parse_label_bytes(
            cls.text, "w3d_fixture_cmds", "w3d_fixture_cmds_end"
        )
        door_count_match = re.search(r"W3D_FIXTURE_DOOR_COUNT:\s*equ\s+(\d+)", cls.text)
        if door_count_match is None:
            raise AssertionError("missing fixture door count")
        cls.door_count = int(door_count_match.group(1))
        static_count_match = re.search(r"W3D_FIXTURE_STATIC_COUNT:\s*equ\s+(\d+)", cls.text)
        if static_count_match is None:
            raise AssertionError("missing fixture static count")
        cls.static_count = int(static_count_match.group(1))
        actor_count_match = re.search(r"W3D_FIXTURE_ACTOR_COUNT:\s*equ\s+(\d+)", cls.text)
        if actor_count_match is None:
            raise AssertionError("missing fixture actor count")
        cls.actor_count = int(actor_count_match.group(1))

    def test_fixture_record_sizes_and_tilemap_indices(self) -> None:
        self.assertEqual(len(self.initial_doors), self.door_count * go.DOOR_SEED_RECORD.size)
        self.assertEqual(
            len(self.initial_statics), self.static_count * go.STATIC_SEED_RECORD.size
        )
        self.assertEqual(len(self.initial_actors), self.actor_count * 39)
        self.assertEqual(len(self.tilemap), 64 * 64)
        for index in range(self.door_count):
            record = go.DOOR_SEED_RECORD.unpack_from(
                self.initial_doors, index * go.DOOR_SEED_RECORD.size
            )
            tile_x, tile_y, vertical, lock, action, position, texture_id, area1, area2 = record
            self.assertIn(vertical, (0, 1))
            self.assertIn(lock, range(6))
            self.assertEqual((action, position), (go.DOOR_CLOSED, 0))
            self.assertIn(texture_id, (121, 123, 124))
            self.assertIn(area1, range(37))
            self.assertIn(area2, range(37))
            self.assertEqual(self.tilemap[tile_y * 64 + tile_x], 0x80 | index)

    def test_initial_wire_stream_exactly_matches_durable_seed_records(self) -> None:
        parsed = go.parse_command_stream(self.commands)
        self.assertEqual(parsed[0][0], go.SUB_INIT_LEVEL)
        self.assertEqual(parsed[-3][0], go.SUB_SET_PLAYER_POSE)
        self.assertEqual(parsed[-2], (go.SUB_SET_VIEW_WEAPON, struct.pack("<h", 421)))
        self.assertEqual(parsed[-1][0], go.SUB_RENDER_FRAME)
        door_bodies = [body for subcommand, body in parsed if subcommand == go.SUB_SET_DOOR]
        self.assertEqual(len(door_bodies), self.door_count)
        for index, body in enumerate(door_bodies):
            self.assertEqual(body[0], index)
            expected = self.initial_doors[
                index * go.DOOR_SEED_RECORD.size : index * go.DOOR_SEED_RECORD.size + go.DOOR_RECORD.size
            ]
            self.assertEqual(body[1:], expected)
        static_bodies = [
            body for subcommand, body in parsed if subcommand == go.SUB_SET_STATIC
        ]
        self.assertEqual(len(static_bodies), self.static_count)
        for index, body in enumerate(static_bodies):
            tile_x, tile_y, shapenum, flags, _item = go.STATIC_SEED_RECORD.unpack_from(
                self.initial_statics, index * go.STATIC_SEED_RECORD.size
            )
            self.assertEqual(
                body,
                go.STATIC_WIRE_RECORD.pack(index, tile_x, tile_y, shapenum, flags),
            )
        actor_bodies = [
            body for subcommand, body in parsed if subcommand == go.SUB_SET_ACTOR
        ]
        self.assertEqual(len(actor_bodies), self.actor_count)
        for actor_id, body in enumerate(actor_bodies, start=1):
            wire_id, shape, x, y, facing, rotations = go.ACTOR_WIRE_RECORD.unpack(body)
            self.assertEqual(wire_id, actor_id)
            record = self.initial_actors[(actor_id - 1) * 39:actor_id * 39]
            self.assertEqual((x, y), struct.unpack_from("<ii", record, 0))
            direction = record[11]
            if direction < 8:
                self.assertEqual(facing, direction * 45)
            self.assertIn(rotations, (0, 2, 8))
            self.assertGreaterEqual(shape, 0)

    def test_stream_has_no_gaps_or_trailing_bytes(self) -> None:
        parsed = go.parse_command_stream(self.commands)
        expected_length = (
            9 + self.door_count * 16 + self.static_count * 14
            + self.actor_count * 22 + 17 + 9 + 7
        )
        self.assertEqual(len(self.commands), expected_length)
        self.assertEqual(
            [subcommand for subcommand, _ in parsed],
            [go.SUB_INIT_LEVEL]
            + [go.SUB_SET_DOOR] * self.door_count
            + [go.SUB_SET_STATIC] * self.static_count
            + [go.SUB_SET_ACTOR] * self.actor_count
            + [go.SUB_SET_PLAYER_POSE, go.SUB_SET_VIEW_WEAPON, go.SUB_RENDER_FRAME],
        )

    def test_generator_command_is_independently_decodable(self) -> None:
        generator = load_generator()
        doors = [(2, 3, True, 0, 121), (7, 9, False, 4, 124)]
        payload = generator.build_command_stream(
            0x1234, 0x4567, doors, [], go.fixed(8), go.fixed(10), 315
        )
        parsed = go.parse_command_stream(payload)
        self.assertEqual(parsed[0], (go.SUB_INIT_LEVEL, struct.pack("<H", 0x4567)))
        self.assertEqual(
            parsed[1][1],
            bytes((0,)) + go.Door(2, 3, True, 0, texture_id=121).wire_record(),
        )
        self.assertEqual(
            parsed[2][1],
            bytes((1,)) + go.Door(7, 9, False, 4, texture_id=124).wire_record(),
        )
        self.assertEqual(
            parsed[3],
            (go.SUB_SET_PLAYER_POSE, go.PLAYER_POSE.pack(go.fixed(8), go.fixed(10), 315)),
        )
        self.assertEqual(parsed[4], (go.SUB_SET_VIEW_WEAPON, struct.pack("<h", 421)))
        self.assertEqual(parsed[5], (go.SUB_RENDER_FRAME, b""))

    def test_generator_door_classification_and_row_major_map(self) -> None:
        generator = load_generator()
        plane = [[0] * 64 for _ in range(64)]
        for index, tile_value in enumerate(range(90, 102)):
            # Keep each synthetic door isolated and give both of its geometric
            # endpoints real area tiles.  The production generator now rejects
            # the formerly convenient all-zero surroundings because those
            # would become malformed runtime graph edges.
            tile_y = 2 + index * 5
            plane[tile_y][20] = tile_value
            area_tile = generator.actorinfo.AREATILE + (index % 37)
            if index % 2 == 0:       # vertical door: east/west endpoints
                plane[tile_y][19] = area_tile
                plane[tile_y][21] = area_tile
            else:                    # horizontal door: north/south endpoints
                plane[tile_y - 1][20] = area_tile
                plane[tile_y + 1][20] = area_tile
        tilemap, doors = generator.build_tilemap_and_doors(plane)
        self.assertEqual(len(doors), 12)
        for index, door in enumerate(doors):
            tile_x, tile_y, vertical, lock, texture_id = door[:5]
            self.assertEqual((tile_x, tile_y), (20, 2 + index * 5))
            self.assertEqual(vertical, index % 2 == 0)
            self.assertEqual(lock, index // 2)
            expected_texture = 121 if lock == 0 else 123 if lock == 5 else 124
            self.assertEqual(texture_id, expected_texture)
            self.assertEqual(tilemap[(2 + index * 5) * 64 + 20], 0x80 | index)


@unittest.skipUnless(STAGED_ROOT.exists(), "staged assembly unavailable")
class StagedAssemblyContractTests(unittest.TestCase):
    def test_opening_saturates_on_carry_or_exact_ffff(self) -> None:
        source = (STAGED_ROOT / "src/asm/wolf3d/src/wolf3d_motion.inc").read_text()
        body = source.split("w3d_advance_opening_door:", 1)[1].split(
            "w3d_advance_open_door:", 1
        )[0]
        normalized = "\n".join(line.split(";", 1)[0].strip() for line in body.splitlines())
        self.assertRegex(
            normalized,
            r"add\.s hl,de\s+jr c,@fully_open\s+ld a,h\s+and l\s+inc a\s+jr z,@fully_open",
        )

    def test_expired_obstructed_timer_is_clamped_before_close_retry(self) -> None:
        source = (STAGED_ROOT / "src/asm/wolf3d/src/wolf3d_motion.inc").read_text()
        body = source.split("w3d_advance_open_door:", 1)[1].split(
            "w3d_try_close_current_door:", 1
        )[0]
        normalized = "\n".join(line.split(";", 1)[0].strip() for line in body.splitlines())
        self.assertRegex(
            normalized,
            r"sbc\.s hl,de\s+ret c\s+ld hl,W3D_DOOR_OPEN_TIMER_LIMIT\s+"
            r"ld \(iy\+0\),l\s+ld \(iy\+1\),h\s+jp w3d_try_close_current_door",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
