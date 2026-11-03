"""Decode the four recorded Episode 1 shareware demonstrations.

The distributed WL1 archive does not carry loose ``DEMO?.WL1`` files.  Its
four recordings are ordinary Huffman-compressed extern chunks in
``VGAGRAPH.WL1``.  Each expanded stream starts with a one-byte zero-based map,
a little-endian total byte length, and one reserved byte, followed by
three-byte ``buttonBits, controlX, controlY`` records.  The two controls are
signed bytes and each record owns the original engine's four 70-Hz tics.
"""

from __future__ import annotations

from dataclasses import dataclass

from .vgagraph import VgaGraph


DEMO_HEADER_SIZE = 4
DEMO_RECORD_SIZE = 3
DEMO_MAPS = (0, 2, 4, 6)


@dataclass(frozen=True)
class RecordedDemo:
    chunk_id: int
    map_index: int
    reserved: int
    records: bytes
    expanded: bytes

    @property
    def record_count(self) -> int:
        return len(self.records) // DEMO_RECORD_SIZE


def find_recorded_demos(archive: VgaGraph) -> tuple[RecordedDemo, ...]:
    """Find and validate the canonical four demo extern chunks by content."""

    candidates: list[RecordedDemo] = []
    for chunk_id in range(len(archive.offsets) - 1):
        try:
            expanded = archive.expand_chunk(chunk_id)
        except (IndexError, ValueError):
            continue
        if len(expanded) < DEMO_HEADER_SIZE:
            continue
        declared = int.from_bytes(expanded[1:3], "little")
        records = expanded[DEMO_HEADER_SIZE:]
        if (
            expanded[0] not in DEMO_MAPS
            or declared != len(expanded)
            or len(records) % DEMO_RECORD_SIZE
        ):
            continue
        if any(records[index] & 0xF0 for index in range(0, len(records), 3)):
            continue
        candidates.append(
            RecordedDemo(
                chunk_id=chunk_id,
                map_index=expanded[0],
                reserved=expanded[3],
                records=records,
                expanded=expanded,
            )
        )

    candidates.sort(key=lambda demo: demo.map_index)
    if tuple(demo.map_index for demo in candidates) != DEMO_MAPS:
        raise ValueError(
            "VGAGRAPH must contain exactly the four Episode 1 demo maps "
            f"{DEMO_MAPS}; found "
            f"{[(demo.chunk_id, demo.map_index) for demo in candidates]}"
        )
    return tuple(candidates)
