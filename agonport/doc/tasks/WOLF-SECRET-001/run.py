"""Exercise the marked pushwall through the real game on a checked-out Oryx."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from wall_trace import pushwall_records


def marker_pixels(picture):
    header, size, depth, rgb = picture.split(b"\n", 3)
    width, height = map(int, size.split())
    if header != b"P6" or depth != b"255" or len(rgb) != width * height * 3:
        raise ValueError("Incomplete framebuffer")
    # Match the yellow stencil in the center of the 3D viewport, excluding HUD.
    return sum(rgb[p:p+3] == b"\xff\xff\x55"
               for y in range(height // 4, height * 3 // 5)
               for x in range(width * 3 // 8, width * 5 // 8)
               for p in ((y * width + x) * 3,))


def viewport(picture):
    # Exclude the HUD, including BJ's idle portrait animation.
    _, size, _, rgb = picture.split(b"\n", 3)
    width, height = map(int, size.split())
    return rgb[:width * height * 3 * 5 // 6]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lease", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    out = root / "test"
    out.mkdir()
    events = out / "events.txt"
    events.touch()
    started = time.monotonic()
    result = {"passed": False, "captures": {}, "peak_c": 0}
    child = None

    def interrupted(signum, _frame):
        raise KeyboardInterrupt(signum)

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, interrupted)

    def guard():
        temperatures = []
        for name in Path("/sys/class/hwmon").glob("*/name"):
            if name.read_text().strip() == "k10temp":
                for label in name.parent.glob("temp*_label"):
                    if label.read_text().strip() == "Tctl":
                        temperatures.append(int(label.with_name(
                            label.name.replace("_label", "_input")).read_text()) / 1000)
        ram = int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines()
                       if line.startswith("MemAvailable:")))
        if (len(temperatures) != 1 or temperatures[0] >= 80 or ram < 524288
                or time.monotonic() - started > 240):
            raise RuntimeError("Oryx guard stopped the test")
        result["peak_c"] = max(temperatures[0], result["peak_c"])
        if child is not None and child.poll() is not None:
            raise RuntimeError(f"Emulator stopped early with status {child.returncode}")

    def wait(seconds):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            guard()
            time.sleep(min(0.10, max(0, until - time.monotonic())))

    def event(line):
        with events.open("a") as stream:
            stream.write(line + "\n")

    def key(code, seconds=0.14):
        event(f"key {code} 1")
        wait(seconds)
        event(f"key {code} 0")
        wait(0.18)

    def capture(name):
        destination = out / f"{name}.ppm"
        event(f"capture {destination}")
        until = time.monotonic() + 4
        while time.monotonic() < until:
            wait(0.08)
            if destination.exists():
                picture = destination.read_bytes()
                try:
                    result["captures"][name] = marker_pixels(picture)
                    return picture
                except ValueError:
                    continue
        raise RuntimeError(f"No complete capture for {name}")

    try:
        subprocess.run(["ssh", "-o", "BatchMode=yes", "raspberrypi",
                        "/Agon/mystuff/agon-dev-env/.venv/bin/python",
                        "/Agon/mystuff/agon-dev-env/cross-agent/vdplet-rollout/oryx_lease.py",
                        "assert-owner", "--owner", "wolf3dorig", "--lease", args.lease],
                       check=True, timeout=20)
        if Path("/sys/devices/system/cpu/cpufreq/boost").read_text().strip() != "0":
            raise RuntimeError("Oryx boost must be off")
        guard()
        env = {k: v for k, v in os.environ.items()
               if k not in ("LD_PRELOAD", "LD_LIBRARY_PATH", "BASH_ENV")
               and not k.startswith(("AGON_FLEXE_", "FLEXE_"))}
        env.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy",
                   LD_PRELOAD=str(root / "input.so"), W3V_REVIEW_EVENTS=str(events),
                   W3V_REVIEW_VDP=str(root / "flexe-vdp.so"), AGON_FLEXE_ENGINE="jit")
        with (out / "frontend.log").open("w") as log:
            child = subprocess.Popen(["./flexe-agon-emulator"], cwd=root, env=env,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            wait(9)
            capture("boot")
            for code in (21, 24, 17, 44, 55, 40):  # RUN .
                key(code)
            for attempt in range(27):
                wait(5)
                startup = capture(f"startup-{attempt:02d}")
                if len(set(startup.split(b"\n", 3)[3])) >= 4:
                    break
            else:
                raise RuntimeError("Stock startup did not show the title within 135 seconds")
            # Sign-on, rating, title, New Game, and Episode 1.
            for step in range(5):
                key(40)
                wait(2)
                capture(f"menu-{step}")
            # Choose Baby difficulty before entering the live room.
            for _ in range(3):
                key(82)
            key(40)
            for step in range(100):
                before = capture(f"ready-{step:03d}")
                if result["captures"][f"ready-{step:03d}"] > 150:
                    (out / "before.ppm").write_bytes(before)
                    break
                wait(0.20)
            else:
                raise RuntimeError("No visible fixture stencil during floor entry")
            key(82, 0.10)  # Up is Use
            moving = capture("moving")
            wire = root / "last-run/mos-to-vdp.bin"
            for _ in range(30):
                wait(0.5)
                records = list(pushwall_records(wire.read_bytes()))
                if records and records[-1]["status"] == 2:
                    break
            else:
                raise RuntimeError("No settled pushwall update")
            expected = {"origin": [10, 13], "current": [10, 11],
                        "direction": 2, "texture": 63, "completed_count": 1}
            if any(records[-1][key] != value for key, value in expected.items()):
                raise RuntimeError(f"Unexpected completed pushwall: {records[-1]}")
            wait(0.4)
            after = capture("after")
            if len({before, moving, after}) != 3 or result["captures"]["after"] < 10:
                raise RuntimeError("Expected the marked wall at three distinct positions")
            key(82)
            wait(1)
            capture("second-use")
            if viewport(after) != viewport((out / "second-use.ppm").read_bytes()):
                raise RuntimeError("Repeated Use changed the settled stencil")
            event("key 26 1")  # W moves forward
            wait(5)
            reached = capture("forward-held")
            wait(1)
            if viewport(reached) != viewport(capture("against-wall")):
                raise RuntimeError("View still changing at the end of the forward hold")
            event("key 26 0")
            if viewport(after) == viewport(reached):
                raise RuntimeError("Forward movement did not enter the opening")
            final_records = list(pushwall_records(wire.read_bytes()))
            if final_records != records:
                raise RuntimeError("Unexpected pushwall update after settling")
            (out / "pushwall.json").write_text(json.dumps(records, indent=2) + "\n")
            event("quit")
            if child.wait(timeout=10):
                raise RuntimeError("Emulator did not quit cleanly")
            stats = json.loads((root / "last-run/stats.json").read_text())
            if any(stats.get(k) for k in ("failed", "unhandled", "unregistered", "unmapped")):
                raise RuntimeError(f"Backend faults: {stats}")
            result["passed"] = True
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        result["seconds"] = time.monotonic() - started
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
