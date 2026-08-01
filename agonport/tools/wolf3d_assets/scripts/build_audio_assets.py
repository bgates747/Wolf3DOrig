#!/usr/bin/env python3
"""Build Wolf3DOrig's native-rate AGNB 0.2 sound-effect assets.

Defaults consume the local shareware ``VSWAP/AUDIOHED/AUDIOT.WL1`` files and
the canonical 22-effect AGNB test collection.  Original VSWAP bytes are never
resampled.  Every available logical sound receives its stable sample buffer
``0x5000 + logicalId``; its three callable playback buffers are reserved at
``0x6000 + logicalId*3 + channel``.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(TOOLS_ROOT))

from agnb.audio import AudioBufferRecord, build_audio_container
from formats.audio import (
    DigitizedSound,
    read_adlib_priorities,
    read_unsigned_pcm_wav,
    read_vswap_digitized_sounds,
)
from formats.audio_catalog import (
    CHANNEL_COUNT,
    COMMAND_BUFFER_BASE,
    CURRENT_PRODUCERS,
    FALLBACKS,
    NATIVE_SAMPLE_RATE,
    SAMPLE_BUFFER_BASE,
    UPLOAD_DIGI_MAP,
    command_buffer_ids,
    sample_buffer_id,
)


DEFAULT_VSWAP = REPO_ROOT / "orig/data/VSWAP.WL1"
DEFAULT_AUDIOHED = REPO_ROOT / "orig/data/AUDIOHED.WL1"
DEFAULT_AUDIOT = REPO_ROOT / "orig/data/AUDIOT.WL1"
DEFAULT_AUDIO_HEADER = REPO_ROOT / "orig/src/WOLFSRC/AUDIOWL1.H"
DEFAULT_WL_GAME = REPO_ROOT / "orig/src/WOLFSRC/WL_GAME.C"
DEFAULT_FALLBACK_DIR = (
    REPO_ROOT.parent
    / "agon-utils/examples/agnb/audio/assets/processed"
)
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT / "agonport/assets/generated/wolf3d/audio"
)
DEFAULT_INCLUDE = REPO_ROOT / "src/asm/wolf3d/src/wolf3d_audio_assets.inc"
CONTAINER_FILENAME = "sfx.agnb"
MANIFEST_FILENAME = "audio_manifest.json"

AUDIO_ENTRY_SIZE = 16
AUDIO_FLAG_REQUIRED = 0x01
AUDIO_FLAG_AVAILABLE = 0x02
AUDIO_FLAG_NATIVE = 0x04
AUDIO_FLAG_FALLBACK = 0x08
GAIN_FORWARD_ROWS = 15
GAIN_LATERAL_COLUMNS = 30
GAIN_LATERAL_BIAS = 15


@dataclass(frozen=True)
class ResolvedSound:
    logical_id: int
    name: str
    priority: int
    producers: tuple[str, ...]
    source_kind: str | None
    source: str | None
    source_note: str | None
    digi_index: int | None
    sample_rate: int
    pcm: bytes | None
    unavailable_reason: str | None

    @property
    def required(self) -> bool:
        return bool(self.producers)

    @property
    def available(self) -> bool:
        return self.pcm is not None


def parse_sound_names(audio_header_text: str) -> tuple[str, ...]:
    """Return the contiguous ``AUDIOWL1.H`` logical sound enum names."""

    match = re.search(
        r"typedef\s+enum\s*\{(?P<body>.*?)\bLASTSOUND\b",
        audio_header_text,
        flags=re.DOTALL,
    )
    if not match:
        raise ValueError("AUDIOWL1.H does not contain the soundnames enum")
    names = tuple(
        item.group(1)
        for item in re.finditer(
            r"^\s*([A-Z][A-Z0-9_]*SND)\s*,",
            match.group("body"),
            flags=re.MULTILINE,
        )
    )
    if len(names) != 69 or len(set(names)) != len(names):
        raise ValueError(
            f"AUDIOWL1.H must expose 69 unique WL1 logical sounds, got {len(names)}"
        )
    return names


def parse_attenuation_tables(
    wl_game_text: str,
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    """Return Wolf3D's original left and right 15-by-30 attenuation tables.

    ``SetSoundLoc`` indexes these as ``[abs(forward)][lateral + 15]`` after
    clamping forward to 0..14 and lateral to -15..14.  Parsing the canonical
    C source keeps the generated Agon mono-gain table tied to the original
    game's hand-tuned spatial falloff rather than maintaining a second copy.
    """

    parsed: dict[str, tuple[tuple[int, ...], ...]] = {}
    for table_name in ("lefttable", "righttable"):
        match = re.search(
            rf"\bbyte\s+{table_name}\s*\[ATABLEMAX\]\s*"
            rf"\[ATABLEMAX\s*\*\s*2\]\s*=\s*\{{(?P<body>.*?)\}}\s*;",
            wl_game_text,
            flags=re.DOTALL,
        )
        if not match:
            raise ValueError(f"WL_GAME.C does not contain {table_name}")
        rows = tuple(
            tuple(int(value) for value in re.findall(r"\d+", row_text))
            for row_text in re.findall(r"\{([^{}]*)\}", match.group("body"))
        )
        if len(rows) != GAIN_FORWARD_ROWS or any(
            len(row) != GAIN_LATERAL_COLUMNS for row in rows
        ):
            dimensions = [len(row) for row in rows]
            raise ValueError(
                f"WL_GAME.C {table_name} must be 15x30, got "
                f"{len(rows)} rows with columns {dimensions}"
            )
        if any(value > 15 for row in rows for value in row):
            raise ValueError(f"WL_GAME.C {table_name} contains attenuation above 15")
        parsed[table_name] = rows
    return parsed["lefttable"], parsed["righttable"]


def build_mono_gain_table(
    left: tuple[tuple[int, ...], ...],
    right: tuple[tuple[int, ...], ...],
) -> tuple[int, ...]:
    """Collapse the original stereo attenuation table to Agon's mono gain.

    The original channel attenuations are averaged with integer rounding,
    then mapped from attenuation 0..15 to VDP gain 127..0.  Integer rounding
    is exact here: a denominator of 15 cannot produce an x.5 tie.
    """

    if len(left) != GAIN_FORWARD_ROWS or len(right) != GAIN_FORWARD_ROWS:
        raise ValueError("mono gain inputs must each contain 15 rows")
    gains: list[int] = []
    for row_index, (left_row, right_row) in enumerate(zip(left, right)):
        if (
            len(left_row) != GAIN_LATERAL_COLUMNS
            or len(right_row) != GAIN_LATERAL_COLUMNS
        ):
            raise ValueError(f"mono gain row {row_index} must contain 30 columns")
        for left_attenuation, right_attenuation in zip(left_row, right_row):
            if not 0 <= left_attenuation <= 15 or not 0 <= right_attenuation <= 15:
                raise ValueError("mono gain attenuation must be in 0..15")
            attenuation = (left_attenuation + right_attenuation + 1) // 2
            gains.append(((15 - attenuation) * 127 + 7) // 15)
    return tuple(gains)


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        try:
            return "../" + path.resolve().relative_to(REPO_ROOT.parent.resolve()).as_posix()
        except ValueError:
            return str(path.resolve())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _duration_ms(byte_length: int, sample_rate: int) -> int:
    return (byte_length * 1000 + sample_rate // 2) // sample_rate


def resolve_sounds(
    names: tuple[str, ...],
    priorities: tuple[int, ...],
    digitized: tuple[DigitizedSound, ...],
    fallback_dir: Path | None,
) -> tuple[ResolvedSound, ...]:
    if len(priorities) != len(names):
        raise ValueError("logical sound names and priorities have different lengths")
    name_set = set(names)
    unknown_native = sorted(set(UPLOAD_DIGI_MAP) - name_set)
    unknown_fallback = sorted(set(FALLBACKS) - name_set)
    unknown_producers = sorted(set(CURRENT_PRODUCERS) - name_set)
    if unknown_native or unknown_fallback or unknown_producers:
        raise ValueError(
            "audio catalog references unknown logical names: "
            f"native={unknown_native}, fallback={unknown_fallback}, "
            f"producers={unknown_producers}"
        )

    resolved: list[ResolvedSound] = []
    for logical_id, (name, priority) in enumerate(zip(names, priorities)):
        producers = CURRENT_PRODUCERS.get(name, ())
        if name in UPLOAD_DIGI_MAP:
            digi_index = UPLOAD_DIGI_MAP[name]
            if digi_index >= len(digitized):
                raise ValueError(
                    f"{name} maps to missing VSWAP digitized index {digi_index}"
                )
            sound = digitized[digi_index]
            if sound.pcm is None:
                raise ValueError(
                    f"shareware-native {name}/digi {digi_index} is sparse at pages "
                    f"{sound.missing_pages}"
                )
            resolved.append(
                ResolvedSound(
                    logical_id,
                    name,
                    priority,
                    producers,
                    "vswap_native",
                    f"orig/data/VSWAP.WL1:digi/{digi_index}",
                    "original shareware unsigned 8-bit mono PCM",
                    digi_index,
                    NATIVE_SAMPLE_RATE,
                    sound.pcm,
                    None,
                )
            )
            continue

        fallback = FALLBACKS.get(name)
        if fallback is not None and fallback_dir is not None:
            fallback_path = fallback_dir / fallback.filename
            if fallback_path.is_file():
                sample_rate, pcm = read_unsigned_pcm_wav(fallback_path)
                resolved.append(
                    ResolvedSound(
                        logical_id,
                        name,
                        priority,
                        producers,
                        "test_pack_fallback",
                        _display_path(fallback_path),
                        fallback.note,
                        None,
                        sample_rate,
                        pcm,
                        None,
                    )
                )
                continue
            unavailable_reason = f"fallback file not found: {_display_path(fallback_path)}"
        elif fallback is not None:
            unavailable_reason = "fallback collection disabled"
        elif producers:
            unavailable_reason = "no native digitized effect or approved PCM fallback"
        else:
            unavailable_reason = "outside the current sound-effects scope"

        resolved.append(
            ResolvedSound(
                logical_id,
                name,
                priority,
                producers,
                None,
                None,
                fallback.note if fallback is not None else None,
                None,
                0,
                None,
                unavailable_reason,
            )
        )
    return tuple(resolved)


def _sound_manifest_entry(sound: ResolvedSound) -> dict[str, Any]:
    reserved_commands = list(command_buffer_ids(sound.logical_id))
    entry: dict[str, Any] = {
        "logicalId": sound.logical_id,
        "name": sound.name,
        "priority": sound.priority,
        "required": sound.required,
        "producers": list(sound.producers),
        "available": sound.available,
        "sourceKind": sound.source_kind,
        "source": sound.source,
        "sourceNote": sound.source_note,
        "digiIndex": sound.digi_index,
        "sampleRate": sound.sample_rate,
        "pcmBytes": len(sound.pcm) if sound.pcm is not None else 0,
        "durationMs": (
            _duration_ms(len(sound.pcm), sound.sample_rate)
            if sound.pcm is not None
            else 0
        ),
        "pcmSha256": _sha256(sound.pcm) if sound.pcm is not None else None,
        "sampleBufferId": (
            sample_buffer_id(sound.logical_id) if sound.available else None
        ),
        "commandBufferIds": reserved_commands if sound.available else [],
        "reservedSampleBufferId": sample_buffer_id(sound.logical_id),
        "reservedCommandBufferIds": reserved_commands,
        "unavailableReason": sound.unavailable_reason,
    }
    return entry


def build_manifest(
    sounds: tuple[ResolvedSound, ...],
    container: bytes,
    mono_gain_table: tuple[int, ...],
    *,
    vswap: bytes,
    audiohed: bytes,
    audiot: bytes,
    wl_game: bytes,
) -> dict[str, Any]:
    available = tuple(sound for sound in sounds if sound.available)
    required = tuple(sound for sound in sounds if sound.required)
    required_available = tuple(sound for sound in required if sound.available)
    unique_pcm: dict[str, int] = {}
    for sound in available:
        assert sound.pcm is not None
        unique_pcm.setdefault(_sha256(sound.pcm), len(sound.pcm))

    return {
        "schemaVersion": 1,
        "containerVersion": {"major": 0, "minor": 2},
        "audioFormat": {
            "vdpFormat": 0x09,
            "encoding": "unsigned_8bit_mono_pcm",
        },
        "monoGainTable": {
            "index": "abs(forward)*30 + (lateral+15)",
            "forwardClamp": [0, GAIN_FORWARD_ROWS - 1],
            "lateralClamp": [-GAIN_LATERAL_BIAS, GAIN_LATERAL_COLUMNS - GAIN_LATERAL_BIAS - 1],
            "rows": GAIN_FORWARD_ROWS,
            "columns": GAIN_LATERAL_COLUMNS,
            "bytes": len(mono_gain_table),
            "minimumGain": min(mono_gain_table),
            "maximumGain": max(mono_gain_table),
            "algorithm": "att=(left+right+1)//2; gain=round((15-att)*127/15)",
            "sha256": _sha256(bytes(mono_gain_table)),
        },
        "idRanges": {
            "samples": {
                "formula": "0x5000 + logicalId",
                "first": SAMPLE_BUFFER_BASE,
                "last": SAMPLE_BUFFER_BASE + len(sounds) - 1,
            },
            "playbackCommands": {
                "formula": "0x6000 + logicalId*3 + channel",
                "channels": CHANNEL_COUNT,
                "first": COMMAND_BUFFER_BASE,
                "last": COMMAND_BUFFER_BASE + len(sounds) * CHANNEL_COUNT - 1,
            },
        },
        "sourceFiles": {
            "vswap": {"path": "orig/data/VSWAP.WL1", "sha256": _sha256(vswap)},
            "audiohed": {
                "path": "orig/data/AUDIOHED.WL1",
                "sha256": _sha256(audiohed),
            },
            "audiot": {"path": "orig/data/AUDIOT.WL1", "sha256": _sha256(audiot)},
            "wlGame": {
                "path": "orig/src/WOLFSRC/WL_GAME.C",
                "sha256": _sha256(wl_game),
            },
        },
        "totals": {
            "logicalSounds": len(sounds),
            "availableLogicalSounds": len(available),
            "unavailableLogicalSounds": len(sounds) - len(available),
            "requiredLogicalSounds": len(required),
            "requiredAvailableLogicalSounds": len(required_available),
            "requiredUnavailableLogicalSounds": len(required) - len(required_available),
            "nativeRecords": sum(sound.source_kind == "vswap_native" for sound in available),
            "fallbackRecords": sum(
                sound.source_kind == "test_pack_fallback" for sound in available
            ),
            "residentPcmBytes": sum(len(sound.pcm or b"") for sound in available),
            "uniquePcmPayloadBytes": sum(unique_pcm.values()),
            "containerBytes": len(container),
            "containerRecords": len(available),
        },
        "containerSha256": _sha256(container),
        "sounds": [_sound_manifest_entry(sound) for sound in sounds],
    }


def build_include(
    sounds: tuple[ResolvedSound, ...],
    container_size: int,
    mono_gain_table: tuple[int, ...],
) -> str:
    available = [sound for sound in sounds if sound.available]
    required = [sound for sound in sounds if sound.required]
    for sound in sounds:
        if not 0 <= sound.priority <= 0xFF:
            raise ValueError(
                f"{sound.name} priority {sound.priority} cannot fit the u8 table field"
            )
        if sound.available:
            assert sound.pcm is not None
            duration = _duration_ms(len(sound.pcm), sound.sample_rate)
            if len(sound.pcm) > 0xFFFF or duration > 0xFFFF:
                raise ValueError(
                    f"{sound.name} size/duration cannot fit the u16 table fields: "
                    f"{len(sound.pcm)} bytes, {duration} ms"
                )
    lines = [
        "; Generated by agonport/tools/wolf3d_assets/scripts/build_audio_assets.py.",
        "; Do not hand-edit. Regenerate from the original WL1 data and approved fallbacks.",
        ";",
        "; Each 16-byte table entry is indexed by the original AUDIOWL1.H logical id:",
        ";   dw sampleBufferId, sampleRate, pcmBytes, durationMs",
        ";   db originalPriority, flags",
        ";   dw commandBufferId[channel 0], [channel 1], [channel 2]",
        "",
        f"W3D_AUDIO_LOGICAL_COUNT:          equ {len(sounds)}",
        f"W3D_AUDIO_CHANNEL_COUNT:          equ {CHANNEL_COUNT}",
        f"W3D_AUDIO_ENTRY_SIZE:             equ {AUDIO_ENTRY_SIZE}",
        f"W3D_AUDIO_SAMPLE_BUFFER_BASE:     equ 0x{SAMPLE_BUFFER_BASE:04X}",
        f"W3D_AUDIO_COMMAND_BUFFER_BASE:    equ 0x{COMMAND_BUFFER_BASE:04X}",
        "W3D_AUDIO_FLAG_REQUIRED:          equ 0x01",
        "W3D_AUDIO_FLAG_AVAILABLE:         equ 0x02",
        "W3D_AUDIO_FLAG_NATIVE:            equ 0x04",
        "W3D_AUDIO_FLAG_FALLBACK:          equ 0x08",
        f"W3D_AUDIO_AVAILABLE_COUNT:        equ {len(available)}",
        f"W3D_AUDIO_REQUIRED_COUNT:         equ {len(required)}",
        f"W3D_AUDIO_REQUIRED_AVAILABLE:     equ {sum(s.available for s in required)}",
        f"W3D_AUDIO_RESIDENT_PCM_BYTES:     equ {sum(len(s.pcm or b'') for s in available)}",
        f"W3D_AUDIO_CONTAINER_BYTES:        equ {container_size}",
        f"W3D_AUDIO_GAIN_FORWARD_ROWS:      equ {GAIN_FORWARD_ROWS}",
        f"W3D_AUDIO_GAIN_LATERAL_COLUMNS:   equ {GAIN_LATERAL_COLUMNS}",
        f"W3D_AUDIO_GAIN_LATERAL_BIAS:      equ {GAIN_LATERAL_BIAS}",
        f"W3D_AUDIO_MONO_GAIN_BYTES:        equ {len(mono_gain_table)}",
        "",
        "W3D_AUDIO_ENTRY_SAMPLE_ID:        equ 0",
        "W3D_AUDIO_ENTRY_SAMPLE_RATE:      equ 2",
        "W3D_AUDIO_ENTRY_PCM_BYTES:        equ 4",
        "W3D_AUDIO_ENTRY_DURATION_MS:      equ 6",
        "W3D_AUDIO_ENTRY_PRIORITY:         equ 8",
        "W3D_AUDIO_ENTRY_FLAGS:            equ 9",
        "W3D_AUDIO_ENTRY_COMMAND0:         equ 10",
        "W3D_AUDIO_ENTRY_COMMAND1:         equ 12",
        "W3D_AUDIO_ENTRY_COMMAND2:         equ 14",
        "",
    ]

    for sound in sounds:
        symbol = sound.name[:-3] if sound.name.endswith("SND") else sound.name
        lines.append(f"W3D_AUDIO_SOUND_{symbol}: equ {sound.logical_id}")

    lines.extend(("", "w3d_audio_asset_table:"))
    for sound in sounds:
        flags = AUDIO_FLAG_REQUIRED if sound.required else 0
        if sound.available:
            flags |= AUDIO_FLAG_AVAILABLE
            flags |= (
                AUDIO_FLAG_NATIVE
                if sound.source_kind == "vswap_native"
                else AUDIO_FLAG_FALLBACK
            )
            assert sound.pcm is not None
            sample_id = sample_buffer_id(sound.logical_id)
            rate = sound.sample_rate
            pcm_bytes = len(sound.pcm)
            duration = _duration_ms(pcm_bytes, rate)
            commands = command_buffer_ids(sound.logical_id)
        else:
            sample_id = rate = pcm_bytes = duration = 0
            commands = (0, 0, 0)
        lines.append(
            f"    ; {sound.logical_id:02d} {sound.name} "
            f"({'available' if sound.available else 'unavailable'})"
        )
        lines.append(
            f"    dw 0x{sample_id:04X},{rate},{pcm_bytes},{duration}"
        )
        lines.append(f"    db {sound.priority},0x{flags:02X}")
        lines.append(
            "    dw " + ",".join(f"0x{command:04X}" for command in commands)
        )
    lines.extend(
        (
            "w3d_audio_asset_table_end:",
            "",
            "; Original WL_GAME.C left/right attenuation collapsed to mono VDP gain.",
            "; Index after clamping: abs(forward)*30 + (lateral+15).",
            "w3d_audio_mono_gain_table:",
        )
    )
    for row in range(GAIN_FORWARD_ROWS):
        start = row * GAIN_LATERAL_COLUMNS
        values = mono_gain_table[start : start + GAIN_LATERAL_COLUMNS]
        lines.append(f"    ; abs(forward) = {row}")
        lines.append("    db " + ",".join(str(value) for value in values))
    lines.extend(("w3d_audio_mono_gain_table_end:", ""))
    return "\n".join(lines)


def build_assets(
    *,
    vswap_path: Path,
    audiohed_path: Path,
    audiot_path: Path,
    audio_header_path: Path,
    wl_game_path: Path,
    fallback_dir: Path | None,
) -> tuple[bytes, dict[str, Any], str, tuple[ResolvedSound, ...]]:
    vswap = vswap_path.read_bytes()
    audiohed = audiohed_path.read_bytes()
    audiot = audiot_path.read_bytes()
    wl_game = wl_game_path.read_bytes()
    names = parse_sound_names(audio_header_path.read_text())
    left_table, right_table = parse_attenuation_tables(
        wl_game.decode("latin-1")
    )
    mono_gain_table = build_mono_gain_table(left_table, right_table)
    priorities = read_adlib_priorities(audiohed, audiot, len(names))
    digitized = read_vswap_digitized_sounds(vswap)
    sounds = resolve_sounds(names, priorities, digitized, fallback_dir)

    records = [
        AudioBufferRecord(
            logical_id=sound.logical_id,
            name=sound.name,
            buffer_id=sample_buffer_id(sound.logical_id),
            sample_rate=sound.sample_rate,
            pcm=sound.pcm or b"",
        )
        for sound in sounds
        if sound.available
    ]
    container = build_audio_container(records)
    manifest = build_manifest(
        sounds,
        container,
        mono_gain_table,
        vswap=vswap,
        audiohed=audiohed,
        audiot=audiot,
        wl_game=wl_game,
    )
    include_text = build_include(sounds, len(container), mono_gain_table)
    return container, manifest, include_text, sounds


def write_assets(
    *,
    output_dir: Path,
    include_path: Path,
    container: bytes,
    manifest: dict[str, Any],
    include_text: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    include_path.parent.mkdir(parents=True, exist_ok=True)
    (output_dir / CONTAINER_FILENAME).write_bytes(container)
    (output_dir / MANIFEST_FILENAME).write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    include_path.write_text(include_text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vswap", type=Path, default=DEFAULT_VSWAP)
    parser.add_argument("--audiohed", type=Path, default=DEFAULT_AUDIOHED)
    parser.add_argument("--audiot", type=Path, default=DEFAULT_AUDIOT)
    parser.add_argument("--audio-header", type=Path, default=DEFAULT_AUDIO_HEADER)
    parser.add_argument("--wl-game", type=Path, default=DEFAULT_WL_GAME)
    parser.add_argument(
        "--fallback-dir",
        type=Path,
        default=DEFAULT_FALLBACK_DIR,
        help="processed unsigned-8 mono WAV directory; pass --no-fallbacks to disable",
    )
    parser.add_argument("--no-fallbacks", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--include", type=Path, default=DEFAULT_INCLUDE)
    args = parser.parse_args()

    fallback_dir = None if args.no_fallbacks else args.fallback_dir
    container, manifest, include_text, sounds = build_assets(
        vswap_path=args.vswap,
        audiohed_path=args.audiohed,
        audiot_path=args.audiot,
        audio_header_path=args.audio_header,
        wl_game_path=args.wl_game,
        fallback_dir=fallback_dir,
    )
    write_assets(
        output_dir=args.output_dir,
        include_path=args.include,
        container=container,
        manifest=manifest,
        include_text=include_text,
    )

    totals = manifest["totals"]
    print(
        f"Generated {args.output_dir / CONTAINER_FILENAME}: "
        f"{totals['containerRecords']} records, "
        f"{totals['residentPcmBytes']} resident PCM bytes, "
        f"{totals['containerBytes']} container bytes"
    )
    print(f"Generated {args.output_dir / MANIFEST_FILENAME}")
    print(f"Generated {args.include}")
    missing = [sound.name for sound in sounds if sound.required and not sound.available]
    if missing:
        print("Required sounds still unavailable: " + ", ".join(missing))
    else:
        print("All current environment/combat/pickup sounds have assets.")


if __name__ == "__main__":
    main()
