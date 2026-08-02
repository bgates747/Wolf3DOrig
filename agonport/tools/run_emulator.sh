#!/usr/bin/env bash
set -euo pipefail

port_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
profile="${port_root}/emulator"
fab_bin="$(readlink -f "${profile}/fab-agon-emulator")"
vdp_module="$(readlink -f "${AGONPORT_VDP:-${profile}/vdp_wolf3d.so}")"
mos_bin="$(readlink -f "${profile}/mos_console8.bin")"
sdcard="$(readlink -f "${profile}/sdcard")"

for required in "${fab_bin}" "${vdp_module}" "${mos_bin}"; do
    if [[ ! -f "${required}" ]]; then
        printf 'Required emulator artifact is missing: %s\n' "${required}" >&2
        exit 1
    fi
done
if [[ ! -d "${sdcard}" ]]; then
    printf 'Required emulator SD directory is missing: %s\n' "${sdcard}" >&2
    exit 1
fi

run_root="$(mktemp -d)"
trap 'rmdir "${run_root}"' EXIT
cd "${run_root}"

if [[ -f "${HOME}/.local/lib/libSDL3.so.0" ]]; then
    export LD_LIBRARY_PATH="${HOME}/.local/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
fi

SDL_VIDEODRIVER=wayland exec "${fab_bin}" \
    --renderer sw \
    --firmware console8 \
    --mos "${mos_bin}" \
    --vdp "${vdp_module}" \
    --sdcard "${sdcard}" \
    --verbose -z
