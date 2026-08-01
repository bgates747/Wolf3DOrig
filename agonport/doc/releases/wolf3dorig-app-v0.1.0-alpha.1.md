# Wolf3DOrig App 0.1.0 Alpha 1

The first versioned Wolf3DOrig application release for Agon. This is an
ordinary GitHub Release, not a GitHub prerelease. The application identifies
itself at runtime as `Wolf3DOrig App 0.1.0 Alpha 1`.

Wolf3DOrig is an experimental, playable, noncommercial port of the original
*Wolfenstein 3D* shareware experience. The eZ80 owns simulation, input,
collision, doors, actors, combat, pickups, death/respawn, and audio events;
the custom ESP32 VDP extension owns raycasting, sprites, HUD composition,
view-weapon drawing, double-buffered presentation, fizzle, and sound output.

## Package contents

`Wolf3DOrig-app-0.1.0-alpha.1.zip` contains the combined custom VDP firmware
at its root and one SD-ready application directory:

```text
firmware.bin
wolf3dorig/
  wolf3d.bin
  tiles.agnb
  sprites.agnb
  hud.agnb
  sfx.agnb
```

It also contains checksums, a machine-readable provenance manifest, the full
project notice, and `autoexec.wolf3dorig.txt` as an example. The example never
overwrites a user's `autoexec.txt`.

## Installation

This application requires the packaged Wolf3DOrig-aware PingoWolf custom VDP.
Copy `firmware.bin` to the SD-card root and flash it from MOS:

```text
FLASH vdp firmware.bin
```

Copy the packaged `wolf3dorig` directory to the SD-card root. Load manually
from MOS with:

```text
cd /wolf3dorig
load wolf3d.bin
run
```

The identical firmware is independently published as
[PingoWolf 0.1.0 Alpha 1](https://github.com/bgates747/agon-vdp/releases/tag/pingowolf-v0.1.0-alpha.1).

## Qualification and provenance

The release tag points to application commit
`3695b7dbfbecb63a635fee332fa4d9a937b9263b`, the hardware-accepted audio
milestone. The packaged application binary and firmware are the immutable
artifacts accepted in both the bespoke emulator and physical-hardware
combined tests.

The newer collision-tuning work on `master` is deliberately excluded after a
release rerun found two direct-eZ80 patrol/door-obstruction mismatches. That
work remains available for correction and a later release rather than being
silently shipped here.

## Rights, permitted purpose, and warranty

This is an unofficial noncommercial educational and historical-engineering
project. It is not an id Software, Bethesda, ZeniMax, or Agon Platform
product. The Author claims no ownership of Wolfenstein 3D names, trademarks,
characters, maps, textures, sprites, sounds, music, source, or other
third-party material. Rights remain with their respective owners.

The complete project notice is included in the archive as `NOTICE.md`. Users
are responsible for determining whether possession, distribution,
modification, demonstration, or use is permitted in their jurisdiction. The
software and data are supplied AS IS, without warranty, and entirely at the
user's risk.
