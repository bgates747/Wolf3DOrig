"""File-only rejoin of failed actual97 and its separate successful cleanup.

Use archived input bytes: prospective corrections must not rewrite history.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import json

T = Path(__file__).resolve().parent
R = T / 'results/actual97'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text())


def main():
    manifest = read(R / 'SHA256.json')
    for name, record in manifest.items():
        p = R / name
        assert sha(p) == record['sha256'] and p.stat().st_size == record['bytes'], name
    kit = read(R / 'kit.json')
    assert sha(R / 'kit.json') == '1b4d2dd929827cdf00f9fa7aef4b1da3ebbfc5b3e665642db263eb8ea900d143'
    cleanup = read(R / 'cleanup97/kit.json')
    delta = read(R / 'cleanup97/binding-delta.json')
    assert len(kit['inputs']) == 664 and len(cleanup['inputs']) == 668
    assert cleanup == dict(kit, inputs=kit['inputs'] | delta['added_inputs'])
    assert set(cleanup['inputs']) - set(kit['inputs']) == set(delta['added_inputs'])
    saved = read(R / 'cleanup97/frozen-inputs/index.json')
    assert set(saved) == set(cleanup['inputs'])
    for name, digest in cleanup['inputs'].items():
        assert saved[name]['sha256'] == digest and sha(saved[name]['snapshot']) == digest, name
    prior = read(T.parent / 'WOLF-PERF-022/results/actual95/kit.json')
    assert all(prior['inputs'][name] == digest for name, digest in delta['added_inputs'].items())
    failure = read(R / 'evidence/failure.json')
    donor = '/Agon/mystuff/agon-extender/agents/net004/uart1-bootstrap-r01/bootstrap.py'
    assert failure['error'] == repr(KeyError(donor))
    assert failure['custody_retained'] and failure['next_dispatch_stopped']
    for pattern in ('??-vdplet-*', 'probe-*', 'module-*'):
        assert not list((R / 'evidence').glob(pattern)), pattern
    assert not (R / 'evidence/flash-b/clean-bootstrap').exists()
    assert sha(R / 'evidence/flash-b/read.bin') == kit['inputs'][kit['install_b']]
    session = read(R / 'observer/session.json')
    attached = read(R / 'observer/attached.json')
    observed = read(R / 'observer/observer-result.json')
    assert attached['nonce'] == session['nonce']
    assert attached['session_sha256'] == sha(R / 'observer/session.json')
    assert 0 <= attached['epoch'] - session['epoch'] <= 45
    assert observed['passed'] and observed['owned_tracer_joined'] and observed['tracer_returncode'] == 0
    assert observed['controller'] == session['controller']
    assert observed['observer'] == attached['observer']
    assert not observed['controller_signalled_by_observer']
    assert 'SIGTERM' not in (R / 'observer/signal.trace').read_text()
    actors = read(R / 'host-actors-terminal.json')
    assert actors['all_original_handles_terminal'] and actors['exact_processes_terminal']
    for name, code, handle in (('controller', 1, 95282), ('observer', 0, 87174), ('cleanup', 0, 51124)):
        terminal = read(R / (name + '-tool-terminal.json'))
        assert terminal['original_session_id'] == handle and terminal['tool_result']['exit_code'] == code
    complete = read(R / 'cleanup97/complete.json')
    assert complete['passed'] and complete['full_handback'] and complete['original_suite_failed']
    assert complete['room_records'] == 0
    terminal = read(R / 'cleanup-actors-terminal.json')
    assert terminal['exact_cleanup_process_terminal'] and terminal['returncode'] == 0
    restored = R / 'cleanup97/evidence/flash-restore/read.bin'
    assert sha(restored) == '85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'
    assert restored.stat().st_size == 1105920
    release = read(R / 'released.json')
    assert release['generation'] == 97 and release['request'] == kit['request']
    assert release['release_observation']['components'] == kit['incoming_components']
    assert all(release['release_observation']['checks'].values())
    released = datetime.fromisoformat(release['released']).timestamp()
    assert 0 <= released - release['release_observation']['epoch'] <= 120
    assert release['next_request']['request'] == '8579d19c9832'
    result = dict(verified=True, cohort_passed=False, room_records=0, info_records=0,
        failure=failure, original_inputs=664, cleanup_inputs=668,
        missing_dependencies=delta['added_inputs'], positive_observer_attached=True,
        sigterm_observed=False, original_controller_exit=1, observer_exit=0, cleanup_exit=0,
        incoming_fullspan_restored=True, full_handback=True, released=release['released'],
        next_request=release['next_request']['request'], manifest_files=len(manifest),
        limits='Known late-loaded host dependency omission; no renderer/performance verdict. Original esptool write/read hard resets occurred; no maintained bootstrap or guest before failure. Cleanup uses ONE unchanged current bootstrap after exact restoration. No new device access, replay, calibration or adoption.')
    (R / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
