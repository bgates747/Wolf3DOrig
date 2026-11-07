"""Finite actual own-child attach checks; observer is a separate foreground job."""
from pathlib import Path
import argparse, hashlib, json, os, re, select, signal, subprocess, sys, time

T = Path(__file__).resolve().parent
B = T / 'build/r03'
D = Path('/Agon/mystuff/agon-dev-env')
E = Path('/Agon/mystuff/agon-extender')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(lease):
    assert sys.executable == '/usr/bin/python3' and hasattr(os, 'pidfd_open')
    for name, digest in json.loads((B / 'inputs.json').read_text()).items():
        assert sha(name) == digest, name
    assert not (B / 'result.json').exists()
    result = dict(passed=False, cases=[], guards=[], no_target_or_appserver_attach=True)
    started = time.monotonic()
    child = observer = None
    pidfd = None

    def interrupted(number, _frame):
        result['host_signal'] = dict(number=number, epoch=time.time())
        raise RuntimeError('Host interrupted controlled attach qualification')

    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(number, interrupted)

    def guard():
        c = int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000
        kb = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))
        result['guards'].append(dict(epoch=time.time(), cpu_c=c, available_kib=kb))
        assert c < 80 and kb >= 524288 and time.monotonic() - started < 120

    def tracer_pid(pid):
        return int(next(line.split()[1] for line in (Path('/proc') / str(pid) / 'status').read_text().splitlines() if line.startswith('TracerPid:')))

    def stop(process):
        if process is None:
            return
        if process.poll() is None:
            process.terminate()  # exact own Popen PID, never another process
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        else:
            process.wait()

    try:
        for case in ('normal', 'direct', 'group', 'observer'):
            subprocess.run([str(D / '.venv/bin/python'), str(D / 'cross-agent/pi5-workloads/pi5_lease.py'),
                            'assert-owner', '--owner', 'wolf3dorig', '--lease', lease], check=True, stdout=subprocess.DEVNULL)
            guard()
            p = B / case
            p.mkdir()
            begin = time.monotonic()
            record = dict(case=case, sender_pid=os.getpid(), sender_uid=os.getuid())
            with (p / 'child.log').open('x') as child_log, (p / 'observer.log').open('x') as observer_log:
                child_argv = [str(E / '.venv/bin/python'), str(T / 'attach_child.py'),
                              '--ready', str(p / 'ready.json'), '--case', case]
                child = subprocess.Popen(child_argv, stdout=child_log, stderr=subprocess.STDOUT, start_new_session=True)
                pidfd = os.pidfd_open(child.pid)
                poll = select.poll()
                poll.register(pidfd, select.POLLIN)
                try:
                    while True:
                        guard()
                        assert time.monotonic() - begin < 5
                        try:
                            ready = json.loads((p / 'ready.json').read_text())
                            break
                        except (FileNotFoundError, json.JSONDecodeError):
                            assert child.poll() is None
                            time.sleep(.02)
                    assert ready['pid'] == ready['pgid'] == child.pid
                    assert ready['ppid'] == os.getpid() and ready['uid'] == os.getuid()
                    argv = ['/usr/bin/strace', '--interruptible=1', '-qq', '-ttt',
                            '-e', 'trace=none', '-e', 'signal=SIGTERM', '-o', str(p / 'trace.log'),
                            '-p', str(child.pid)]
                    observer = subprocess.Popen(argv, stdout=observer_log, stderr=subprocess.STDOUT, start_new_session=True)
                    record.update(child=ready, child_argv=child_argv, observer_pid=observer.pid, observer_argv=argv)
                    while tracer_pid(child.pid) != observer.pid:
                        guard()
                        assert time.monotonic() - begin < 5 and observer.poll() is None, 'Exact owned-child attach refused/expired'
                        time.sleep(.02)
                    assert os.getpgid(observer.pid) == observer.pid != child.pid
                    record['attached_before_signal'] = True
                    (p / 'attached.json').write_text(json.dumps(record, indent=2) + '\n')
                    if case != 'normal':
                        record['signal_issued'] = dict(epoch=time.time(), number=15, target=case)
                        (p / 'issued.json').write_text(json.dumps(record, indent=2) + '\n')
                        if case == 'direct':
                            os.kill(child.pid, signal.SIGTERM)
                        elif case == 'group':
                            os.killpg(child.pid, signal.SIGTERM)
                        else:
                            os.kill(observer.pid, signal.SIGTERM)
                    if case == 'observer':
                        deadline = time.monotonic() + 5
                        while observer.poll() is None:
                            guard()
                            assert time.monotonic() < deadline
                            time.sleep(.02)
                        observer.wait()
                        assert observer.returncode in (-15, 143)
                        deadline = time.monotonic() + 3
                        while tracer_pid(child.pid) != 0:
                            guard()
                            assert time.monotonic() < deadline
                            time.sleep(.02)
                        assert child.poll() is None and not poll.poll(0)
                        record['observer_cancel_detaches_without_killing_child'] = True
                        record['explicit_owned_child_cleanup_after_detach'] = True
                        child.terminate()
                    while child.poll() is None or observer.poll() is None:
                        guard()
                        assert time.monotonic() - begin < 20
                        time.sleep(.02)
                    child.wait()
                    observer.wait()
                    assert poll.poll(0), 'Original tracee terminal descriptor not ready'
                    record.update(child_returncode=child.returncode, observer_returncode=observer.returncode)
                    trace = (p / 'trace.log').read_text()
                    entries = re.findall(r'--- SIGTERM \{([^}\n]+)\}', trace)
                    record['SIGTERM_records'] = entries
                    matched = any('si_code=SI_USER' in entry and
                        re.search(r'\bsi_pid=' + str(os.getpid()) + r'\b', entry) and
                        re.search(r'\bsi_uid=' + str(os.getuid()) + r'\b', entry) for entry in entries)
                    record['sender_observed'] = matched
                    if case == 'normal':
                        assert child.returncode == observer.returncode == 0 and not entries
                    elif case in ('direct', 'group'):
                        assert child.returncode == -15 and observer.returncode == 0 and matched
                    else:
                        assert child.returncode == -15 and not entries
                    record['seconds'] = time.monotonic() - begin
                    result['cases'].append(record)
                finally:
                    stop(observer)
                    stop(child)
                    observer = child = None
                    os.close(pidfd)
                    pidfd = None
        result['passed'] = True
        result['coverage'] = 'Controlled normal/direct/target-group/observer-cancel cases only. Separate-group attach qualifies prospective signal sender without changing target parent/group or blocking SIGTERM. Actual84/91 cause remains UNKNOWN; no hardware/controller adoption selected.'
    except BaseException as error:
        result['error'] = repr(error)
        raise
    finally:
        stop(observer)
        stop(child)
        if pidfd is not None:
            os.close(pidfd)
        result['seconds'] = time.monotonic() - started
        result['owned_children_joined'] = True
        (B / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=result['passed'], cases=len(result['cases']), seconds=result['seconds']), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--lease', required=True)
    main(parser.parse_args().lease)
