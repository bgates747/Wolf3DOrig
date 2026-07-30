# Agon port notes

Informal running log of asides about porting to the Agon platform --
questions the Author asked while getting up to speed, answers given, and
whatever got resolved or deferred. Not rigorously structured. Append new
entries at the bottom as they come up.

---

## 2026-07-30: What is VSWAP, and how would Agon parse it?

**Q: what does VSWAP mean / what's in it?**

VSWAP.WL1 (shareware) / VSWAP.WL6 (retail) is id Software's combined
graphics+sound container for Wolf3D. Three regions of chunks, in order:
1. Wall/door textures (flat tileable images for the raycaster)
2. Sprites (camera-facing billboards: enemies, decor, pickups, gun/hand)
3. Digitized sound effects (music is separate, in AUDIOT/AUDIOHED)

Chunk index alone tells you which region a chunk is in, via two header
boundary numbers: everything before `spritestart` is a wall/door texture,
`spritestart..soundstart` is sprite art, `soundstart..numchunks` is sound.

**Q: is it a containerized chunk format, like RIFF?**

Same basic theory (header + index/offset table + raw payload blob), but
unlike RIFF, VSWAP chunks are NOT self-describing -- no per-chunk type tag
or embedded size-and-type in the payload itself. A chunk is just raw
bytes; you only know what it *means* from its index position relative to
`spritestart`/`soundstart`, and dimensions (e.g. 64x64 for walls) are
hardcoded convention, not stored per-chunk. More fragile to parse
correctly than RIFF, but simpler in one way: no need to walk the file
chunk-by-chunk, since offsets/lengths are all listed up front.

**Q: is the metadata all at the beginning of the file?**

Yes. Confirmed against `src/toolchain/formats/vswap.py`'s `read_vswap()`.
Layout, in order, all contiguous at the start of the file:
1. Header (6 bytes): `numchunks` (u16), `spritestart` (u16), `soundstart` (u16)
2. Offset table: `numchunks` x u32 -- absolute file offset of each chunk
3. Length table: `numchunks` x u16 -- byte length of each chunk

Chunk payload bytes only start after that. (Real file pads the payload
start up to a 4096-byte boundary -- see repo memory / devlog for that
tangent, not an Agon-specific concern.)

Implication for the Agon port: no need for RIFF-style sequential
chunk-by-chunk scanning. Read the fixed-size metadata block once at load
time, build an in-memory index, then random-seek directly to any chunk's
offset on demand. Whatever file I/O primitive Agon uses for this needs
random-access seek/read, not just sequential streaming, since offsets are
absolute file positions.

**Q: is there a max size on the metadata itself?**

No explicit cap in the format; bounded only by `numchunks` being a u16
(max 65,535 chunks -> metadata = `6 + numchunks*6` bytes, worst case
~384 KB). Real shareware file has `numchunks=663` -> actual metadata is
only 3,984 bytes (padded to 4096 before chunk data starts). Trivial to
load entirely into RAM up front on any platform, Agon included.

**Resolution:** informational only, no code changes this round. Feeds
into future Agon-side VSWAP loader design once porting work actually
starts.
