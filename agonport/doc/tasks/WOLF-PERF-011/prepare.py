"""One task-private physical paced producer; optimized module bytes unchanged."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

T = Path(__file__).resolve().parent
Q = T.parent / 'WOLF-PERF-009'
B = T / 'build/guest01'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    for p, digest in json.loads((T / 'SOURCE-PINS.json').read_text()).items():
        assert sha(p) == digest, p
    before = Q / 'build/guests01/candidate/unpaced/source'
    src = B / 'source'
    shutil.copytree(before, src, ignore=shutil.ignore_patterns('*.bin', '*.lst', '*.log'))
    donor = T.parent / 'WOLF-PERF-003/build/hardware05/vdplet/paced/source/bench.inc'
    old = (before / 'bench.inc').read_text()
    new = donor.read_text()
    # The proven physical paced method changes only pace selection and presentation.
    diff = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True)))
    assert diff.count('@@') == 6 and new.count('call w3d_vdu_present') == 2
    (B / 'paced-method.diff').write_text(diff)
    (src / 'bench.inc').write_text(new)
    p = src / 'wolf3d.asm'
    s = p.read_text()
    assert s.count('WP_MODE: equ 2') == 1
    p.write_text(s.replace('WP_MODE: equ 2', 'WP_MODE: equ 3', 1))
    p = src / 'loading_pages.inc'
    s = p.read_text()
    assert s.count('Rotation starts after loading.') == 1
    p.write_text(s.replace('Rotation starts after loading.', 'VISIBLE ROTATION - TWO TURNS IN 20 SECONDS'))
    module = Q / 'build/r01/candidate/module/wolf_perf.vdpl'
    assert sha(module) == 'a926b48ab3207b59773cc8283d59cc687f274ef2af00017451567449a4c69656'
    record = dict(source=str(src), guest=str(src/'wolf3d.bin'), listing=str(src/'wolf3d.lst'),
                  module=str(module), module_sha256=sha(module), package_bytes=24420,
                  package_limit=24421, remote_name='rotate.bin')
    (B/'binding.json').write_text(json.dumps(record, indent=2)+'\n')
    files = [p for p in B.rglob('*') if p.is_file()] + [p for p in T.iterdir() if p.is_file()]
    (B/'inputs.json').write_text(json.dumps({str(p):sha(p) for p in files}, indent=2)+'\n')


if __name__ == '__main__':
    main()
