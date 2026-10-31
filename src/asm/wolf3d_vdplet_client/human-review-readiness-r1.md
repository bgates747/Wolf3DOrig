# Production-client readable review readiness and acceptance r1

The finite production-client automated gate passed once under Oryx generation
35 and was explicitly released. Its raw evidence was checksum-verified against
Oryx before the generated profile outputs were reset. The exact accepted
fixture was staged again, source-visible and stopped, for a readable Author
review.

The readable review passed on 2026-10-31 under a finite self-service Oryx lease.
The scene was visually accepted, Enter requested orderly unload, MOS returned
to a live prompt, and `dir` worked after exit. This acceptance does not
authorize another GUI run, hardware operation, default-backend change or
publication.

## Stopped profile

- profile: `/home/smith/Agon/mystuff/Wolf3dOrig/.emulator/vdplet-client`
- launcher: `flexe-agon-emulator`
- stopped-profile receipt SHA-256:
  `d6fa1da0466d4013f1f4efe835f8fb8293bc10890aae0591ca0f115301ae9463`
- fixture client: `1096669ce659a744b4cb95ac53dc3c9881fd6578d646645c9eb0a541f149f230`
- copied module: `57b635fc1807d9108e576cfff4c79c7f57ade48164fc5be97d75a3562e54b1be`
- reference scene: `42e227e80bba3cd7d65dc1bc1bee0b87e5d233e1cd8d3a1dd4f26805499bb4a2`
- launcher SHA-256:
  `885661c288468cae435c50bc8a4962c8ffbc8c6f219ea780896e74d19e117652`
- input helper SHA-256:
  `7d9f52a705776bf9db3ab84d16fcf66902a589e3a494ff42103fda27f60315e4`
- runtime manifest SHA-256:
  `4c2b32753bdf5d403dbd37e922c8c654a356402a429c5cfb50dd6c1e57b86d84`

Before the review, the profile contained no generated `client.dat` and both
generated run directories were empty. The stopped receipt records the accepted
generation-35 automated pass.

## Exact review procedure

The accepted review was launched from an Oryx desktop terminal with:

```bash
cd /home/smith/Agon/mystuff/Wolf3dOrig/.emulator/vdplet-client
./flexe-agon-emulator
```

Expected sequence:

1. The emulator automatically loads `/wolfclient/client.bin` and displays the
   copied-pixel fixture: light gray ceiling, dark gray floor, orange/yellow
   textured corridor walls and the centered yellow billboard with its red
   stripe. This must agree with `reference.png` in the guest directory.
2. Press **Enter once**. The client must unload its owned module and restore
   the MOS text screen at the `/wolfclient *` prompt; it must not hang.
3. Type `dir` and press Enter. MOS must produce the directory listing, including
   the newly written `client.dat`, and return to a live `/wolfclient *` prompt.
4. Close the emulator window normally. Do not start a second run.

Afterward the agent must preserve and verify `client.dat`, inspect Oryx for a
clean whole-host stop, explicitly release the Author lease, and report the
visual, keyboard, MOS-prompt and directory-listing observations. The expected
successful 16-byte result has SHA-256
`de684fe97a8737e448113faf2b5efbac7c45a93195471ecc6882087f60822ddb`.

## Acceptance result

All expected observations passed. The generated
`sdcard/wolfclient/client.dat` matched the expected SHA-256 above exactly. A
fresh whole-host inspection found Oryx empty after the Author closed the
emulator, and the lease was released normally with no queued successor.
