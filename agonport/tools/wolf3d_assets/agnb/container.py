"""AGNB 0.1 RIFF container writer (BHDR + IMAG + DATA per buffer record).

Forked 2026-07-31 from agon-utils' examples/agnb/images/container/scripts/
do_assembly.py (RIFF chunk-building helpers only: align4/make_chunk/
make_buffer_record/build_container) per Author decision to vendor canonical
AGNB tooling rather than import across project boundaries. Deliberately
drops that script's eZ80 .inc/equ-table generation and ez80asm invocation --
unneeded here since this project's buffer ids are formula-derived from
kind+assetId (see agnb/manifest.py), not named per-asset constants.

On-disk format (unchanged from the canonical spec, see agon-utils'
docs/agon-buffer-file-format-specification.md and this project's
agonport/doc/wolf3d-asset-toolchain-plan.md)::

    RIFF  u32(file_size - 8)  AGNB
      VERS  size=2            u8 major=0, u8 minor=1
      LIST  type=BUFR
        BHDR  size=2          u16 bufferId
        IMAG  size=5          u16 width, u16 height, u8 format=1 (RGBA2222)
        DATA  size=width*height   u8 pixels[]  (row-major, no row padding)
"""

import struct
from dataclasses import dataclass
from pathlib import Path

VERSION_MAJOR = 0
VERSION_MINOR = 1
IMAGE_FORMAT_RGBA2222 = 1
MAX_U32 = 0xFFFFFFFF


@dataclass(frozen=True)
class BufferRecord:
    """One validated LIST BUFR image record's inputs."""

    name: str
    bufferId: int
    width: int
    height: int
    rgba2File: Path
    dataSize: int


def align4(size: int) -> int:
    return (size + 3) & ~3


def make_chunk(chunk_id: bytes, payload: bytes) -> bytes:
    """Return one aligned RIFF chunk, including its header and zero padding."""
    if len(chunk_id) != 4:
        raise ValueError(f"RIFF chunk ID must contain four bytes: {chunk_id!r}")
    if len(payload) > MAX_U32:
        raise ValueError(f"RIFF payload is too large: {len(payload)} bytes")

    padding = bytes(align4(len(payload)) - len(payload))
    return chunk_id + struct.pack("<I", len(payload)) + payload + padding


def make_buffer_record(record: BufferRecord) -> bytes:
    """Return one aligned LIST BUFR record."""
    pixels = record.rgba2File.read_bytes()
    if len(pixels) != record.dataSize:
        raise RuntimeError(f"RGBA2222 file changed while building: {record.rgba2File}")

    nested_chunks = b"".join(
        (
            make_chunk(b"BHDR", struct.pack("<H", record.bufferId)),
            make_chunk(
                b"IMAG",
                struct.pack("<HHB", record.width, record.height, IMAGE_FORMAT_RGBA2222),
            ),
            make_chunk(b"DATA", pixels),
        )
    )
    return make_chunk(b"LIST", b"BUFR" + nested_chunks)


def build_container(records: list[BufferRecord]) -> bytes:
    """Compile validated buffer records into one complete RIFF AGNB file."""
    if not records:
        raise ValueError("An AGNB container requires at least one buffer record")

    seen_ids = set()
    for record in records:
        if record.bufferId in seen_ids:
            raise ValueError(f"Duplicate bufferId in container: {record.bufferId}")
        seen_ids.add(record.bufferId)

    body = bytearray(b"AGNB")
    body.extend(make_chunk(b"VERS", bytes((VERSION_MAJOR, VERSION_MINOR))))
    for record in records:
        body.extend(make_buffer_record(record))

    if len(body) > MAX_U32:
        raise ValueError(f"RIFF container is too large: {len(body) + 8} bytes")
    return b"RIFF" + struct.pack("<I", len(body)) + body
