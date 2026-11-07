"""Sole101 restoration FIRST after original bootstrap failed before any guest.

Separate immutable cleanup context, ordinary verified constructor, same lease.
No pre-restore reset, guest, timer query, profiling replay or invented RAM claim.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import time

T = Path(__file__).resolve().parent
B = T / 'build/hardware01'
C = B / 'cleanup101'
G = Path('/Agon/mystuff/agon-extender/agents/bench-scheduler/wolf-profile001')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    grant = json.loads((G / 'grant.json').read_text())
    assert grant['generation'] == 101 and grant['owner'] == 'wolf3dorig'
    assert grant['request'] == 'b23015b2e071'
    assert grant['lease'] == 'dd0161cdd4f643739e6aed8af30a899b'
    assert sha(B / 'kit.json') == '0f774a0c138e26e0edd63aa7e89ede9ca64616afd78d163cf4c48a4757c861b5'
    actors = json.loads((B / 'host-actors-terminal.json').read_text())
    assert actors['all_original_handles_terminal'] and actors['exact_processes_terminal']
    assert actors['controller_returncode'] == 1 and actors['observer_returncode'] == 0
    failure = json.loads((B / 'evidence/failure.json').read_text())
    assert failure['error'] == repr(RuntimeError('Agon admission failed; no retry/RUN'))
    assert failure['next_dispatch_stopped'] and failure['custody_retained']
    assert not (B / 'evidence/full-game').exists()
    original = json.loads((B / 'kit.json').read_text())
    assert (B / 'evidence/flash-b/read.bin').read_bytes() == Path(original['install_b']).read_bytes()
    C.mkdir(exist_ok=False)
    shutil.copyfile(B / 'kit.json', C / 'kit.json')
    context = json.loads((G / 'context.json').read_text())
    assert context['sole_operator_handoff'] and context['no_pending_extender_target_commands']
    context['manifest'] = str(C / 'kit.json')
    context['cleanup_only'] = dict(original_grant_sha256=sha(G / 'grant.json'),
        original_failure_sha256=sha(B / 'evidence/failure.json'), once=True,
        no_replay_or_guest_or_INFO_or_PRT=True, no_guest_LOAD_or_RAM_exists=True,
        no_pre_restore_reset=True, original_kit_unchanged=True, old_goal_paused=True)
    (C / 'context.json').write_text(json.dumps(context, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('profile_cleanup101', T / 'hardware.py')
    hardware = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hardware)
    hardware.B = C
    hardware.h.B = C
    bench = hardware.Bench(C / 'context.json')
    bench.cleaning = True
    bench.deadline = time.monotonic() + 900
    entry = bench.out / 'entry'
    entry.mkdir(exist_ok=False)
    for name, key in (('startup.bin', 'startup_sha256'), ('listener.bin', 'listener_sha256')):
        source = B / 'evidence/entry' / name
        assert sha(source) == bench.components[key]
        shutil.copyfile(source, entry / name)
    hardware.h.save(C / 'scope.json', dict(epoch=time.time(), lease=bench.lease,
        cleanup_only=True, original_failure_preserved=True, no_guest_loaded_or_run=True,
        no_original_guest_RAM_claim=True, no_pre_restore_reset=True,
        action='Exact85f9 fullspan restore/readback FIRST, ONE maintained current matched '
               'bootstrap and full fresh handback; no replay, then normal release'))
    bench.own()
    bench.ports_free()
    try:
        bench.flash('restore', bench.kit['restore'])
        bench.handback()
        hardware.h.save(C / 'complete.json', dict(passed=True, original_suite_failed=True,
            guest_invocations=0, exact_incoming_restored=True, full_handback=True,
            epoch=time.time()))
        print('CLEANUP101 COMPLETE: exact incoming restoration/full handback; no guest', flush=True)
    except BaseException as error:
        hardware.h.save(C / 'failure.json', dict(error=repr(error), custody_retained=True,
            cleanup_leaf_stopped=True, no_retry=True, epoch=time.time()))
        raise


if __name__ == '__main__':
    main()
