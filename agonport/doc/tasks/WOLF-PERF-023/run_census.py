"""One finite serial sanitized source census, with no candidate or device code."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, signal, subprocess, time

T = Path(__file__).resolve().parent
B = T / 'build/census01'
D = Path('/Agon/mystuff/agon-dev-env')
P = T.parent / 'WOLF-PERF-021/build/r01/candidate'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(lease):
    subprocess.run([str(D / '.venv/bin/python'), str(D / 'cross-agent/pi5-workloads/pi5_lease.py'),
        'assert-owner', '--owner', 'wolf3dorig', '--lease', lease], check=True, stdout=subprocess.DEVNULL)
    assert not B.exists(), 'Preserve any old attempt; use a new revision'
    for name, digest in json.loads((T / 'PRE-CODE-PINS.json').read_text()).items():
        assert sha(name) == digest, name
    kit = json.loads((T.parent / 'WOLF-PERF-022/build/hardware02/kit.json').read_text())
    B.mkdir(parents=True)
    (B / 'production').mkdir()
    files = [T / n for n in ('PLAN.md', 'PRE-CODE-PINS.json', 'count_spans.cpp', 'run_census.py')]
    for path in (P / 'production').iterdir():
        if path.suffix in ('.h', '.inc') or path.name in ('wolf3d_renderer.cpp', 'wolf3d_world_mirror.cpp'):
            assert sha(path) == kit['inputs'][str(path)], path
            shutil.copyfile(path, B / 'production' / path.name)
            files.append(path)
    source = B / 'production/wolf3d_renderer.cpp'
    original = source.read_text()
    assert sha(source) == sha(P / 'native-source/wolf3d_renderer.cpp')
    begin = original.index('void compose_background(')
    end = original.index('uint8_t shifted_component(', begin)
    outside = original[:begin] + original[end:]
    assert original.count('fill_span(') == 3 and outside.count('fill_span(') == 2
    assert outside.count('fill_rect(') == 1 and original.count('compose_background(') == 2
    needle = 'uint32_t count, uint8_t color) {\n'
    assert original.count(needle) == 1
    telemetry = '    ::count_span(target.linear != nullptr, target.x_bias + x, target.pixel_xor, count);\n'
    changed = original.replace(needle, needle + telemetry)
    assert changed.replace(telemetry, '') == original
    source.write_text(changed)
    shutil.copyfile(T / 'count_spans.cpp', B / 'count_spans.cpp')
    files.extend(p for p in (B / 'production').iterdir())
    files.append(B / 'count_spans.cpp')
    sdk = P / 'sdk/include'
    for path in sdk.iterdir():
        if path.is_file():
            assert sha(path) == kit['inputs'][str(path)], path
            files.append(path)
    inputs = {str(path.resolve()): sha(path) for path in files}
    (B / 'inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
    receipt = dict(passed=False, inputs=inputs, steps=[], guards=[], source_callgraph_exhaustive=True,
        renderer_reversed_exactly=True, candidate_implemented=False, target_io=False)
    started = time.monotonic(); child = None
    def interrupted(number, _frame):
        receipt['signal'] = number
        raise KeyboardInterrupt(number)
    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP): signal.signal(number, interrupted)
    def guard():
        c = int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))
        receipt['guards'].append(dict(epoch=time.time(), cpu_c=c, available_kib=available))
        assert c < 80 and available >= 524288 and time.monotonic() - started < 180
    try:
        flags = ['g++', '-std=c++17', '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-pedantic',
            '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', '-I' + str(sdk)]
        commands = [('compile', flags + [str(B / 'count_spans.cpp'), str(B / 'production/wolf3d_world_mirror.cpp'), '-o', str(B / 'census')]),
                    ('count', [str(B / 'census'), str(B / 'poses.csv')])]
        for name, argv in commands:
            subprocess.run([str(D / '.venv/bin/python'), str(D / 'cross-agent/pi5-workloads/pi5_lease.py'),
                'assert-owner', '--owner', 'wolf3dorig', '--lease', lease], check=True, stdout=subprocess.DEVNULL)
            guard(); step = time.monotonic()
            with (B / (name + '.log')).open('x') as log:
                child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                while child.poll() is None: guard(); time.sleep(.25)
            receipt['steps'].append(dict(name=name, argv=argv, returncode=child.returncode, seconds=time.monotonic()-step))
            assert child.returncode == 0, name
            child = None
        receipt['counts'] = json.loads((B / 'count.log').read_text())
        receipt['passed'] = True
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired: os.killpg(child.pid, signal.SIGKILL); child.wait()
        receipt['owned_children_joined'] = True
        receipt['seconds'] = time.monotonic()-started
        (B / 'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt['counts']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--lease', required=True)
    main(parser.parse_args().lease)
