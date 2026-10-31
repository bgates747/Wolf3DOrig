#!/usr/bin/env python3
"""Finite real-wire driver for the bounded Wolf VDPlet target proof."""

from collections import deque
import ctypes
import hashlib
import json
import os
from pathlib import Path
import struct
import threading
import time


def word(value: int) -> bytes:
    return struct.pack("<H", value)


def command(key: int, operation: int) -> bytes:
    return bytes((23, 0, 160)) + word(key) + bytes((operation,))


def upload(key: int, data: bytes) -> bytes:
    if not data:
        raise ValueError("buffer upload must be nonempty")
    parts = [command(key, 2)]
    for offset in range(0, len(data), 4096):
        block = data[offset:offset + 4096]
        parts.extend((command(key, 0), word(len(block)), block))
    return b"".join(parts) + command(key, 14)


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Target:
    """One owned, headless VDP backend execution."""

    def __init__(self, engine: str, output: Path, backend: Path,
                 firmware: Path, timeout: float = 300):
        self.output = Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.backend = Path(backend).resolve()
        self.firmware = Path(firmware).resolve()
        self.elf = self.firmware.with_suffix(".elf")
        os.environ.update(
            AGON_FLEXE_FIRMWARE=str(self.firmware),
            AGON_FLEXE_ELF=str(self.elf),
            AGON_FLEXE_ENGINE=engine,
            AGON_FLEXE_ARTIFACTS=str(self.output),
            SDL_VIDEODRIVER="dummy",
            SDL_AUDIODRIVER="dummy",
        )
        self.lib = ctypes.CDLL(str(self.backend))
        for name in ("z80_uart0_is_cts", "z80_recv_from_vdp", "flexe_vdp_failed"):
            getattr(self.lib, name).restype = ctypes.c_bool
        self.lib.z80_recv_from_vdp.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
        self.lib.z80_send_to_vdp.argtypes = [ctypes.c_uint8]
        self.lib.flexe_vdp_cycles.restype = ctypes.c_uint64
        self.lib.flexe_vdp_frames.restype = ctypes.c_uint64
        self.lib.copyVgaFramebuffer.argtypes = [
            ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_float)
        ]
        self.frames = deque()
        self.pending = bytearray()
        self.raw = bytearray()
        self.observed = bytearray()
        self.sent = 0
        self.start = time.monotonic()
        self.timeout = timeout
        self.token = 0
        self.lib.vdp_setup()
        self.thread = threading.Thread(target=self.lib.vdp_loop)
        self.thread.start()
        self.send(bytes((23, 0, 128, 0x42)))
        self.wait(lambda: any(key == 128 and data == b"B" for key, data in self.frames))
        self.frames.clear()

    def poll(self) -> None:
        byte = ctypes.c_uint8()
        while self.lib.z80_recv_from_vdp(ctypes.byref(byte)):
            value = byte.value
            self.raw.append(value)
            if not self.pending and value < 128:
                continue
            self.pending.append(value)
            if len(self.pending) >= 2 and len(self.pending) == self.pending[1] + 2:
                self.frames.append((self.pending[0], bytes(self.pending[2:])))
                self.pending.clear()
        if self.lib.flexe_vdp_failed():
            raise RuntimeError("ESP32 execution stopped or faulted")
        if time.monotonic() - self.start > self.timeout:
            raise TimeoutError(
                f"target deadline; guest cycles={self.lib.flexe_vdp_cycles()}"
            )

    def wait(self, predicate) -> None:
        while True:
            self.poll()
            if predicate():
                return
            time.sleep(0.0002)

    def send(self, data: bytes) -> None:
        for value in data:
            self.wait(self.lib.z80_uart0_is_cts)
            self.lib.z80_send_to_vdp(value)
            self.sent += 1

    def transaction(self, operation: int, fields: bytes, kind: int,
                    expected: int | None = None) -> int:
        self.token = (self.token + 1) & 0xffff
        body = struct.pack("<BBHBB", 1, operation, self.token, 1, 0) + fields
        self.send(bytes((23, 0, 216)) + word(len(body)) + body)
        while True:
            self.wait(lambda: bool(self.frames))
            key, data = self.frames.popleft()
            if key != 129 or not data.startswith(b"VDPL"):
                continue
            if len(data) != 10 or data[4] != 1:
                raise AssertionError(data.hex())
            actual_kind, token, value = struct.unpack_from("<BHH", data, 5)
            if (actual_kind, token) != (kind, self.token):
                raise AssertionError((operation, actual_kind, token, value))
            if expected is not None and value != expected:
                raise AssertionError((operation, value, expected))
            self.observed += data
            return value

    def load(self, image: Path, key: int = 60023) -> int:
        data = Path(image).read_bytes()
        self.send(upload(key, data))
        return self.transaction(1, struct.pack("<HIH", key, len(data), 0), 2)

    def run(self, handle: int, entry: int, arguments: int, expected: int = 0) -> int:
        return self.transaction(
            2, struct.pack("<HHH", handle, entry, arguments),
            5 if expected else 3, expected,
        )

    def unload(self, handle: int) -> None:
        self.transaction(3, word(handle), 3, 0)

    def barrier(self) -> None:
        self.frames.clear()
        self.send(bytes((23, 0, 132, 0, 0, 0, 0)))
        self.wait(lambda: any(key == 132 for key, _ in self.frames))
        self.frames.clear()

    def capture(self) -> tuple[int, int, bytes]:
        self.barrier()
        first = self.lib.flexe_vdp_frames()
        deadline = time.monotonic() + 10

        def complete() -> bool:
            if time.monotonic() > deadline:
                raise TimeoutError(f"no fresh VGA frames: before={first}")
            return self.lib.flexe_vdp_frames() >= first + 3

        self.wait(complete)
        width = ctypes.c_uint32()
        height = ctypes.c_uint32()
        rate = ctypes.c_float()
        pixels = (ctypes.c_uint8 * (1024 * 768 * 3))()
        self.lib.copyVgaFramebuffer(
            ctypes.byref(width), ctypes.byref(height), pixels, ctypes.byref(rate)
        )
        count = width.value * height.value * 3
        return width.value, height.value, bytes(pixels[:count])

    def close(self) -> dict:
        self.lib.vdp_shutdown()
        self.thread.join(timeout=10)
        if self.thread.is_alive():
            raise RuntimeError("VDP worker did not stop")
        (self.output / "results.dat").write_bytes(self.observed)
        (self.output / "wire-rx.dat").write_bytes(self.raw)
        return json.loads((self.output / "stats.json").read_text())
