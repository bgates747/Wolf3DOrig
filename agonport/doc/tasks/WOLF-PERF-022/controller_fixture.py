"""Disposable foreground controller: real recorder, dummy callbacks, no device I/O."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import sys
import time
import host_observer as session
from observe import assert_owner

T = Path(__file__).resolve().parent
HANDLER = T.parent / 'WOLF-PERF-003/hardware/host_interrupt08.py'


def main(folder, lease, case):
    folder = Path(folder)
    folder.mkdir(exist_ok=False)
    assert_owner(lease, 'compiler')
    spec = importlib.util.spec_from_file_location('actual_host_interrupt', HANDLER)
    interrupt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(interrupt)
    interrupt.install(folder / 'handler')
    result = dict(case=case, callbacks=0, no_device_io=True, passed=False)
    started = time.monotonic()
    try:
        c = int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000
        kb = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))
        assert c < 80 and kb >= 524288
        record = session.create(folder / 'observer', lease, 'offline-fixture-not-hardware-kit')
        session.write_once(folder / 'ready.json', record)
        session.wait(folder / 'observer', record, seconds=45)
        # Negative controls use a separate file namespace with the SAME live
        # identities; they cannot disturb the real immutable positive ACK.
        ack = session.load(folder / 'observer/attached.json')
        negative = []
        for bad in ('missing', 'nonce', 'observer-start', 'tracer-pid', 'session'):
            scratch = folder / ('negative-' + bad)
            scratch.mkdir()
            session.write_once(scratch / 'session.json', record)
            changed = json.loads(json.dumps(ack))
            if bad == 'nonce': changed['nonce'] = 'wrong'
            if bad == 'observer-start': changed['observer']['start'] += 1
            if bad == 'tracer-pid': changed['tracer']['pid'] = os.getpid()
            if bad == 'session': changed['session_sha256'] = 'wrong'
            if bad != 'missing': session.write_once(scratch / 'attached.json', changed)
            try:
                session.check(scratch, record)
                raise AssertionError('Negative handshake admitted: ' + bad)
            except session.ObserverUnavailable:
                negative.append(bad)
        result['negative_refusals'] = negative
        session.check(folder / 'observer', record)
        result['callbacks'] += 1
        session.write_once(folder / 'first-callback.json', dict(callbacks=1, pid=os.getpid()))
        if case == 'signal':
            while time.monotonic() - started < 70:
                time.sleep(.05)
            raise AssertionError('Expected controlled signal not delivered')
        elif case == 'cancel':
            deadline = time.monotonic() + 30
            while True:
                try:
                    session.check(folder / 'observer', record)
                except session.ObserverUnavailable:
                    result['observer_loss_refused_successor'] = True
                    break
                assert time.monotonic() < deadline
                time.sleep(.025)
            # Safe preservation/cleanup remains possible after refusal.
            result['cleanup_callback'] = True
        else:
            time.sleep(.3)
        result['passed'] = True
    except interrupt.HostInterrupted as error:
        result['signal'] = error.signum
        result['passed'] = case == 'signal' and error.signum == 15
        raise
    finally:
        result['seconds'] = time.monotonic() - started
        session.write_once(folder / 'controller-result.json', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', required=True, type=Path)
    parser.add_argument('--lease', required=True)
    parser.add_argument('--case', required=True, choices=('normal', 'signal', 'cancel'))
    a = parser.parse_args()
    main(a.folder, a.lease, a.case)
