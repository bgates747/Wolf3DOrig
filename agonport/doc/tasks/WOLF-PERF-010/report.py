"""Offline audit of the retained run; never relabel its failed controller result."""
from pathlib import Path
import hashlib
import json
from PIL import Image
import caption

T = Path(__file__).resolve().parent
B = T / 'build/visual02'
R = B / 'oryx-result'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    build = json.loads((T / 'build/r02/receipt.json').read_text())
    assert build['passed'] and len(build['unchanged_timed']) == 2
    for name, digest in json.loads((B / 'dispatch.json').read_text()).items():
        assert sha(B / name) == digest, name
    assert sha(B / 'run_visual.py') == sha(T / 'run_visual.py')
    actual = json.loads((R / 'inputs.json').read_text())
    for p in (B / 'payload').rglob('*'):
        if p.is_file():
            assert actual['sdcard/wolf3d/' + str(p.relative_to(B / 'payload'))] == sha(p)
    for n in ('vdp_wolf_fab.so', 'input.so'):
        assert actual[n] == sha(B / n)
    run = json.loads((R / 'run/result.json').read_text())
    assert run['passed'] is False and run['returncode'] == 0
    assert run['error'] == "RuntimeError('Unexpected frontend exit')"
    assert not (R / 'sdcard/wolf3d/loading3.bin').exists()
    bridge = run['bridge']
    assert (bridge['loads'], bridge['unloads'], bridge['renders'], bridge['errors'],
            bridge['residual_cleanup']) == (1, 1, 0, 0, 0)
    assert not any(bridge[k] for k in ('loaded', 'busy', 'frame'))
    expected = b''.join(bytes([255] * 3) if x == 0xff else bytes(3)
                        for x in caption.pixels())
    frames = []
    missing = []
    for c in run['captures']:
        p = R / 'run' / c['file']
        if not p.exists():
            missing.append(c)
            continue
        im = Image.open(p).convert('RGB')
        matches = im.size == (320, 240) and im.crop((11, 183, 309, 197)).tobytes() == expected
        frames.append(dict(c, size=list(im.size), caption_exact=matches, sha256=sha(p)))
    assert missing == [run['captures'][-1]], 'Only final queued capture may be absent after quit'
    held = [f for f in frames if 10 <= int(f['file'][6:10]) <= 23]
    assert len(held) == 14 and all(f['caption_exact'] for f in held)
    assert len({f['sha256'] for f in held}) == 1
    assert held[-1]['seconds'] - held[0]['seconds'] > 3.8
    guards = json.loads((R / 'run/guards.json').read_text())
    assert all(len(g['cpu_c']) == 1 and g['cpu_c'][0] < 80 and
               g['available_kib'] >= 524288 for g in guards)
    # Normal MOS return is an explicit visual observation, not an invented file marker.
    owner = json.loads((R / 'run/owner-quit.json').read_text())
    assert owner['normal_guest_return_visually_observed']
    assert next(f for f in frames if f['file'] == 'frame-0300.ppm')['size'] == [640, 480]
    for frame, output in [('frame-0010.ppm', 'CAPTION.png'), ('frame-0300.ppm', 'RETURN.png')]:
        Image.open(R / 'run' / frame).save(T / output)
    result = dict(
        caption_pixel_check_passed=True, original_controller_passed=False,
        completion_disposition='Owner observed normal MOS return, then requested ordinary quit; frontend returned0. Wrong loading3.bin predicate preserved.',
        scope='Fab native-source bridge display only; no Xtensa execution, physical timer, hardware caption or performance qualification.',
        assembly_passed=build['passed'], unchanged_timed=build['unchanged_timed'],
        caption=build['caption'], captures=len(frames), missing_final_queued_capture=missing,
        exact_caption_captures=sum(f['caption_exact'] for f in frames),
        held_page_interval=dict(first=held[0], last=held[-1], captures=len(held),
            interpretation='Two source-selected two-second holds separated by explicit present; capture pixels cannot independently identify buffer numbers.'),
        bridge=bridge, normal_return_frame='frame-0300.ppm',
        peak_cpu_c=max(g['cpu_c'][0] for g in guards),
        retrieved_archive_sha256='afc11cdd07ab78ff9abbcfbea540459d2c90496bd4b225cd10b304b1a79e2144',
        records=frames)
    (T / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}, indent=2))


if __name__ == '__main__':
    main()
