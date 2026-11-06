"""Oryx: archive stopped four-way trial evidence, without modifying profiles."""
from pathlib import Path
import hashlib
import json
import tarfile

root = Path.home() / 'Agon/mystuff/Wolf3dOrig/.emulator/wolf-four01'
files = {root / 'profiles.json'}
for record in json.loads((root / 'profiles.json').read_text()):
    profile = Path(record['profile'])
    if not (profile / 'run').exists():
        continue
    assert any((profile / 'run' / n).exists() for n in ('result.json', 'runner.json')), profile
    for directory in ('run', 'last-run'):
        files.update(p for p in (profile / directory).rglob('*') if p.is_file())
    files.update(profile / n for n in ('inputs.json', '.runtime.sha256'))
    for name in ('timing.bin', 'native.bin', 'before.bin', 'after.bin', 'loading-state.bin'):
        path = profile / 'sdcard/wolf3d' / name
        if path.exists():
            files.add(path)
manifest = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(files)}
receipt = root / 'retrieval-manifest.json'
receipt.write_text(json.dumps(manifest, indent=2) + '\n')
archive = Path('/tmp/wolf-four01-results.tar.gz')
with tarfile.open(archive, 'w:gz') as output:
    for path in sorted(files | {receipt}):
        output.add(path, arcname=str(path.relative_to(root)), recursive=False)
print(json.dumps({'files': len(files), 'archive': str(archive),
                  'bytes': archive.stat().st_size,
                  'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}, indent=2))
