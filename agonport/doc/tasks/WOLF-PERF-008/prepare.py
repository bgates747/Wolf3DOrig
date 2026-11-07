"""File-only provider arm; never edit the frozen original source or SDK."""
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
    pins = json.loads((T / 'SOURCE-PINS.json').read_text())
    for name, digest in pins['files'].items():
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
                p = a / folder / 'wolf3d_module.cpp'
                old = p.read_text()
                start = old.index('union WideWords {')
                end = old.index('\n#endif', start)
                assert old[start:end].count('extern "C"') == 2
                new = old[:start] + old[end:]
                p.write_text(new)
                changes.append(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                    fromfile='original/' + folder, tofile='candidate/' + folder)))
    (B / 'provider.patch').write_text('\n'.join(changes))
    files = [p for p in B.rglob('*') if p.is_file()]
    files += [T / n for n in ('PLAN.md', 'PRE-CODE.md', 'SOURCE-PINS.json', 'prepare.py', 'build.py', 'target_compile.py')]
    (B / 'inputs.json').write_text(json.dumps({'contract': '80a36c4', 'inputs': {str(p): sha(p) for p in files}}, indent=2) + '\n')
    print('Prepared unchanged c8f control and existing-math provider arm; no compile or target access.')


if __name__ == '__main__':
    main()
