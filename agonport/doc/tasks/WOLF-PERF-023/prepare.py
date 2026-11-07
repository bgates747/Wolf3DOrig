"""Isolate exact combined021 control; change only the supported native span."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

T = Path(__file__).resolve().parent
B = T / 'build/r01'
BASE = T.parent / 'WOLF-PERF-021/build/r01/candidate'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not B.exists(), 'Preserve prior selections; use a new revision'
    pins = json.loads((T / 'PRE-CODE-PINS.json').read_text())
    for path, digest in pins.items(): assert sha(path) == digest, path
    assert sha(BASE / 'module/wolf_perf.vdpl') == '8d3d19bb74e1f2ea862b2154c038dfd23de2fd741fd1831d1880d849b5ad838b'
    census = json.loads((T / 'build/census02/receipt.json').read_text())
    assert census['passed'] and census['counts']['eligible_bytes'] == 46080000
    assert not census['candidate_implemented'] and not census['target_io']
    advice = T / 'results/source01/WOLF-ALIGNED-BYTE-SPAN-ADVICE-2026-11-07.md'
    assert advice.is_file()
    prior = json.loads((T.parent / 'WOLF-PERF-022/build/hardware02/kit.json').read_text())
    insertion = '''    // Complete four-byte groups are permuted onto the same distinct bytes.
    // All span/row order and one masked byte read/store per address remain.
    if (pixel_xor <= 3u && ((mapped_x | count) & 3u) == 0 &&
        count <= UINT32_MAX - mapped_x) {
        uint8_t *pixel = row + mapped_x;
        while (count-- != 0) {
            *pixel = static_cast<uint8_t>((*pixel & preserve_mask) | color_bits);
            ++pixel;
        }
        return;
    }
'''
    needle = '''    const uint8_t color_bits = static_cast<uint8_t>(color & target.color_mask);
    while (count-- != 0) {'''
    B.mkdir(parents=True)
    changes = []
    records = {}
    for arm in ('original', 'candidate'):
        root = B / arm; root.mkdir()
        for folder in ('production', 'native-source', 'qualification', 'sdk'):
            for source in (BASE / folder).rglob('*'):
                if source.is_file() and '__pycache__' not in source.parts:
                    assert sha(source) == prior['inputs'][str(source)], source
            shutil.copytree(BASE / folder, root / folder, ignore=shutil.ignore_patterns('__pycache__'))
        assert sha(BASE / 'wolf3d_tables.inc') == prior['inputs'][str(BASE / 'wolf3d_tables.inc')]
        shutil.copyfile(BASE / 'wolf3d_tables.inc', root / 'wolf3d_tables.inc')
        if arm == 'candidate':
            for folder in ('production', 'native-source'):
                target = root / folder / 'wolf3d_renderer.cpp'
                old = target.read_text()
                assert old.count(needle) == 1
                new = old.replace(needle, needle.replace('    while', insertion + '    while'), 1)
                assert new.replace(insertion, '', 1) == old
                # The zero return and whole linear branch precede this insertion.
                assert new.index('if (count == 0) return;') < new.index(insertion)
                assert old[:old.index(needle)] == new[:new.index(needle.splitlines()[0])]
                target.write_text(new)
                changes.append(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                    fromfile='original/' + folder + '/wolf3d_renderer.cpp', tofile='candidate/' + folder + '/wolf3d_renderer.cpp')))
                records[folder] = dict(original_sha256=hashlib.sha256(old.encode()).hexdigest(),
                    candidate_sha256=sha(target), inverse_exact=True, count0_linear_unchanged=True)
    for folder in ('production', 'native-source'):
        assert (B / 'original' / folder / 'wolf3d_module.cpp').read_bytes() == (B / 'candidate' / folder / 'wolf3d_module.cpp').read_bytes()
    assert (B / 'candidate/production/wolf3d_renderer.cpp').read_bytes() == (B / 'candidate/native-source/wolf3d_renderer.cpp').read_bytes()
    (T / 'candidate.patch').write_text('\n'.join(changes))
    (B / 'source-binding.json').write_text(json.dumps(dict(passed=True, units=records,
        only_span_insertion=True, helpers_modules_tables_sdk_unchanged=True, candidate_qualified=False,
        actual_control_package=sha(BASE / 'module/wolf_perf.vdpl')), indent=2) + '\n')
    files = [p for p in B.rglob('*') if p.is_file()] + [p for p in T.iterdir() if p.is_file()]
    (B / 'inputs.json').write_text(json.dumps(dict(contract='ab94798+a630c8c',
        inputs={str(p.resolve()): sha(p) for p in files}), indent=2) + '\n')
    print(json.dumps(dict(passed=True, isolated_files=len(files), compiler_or_target=False)))


if __name__ == '__main__':
    main()
