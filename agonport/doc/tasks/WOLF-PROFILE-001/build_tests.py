"""Prepare finite actual-eZ80 profiling cases; compiler lease required."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SPEC = importlib.util.spec_from_file_location("profile_builder", ROOT / "src/asm/wolf3d/scripts/build.py")
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)


def once(s, old, new):
    if s.count(old) != 1:
        raise ValueError(f"Expected one source anchor: {old!r}")
    return s.replace(old, new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    if not args.revision.replace("-", "").isalnum():
        parser.error("revision must be alphanumeric/hyphen")
    out = HERE / "build" / args.revision
    out.mkdir(parents=True, exist_ok=False)
    receipts = {}
    for case in ("writer", "short-write", "native-join", "full-game"):
        folder = out / case
        src = folder / "source"
        shutil.copytree(b.SOURCE, src)
        native, full = case == "native-join", case == "full-game"
        b.select_backend(src / "wolf3d_backend.inc", "vdplet-direct" if native else "standalone")
        b.select_profile(src / "wolf3d_backend.inc", True, native)
        if native:
            # No target native execution is claimed. Exercise the real assembly
            # native record joining with independent, labelled synthetic replies.
            b.select_package(src / "wolf3d_vdplet_package.inc", 22572)
            p = src / "wolf3d_profile.inc"
            s = p.read_text()
            s = once(s, "wp_native_read16:\n", "wp_native_read16:\n    jp wp_test_read16\nwp_native_read16_unused:\n")
            s = once(s, "wp_native_reset:\n", "wp_native_reset:\n    or a\n    ret\nwp_native_reset_unused:\n")
            p.write_text(s)
            raw = struct.pack("<4sIII", b"WPN1", 1, 120, 52685)
            raw += b"".join(struct.pack("<IIIII", i, 0, 4800000, 4824000, 4848000) for i in range(120))
            (src / "native-mock.inc").write_text("\n".join("    db " + ",".join(str(x) for x in raw[i:i+16]) for i in range(0, len(raw), 16)) + "\n")
        if case == "short-write":
            p = src / "wolf3d_profile.inc"
            s = p.read_text()
            assert s.count("    MOSCALL mos_fwrite") == 2
            p.write_text(s.replace("    MOSCALL mos_fwrite", "    call wp_test_short_write"))
        # A labelled test-only hold makes the actual disk cue observable to
        # capture; its cost is inside the logging gap, never a speed result.
        p = src / "wolf3d_profile.inc"
        p.write_text(once(p.read_text(), "wp_flush:\n", "wp_flush:\n    call wp_test_hold\n"))
        p = src / "wolf3d.asm"
        s = p.read_text()
        if full:
            s = once(s, "    call w3d_main_body\n", "    call wp_test\n")
            s = once(s, "    call w3d_poll_keys\n", "    call w3d_poll_keys\n    call wp_test_steer\n")
        else:
            s = once(s, "    call main\n", "    call wp_test\n")
        s = once(s, "    W3D_PROFILE_CALL w3d_profile_finish\n", "    W3D_PROFILE_CALL w3d_profile_finish\n    call wp_test_result\n")
        s += "\nWPT_FULL_GAME: equ " + str(int(full)) + "\nWPT_NATIVE_MOCK: equ " + str(int(native))
        s += "\nWPT_FRAMES: equ " + str(250 if full else 240) + '\n    include "selftest.inc"\n'
        p.write_text(s)
        shutil.copyfile(HERE / "selftest.inc", src / "selftest.inc")
        binary = src / "test.bin"
        with (folder / "assemble.log").open("w") as log:
            subprocess.run([str(b.resolve_assembler(None)), "wolf3d.asm", binary.name, "-l", "-c"], cwd=src,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
        receipts[case] = {"binary": str(binary), "bytes": binary.stat().st_size,
                          "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                          "native_synthetic": native, "full_game": full,
                          "expected_status": 3 if case == "short-write" else 0,
                          "minimum_frames": 120 if case == "short-write" else 240,
                          "inputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(src.iterdir()) if p.suffix in (".inc", ".asm")}}
    (out / "receipt.json").write_text(json.dumps(receipts, indent=2) + "\n")
    print(json.dumps({k: {a: v for a, v in d.items() if a != "inputs"} for k, d in receipts.items()}, indent=2))


if __name__ == "__main__":
    main()
