"""Finite serial target-package gate with actual compiler ownership per child."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

T = Path(__file__).resolve().parent
B = T / 'build/r01'
D = Path('/Agon/mystuff/agon-dev-env')
TOOL = Path('/home/smith/.platformio/packages/toolchain-xtensa-esp32/bin')


def main(lease):
    for name, digest in json.loads((B / 'inputs.json').read_text())['inputs'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
    assert not (B / 'build-receipt.json').exists(), 'Preserve first attempt'
    start = time.monotonic()
    receipt = dict(steps=[], guards=[], passed=False)

    def stop(signum, _frame):
        receipt['host_signal'] = dict(number=signum, epoch=time.time(), pid=os.getpid())
        raise InterruptedError(signum)

    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, stop)

    def guard():
        c = int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000
        mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))
        receipt['guards'].append(dict(epoch=time.time(), cpu_c=c, available_kib=mem))
        assert c < 80 and mem >= 524288 and time.monotonic() - start < 900

    def run(label, args):
        subprocess.run([str(D / '.venv/bin/python'), str(D / 'cross-agent/pi5-workloads/pi5_lease.py'),
            'assert-owner', '--owner', 'wolf3dorig', '--lease', lease], check=True, stdout=subprocess.DEVNULL)
        guard()
        begin = time.monotonic()
        with (B / (label + '.log')).open('x') as log:
            child = subprocess.Popen(list(map(str, args)), cwd=T, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                while child.poll() is None:
                    guard()
                    assert time.monotonic() - begin < 180, label
                    time.sleep(.25)
                receipt['steps'].append(dict(label=label, args=list(map(str, args)), returncode=child.returncode, seconds=time.monotonic() - begin))
                assert child.returncode == 0, label
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()

    try:
        for arm in ('original', 'candidate'):
            run(arm + '-package', [sys.executable, T / 'target_compile.py', '--arm', arm])
            run(arm + '-symbols', [TOOL / 'xtensa-esp32-elf-nm', '-S', B / arm / 'module/wolf_perf.elf'])
        receipt['passed'] = True
    finally:
        receipt['total_seconds'] = time.monotonic() - start
        (B / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--lease', required=True)
    main(p.parse_args().lease)
