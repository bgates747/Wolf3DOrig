"""Native foreground exact-controller observer; never signals its tracee."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import select
import signal
import subprocess
import sys
import time
import host_observer as session

D = Path('/Agon/mystuff/agon-dev-env')


def preflight():
    assert sys.executable == '/usr/bin/python3' and hasattr(os, 'pidfd_open')
    files = {str(Path(sys.executable).resolve()), '/usr/bin/strace'}
    for module in tuple(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name and Path(name).is_file():
            files.add(str(Path(name).resolve()))
    return dict(passed=True, interpreter=sys.executable, target_access=False,
                files={n: hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in sorted(files)})


def assert_owner(lease, resource):
    script = (D / 'cross-agent/olimex-bench/bench_lease.py' if resource == 'bench'
              else D / 'cross-agent/pi5-workloads/pi5_lease.py')
    subprocess.run([str(D / '.venv/bin/python'), str(script), 'assert-owner',
                    '--owner', 'wolf3dorig', '--lease', lease],
                   check=True, stdout=subprocess.DEVNULL, timeout=15)


def bind_context(context, record):
    """Rejoin the same immutable kit and real grant, without device imports."""
    c = session.load(context)
    manifest = Path(c['manifest'])
    kit = session.load(manifest)
    grant = session.load(c['grant'])
    if 'active' in grant:
        grant = grant['active']
    assert grant['owner'] == 'wolf3dorig'
    assert grant['lease'] == record['lease']
    assert grant['task'] == kit['task'] == 'WOLF-PERF-022-hardware01'
    assert grant['request'] == kit['request'] == 'dfe8c5bda3b7'
    assert grant['entry_observation']['components'] == kit['incoming_components']
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == record['kit_sha256']
    assert manifest.resolve() == Path(__file__).resolve().parent / 'build/hardware01/kit.json'
    for name, digest in kit['inputs'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name


def main(folder, lease, resource, context=None):
    assert sys.executable == '/usr/bin/python3' and hasattr(os, 'pidfd_open')
    folder = Path(folder).resolve()
    record = session.load(folder / 'session.json')
    assert record['schema'] == 'wolf-observer-session-v1' and record['lease'] == lease
    target = record['controller']
    assert target['uid'] == os.getuid() and target['pid'] != os.getpid()
    assert session.identity(target['pid']) == target
    assert session.tracer(target['pid']) == 0, 'Controller already traced'
    if resource == 'bench':
        assert context is not None, 'Actual context is mandatory'
        expected = session.load(Path(__file__).resolve().parent / 'OBSERVER-PREFLIGHT.json')
        assert preflight() == expected, 'Actual native observer closure differs'
        bind_context(context, record)
    assert_owner(lease, resource)
    # pidfd remains tied to this original process, even if its PID is reused.
    fd = os.pidfd_open(target['pid'])
    poll = select.poll()
    poll.register(fd, select.POLLIN)
    assert session.identity(target['pid']) == target
    child = None
    outcome = dict(controller=target, observer=session.identity(os.getpid()),
                   controller_signalled_by_observer=False, passed=False)
    def interrupted(number, _frame):
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(sig, signal.SIG_DFL)
        outcome['observer_signal'] = number
        raise InterruptedError(number)
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, interrupted)
    started = time.monotonic()
    try:
        argv = ['/usr/bin/strace', '--interruptible=1', '-qq', '-ttt',
                '-e', 'trace=none', '-e', 'signal=SIGTERM',
                '-o', str(folder / 'signal.trace'), '-p', str(target['pid'])]
        outcome['argv'] = argv
        with (folder / 'observer.log').open('x') as log:
            child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True)
            deadline = time.monotonic() + 5
            while session.tracer(target['pid']) != child.pid:
                assert child.poll() is None and not poll.poll(0)
                assert time.monotonic() < deadline, 'Attach deadline expired'
                time.sleep(.01)
            ack = dict(nonce=record['nonce'],
                       session_sha256=hashlib.sha256((folder / 'session.json').read_bytes()).hexdigest(),
                       observer=session.identity(os.getpid()), tracer=session.identity(child.pid),
                       epoch=time.time())
            assert ack['tracer']['pgid'] == child.pid != target['pgid']
            session.write_once(folder / 'attached.json', ack)
            while not poll.poll(100):
                assert child.poll() is None, 'Tracer ended while controller was live'
                assert time.monotonic() - started < 4250, 'Finite observer bound expired'
            child.wait(timeout=5)
            assert child.returncode == 0
            outcome['passed'] = True
    finally:
        # Only our own tracer Popen is signalled. Cancellation detaches; it never
        # signals, waits for, or takes cleanup custody of the controller.
        if child is not None:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
            else:
                child.wait()
            outcome['tracer_returncode'] = child.returncode
            outcome['owned_tracer_joined'] = True
        os.close(fd)
        outcome['seconds'] = time.monotonic() - started
        session.write_once(folder / 'observer-result.json', outcome)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', type=Path)
    parser.add_argument('--lease')
    parser.add_argument('--resource', choices=('bench', 'compiler'), default='bench')
    parser.add_argument('--context', type=Path)
    parser.add_argument('--preflight-only', action='store_true')
    a = parser.parse_args()
    if a.preflight_only:
        print(json.dumps(preflight(), indent=2))
    else:
        assert a.folder is not None and a.lease is not None
        main(a.folder, a.lease, a.resource, a.context)
