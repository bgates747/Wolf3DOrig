"""Original Wolf3D shareware audio-file decoders used by the Agon port.

The digitized effects are stored as 4096-byte pages at the end of
``VSWAP.WL1``.  The final VSWAP chunk is a directory of ``(startPage,
byteLength)`` pairs.  Sparse pages are intentional in the shareware file:
they preserve the full retail digitized-sound numbering while omitting
effects that the upload build never references.

``AUDIOHED.WL1`` and ``AUDIOT.WL1`` remain the authority for each logical
sound's original priority.  The initial port does not decode their PC-speaker
or AdLib payloads; only the common six-byte ``length, priority`` header is
needed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
import wave


PM_PAGE_SIZE = 4096
START_ADLIB_SOUNDS_WL1 = 69
MAX_U16 = 0xFFFF


@dataclass(frozen=True)
class DigitizedSound:
    """One entry in VSWAP's terminal digitized-sound directory."""

    digi_index: int
    start_page: int
    byte_length: int
    pcm: bytes | None
    missing_pages: tuple[int, ...]

    @property
    def available(self) -> bool:
        return self.pcm is not None


def _read_vswap_chunks(data: bytes) -> tuple[int, int, int, tuple[bytes, ...]]:
    if len(data) < 6:
        raise ValueError("VSWAP header is truncated")
    num_chunks, sprite_start, sound_start = struct.unpack_from("<HHH", data, 0)
    if num_chunks < 2:
        raise ValueError(f"VSWAP has too few chunks: {num_chunks}")
    table_end = 6 + num_chunks * 6
    if table_end > len(data):
        raise ValueError("VSWAP offset/length tables are truncated")
    if not 0 <= sprite_start <= sound_start < num_chunks - 1:
        raise ValueError(
            "VSWAP chunk boundaries are invalid: "
            f"sprites={sprite_start}, sounds={sound_start}, chunks={num_chunks}"
        )

    offsets = struct.unpack_from(f"<{num_chunks}I", data, 6)
    lengths = struct.unpack_from(f"<{num_chunks}H", data, 6 + num_chunks * 4)
    chunks: list[bytes] = []
    for index, (offset, length) in enumerate(zip(offsets, lengths)):
        if length == 0:
            if offset != 0:
                raise ValueError(
                    f"VSWAP sparse chunk {index} has nonzero offset {offset}"
                )
            chunks.append(b"")
            continue
        end = offset + length
        if offset < table_end or end > len(data):
            raise ValueError(
                f"VSWAP chunk {index} escapes the file: offset={offset}, length={length}"
            )
        chunks.append(data[offset:end])
    return num_chunks, sprite_start, sound_start, tuple(chunks)


def read_vswap_digitized_sounds(data: bytes) -> tuple[DigitizedSound, ...]:
    """Decode the final VSWAP sound directory and reconstruct available PCM.

    An entry whose page range contains a sparse chunk is returned as
    unavailable rather than fabricated.  For an available entry, every page
    must have exactly the number of bytes consumed by the original sound.
    """

    num_chunks, _sprite_start, sound_start, chunks = _read_vswap_chunks(data)
    directory = chunks[-1]
    if not directory or len(directory) % 4:
        raise ValueError(
            "VSWAP digitized-sound directory must be a nonempty sequence of "
            "four-byte entries"
        )

    sound_page_count = num_chunks - sound_start - 1
    sounds: list[DigitizedSound] = []
    previous_end = 0
    for digi_index, (start_page, byte_length) in enumerate(
        struct.iter_unpack("<HH", directory)
    ):
        if byte_length == 0:
            raise ValueError(f"VSWAP digitized sound {digi_index} has zero length")
        page_count = (byte_length + PM_PAGE_SIZE - 1) // PM_PAGE_SIZE
        end_page = start_page + page_count
        if start_page != previous_end:
            raise ValueError(
                f"VSWAP digitized sound {digi_index} starts at page {start_page}, "
                f"expected contiguous directory page {previous_end}"
            )
        if end_page > sound_page_count:
            raise ValueError(
                f"VSWAP digitized sound {digi_index} ends at page {end_page}, "
                f"past the {sound_page_count} sound pages"
            )
        previous_end = end_page

        absolute_pages = tuple(
            sound_start + start_page + offset for offset in range(page_count)
        )
        missing_pages = tuple(index for index in absolute_pages if not chunks[index])
        pcm: bytes | None
        if missing_pages:
            pcm = None
        else:
            parts: list[bytes] = []
            remaining = byte_length
            for page_index in absolute_pages:
                expected = min(PM_PAGE_SIZE, remaining)
                page = chunks[page_index]
                if len(page) != expected:
                    raise ValueError(
                        f"VSWAP sound page {page_index} has {len(page)} bytes, "
                        f"expected {expected} for digitized sound {digi_index}"
                    )
                parts.append(page)
                remaining -= expected
            pcm = b"".join(parts)
            if len(pcm) != byte_length:
                raise AssertionError("internal VSWAP digitized-sound size mismatch")

        sounds.append(
            DigitizedSound(
                digi_index=digi_index,
                start_page=start_page,
                byte_length=byte_length,
                pcm=pcm,
                missing_pages=missing_pages,
            )
        )

    if previous_end != sound_page_count:
        raise ValueError(
            f"VSWAP sound directory covers {previous_end} pages, "
            f"but the file contains {sound_page_count}"
        )
    return tuple(sounds)


def read_adlib_priorities(
    audio_header: bytes,
    audio_data: bytes,
    logical_sound_count: int,
    *,
    start_chunk: int = START_ADLIB_SOUNDS_WL1,
) -> tuple[int, ...]:
    """Read ``SoundCommon.priority`` from the WL1 AdLib sound chunks."""

    if len(audio_header) % 4:
        raise ValueError("AUDIOHED length is not a multiple of four")
    offsets = struct.unpack(f"<{len(audio_header) // 4}I", audio_header)
    required_offsets = start_chunk + logical_sound_count + 1
    if len(offsets) < required_offsets:
        raise ValueError(
            f"AUDIOHED has {len(offsets)} offsets, needs {required_offsets}"
        )

    priorities: list[int] = []
    for logical_id in range(logical_sound_count):
        chunk_index = start_chunk + logical_id
        start = offsets[chunk_index]
        end = offsets[chunk_index + 1]
        if start > end or end > len(audio_data) or end - start < 6:
            raise ValueError(
                f"AUDIOT AdLib chunk {chunk_index} has invalid bounds "
                f"{start}..{end}"
            )
        declared_length, priority = struct.unpack_from("<IH", audio_data, start)
        if declared_length > end - start - 6:
            raise ValueError(
                f"AUDIOT AdLib chunk {chunk_index} declares {declared_length} "
                f"data bytes in a {end - start}-byte chunk"
            )
        priorities.append(priority)
    return tuple(priorities)


def read_unsigned_pcm_wav(path: Path) -> tuple[int, bytes]:
    """Return the sample rate and PCM bytes from a mono unsigned-8 WAV."""

    with wave.open(str(path), "rb") as wav_file:
        if wav_file.getcomptype() != "NONE":
            raise ValueError(f"{path} is not uncompressed PCM")
        if wav_file.getnchannels() != 1:
            raise ValueError(f"{path} is not mono")
        if wav_file.getsampwidth() != 1:
            raise ValueError(f"{path} is not unsigned 8-bit PCM")
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        if not 1 <= sample_rate <= MAX_U16:
            raise ValueError(f"{path} sample rate is outside u16: {sample_rate}")
        if frame_count == 0:
            raise ValueError(f"{path} contains no PCM frames")
        pcm = wav_file.readframes(frame_count)
    if len(pcm) != frame_count:
        raise ValueError(
            f"{path} returned {len(pcm)} bytes for {frame_count} unsigned-8 frames"
        )
    return sample_rate, pcm
