"""One selected standing recovery leaf; no reflash, application or test replay."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import time

T = Path(__file__).resolve().parent
B = T / 'build/hardware01'
G = Path('/Agon/mystuff/agon-extender/agents/bench-scheduler/wolf-profile001')
E = Path('/Agon/mystuff/agon-extender')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(arm):
    assert arm in ('agon', 'paired')
    grant = json.loads((G / 'grant.json').read_text())
    assert grant['owner'] == 'wolf3dorig' and grant['generation'] == 101
    assert grant['request'] == 'b23015b2e071'
    assert grant['lease'] == 'dd0161cdd4f643739e6aed8af30a899b'
    assert sha(B / 'kit.json') == '0f774a0c138e26e0edd63aa7e89ede9ca64616afd78d163cf4c48a4757c861b5'
    failed = json.loads((B / 'cleanup101/failure.json').read_text())
    assert failed['error'] == repr(RuntimeError('Agon admission failed; no retry/RUN'))
    if arm == 'paired':
        first = B / 'recovery101-agon'
        assert (first / 'failure.json').exists() and not (first / 'complete.json').exists()
        assert json.loads((first / 'evidence/agon-only/helper-result.json').read_text())['returncode'] != 0
    kit = json.loads((B / 'kit.json').read_text())
    read = B / 'cleanup101/evidence/flash-restore/read.bin'
    assert read.read_bytes() == Path(kit['restore']).read_bytes()
    C = B / ('recovery101-' + arm)
    C.mkdir(exist_ok=False)
    shutil.copyfile(B / 'kit.json', C / 'kit.json')
    context = json.loads((G / 'context.json').read_text())
    assert context['sole_operator_handoff'] and context['no_pending_extender_target_commands']
    context['manifest'] = str(C / 'kit.json')
    context['cleanup_only'] = dict(arm=arm, no_reflash=True, no_guest_or_INFO_or_PRT=True,
        original_failure_preserved=True, old_goal_paused=True, once=True)
    (C / 'context.json').write_text(json.dumps(context, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('profile_recovery101', T / 'hardware.py')
    hw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hw)
    hw.B = C
    hw.h.B = C
    b = hw.Bench(C / 'context.json')
    b.cleaning = True
    b.deadline = time.monotonic() + 600
    entry = b.out / 'entry'
    entry.mkdir()
    for name, key in (('startup.bin', 'startup_sha256'), ('listener.bin', 'listener_sha256')):
        source = B / 'evidence/entry' / name
        assert sha(source) == b.components[key]
        shutil.copyfile(source, entry / name)
    restored = b.out / 'flash-restore'
    restored.mkdir()
    shutil.copyfile(read, restored / 'read.bin')
    hw.h.save(restored / 'receipt.json', dict(passed=True, independent_readback=True,
        image_sha256=sha(read), span=1105920, offset=65536, app_only=True,
        original_readback=str(read), original_bootstrap_failed=True,
        no_reflash_in_recovery=True, recovery_boot_proof_separate=True))
    b.own()
    b.ports_free()
    try:
        p = b.folder('agon-only' if arm == 'agon' else 'paired')
        if arm == 'agon':
            argv = [str(E / '.venv/bin/python'), str(E / 'scripts/reset_agon_usb.py'),
                    '--config', str(E / 'agents/bench-reset/usb-reset.local.json'),
                    '--verify-url', b.url, '--verify-timeout', '60']
            hw.h.save(p / 'issued.json', dict(argv=argv, once=True, arm=arm, epoch=time.time()))
            with (p / 'helper.log').open('x') as log:
                result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=90)
            hw.h.save(p / 'helper-result.json', dict(returncode=result.returncode,
                      owned_child_joined=True, once=True, epoch=time.time()))
            assert result.returncode == 0, 'One Agon-only recovery failed; no in-leaf retry'
            b.cli(p, 'recovered-cli')
        else:
            b.boot(p, 'recovered-paired')
        b.handback()
        hw.h.save(C / 'complete.json', dict(passed=True, original_cohort_failed=True,
            recovered_arm=arm, exact_incoming_restored=True, full_handback=True,
            no_guest_or_test_replay=True, epoch=time.time()))
        print('RECOVERY101 COMPLETE', arm, flush=True)
    except BaseException as error:
        hw.h.save(C / 'failure.json', dict(error=repr(error), custody_retained=True,
            recovery_leaf_stopped=True, no_retry=True, epoch=time.time()))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--arm', choices=('agon', 'paired'), required=True)
    main(parser.parse_args().arm)
