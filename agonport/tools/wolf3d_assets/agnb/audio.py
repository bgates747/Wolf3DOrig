"""Canonical AGNB 0.2 audio-container writer for Wolf3D sound assets."""

from __future__ import annotations

from dataclasses import dataclass
import struct

from .container import MAX_U32, make_chunk


VERSION_MAJOR = 0
VERSION_MINOR = 2
VDP_FORMAT_UNSIGNED_8BIT_MONO_WITH_RATE = 0x09
INVALID_BUFFER_ID = 0xFFFF


@dataclass(frozen=True)
class AudioBufferRecord:
    logical_id: int
    name: str
    buffer_id: int
    sample_rate: int
    pcm: bytes


def validate_record(record: AudioBufferRecord) -> None:
    if not 0 <= record.logical_id <= 0xFF:
        raise ValueError(f"logical sound id is outside u8: {record.logical_id}")
    if not record.name:
        raise ValueError("audio record name must not be empty")
    if not 0 <= record.buffer_id < INVALID_BUFFER_ID:
        raise ValueError(f"invalid audio buffer id: {record.buffer_id:#x}")
    if not 1 <= record.sample_rate <= 0xFFFF:
        raise ValueError(f"sample rate is outside u16: {record.sample_rate}")
    if not record.pcm:
        raise ValueError(f"audio record {record.name} has no PCM bytes")
    if len(record.pcm) > 0xFFFFFF:
        raise ValueError(
            f"audio record {record.name} exceeds the eZ80 loader's u24 limit"
        )


def make_audio_buffer_record(record: AudioBufferRecord) -> bytes:
    validate_record(record)
    nested = b"".join(
        (
            make_chunk(b"BHDR", struct.pack("<H", record.buffer_id)),
            make_chunk(
                b"AUDI",
                struct.pack(
                    "<BH",
                    VDP_FORMAT_UNSIGNED_8BIT_MONO_WITH_RATE,
                    record.sample_rate,
                ),
            ),
            make_chunk(b"DATA", record.pcm),
        )
    )
    return make_chunk(b"LIST", b"BUFR" + nested)


def build_audio_container(records: list[AudioBufferRecord]) -> bytes:
    if not records:
        raise ValueError("an AGNB audio container requires at least one record")

    seen_ids: set[int] = set()
    for record in records:
        validate_record(record)
        if record.buffer_id in seen_ids:
            raise ValueError(f"duplicate audio buffer id: {record.buffer_id:#x}")
        seen_ids.add(record.buffer_id)

    body = bytearray(b"AGNB")
    body.extend(make_chunk(b"VERS", bytes((VERSION_MAJOR, VERSION_MINOR))))
    for record in records:
        body.extend(make_audio_buffer_record(record))
    if len(body) > MAX_U32:
        raise ValueError(f"RIFF audio container is too large: {len(body) + 8}")
    return b"RIFF" + struct.pack("<I", len(body)) + body
