"""Compare candidate and accepted full-frame output on the pinned VDP backend."""

import hashlib
import json
from pathlib import Path
import struct

from qualification.target import Target, sha, upload, word

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixture"
OUT = ROOT / "results"
FLIP = bytes((23, 0, 195))


def batch_for(shape, shift):
    batch = bytearray((FIXTURE / "update-full.bin").read_bytes())
    found = set()
    at = 16
    while at < len(batch):
        kind, length = batch[at:at + 2]
        if kind == 7 and length == 12:
            batch[at + 13] = shift
            found.add(kind)
        if kind == 8 and length == 2:
            struct.pack_into("<h", batch, at + 2, shape)
            found.add(kind)
        at += length + 2
    assert at == len(batch) and found == {7, 8}
    return batch


def send_prepared(target, shape):
    index = shape - 416
    rectangles = json.loads((ROOT / "rectangles.json").read_text())
    _, _, width, height = rectangles[index]
    key = 0x5700 + index
    image = (ROOT / f"weapon-{shape}.rgba2222").read_bytes()
    assert len(image) == width * height
    create = bytes((23, 27, 32)) + word(key) + bytes((23, 27, 33)) + word(width) + word(height) + b"\x01"
    target.send(upload(key, image) + create)


def main():
    target = Target.__new__(Target)
    firmware = ROOT / "firmware/vdp.bin"
    result = {"passed": False, "firmware": sha(firmware), "matched": []}
    try:
        target.__init__("jit", OUT, ROOT / "backend/flexe-vdp.so", firmware, timeout=120)
        target.send(bytes((22, 136, 23, 1, 0, 23, 0, 192, 0, 26, 12)))
        for key, file in ((0x7100, "workspace.bin"), (0x7102, "argument.bin"), (2, "tilemap.bin")):
            target.send(upload(key, (FIXTURE / file).read_bytes()))
        for line in (FIXTURE / "assets.txt").read_text().splitlines():
            key, length, file = line.split()
            asset = (FIXTURE / file).read_bytes()
            assert len(asset) == int(length)
            target.send(upload(int(key, 0), asset))
        for shape in (421, 433):
            target.send(upload(0x2000 + shape, (ROOT / f"original-{shape}.rgba2222").read_bytes()))
            send_prepared(target, shape)
        matched = ((421, 0), (433, 0), (421, 3), (433, 131), (-1, 0))
        for shape, shift in matched:
            images = []
            for module in ("baseline", "cropped"):
                handle = target.load(ROOT / (module + ".vdpl"))
                target.run(handle, 0, 0x7102)
                target.send(upload(0x7101, batch_for(shape, shift)))
                target.run(handle, 1, 0x7102)
                target.send(FLIP)
                width, height, captured = target.capture()
                assert (width, height, len(captured)) == (320, 240, 320 * 240 * 3)
                images.append(captured)
                target.unload(handle)
            if images[0] != images[1]:
                pixel = next(i // 3 for i, pair in enumerate(zip(*images)) if pair[0] != pair[1])
                raise AssertionError(f"Shape {shape}, shift {shift}, mismatch at pixel {pixel}")
            result["matched"].append({"shape": shape, "shift": shift,
                                      "hash": hashlib.sha256(images[0]).hexdigest()})
        # Show that the distinct opaque weapon actually changed the composited output.
        assert len({m["hash"] for m in result["matched"]}) == len(matched)
        result["passed"] = True
    except BaseException as error:
        result["error"] = repr(error)
        raise
    finally:
        if hasattr(target, "thread"):
            result["backend_stats"] = target.close()
        (OUT / "evidence.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
