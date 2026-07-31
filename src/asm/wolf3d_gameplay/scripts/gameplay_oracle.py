#!/usr/bin/env python3
"""Independent host oracle for the eZ80-owned Wolf3D gameplay subset.

This deliberately models the documented external behavior rather than the
assembly's register-level implementation.  Coordinates are signed 16.16,
door positions are unsigned 0.16, the map is row-major, and the simulation
runs at an exact 30 Hz.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import struct
from typing import Iterable, Sequence


MAP_SIZE = 64
TILE_GLOBAL = 1 << 16
PLAYER_RADIUS = 0x5800
STATIC_BLOCKING_BYTES = MAP_SIZE * MAP_SIZE // 8

TILE_OPEN = 0x00
TILE_DOOR_MIN = 0x80
TILE_DOOR_MAX = 0xBF
TILE_DOOR_MASK = 0x7F

DOOR_CLOSED = 0
DOOR_OPENING = 1
DOOR_OPEN = 2
DOOR_CLOSING = 3

DOOR_STEP_LO = 0x0955
DOOR_STEP_HI = 0x0956
DOOR_OPEN_TIMER_STEP = 7
DOOR_OPEN_TIMER_LIMIT = 900

CONTROL_USE = 0x40

STATIC_FLAG_BONUS = 0x02
ITEM_GIBS = 2
ITEM_ALPO = 3
ITEM_FIRSTAID = 4
ITEM_KEY1 = 5
ITEM_KEY2 = 6
ITEM_KEY3 = 7
ITEM_KEY4 = 8
ITEM_CROSS = 9
ITEM_CHALICE = 10
ITEM_BIBLE = 11
ITEM_CROWN = 12
ITEM_CLIP = 13
ITEM_CLIP2 = 14
ITEM_MACHINEGUN = 15
ITEM_CHAINGUN = 16
ITEM_FOOD = 17
ITEM_FULLHEAL = 18

HUD_DIRTY_HEALTH = 0x01
HUD_DIRTY_AMMO = 0x02
HUD_DIRTY_KEYS = 0x04
HUD_DIRTY_WEAPON = 0x08
HUD_DIRTY_SCORE = 0x10
HUD_DIRTY_LIVES = 0x20

VDU_WOLF3D = 0x4A
SUB_INIT_LEVEL = 1
SUB_SET_PLAYER_POSE = 2
SUB_SET_DOOR = 3
SUB_SET_ACTOR = 4
SUB_SET_STATIC = 6
SUB_RENDER_FRAME = 7

DOOR_RECORD = struct.Struct("<BBBBBHB")
DOOR_SEED_RECORD = struct.Struct("<BBBBBHBBB")
STATIC_SEED_RECORD = struct.Struct("<BBhBB")
STATIC_WIRE_RECORD = struct.Struct("<HBBhB")
ACTOR_WIRE_RECORD = struct.Struct("<HhiiHB")
PLAYER_POSE = struct.Struct("<iiH")


@dataclass(frozen=True)
class Pose:
    x: int
    y: int
    angle: int = 0


@dataclass
class Door:
    tile_x: int
    tile_y: int
    vertical: bool
    lock: int
    action: int = DOOR_CLOSED
    position: int = 0
    texture_id: int = 121
    timer: int = 0
    dirty: bool = False

    def wire_record(self) -> bytes:
        return DOOR_RECORD.pack(
            self.tile_x,
            self.tile_y,
            int(self.vertical),
            self.lock,
            self.action,
            self.position,
            self.texture_id,
        )


@dataclass
class StaticObject:
    tile_x: int
    tile_y: int
    shapenum: int
    flags: int
    itemnumber: int
    dirty: bool = False


@dataclass
class PlayerState:
    health: int = 100
    ammo: int = 8
    key_flags: int = 0
    weapon: int = 1
    best_weapon: int = 1
    chosen_weapon: int = 1
    score: int = 0
    next_extra: int = 40_000
    lives: int = 3
    treasure_count: int = 0
    hud_dirty: int = 0


def _add_health(player: PlayerState, amount: int) -> None:
    value = min(100, player.health + amount)
    if value != player.health:
        player.health = value
        player.hud_dirty |= HUD_DIRTY_HEALTH


def _add_ammo(player: PlayerState, amount: int) -> None:
    was_empty = player.ammo == 0
    value = min(99, player.ammo + amount)
    if value != player.ammo:
        player.ammo = value
        player.hud_dirty |= HUD_DIRTY_AMMO
        if was_empty and player.weapon != player.chosen_weapon:
            player.weapon = player.chosen_weapon
            player.hud_dirty |= HUD_DIRTY_WEAPON


def _add_score(player: PlayerState, points: int) -> None:
    player.score = (player.score + points) & 0xFFFFFFFF
    player.hud_dirty |= HUD_DIRTY_SCORE
    while player.score >= player.next_extra:
        player.next_extra = (player.next_extra + 40_000) & 0xFFFFFFFF
        if player.lives < 9:
            player.lives += 1
            player.hud_dirty |= HUD_DIRTY_LIVES


def pickup_overlaps_player(static: StaticObject, pose: Pose) -> bool:
    x_low, x_high, y_low, y_high = player_bounds(pose)
    return x_low <= static.tile_x <= x_high and y_low <= static.tile_y <= y_high


def apply_pickup(static: StaticObject, player: PlayerState) -> bool:
    """Apply the eZ80 pickup subset; return true only when it is removed."""

    if static.shapenum == -1 or not (static.flags & STATIC_FLAG_BONUS):
        return False
    item = static.itemnumber
    if item == ITEM_ALPO:
        if player.health >= 100:
            return False
        _add_health(player, 4)
    elif item == ITEM_FIRSTAID:
        if player.health >= 100:
            return False
        _add_health(player, 25)
    elif ITEM_KEY1 <= item <= ITEM_KEY4:
        previous = player.key_flags
        player.key_flags |= 1 << (item - ITEM_KEY1)
        if player.key_flags != previous:
            player.hud_dirty |= HUD_DIRTY_KEYS
    elif item in (ITEM_CROSS, ITEM_CHALICE, ITEM_BIBLE, ITEM_CROWN):
        _add_score(player, {ITEM_CROSS: 100, ITEM_CHALICE: 500,
                            ITEM_BIBLE: 1000, ITEM_CROWN: 5000}[item])
        player.treasure_count = (player.treasure_count + 1) & 0xFFFF
    elif item == ITEM_CLIP:
        if player.ammo >= 99:
            return False
        _add_ammo(player, 8)
    elif item == ITEM_CLIP2:
        if player.ammo >= 99:
            return False
        _add_ammo(player, 4)
    elif item in (ITEM_MACHINEGUN, ITEM_CHAINGUN):
        _add_ammo(player, 6)
        weapon = 2 if item == ITEM_MACHINEGUN else 3
        if player.best_weapon < weapon:
            player.best_weapon = player.weapon = player.chosen_weapon = weapon
            player.hud_dirty |= HUD_DIRTY_WEAPON
    elif item == ITEM_FOOD:
        if player.health >= 100:
            return False
        _add_health(player, 10)
    elif item == ITEM_FULLHEAL:
        if player.health != 100:
            player.health = 100
            player.hud_dirty |= HUD_DIRTY_HEALTH
        _add_ammo(player, 25)
        if player.lives < 9:
            player.lives += 1
            player.hud_dirty |= HUD_DIRTY_LIVES
        player.treasure_count = (player.treasure_count + 1) & 0xFFFF
    elif item == ITEM_GIBS:
        if player.health > 10:
            return False
        _add_health(player, 1)
    else:
        return False

    static.shapenum = -1
    static.dirty = True
    return True


def collect_overlapping_pickups(
    statics: Sequence[StaticObject], pose: Pose, player: PlayerState
) -> list[int]:
    removed: list[int] = []
    for index, static in enumerate(statics):
        if pickup_overlaps_player(static, pose) and apply_pickup(static, player):
            removed.append(index)
    return removed


def empty_bordered_map() -> bytearray:
    """Return a 64x64 open map with a one-cell solid perimeter."""

    tilemap = bytearray(MAP_SIZE * MAP_SIZE)
    for coordinate in range(MAP_SIZE):
        tilemap[coordinate] = 1
        tilemap[(MAP_SIZE - 1) * MAP_SIZE + coordinate] = 1
        tilemap[coordinate * MAP_SIZE] = 1
        tilemap[coordinate * MAP_SIZE + MAP_SIZE - 1] = 1
    return tilemap


def empty_static_blocking_bits() -> bytearray:
    return bytearray(STATIC_BLOCKING_BYTES)


def set_static_blocked(bits: bytearray, x: int, y: int, blocked: bool = True) -> None:
    if not 0 <= x < MAP_SIZE or not 0 <= y < MAP_SIZE:
        raise ValueError((x, y))
    index = y * MAP_SIZE + x
    mask = 1 << (index & 7)
    if blocked:
        bits[index >> 3] |= mask
    else:
        bits[index >> 3] &= ~mask


def static_tile_blocked(bits: bytes | bytearray | None, x: int, y: int) -> bool:
    if bits is None:
        return False
    if len(bits) != STATIC_BLOCKING_BYTES:
        raise ValueError(f"static blocking bitset must be {STATIC_BLOCKING_BYTES} bytes")
    if not 0 <= x < MAP_SIZE or not 0 <= y < MAP_SIZE:
        return True
    index = y * MAP_SIZE + x
    return bool(bits[index >> 3] & (1 << (index & 7)))


def fixed(tile: int, fraction: int = 0x8000) -> int:
    if not 0 <= fraction <= 0xFFFF:
        raise ValueError(f"fraction outside uint16: {fraction}")
    return tile * TILE_GLOBAL + fraction


def tile_at(tilemap: bytes | bytearray, x: int, y: int) -> int:
    if not 0 <= x < MAP_SIZE or not 0 <= y < MAP_SIZE:
        return 0xFF
    return tilemap[y * MAP_SIZE + x]


def tile_is_clear(
    tilemap: bytes | bytearray,
    doors: Sequence[Door],
    x: int,
    y: int,
    static_blocking_bits: bytes | bytearray | None = None,
) -> bool:
    """Return whether a tile has no tile-wide movement obstruction.

    Known door cells are not tile-wide solids.  Their zero-thickness moving
    slabs are tested against the complete player AABB by
    :func:`player_position_clear` after these ordinary wall/static checks.
    """

    value = tile_at(tilemap, x, y)
    if value == TILE_OPEN:
        return not static_tile_blocked(static_blocking_bits, x, y)
    if TILE_DOOR_MIN <= value <= TILE_DOOR_MAX:
        index = value & TILE_DOOR_MASK
        return index < len(doors)
    return False


def player_bounds(pose: Pose, radius: int = PLAYER_RADIUS) -> tuple[int, int, int, int]:
    """Return inclusive low/high tile bounds for the square player AABB."""

    return (
        (pose.x - radius) // TILE_GLOBAL,
        (pose.x + radius) // TILE_GLOBAL,
        (pose.y - radius) // TILE_GLOBAL,
        (pose.y + radius) // TILE_GLOBAL,
    )


def player_fixed_bounds(pose: Pose, radius: int = PLAYER_RADIUS) -> tuple[int, int, int, int]:
    """Return the inclusive 16.16-coordinate bounds of the square player."""

    return pose.x - radius, pose.x + radius, pose.y - radius, pose.y + radius


def door_slab_overlaps_player(door: Door, pose: Pose, radius: int = PLAYER_RADIUS) -> bool:
    """Return whether the square player touches a moving door panel.

    This is the renderer's exact integer-fraction contract expressed in world
    coordinates.  A vertical door lies on ``x=tilex+0x8000`` and slides along
    Y; a horizontal door swaps the axes.  At position ``p``, fractions
    ``0..p`` are the inclusive gap and ``p+1..0xffff`` are panel.  The player
    AABB and center plane both use inclusive contact, so touching the plane or
    the first remaining panel fraction blocks.  Position ``0xffff`` has no
    panel at all, independently of the action label.
    """

    if door.position == 0xFFFF:
        return False

    x_low, x_high, y_low, y_high = player_fixed_bounds(pose, radius)
    tile_x = door.tile_x * TILE_GLOBAL
    tile_y = door.tile_y * TILE_GLOBAL
    panel_start_offset = door.position + 1

    if door.vertical:
        plane = tile_x + TILE_GLOBAL // 2
        panel_start = tile_y + panel_start_offset
        panel_end = tile_y + 0xFFFF
        return (
            x_low <= plane <= x_high
            and y_high >= panel_start
            and y_low <= panel_end
        )

    plane = tile_y + TILE_GLOBAL // 2
    panel_start = tile_x + panel_start_offset
    panel_end = tile_x + 0xFFFF
    return (
        y_low <= plane <= y_high
        and x_high >= panel_start
        and x_low <= panel_end
    )


def player_position_clear(
    tilemap: bytes | bytearray,
    doors: Sequence[Door],
    pose: Pose,
    radius: int = PLAYER_RADIUS,
    static_blocking_bits: bytes | bytearray | None = None,
) -> bool:
    x_low, x_high, y_low, y_high = player_bounds(pose, radius)
    if not (
        0 <= x_low < MAP_SIZE
        and 0 <= x_high < MAP_SIZE
        and 0 <= y_low < MAP_SIZE
        and 0 <= y_high < MAP_SIZE
    ):
        return False
    # The radius is below one tile, so the inclusive AABB spans at most two
    # cells per axis. These are exactly the four ordinary wall/static probes.
    cells = {
        (x_low, y_low),
        (x_high, y_low),
        (x_low, y_high),
        (x_high, y_high),
    }
    for x, y in cells:
        if not tile_is_clear(tilemap, doors, x, y, static_blocking_bits):
            return False

    # Door cells are wells containing a zero-thickness moving panel, not solid
    # tiles. Check each referenced slab once against the complete player AABB.
    checked_doors: set[int] = set()
    for x, y in cells:
        value = tile_at(tilemap, x, y)
        if not TILE_DOOR_MIN <= value <= TILE_DOOR_MAX:
            continue
        index = value & TILE_DOOR_MASK
        if index in checked_doors:
            continue
        checked_doors.add(index)
        if door_slab_overlaps_player(doors[index], pose, radius):
            return False
    return True


def clip_move(
    tilemap: bytes | bytearray,
    doors: Sequence[Door],
    pose: Pose,
    dx: int,
    dy: int,
    static_blocking_bits: bytes | bytearray | None = None,
) -> tuple[Pose, str]:
    """Apply original ClipMove ordering and return (new_pose, path_taken)."""

    combined = replace(pose, x=pose.x + dx, y=pose.y + dy)
    if player_position_clear(tilemap, doors, combined, static_blocking_bits=static_blocking_bits):
        return combined, "xy"
    x_only = replace(pose, x=pose.x + dx)
    if player_position_clear(tilemap, doors, x_only, static_blocking_bits=static_blocking_bits):
        return x_only, "x"
    y_only = replace(pose, y=pose.y + dy)
    if player_position_clear(tilemap, doors, y_only, static_blocking_bits=static_blocking_bits):
        return y_only, "y"
    return pose, "blocked"


def adjacent_tile(pose: Pose) -> tuple[int, int]:
    """Return the use tile using Wolf3D's exact integer-degree sectors."""

    angle = pose.angle % 360
    tile_x = pose.x // TILE_GLOBAL
    tile_y = pose.y // TILE_GLOBAL
    if angle < 45 or angle > 315:
        return tile_x + 1, tile_y
    if angle < 135:
        return tile_x, tile_y - 1
    if angle < 225:
        return tile_x - 1, tile_y
    return tile_x, tile_y + 1


def player_obstructs(door: Door, pose: Pose) -> bool:
    """Use the same panel geometry for closing obstruction as movement."""

    return door_slab_overlaps_player(door, pose)


def lock_allows(lock: int, player_key_flags: int) -> bool:
    if lock in (0, 5):
        return True
    if 1 <= lock <= 4:
        return bool(player_key_flags & (1 << (lock - 1)))
    return False


def operate_door(door: Door, player: Pose, player_key_flags: int = 0) -> bool:
    """Operate one door in place; return whether authoritative state changed."""

    if not lock_allows(door.lock, player_key_flags):
        return False
    if door.action == DOOR_OPENING:
        # The original routes this through CloseDoor, which refuses because
        # an opening door still occupies its actorat cell.
        return False
    if door.action == DOOR_OPEN:
        if player_obstructs(door, player):
            return False
        door.action = DOOR_CLOSING
        door.dirty = True
        return True
    # Closed and closing both start/reverse toward open at current position.
    door.action = DOOR_OPENING
    door.timer = 0
    door.dirty = True
    return True


class UseEdge:
    """One operate event per sampled press, mirroring w3d_use_was_down."""

    def __init__(self) -> None:
        self.was_down = False

    def sample(self, down: bool) -> bool:
        if not down:
            self.was_down = False
            return False
        if self.was_down:
            return False
        self.was_down = True
        return True


def use_adjacent_door(
    tilemap: bytes | bytearray,
    doors: Sequence[Door],
    pose: Pose,
    player_key_flags: int = 0,
) -> int | None:
    """Operate the door containing the player, or the cardinal door ahead.

    Door wells are real traversable cells in this port.  Once the player has
    entered one, the containing door must remain usable irrespective of view
    angle; otherwise the old cardinal adjacent-cell lookup is preserved.
    A door-valued current cell with an out-of-range index is malformed and
    fails closed instead of falling through to a different adjacent door.

    The historical function name is retained because callers use this as the
    complete Use-key operation, not merely as a coordinate helper.
    """

    current_x = pose.x // TILE_GLOBAL
    current_y = pose.y // TILE_GLOBAL
    current_value = tile_at(tilemap, current_x, current_y)
    if TILE_DOOR_MIN <= current_value <= TILE_DOOR_MAX:
        current_index = current_value & TILE_DOOR_MASK
        if current_index >= len(doors):
            return None
        return (
            current_index
            if operate_door(doors[current_index], pose, player_key_flags)
            else None
        )

    tile_x, tile_y = adjacent_tile(pose)
    value = tile_at(tilemap, tile_x, tile_y)
    if not TILE_DOOR_MIN <= value <= TILE_DOOR_MAX:
        return None
    index = value & TILE_DOOR_MASK
    if index >= len(doors):
        return None
    return index if operate_door(doors[index], pose, player_key_flags) else None


class DoorSimulation:
    """Authoritative 30 Hz door scheduler, including global 3-step phase."""

    def __init__(self, doors: Iterable[Door], phase: int = 0) -> None:
        self.doors = list(doors)
        self.phase = phase % 3

    def _next_delta(self) -> int:
        delta = DOOR_STEP_HI if self.phase == 2 else DOOR_STEP_LO
        self.phase = (self.phase + 1) % 3
        return delta

    def tick(self, player: Pose) -> int:
        """Advance one 30 Hz quantum; return number of changed doors."""

        delta = self._next_delta()
        changes = 0
        for door in self.doors:
            before = (door.action, door.position, door.timer, door.dirty)
            if door.action == DOOR_OPENING:
                position = door.position + delta
                if position >= 0xFFFF:
                    door.position = 0xFFFF
                    door.action = DOOR_OPEN
                    door.timer = 0
                else:
                    door.position = position
                door.dirty = True
            elif door.action == DOOR_OPEN:
                door.timer = (door.timer + DOOR_OPEN_TIMER_STEP) & 0xFFFF
                if door.timer >= DOOR_OPEN_TIMER_LIMIT:
                    door.timer = DOOR_OPEN_TIMER_LIMIT
                    if not player_obstructs(door, player):
                        door.action = DOOR_CLOSING
                        door.dirty = True
            elif door.action == DOOR_CLOSING:
                if player_obstructs(door, player):
                    door.action = DOOR_OPENING
                    door.timer = 0
                    door.dirty = True
                else:
                    position = door.position - delta
                    if position <= 0:
                        door.position = 0
                        door.action = DOOR_CLOSED
                        door.timer = 0
                    else:
                        door.position = position
                    door.dirty = True
            after = (door.action, door.position, door.timer, door.dirty)
            changes += before != after
        return changes


def wire_header(control_buffer_id: int, subcommand: int) -> bytes:
    return bytes((23, 0, 0xA0)) + struct.pack("<H", control_buffer_id) + bytes(
        (VDU_WOLF3D, subcommand)
    )


def set_door_command(control_buffer_id: int, index: int, door: Door) -> bytes:
    return wire_header(control_buffer_id, SUB_SET_DOOR) + bytes((index,)) + door.wire_record()


def player_pose_command(control_buffer_id: int, pose: Pose) -> bytes:
    return wire_header(control_buffer_id, SUB_SET_PLAYER_POSE) + PLAYER_POSE.pack(
        pose.x, pose.y, pose.angle % 360
    )


def parse_command_stream(payload: bytes) -> list[tuple[int, bytes]]:
    """Parse only the fixed Wolf3D control commands used by the fixture."""

    body_lengths = {
        SUB_INIT_LEVEL: 2,
        SUB_SET_PLAYER_POSE: PLAYER_POSE.size,
        SUB_SET_DOOR: 1 + DOOR_RECORD.size,
        SUB_SET_ACTOR: ACTOR_WIRE_RECORD.size,
        SUB_SET_STATIC: STATIC_WIRE_RECORD.size,
        SUB_RENDER_FRAME: 0,
    }
    commands: list[tuple[int, bytes]] = []
    offset = 0
    while offset < len(payload):
        if payload[offset : offset + 3] != bytes((23, 0, 0xA0)):
            raise ValueError(f"invalid VDU prefix at byte {offset}")
        if offset + 7 > len(payload) or payload[offset + 5] != VDU_WOLF3D:
            raise ValueError(f"truncated or wrong VDP opcode at byte {offset}")
        subcommand = payload[offset + 6]
        if subcommand not in body_lengths:
            raise ValueError(f"unsupported subcommand {subcommand} at byte {offset}")
        body_start = offset + 7
        body_end = body_start + body_lengths[subcommand]
        if body_end > len(payload):
            raise ValueError(f"truncated subcommand {subcommand} at byte {offset}")
        commands.append((subcommand, payload[body_start:body_end]))
        offset = body_end
    return commands
