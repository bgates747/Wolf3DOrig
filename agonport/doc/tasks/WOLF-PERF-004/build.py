"""Serial finite compilation and ordinary host checks; actual Pi owner only."""
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
P3 = T.parent / 'WOLF-PERF-003'
SDK = P3 / 'build/r04/inputs/sdk'
D = Path('/Agon/mystuff/agon-dev-env')
TOOL = Path('/home/smith/.platformio/packages/toolchain-xtensa-esp32/bin')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(lease, revision):
    global B
    assert revision == 'r03', 'Preserve prior failed attempts'
    B = T / 'build' / revision
    inputs = json.loads((B / 'inputs.json').read_text())
    for name, digest in inputs['inputs'].items():
        assert sha(name) == digest, name
    assert not (B / 'build-receipt.json').exists(), 'New revision required after an attempt'
    start = time.monotonic()
    receipt = dict(steps=[], guards=[], passed=False)

    class BuildInterrupted(BaseException):
        pass

    def stop(signum, _frame):
        receipt['host_signal'] = dict(number=signum, epoch=time.time(), pid=os.getpid())
        raise BuildInterrupted(signum)

    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, stop)

    def guard():
        c = int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000
        available = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))
        receipt['guards'].append(dict(epoch=time.time(), cpu_c=c, available_kib=available))
        assert c < 80 and available >= 524288 and time.monotonic() - start < 900

    def run(label, args, cwd, bound=180):
        subprocess.run([str(D / '.venv/bin/python'), str(D / 'cross-agent/pi5-workloads/pi5_lease.py'),
                        'assert-owner', '--owner', 'wolf3dorig', '--lease', lease], check=True, stdout=subprocess.DEVNULL)
        guard()
        begin = time.monotonic()
        with (B / (label + '.log')).open('x') as log:
            p = subprocess.Popen(list(map(str, args)), cwd=cwd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                while p.poll() is None:
                    guard()
                    assert time.monotonic() - begin < bound, label
                    time.sleep(.25)
                receipt['steps'].append(dict(label=label, args=list(map(str, args)), returncode=p.returncode, seconds=time.monotonic() - begin))
                assert p.returncode == 0, label
            finally:
                if p.poll() is None:
                    os.killpg(p.pid, signal.SIGTERM)
                    try:
                        p.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid, signal.SIGKILL)
                        p.wait()
                (B / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

    try:
        flags = ['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-pedantic', '-I' + str(SDK / 'include'),
                 '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer']
        for arm in ('original', 'candidate'):
            a = B / arm
            prod = a / 'production'
            result = a / 'host-results'
            result.mkdir()
            core = [prod / 'wolf3d_world_mirror.cpp', prod / 'wolf3d_renderer.cpp']
            run(arm + '-fixed-div-compile', flags + [prod / 'wolf3d_world_mirror.cpp', '-I' + str(prod), T / 'test_fixed_div.cpp', '-o', result / 'fixed-div'], prod)
            run(arm + '-fixed-div-check', [result / 'fixed-div'], prod)
            run(arm + '-renderer-compile', flags + core + [prod / 'test_renderer.cpp', '-o', result / 'renderer'], prod)
            run(arm + '-renderer-check', [result / 'renderer', result / 'fixture-frame.bin', result / 'fixture-geometry.bin'], prod)
            run(arm + '-module-compile', flags + ['-DWOLF3D_HOST_TEST', prod / 'wolf3d_module.cpp', prod / 'test_module.cpp', '-o', result / 'module'], prod)
            run(arm + '-module-check', [result / 'module', result / 'module-frame.bin', result / 'target-fixture'], prod)
            run(arm + '-equivalence-compile', flags + core + ['-I' + str(prod), T / 'test_equivalence.cpp', '-o', result / 'equivalence'], prod)
            run(arm + '-equivalence-check', [result / 'equivalence', result / 'frames600.bin', result / 'states600.bin'], prod, bound=240)
            # Preserve the measured target instrumentation and exact safe SDK.
            module_out = a / 'module'
            run(arm + '-target-package', [sys.executable, SDK / 'tools/build_module.py', a / 'native-source/wolf3d_module.cpp',
                '--output', module_out, '--name', 'wolf_perf', '--capabilities', '257', '--abi-minor', '6',
                '--text-limit', '65536', '--data-limit', '16384', '--stack-limit', '2048', '--image-limit', '131072',
                '--build-id', '0x20261104'], a, bound=180)
        for name in ('fixture-frame.bin', 'fixture-geometry.bin', 'module-frame.bin', 'frames600.bin', 'states600.bin'):
            original = B / 'original/host-results' / name
            candidate = B / 'candidate/host-results' / name
            assert original.read_bytes() == candidate.read_bytes(), name
        assert sha(B / 'original/module/wolf_perf.vdpl') == '1907ce1711f68676dc1c0c6eb70b8f55ae03d0934aee537329edcf77fe652610', 'Original target rebuild must match physical54 exactly'
        receipt['compared_outputs'] = {n: dict(bytes=(B / 'original/host-results' / n).stat().st_size,
            sha256=sha(B / 'original/host-results' / n)) for n in ('fixture-frame.bin', 'fixture-geometry.bin', 'module-frame.bin', 'frames600.bin', 'states600.bin')}
        receipt['packages'] = {arm: json.loads((B / arm / 'module/wolf_perf.json').read_text()) for arm in ('original', 'candidate')}
        # Extra source .su, nm and actual section receipts remain beside each ELF.
        for arm in ('original', 'candidate'):
            run(arm + '-symbols', [TOOL / 'xtensa-esp32-elf-nm', '-S', B / arm / 'module/wolf_perf.elf'], B)
        receipt['passed'] = True
        print('PASS exact original/candidate host outputs and 600 direct frames; original target rebuild matches1907; candidate packaged safely.')
    finally:
        receipt['total_seconds'] = time.monotonic() - start
        (B / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--lease', required=True)
    p.add_argument('--revision', required=True)
    args = p.parse_args()
    main(args.lease, args.revision)
