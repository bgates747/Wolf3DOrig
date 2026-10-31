#!/usr/bin/env python3
"""Host-only checks for target/review preparation; never loads a backend."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REVIEW = ROOT / "review-rows"
BUILD = REVIEW / "build"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    sys.path.insert(0, str(HERE))
    qualifier = load(HERE / "qualify_rows.py", "wolf_rows_qualifier")
    assert qualifier.EXPECTED_CAPABILITY_MASK == 273
    assert qualifier.DIRECT_WORKSPACE_BYTES == 11552
    assert qualifier.COPIED_WORKSPACE_BYTES == 92160
    assert qualifier.DIRECT_GEOMETRY_OFFSET == 960
    assert qualifier.COPIED_GEOMETRY_OFFSET == 76800
    assert qualifier.rgb222_frame(bytes((0, 63))) == bytes((0, 0, 0, 255, 255, 255))
    assert qualifier.summary([1.0, 2.0, 3.0])["median"] == 2.0
    review_builder = load(REVIEW / "build.py", "wolf_rows_review_builder")
    guest_source = review_builder.direct_guest_source()
    assert "wolf3d_scene_rows.vdpl C code" in guest_source
    assert "Saves 80,608 workspace bytes; costs about 33% more cycles" in guest_source
    assert "MOS mode, cursor, callback, and buffers were restored" in guest_source
    assert "drawn entirely by wolf3d_scene.vdpl" not in guest_source

    BUILD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="prep-check-", dir=BUILD) as name:
        temporary = Path(name)
        jit = temporary / "jit.json"
        interp = temporary / "interp.json"
        jit.write_text('{"passed":true,"engine":"jit","synthetic":true}\n')
        interp.write_text('{"passed":true,"engine":"interp","synthetic":true}\n')
        package = temporary / "package"
        subprocess.run([
            sys.executable, str(REVIEW / "build.py"),
            "--guest-binary", str(Path(__file__)),
            "--jit-receipt", str(jit),
            "--interp-receipt", str(interp),
            "--output", str(package),
        ], check=True, stdout=subprocess.DEVNULL)
        expected = json.loads((package / "expected.json").read_text())
        assert expected["workspace_bytes"] == 11552
        assert expected["transactions"][0]["value"] == 287
        assert expected["files"]["wolf3d_scene_rows.vdpl"]["sha256"] == (
            "c32381bc659b6e1fcc479eef22168a77eea22da310202da794234f172ccab670"
        )
        assert expected["files"]["wolf3d_scene.vdpl"]["sha256"] == (
            "57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be"
        )

        missing = subprocess.run([
            sys.executable, str(REVIEW / "build.py"),
            "--guest-binary", str(Path(__file__)),
            "--jit-receipt", str(temporary / "missing-jit.json"),
            "--interp-receipt", str(interp),
            "--output", str(temporary / "must-not-exist"),
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert missing.returncode != 0
        assert "Both granted target runs must pass" in missing.stdout
        assert not (temporary / "must-not-exist").exists()

    print("rows preparation: pass helper and fail-closed review packaging")


if __name__ == "__main__":
    main()
