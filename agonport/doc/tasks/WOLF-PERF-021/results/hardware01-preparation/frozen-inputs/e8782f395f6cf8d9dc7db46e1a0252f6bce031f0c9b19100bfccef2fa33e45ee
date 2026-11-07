"""One new serial build-check receipt; preserve completed build374 unchanged."""
from pathlib import Path
import argparse, hashlib, json, os, signal, subprocess, time

T = Path(__file__).resolve().parent
B = T / 'build/alias01'
D = Path('/Agon/mystuff/agon-dev-env')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(lease):
    inputs = json.loads((B / 'inputs.json').read_text())
    for name, digest in inputs.items():
        assert sha(name) == digest, name
    assert not (B / 'receipt.json').exists(), 'New revision after any attempt'
    start = time.monotonic()
    receipt = dict(passed=False, steps=[], guards=[], input_count=len(inputs))

    def interrupted(number, _frame):
        receipt['signal'] = dict(number=number, epoch=time.time(), pid=os.getpid())
        raise RuntimeError('Host interruption')

    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(number, interrupted)

    def guard():
        c = int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000
        kb = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))
        receipt['guards'].append(dict(epoch=time.time(), cpu_c=c, available_kib=kb))
        assert c < 80 and kb >= 524288 and time.monotonic() - start < 600

    def run(label, args, bound):
        subprocess.run([str(D / '.venv/bin/python'), str(D / 'cross-agent/pi5-workloads/pi5_lease.py'),
                        'assert-owner', '--owner', 'wolf3dorig', '--lease', lease], check=True, stdout=subprocess.DEVNULL)
        guard()
        begin = time.monotonic()
        with (B / (label + '.log')).open('x') as log:
            child = subprocess.Popen(list(map(str, args)), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                while child.poll() is None:
                    guard()
                    assert time.monotonic() - begin < bound, label
                    time.sleep(.25)
                receipt['steps'].append(dict(label=label, argv=list(map(str, args)), returncode=child.returncode, seconds=time.monotonic() - begin))
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
            root = T / 'build/r01' / arm
            prod = root / 'production'
            output = B / (arm + '-test')
            run(arm + '-compile', ['g++', '-std=c++17', '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-pedantic',
                '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer',
                '-I' + str(root / 'sdk/include'), '-I' + str(prod), prod / 'wolf3d_world_mirror.cpp',
                T / 'test_background_alias.cpp', '-o', output], 180)
            run(arm + '-check', [output], 60)
            assert 'PASS 1176 original globally ordered background cases' in (B / (arm + '-check.log')).read_text()
        receipt['passed'] = True
        receipt['cases_per_arm'] = 1176
    except BaseException as error:
        receipt['error'] = repr(error)
        raise
    finally:
        receipt['seconds'] = time.monotonic() - start
        receipt['owned_children_joined'] = True
        (B / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('PASS original/candidate ordered row-alias oracle1176 cases each; no target execution')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--lease', required=True)
    main(parser.parse_args().lease)
