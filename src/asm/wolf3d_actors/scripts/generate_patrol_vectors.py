#!/usr/bin/env python3
"""Generate fixed-record eZ80 patrol vectors from the independent oracle.

The output is either a binary blob (``.bin``) or an ez80asm include (any other
suffix).  Every 192-byte record carries complete initial/expected 39-byte actor
records, one optional door, clock phases, dirty results, and up to eight sparse
world-cell patches.  A direct harness can therefore initialize maps and compare
authoritative results without containing a second patrol implementation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import struct
from typing import Callable

import actor_oracle as ao


MAGIC = b"W3PV"
VERSION = 1
SEED = 0x574F3344
HEADER = struct.Struct("<4sHHII")
HEADER_SIZE = HEADER.size
RECORD_SIZE = 192
PATCH_SIZE = 8
PATCH_CAPACITY = 8

OFF_CASE_ID = 0
OFF_STEPS = 2
OFF_ACTOR_PHASE = 4
OFF_DOOR_PHASE = 5
OFF_ACTOR_ID = 6
OFF_DOOR_INDEX = 7
OFF_PLAYER_X = 8
OFF_PLAYER_Y = 12
OFF_INITIAL_ACTOR = 16
OFF_EXPECTED_ACTOR = 55
OFF_INITIAL_DOOR = 94
OFF_EXPECTED_DOOR = 104
OFF_INITIAL_DOOR_TIMER = 114
OFF_EXPECTED_DOOR_TIMER = 116
OFF_EXPECTED_ACTOR_DIRTY = 118
OFF_EXPECTED_DOOR_DIRTY = 119
OFF_FINAL_ACTOR_PHASE = 120
OFF_FINAL_DOOR_PHASE = 121
OFF_EXPECTED_ACTOR_PRESENT = 122
OFF_PATCH_COUNT = 123
OFF_PATCHES = 128


@dataclass
class Scenario:
    case_id: int
    name: str
    steps: int
    world: ao.World
    actor_id: int
    patch_coordinates: tuple[tuple[int, int], ...]
    door_index: int = 0xFF


@dataclass(frozen=True)
class BuiltVector:
    case_id: int
    name: str
    payload: bytes


def _actor(**overrides: int) -> ao.Actor:
    values = dict(
        x=ao.fixed(10), y=ao.fixed(10), tile_x=11, tile_y=10,
        area=0, direction=ao.DIR_EAST, active=ao.ACTIVE_YES,
        actor_class=ao.CLASS_GUARD, flags=ao.FLAG_SHOOTABLE,
        ticcount=0, state=ao.STATE_GRD_PATH1,
        distance=ao.TILE_GLOBAL, angle=0, hitpoints=25, speed=512,
        next_slot=0xFF, previous_slot=0xFF,
    )
    values.update(overrides)
    return ao.Actor(**values)


def _world_with_actor(actor: ao.Actor, actor_id: int = 1) -> ao.World:
    world = ao.World()
    world.add_actor(actor_id, actor)
    return world


def _scenario_cadence() -> Scenario:
    actor = _actor(ticcount=20, speed=0)
    return Scenario(1, "cadence_223", 3, _world_with_actor(actor), 1, ((11, 10),))


def _scenario_zero_latch() -> Scenario:
    actor = _actor(ticcount=0)
    return Scenario(2, "zero_tic_latch", 3, _world_with_actor(actor), 1, ((11, 10),))


def _scenario_same_shape_pause() -> Scenario:
    actor = _actor(ticcount=2, speed=0)
    return Scenario(3, "same_shape_pause_clean", 1, _world_with_actor(actor), 1, ((11, 10),))


def _scenario_shape_change() -> Scenario:
    actor = _actor(state=ao.STATE_GRD_PATH1S, ticcount=2, speed=0)
    return Scenario(4, "pause_to_path2_dirty", 1, _world_with_actor(actor), 1, ((11, 10),))


def _scenario_dog_residual() -> Scenario:
    actor = _actor(
        x=ao.fixed(11) - 512,
        tile_x=11,
        actor_class=ao.CLASS_DOG,
        state=ao.STATE_DOG_PATH1,
        distance=512,
        speed=1500,
    )
    world = _world_with_actor(actor, 7)
    world.set_path(11, 10, ao.DIR_NORTH)
    return Scenario(5, "dog_residual_arrow", 1, world, 7, ((11, 10), (11, 9)))


def _door_selection(actor_class: int, case_id: int, name: str) -> Scenario:
    state = ao.STATE_DOG_PATH1 if actor_class == ao.CLASS_DOG else ao.STATE_GRD_PATH1
    speed = 1500 if actor_class == ao.CLASS_DOG else 512
    actor = _actor(
        tile_x=10, tile_y=10, direction=ao.DIR_NODIR, distance=0,
        actor_class=actor_class, state=state, speed=speed,
    )
    world = _world_with_actor(actor)
    world.set_path(10, 10, ao.DIR_EAST)
    world.install_door(0, ao.Door(11, 10))
    return Scenario(case_id, name, 1, world, 1, ((10, 10), (11, 10)), 0)


def _scenario_dog_closed_door() -> Scenario:
    return _door_selection(ao.CLASS_DOG, 6, "dog_closed_door_block")


def _scenario_guard_wait() -> Scenario:
    return _door_selection(ao.CLASS_GUARD, 7, "guard_requests_door")


def _scenario_door_before_actor() -> Scenario:
    actor = _actor(tile_x=11, tile_y=10, distance=-1)
    world = _world_with_actor(actor)
    world.install_door(0, ao.Door(11, 10, action=ao.DOOR_OPENING, position=0xF6AA))
    # install_door occurs after add_actor but retains the independent actorat.
    return Scenario(8, "door_before_waiting_guard", 1, world, 1, ((11, 10),), 0)


def _scenario_player_overlap() -> Scenario:
    actor = _actor()
    world = _world_with_actor(actor)
    world.player_x = actor.x + 1024 + ao.PHYSICAL_OBJECT_CLEARANCE
    world.player_y = actor.y
    return Scenario(9, "inclusive_player_overlap", 1, world, 1, ((11, 10),))


def _scenario_malformed_wait() -> Scenario:
    actor = _actor(
        tile_x=11,
        tile_y=10,
        direction=ao.DIR_EAST,
        distance=-257,
    )
    world = _world_with_actor(actor)
    # A low-byte-only decoder would turn -257 into door zero.  The full-width
    # contract leaves this real door untouched and stops the actor at NODIR.
    world.install_door(0, ao.Door(11, 10, action=ao.DOOR_CLOSED))
    return Scenario(
        11,
        "malformed_wait_no_low_byte_alias",
        1,
        world,
        1,
        ((11, 10),),
        0,
    )


def _parse_label_bytes(text: str, start_label: str, end_label: str) -> bytes:
    match = re.search(
        rf"(?ms)^\s*{re.escape(start_label)}:\s*$"
        rf"(.*?)"
        rf"^\s*{re.escape(end_label)}:\s*$",
        text,
    )
    if match is None:
        raise ValueError(f"cannot find {start_label}..{end_label}")
    values: list[int] = []
    for line in match.group(1).splitlines():
        directive = re.search(r"\bdb\s+([^;]+)", line, re.IGNORECASE)
        if directive:
            values.extend(int(item.strip(), 0) for item in directive.group(1).split(","))
    return bytes(values)


def _scenario_real_e1l1(fixture: Path) -> Scenario:
    text = fixture.read_text()
    actor_bytes = _parse_label_bytes(
        text, "w3d_fixture_initial_actors", "w3d_fixture_initial_actors_end"
    )
    door_bytes = _parse_label_bytes(
        text, "w3d_fixture_initial_doors", "w3d_fixture_initial_doors_end"
    )
    actor = ao.Actor.from_bytes(actor_bytes[10 * 39:11 * 39])
    actor.ticcount = 8
    # This sparse acceptance instantiates only slot 11. Detach the real
    # fixture's live-list links so a direct harness does not walk into absent
    # slots 10/12 after processing the isolated actor.
    actor.next_slot = 0xFF
    actor.previous_slot = 0xFF
    # This vector deliberately isolates real slot 11. The fixture's durable
    # record links to slots 10/12, but those actors are not part of the sparse
    # scenario; normalize both links so production list traversal observes the
    # same one-actor world as the host oracle.
    actor.next_slot = 0xFF
    actor.previous_slot = 0xFF
    # Only the cells reached by this real route are needed by the direct
    # vector. Their area/path values are the exact E1L1 values.
    paths = _parse_label_bytes(
        text, "w3d_fixture_path_directions", "w3d_fixture_path_directions_end"
    )
    areas = _parse_label_bytes(text, "w3d_fixture_area_map", "w3d_fixture_area_map_end")
    tilemap = _parse_label_bytes(text, "w3d_fixture_tilemap", "w3d_fixture_tilemap_end")
    world = ao.World()
    for x, y in ((6, 33), (5, 33)):
        index = y * 64 + x
        world.tilemap[index] = tilemap[index]
        world.path_directions[index] = paths[index]
        world.area_map[index] = areas[index]
    start = 8 * 10
    door = ao.Door.from_fixture_bytes(door_bytes[start:start + 10])
    world.doors[8] = door
    world.add_actor(11, actor)
    return Scenario(10, "real_e1l1_slot11_door8", 92, world, 11,
                    ((6, 33), (5, 33)), 8)


SCENARIO_FACTORIES: tuple[Callable[[], Scenario], ...] = (
    _scenario_cadence,
    _scenario_zero_latch,
    _scenario_same_shape_pause,
    _scenario_shape_change,
    _scenario_dog_residual,
    _scenario_dog_closed_door,
    _scenario_guard_wait,
    _scenario_door_before_actor,
    _scenario_player_overlap,
)


def scenarios(fixture: Path) -> list[Scenario]:
    return (
        [factory() for factory in SCENARIO_FACTORIES]
        + [_scenario_real_e1l1(fixture), _scenario_malformed_wait()]
    )


def build_vector(scenario: Scenario) -> BuiltVector:
    world = scenario.world
    actor = world.actors[scenario.actor_id]
    initial_actor = actor.to_bytes()
    initial_actorat = bytes(world.actorat)
    initial_actor_phase = world.actor_clock_phase
    initial_door_phase = world.door_clock_phase
    initial_door = bytes(10)
    initial_door_timer = 0
    if scenario.door_index != 0xFF:
        door = world.doors[scenario.door_index]
        initial_door = door.fixture_bytes()
        initial_door_timer = door.timer

    world.step(scenario.steps)

    expected_actor = world.actors.get(scenario.actor_id)
    expected_actor_bytes = expected_actor.to_bytes() if expected_actor else bytes(39)
    expected_door = bytes(10)
    expected_door_timer = 0
    if scenario.door_index != 0xFF:
        door = world.doors[scenario.door_index]
        expected_door = door.fixture_bytes()
        expected_door_timer = door.timer

    coordinates: list[tuple[int, int]] = []
    for coordinate in scenario.patch_coordinates:
        if coordinate not in coordinates:
            coordinates.append(coordinate)
    initial_actor_object = ao.Actor.from_bytes(initial_actor)
    actor_coordinates = [(initial_actor_object.tile_x, initial_actor_object.tile_y)]
    if expected_actor is not None:
        actor_coordinates.append((expected_actor.tile_x, expected_actor.tile_y))
    for coordinate in actor_coordinates:
        if coordinate not in coordinates:
            coordinates.append(coordinate)
    if scenario.door_index != 0xFF:
        door = world.doors[scenario.door_index]
        coordinate = (door.tile_x, door.tile_y)
        if coordinate not in coordinates:
            coordinates.append(coordinate)
    if len(coordinates) > PATCH_CAPACITY:
        raise ValueError(f"{scenario.name} needs {len(coordinates)} cell patches")

    payload = bytearray(RECORD_SIZE)
    struct.pack_into("<HHBBBBii", payload, OFF_CASE_ID,
                     scenario.case_id, scenario.steps,
                     initial_actor_phase, initial_door_phase,
                     scenario.actor_id, scenario.door_index,
                     world.player_x, world.player_y)
    payload[OFF_INITIAL_ACTOR:OFF_INITIAL_ACTOR + 39] = initial_actor
    payload[OFF_EXPECTED_ACTOR:OFF_EXPECTED_ACTOR + 39] = expected_actor_bytes
    payload[OFF_INITIAL_DOOR:OFF_INITIAL_DOOR + 10] = initial_door
    payload[OFF_EXPECTED_DOOR:OFF_EXPECTED_DOOR + 10] = expected_door
    struct.pack_into("<HH", payload, OFF_INITIAL_DOOR_TIMER,
                     initial_door_timer, expected_door_timer)
    payload[OFF_EXPECTED_ACTOR_DIRTY] = int(scenario.actor_id in world.dirty_actors)
    payload[OFF_EXPECTED_DOOR_DIRTY] = int(
        scenario.door_index != 0xFF and scenario.door_index in world.dirty_doors
    )
    payload[OFF_FINAL_ACTOR_PHASE] = world.actor_clock_phase
    payload[OFF_FINAL_DOOR_PHASE] = world.door_clock_phase
    payload[OFF_EXPECTED_ACTOR_PRESENT] = int(expected_actor is not None)
    payload[OFF_PATCH_COUNT] = len(coordinates)

    for patch_index, (x, y) in enumerate(coordinates):
        index = y * 64 + x
        offset = OFF_PATCHES + patch_index * PATCH_SIZE
        payload[offset:offset + PATCH_SIZE] = bytes((
            x, y,
            world.tilemap[index],
            world.path_directions[index],
            world.area_map[index],
            world.static_blocked[index],
            initial_actorat[index],
            world.actorat[index],
        ))
    assert len(payload) == RECORD_SIZE
    return BuiltVector(scenario.case_id, scenario.name, bytes(payload))


def build_vectors(fixture: Path) -> list[BuiltVector]:
    return [build_vector(scenario) for scenario in scenarios(fixture)]


def build_blob(vectors: list[BuiltVector]) -> bytes:
    return HEADER.pack(MAGIC, VERSION, RECORD_SIZE, len(vectors), SEED) + b"".join(
        vector.payload for vector in vectors
    )


def emit_include(path: Path, vectors: list[BuiltVector], blob: bytes) -> None:
    lines = [
        "; Generated by generate_patrol_vectors.py. Do not hand-edit.",
        "; Each sparse cell patch is x,y,tile,path,area,static,actorat-in,actorat-out.",
        f"W3D_PATROL_VECTOR_VERSION: equ {VERSION}",
        f"W3D_PATROL_VECTOR_RECORD_SIZE: equ {RECORD_SIZE}",
        f"W3D_PATROL_VECTOR_COUNT: equ {len(vectors)}",
        f"W3D_PATROL_VECTOR_HEADER_SIZE: equ {HEADER_SIZE}",
        f"W3D_PV_INITIAL_ACTOR: equ {OFF_INITIAL_ACTOR}",
        f"W3D_PV_EXPECTED_ACTOR: equ {OFF_EXPECTED_ACTOR}",
        f"W3D_PV_INITIAL_DOOR: equ {OFF_INITIAL_DOOR}",
        f"W3D_PV_EXPECTED_DOOR: equ {OFF_EXPECTED_DOOR}",
        f"W3D_PV_PATCHES: equ {OFF_PATCHES}",
        "",
        "w3d_patrol_vector_blob:",
    ]
    for offset in range(0, HEADER_SIZE, 24):
        chunk = blob[offset:min(HEADER_SIZE, offset + 24)]
        lines.append("    db " + ",".join(str(value) for value in chunk))
    for index, vector in enumerate(vectors):
        lines.append(f"    ; case {vector.case_id}: {vector.name}")
        for offset in range(0, RECORD_SIZE, 24):
            chunk = vector.payload[offset:offset + 24]
            lines.append("    db " + ",".join(str(value) for value in chunk))
    lines.extend(("w3d_patrol_vector_blob_end:", ""))
    path.write_text("\n".join(lines))


def main() -> None:
    default_fixture = Path(__file__).resolve().parents[4] / "src/asm/wolf3d/src/wolf3d_fixture.inc"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=default_fixture)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    vectors = build_vectors(args.fixture)
    blob = build_blob(vectors)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.suffix.lower() == ".bin":
        args.out.write_bytes(blob)
    else:
        emit_include(args.out, vectors, blob)
    print(
        f"wrote {len(vectors)} patrol vectors ({len(blob)} bytes, "
        f"record size {RECORD_SIZE}) to {args.out}"
    )


if __name__ == "__main__":
    main()
