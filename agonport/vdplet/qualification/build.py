#!/usr/bin/env python3
"""Build and host-qualify the bounded Wolf3D VDPlet scene."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJECT = ROOT.parents[1]
BUILD = HERE / "build"


def run(command: list[object], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(value) for value in command], check=True, **kwargs)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
    ).strip()


def verify_sdk_receipt(sdk: Path, receipt_path: Path | None) -> dict:
    if receipt_path is None:
        return {}
    receipt = json.loads(receipt_path.read_text())
    expected_root = (Path(receipt["sdk"]).resolve()
                     if "sdk" in receipt else sdk)
    if sdk != expected_root:
        raise AssertionError(f"SDK snapshot {sdk} does not match receipt {expected_root}")
    actual = {}
    for relative, expected in receipt["files"].items():
        path = sdk / relative
        actual[relative] = sha(path)
        if actual[relative] != expected:
            raise AssertionError(f"SDK receipt mismatch for {relative}")
    return {
        "candidate": receipt.get("candidate", receipt.get("source_baseline")),
        "baseline_commit": receipt.get("baseline_commit"),
        "contract_sha256": receipt.get("contract_sha256"),
        "receipt_path": str(receipt_path),
        "receipt_sha256": sha(receipt_path),
        "files": actual,
    }


def parse_stack(path: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in path.read_text().splitlines():
        fields = line.rsplit("\t", 2)
        if len(fields) == 3:
            result[fields[0].split(":", 3)[-1]] = int(fields[1])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sdk", type=Path,
        default=Path("/Agon/mystuff/agon-vdplet/build/vdpl-012/sdk"),
    )
    parser.add_argument(
        "--sdk-python", type=Path,
        default=Path("/Agon/mystuff/agon-vdplet/.venv/bin/python"),
    )
    parser.add_argument(
        "--sdk-receipt", type=Path,
        default=Path("/Agon/mystuff/agon-vdplet/build/vdpl-012/sdk/snapshot.json"),
    )
    parser.add_argument("--oracle", type=Path,
                        default=Path("/Agon/mystuff/agon-vdp-wolf3d"))
    args = parser.parse_args()
    sdk = args.sdk.resolve()
    sdk_python = args.sdk_python.resolve()
    sdk_receipt = (args.sdk_receipt.resolve()
                   if args.sdk_receipt is not None else None)
    oracle_root = args.oracle.resolve()
    verified_sdk = verify_sdk_receipt(sdk, sdk_receipt)
    BUILD.mkdir(parents=True, exist_ok=True)

    run([PROJECT / ".venv/bin/python", ROOT / "generate_fixture.py"])
    fixture = BUILD / "fixture"
    oracle = BUILD / "oracle"
    host_runner = BUILD / "host_runner"
    error_runner = BUILD / "error_runner"
    rows_runner = BUILD / "rows_runner"
    include = ["-I" + str(ROOT)]
    warnings = ["-Wall", "-Wextra", "-Werror"]
    run(["g++", "-std=c++17", "-O2", *warnings,
         "-I" + str(oracle_root), *include,
         HERE / "oracle.cpp", "-o", oracle])
    run(["g++", "-std=c++17", "-O2", *warnings, "-DWOLF3D_HOST_TEST",
         "-I" + str(sdk / "include"), *include, "-I" + str(HERE),
         ROOT / "wolf3d_scene.cpp", HERE / "host_runner.cpp", "-o", host_runner])
    run(["g++", "-std=c++17", "-O2", *warnings, "-DWOLF3D_HOST_TEST",
         "-I" + str(sdk / "include"), *include, "-I" + str(HERE),
         ROOT / "wolf3d_scene.cpp", HERE / "error_runner.cpp", "-o", error_runner])
    run(["g++", "-std=c++17", "-O2", *warnings, "-DWOLF3D_HOST_TEST",
         "-I" + str(sdk / "include"), *include, "-I" + str(HERE),
         ROOT / "wolf3d_scene_rows.cpp", HERE / "rows_runner.cpp", "-o", rows_runner])

    oracle_frame = BUILD / "oracle-frame.bin"
    oracle_geometry = BUILD / "oracle-geometry.bin"
    module_frame = BUILD / "module-frame.bin"
    module_geometry = BUILD / "module-geometry.bin"
    rows_frame = BUILD / "rows-frame.bin"
    rows_geometry = BUILD / "rows-geometry.bin"
    oracle_log = subprocess.check_output([
        str(oracle), str(fixture / "map.bin"), str(fixture / "textures.bin"),
        str(fixture / "config.bin"), str(oracle_frame), str(oracle_geometry)
    ], text=True).strip()
    host_log = subprocess.check_output([
        str(host_runner), str(fixture / "map.bin"), str(fixture / "textures.bin"),
        str(fixture / "config.bin"), str(fixture / "workspace.bin"),
        str(module_frame), str(module_geometry)
    ], text=True).strip()
    error_log = subprocess.check_output([
        str(error_runner), str(fixture / "map.bin"), str(fixture / "textures.bin"),
        str(fixture / "config.bin"), str(fixture / "workspace.bin")
    ], text=True).strip()
    rows_log = subprocess.check_output([
        str(rows_runner), str(fixture / "map.bin"), str(fixture / "textures.bin"),
        str(fixture / "config.bin"), str(fixture / "workspace.bin"),
        str(rows_frame), str(rows_geometry)
    ], text=True).strip()
    if module_frame.read_bytes() != oracle_frame.read_bytes():
        raise AssertionError("module frame differs from standalone renderer oracle")
    if module_geometry.read_bytes() != oracle_geometry.read_bytes():
        raise AssertionError("module DDA geometry differs from standalone renderer oracle")
    if rows_frame.read_bytes() != oracle_frame.read_bytes():
        raise AssertionError("direct-row frame differs from standalone renderer oracle")
    if rows_geometry.read_bytes() != oracle_geometry.read_bytes():
        raise AssertionError("direct-row DDA geometry differs from standalone renderer oracle")

    module_dir = BUILD / "module"
    module_dir.mkdir(exist_ok=True)
    run([
        sdk_python, sdk / "tools/build_module.py", ROOT / "wolf3d_scene.cpp",
        "--output", module_dir, "--name", "wolf3d_scene",
        "--capabilities", "17", "--abi-minor", "3",
        "--text-limit", "65536", "--data-limit", "16384",
        "--stack-limit", "2048", "--image-limit", "131072",
        "--build-id", "0x20261030"
    ], stdout=subprocess.DEVNULL)
    manifest = json.loads((module_dir / "wolf3d_scene.json").read_text())
    module = manifest["module"]
    if (module["capabilities"], module["abi_minor"]) != (17, 3):
        raise AssertionError("module ABI/capability receipt mismatch")
    if module["resident_text_bytes"] > 65536 or module["resident_data_bytes"] > 16384:
        raise AssertionError("module admission envelope exceeded")
    if module["sha256"] != "57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be":
        raise AssertionError("accepted copied package changed")

    rows_module_dir = BUILD / "rows-module"
    rows_module_dir.mkdir(exist_ok=True)
    run([
        sdk_python, sdk / "tools/build_module.py", ROOT / "wolf3d_scene_rows.cpp",
        "--output", rows_module_dir, "--name", "wolf3d_scene_rows",
        "--capabilities", "273", "--abi-minor", "6",
        "--text-limit", "65536", "--data-limit", "16384",
        "--stack-limit", "2048", "--image-limit", "131072",
        "--build-id", "0x20261030"
    ], stdout=subprocess.DEVNULL)
    rows_manifest = json.loads(
        (rows_module_dir / "wolf3d_scene_rows.json").read_text()
    )
    rows_module = rows_manifest["module"]
    if (rows_module["capabilities"], rows_module["abi_minor"]) != (273, 6):
        raise AssertionError("direct-row ABI/capability receipt mismatch")
    if (rows_module["resident_text_bytes"] > 65536 or
            rows_module["resident_data_bytes"] > 16384):
        raise AssertionError("direct-row module admission envelope exceeded")

    prefix = Path.home() / ".platformio/packages/toolchain-xtensa-esp32/bin/xtensa-esp32-elf-"
    compiler_prefix = str(prefix)
    undefined = subprocess.check_output(
        [compiler_prefix + "nm", "-u", str(module_dir / "wolf3d_scene.o")],
        text=True,
    ).strip().splitlines()
    if undefined:
        raise AssertionError(f"unresolved object symbols: {undefined}")
    relocation_lines = [
        line.strip() for line in (module_dir / "wolf3d_scene.readelf.txt").read_text().splitlines()
        if "R_XTENSA_" in line
    ]
    if not relocation_lines or any("R_XTENSA_RELATIVE" not in line for line in relocation_lines):
        raise AssertionError(f"unexpected relocation set: {relocation_lines}")

    rows_undefined = subprocess.check_output(
        [compiler_prefix + "nm", "-u", str(rows_module_dir / "wolf3d_scene_rows.o")],
        text=True,
    ).strip().splitlines()
    if rows_undefined:
        raise AssertionError(f"unresolved direct-row object symbols: {rows_undefined}")
    rows_relocations = [
        line.strip() for line in
        (rows_module_dir / "wolf3d_scene_rows.readelf.txt").read_text().splitlines()
        if "R_XTENSA_" in line
    ]
    if (not rows_relocations or
            any("R_XTENSA_RELATIVE" not in line for line in rows_relocations)):
        raise AssertionError(f"unexpected direct-row relocations: {rows_relocations}")

    stack = parse_stack(module_dir / "wolf3d_scene.su")
    rows_stack = parse_stack(rows_module_dir / "wolf3d_scene_rows.su")
    def stack_for(fragment: str) -> int:
        matches = [value for name, value in rows_stack.items() if fragment in name]
        if len(matches) != 1:
            raise AssertionError(f"cannot identify stack frame {fragment}: {matches}")
        return matches[0]
    rows_call_chains = {
        "vdplet_entry -> fill_rect (store_pixel inlined)": (
            stack_for("vdplet_entry") + stack_for("fill_rect")
        ),
        "vdplet_entry -> __divdi3 -> divide_u64": (
            stack_for("vdplet_entry") + stack_for("__divdi3") +
            stack_for("divide_u64")
        ),
        "vdplet_entry -> __udivdi3 -> divide_u64": (
            stack_for("vdplet_entry") + stack_for("__udivdi3") +
            stack_for("divide_u64")
        ),
    }
    evidence = {
        "scope": "host parity and actual Xtensa package admission; no emulator or physical claim",
        "wolf3dorig_head_before_prototype": "7e899cf",
        "oracle_repository": str(oracle_root),
        "oracle_head": git_head(oracle_root),
        "runtime_repository": str(sdk),
        "runtime_head": git_head(sdk),
        "runtime_sdk_snapshot": verified_sdk,
        "runtime_sdk_python": str(sdk_python),
        "oracle_log": oracle_log,
        "host_log": host_log,
        "host_error_log": error_log,
        "frame_bytes_compared": len(oracle_frame.read_bytes()),
        "geometry_bytes_compared": len(oracle_geometry.read_bytes()),
        "frame_sha256": sha(oracle_frame),
        "geometry_sha256": sha(oracle_geometry),
        "map_sha256": sha(fixture / "map.bin"),
        "textures_sha256": sha(fixture / "textures.bin"),
        "config_sha256": sha(fixture / "config.bin"),
        "source_sha256": sha(ROOT / "wolf3d_scene.cpp"),
        "contract_sha256": sha(ROOT / "wolf3d_scene_contract.h"),
        "tables_sha256": sha(ROOT / "wolf3d_tables.inc"),
        "package": module,
        "undefined_symbols": undefined,
        "relocations": relocation_lines,
        "source_stack_frames": stack,
        "largest_source_stack_frame": max(stack.values()),
        "stack_limit_note": (
            "Source .su frames are not a whole-task proof. Target qualification must "
            "record the INFO17 minimum-free watermark before and after the complete "
            "exercised render/service path."
        ),
        "passed": True,
    }
    (BUILD / "host-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    shutil.copyfile(module_dir / "wolf3d_scene.vdpl", BUILD / "wolf3d_scene.vdpl")
    rows_evidence = {
        "scope": (
            "ABI1.6 direct-colour-row source, host parity/error/lifecycle, and "
            "actual Xtensa package admission; no target emulator, hardware, "
            "human review, performance, or publication claim"
        ),
        "task": "G057-WLF-002 / TODO 8a",
        "runtime_sdk_snapshot": verified_sdk,
        "runtime_sdk_python": str(sdk_python),
        "oracle_repository": str(oracle_root),
        "oracle_head": git_head(oracle_root),
        "rows_host_log": rows_log,
        "copied_host_log": host_log,
        "copied_error_log": error_log,
        "frame_bytes_compared": len(oracle_frame.read_bytes()),
        "geometry_bytes_compared": len(oracle_geometry.read_bytes()),
        "frame_sha256": sha(rows_frame),
        "geometry_sha256": sha(rows_geometry),
        "oracle_frame_sha256": sha(oracle_frame),
        "oracle_geometry_sha256": sha(oracle_geometry),
        "source_sha256": sha(ROOT / "wolf3d_scene_rows.cpp"),
        "contract_sha256": sha(ROOT / "wolf3d_scene_rows_contract.h"),
        "copied_contract_sha256": sha(ROOT / "wolf3d_scene_contract.h"),
        "tables_sha256": sha(ROOT / "wolf3d_tables.inc"),
        "copied_source_sha256": sha(ROOT / "wolf3d_scene.cpp"),
        "copied_package_sha256": module["sha256"],
        "workspace": {
            "copied_bytes": 92160,
            "direct_target_bytes": 11552,
            "direct_host_bytes": 12512,
            "target_delta_bytes": 11552 - 92160,
            "full_colour_dummy_frame_bytes": 0,
        },
        "package": rows_module,
        "package_delta": {
            "package_bytes": rows_module["package_bytes"] - module["package_bytes"],
            "resident_text_bytes": (
                rows_module["resident_text_bytes"] - module["resident_text_bytes"]
            ),
            "resident_data_bytes": (
                rows_module["resident_data_bytes"] - module["resident_data_bytes"]
            ),
            "relative_relocations": (
                rows_module["relative_relocations"] - module["relative_relocations"]
            ),
        },
        "undefined_symbols": rows_undefined,
        "relocations": rows_relocations,
        "source_stack_frames": rows_stack,
        "largest_source_stack_frame": max(rows_stack.values()),
        "source_call_chain_sums": rows_call_chains,
        "largest_source_call_chain_sum": max(rows_call_chains.values()),
        "stack_limit_note": (
            "The call-chain sum covers module-owned non-inlined source frames "
            "visible in GCC .su output. Runtime callback frames and the VDP task "
            "still require later target INFO high-water evidence."
        ),
        "preservation_checks": {
            "independent_noncontiguous_rows": True,
            "native_sync_bits": True,
            "row_guards": True,
            "post_end_writes": True,
            "retained_row_pointers": True,
            "copied_pixel_calls": 0,
        },
        "performance_claim": None,
        "passed": True,
    }
    (BUILD / "rows-host-evidence.json").write_text(
        json.dumps(rows_evidence, indent=2) + "\n"
    )
    shutil.copyfile(rows_module_dir / "wolf3d_scene_rows.vdpl",
                    BUILD / "wolf3d_scene_rows.vdpl")
    print(json.dumps({
        "passed": True,
        "frame_sha256": evidence["frame_sha256"],
        "geometry_sha256": evidence["geometry_sha256"],
        "text_bytes": module["resident_text_bytes"],
        "data_bytes": module["resident_data_bytes"],
        "package_bytes": module["package_bytes"],
        "largest_source_stack_frame": evidence["largest_source_stack_frame"],
        "rows": {
            "frame_sha256": rows_evidence["frame_sha256"],
            "geometry_sha256": rows_evidence["geometry_sha256"],
            "workspace_target_bytes": 11552,
            "package_bytes": rows_module["package_bytes"],
            "text_bytes": rows_module["resident_text_bytes"],
            "data_bytes": rows_module["resident_data_bytes"],
            "largest_source_stack_frame": rows_evidence["largest_source_stack_frame"],
            "largest_source_call_chain_sum": rows_evidence["largest_source_call_chain_sum"],
        },
    }, indent=2))


if __name__ == "__main__":
    main()
