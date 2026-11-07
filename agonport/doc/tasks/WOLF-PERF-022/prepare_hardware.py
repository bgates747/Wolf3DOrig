"""File-only exact producer/control/current-release/dual-interpreter kit join."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import sys

T = Path(__file__).resolve().parent
P = T.parent / 'WOLF-PERF-021'
B = T / 'build/hardware02'
E = Path('/Agon/mystuff/agon-extender')
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert Path(sys.executable) == E / '.venv/bin/python'
    assert not B.exists(), 'New revision required after a frozen selection'
    sys.path.insert(0, str(T))
    import hardware02 as hw
    spec = importlib.util.spec_from_file_location('qualified021_exact_producers', P / 'qualify_hardware_guests.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    qualified = module.qualify()
    old = json.loads((P / 'build/hardware02/kit.json').read_text())
    # Rejoin every original pin. The disposed historical plan is retained by
    # its original immutable bytes; it is not silently rehashed as new history.
    index = json.loads((P / 'build/hardware02/frozen-inputs/index.json').read_text())
    files = []
    for name, digest in old['inputs'].items():
        selected = Path(name)
        if selected == P / 'HARDWARE-PLAN.md':
            selected = Path(index[name]['snapshot'])
        assert sha(selected) == digest, name
        files.append(selected)
    comp_path = T / 'build/composition04/receipt.json'
    comp = json.loads(comp_path.read_text()); assert comp['passed']
    for name, digest in comp['inputs'].items():
        assert sha(name) == digest, name
        files.append(Path(name))
    files.extend(Path(n) for n in qualified['inputs'])
    files.extend((comp_path, P / 'qualify_hardware_guests.py'))
    # Latest actual predecessor, not an old token or fresh-device claim.
    latest = E / 'agents/bench-scheduler/mechagon-goal001-r07'
    release = json.loads((latest / 'released.json').read_text())
    assert release['generation'] == 92 and release['released']
    components = release['release_observation']['components']
    assert components == old['incoming_components']
    assert sha(latest / 'owner-install/verify-rollback/ROM.bin') == components['emos_rom_sha256']
    files.extend(latest / n for n in ('released.json', 'release-observation.json', 'final/fresh.json',
        'owner-install/verify-rollback/ROM.bin', 'owner-install/verify-rollback/receipt.json'))
    B.mkdir()
    for name, key in (('restore.bin', 'restore'), ('install-b.bin', 'install_b')):
        shutil.copyfile(old[key], B / name)
    assert sha(B / 'restore.bin') == '85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'
    assert sha(B / 'install-b.bin') == '493fd0a010bedcfc5916314353f93565f7b159ac163d9bc61e7c5078140669e8'
    remote = '/test/wolf/perf022/r02'
    (B / 'state.txt').write_bytes(('SAVE ' + remote + '/post-mode.bin &BC349 &1\r\nSAVE ' + remote + '/post-callback.bin &BC38E &3\r\nEMOS sdserve --fast /\r\n').encode())
    (B / 'route.txt').write_bytes(('SAVE ' + remote + '/route.bin &BCB25 &1\r\nEMOS sdserve --fast /\r\n').encode())
    binding = json.loads(Path(old['source_binding']).read_text())
    assert binding['passed'] and binding['rom_sha256'] == components['emos_rom_sha256']
    binding['provenance'] = 'Exact actual92 fulla25f rollback/readback and complete handback/release match retained d9b/a25f/5d657/ed403/0566; source and85f9 native rollback pins rejoined. No new device read or grant claimed. Real successor and fresh actual admission must still match.'
    (B / 'source-binding.json').write_text(json.dumps(binding, indent=2) + '\n')
    (B / 'guest-qualification.json').write_text(json.dumps(qualified, indent=2) + '\n')
    guests = json.loads((T / 'HARDWARE-GUESTS.json').read_text())
    assert guests == old['guests'], 'No guest rebuild or operand change selected'
    modules = {a: guests[a]['room']['module'] for a in hw.ARMS}
    stage = dict(old['stage'])
    stage.update({'state.txt': str(B / 'state.txt'), 'route.txt': str(B / 'route.txt')})
    files.extend(T / n for n in ('PLAN.md', 'prepare_hardware.py', 'hardware02.py', 'launch02.py',
        'host_observer.py', 'observe.py', 'OBSERVER-PREFLIGHT.json', 'LAUNCH-PREFLIGHT.json',
        'bootstrap.py', 'guest_binding.py', 'analyze.py', 'HARDWARE-GUESTS.json', 'snapshot_inputs.py',
        'test_hardware02.py', 'test_replacement02.py', 'test_observer_controller.py', 'run_composition.py',
        'HOST-RESULT01.md'))
    files.extend(T / 'results/host01' / n for n in ('RESULT.json', 'SHA256.json', 'release.json'))
    for name, expected_interpreter in (('LAUNCH-PREFLIGHT.json', str(E / '.venv/bin/python')),
                                       ('OBSERVER-PREFLIGHT.json', '/usr/bin/python3')):
        environment = json.loads((T / name).read_text())
        assert environment['passed'] and not environment['target_access']
        assert environment['interpreter'] == expected_interpreter
        for file, digest in environment['files'].items():
            assert sha(file) == digest, file
            files.append(Path(file))
    for imported in tuple(sys.modules.values()):
        name = getattr(imported, '__file__', None)
        if name and name.endswith(('.py', '.so')) and name.startswith(('/Agon/mystuff/', '/usr/')):
            files.append(Path(name))
    files.extend(p for p in B.iterdir() if p.is_file())
    kit = {k: old[k] for k in ('native_b_sha256', 'listings', 'flash_span', 'p4_boot_build')}
    kit.update(task='WOLF-PERF-022-hardware02', request=hw.REQUEST, remote=remote,
        incoming_components=components, modules=modules, stage=stage, guests=guests,
        retain_lease_after_test=False, restore=str(B / 'restore.bin'), install_b=str(B / 'install-b.bin'),
        source_binding=str(B / 'source-binding.json'), source_binding_passed=True, boot_binding_passed=True,
        inputs={str(p.resolve()): sha(p) for p in files},
        restrictions='ONE full six uncapped original/cyan/combined/combined/cyan/original rooms/sevenINFO. Positive exact-controller foreground observer before any target I/O;45s handshake INCLUDED in4200s/360cleanup/660newguest guards. First unexpectedSTOP/RAMbeforeLOAD/safe in-flight completion/exact85f9restore/fullcleanup/all actorsjoined/normalrelease. Mech-first, no runtime/firmware/carrier/default adoption.')
    for arm in hw.ARMS:
        kit[arm + '_module_sha256'] = sha(modules[arm])
    hw.verify_kit(kit)
    (B / 'kit.json').write_text(json.dumps(kit, indent=2) + '\n')
    print(json.dumps(dict(passed=True, files=len(kit['inputs']), stage=len(stage), kit_sha256=sha(B / 'kit.json'))))


if __name__ == '__main__':
    main()
