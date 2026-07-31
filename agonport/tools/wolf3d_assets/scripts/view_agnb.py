#!/usr/bin/env python3
"""Stage E: interactively inspect image records in a Wolf3D .agnb container.

Forked 2026-07-31 from agon-utils' examples/agnb/images/container/scripts/
view_agnb.py (UI/RIFF-parsing shape only, adapted) per Author decision to
vendor canonical AGNB tooling rather than import across project boundaries.
Its own independent RIFF parser is kept (doesn't trust pack_agnb.py), but
the manifest lookup is repointed at this project's per-level tiles.jsonl/
sprites.jsonl (agnb/manifest.py's ImageManifestEntry schema: kind + assetId
-derived bufferId) instead of the upstream demo's single flat manifest.

Usage:
    scripts/view_agnb.py                          # level_00, tiles.agnb
    scripts/view_agnb.py --level level_03 --which sprites
    scripts/view_agnb.py path/to/some.agnb --manifest path/to/some.jsonl
"""

import argparse
import json
import struct
import sys
import tempfile
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk

import agonutils
from PIL import Image, ImageTk

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from agnb.manifest import ImageManifestEntry, load_manifest  # noqa: E402

GENERATED_DIR = PROJECT_DIR.parents[1] / "assets" / "generated" / "wolf3d"
LEVELS_DIR = GENERATED_DIR / "levels"
MIN_SCALE = 1
MAX_SCALE = 32


@dataclass(frozen=True)
class ImageRecord:
    index: int
    bufferId: int
    width: int
    height: int
    imageFormat: int
    dataOffset: int
    dataSize: int
    listOffset: int


@dataclass(frozen=True)
class AssetSet:
    name: str
    container: Path
    manifest: Path


@dataclass(frozen=True)
class ManifestView:
    name: str
    source: str
    kind: str
    assetId: int | str
    bufferId: int


def load_manifest_view(path: Path, kind: str) -> list[ManifestView]:
    if kind != "hud":
        return [
            ManifestView(e.name, e.source, e.kind, e.assetId, e.bufferId)
            for e in load_manifest(path)
        ]
    entries = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        entries.append(
            ManifestView(
                value["name"], value["source"], "hud",
                value["chunkId"] if value["chunkId"] is not None else "panel",
                value["bufferId"],
            )
        )
    return entries


def available_asset_sets(level: str) -> dict[str, AssetSet]:
    level_dir = LEVELS_DIR / level
    candidates = {
        "tiles": AssetSet("tiles", level_dir / "tiles.agnb", level_dir / "tiles.jsonl"),
        "sprites": AssetSet("sprites", level_dir / "sprites.agnb", level_dir / "sprites.jsonl"),
        "hud": AssetSet("hud", GENERATED_DIR / "hud" / "hud.agnb", GENERATED_DIR / "hud" / "hud_assets.jsonl"),
    }
    return {name: item for name, item in candidates.items() if item.container.is_file()}


def read_chunk(data: bytes, offset: int, boundary: int):
    if offset + 8 > boundary:
        raise ValueError(f"Truncated chunk header at file offset {offset}")

    chunk_id = data[offset : offset + 4]
    payload_size = struct.unpack_from("<I", data, offset + 4)[0]
    payload_start = offset + 8
    payload_end = payload_start + payload_size
    next_offset = payload_start + ((payload_size + 3) & ~3)
    if payload_end > boundary or next_offset > boundary:
        raise ValueError(f"Chunk {chunk_id!r} at {offset} crosses its boundary")
    if any(data[payload_end:next_offset]):
        raise ValueError(f"Chunk {chunk_id!r} at {offset} has nonzero padding")

    return chunk_id, payload_start, payload_end, next_offset


def parse_container(path: Path) -> tuple[bytes, list[ImageRecord]]:
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"AGNB":
        raise ValueError(f"Not a RIFF AGNB file: {path}")
    declared_size = struct.unpack_from("<I", data, 4)[0]
    if declared_size != len(data) - 8:
        raise ValueError(
            f"RIFF size mismatch: header says {declared_size}, file needs {len(data) - 8}"
        )

    records = []
    version_seen = False
    offset = 12
    while offset < len(data):
        chunk_offset = offset
        chunk_id, payload_start, payload_end, offset = read_chunk(
            data, offset, len(data)
        )

        if chunk_id == b"VERS":
            if version_seen or records:
                raise ValueError("VERS must occur once before all buffer records")
            if data[payload_start:payload_end] != b"\x00\x01":
                raise ValueError("Viewer supports only AGNB version 0.1")
            version_seen = True
            continue

        if chunk_id != b"LIST":
            continue
        if not version_seen:
            raise ValueError("LIST BUFR encountered before VERS")
        if payload_end - payload_start < 4:
            raise ValueError(f"Truncated LIST at file offset {chunk_offset}")
        if data[payload_start : payload_start + 4] != b"BUFR":
            continue

        nested = []
        nested_offset = payload_start + 4
        while nested_offset < payload_end:
            nested_chunk = read_chunk(data, nested_offset, payload_end)
            nested.append(nested_chunk)
            nested_offset = nested_chunk[3]
        if nested_offset != payload_end:
            raise ValueError(f"Invalid LIST boundary at file offset {chunk_offset}")
        if [item[0] for item in nested] != [b"BHDR", b"IMAG", b"DATA"]:
            raise ValueError(
                f"Unsupported BUFR layout at file offset {chunk_offset}: "
                f"{[item[0] for item in nested]!r}"
            )

        _id, start, end, _next = nested[0]
        if end - start != 2:
            raise ValueError(f"Invalid BHDR size at file offset {chunk_offset}")
        bufferId = struct.unpack_from("<H", data, start)[0]
        if bufferId == 0xFFFF:
            raise ValueError(f"Reserved bufferId at file offset {chunk_offset}")

        _id, start, end, _next = nested[1]
        if end - start != 5:
            raise ValueError(f"Invalid IMAG size at file offset {chunk_offset}")
        width, height, imageFormat = struct.unpack_from("<HHB", data, start)
        if imageFormat != 1:
            raise ValueError(f"Unsupported image format {imageFormat}")

        _id, data_start, data_end, _next = nested[2]
        dataSize = data_end - data_start
        if not width or not height or dataSize != width * height:
            raise ValueError(
                f"Invalid RGBA2222 dimensions or DATA size at {chunk_offset}"
            )

        records.append(
            ImageRecord(
                index=len(records),
                bufferId=bufferId,
                width=width,
                height=height,
                imageFormat=imageFormat,
                dataOffset=data_start,
                dataSize=dataSize,
                listOffset=chunk_offset,
            )
        )

    if not version_seen:
        raise ValueError("Missing VERS chunk")
    if not records:
        raise ValueError("Container contains no supported image records")
    if len({record.bufferId for record in records}) != len(records):
        raise ValueError("Container contains duplicate bufferIds")
    return data, records


class ContainerViewer(tk.Tk):
    def __init__(self, asset_sets: dict[str, AssetSet], initial_kind: str):
        super().__init__()
        self.asset_sets = asset_sets
        self.kind_var = tk.StringVar(value=initial_kind)
        self.container_path = Path()
        self.container_data = b""
        self.records = []
        self.manifestByBufferId = {}
        self.record_index = 0
        self.scale = 1
        self.current_payload = b""
        self.source_image = None
        self.display_image = None
        self.tk_image = None
        self.temp_dir = tempfile.TemporaryDirectory(prefix="agnb-viewer-")

        self.title("Wolf3D AGNB Viewer")
        self.geometry("1400x1000")
        self.minsize(900, 650)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.enlarge_fonts()

        self.metadata_var = tk.StringVar()
        self.scale_var = tk.StringVar()
        self.pixel_var = tk.StringVar(value="Move over the image to inspect a pixel")
        self.jump_var = tk.StringVar(value="1")

        self.build_ui()
        self.bind_keys()
        self.select_kind()

    def select_kind(self, _event=None):
        selected = self.asset_sets[self.kind_var.get()]
        self.container_path = selected.container
        self.container_data, self.records = parse_container(selected.container)
        entries = load_manifest_view(selected.manifest, selected.name) if selected.manifest.is_file() else []
        self.manifestByBufferId = {entry.bufferId: entry for entry in entries}
        self.title(f"Wolf3D AGNB Viewer — {selected.name}: {selected.container}")
        self.show_record(0)

    def enlarge_fonts(self):
        """Make the standard Tk widget fonts large and high-contrast."""
        font_names = (
            "TkDefaultFont",
            "TkTextFont",
            "TkMenuFont",
            "TkHeadingFont",
            "TkCaptionFont",
            "TkSmallCaptionFont",
            "TkIconFont",
            "TkFixedFont",
        )
        for name in font_names:
            try:
                font = tkfont.nametofont(name)
            except tk.TclError:
                continue
            current_size = int(font.cget("size"))
            enlarged_size = current_size * 2
            font.configure(size=enlarged_size, weight="bold")

    def build_ui(self):
        toolbar = ttk.Frame(self, padding=12)
        toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Label(toolbar, text="Kind:").pack(side="left")
        kind_box = ttk.Combobox(
            toolbar,
            textvariable=self.kind_var,
            values=tuple(self.asset_sets),
            state="readonly",
            width=10,
        )
        kind_box.pack(side="left", padx=(4, 12))
        kind_box.bind("<<ComboboxSelected>>", self.select_kind)
        ttk.Button(toolbar, text="|<", command=lambda: self.show_record(0)).pack(
            side="left"
        )
        ttk.Button(toolbar, text="<", command=lambda: self.step_record(-1)).pack(
            side="left"
        )
        ttk.Button(toolbar, text=">", command=lambda: self.step_record(1)).pack(
            side="left"
        )
        ttk.Button(
            toolbar,
            text=">|",
            command=lambda: self.show_record(len(self.records) - 1),
        ).pack(side="left")

        ttk.Label(toolbar, text="  Record:").pack(side="left")
        jump_entry = ttk.Entry(toolbar, width=7, textvariable=self.jump_var)
        jump_entry.pack(side="left")
        jump_entry.bind("<Return>", self.jump_to_record)
        ttk.Button(toolbar, text="Go", command=self.jump_to_record).pack(side="left")

        ttk.Separator(toolbar, orient="vertical").pack(
            side="left", fill="y", padx=10
        )
        ttk.Button(toolbar, text="−", command=lambda: self.change_scale(-1)).pack(
            side="left"
        )
        ttk.Label(toolbar, textvariable=self.scale_var, width=8, anchor="center").pack(
            side="left"
        )
        ttk.Button(toolbar, text="+", command=lambda: self.change_scale(1)).pack(
            side="left"
        )
        ttk.Button(toolbar, text="1:1", command=lambda: self.set_scale(1)).pack(
            side="left", padx=(6, 0)
        )

        ttk.Label(
            self,
            textvariable=self.metadata_var,
            padding=(16, 6),
            justify="left",
            font="TkFixedFont",
        ).grid(row=1, column=0, sticky="ew")

        image_frame = ttk.Frame(self)
        image_frame.grid(row=2, column=0, sticky="nsew")
        image_frame.rowconfigure(0, weight=1)
        image_frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            image_frame, background="#303030", highlightthickness=0
        )
        x_scroll = ttk.Scrollbar(
            image_frame, orient="horizontal", command=self.canvas.xview
        )
        y_scroll = ttk.Scrollbar(
            image_frame, orient="vertical", command=self.canvas.yview
        )
        self.canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.canvas.bind("<Motion>", self.inspect_pixel)
        self.canvas.bind("<Leave>", lambda _event: self.pixel_var.set(""))

        ttk.Label(
            self,
            textvariable=self.pixel_var,
            padding=12,
            anchor="w",
            font="TkFixedFont",
        ).grid(row=3, column=0, sticky="ew")

        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

    def bind_keys(self):
        self.bind("<Left>", lambda _event: self.step_record(-1))
        self.bind("<Right>", lambda _event: self.step_record(1))
        self.bind("<Home>", lambda _event: self.show_record(0))
        self.bind("<End>", lambda _event: self.show_record(len(self.records) - 1))
        for key in ("<plus>", "<equal>", "<KP_Add>"):
            self.bind(key, lambda _event: self.change_scale(1))
        for key in ("<minus>", "<KP_Subtract>"):
            self.bind(key, lambda _event: self.change_scale(-1))
        self.bind("<Escape>", lambda _event: self.close())
        self.bind("q", lambda _event: self.close())

    def decode_current_record(self, record: ImageRecord) -> Image.Image:
        payload = self.container_data[
            record.dataOffset : record.dataOffset + record.dataSize
        ]
        self.current_payload = payload

        temp_root = Path(self.temp_dir.name)
        rgba_file = temp_root / "record.rgba2"
        png_file = temp_root / "record.png"
        rgba_file.write_bytes(payload)
        agonutils.rgba2_to_img(
            str(rgba_file), str(png_file), record.width, record.height
        )
        with Image.open(png_file) as image:
            return image.convert("RGBA").copy()

    def show_record(self, index: int):
        self.record_index = max(0, min(index, len(self.records) - 1))
        record = self.records[self.record_index]
        manifest_entry = self.manifestByBufferId.get(record.bufferId)
        if manifest_entry:
            source_name = f"{manifest_entry.name} ({manifest_entry.source})"
            kind_info = f"kind={manifest_entry.kind} assetId={manifest_entry.assetId}"
        else:
            source_name = "<not in manifest>"
            kind_info = ""
        self.source_image = self.decode_current_record(record)
        self.jump_var.set(str(self.record_index + 1))
        self.metadata_var.set(
            f"Record: {self.record_index + 1}/{len(self.records)}    "
            f"bufferId: {record.bufferId} (0x{record.bufferId:04X})    {kind_info}\n"
            f"Source: {source_name}\n"
            f"Image: {record.width}×{record.height}    Format: {record.imageFormat} "
            f"(RGBA2222)    DATA: {record.dataSize} bytes\n"
            f"LIST offset: 0x{record.listOffset:08X}    "
            f"DATA offset: 0x{record.dataOffset:08X}"
        )
        self.render_image()

    def render_image(self):
        width = self.source_image.width * self.scale
        height = self.source_image.height * self.scale
        if self.scale == 1:
            self.display_image = self.source_image
        else:
            self.display_image = self.source_image.resize(
                (width, height), Image.Resampling.NEAREST
            )
        self.tk_image = ImageTk.PhotoImage(self.display_image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.canvas.configure(scrollregion=(0, 0, width, height))
        self.scale_var.set(f"{self.scale}×")
        self.pixel_var.set("Move over the image to inspect a pixel")

    def step_record(self, amount: int):
        self.show_record((self.record_index + amount) % len(self.records))

    def jump_to_record(self, _event=None):
        try:
            requested = int(self.jump_var.get())
        except ValueError:
            self.bell()
            return
        if not 1 <= requested <= len(self.records):
            self.bell()
            return
        self.show_record(requested - 1)

    def set_scale(self, scale: int):
        scale = max(MIN_SCALE, min(scale, MAX_SCALE))
        if scale != self.scale:
            self.scale = scale
            self.render_image()

    def change_scale(self, amount: int):
        self.set_scale(self.scale + amount)

    def inspect_pixel(self, event):
        record = self.records[self.record_index]
        x = int(self.canvas.canvasx(event.x) // self.scale)
        y = int(self.canvas.canvasy(event.y) // self.scale)
        if not 0 <= x < record.width or not 0 <= y < record.height:
            self.pixel_var.set("")
            return

        packed = self.current_payload[y * record.width + x]
        red = (packed & 0x03) * 85
        green = ((packed >> 2) & 0x03) * 85
        blue = ((packed >> 4) & 0x03) * 85
        alpha = ((packed >> 6) & 0x03) * 85
        self.pixel_var.set(
            f"x={x} y={y}    RGBA2222=0x{packed:02X}    "
            f"RGBA8888=({red}, {green}, {blue}, {alpha})"
        )

    def close(self):
        self.temp_dir.cleanup()
        self.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "container",
        nargs="?",
        type=Path,
        help="AGNB file to inspect (default: derived from --level/--which)",
    )
    parser.add_argument(
        "--level",
        default="level_00",
        help=f"Level directory name under {LEVELS_DIR} (default: level_00)",
    )
    parser.add_argument(
        "--which",
        choices=("tiles", "sprites", "hud"),
        default="tiles",
        help="Which per-level container to open when --container isn't given",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Manifest .jsonl for the container (default: <level>/<which>.jsonl)",
    )
    args = parser.parse_args()

    asset_sets = available_asset_sets(args.level)
    if args.container:
        asset_sets = {
            "custom": AssetSet(
                "custom", args.container,
                args.manifest or args.container.with_suffix(".jsonl"),
            )
        }
        initial_kind = "custom"
    else:
        initial_kind = args.which
    if initial_kind not in asset_sets:
        available = sorted(asset_sets)
        raise SystemExit(f"No generated {initial_kind!r} assets; available kinds: {available}")

    viewer = ContainerViewer(asset_sets, initial_kind)
    viewer.mainloop()


if __name__ == "__main__":
    main()
