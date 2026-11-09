"""File-only release verification; never builds, executes firmware or contacts a device."""
from pathlib import Path
import gzip
import hashlib
import json
import subprocess
import zipfile

TASK = Path(__file__).resolve().parent
RELEASES = TASK / 'build/releases'
VDPLET = Path('/Agon/mystuff/agon-vdplet')
EMOS = Path('/Agon/mystuff/agon-extender')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sums(text):
    entries = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        value, name = line.split(maxsplit=1)
        name = name.lstrip('*')
        assert len(value) == 64 and name not in entries
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        entries[name] = value
    return entries


def verify():
    receipts = {}
    for kind in ('vdplet', 'eirene'):
        metadata = json.loads((RELEASES / (kind + '-release.json')).read_text())
        assets = {}
        for asset in metadata['assets']:
            path = RELEASES / kind / asset['name']
            data = path.read_bytes()
            value = digest(data)
            assert len(data) == asset['size']
            assert asset['digest'] == 'sha256:' + value
            assets[path.name] = dict(bytes=len(data), sha256=value,
                                     asset_id=asset['id'])
        receipts[kind] = dict(tag=metadata['tag_name'], url=metadata['html_url'],
                              release_id=metadata['id'], assets=assets)

    vdp = RELEASES / 'vdplet'
    checks = sums((vdp / 'SHA256SUMS').read_text())
    assert len(checks) == 9
    for name, expected in checks.items():
        assert digest((vdp / name).read_bytes()) == expected, name
    manifest = json.loads((vdp / 'release-manifest.json').read_text())
    assert manifest['tag'] == 'v0.1.2-alpha'
    assert manifest['features'] == dict(pixels=True, text_profile='text96',
        borrow_rows=True, read_bytes=True, uart_rx_repair=True,
        async_worker=False, counted_return=False, pcm_sink=False)
    for suffix in ('elf', 'map'):
        original = gzip.decompress((vdp / ('vdp-vdplet-0.1.2-alpha.' + suffix + '.gz')).read_bytes())
        record = manifest['original_artifacts']['firmware.' + suffix]
        assert len(original) == record['bytes'] and digest(original) == record['sha256']
        (vdp / ('firmware.' + suffix)).write_bytes(original)
    receipts['vdplet'].update(source_commit=manifest['source_commit'],
        checksum_entries_verified=len(checks), features=manifest['features'])

    # Verify the local release source against the published source-freeze,
    # using git object reads rather than an unpinned working tree.
    freeze = json.loads((vdp / 'source-freeze.json').read_text())
    export = TASK / 'build/vdplet-source'
    for name, expected in freeze.items():
        data = subprocess.run(['git', '-C', str(VDPLET), 'show',
            manifest['source_commit'] + ':' + name], check=True, capture_output=True).stdout
        assert digest(data) == expected, name
        destination = export / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    receipts['vdplet']['release_source_files_verified'] = len(freeze)
    source = json.loads((vdp / 'firmware-source.json').read_text())
    firmware_source = Path(source['source']) / 'video'
    exported = {}
    for name, expected in source['exported_headers'].items():
        path = firmware_source / name
        assert digest(path.read_bytes()) == expected, name
        exported[str(path)] = expected
    config = firmware_source / 'vdplet_build.h'
    assert digest(config.read_bytes()) == source['build_configuration_sha256']
    exported[str(config)] = digest(config.read_bytes())
    receipts['vdplet']['verified_exported_headers_and_configuration'] = exported

    edir = RELEASES / 'eirene'
    archive = edir / '3.1.0_uart0_rc_3.zip'
    outer = sums((edir / '3.1.0_uart0_rc_3.zip.sha256').read_text())
    assert digest(archive.read_bytes()) == outer[archive.name]
    with zipfile.ZipFile(archive) as z:
        entries = sums(z.read('SHA256SUMS').decode())
        for name, expected in entries.items():
            assert digest(z.read(name)) == expected, name
        data = z.read('mos-rc3.bin')
        assert len(data) == 100879
        assert digest(data) == 'd7a51147f3381cd68d56f3fbe4605434a897dfae1b049269afeba09ec2b7eb50'
        for name in z.namelist():
            path = Path(name)
            assert not path.is_absolute() and '..' not in path.parts
            if name.endswith('/'):
                continue
            target = edir / 'extracted' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(name))
    receipts['eirene'].update(source_commit='97311c437093e416342a6c836cf9914f2ced027d',
        member='mos-rc3.bin', bytes=len(data), sha256=digest(data),
        internal_checksum_entries_verified=len(entries))

    selector = EMOS / 'docs/olimex-firmware-standard.json'
    standard = json.loads(selector.read_text())
    assert standard['vdp']['sha256'] == receipts['vdplet']['assets']['vdp-vdplet-0.1.2-alpha.bin']['sha256']
    assert standard['vdp']['checksums_sha256'] == digest((vdp / 'SHA256SUMS').read_bytes())
    receipts['olimex_selector'] = dict(path=str(selector), sha256=digest(selector.read_bytes()),
        emos=standard['emos'], installed_state_claim=False)
    receipts['scope'] = 'Release/source/hash verification only; no build, loader execution, emulator, device or installed-state claim.'
    (TASK / 'RELEASE-VERIFICATION.json').write_text(json.dumps(receipts, indent=2) + '\n')
    return receipts


if __name__ == '__main__':
    result = verify()
    print(json.dumps(dict(vdplet_checksums=result['vdplet']['checksum_entries_verified'],
        release_sources=result['vdplet']['release_source_files_verified'],
        eirene_checksums=result['eirene']['internal_checksum_entries_verified'],
        firmware_verified=True)))
