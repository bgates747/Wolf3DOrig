"""Four serial real guest assemblies; unchanged timed binaries are a hard gate."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
import caption

T = Path(__file__).resolve().parent
B = T / 'build/r02'
Q = T.parent / 'WOLF-PERF-009'
D = Path('/Agon/mystuff/agon-dev-env')
ASM = T.parents[3] / 'src/asm/wolf3d/tgt/.tools/ez80asm'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(lease):
    for name, digest in json.loads((B / 'inputs.json').read_text()).items():
        assert sha(name) == digest, name
    assert not (B / 'receipt.json').exists(), 'Preserve prior attempt'
    start = time.monotonic()
    receipt = dict(passed=False, steps=[], guards=[], bindings={}, unchanged_timed={})
    child = None

    def interrupted(signum, _frame):
        receipt['signal'] = dict(number=signum, epoch=time.time())
        raise KeyboardInterrupt(signum)

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, interrupted)

    def guard():
        c = int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000
        mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))
        receipt['guards'].append(dict(epoch=time.time(), cpu_c=c, available_kib=mem))
        assert c < 80 and mem >= 524288 and time.monotonic() - start < 600

    try:
        spec = importlib.util.spec_from_file_location('actual_binding', Q / 'guest_binding.py')
        binding = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(binding)
        originals = json.loads((Q / 'build/guests01/bindings.json').read_text())
        for arm in ('original', 'candidate'):
            receipt['bindings'][arm] = {}
            for mode in ('control', 'unpaced'):
                subprocess.run([str(D / '.venv/bin/python'), str(D / 'cross-agent/pi5-workloads/pi5_lease.py'),
                    'assert-owner', '--owner', 'wolf3dorig', '--lease', lease], check=True, stdout=subprocess.DEVNULL)
                guard()
                src = B / arm / mode / 'source'
                before = time.monotonic()
                with (B / f'{arm}-{mode}.log').open('x') as log:
                    child = subprocess.Popen([str(ASM),'wolf3d.asm','wolf3d.bin','-l','-c'], cwd=src,
                        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    while child.poll() is None:
                        guard()
                        assert time.monotonic() - before < 120
                        time.sleep(.1)
                receipt['steps'].append(dict(arm=arm,mode=mode,returncode=child.returncode,seconds=time.monotonic()-before))
                assert child.returncode == 0
                child = None
                selected = dict(originals[arm][mode], source=str(src), guest=str(src/'wolf3d.bin'), listing=str(src/'wolf3d.lst'))
                receipt['bindings'][arm][mode] = binding.verify(selected)
                baseline = Path(originals[arm][mode]['source'])
                assert (src/'bench.inc').read_bytes() == (baseline/'bench.inc').read_bytes(), 'Timer/renderer logic changed'
                if mode == 'unpaced':
                    assert (src/'wolf3d.bin').read_bytes() == Path(originals[arm][mode]['guest']).read_bytes(), 'Timed guest must remain byte identical'
                    receipt['unchanged_timed'][arm] = sha(src/'wolf3d.bin')
                else:
                    raw = (src/'wolf3d.bin').read_bytes()
                    assert raw.count(caption.pixels()) == 1
                    assert b'NO ROTATION EXPECTED - TIMER ABORT CHECK\0' in raw
                    assert b'Rotation starts after loading.\0' not in raw
                    assert bytes([23,0,0xca]) in raw
                    assert bytes([23,27,0x20,0xb0,0xf1,23,27,3,caption.X,0,caption.Y,0]) in raw
        assert 180 <= caption.Y and caption.Y + caption.HEIGHT <= 200
        assert 0 <= caption.X and caption.X + caption.WIDTH <= 320
        receipt['caption'] = dict(text=caption.TEXT,width=caption.WIDTH,height=caption.HEIGHT,
            x=caption.X,y=caption.Y,buffer_id=caption.BUFFER,bytes=len(caption.pixels()),sha256=hashlib.sha256(caption.pixels()).hexdigest())
        receipt['passed'] = True
        print('PASS four actual assemblies/24 bound package operands; both unpaced binaries unchanged; caption payload, layout and static-only hint verified')
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        receipt['seconds'] = time.monotonic() - start
        (B / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--lease', required=True)
    main(p.parse_args().lease)
