"""One serial assembly plus actual package and per-frame presentation checks."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re
import signal
import subprocess
import time

T = Path(__file__).resolve().parent
B = T/'build/guest01'
D = Path('/Agon/mystuff/agon-dev-env')
ASM = T.parents[3]/'src/asm/wolf3d/tgt/.tools/ez80asm'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(lease):
    result = dict(passed=False, guards=[])
    child = None
    begin = time.monotonic()
    def guard():
        cpu = int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
        mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))
        result['guards'].append(dict(cpu_c=cpu, available_kib=mem))
        assert cpu < 80 and mem >= 524288 and time.monotonic()-begin < 120
    try:
        for p, digest in json.loads((B/'inputs.json').read_text()).items():
            assert sha(p) == digest, p
        subprocess.run([str(D/'.venv/bin/python'), str(D/'cross-agent/pi5-workloads/pi5_lease.py'),
                        'assert-owner','--owner','wolf3dorig','--lease',lease], check=True, stdout=subprocess.DEVNULL)
        guard()
        with (B/'assembly.log').open('x') as log:
            child = subprocess.Popen([str(ASM),'wolf3d.asm','wolf3d.bin','-l','-c'], cwd=B/'source',
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            while child.poll() is None:
                guard(); time.sleep(.1)
        assert child.returncode == 0
        spec = importlib.util.spec_from_file_location('binding', T.parent/'WOLF-PERF-009/guest_binding.py')
        binding = importlib.util.module_from_spec(spec); spec.loader.exec_module(binding)
        result['producer'] = binding.verify(json.loads((B/'binding.json').read_text()))
        listing = (B/'source/wolf3d.lst').read_text()
        binary = (B/'source/wolf3d.bin').read_bytes()
        labels = {}
        for name in ('wp_next','wp_prt_stop','w3d_vdu_present','w3d_audio_wait_for_vdp_ingress','wp_run'):
            m = re.search(r'^([0-9A-F]{6})[^\n]*\b'+name+r':', listing, re.M)
            assert m, name
            labels[name] = int(m[1], 16)
        calls = []
        pattern = r'^([0-9A-F]{6}) ((?:[0-9A-F]{2} ){3}[0-9A-F]{2})\s+\d+\*?\s+call (w3d_vdu_present|w3d_audio_wait_for_vdp_ingress)\b'
        for m in re.finditer(pattern, listing, re.M):
            at = int(m[1],16)
            if not labels['wp_next'] <= at < labels['wp_next']+700:
                continue
            actual = binary[at-0x40000:at-0x40000+4]
            assert actual == bytes.fromhex(m[2]) == bytes([0xcd])+labels[m[3]].to_bytes(3,'little')
            calls.append(dict(address=at, target=m[3]))
        bench = (B/'source/bench.inc').read_text()
        loop = bench.split('wp_next:',1)[1].split('call wp_prt_stop',1)[0]
        assert loop.count('call w3d_vdu_present') == 1
        assert re.search(r'call w3d_vdu_present\s*;[^\n]*\n\s*call w3d_audio_wait_for_vdp_ingress\s*\n\s*jp c,wp_failed',loop)
        assert loop.index('call w3d_vdplet_wait_run') < loop.index('call w3d_vdu_present') < loop.index('ld (ix+21),hl') < loop.index('jp c,wp_next')
        assert {x['target'] for x in calls} == {'w3d_vdu_present','w3d_audio_wait_for_vdp_ingress'}
        result.update(passed=True, actual_presentation_calls=calls, labels=labels,
                      guest_bytes=len(binary), bench_sha256=sha(B/'source/bench.inc'),
                      mode=3, latest_renderer_unchanged=True)
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired: os.killpg(child.pid,signal.SIGKILL); child.wait()
        result['seconds'] = time.monotonic()-begin
        (B/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--lease',required=True)
    main(p.parse_args().lease)
