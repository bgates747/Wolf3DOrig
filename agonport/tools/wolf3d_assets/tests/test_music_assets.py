from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from agonport.tools.wolf3d_assets.formats.music import (
    EPISODE_ONE_FLOOR_MUSIC,
    MUSIC_NAMES,
    REQUIRED_MUSIC_IDS,
    SHELL_MUSIC,
    START_MUSIC_CHUNK,
    read_music_tracks,
)
from agonport.tools.wolf3d_assets.scripts.build_music_assets import (
    DEFAULT_AUDIOHED,
    DEFAULT_AUDIOT,
    build,
)


REPO_ROOT = Path(__file__).resolve().parents[4]


class MusicAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audiohed = DEFAULT_AUDIOHED.read_bytes()
        cls.audiot = DEFAULT_AUDIOT.read_bytes()
        cls.tracks = read_music_tracks(cls.audiohed, cls.audiot)

    def test_archive_uses_full_music_layout(self) -> None:
        self.assertEqual(START_MUSIC_CHUNK, 261)
        self.assertEqual(len(self.tracks), 27)
        self.assertEqual(self.tracks[0].chunk_index, 261)
        self.assertEqual(self.tracks[-1].chunk_index, 287)

    def test_required_episode_one_tracks_exist(self) -> None:
        self.assertEqual(
            [self.tracks[index].name for index in REQUIRED_MUSIC_IDS],
            [
                "CORNER",
                "WARMARCH",
                "GETTHEM",
                "NAZI_NOR",
                "POW",
                "SEARCHN",
                "SUSPENSE",
                "WONDERIN",
                "ENDLEVEL",
                "ROSTER",
                "URAHERO",
            ],
        )
        self.assertTrue(all(self.tracks[index].available for index in REQUIRED_MUSIC_IDS))

    def test_source_assignments_match_shareware(self) -> None:
        self.assertEqual(EPISODE_ONE_FLOOR_MUSIC, (3, 11, 9, 12, 3, 11, 9, 12, 2, 0))
        self.assertEqual(
            SHELL_MUSIC,
            {
                "title": 7,
                "menu": 14,
                "read_this": 0,
                "high_scores": 23,
                "intermission": 16,
                "victory": 24,
            },
        )

    def test_cumulative_timing_has_no_event_rounding_drift(self) -> None:
        for track in self.tracks:
            if not track.available:
                continue
            self.assertEqual(
                sum(event.delay_120hz for event in track.events),
                track.loop_ticks_120hz,
            )
            expected = (track.source_ticks * 120 + 350) // 700
            self.assertEqual(track.loop_ticks_120hz, expected)

    def test_known_canonical_track_hashes(self) -> None:
        expected = {
            "NAZI_NOR": "ee9207f54616ebf4c9ce28cda4ddac8a71535e87c69d53f6755a22c69221c81f",
            "GETTHEM": "1554dd047870bc2efe555d0477b9621c11e645c815e01c49054ff2500922fef1",
            "ENDLEVEL": "9d4d16ccff95fb0add3c31655cd0ba027987925ddde03fba24149f5e2f11342a",
        }
        by_name = {track.name: track for track in self.tracks}
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256(by_name[name].source_bytes).hexdigest(), digest)

    def test_builder_is_deterministic_and_manifest_matches_include(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            include = root / "wolf3d_music_assets.inc"
            manifest_path = root / "music_manifest.json"
            manifest = build(DEFAULT_AUDIOHED, DEFAULT_AUDIOT, include, manifest_path)
            parsed = json.loads(manifest_path.read_text())
            self.assertEqual(parsed, manifest)
            payload = include.read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), manifest["generated_include"]["sha256"])
            self.assertIn(b"w3d_music_track_getthem:", payload)
            self.assertIn(b"W3D_MUSIC_URAHERO: equ 24", payload)
            self.assertEqual(
                payload,
                (REPO_ROOT / "src/asm/wolf3d/src/wolf3d_music_assets.inc").read_bytes(),
            )

    def test_production_lifecycle_owns_original_assignments(self) -> None:
        source = REPO_ROOT / "src/asm/wolf3d/src"
        app = (source / "wolf3d.asm").read_text()
        shell = (source / "wolf3d_shell.inc").read_text()
        loader = (source / "wolf3d_level_loader.inc").read_text()
        self.assertIn(
            "ld a,W3D_MUSIC_ENDLEVEL\n    call w3d_music_start\n"
            "    call w3d_intermission_begin",
            app,
        )
        self.assertIn("call w3d_music_start_current_floor", loader)
        for assignment in (
            "W3D_MUSIC_NAZI_NOR",
            "W3D_MUSIC_WONDERIN",
            "W3D_MUSIC_CORNER",
            "W3D_MUSIC_ROSTER",
            "W3D_MUSIC_URAHERO",
        ):
            self.assertIn(f"ld a,{assignment}\n    call w3d_music_start", shell)
        self.assertIn("call w3d_music_service\n    MOSCALL mos_getkbmap", shell)


if __name__ == "__main__":
    unittest.main()
