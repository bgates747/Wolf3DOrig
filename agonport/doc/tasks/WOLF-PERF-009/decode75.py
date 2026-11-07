"""File-only original/candidate comparison; refuse incomplete physical suites."""
from pathlib import Path
import argparse
import hashlib
import json
import statistics
import struct

T = Path(__file__).resolve().parent
OUT = T / 'build/hardware01/evidence'
ARMS = {'original': (3, 6), 'candidate': (4, 5)}
EXPECTED = {'original':'c8f99354bef6495e76f15201e64bdd010da6369a0b91d2fed37c0a3eb27f997d',
            'candidate':'a926b48ab3207b59773cc8283d59cc687f274ef2af00017451567449a4c69656'}


def decode_run(path):
    """Recheck raw record identity/counter bounds independently of saved CSV."""
    path = Path(path)
    timing = (path / 'timing.bin').read_bytes()
    native = (path / 'native.bin').read_bytes()
    u24 = lambda b: int.from_bytes(b, 'little')
    assert len(timing) == 16233 and timing[:8] == b'WPF3\1\2\1\1'
    assert timing[29:33] == bytes([34,36,0,2])
    count, ps, pe, ms, me, empty, nsize = [u24(timing[8+i*3:11+i*3]) for i in range(7)]
    assert count == 600 and 0 < pe-ps < 3600000 and 0 < me-ms
    assert len(native) == nsize == 12016
    magic, version, ncount, prid = struct.unpack_from('<4I',native)
    assert (magic,version,ncount) == (0x314e5057,1,600)
    rows = []
    for i in range(count):
        fields = [u24(timing[33+i*27+k*3:36+i*27+k*3]) for k in range(9)]
        step, angle, *stamps, size = fields
        idx, nangle, render, scope, command = struct.unpack_from('<5I',native,16+i*20)
        assert step == i+1 and angle == (720*step//600)%360 and nangle == angle and idx == i and size == 28
        assert stamps == sorted(stamps) and 0 < stamps[-1]-stamps[0] < 8000
        assert 0 < render <= scope <= command < 0x80000000
        rows.append(dict(step=step,angle=angle,draw_ccount=render,scope_ccount=scope,command_ccount=command))
    return dict(rows=rows,prt_ticks=pe-ps,mos_ticks=me-ms,raw_prid=prid,
                hashes={n:hashlib.sha256((path/n).read_bytes()).hexdigest() for n in ('timing.bin','native.bin')})


def summarize(values):
    values = sorted(values)
    return dict(count=len(values),mean=statistics.mean(values),median=statistics.median(values),
                minimum=values[0],maximum=values[-1],p95=values[(95*len(values)+99)//100-1])


def compare(root):
    root = Path(root)
    completed = json.loads((root/'complete.json').read_text())
    assert completed == dict(passed=True,guests=6,resource_probes=7,restored=True)
    kit = json.loads((root.parent/'kit.json').read_text())
    for i,arm,mode in ((1,'original','control'),(2,'candidate','control'),(3,'original','unpaced'),(4,'candidate','unpaced'),(5,'candidate','unpaced'),(6,'original','unpaced')):
        saved = json.loads((root/f'{i:02d}-vdplet-{mode}'/'guest-binding.json').read_text())
        assert saved == dict(arm=arm, **kit['guests'][arm][mode])
        assert saved['module_sha256'] == EXPECTED[arm]
    assert json.loads((root/'flash-restore/receipt.json').read_text())['passed']
    assert all(json.loads(p.read_text())['passed'] for p in root.glob('probe-*/receipt.json'))
    assert len(list(root.glob('probe-*/receipt.json'))) == 7
    for i,arm in ((1,'original'),(2,'candidate')):
        folder = root/f'{i:02d}-vdplet-control'
        assert json.loads((folder/'receipt.json').read_text())['passed']
        assert json.loads((folder/'arm.json').read_text()) == dict(arm=arm,module_sha256=EXPECTED[arm])
    groups = {}
    for arm, indices in ARMS.items():
        runs = []
        for i in indices:
            folder = root/f'{i:02d}-vdplet-unpaced'
            assert json.loads((folder/'receipt.json').read_text())['passed']
            assert json.loads((folder/'arm.json').read_text()) == dict(arm=arm,module_sha256=EXPECTED[arm])
            runs.append(decode_run(folder))
        groups[arm] = runs
    assert len({run['raw_prid'] for runs in groups.values() for run in runs}) == 1
    result = dict(schema='wolf-perf009-wall-column-comparison-v1',arms={},paired={},
                  limits='Completed frozen fixture only. Raw CCOUNT includes preemption/service waits;240MHz conversion and PRT/MOS rates nominal, no external clock/optical calibration. Repeated/scripted samples are correlated; no statistical independence or universal FPS claim. No default adoption.')
    for arm,runs in groups.items():
        rows = [row for run in runs for row in run['rows']]
        summary = {key:summarize([r[key] for r in rows]) for key in ('draw_ccount','scope_ccount','command_ccount')}
        result['arms'][arm] = dict(module_sha256=EXPECTED[arm],samples=len(rows),raw_prid=runs[0]['raw_prid'],
            counters=summary,nominal_ms={k:v['mean']/240000 for k,v in summary.items()},
            completed_fps_prt_nominal=len(rows)*1000/sum(r['prt_ticks'] for r in runs),
            completed_fps_mos_nominal=len(rows)*120/sum(r['mos_ticks'] for r in runs),
            runs=[{k:v for k,v in run.items() if k!='rows'} for run in runs])
    for pair,(original,candidate) in enumerate(zip(groups['original'],groups['candidate']),1):
        assert [(r['step'],r['angle']) for r in original['rows']] == [(r['step'],r['angle']) for r in candidate['rows']]
        result['paired'][str(pair)] = {key:summarize([a[key]-b[key] for a,b in zip(original['rows'],candidate['rows'])]) for key in ('draw_ccount','scope_ccount','command_ccount')}
    a = result['arms']['original']['counters']['draw_ccount']['mean']
    b = result['arms']['candidate']['counters']['draw_ccount']['mean']
    result['mean_draw_reduction_percent'] = 100*(a-b)/a
    result['mean_draw_saved_nominal_ms'] = (a-b)/240000
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('directory',nargs='?',type=Path,default=OUT)
    print(json.dumps(compare(parser.parse_args().directory),indent=2))
