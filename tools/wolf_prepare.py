#!/usr/bin/env python3
"""Prepare a complete pinned-release Wolf payload/profile. Never launches it."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from wolf_firmware import (ROOT, DEFAULT_CACHE, DEFAULT_PAYLOAD, release_files,
    module_info, require, sha, verify_payload, VDP_SHA, MOS_SHA)


def fresh_directory(path):
    path = Path(path)
    require(not path.exists() and not path.is_symlink(), 'Use a fresh output directory: ' + str(path))
    path.mkdir(parents=True)
    return path


def fetch_releases(cache):
    cache = fresh_directory(cache)
    for kind, repo, tag in [('vdplet','agon-vdplet','v0.1.2-alpha'),
                            ('eirene','eirene-mos','3.1.0_uart0_rc_3')]:
        subprocess.run(['gh','release','download',tag,'--repo','bgates747/'+repo,
            '--dir',str(cache/kind)],check=True,timeout=180)
    return release_files(cache)['identity']


def olimex_binding():
    """Read current owner selection; never infer installed state or a grant."""
    directory=ROOT.parent/'agon-extender/docs'
    path=directory/'olimex-firmware-standard.json'
    data=json.loads(path.read_text())
    from wolf_firmware import VDP_SHA
    require(data['vdp']['sha256']==VDP_SHA,'Olimex selector differs; reconcile with owner')
    require(data['emos']['binding_status']=='selected-retained-owner-inventory-confirmed',
            'Olimex EMOS binding is incomplete; resolve with owner')
    return dict(selector=str(path),selector_sha256=sha(path),vdp=data['vdp'],emos=data['emos'],
        installed_state_checked=False,grant=False,firmware_install_selected=False,
        cleanup='Reuse verified standards; any selected exception returns changed components to current standards')


def package(receipt, output, cache=DEFAULT_CACHE):
    receipt = Path(receipt).resolve()
    data = json.loads(receipt.read_text())
    require(data.get('backend') == 'vdplet-direct', 'Routine payload requires vdplet-direct build')
    require(data.get('firmware_policy') == 'pinned-release-v1', 'Rebuild with current pinned-firmware builder')
    require(data.get('required_firmware') == dict(vdp_sha256=VDP_SHA,mos_sha256=MOS_SHA),
            'Stale build receipt firmware pins; rebuild the application receipt')
    binary = ROOT / data['output']
    module = ROOT / data['module']['output']
    require(binary.stat().st_size == data['bytes'] and sha(binary) == data['sha256'], 'Application/receipt mismatch')
    info = module_info(module)
    require(info['sha256'] == data['module']['sha256'] and info['bytes'] == data['module']['bytes'], 'Built application/module mismatch')
    files = release_files(cache)
    storage = data.get('package_storage', {})
    require(storage.get('package_bytes') == info['bytes'] and storage.get('bytes', 0) >= max(info['bytes'], 4096),
            'Application package storage was not qualified for this module')
    sources = {'wolf3d.bin': binary, 'wolf3d.vdpl': module, 'build-receipt.json': receipt}
    generated = ROOT / 'agonport/assets/generated/wolf3d'
    sources.update({name+'.agnb': generated/sub/(name+'.agnb') for name, sub in
        [('hud','hud'),('sfx','audio'),('shell','shell'),('help','shell'),('end','shell')]})
    for level in range(10):
        for name in ('tiles.agnb','sprites.agnb','state_baby.w3l','state_easy.w3l','state_medium.w3l','state_hard.w3l'):
            relative = f'level_{level:02d}/{name}'
            sources[relative] = generated/'levels'/relative
    for name, source in sources.items():
        require(source.is_file() and source.stat().st_size > 0, 'Missing payload input: '+str(source))
    output = fresh_directory(output)
    for name, source in sources.items():
        destination = output/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    manifest = dict(schema='wolf-pinned-payload-v1', kind='game', entry='wolf3d.bin',
        module=info, firmware=files['identity'], run_permission=False,
        files={n:dict(bytes=(output/n).stat().st_size,sha256=sha(output/n)) for n in sorted(sources)})
    (output/'payload.json').write_text(json.dumps(manifest,indent=2)+'\n')
    verify_payload(output)
    return manifest


def profile(payload, output, frontend, backend, cache=DEFAULT_CACHE):
    manifest = verify_payload(payload)
    releases = release_files(cache)
    frontend, backend = Path(frontend).resolve(), Path(backend).resolve()
    require(frontend.is_file() and os.access(frontend,os.X_OK), 'Existing Alexe frontend required')
    require(backend.is_file(), 'Existing Alexe VDP backend required')
    output = Path(output).resolve()
    # A fresh profile, not mutation of another accepted/live profile.
    fresh_directory(output)
    shutil.copytree(payload, output/'sdcard/wolf3d')
    for name, source in [('flexe-agon-emulator.bin',frontend),('flexe-vdp.so',backend)]:
        shutil.copyfile(source,output/name)
    for name, content in [('esp32-firmware.bin',releases['firmware']),('esp32-firmware.elf',releases['elf']),
                          ('mos_platform.bin',releases['mos']),('mos_platform.map',releases['mos_map'])]:
        (output/name).write_bytes(content)
    # No RUN: preserve manual start. Plain load works for both game and fixture.
    (output/'sdcard/autoexec.txt').write_bytes(('SET KEYBOARD 1\r\ncd /wolf3d\r\nload '+manifest['entry']+'\r\n').encode())
    launcher = output/'flexe-agon-emulator'
    launcher.write_text('''#!/usr/bin/env bash
set -euo pipefail
profile_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$profile_dir"
sha256sum --check --status .runtime.sha256
for arg in "$@"; do
    case "$arg" in --vdp*|--mos*|--sdcard*|--firmware*) echo 'Pinned runtime override refused' >&2; exit 1;; esac
done
export AGON_FLEXE_FIRMWARE="$profile_dir/esp32-firmware.bin"
export AGON_FLEXE_ELF="$profile_dir/esp32-firmware.elf"
export AGON_FLEXE_ENGINE="${AGON_FLEXE_ENGINE:-jit}"
export AGON_FLEXE_ARTIFACTS="$profile_dir/last-run"
mkdir -p "$AGON_FLEXE_ARTIFACTS"
if [[ -f "$HOME/.local/lib/libSDL3.so.0" ]]; then
    export LD_LIBRARY_PATH="$HOME/.local/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
exec ./flexe-agon-emulator.bin --firmware platform --mos "$profile_dir/mos_platform.bin" --vdp "$profile_dir/flexe-vdp.so" --sdcard "$profile_dir/sdcard" -z "$@"
''')
    launcher.chmod(0o755)
    (output/'flexe-agon-emulator.bin').chmod(0o755)
    inputs = [p for p in output.rglob('*') if p.is_file()]
    (output/'.runtime.sha256').write_text(''.join(sha(p)+'  '+str(p.relative_to(output))+'\n' for p in sorted(inputs)))
    result = dict(schema='wolf-pinned-profile-v1', firmware=releases['identity'],
        frontend_sha256=sha(frontend),backend_sha256=sha(backend),
        payload_sha256=sha(Path(payload)/'payload.json'), stopped=True, launched=False,
        autoexec_runs=False, runtime_qualification='Not executed', launcher=str(launcher))
    (output/'profile.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def fixture(package_directory, output, cache=DEFAULT_CACHE):
    """Package the corrected finite client, retaining its actual build manifest."""
    package_directory = Path(package_directory).resolve()
    expected = json.loads((package_directory/'expected.json').read_text())
    for name, record in expected['package_files'].items():
        source = package_directory/name
        require(source.stat().st_size == record['bytes'] and sha(source) == record['sha256'],
                'Finite-client input changed: '+name)
    require('package_storage' in expected, 'Rebuild finite client with owned staging storage')
    module = module_info(package_directory/'wolf3d.vdpl')
    identity = release_files(cache)['identity']
    output = fresh_directory(output)
    for source in package_directory.rglob('*'):
        if source.is_file():
            target = output/source.relative_to(package_directory)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
    names=[str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()]
    manifest=dict(schema='wolf-pinned-payload-v1',kind='finite-client',entry='client.bin',
        module=module,firmware=identity,run_permission=False,
        files={n:dict(bytes=(output/n).stat().st_size,sha256=sha(output/n)) for n in sorted(names)})
    (output/'payload.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return verify_payload(output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=DEFAULT_CACHE)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('verify-release')
    sub.add_parser('fetch-releases')
    sub.add_parser('olimex-binding')
    p=sub.add_parser('package');p.add_argument('--receipt',type=Path,required=True);p.add_argument('--output',type=Path,default=DEFAULT_PAYLOAD)
    p=sub.add_parser('fixture');p.add_argument('--package',type=Path,default=ROOT/'src/asm/wolf3d_vdplet_client/tgt/pinned/package');p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('profile');p.add_argument('--payload',type=Path,default=DEFAULT_PAYLOAD);p.add_argument('--output',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--backend',type=Path,required=True)
    p=sub.add_parser('verify-payload');p.add_argument('payload',type=Path,nargs='?',default=DEFAULT_PAYLOAD)
    args=parser.parse_args()
    if args.command=='verify-release': result=release_files(args.cache)['identity']
    elif args.command=='fetch-releases': result=fetch_releases(args.cache)
    elif args.command=='olimex-binding': result=olimex_binding()
    elif args.command=='package': result=package(args.receipt,args.output,args.cache)
    elif args.command=='profile': result=profile(args.payload,args.output,args.frontend,args.backend,args.cache)
    elif args.command=='fixture': result=fixture(args.package,args.output,args.cache)
    else: result=verify_payload(args.payload)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    try:
        main()
    except (ValueError,KeyError,FileNotFoundError) as exc:
        raise SystemExit('Preparation refused: '+str(exc))
