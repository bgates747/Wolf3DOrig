"""Isolated Oryx preparation/one-case runner; assert FIFO ownership before run."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

BASE = Path.home() / "Agon/mystuff/Wolf3dOrig/.emulator/wolf-profile001-functional01"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare():
    old = Path.home() / "Agon/mystuff/Wolf3dOrig/.emulator/wolf-four01/fab-bespoke-01"
    runtime = {"vdp_wolf3d.so": "5c4e4b9bf6b58ade665b1d19f87697b54d08113a0962b3fe946bf899a1d49e2f",
               "fab-agon-emulator.bin": "aec5f8c266117d5bf864c6124d3c8986d042802ed5cbaaf8813e04a9fb8d0bea",
               "input.so": "7d9f52a705776bf9db3ab84d16fcf66902a589e3a494ff42103fda27f60315e4",
               "mos_platform.bin": "d564243283972690933a4554296ad6202ca4ef54572279533a942960846bebae",
               "mos_platform.map": "d69e60bbce61a7b4b3eef318ba395f11c4e1a5b585755755113992dc94edcb86",
               "fab-agon-emulator": "4d7a33e70fbed76038e0a416e00984cfc90a0e56852eb6775a9333a36ef0cdba"}
    for name, digest in runtime.items():
        assert sha(old / name) == digest, name
    cases = json.loads((BASE / "inputs/receipt.json").read_text())
    for case, receipt in cases.items():
        p = BASE / case
        p.mkdir(exist_ok=False)
        for name in (*runtime, ".mos-release", ".mos-release.sha256", ".bespoke-vdp-profile"):
            shutil.copyfile(old / name, p / name)
        (p / "fab-agon-emulator").chmod(0o755)
        (p / "fab-agon-emulator.bin").chmod(0o755)
        sd = p / "sdcard"
        game = sd / "wolf3d"
        game.mkdir(parents=True)
        if receipt["full_game"]:
            shutil.copytree(BASE / "inputs/assets", game, dirs_exist_ok=True)
        shutil.copyfile(BASE / "inputs" / case / "test.bin", game / "wolf3d.bin")
        assert sha(game / "wolf3d.bin") == receipt["sha256"]
        (sd / "autoexec.txt").write_bytes(b"SET KEYBOARD 1\r\ncd /wolf3d\r\nrunbin ./wolf3d.bin\r\n")
        files = [p / name for name in runtime] + [sd / "autoexec.txt"]
        files += [x for x in game.rglob("*") if x.is_file()]
        manifest = {str(x.relative_to(p)): sha(x) for x in files}
        (p / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (p / ".runtime.sha256").write_text("".join(d + "  " + n + "\n" for n, d in manifest.items()))
    print("Four isolated profiles prepared; no emulator launched.")


def guard():
    assert Path("/sys/devices/system/cpu/cpufreq/boost").read_text().strip() == "0"
    temps = []
    for name in Path("/sys/class/hwmon").glob("*/name"):
        if name.read_text().strip() == "k10temp":
            for label in name.parent.glob("temp*_label"):
                if label.read_text().strip() == "Tctl":
                    temps.append(int(label.with_name(label.name.replace("_label", "_input")).read_text()) / 1000)
    available = int(next(x.split()[1] for x in Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable:")))
    if len(temps) != 1 or temps[0] >= 80 or available < 524288:
        raise RuntimeError("thermal/sensor/RAM guard")
    return {"cpu_c": temps[0], "available_kib": available}


def run(case, lease):
    # Central Pi authority, exact original token, sequential before child I/O.
    subprocess.run(["ssh", "-o", "BatchMode=yes", "raspberrypi",
                    "/Agon/mystuff/agon-dev-env/.venv/bin/python",
                    "/Agon/mystuff/agon-dev-env/cross-agent/vdplet-rollout/oryx_lease.py",
                    "assert-owner", "--owner", "wolf3dorig", "--lease", lease],
                   check=True, stdout=subprocess.DEVNULL, timeout=30)
    p = BASE / case
    for name, digest in json.loads((p / "inputs.json").read_text()).items():
        assert sha(p / name) == digest, name
    expected = json.loads((BASE / "inputs/receipt.json").read_text())[case]
    out = p / "run"
    out.mkdir(exist_ok=False)
    events = out / "events.txt"
    events.write_text("")
    env = dict(os.environ)
    for key in ("BASH_ENV", "LD_LIBRARY_PATH", "FLEXE_UART_OBSERVER_OUTPUT", "FLEXE_TX_OBSERVER_OUTPUT", "FLEXE_TX_BATCH_OBSERVER_OUTPUT"):
        env.pop(key, None)
    env.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy",
               LD_PRELOAD=str(p / "input.so"), W3V_REVIEW_EVENTS=str(events),
               W3V_REVIEW_VDP=str(p / "vdp_wolf3d.so"))
    began = time.monotonic()
    process, observations = None, []
    result = {"case": case, "success": False, "native_synthetic": expected["native_synthetic"],
              "limits": "Actual eZ80 correctness only. Test-only 200ms cue hold; no physical performance claim."}
    with (out / "frontend.log").open("w") as log:
        try:
            observations.append(dict(seconds=0, **guard()))
            process = subprocess.Popen(["./fab-agon-emulator"], cwd=p, env=env,
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            result["pid"] = process.pid
            print(json.dumps({"case": case, "pid": process.pid}), flush=True)
            next_guard, next_capture, captures = 0, 0, 0
            done = p / "sdcard/wolf3d/DONE.BIN"
            while time.monotonic() - began < 300:
                if process.poll() is not None:
                    raise RuntimeError(f"emulator exited early: {process.returncode}")
                now = time.monotonic() - began
                if now >= next_guard:
                    observations.append(dict(seconds=now, **guard()))
                    next_guard = now + 1
                if now >= next_capture:
                    with events.open("a") as e:
                        e.write("capture " + str(out / f"frame-{captures:04d}.ppm") + "\n")
                    captures += 1
                    next_capture = now + 0.05
                if done.exists() and done.stat().st_size == 32:
                    raw = done.read_bytes()
                    if raw[:4] != b"WPT1":
                        raise RuntimeError("bad completion report magic")
                    status, owned = raw[4:6]
                    frames = int.from_bytes(raw[8:11], "little")
                    entry = int.from_bytes(raw[12:15], "little")
                    end = int.from_bytes(raw[16:19], "little")
                    assert status == expected["expected_status"], ("profile status", status)
                    assert owned == 0 and not raw[7] & 1, "timer still owned/enabled"
                    assert entry == end, ("stack mismatch", entry, end)
                    assert frames >= expected["minimum_frames"], ("missing frames", frames)
                    shutil.copyfile(done, out / "DONE.BIN")
                    path = p / "sdcard/wolf3d/WOLFPROF.BIN"
                    raw_profile = path.read_bytes()
                    shutil.copyfile(path, out / "WOLFPROF.BIN")
                    if case == "short-write":
                        assert len(raw_profile) == 31, "first partial header wasn't preserved"
                    else:
                        spec = importlib.util.spec_from_file_location("decoder", BASE / "inputs/decode_profile.py")
                        decoder = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(decoder)
                        report = decoder.decode(raw_profile)
                        assert report["completed_frame_records"] == frames
                        assert len(report["complete_blocks"]) >= 2
                        (out / "decoded.json").write_text(json.dumps(report, indent=2) + "\n")
                    result.update(success=True, profile_status=status, frames=frames,
                                  profile_bytes=len(raw_profile), profile_sha256=sha(path),
                                  stack=entry, captures_requested=captures)
                    break
                time.sleep(0.02)
            else:
                raise TimeoutError("original 300s correctness bound reached")
        except BaseException as exc:
            result["error"] = repr(exc)
        finally:
            if process and process.poll() is None:
                with events.open("a") as e:
                    e.write("capture " + str(out / "final.ppm") + "\nquit\n")
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=2)
            result.update(whole_seconds=time.monotonic() - began,
                          returncode=None if process is None else process.returncode)
            (out / "host-guards.json").write_text(json.dumps(observations, indent=2) + "\n")
            (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--case", choices=("writer", "short-write", "native-join", "full-game"))
    parser.add_argument("--lease")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        if not args.case or not args.lease:
            parser.error("run requires exact case and lease")
        raise SystemExit(run(args.case, args.lease))
