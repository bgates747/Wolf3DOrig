"""Wolfenstein 3D shareware IMF music extraction and timing conversion.

The bundled v1.4 ``AUDIOHED.WL1`` uses the full 87-sound layout even though
the file suffix is WL1.  Its music therefore begins at chunk 261, matching
``AUDIOWL6.H`` and the source actually included by ``ID_HEADS.H``.  Several
historical ``AUDIOWL1.H`` constants describe an older compact layout and must
not be used with this archive.

Each music chunk is a little-endian byte length followed by four-byte IMF
events: OPL register, value, and a u16 delay measured at 700 Hz.  The Agon
client services music from MOS's 120 Hz clock.  Delays are converted with a
cumulative rational transform so the end of every song lands on the nearest
120 Hz tick without accumulating per-event rounding drift.
"""

from __future__ import annotations

from dataclasses import dataclass
import struct


START_MUSIC_CHUNK = 261
MUSIC_COUNT = 27
IMF_HZ = 700
MOS_HZ = 120

MUSIC_NAMES = (
    "CORNER",
    "DUNGEON",
    "WARMARCH",
    "GETTHEM",
    "HEADACHE",
    "HITLWLTZ",
    "INTROCW3",
    "NAZI_NOR",
    "NAZI_OMI",
    "POW",
    "SALUTE",
    "SEARCHN",
    "SUSPENSE",
    "VICTORS",
    "WONDERIN",
    "FUNKYOU",
    "ENDLEVEL",
    "GOINGAFT",
    "PREGNANT",
    "ULTIMATE",
    "NAZI_RAP",
    "ZEROHOUR",
    "TWELFTH",
    "ROSTER",
    "URAHERO",
    "VICMARCH",
    "WARMRCH1",
)

REQUIRED_MUSIC_IDS = (0, 2, 3, 7, 9, 11, 12, 14, 16, 23, 24)

EPISODE_ONE_FLOOR_MUSIC = (3, 11, 9, 12, 3, 11, 9, 12, 2, 0)

SHELL_MUSIC = {
    "title": 7,
    "menu": 14,
    "read_this": 0,
    "high_scores": 23,
    "intermission": 16,
    "victory": 24,
}


@dataclass(frozen=True)
class ImfEvent:
    register: int
    value: int
    delay_700hz: int
    delay_120hz: int


@dataclass(frozen=True)
class MusicTrack:
    music_id: int
    name: str
    chunk_index: int
    source_bytes: bytes
    events: tuple[ImfEvent, ...]
    source_ticks: int
    loop_ticks_120hz: int

    @property
    def available(self) -> bool:
        return bool(self.events)


def _read_offsets(audio_header: bytes) -> tuple[int, ...]:
    if len(audio_header) % 4:
        raise ValueError("AUDIOHED length is not a multiple of four")
    offsets = struct.unpack(f"<{len(audio_header) // 4}I", audio_header)
    if len(offsets) < START_MUSIC_CHUNK + MUSIC_COUNT + 1:
        raise ValueError("AUDIOHED does not contain the full WL1 music table")
    return offsets


def _convert_delays(raw_events: bytes) -> tuple[tuple[ImfEvent, ...], int, int]:
    if len(raw_events) % 4:
        raise ValueError("IMF event payload length is not a multiple of four")
    source_due = 0
    converted_due = 0
    events: list[ImfEvent] = []
    for register, value, delay in struct.iter_unpack("<BBH", raw_events):
        source_due += delay
        next_due = (source_due * MOS_HZ + IMF_HZ // 2) // IMF_HZ
        converted_delay = next_due - converted_due
        if not 0 <= converted_delay <= 0xFFFF:
            raise ValueError("converted IMF delay escapes u16")
        events.append(ImfEvent(register, value, delay, converted_delay))
        converted_due = next_due
    return tuple(events), source_due, converted_due


def read_music_tracks(audio_header: bytes, audio_data: bytes) -> tuple[MusicTrack, ...]:
    offsets = _read_offsets(audio_header)
    tracks: list[MusicTrack] = []
    for music_id, name in enumerate(MUSIC_NAMES):
        chunk_index = START_MUSIC_CHUNK + music_id
        start = offsets[chunk_index]
        end = offsets[chunk_index + 1]
        if start > end or end > len(audio_data) or end - start < 2:
            raise ValueError(
                f"AUDIOT music chunk {chunk_index} has invalid bounds {start}..{end}"
            )
        source = audio_data[start:end]
        declared_length = struct.unpack_from("<H", source)[0]
        if declared_length % 4:
            raise ValueError(f"music chunk {chunk_index} declares a partial IMF event")
        if declared_length > len(source) - 2:
            raise ValueError(
                f"music chunk {chunk_index} declares {declared_length} bytes in "
                f"a {len(source)}-byte chunk"
            )
        events, source_ticks, loop_ticks = _convert_delays(
            source[2 : 2 + declared_length]
        )
        tracks.append(
            MusicTrack(
                music_id,
                name,
                chunk_index,
                source,
                events,
                source_ticks,
                loop_ticks,
            )
        )
    missing = [MUSIC_NAMES[index] for index in REQUIRED_MUSIC_IDS if not tracks[index].available]
    if missing:
        raise ValueError(f"required WL1 music tracks are empty: {', '.join(missing)}")
    return tuple(tracks)
