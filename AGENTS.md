# Agent instructions

## Firmware defaults

Follow [FIRMWARE.md](FIRMWARE.md) for all test/deployment preparation. Smith pins
VDPlet v0.1.2-alpha selection `0.1.2-alpha-async-r1` (dc43ecb8, replacing
the original b004 image at the same tag) on Alexe, Olimex and Console8; Eirene MOS
3.1.0_uart0_rc_3 on Alexe/Console8, and scheduler-maintained latest approved
EMOS on Olimex. Verify the release assets/checksums. Older profile/kit examples
do not override these pins. Existing permissions remain in force.

## Network access authority

For access between development machines, read the [canonical network instructions](https://github.com/bgates747/agon-dev-env/blob/feature/standardized-deployment/codex/environment.md#ssh-between-development-machines) in `~/Agon/mystuff/agon-dev-env/codex/environment.md` and its machine-local `.local/ssh-001/CONNECTIONS.md` guide. They own current hostnames, discovery, SSH identities, sudo, and LAN shares. Do not duplicate access recipes or revive old aliases, addresses, or share mappings in this project. Project-specific application protocol documentation remains local.

## SD-card handling

After an SD-card deployment, synchronize and verify the completed writes but leave the card mounted. Never unmount or eject an SD card unless Smith explicitly requests it; the Author or another agent may still want to use the mounted card. Report that the transfer is complete without declaring the card safe to remove.

## Olimex bench authority

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).

This guide alone defines bench preparation, scheduling, execution, recovery and
check-in. Local task packets specify the fixture and evidence, not alternate
bench procedures.
