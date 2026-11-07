"""Finite owned-child prospective trace checks, no device or app-server attach."""
from pathlib import Path
import argparse, hashlib, json, os, re, select, signal, subprocess, time

T = Path(__file__).resolve().parent
B = T / 'build/r01'
D = Path('/Agon/mystuff/agon-dev-env')
E = Path('/Agon/mystuff/agon-extender')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(lease):
    inputs = json.loads((B / 'inputs.json').read_text())
    for name, digest in inputs.items():
        assert sha(name) == digest, name
    assert not (B / 'result.json').exists(), 'New revision after an attempt'
    receipt = dict(passed=False, cases=[], guards=[],
                   no_device_or_other_process_attach=True)
    start = time.monotonic()
    active = None

    def interrupted(number, _frame):
        receipt['host_signal'] = dict(number=number, epoch=time.time(), pid=os.getpid())
        raise RuntimeError('Qualification parent interrupted')

    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(number, interrupted)

    def guard():
        c = int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000
        kb = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))
        receipt['guards'].append(dict(epoch=time.time(), cpu_c=c, available_kib=kb))
        assert c < 80 and kb >= 524288 and time.monotonic() - start < 120

    def own():
        subprocess.run([str(D / '.venv/bin/python'), str(D / 'cross-agent/pi5-workloads/pi5_lease.py'),
                        'assert-owner', '--owner', 'wolf3dorig', '--lease', lease],
                       check=True, stdout=subprocess.DEVNULL)

    def cleanup(process):
        # Each group was created by this helper, never a host-wide PID selector.
        # A tracer can exit before its tracee, so reconcile the entire owned PG.
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            process.wait()
            return
        os.killpg(process.pid, signal.SIGTERM)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            process.poll()
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                process.wait()
                return
            time.sleep(.05)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()

    try:
        for case in ('normal', 'direct', 'group'):
            own()
            guard()
            p = B / case
            p.mkdir()
            argv = ['/usr/bin/strace', '--interruptible=1', '-f', '-qq', '-ttt',
                    '-e', 'trace=none', '-e', 'signal=SIGTERM', '-o', str(p / 'trace.log'),
                    str(E / '.venv/bin/python'), str(T / 'child.py'),
                    '--ready', str(p / 'ready.json'), '--case', case]
            begin = time.monotonic()
            with (p / 'stdout.log').open('x') as log:
                active = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                pidfd = None
                record = dict(case=case, argv=argv, tracer_pid=active.pid,
                              sender_pid=os.getpid(), sender_uid=os.getuid())
                try:
                    while True:
                        guard()
                        assert time.monotonic() - begin < 5, 'Owned child never became ready'
                        try:
                            ready = json.loads((p / 'ready.json').read_text())
                            break
                        except (FileNotFoundError, json.JSONDecodeError):
                            assert active.poll() is None, 'Tracer exited before ready'
                            time.sleep(.05)
                    assert ready['case'] == case and ready['uid'] == os.getuid()
                    assert ready['ppid'] == active.pid and ready['pgid'] == active.pid
                    assert ready['pid'] != active.pid and ready['default_signal_disposition']
                    record['child'] = ready
                    pidfd = os.pidfd_open(ready['pid']) if case != 'normal' else None
                    if case != 'normal':
                        # Readiness is from this exact newly started owned child.
                        assert os.getpgid(ready['pid']) == active.pid
                        record['signal_issued'] = dict(epoch=time.time(), signal=15,
                            target='owned-child-PID' if case == 'direct' else 'owned-new-process-group')
                        (p / 'issued.json').write_text(json.dumps(record, indent=2) + '\n')
                        if case == 'direct':
                            os.kill(ready['pid'], signal.SIGTERM)
                        else:
                            os.killpg(active.pid, signal.SIGTERM)
                    while active.poll() is None:
                        guard()
                        assert time.monotonic() - begin < 20, 'Case terminal deadline'
                        time.sleep(.05)
                    record['returncode'] = active.returncode
                    if pidfd is not None:
                        poll = select.poll()
                        poll.register(pidfd, select.POLLIN)
                        assert poll.poll(3000), 'Owned tracee not terminal after tracer exit'
                        record['tracee_exit_observed_by_pidfd'] = True
                    trace = (p / 'trace.log').read_text()
                    matches = re.findall(r'--- SIGTERM \{([^}\n]+)\}', trace)
                    record['SIGTERM_records'] = matches
                    record['sender_observed'] = any('si_code=SI_USER' in m and
                        re.search(r'\bsi_pid=' + str(os.getpid()) + r'\b', m) and
                        re.search(r'\bsi_uid=' + str(os.getuid()) + r'\b', m) for m in matches)
                    if case == 'normal':
                        assert active.returncode == 0 and not matches
                    else:
                        assert active.returncode in (-15, 143)
                    if case == 'direct':
                        assert record['sender_observed'], 'Direct-signal attribution unavailable'
                    record['seconds'] = time.monotonic() - begin
                    receipt['cases'].append(record)
                finally:
                    cleanup(active)
                    active = None
                    if pidfd is not None:
                        os.close(pidfd)
        receipt['passed'] = True
        receipt['direct_sender_attribution_qualified'] = True
        receipt['group_sender_attribution_qualified'] = receipt['cases'][2]['sender_observed']
        receipt['scope'] = 'Controlled prospective cases only; actual84/91 signal cause remains UNKNOWN. Missing group attribution limits adoption; no hidden signal blocking, lifetime change, service change, detach, reproduction or hardware trial.'
    except BaseException as error:
        receipt['error'] = repr(error)
        raise
    finally:
        if active is not None:
            cleanup(active)
        receipt['seconds'] = time.monotonic() - start
        receipt['owned_children_joined'] = True
        (B / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ('passed', 'direct_sender_attribution_qualified', 'group_sender_attribution_qualified', 'seconds')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--lease', required=True)
    main(parser.parse_args().lease)
