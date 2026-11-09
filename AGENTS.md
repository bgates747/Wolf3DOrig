# Agent instructions

## Firmware defaults

Follow [FIRMWARE.md](FIRMWARE.md) for all test/deployment preparation. Smith pins
VDPlet v0.1.2-alpha on Alexe, Olimex and Console8; Eirene MOS
3.1.0_uart0_rc_3 on Alexe/Console8, and scheduler-maintained latest approved
EMOS on Olimex. Verify the release assets/checksums. Older profile/kit examples
do not override these pins. Justify required firmware exceptions in the normal
scheduling request; existing permissions remain in force.

## Network access authority

For access between development machines, read the [canonical network instructions](https://github.com/bgates747/agon-dev-env/blob/feature/standardized-deployment/codex/environment.md#ssh-between-development-machines) in `~/Agon/mystuff/agon-dev-env/codex/environment.md` and its machine-local `.local/ssh-001/CONNECTIONS.md` guide. They own current hostnames, discovery, SSH identities, sudo, and LAN shares. Do not duplicate access recipes or revive old aliases, addresses, or share mappings in this project. Project-specific device/protocol and bench-safety instructions remain local.

## SD-card handling

After an SD-card deployment, synchronize and verify the completed writes but leave the card mounted. Never unmount or eject an SD card unless Smith explicitly requests it; the Author or another agent may still want to use the mounted card. Report that the transfer is complete without declaring the card safe to remove.
