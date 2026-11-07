"""Preserve a qualified hardware02 kit before dispatch; file-only, one-shot."""
from pathlib import Path
import hashlib
import json
import shutil
import hardware02 as hardware
import bootstrap

T = Path(__file__).resolve().parent
B = T / 'build/hardware02'
R = T / 'results/hardware02-preparation'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (B / 'evidence').exists(), 'Archive before constructor/target dispatch'
    kit = json.loads((B / 'kit.json').read_text())
    hardware.verify_kit(kit)
    assert kit['request'] == '0d70a117969f'
    assert kit['remote'] == '/test/wolf/perf023/r02'
    assert not R.exists(), 'Never overwrite a frozen preparation'
    R.mkdir()
    for p in B.iterdir():
        if p.is_file():
            shutil.copyfile(p, R / p.name)
    archive = R / 'frozen-inputs'
    archive.mkdir()
    saved = {}
    for name, digest in kit['inputs'].items():
        data = Path(name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, name
        snapshot = archive / digest
        if not snapshot.exists():
            snapshot.write_bytes(data)
        saved[name] = dict(sha256=digest, bytes=len(data), snapshot=str(snapshot))
    (archive / 'index.json').write_text(json.dumps(saved, indent=2) + '\n')
    result = dict(passed=True, target_access=False, request=kit['request'],
        kit_sha256=sha(B / 'kit.json'), inputs=len(saved),
        distinct_bytes=len({v['sha256'] for v in saved.values()}),
        stage_files=len(kit['stage']), explicit_bootstrap_closure=bootstrap.verify_closure(kit),
        original_failed97_kit_unchanged=sha(T / 'results/actual97/kit.json') ==
            '1b4d2dd929827cdf00f9fa7aef4b1da3ebbfc5b3e665642db263eb8ea900d143',
        limits='Frozen preparation only; no grant, target execution or physical performance result.')
    assert result['original_failed97_kit_unchanged']
    (R / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
    (R / 'SHA256.json').write_text(json.dumps({str(p.relative_to(R)):
        dict(bytes=p.stat().st_size, sha256=sha(p)) for p in R.rglob('*')
        if p.is_file() and p != R / 'SHA256.json'}, indent=2) + '\n')
    for name, record in json.loads((R / 'SHA256.json').read_text()).items():
        assert sha(R / name) == record['sha256'], name
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
