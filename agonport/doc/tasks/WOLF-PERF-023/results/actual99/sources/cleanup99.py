"""Sole99 preservation/restoration only after the observer's SIGTERM stop.

Ordinary constructor, unchanged683-input kit, separate namespace, no guest or
observer restart. Existing preserve_setup proves CLI and SAVEs RAM before LOAD
or reset, retains available diagnostics, restores85f9 and fully hands back.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import time

T = Path(__file__).resolve().parent
B = T / 'build/hardware02'
C = B / 'cleanup99'
G = Path('/Agon/mystuff/agon-extender/agents/bench-scheduler/wolf-perf023-r02')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    grant = json.loads((G / 'grant.json').read_text())
    assert grant['generation'] == 99 and grant['lease'] == '59966ca11750434dadfdaafd611620b3'
    assert grant['owner'] == 'wolf3dorig' and grant['request'] == '0d70a117969f'
    assert sha(B / 'kit.json') == 'bafa9e767684710a8bef275d98da74d0ee6e872d177a25dec0a15b8e5cdc53d6'
    actors = json.loads((B / 'host-actors-terminal.json').read_text())
    assert actors['all_original_handles_terminal'] and actors['exact_processes_terminal']
    assert actors['controller_returncode'] == actors['observer_returncode'] == 1
    observed = json.loads((B / 'observer/observer-result.json').read_text())
    assert observed['observer_signal'] == 15 and observed['owned_tracer_joined']
    failure = json.loads((B / 'evidence/failure.json').read_text())
    assert failure['next_dispatch_stopped'] and 'ObserverUnavailable' in failure['error']
    assert not (B / 'evidence/03-vdplet-room').exists()
    raw = (B / 'evidence/02-vdplet-room/serial.bin').read_bytes()
    assert b'WOLF-PERF-003 COMPLETE' in raw and b'VDPL UNLOAD status=0' in raw
    assert raw.rstrip().endswith(b'/test/wolf/perf023/r02 *')
    C.mkdir(exist_ok=False)
    shutil.copyfile(B / 'kit.json', C / 'kit.json')
    context = json.loads((G / 'context.json').read_text())
    assert context['sole_operator_handoff'] and context['no_pending_extender_target_commands']
    context['manifest'] = str(C / 'kit.json')
    context['cleanup_only'] = dict(original_grant_sha256=sha(G / 'grant.json'),
        original_failure_sha256=sha(B / 'evidence/failure.json'), once=True,
        no_replay_or_guest_or_INFO=True, preserve_original_RAM_before_LOAD_reset=True,
        original_kit_unchanged=True, human_goal_paused=True)
    (C / 'context.json').write_text(json.dumps(context, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('wolf023_cleanup99', T / 'hardware02.py')
    hardware = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hardware)
    hardware.B = C
    hardware.h.B = C
    bench = hardware.Bench(C / 'context.json')
    bench.cleaning = True
    bench.deadline = time.monotonic() + 900
    entry = bench.out / 'entry'
    entry.mkdir(exist_ok=False)
    for name, key in [('startup.bin', 'startup_sha256'), ('listener.bin', 'listener_sha256')]:
        source = B / 'evidence/entry' / name
        assert sha(source) == bench.components[key]
        shutil.copyfile(source, entry / name)
    bench.own()
    bench.ports_free()
    try:
        # Original candidate has returned to real CLI. No new application or
        # probe; this existing path proves CLI again, saves genuine RAM first,
        # collects only available original loading diagnostics, then restores.
        bench.preserve_setup()
        hardware.h.save(C / 'complete.json', dict(passed=True, original_cohort_failed=True,
            goal_paused=True, original_RAM_preserved_before_LOAD_reset=True,
            exact_incoming_restored=True, full_handback=True, epoch=time.time()))
        print('CLEANUP99 COMPLETE: RAM preserved, exact incoming restore/full handback; no replay', flush=True)
    except BaseException as error:
        hardware.h.save(C / 'failure.json', dict(error=repr(error), custody_retained=True,
            cleanup_leaf_stopped=True, no_retry=True, epoch=time.time()))
        raise


if __name__ == '__main__':
    main()
