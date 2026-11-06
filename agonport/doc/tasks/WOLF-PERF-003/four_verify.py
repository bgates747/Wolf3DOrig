"""Offline checks on retrieved four-way results. No emulator or device access."""
from pathlib import Path
import hashlib
import json
from wire_check import check

base = Path(__file__).resolve().parent / 'build/four01'
root = base / 'evidence'
manifest = json.loads((root / 'retrieval-manifest.json').read_text())
for name, digest in manifest.items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
trials = json.loads((base / 'controller-results.json').read_text())['trials']
rows = []
for trial in trials:
    profile = root / Path(trial['profile']).name
    result = json.loads((profile / 'run' / ('result.json' if trial['emulator'] == 'fab' else 'runner.json')).read_text())
    assert bool(result['success']) == trial['success']
    guards = json.loads((profile / 'run/host-guards.json').read_text())
    temperatures = [temperature for row in guards for temperature in row.get('cpu_c', [])]
    assert temperatures and max(temperatures) < 80
    row = {**trial, 'peak_cpu_c': max(temperatures)}
    if trial['success']:
        assert result['returncode'] == 0
        raw = (profile / 'run/timing.bin').read_bytes()
        assert len(raw) == 16233 and raw[:5] == b'WPF3\1' and raw[5:8] == b'\3\1\1'
        count = int.from_bytes(raw[8:11], 'little')
        assert raw[29:32] == bytes([34, 36, 0]) and raw[32] == (1 if trial['backend'] == 'bespoke' else 2)
        assert 0 < count <= 600
        previous = 0
        for i in range(count):
            values = [int.from_bytes(raw[33+i*27+k*3:36+i*27+k*3], 'little') for k in range(9)]
            step, angle, *rest = values
            assert previous < step <= 600 and angle == (720*step//600) % 360
            assert rest[:-1] == sorted(rest[:-1])
            previous = step
        assert previous == 600 and not any(raw[33+count*27:])
        row['completed_records'] = count
        if trial['emulator'] == 'flexe':
            row['wire'] = check(profile)
            stats = result['stats']
            assert not stats['failed'] and not any(stats.get(k, 0) for k in ('unhandled', 'unregistered', 'unmapped'))
        else:
            assert count == 600
            if trial['backend'] == 'vdplet':
                bridge = result['bridge']
                assert bridge['loads'] == bridge['unloads'] == 1 and bridge['renders'] == 602
                assert not any(bridge[k] for k in ('errors', 'residual_cleanup', 'loaded', 'busy', 'frame'))
    rows.append(row)
for backend in ('bespoke', 'vdplet'):
    selected = [r for r in rows if r['emulator'] == 'flexe' and r['backend'] == backend]
    assert len(selected) == (5 if selected[0]['success'] else 2)
report = {'retrieval_hashes_verified': len(manifest), 'trials': rows}
(base / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
