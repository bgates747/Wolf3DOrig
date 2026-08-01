from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(TOOLS_ROOT))

from formats.audio_catalog import (
    CURRENT_PRODUCERS,
    FALLBACKS,
    UPLOAD_DIGI_MAP,
    command_buffer_ids,
    sample_buffer_id,
)
from scripts.build_audio_assets import (
    DEFAULT_AUDIO_HEADER,
    DEFAULT_AUDIOHED,
    DEFAULT_AUDIOT,
    DEFAULT_FALLBACK_DIR,
    DEFAULT_INCLUDE,
    DEFAULT_VSWAP,
    DEFAULT_WL_GAME,
    GAIN_FORWARD_ROWS,
    GAIN_LATERAL_COLUMNS,
    build_assets,
    build_mono_gain_table,
    parse_attenuation_tables,
    write_assets,
)


def _riff_chunks(data: bytes, start: int, end: int):
    offset = start
    while offset < end:
        if offset + 8 > end:
            raise AssertionError("truncated RIFF chunk header")
        chunk_id = data[offset : offset + 4]
        size = struct.unpack_from("<I", data, offset + 4)[0]
        payload_start = offset + 8
        payload_end = payload_start + size
        aligned_end = payload_start + ((size + 3) & ~3)
        if payload_end > end or aligned_end > end:
            raise AssertionError("RIFF chunk escapes its parent")
        if any(data[payload_end:aligned_end]):
            raise AssertionError("RIFF chunk padding is not zero")
        yield chunk_id, data[payload_start:payload_end]
        offset = aligned_end
    if offset != end:
        raise AssertionError(f"RIFF alignment ended at {offset}, expected {end}")


def _audio_records(container: bytes) -> list[tuple[int, int, int, bytes]]:
    if container[:4] != b"RIFF" or container[8:12] != b"AGNB":
        raise AssertionError("not an AGNB RIFF file")
    if struct.unpack_from("<I", container, 4)[0] != len(container) - 8:
        raise AssertionError("RIFF size does not cover the complete container")

    chunks = list(_riff_chunks(container, 12, len(container)))
    if not chunks or chunks[0] != (b"VERS", b"\x00\x02"):
        raise AssertionError("audio container is not canonical AGNB 0.2")

    records: list[tuple[int, int, int, bytes]] = []
    for chunk_id, payload in chunks[1:]:
        if chunk_id != b"LIST" or payload[:4] != b"BUFR":
            raise AssertionError("unexpected top-level audio chunk")
        nested = list(_riff_chunks(payload, 4, len(payload)))
        if [chunk_id for chunk_id, _ in nested] != [b"BHDR", b"AUDI", b"DATA"]:
            raise AssertionError("audio record is not BHDR/AUDI/DATA")
        buffer_id = struct.unpack("<H", nested[0][1])[0]
        vdp_format, sample_rate = struct.unpack("<BH", nested[1][1])
        records.append((buffer_id, vdp_format, sample_rate, nested[2][1]))
    return records


def _independent_vswap_sounds(data: bytes) -> tuple[bytes | None, ...]:
    """Small test-only extraction path, independent of formats.audio."""

    chunk_count, _sprite_start, sound_start = struct.unpack_from("<HHH", data)
    offsets = struct.unpack_from(f"<{chunk_count}I", data, 6)
    lengths = struct.unpack_from(f"<{chunk_count}H", data, 6 + 4 * chunk_count)

    def chunk(index: int) -> bytes:
        offset, length = offsets[index], lengths[index]
        return data[offset : offset + length] if offset and length else b""

    directory = chunk(chunk_count - 1)
    sounds: list[bytes | None] = []
    for start_page, byte_length in struct.iter_unpack("<HH", directory):
        page_count = (byte_length + 4095) // 4096
        pages = [chunk(sound_start + start_page + page) for page in range(page_count)]
        if any(not page for page in pages):
            sounds.append(None)
        else:
            sounds.append(b"".join(pages)[:byte_length])
    return tuple(sounds)


def _independent_wav(path: Path) -> tuple[int, bytes]:
    with wave.open(str(path), "rb") as wav_file:
        if (
            wav_file.getnchannels() != 1
            or wav_file.getsampwidth() != 1
            or wav_file.getcomptype() != "NONE"
        ):
            raise AssertionError(f"test fallback is not unsigned-8 mono PCM: {path}")
        return wav_file.getframerate(), wav_file.readframes(wav_file.getnframes())


class AudioAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls.temporary.name) / "audio"
        cls.include_path = Path(cls.temporary.name) / "wolf3d_audio_assets.inc"
        cls.container, cls.manifest, cls.include_text, cls.sounds = build_assets(
            vswap_path=DEFAULT_VSWAP,
            audiohed_path=DEFAULT_AUDIOHED,
            audiot_path=DEFAULT_AUDIOT,
            audio_header_path=DEFAULT_AUDIO_HEADER,
            wl_game_path=DEFAULT_WL_GAME,
            fallback_dir=DEFAULT_FALLBACK_DIR,
        )
        write_assets(
            output_dir=cls.output_dir,
            include_path=cls.include_path,
            container=cls.container,
            manifest=cls.manifest,
            include_text=cls.include_text,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_inventory_covers_current_producers_without_gaps(self) -> None:
        self.assertEqual(len(self.sounds), 69)
        self.assertEqual(len(UPLOAD_DIGI_MAP), 20)
        self.assertEqual(len(FALLBACKS), 19)
        self.assertTrue(
            set(CURRENT_PRODUCERS) <= set(UPLOAD_DIGI_MAP) | set(FALLBACKS)
        )
        self.assertEqual(
            set(UPLOAD_DIGI_MAP) - set(CURRENT_PRODUCERS),
            {
                "DEATHSCREAM3SND",
                "GUTENTAGSND",
                "MUTTISND",
                "BOSSFIRESND",
            },
        )
        by_name = {sound.name: sound for sound in self.sounds}
        missing = [name for name in CURRENT_PRODUCERS if not by_name[name].available]
        self.assertEqual(missing, [])
        self.assertEqual(self.manifest["totals"]["nativeRecords"], 20)
        self.assertEqual(self.manifest["totals"]["fallbackRecords"], 19)
        self.assertEqual(self.manifest["totals"]["containerRecords"], 39)
        self.assertEqual(
            self.manifest["totals"]["requiredUnavailableLogicalSounds"], 0
        )

    def test_native_vswap_pcm_is_preserved_byte_for_byte_at_7000_hz(self) -> None:
        source_sounds = _independent_vswap_sounds(DEFAULT_VSWAP.read_bytes())
        available_indices = {
            index for index, pcm in enumerate(source_sounds) if pcm is not None
        }
        self.assertEqual(available_indices, set(range(16)) | {20, 21, 22, 32})

        records = {buffer_id: (vdp_format, rate, pcm) for buffer_id, vdp_format, rate, pcm in _audio_records(self.container)}
        by_name = {sound.name: sound for sound in self.sounds}
        for name, digi_index in UPLOAD_DIGI_MAP.items():
            sound = by_name[name]
            vdp_format, rate, pcm = records[sample_buffer_id(sound.logical_id)]
            self.assertEqual(vdp_format, 0x09)
            self.assertEqual(rate, 7000)
            self.assertEqual(pcm, source_sounds[digi_index])

    def test_fallback_pcm_is_preserved_byte_for_byte_at_its_native_rate(self) -> None:
        records = {buffer_id: (rate, pcm) for buffer_id, _format, rate, pcm in _audio_records(self.container)}
        by_name = {sound.name: sound for sound in self.sounds}
        for name, fallback in FALLBACKS.items():
            expected_rate, expected_pcm = _independent_wav(
                DEFAULT_FALLBACK_DIR / fallback.filename
            )
            sound = by_name[name]
            rate, pcm = records[sample_buffer_id(sound.logical_id)]
            self.assertEqual(rate, expected_rate)
            self.assertEqual(pcm, expected_pcm)
            self.assertEqual(sound.source_kind, "test_pack_fallback")

    def test_container_is_exact_agnb_02_and_uses_stable_noncolliding_ids(self) -> None:
        records = _audio_records(self.container)
        available_ids = [sound.logical_id for sound in self.sounds if sound.available]
        self.assertEqual(
            [buffer_id for buffer_id, _format, _rate, _pcm in records],
            [sample_buffer_id(logical_id) for logical_id in available_ids],
        )
        sample_ids = {sample_buffer_id(logical_id) for logical_id in range(69)}
        command_ids = {
            command_id
            for logical_id in range(69)
            for command_id in command_buffer_ids(logical_id)
        }
        self.assertEqual(len(sample_ids), 69)
        self.assertEqual(len(command_ids), 69 * 3)
        self.assertTrue(sample_ids.isdisjoint(command_ids))
        self.assertEqual(min(sample_ids), 0x5000)
        self.assertEqual(max(sample_ids), 0x5044)
        self.assertEqual(min(command_ids), 0x6000)
        self.assertEqual(max(command_ids), 0x60CE)
        self.assertIn("W3D_AUDIO_SOUND_ATKKNIFE: equ 23", self.include_text)
        self.assertNotIn("W3D_SOUND_ATKKNIFE", self.include_text)

    def test_manifest_priorities_are_exact_original_adlib_priorities(self) -> None:
        audiohed = DEFAULT_AUDIOHED.read_bytes()
        audiot = DEFAULT_AUDIOT.read_bytes()
        offsets = struct.unpack(f"<{len(audiohed) // 4}I", audiohed)
        expected = [
            struct.unpack_from("<H", audiot, offsets[69 + logical_id] + 4)[0]
            for logical_id in range(69)
        ]
        self.assertEqual(
            [entry["priority"] for entry in self.manifest["sounds"]], expected
        )

    def test_unavailable_records_remain_explicit_when_fallbacks_are_disabled(self) -> None:
        _container, manifest, _include, sounds = build_assets(
            vswap_path=DEFAULT_VSWAP,
            audiohed_path=DEFAULT_AUDIOHED,
            audiot_path=DEFAULT_AUDIOT,
            audio_header_path=DEFAULT_AUDIO_HEADER,
            wl_game_path=DEFAULT_WL_GAME,
            fallback_dir=None,
        )
        by_name = {sound.name: sound for sound in sounds}
        for name in FALLBACKS:
            self.assertFalse(by_name[name].available)
        manifest_by_name = {entry["name"]: entry for entry in manifest["sounds"]}
        for name in FALLBACKS:
            entry = manifest_by_name[name]
            self.assertIsNone(entry["sampleBufferId"])
            self.assertEqual(entry["commandBufferIds"], [])
            self.assertEqual(
                entry["reservedSampleBufferId"], sample_buffer_id(entry["logicalId"])
            )
            self.assertEqual(
                entry["reservedCommandBufferIds"],
                list(command_buffer_ids(entry["logicalId"])),
            )
            self.assertEqual(entry["unavailableReason"], "fallback collection disabled")

    def test_mono_gain_table_matches_original_source_and_contract(self) -> None:
        left, right = parse_attenuation_tables(DEFAULT_WL_GAME.read_text(encoding="latin-1"))
        self.assertEqual((len(left), len(right)), (15, 15))
        self.assertTrue(all(len(row) == 30 for row in left + right))
        for row in range(GAIN_FORWARD_ROWS):
            self.assertEqual(left[row], tuple(reversed(right[row])))

        gains = build_mono_gain_table(left, right)
        self.assertEqual(len(gains), GAIN_FORWARD_ROWS * GAIN_LATERAL_COLUMNS)
        self.assertTrue(all(0 <= gain <= 127 for gain in gains))
        for row in range(GAIN_FORWARD_ROWS):
            gain_row = gains[row * 30 : (row + 1) * 30]
            self.assertEqual(gain_row, tuple(reversed(gain_row)))
            for column, (left_attenuation, right_attenuation) in enumerate(
                zip(left[row], right[row])
            ):
                attenuation = (left_attenuation + right_attenuation + 1) // 2
                expected = round((15 - attenuation) * 127 / 15)
                self.assertEqual(gain_row[column], expected)

        self.assertEqual(gains[0 * 30 + 15], 127)
        self.assertEqual(gains[0 * 30 + 0], 59)
        self.assertEqual(gains[14 * 30 + 15], 59)

        manifest_gain = self.manifest["monoGainTable"]
        self.assertEqual(manifest_gain["bytes"], 450)
        self.assertEqual(manifest_gain["rows"], 15)
        self.assertEqual(manifest_gain["columns"], 30)
        table_section = self.include_text.split("w3d_audio_mono_gain_table:\n", 1)[1]
        table_section = table_section.split("w3d_audio_mono_gain_table_end:", 1)[0]
        emitted = tuple(
            int(value)
            for line in table_section.splitlines()
            if line.strip().startswith("db ")
            for value in line.split("db ", 1)[1].split(",")
        )
        self.assertEqual(emitted, gains)

    def test_generated_outputs_are_deterministic_and_tracked_include_is_current(self) -> None:
        second = build_assets(
            vswap_path=DEFAULT_VSWAP,
            audiohed_path=DEFAULT_AUDIOHED,
            audiot_path=DEFAULT_AUDIOT,
            audio_header_path=DEFAULT_AUDIO_HEADER,
            wl_game_path=DEFAULT_WL_GAME,
            fallback_dir=DEFAULT_FALLBACK_DIR,
        )
        self.assertEqual(second[0], self.container)
        self.assertEqual(second[1], self.manifest)
        self.assertEqual(second[2], self.include_text)
        self.assertEqual(DEFAULT_INCLUDE.read_text(), self.include_text)
        self.assertEqual(
            json.loads((self.output_dir / "audio_manifest.json").read_text()),
            self.manifest,
        )
        self.assertEqual((self.output_dir / "sfx.agnb").read_bytes(), self.container)


if __name__ == "__main__":
    unittest.main()
