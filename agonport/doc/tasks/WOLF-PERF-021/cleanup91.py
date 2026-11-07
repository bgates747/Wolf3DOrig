"""One standing ordinary Agon recovery, preserve existing SD, exact restoration.

The original observation bound expired without actual CLI. No original live RAM
is claimed. No guest, getter, LOAD, suite replay or new resource probe is used.
"""
from pathlib import Path
import importlib.util, json, os, shutil, subprocess, time

T = Path(__file__).resolve().parent
B = T / 'build/hardware01'
C = B / 'restore91'
G = Path('/Agon/mystuff/agon-extender/agents/bench-scheduler/wolf-perf021-r01')
E = Path('/Agon/mystuff/agon-extender')


def main():
    context = json.loads((G / 'context.json').read_text())
    failure = json.loads((B / 'evidence/failure.json').read_text())
    original = B / 'evidence/01-vdplet-room'
    issued = json.loads((original / 'run-issued.json').read_text())
    journal = json.loads((original / 'run-keys.json').read_text())
    assert failure['error'] == 'HostInterrupted(15)' and failure['custody_retained']
    assert time.time() > issued['epoch'] + 300
    assert not (B / 'evidence/complete.json').exists()
    assert not list((B / 'evidence').glob('02-vdplet-*'))
    assert not journal['active'] and journal['pending'] is None
    observation = json.loads((B / 'cleanup91/evidence/original-observation/receipt.json').read_text())
    assert observation['passive_only'] and not observation['returned_prompt']
    C.mkdir(exist_ok=False)
    shutil.copy2(B / 'kit.json', C / 'kit.json')
    context['manifest'] = str(C / 'kit.json')
    context['cleanup_only'] = dict(original_context=str(G / 'context.json'),
        original_failure=str(B / 'evidence/failure.json'), no_suite_replay=True,
        original_live_RAM_unavailable=True, one_ordinary_recovery=True)
    (C / 'context.json').write_text(json.dumps(context, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('p21_restore91', T / 'hardware02.py')
    hw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hw)
    assert hw.sha(C / 'kit.json') == hw.sha(B / 'kit.json')
    hw.B = C
    hw.h.B = C
    b = hw.Bench(C / 'context.json')  # ordinary constructor is file-only
    b.cleaning = True
    b.deadline = time.monotonic() + 900
    assert b.grant['generation'] == 91 and b.lease == '3158fddf326443eaad29a533d23bfd18'
    entry = b.out / 'entry'
    entry.mkdir()
    for name, key in (('startup.bin', 'startup_sha256'), ('listener.bin', 'listener_sha256')):
        source = B / 'evidence/entry' / name
        assert hw.sha(source) == b.components[key]
        shutil.copy2(source, entry / name)
    for line in (entry / 'startup.bin').read_text().splitlines():
        assert not line.strip().upper().startswith(('RUN', 'EXEC', 'LOAD'))
    p = b.folder('recovery')
    guest = b.kit['guests']['original']['room']
    binary = Path(guest['guest'])
    assert binary.stat().st_size == 325309
    for name in ('guest', 'listing'):
        shutil.copy2(guest[name], p / ('original-' + Path(guest[name]).name))
    hw.h.save(p / 'scope.json', dict(epoch=time.time(), pid=os.getpid(), ppid=os.getppid(),
        lease=b.lease, original_error=failure, original_run=issued,
        original_guest_RAM=dict(base=0x40000, bytes=binary.stat().st_size,
            end_exclusive=0x40000 + binary.stat().st_size, live_preserved=False,
            reason='No actual returned CLI within original observation envelope; no SAVE/reset pretended before it.'),
        reset_ledger_before=dict(original_timed_image_p4_init=1, original_timed_image_agon_reset=1,
            original_timed_image_admitted=True, recovery_specific_attempts=0),
        no_suite_LOAD_RUN_getter_probe_or_replay=True,
        action='ONE ordinary Agon recovery, actual CLI, preserve existing original SD only, exact incoming restoration/readback/fullhandback'))
    try:
        b.own()
        b.ports_free()
        state = b.state()
        hw.h.save(p / 'before-state.json', state)
        assert state['keyboard']['boot'] == journal['boot']
        assert not state['keyboard']['held'] and not state['keyboard']['pending']
        assert state['keyboard']['physical_neutral'] and not state['sd']['online']
        assert not state['sd']['pending'] and state['worker']['phase'] == 0
        argv = [str(E / '.venv/bin/python'), str(E / 'scripts/reset_agon_usb.py'),
            '--config', str(E / 'agents/bench-reset/usb-reset.local.json'),
            '--verify-url', b.url, '--verify-timeout', '60']
        hw.h.save(p / 'ordinary-agon-reset-issued.json', dict(epoch=time.time(), once=True, argv=argv))
        with (p / 'ordinary-agon-reset.log').open('x') as log:
            child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT)
            try:
                result = child.wait(timeout=75)
            finally:
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()
        assert result == 0, 'Ordinary recovery leaf failed; stop, no automatic fallback here'
        b.cli(p, 'actual-post-reset-cli')
        hw.h.save(p / 'actual-cli.json', dict(passed=True, epoch=time.time(), post_reset=True,
            original_live_RAM_preserved=False, no_original_return_claim=True))
        b.service(p, 'original-sd-preservation')
        metadata = b.metadata(p, 'original-sd-listing')
        try:
            entries = list(metadata.entries(b.remote))
        finally:
            metadata.lock.close()
        hw.h.save(p / 'entries.json', entries)
        wanted = ('before.bin', 'after.bin', 'stack.bin', 'timing.bin', 'native.bin', 'loading.bin', 'loading3.bin')
        captured = {}
        for name in wanted:
            found = [row for row in entries if row[0].rsplit('/', 1)[-1] == name]
            if not found:
                captured[name] = dict(absent=True)
                continue
            assert len(found) == 1 and not found[0][2] & 16
            output = p / name
            b.transfer(p, 'original-' + name, 'get', b.remote + '/' + name, output)
            captured[name] = dict(bytes=output.stat().st_size, sha256=hw.sha(output), collected_after_reset=True)
        hw.h.save(p / 'original-sd-capture.json', dict(files=captured,
            namespace_cleared_before_original_RUN=True, no_new_guest_since_original_RUN=True,
            original_live_RAM_preserved=False, comparison_passed=False,
            limit='Existing original namespace SD files collected after recovery; provenance/contents require separate validation. No reset-created RAM is labelled original.'))
        b.exit(p, 'restore-offline')
        b.flash('restore', b.kit['restore'])
        b.handback()
        hw.h.save(C / 'complete.json', dict(passed=True, exact_incoming_restored=True,
            full_handback=True, original_suite_failed=True, benchmark_comparison=False,
            ordinary_recovery_attempts=1, paired_recovery_attempts=0,
            original_live_RAM_preserved=False, owned_children_joined=True, epoch=time.time()))
        print('CLEANUP91 COMPLETE; EXACT RESTORATION AND HANDOFF READY', flush=True)
    except BaseException as error:
        hw.h.save(C / 'failure.json', dict(error=repr(error), cleanup_leaf_stopped=True,
            custody_retained=True, no_retry=True, epoch=time.time()))
        raise


if __name__ == '__main__':
    main()
