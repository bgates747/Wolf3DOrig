"""Build isolated full-game weapon test payloads and the ordered bench packet."""

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRODUCTION = ROOT / "agonport/vdplet/production"
ASSEMBLY = ROOT / "src/asm/wolf3d/scripts/build.py"
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "agonport/vdplet")]
from wolf_firmware import (DEFAULT_PAYLOAD, PRODUCTION_MODULE_SHA, module_info,
                           release_files, sha, verify_payload)  # noqa: E402
from prepare import parse_container  # noqa: E402
from wire_check import prepared_image  # noqa: E402
from agnb.container import BufferRecord, make_buffer_record  # noqa: E402


def replace_once(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f"Source join changed in {path.name}: {old!r}")
    path.write_text(text.replace(old, new, 1))


def build_module(output, rectangles):
    source = output / "candidate-source"
    source.mkdir()
    for path in PRODUCTION.iterdir():
        if path.name.startswith(("wolf3d_", "original_")) and path.is_file():
            shutil.copyfile(path, source / path.name)
    shutil.copyfile(HERE / "prepared_weapon.inc", source / "prepared_weapon.inc")
    (source / "weapon_rectangles.inc").write_text("".join(
        "    {%d, %d, %d, %d},\n" % rect for rect in rectangles))
    renderer = source / "wolf3d_renderer.cpp"
    h = source / "wolf3d_renderer.h"
    wrapper = source / "wolf3d_module.cpp"
    replace_once(h, "const RenderTarget &target, RenderStats *stats = nullptr);",
                 "const RenderTarget &target, RenderStats *stats = nullptr,\n"
                 "                                 bool skip_weapon = false);")
    replace_once(renderer, "uint32_t required_workspace,\n                                    RenderStats *stats)",
                 "uint32_t required_workspace,\n                                    RenderStats *stats,\n"
                 "                                    bool skip_weapon = false)")
    replace_once(renderer, "    detail = draw_view_weapon(world, resources, frame, stats);\n"
                 "    if (detail != RenderDetail::ok) return detail;", "    if (!skip_weapon) {\n"
                 "        detail = draw_view_weapon(world, resources, frame, stats);\n"
                 "        if (detail != RenderDetail::ok) return detail;\n    }")
    replace_once(renderer, "const RenderTarget &target,\n                                 RenderStats *stats)",
                 "const RenderTarget &target,\n                                 RenderStats *stats, bool skip_weapon)")
    replace_once(renderer, "W3P_DIRECT_WORKSPACE_BYTES, stats);",
                 "W3P_DIRECT_WORKSPACE_BYTES, stats, skip_weapon);")
    replace_once(wrapper, "static ModuleState g_module;", 'static ModuleState g_module;\n\n#include "prepared_weapon.inc"')
    # Direct rows only. The copied-pixel compatibility path retains the current renderer.
    replace_once(wrapper, "    ServiceAssets service_assets = {host, VDPL_OK};",
                 "    const int prepared_index = direct_rows ? prepared_weapon_index(g_module.mirror) : -1;\n"
                 "    ServiceAssets service_assets = {host, VDPL_OK};")
    replace_once(wrapper, "                g_module.mirror, resources, target);",
                 "                g_module.mirror, resources, target, nullptr, prepared_index >= 0);")
    replace_once(wrapper, "    if (status == VDPL_OK) mark_mirror_presented(g_module.mirror);",
                 "    if (status == VDPL_OK && prepared_index >= 0)\n"
                 "        status = plot_prepared_weapon(host, prepared_index);\n"
                 "    if (status == VDPL_OK) mark_mirror_presented(g_module.mirror);")
    spec = importlib.util.spec_from_file_location("module_builder", PRODUCTION / "build.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    module_dir = output / "module"
    builder.run([builder.SDK_PYTHON, builder.SDK / "tools/build_module.py", wrapper,
                 "--output", module_dir, "--compiler", builder.TOOLCHAIN / "xtensa-esp32-elf-gcc",
                 "--name", "wolf_weapon", "--capabilities", "261", "--abi-minor", "6",
                 "--text-limit", "65536", "--data-limit", "16384", "--stack-limit", "2048",
                 "--image-limit", "131072", "--build-id", "0x20261119"])
    module = module_dir / "wolf_weapon.vdpl"
    info = module_info(module)
    assert (info["abi_minor"], info["capabilities"]) == (6, 261)
    raw = json.loads((module_dir / "wolf_weapon.json").read_text())
    assert raw["module"]["compiler_target"]["psram_cache_workaround"]
    stack = builder.parse_stack(module_dir / "wolf_weapon.su")
    def frame(fragment):
        return max(size for name, size in stack.items() if fragment in name)
    draw_stack = sum(frame(s) for s in ("vdplet_entry", "render_world_direct", "render_world_to_target",
                                        "draw_walls", "acquire_asset"))
    assert draw_stack <= 2048, draw_stack
    (output / "module-info.json").write_text(json.dumps({**info, "draw_stack": draw_stack}, indent=2) + "\n")
    return module


def patch_uncapped(path):
    replace_once(path, "@ordinary_render:\n    ld a,(w3d_world_dirty)\n    or a\n    jp z,mainloop\n",
                 "@ordinary_render:\n    ld a,1\n    ld (w3d_player_dirty),a\n")
    replace_once(path, "    call w3d_submit_dirty_world_render\n    jp mainloop\n\n; Gameplay Escape",
                 "    call w3d_submit_dirty_world_render\n    jp c,w3d_gameplay_fatal_shutdown\n"
                 "    jp mainloop\n\n; Gameplay Escape")


def patch_benchmark(path):
    shutil.copyfile(HERE / "weapon_bench.inc", path.parent / "weapon_bench.inc")
    replace_once(path, '    include "wolf3d_profile.inc"\n',
                 '    include "wolf3d_profile.inc"\n    include "weapon_bench.inc"\n')
    replace_once(path, "    W3D_PROFILE_CALL w3d_profile_finish\n",
                 "    W3D_PROFILE_CALL w3d_profile_finish\n    call w3d_weapon_bench_report\n")
    replace_once(path, "    call w3d_shell_reset_quick_slot\n    .if W3D_DIAGNOSTIC_HIGHSCORE_MODE",
                 "    call w3d_shell_reset_quick_slot\n    jp w3d_weapon_bench_demo\n"
                 "    .if W3D_DIAGNOSTIC_HIGHSCORE_MODE")


def build_client(output, module, benchmark):
    spec = importlib.util.spec_from_file_location("client_builder", ASSEMBLY)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    output.mkdir()
    builder.SOURCE = Path(shutil.copytree(builder.SOURCE, output / "game-source"))
    patch_uncapped(builder.SOURCE / "wolf3d.asm")
    if benchmark:
        patch_benchmark(builder.SOURCE / "wolf3d.asm")
    return builder.build(builder.resolve_assembler(None), "vdplet-direct", module,
                         profile=True, output_dir=output)


def payload(output, original, packed, input_root, receipt):
    output.mkdir()
    for name in original["files"]:
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name == "wolf3d.bin":
            source = ROOT / receipt["output"]
        elif name == "wolf3d.vdpl":
            source = ROOT / receipt["module"]["output"]
        elif name == "build-receipt.json":
            source = (ROOT / receipt["output"]).with_suffix(".json")
        else:
            source = input_root / name
        if name.endswith("/sprites.agnb"):
            data, records = parse_container(source)
            if any(0x5700 <= r.bufferId < 0x5714 for r in records):
                raise ValueError(f"Prepared bitmap ID collision in {source}")
            combined = data[:4] + struct.pack("<I", len(data) - 8 + len(packed)) + data[8:] + packed
            path.write_bytes(combined)
            _, check = parse_container(path)
            assert [r.bufferId for r in check[-20:]] == list(range(0x5700, 0x5714))
        else:
            shutil.copyfile(source, path)
    result = dict(original, module=module_info(output / "wolf3d.vdpl"),
                  files={name: {"bytes": (output / name).stat().st_size, "sha256": sha(output / name)}
                         for name in original["files"]})
    (output / "payload.json").write_text(json.dumps(result, indent=2) + "\n")
    verify_payload(output)


def make_bench_job(builds, output, namespace, preserve):
    def pinned(path):
        return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha(path)}

    # The timing builds enter the first stock demo directly, at hard difficulty.
    demo_inputs = ("wolf3d.vdpl", "shell.agnb", "sfx.agnb", "hud.agnb",
                   "level_00/state_hard.w3l", "level_00/tiles.agnb", "level_00/sprites.agnb")
    arms = []
    for arm in ("baseline", "cropped"):
        payload_root = builds / arm
        manifest = verify_payload(payload_root)
        if not set(demo_inputs).issubset(manifest["files"]):
            raise ValueError(f"Incomplete E1L1 demo inputs for {arm}")
        cwd = f"/test/{namespace}/{arm}"
        arms.append({"id": arm, "cwd": cwd, "agon": pinned(payload_root / "wolf3d.bin"),
                     "sd_program": cwd + "/wolf3d.bin", "address": "040000", "seconds": 240,
                     "success": "WOLFWEAPON PASS", "failure": "WOLFWEAPON FAIL",
                     "results": [cwd + "/WOLFPROF.BIN"],
                     "inputs": [{"sd_path": f"{cwd}/{name}", "source": pinned(payload_root / name)}
                                for name in demo_inputs]})
    job = {"schema": 3, "namespace": namespace, "fixtures": arms, "firmware": {},
           "preserve": preserve}
    with output.open("x") as stream:
        json.dump(job, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--original", type=Path, default=DEFAULT_PAYLOAD)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True)
    release_files()
    original = verify_payload(args.original)
    control = args.original / "wolf3d.vdpl"
    assert sha(control) == PRODUCTION_MODULE_SHA
    frames_file = output / "weapons.raw"
    subprocess.run([sys.executable, HERE / "prepare.py", args.original, frames_file], check=True)
    frames = frames_file.read_bytes()
    packed, rectangles = bytearray(), []
    for index in range(20):
        x, y, w, h, pixels = prepared_image(frames[index * 4096:(index + 1) * 4096])
        rectangles.append((x, y, w, h))
        file = output / f"weapon-{416 + index}.rgba2222"
        file.write_bytes(pixels)
        packed.extend(make_buffer_record(BufferRecord(file.stem, 0x5700 + index, w, h, file, w * h)))
    assert sum(w * h for _, _, w, h in rectangles) == 75010
    candidate = build_module(output, rectangles)
    for arm, module, benchmark in (("baseline", control, True), ("cropped", candidate, True),
                                  ("play", candidate, False)):
        receipt = build_client(output / (arm + "-build"), module, benchmark)
        payload(output / arm, original, packed, args.original, receipt)
    for name in original["files"]:
        if name not in ("wolf3d.bin", "wolf3d.vdpl", "build-receipt.json"):
            assert sha(output / "baseline" / name) == sha(output / "cropped" / name)


if __name__ == "__main__":
    main()
