"""Minimal, strict Intel/Microsoft OMF LEDATA extraction.

Wolfenstein 3-D's shareware sign-on screen is linked into the DOS executable
as ``SIGNON.OBJ`` rather than stored in VGAGRAPH.  The object contains one
64,000-byte segment split across 16-bit LEDATA records.  This module extracts
that segment without depending on a host linker or checking in derived art.

The original Microsoft toolchain occasionally emits a zero checksum byte to
mean "checksum omitted".  Non-zero checksums remain strictly verified.
"""

from __future__ import annotations

import struct


class OmfError(ValueError):
    """Raised when an OMF stream violates the bounded extraction contract."""


def _read_index(data: bytes, offset: int) -> tuple[int, int]:
    if offset >= len(data):
        raise OmfError("truncated OMF index")
    first = data[offset]
    if first & 0x80:
        if offset + 1 >= len(data):
            raise OmfError("truncated two-byte OMF index")
        return ((first & 0x7F) << 8) | data[offset + 1], offset + 2
    return first, offset + 1


def extract_ledata_segment(
    blob: bytes,
    *,
    segment_index: int,
    expected_size: int,
) -> bytes:
    """Return one gapless 16-bit LEDATA segment from an OMF object.

    Only record type A0 (LEDATA16) contributes bytes.  Every selected range
    must be within ``expected_size`` and appear exactly once; gaps, overlaps,
    malformed records, and bad non-zero checksums are rejected.
    """

    if not 0 < segment_index < 0x8000:
        raise OmfError("segment index is outside the OMF index range")
    if expected_size <= 0 or expected_size > 0x10000:
        raise OmfError("expected LEDATA16 segment size is invalid")

    output = bytearray(expected_size)
    covered = bytearray(expected_size)
    position = 0
    selected_records = 0

    while position < len(blob):
        if len(blob) - position < 3:
            raise OmfError("truncated OMF record header")
        record_start = position
        record_type = blob[position]
        record_length = struct.unpack_from("<H", blob, position + 1)[0]
        position += 3
        if record_length < 1:
            raise OmfError("OMF record omits its checksum byte")
        record_end = position + record_length
        if record_end > len(blob):
            raise OmfError("OMF record extends beyond the input")
        payload = blob[position : record_end - 1]
        checksum = blob[record_end - 1]
        if checksum and sum(blob[record_start:record_end]) & 0xFF:
            raise OmfError("invalid OMF record checksum")
        position = record_end

        if record_type != 0xA0:
            continue
        record_segment, cursor = _read_index(payload, 0)
        if len(payload) - cursor < 2:
            raise OmfError("truncated LEDATA16 offset")
        data_offset = struct.unpack_from("<H", payload, cursor)[0]
        data = payload[cursor + 2 :]
        if record_segment != segment_index:
            continue
        if not data:
            raise OmfError("selected LEDATA16 record has no data")
        data_end = data_offset + len(data)
        if data_end > expected_size:
            raise OmfError("selected LEDATA16 record exceeds the segment")
        if any(covered[data_offset:data_end]):
            raise OmfError("selected LEDATA16 records overlap")
        output[data_offset:data_end] = data
        covered[data_offset:data_end] = b"\x01" * len(data)
        selected_records += 1

    if not selected_records:
        raise OmfError("requested OMF segment has no LEDATA16 records")
    if not all(covered):
        raise OmfError("requested OMF segment contains gaps")
    return bytes(output)
