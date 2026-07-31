# Agon architecture technical précis

Status: DRAFT

This is a first-pass architectural orientation for the Wolf3D Agon port, not
a complete platform specification. The authoritative source is the local
official documentation checkout at `/home/smith/Agon/agon-docs/docs`.

## Machine model

Agon is effectively two computers connected by a high-speed UART:

1. An eZ80F92 is the application CPU. It runs MOS, accesses the SD card, and
   has 512 KB of attached RAM.
2. An ESP32-Pico-D4 is the VDP. It owns VGA video, audio, PS/2 keyboard and
   mouse handling, and has 8 MB of attached PSRAM for framebuffers, bitmaps,
   sound samples, fonts, buffers, and other VDP-side resources.

The processors have no shared memory. The eZ80 cannot write a framebuffer and
the VDP cannot read application RAM. The eZ80 sends a byte stream of text,
VDU commands, and asset data to the VDP; the VDP sends input and query results
back through its serial protocol. Current firmware uses 1,152,000 baud
(384,000 before MOS/VDP 1.03).

This split is the central architectural fact for the port. Rendering cannot be
designed like a conventional software framebuffer unless custom VDP firmware
explicitly provides such an abstraction. Work must be divided deliberately
between eZ80 game logic and VDP-resident rendering/data.

## eZ80 and MOS

The eZ80 is Z80-compatible but also supports 24-bit ADL mode and a 16 MB
address space. Agon supplies 512 KB of eZ80 RAM. MOS supports both classic Z80
and ADL programs; ADL is the natural model for a substantial game because it
can address the available memory directly.

The relevant default memory map is:

- `0x000000-0x01FFFF`: MOS flash ROM.
- `0x040000-0x0AFFFF`: normal user RAM.
- `0x0B0000-0x0B7FFF`: moslet/future-module area.
- `0x0B8000-0x0BBFFF`: reserved for MOS.
- `0x0BC000-0x0BFFFF`: MOS heap and stack.
- `0xB7E000-0xB7FFFF`: 8 KB eZ80 internal fast RAM.

Regular executables normally load at `0x040000`; moslets load at `0x0B0000`
and should fit in 32 KB. Executables conventionally use `.bin` and carry a
MOS header at file offset `0x40`, including whether code runs in Z80 or ADL
mode. MOS 3 introduces an advanced, backward-compatible header for flags such
as module safety and an optional load/execution address.

MOS provides the command line, FAT32 SD-card filesystem, program loading, boot
scripts, and application APIs. Assembly programs enter MOS mainly through
`RST.LIS` handlers:

- `RST 08h`: MOS API/command call.
- `RST 10h`: send one byte to the VDP.
- `RST 18h`: send a byte stream to the VDP.
- `RST 38h`: crash report on recent MOS versions.

MOS file-handle APIs are preferred over direct FatFS calls for ordinary
application I/O. The keyboard can be read as a blocking character, recent key
state, or a 16-byte virtual-key bitmap; the bitmap is the relevant model for
simultaneous movement/action controls.

## VDP programming model

The VDP is a smart terminal and graphics/audio coprocessor, not a passive
video chip. Its input is a variable-length command stream derived from BBC
Micro VDU conventions. Printable bytes draw text; control bytes select modes,
colours, plotting operations, bitmaps, sprites, audio, buffered commands, and
Agon-specific system functions.

A command may span multiple eZ80 writes. Commands must not be interleaved with
unrelated output while incomplete. Large transfers should therefore use the
Buffered Commands API rather than embedding an entire asset in one long VDU
command.

VDP buffers are identified by 16-bit IDs (65534 generally usable). They can
hold data blocks, bitmaps, sound samples, fonts, or executable VDU command
sequences. Important capabilities include:

- Uploading an asset in smaller blocks, then consolidating it.
- Creating a bitmap directly from a selected buffer.
- Storing command sequences on the VDP and invoking them later with a short
  call from the eZ80.
- Adjusting, reversing, splitting, sharing, and conditionally executing buffer
  contents on the VDP side.
- Querying VDP memory usage and graphics/input state through VDP variables.

Buffers are volatile across VDP reset and may have been used by earlier
programs, so an application must own a documented ID range and clear or
initialize it explicitly.

For Wolf3D, preloading textures/sprites and reusable draw-command sequences
into VDP buffers is likely more appropriate than repeatedly streaming bitmap
pixels each frame. The exact eZ80/VDP renderer boundary remains a design and
measurement question.

## Video, colour, and coordinates

The VDP supports several VGA modes. The most immediately relevant stock mode
is mode 8: 320x240, 64 colours, 60 Hz. Mode 12 is 320x200, 64 colours, 70 Hz.
Adding 128 selects a double-buffered counterpart where one is supported; a
buffer-swap command synchronizes at VSYNC.

Agon's physical colour is RGB222: two bits each for red, green, and blue, for
64 possible colours. Screen modes may expose 2, 4, 16, or 64 logical colours,
with palette entries mapping logical colours to physical RGB222 values.

The default graphics coordinate system emulates BBC Micro conventions: a
1280x1024 logical space with the origin at bottom left. It can be disabled in
favor of native pixel coordinates with the origin at top left, which is the
more natural model for a pixel-addressed Wolf3D viewport.

The VDP owns its framebuffer memory. Mode allocation can fail if VDP memory is
already consumed; software should choose a supported baseline mode and manage
VDP resources deliberately.

## Bitmap and sprite assets

Bitmap data normally lives in VDP buffers. Supported general formats include:

- RGBA8888: four bytes per pixel, expensive for transfer and storage.
- RGBA2222: one byte per pixel, aligned with the hardware's colour depth.
- Mono/mask: one bit per pixel using the selected foreground colour.

For RGBA bitmap formats, any non-zero alpha means fully visible; stock VDP does
not alpha-blend. Mono/mask off-pixels are transparent. This matters when
converting Wolf3D sprites: palette conversion and transparency encoding are
separate decisions, and RGBA2222 is the likely compact stock-VDP source
format.

The sprite API builds sprite frames from bitmaps. Traditional Agon software
sprites are automatically redrawn bitmaps and can flicker or impose substantial
copying costs, especially in single-buffered modes. Newer experimental
hardware sprites avoid framebuffer redraws but have scanline, size, mode, and
format limits; emulator capacity is not representative of hardware. A
Wolf3D renderer should not assume the stock sprite API is automatically the
right mechanism for world billboards.

## Input, audio, and peripherals

The VDP receives PS/2 keyboard and mouse input and reports it to MOS/eZ80.
Console8 includes a PS/2 mouse port and two Atari-compatible joystick ports;
Agon models are software-compatible but their physical GPIO layouts differ.
Programs targeting keyboard gameplay can read MOS's virtual keyboard bitmap
for concurrent keys.

The VDP also owns audio output and stores uploaded sound samples in buffers.
This suggests digitized Wolf3D effects belong in VDP memory, while playback is
triggered by compact commands from the eZ80. Audio format and capacity need a
separate focused pass.

## Emulator and firmware relationship

Fab Agon Emulator emulates the eZ80/MOS side but runs the VDP as a host-native
shared library. It does not execute ESP32 `firmware.bin`.

A custom VDP therefore has two related but distinct build products:

1. A native `.so` linked against Fab's userspace compatibility layer for
   desktop testing.
2. An ESP32 PlatformIO `firmware.bin` for physical Agon hardware.

The two should share command and rendering source where practical, but a
successful native-module test is not proof of ESP32 timing or behavior.
Physical hardware remains authoritative for UART flow, frame timing, VDP
memory pressure, and performance.

## Initial implications for Wolf3D

1. Use an ADL eZ80 executable unless later evidence strongly favors a different
   arrangement.
2. Treat eZ80 RAM, VDP PSRAM, SD storage, and UART bandwidth as separate
   budgets.
3. Prefer loading converted wall/sprite assets once into VDP buffers.
4. Investigate 320x200 mode 12 and 320x240 mode 8, including their available
   double-buffered variants and hardware behavior.
5. Convert the Wolf3D palette and sprite transparency deliberately to RGB222/
   RGBA2222; do not assume PNG conversion alone determines the runtime format.
6. Design input around the keyboard bitmap rather than blocking character
   reads.
7. Prototype and measure the renderer split on both Fab and hardware before
   committing to stock bitmap commands, buffered command procedures, or a
   custom VDP command/renderer.

## Official pages consulted

- `index.md`
- `Theory-of-operation.md`
- `Programming.md`
- `MOS.md`
- `mos/API.md`
- `mos/Executables.md`
- `mos/Keyboard.md`
- `VDP.md`
- `vdp/Screen-Modes.md`
- `vdp/Bitmaps-API.md`
- `vdp/Buffered-Commands-API.md`
- `vdp/VDP-Variables.md`
- `GPIO.md`
