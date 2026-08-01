from __future__ import annotations

import random
import re
from pathlib import Path
import unittest

import audio_oracle as ao


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


class AudioOracleTests(unittest.TestCase):
    def test_ranges_and_wire_lengths_are_stable(self) -> None:
        self.assertEqual(ao.sample_buffer_id(0), 0x5000)
        self.assertEqual(ao.sample_buffer_id(68), 0x5044)
        self.assertEqual(ao.command_buffer_id(0, 0), 0x6000)
        self.assertEqual(ao.command_buffer_id(68, 2), 0x60CE)
        self.assertEqual(len(ao.buffered_wire(24, 0, 91)), 12)
        self.assertEqual(len(ao.direct_wire(24, 0, 91)), 23)
        self.assertEqual(len(ao.buffered_procedure(24, 0)), 23)
        self.assertEqual(len(ao.upload_wire(24, 0)), 37)

    def test_wire_sequences_reset_before_replacing_a_busy_channel(self) -> None:
        direct = ao.direct_wire(24, 2, 73)
        self.assertEqual(direct[:5], bytes((23, 0, 0x85, 2, 10)))
        self.assertEqual(direct[5:13], bytes((23, 0, 0x85, 2, 4, 8, 0x18, 0x50)))
        self.assertEqual(direct[13:], bytes((23, 0, 0x85, 2, 0, 73, 0, 0, 0, 0)))
        buffered = ao.buffered_wire(24, 2, 73)
        self.assertEqual(buffered, bytes((23, 0, 0xA0, 0x4A, 0x60, 1,
                                          23, 0, 0x85, 2, 2, 73)))

    def test_priorities_match_generated_asset_table(self) -> None:
        generated = ROOT / "src/asm/wolf3d/src/wolf3d_audio_assets.inc"
        values = [
            int(value)
            for value in re.findall(r"^\s*db\s+(\d+),0x[0-9A-F]{2}$", generated.read_text(), re.M)
        ]
        self.assertEqual(tuple(values), ao.PRIORITIES)
        self.assertEqual(len(values), ao.SOUND_COUNT)

    def test_same_quantum_priority_and_stable_ties(self) -> None:
        audio = ao.AudioOracle()
        audio.loaded.update((6, 18, 23, 24, 30))
        audio.begin_quantum()
        for sound in (23, 24, 6, 18, 30):
            self.assertTrue(audio.request(sound, 100, ao.FLAG_POSITIONED))
        # Active AdLib priorities: GETMACHINE 90, NOWAY 50, knife/pistol 1.
        self.assertEqual([event.sound for event in audio.pending], [30, 6, 23])
        self.assertEqual(audio.dropped_requests, 2)
        emissions = audio.flush_quantum()
        self.assertEqual([item.channel for item in emissions], [0, 1, 2])

        audio.begin_quantum()
        for sound in (7, 8, 9):  # all priority 50
            audio.loaded.add(sound)
            audio.request(sound, 127)
        self.assertEqual([event.sound for event in audio.pending], [7, 8, 9])

    def test_catchup_suppression_and_round_robin(self) -> None:
        audio = ao.AudioOracle()
        audio.loaded.update(range(ao.SOUND_COUNT))
        audio.begin_quantum()
        audio.request(9, 127)
        audio.discard_quantum()
        audio.begin_quantum()
        audio.request(24, 127)
        self.assertEqual([item.channel for item in audio.flush_quantum()], [0])
        self.assertEqual(audio.discarded_quanta, 1)
        self.assertEqual(audio.discarded_events, 1)

        for expected in (1, 2, 0, 1):
            audio.begin_quantum()
            audio.request(23, 127)
            self.assertEqual(audio.flush_quantum()[0].channel, expected)

    def test_random_batches_match_independent_top_three_reference(self) -> None:
        rng = random.Random(0x573D)
        audio = ao.AudioOracle()
        audio.loaded.update(range(ao.SOUND_COUNT))
        for _ in range(10_000):
            audio.begin_quantum()
            raw: list[tuple[int, int]] = []
            for order in range(rng.randrange(0, 12)):
                sound = rng.randrange(ao.SOUND_COUNT)
                raw.append((sound, order))
                audio.request(sound, rng.randrange(1, 160), rng.randrange(2))
            expected = sorted(raw, key=lambda item: -ao.PRIORITIES[item[0]])[:3]
            self.assertEqual(
                [(item.sound, item.order) for item in audio.pending], expected
            )
            if rng.randrange(4) == 0:
                audio.discard_quantum()
            else:
                audio.flush_quantum()


if __name__ == "__main__":
    unittest.main()
