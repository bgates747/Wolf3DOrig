"""One Oryx backend-only correctness run for ordinary cropped bitmap plots."""

import json
from pathlib import Path

from qualification.target import Target, sha, upload, word

ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "weapon-frames.bin"
FIRMWARE = ROOT / "firmware/vdp.bin"
BACKEND = ROOT / "backend/flexe-vdp.so"
OUT = ROOT / "results"
FLIP = bytes((23, 0, 195))
PIXELS = 320 * 240


def prepared_image(source):
    width, height = 161, 160
    step = (64 << 16) // width
    prepared = bytes(source[(y * step >> 16) * 64 + (x * step >> 16)]
                     for y in range(height) for x in range(width))
    opaque = [(x, y) for y in range(height) for x in range(width)
              if prepared[y * width + x] & 0xC0]
    left = min(x for x, _ in opaque)
    top = min(y for _, y in opaque)
    right = max(x for x, _ in opaque) + 1
    bottom = max(y for _, y in opaque) + 1
    cropped = b"".join(prepared[y * width + left:y * width + right]
                       for y in range(top, bottom))
    return 80 + left, 20 + top, right - left, bottom - top, cropped


def rgb(pixel):
    return bytes(((pixel & 3) * 85, ((pixel >> 2) & 3) * 85, ((pixel >> 4) & 3) * 85))


def capture(target):
    width, height, pixels = target.capture()
    if (width, height, len(pixels)) != (320, 240, PIXELS * 3):
        raise AssertionError(f"Unexpected framebuffer dimensions {width}x{height}")
    return pixels


def main():
    frames = FRAMES.read_bytes()
    if len(frames) != 20 * 4096:
        raise ValueError("Expected all 20 weapon frames")
    bitmap = 0x5700  # Owned only by this fresh VDP worker.
    select = bytes((23, 27, 32)) + word(bitmap)
    clear = [bytes((17, 128 + color, 12)) for color in (4, 2)]
    target = Target.__new__(Target)
    result = dict(passed=False, controls=[], firmware=sha(FIRMWARE), frames=sha(FRAMES))
    try:
        target.__init__("jit", OUT, BACKEND, FIRMWARE, timeout=120)
        target.send(bytes((22, 136, 23, 1, 0, 23, 0, 192, 0, 26)))
        colors = []
        for fill in clear:
            target.send(fill + FLIP)
            visible = capture(target)
            colors.append(visible[:3])
            if visible != colors[-1] * PIXELS:
                raise AssertionError("Expected a uniform background")
        if colors[0] == colors[1]:
            raise AssertionError("The two background controls are indistinguishable")

        for i in range(20):
            x, y, w, h, pixels = prepared_image(frames[i * 4096:(i + 1) * 4096])
            # Explicitly wait through each swap before replacing its bitmap backing.
            define = select + bytes((23, 27, 33)) + word(w) + word(h) + b"\x01"
            plot = bytes((23, 27, 3)) + word(x) + word(y)
            target.send(upload(bitmap, pixels) + define + clear[i & 1] + plot)
            if capture(target) != visible:
                raise AssertionError(f"Plot escaped the back page for shape {416 + i}")
            expected = bytearray(colors[i & 1] * PIXELS)
            for index, pixel in enumerate(pixels):
                if pixel & 0xC0:
                    row, col = divmod(index, w)
                    at = ((y + row) * 320 + x + col) * 3
                    expected[at:at + 3] = rgb(pixel)
            target.send(FLIP)
            visible = capture(target)
            if visible != expected:
                different = next(j for j, (a, b) in enumerate(zip(visible, expected)) if a != b)
                row, col = divmod(different // 3, 320)
                raise AssertionError(f"Shape {416 + i} differs at ({col}, {row})")
            result["controls"].append({"shape": 416 + i, "hidden": True, "pixel_match": True})
        result["passed"] = True
    except BaseException as error:
        result["error"] = repr(error)
        raise
    finally:
        thread = getattr(target, "thread", None)
        if thread is not None:
            result["backend_stats"] = target.close()
        (OUT / "evidence.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
