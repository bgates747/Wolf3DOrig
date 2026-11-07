"""Bounded sole105 cleanup after completed game and stale metadata journal.

Preserve original failure/data, retire only the current idle listener through
a fresh normal journal, restore exact incoming native/tail FIRST and hand back.
No guest, profiler query, pre-restore reset or test replay.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import time

T = Path(__file__).resolve().parent
B = T / 'build/hardware02'
C = B / 'cleanup105'
G = Path('/Agon/mystuff/agon-extender/agents/bench-scheduler/wolf-profile001-hardware02')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    grant = json.loads((G / 'grant.json').read_text())
    assert grant['generation'] == 105 and grant['owner'] == 'wolf3dorig'
    assert grant['request'] == '47bae5199a9c'
    assert grant['lease'] == '1e14ee6637224334b3834170a28bab7b'
    assert sha(B / 'kit.json') == 'a0a6aa96d725793752f7b573277399f5c9570bce4243447cfe7c8f48a57e0e5b'
    actors = json.loads((B / 'host-actors-terminal.json').read_text())
    assert actors['all_original_handles_terminal'] and actors['exact_processes_terminal']
    assert actors['controller_returncode'] == 1 and actors['observer_returncode'] == 0
    failure = json.loads((B / 'evidence/failure.json').read_text())
    assert failure['error'] == "RemoteError('Service restarted; preserve this state, use a new state file, and inspect stage recovery')"
    old = json.loads((B / 'evidence/full-game/post-exit-metadata.json').read_text())
    assert old['pending'] is None and old['sequence'] == 2
    original = json.loads((B / 'kit.json').read_text())
    assert (B / 'evidence/full-game/returned-cli.json').exists()
    assert (B / 'evidence/full-game/ram.bin').stat().st_size == original['guest']['guest_bytes']
    assert (B / 'evidence/flash-b/read.bin').read_bytes() == Path(original['install_b']).read_bytes()
    C.mkdir(exist_ok=False)
    shutil.copyfile(B / 'kit.json', C / 'kit.json')
    context = json.loads((G / 'context.json').read_text())
    assert context['sole_operator_handoff'] and context['no_pending_extender_target_commands']
    context['manifest'] = str(C / 'kit.json')
    context['cleanup_only'] = dict(original_grant_sha256=sha(G / 'grant.json'),
        original_failure_sha256=sha(B / 'evidence/failure.json'), once=True,
        cleanup_source_sha256=sha(__file__), original_ram_sha256=sha(B / 'evidence/full-game/ram.bin'),
        no_replay_or_guest_or_INFO_or_PRT=True, no_pre_restore_reset=True,
        original_kit_unchanged=True, old_goal_paused=True)
    (C / 'context.json').write_text(json.dumps(context, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('profile_cleanup105', T / 'hardware.py')
    hw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hw)
    hw.B = C
    hw.h.B = C
    bench = hw.Bench(C / 'context.json')  # ordinary verified construction
    bench.cleaning = True  # cleanup remains required after original actors stop
    bench.deadline = time.monotonic() + 900
    entry = bench.out / 'entry'
    entry.mkdir(exist_ok=False)
    for name, key in (('startup.bin', 'startup_sha256'), ('listener.bin', 'listener_sha256')):
        source = B / 'evidence/entry' / name
        assert sha(source) == bench.components[key]
        shutil.copyfile(source, entry / name)
    # Validate preserved original data without invoking any guest/device query.
    result = hw.qualify_guest.check_return(original['guest'], B / 'evidence/full-game')
    hw.h.save(C / 'scope.json', dict(epoch=time.time(), lease=bench.lease,
        cleanup_only=True, original_failure_preserved=True, preserved_return=result,
        no_pre_restore_reset=True, no_new_guest_or_timer_query=True,
        action='fresh normal current-listener retirement; exact85f9 restore/readback '
               'FIRST; one current matched bootstrap/fullhandback/normalrelease'))
    try:
        bench.own()
        bench.ports_free()
        p = bench.folder('current-listener')
        state = bench.state()
        hw.h.save(p / 'before-state.json', state)
        assert state['sd']['online'] and not state['sd']['pending']
        assert state['worker']['phase'] == 0
        assert state['sd']['boot'] != old['boot'], 'Reconcile actual incarnation; never replay stale journal'
        client = bench.metadata(p, 'fresh-stage-inspection')
        try:
            inspected = {}
            for name in ('route.bin', 'profile.bin', 'wolf3d.vdpl'):
                answer = client.rpc(10, b'\0' + hw.h.path_payload(bench.remote + '/' + name))
                inspected[name] = answer.hex()
                assert answer == b'\1', 'Unexpected owned-path recovery state; stop without mutation'
            hw.h.save(p / 'stage-inspection.json', inspected)
        finally:
            client.lock.close()
        bench.exit(p, 'fresh-current-exit')
        bench.flash('restore', bench.kit['restore'])
        bench.handback()
        hw.h.save(C / 'complete.json', dict(passed=True, original_suite_failed=True,
            original_game_and_data_passed=True, extra_guest_invocations=0,
            exact_incoming_restored=True, full_handback=True, epoch=time.time()))
        print('CLEANUP105 COMPLETE: incoming fullspan restored/readback/full handback', flush=True)
    except BaseException as error:
        hw.h.save(C / 'failure.json', dict(error=repr(error), custody_retained=True,
            cleanup_leaf_stopped=True, no_retry=True, epoch=time.time()))
        raise


if __name__ == '__main__':
    main()
