"""File-only immutable physical kit; never obtains a grant or contacts a device."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

T = Path(__file__).resolve().parent
B = T / 'build/hardware01'
E = Path('/Agon/mystuff/agon-extender')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert Path(sys.executable) == E / '.venv/bin/python'
    assert not B.exists(), 'Preserve frozen kits; select a new revision'
    import hardware as hw
    import bootstrap
    import qualify_guest
    inventory_path = E / 'agents/bench-scheduler/wolf-profile001/source-bindings.json'
    inventory = json.loads(inventory_path.read_text())
    for name, pin in inventory['pins'].items():
        assert sha(name) == pin['sha256'] and Path(name).stat().st_size == pin['bytes'], name
    old_path = T.parent / 'WOLF-PERF-023/build/hardware02/kit.json'
    old = json.loads(old_path.read_text())
    assert old['incoming_components'] == inventory['components']
    B.mkdir()
    guest = json.loads((T / 'build/hardware-guest01/receipt.json').read_text())
    guest['source'] = str(Path(guest['guest']).parent)
    qualified = qualify_guest.verify(guest)
    (B / 'guest-qualification.json').write_text(json.dumps(qualified, indent=2) + '\n')
    remote = '/test/wolf/profile001/r01'
    (B / 'state.txt').write_bytes((f'SAVE {remote}/post-mode.bin &BC349 &1\r\n'
        f'SAVE {remote}/post-callback.bin &BC38E &3\r\nEMOS sdserve --fast /\r\n').encode())
    (B / 'route.txt').write_bytes((f'SAVE {remote}/route.bin &BCB25 &1\r\n'
        'EMOS sdserve --fast /\r\n').encode())
    (B / 'wolf3d.cfg').write_bytes(b'')
    for name, key in (('restore.bin', 'restore'), ('install-b.bin', 'install_b')):
        assert sha(old[key]) == old['inputs'][old[key]]
        shutil.copyfile(old[key], B / name)
    binding = json.loads(Path(old['source_binding']).read_text())
    binding['provenance'] = ('Retained actual99 full85f9 restoration/readback and exact current '
        'a25f source/map from Extender source-bindings. Actual predecessor release and fresh '
        'grant must match this tuple before contact; no new device observation claimed here.')
    (B / 'source-binding.json').write_text(json.dumps(binding, indent=2) + '\n')
    assets = T / 'build/oryx-inputs01/assets'
    stage = {str(p.relative_to(assets)): str(p) for p in sorted(assets.rglob('*'))
             if p.is_file() and p.suffix in ('.agnb', '.w3l')}
    assert len(stage) == 11
    stage.update({'wolf3d.cfg': str(B / 'wolf3d.cfg'), 'profile.bin': guest['guest'],
                  'wolf3d.vdpl': guest['module'], 'state.txt': str(B / 'state.txt'),
                  'route.txt': str(B / 'route.txt')})
    files = [inventory_path, old_path, Path(old['source_binding']),
             T / 'build/hardware-guest01/receipt.json', Path(guest['guest']), Path(guest['listing'])]
    files += [Path(p) for p in guest['inputs']]
    files += [Path(p) for p in stage.values()]
    files += list(bootstrap.REQUIRED)
    files += [Path(p) for p in inventory['pins']]
    files += [T / n for n in ('PLAN.md', 'PRE-CODE.md', 'FORMAT.md', 'HARDWARE-PLAN.md',
              'build_hardware_guest.py', 'selftest.inc', 'hardware.py', 'prepare_hardware.py',
              'qualify_guest.py', 'test_hardware.py', 'bootstrap.py', 'launch02.py',
              'host_observer.py', 'observe.py', 'HOST-REUSE.md', 'HOST-RESULT.json',
              'LAUNCH-PREFLIGHT.json', 'OBSERVER-PREFLIGHT.json')]
    files.append(T.parents[3] / 'src/asm/wolf3d/scripts/decode_profile.py')
    for name, interpreter in (('LAUNCH-PREFLIGHT.json', str(E / '.venv/bin/python')),
                              ('OBSERVER-PREFLIGHT.json', '/usr/bin/python3')):
        environment = json.loads((T / name).read_text())
        assert environment['passed'] and not environment['target_access']
        assert environment['interpreter'] == interpreter
        for p, digest in environment['files'].items():
            assert sha(p) == digest, p
            files.append(Path(p))
    for module in tuple(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name and name.endswith(('.py', '.so')) and name.startswith(('/Agon/mystuff/', '/usr/')):
            files.append(Path(name))
    # Imported helpers do not reveal future subprocess/dynamic imports.
    files.append(T.parent / 'WOLF-PERF-003/hardware/host_interrupt08.py')
    files += [p for p in B.iterdir() if p.is_file()]
    kit = dict(task='WOLF-PROFILE-001-hardware01', request=hw.REQUEST, remote=remote,
        incoming_components=inventory['components'], guest=guest, stage=stage,
        module_sha256=guest['module_sha256'], native_b_sha256=old['native_b_sha256'],
        source_binding=str(B / 'source-binding.json'), source_binding_passed=True,
        boot_binding_passed=True, p4_boot_build=inventory['p4_boot_build'],
        flash_span=1105920, restore=str(B / 'restore.bin'), install_b=str(B / 'install-b.bin'),
        retain_lease_after_test=False, inputs={str(p.resolve()): sha(p) for p in files},
        restrictions='ONE full-game250-submission profiling integration, two idle INFO17 queries; '
        '1800s absolute/360s cleanup/660s new-guest guard/300s original guest. '
        'Mandatory dual foreground/positive exact attach before IO. First unexpected STOP, '
        'RAM before LOAD/reset where actual CLI permits; exact85f9 restore/readback/fullhandback/'
        'joined original actors/normal release. No replay/HOLD/paused goal resumption.')
    hw.verify_kit(kit)
    (B / 'kit.json').write_text(json.dumps(kit, indent=2) + '\n')
    print(json.dumps(dict(passed=True, inputs=len(kit['inputs']), staged_files=len(stage),
                          kit_sha256=sha(B / 'kit.json'), target_access=False)))


if __name__ == '__main__':
    main()
