"""File-only wall sampler hoisting from exact original-ray c8f control."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

T = Path(__file__).resolve().parent
B = T / 'build/r01'
BASE = T.parent / 'WOLF-PERF-007/build/r01/candidate'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    for name, digest in json.loads((T / 'SOURCE-PINS.json').read_text())['files'].items():
        assert sha(name) == digest, name
    B.mkdir(parents=True, exist_ok=False)
    changes = []
    for arm in ('original', 'candidate'):
        a = B / arm
        a.mkdir()
        for name in ('native-source', 'production', 'qualification', 'sdk'):
            shutil.copytree(BASE / name, a / name, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(BASE / 'wolf3d_tables.inc', a / 'wolf3d_tables.inc')
        if arm == 'candidate':
            for folder in ('native-source', 'production'):
                p = a / folder / 'wolf3d_renderer.cpp'
                old = p.read_text()
                new = old.replace('RenderDetail draw_walls(', (T / 'wall_column.inc').read_text() + '\nRenderDetail draw_walls(', 1)
                start = new.index('            int32_t fraction = step * (clipped_top - top);')
                end = new.index('\n        }\n        detail = release_asset', start)
                new = new[:start] + '''            draw_wall_column(frame, static_cast<uint32_t>(kViewX + col),
                             static_cast<uint32_t>(kViewY + clipped_top),
                             destination_height, span.bytes, tex_u[col],
                             step * (clipped_top - top), step);''' + new[end:]
                p.write_text(new)
                changes.append(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile='original/' + folder, tofile='candidate/' + folder)))
    assert (B / 'candidate/production/wolf3d_renderer.cpp').read_bytes() == (B / 'candidate/native-source/wolf3d_renderer.cpp').read_bytes()
    (B / 'renderer.patch').write_text('\n'.join(changes))
    files = [p for p in B.rglob('*') if p.is_file()]
    files += [p for p in T.iterdir() if p.is_file()]
    files += [T.parent / 'WOLF-PERF-007' / n for n in ('test_equivalence.cpp', 'test_spans.cpp')]
    (B / 'inputs.json').write_text(json.dumps({'contract': 'c0f2245', 'inputs': {str(p): sha(p) for p in files}}, indent=2) + '\n')


if __name__ == '__main__':
    main()
