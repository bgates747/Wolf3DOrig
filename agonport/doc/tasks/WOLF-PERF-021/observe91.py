"""Cleanup-only original-epoch passive observation; no keyboard/reset/LOAD/RUN."""
from pathlib import Path
import importlib.util, json, os, shutil, time

T = Path(__file__).resolve().parent
B = T / 'build/hardware01'
C = B / 'cleanup91'
G = Path('/Agon/mystuff/agon-extender/agents/bench-scheduler/wolf-perf021-r01')


def owner():
    spec = importlib.util.spec_from_file_location('p21_cleanup91', T / 'hardware02.py')
    hw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hw)
    hw.B = C
    hw.h.B = C
    b = hw.Bench(C / 'context.json')
    b.cleaning = True
    b.deadline = time.monotonic() + 900
    assert b.grant['generation'] == 91 and b.lease == '3158fddf326443eaad29a533d23bfd18'
    return hw, b


def main():
    context = json.loads((G / 'context.json').read_text())
    kit = json.loads((B / 'kit.json').read_text())
    failure = json.loads((B / 'evidence/failure.json').read_text())
    assert failure['error'] == 'HostInterrupted(15)' and failure['custody_retained']
    assert not (B / 'evidence/complete.json').exists()
    assert not list((B / 'evidence').glob('02-vdplet-*'))
    C.mkdir(exist_ok=False)
    shutil.copy2(B / 'kit.json', C / 'kit.json')
    context['manifest'] = str(C / 'kit.json')
    context['cleanup_only'] = dict(original_context=str(G / 'context.json'),
        original_failure=str(B / 'evidence/failure.json'), no_suite_replay=True)
    (C / 'context.json').write_text(json.dumps(context, indent=2) + '\n')
    hw, b = owner()
    entry = b.out / 'entry'
    entry.mkdir()
    for name, key in (('startup.bin', 'startup_sha256'), ('listener.bin', 'listener_sha256')):
        source = B / 'evidence/entry' / name
        assert hw.sha(source) == b.components[key]
        shutil.copy2(source, entry / name)
    p = b.folder('original-observation')
    for name in ('serial.bin', 'run-keys.json', 'run-issued.json', 'guest-binding.json'):
        shutil.copy2(B / 'evidence/01-vdplet-room' / name, p / ('original-' + name))
    original = json.loads((p / 'original-run-keys.json').read_text())
    issued = json.loads((p / 'original-run-issued.json').read_text())
    assert original['active'] is False and original['pending'] is None
    assert original['boot'] == 2341992575
    b.own()
    b.ports_free()
    state = b.state()
    hw.h.save(p / 'before-status.json', state)
    assert state['keyboard']['boot'] == original['boot']
    assert not state['keyboard']['held'] and not state['keyboard']['pending']
    end = min(time.time() + 45, issued['epoch'] + 300)
    assert end > time.time(), 'Original passive observation envelope expired'
    raw = bytearray()
    print('PASSIVE CLEANUP PID', os.getpid(), flush=True)
    with hw.h.m.open_passive_serial(b.port, baudrate=115200, timeout=.2) as serial:
        while time.time() < end:
            raw.extend(serial.read(8192))
            assert len(raw) <= 4 * 1024 * 1024
            (p / 'continuation-serial.bin').write_bytes(raw)
            if b.remote.encode() + b' *' in raw:
                break
    hw.h.save(p / 'after-status.json', b.state())
    hw.h.save(p / 'receipt.json', dict(passive_only=True, bytes=len(raw),
        original_run_epoch=issued['epoch'], original_bound_epoch=issued['epoch'] + 300,
        observation_epoch=time.time(), returned_prompt=b.remote.encode() + b' *' in raw,
        no_keyboard_write_or_reset_or_replay=True,
        limit='A newly opened passive serial handle can miss bytes emitted before it opened; no missing-prompt inference or invented completion.'))
    print('PASSIVE OBSERVATION COMPLETE', len(raw), flush=True)


if __name__ == '__main__':
    main()
