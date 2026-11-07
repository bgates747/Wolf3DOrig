"""Independent stream fixtures for the permanent game profiler's decoder."""
import importlib.util
from pathlib import Path
import struct

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "wolf_profile_decoder", ROOT / "src/asm/wolf3d/scripts/decode_profile.py")
decoder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decoder)


def put24(record, at, value):
    record[at:at + 3] = (value % (1 << 24)).to_bytes(3, "little")


def record(number, start, index, *, cue=False, native=False, session=False):
    r = bytearray(64)
    put24(r, 0, number)
    for at, value in zip((3, 6, 9, 12, 15, 18), (0, 2, 23, 24, 25, 33)):
        put24(r, at, start + value)
    put24(r, 21, 1)
    r[42] = 0x1c | int(cue) | (2 if native else 0) | (32 if session else 0)
    r[44] = 1 if native else 0
    r[59] = index
    if native:
        struct.pack_into("<III", r, 30, 4_800_000, 4_824_000, 4_848_000)
        struct.pack_into("<I", r, 60, 52685)
    return bytes(r)


def block(records, number=0, *, native=False, gap=(0, 0, 0, 0)):
    return struct.pack("<4sBBBBHHIIIII", b"WPF1", 1, int(native), 1,
                       int(native), len(records), 64, number, *gap) + b"".join(records)


def test_excludes_disk_gap_and_cue_from_rate_but_retains_wall_time():
    data = block([record(1, 0, 0, session=True), record(2, 33, 1),
                  record(3, 66, 2, cue=True)])
    data += block([record(4, 600, 0), record(5, 633, 1)], 1,
                  gap=(90, 600, 100, 600))
    r = decoder.decode(data)
    assert r["completed_frame_records"] == 5
    assert r["logging_excluded_fence_intervals_ms"]["count"] == 2
    assert r["logging_excluded_fence_rate"] == pytest.approx(1000 / 33)
    assert r["observed_fence_rate_including_logging"] < 7
    assert r["closed_logging_gaps"][0]["disk_ms"] == 500
    assert r["closed_logging_gaps"][0]["total_ms"] == 510
    assert r["stage_nominal_ms"]["presentation_fence_ms"]["count"] == 4


def test_native_draw_is_distinct_from_completion_and_missing_is_unavailable():
    r = decoder.decode(block([record(1, 0, 0, native=True)], native=True))
    assert r["native_at_nominal_240MHz_ms"]["draw"]["mean"] == 20
    assert r["stage_nominal_ms"]["prepare_callback_ms"]["mean"] == 23
    no = decoder.decode(block([record(1, 0, 0)]))
    assert no["native_at_nominal_240MHz_ms"]["draw"] == {"count": 0}


def test_tick_wrap_does_not_create_a_huge_frame():
    r = decoder.decode(block([record(1, (1 << 24) - 10, 0)]))
    assert r["stage_nominal_ms"]["prepare_fence_ms"]["mean"] == 33


def test_does_not_bridge_menu_sessions_or_failed_attempts():
    r = decoder.decode(block([record(1, 0, 0), record(4, 33, 1),
                              record(5, 66, 2, session=True), record(6, 99, 3)]))
    assert r["logging_excluded_fence_intervals_ms"]["count"] == 1
    assert r["observed_fence_intervals_including_logging_ms"]["count"] == 2


def test_irq_reply_can_precede_sender_return():
    r = bytearray(record(1, 0, 0))
    put24(r, 6, 24)
    assert decoder.decode(block([r]))["completed_frame_records"] == 1


@pytest.mark.parametrize("cut", (1, 20, 32, 48, 63))
def test_torn_second_write_is_explicit_and_never_counted(cut):
    first = block([record(1, 0, 0)])
    second = block([record(2, 1000, 0)], 1, gap=(33, 1000, 35, 1000))
    with pytest.raises(decoder.ProfileError):
        decoder.decode(first + second[:-cut])
    r = decoder.decode(first + second[:-cut], salvage=True)
    assert r["completed_frame_records"] == 1
    assert r["warnings"]


@pytest.mark.parametrize("at,value", ((0, 0), (42, 0), (43, 1), (44, 1), (59, 7)))
def test_bad_records_are_refused(at, value):
    r = bytearray(record(1, 0, 0))
    r[at] = value
    with pytest.raises(decoder.ProfileError):
        decoder.decode(block([r]))


def test_reversed_clock_is_not_silently_wrapped():
    r = bytearray(record(1, 0, 0))
    put24(r, 18, 24)
    with pytest.raises(decoder.ProfileError):
        decoder.decode(block([r]))


def test_private_native_switch_requires_the_bound_module():
    spec = importlib.util.spec_from_file_location(
        "wolf_profile_build", ROOT / "src/asm/wolf3d/scripts/build.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    with pytest.raises(SystemExit, match="requires --profile"):
        builder.build(Path("unused"), "standalone", None, profile_native=True)
