"""Inventory retained candidates without building or executing them.

The package screen checks static header/ELF/resource requirements only. It is
not the runtime loader, a target allocation test or new execution qualification.
"""
from pathlib import Path
import hashlib
import json
import struct
import subprocess

TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[3]
sha = lambda b: hashlib.sha256(b).hexdigest()


def screen(raw):
    assert raw[:4] == b'VDPL' and len(raw) >= 64
    u16 = lambda n: struct.unpack_from('<H', raw, n)[0]
    u32 = lambda n: struct.unpack_from('<I', raw, n)[0]
    h = dict(version=u16(4), header_bytes=u16(6), package_bytes=u32(8),
        architecture=u32(12), abi_major=u16(16), abi_minor=u16(18),
        capabilities=u32(20), text_limit=u32(24), data_limit=u32(28),
        stack_limit=u32(32), build_id=u32(36), elf_offset=u32(40),
        elf_bytes=u32(44), compiler=u32(48))
    assert (h['version'], h['header_bytes'], h['package_bytes'], h['architecture']) == (1, 64, len(raw), 0x32505345)
    assert h['abi_major'] == 1 and h['abi_minor'] <= 6
    # Release: legacy v1.2 + pixels + colour rows, with lean PCM and no sink.
    assert h['capabilities'] & ~287 == 0
    assert 0 < h['text_limit'] <= 98304 and 0 < h['data_limit'] <= 16384
    assert h['stack_limit'] <= 2048 and len(raw) <= 131072
    assert h['compiler'] == 80400 and raw[52:64] == bytes(12)
    assert h['elf_offset'] == 64 and h['elf_bytes'] == len(raw) - 64
    elf = raw[64:]
    assert elf[:7] == b'\x7fELF\x01\x01\x01'
    assert struct.unpack_from('<HHI', elf, 16) == (3, 94, 1)
    offset = struct.unpack_from('<I', elf, 32)[0]
    entsize, count, names = struct.unpack_from('<HHH', elf, 46)
    assert entsize == 40 and 0 < count <= 32 and names < count
    sections = [struct.unpack_from('<10I', elf, offset + 40*i) for i in range(count)]
    ns = sections[names]
    strings = elf[ns[4]:ns[4]+ns[5]]
    text = data = 0
    allocated = []
    align = lambda n: (n+3) & ~3
    for s in sections:
        name = strings[s[0]:].split(b'\0', 1)[0].decode()
        if s[1] in (2, 11):
            assert s[9] == 16 and s[5] % 16 == 0
            for at in range(s[4]+16, s[4]+s[5], 16):
                assert struct.unpack_from('<H', elf, at+14)[0] != 0, 'undefined symbol'
        assert s[1] != 9, 'REL relocation'
        if s[1] == 4:
            assert s[9] == 12 and s[5] % 12 == 0
            for at in range(s[4], s[4]+s[5], 12):
                address, info, addend = struct.unpack_from('<3I', elf, at)
                assert address % 4 == 0 and info == 5 and addend == 0
        if not s[2] & 2 or not s[5]:
            continue
        if name in ('.hash', '.dynsym', '.dynstr', '.rela.dyn'):
            continue
        assert name in ('.text', '.rodata', '.data', '.bss', '.data.rel.ro'), name
        allocated.append(dict(name=name, bytes=s[5]))
        if name == '.text':
            text += align(s[5])
        else:
            data += align(s[5])
    assert 0 < text <= h['text_limit'] and data <= h['data_limit']
    h.update(resident_text=text, resident_data=data, allocated_sections=allocated,
             static_screen_passed=True, runtime_qualified_on_pins=False)
    return h


def main():
    roots = [ROOT/'agonport/vdplet', ROOT/'src/asm/wolf3d/tgt']
    roots += sorted((ROOT/'agonport/doc/tasks').glob('WOLF-PERF-*'))
    files = subprocess.run(['rg', '--files', '--hidden', '--no-ignore',
        '-g', '*.vdpl', *map(str, roots)], capture_output=True, text=True, check=True).stdout.splitlines()
    packages = {}
    for name in files:
        p = Path(name)
        if any(part in ('frozen-inputs', 'profiles', 'payload') for part in p.parts):
            continue
        raw = p.read_bytes()
        value = sha(raw)
        if value not in packages:
            try:
                record = screen(raw)
            except (AssertionError, ValueError, struct.error) as exc:
                record = dict(static_screen_passed=False, reason=str(exc),
                              runtime_qualified_on_pins=False)
            packages[value] = dict(bytes=len(raw), paths=[], **record)
        packages[value]['paths'].append(str(p.relative_to(ROOT)))

    entries = []
    for p in sorted((ROOT/'src/asm').glob('*/src/*.asm')):
        if not (p.name.endswith('_regression.asm') or p.name in ('wolf3d.asm', 'wolf3d_hello.asm')):
            continue
        entries.append(dict(path=str(p.relative_to(ROOT)), sha256=sha(p.read_bytes())))
    runners = []
    for p in sorted((ROOT/'src/asm').glob('*/scripts/*emulator*py')):
        source = p.read_text()
        runners.append(dict(path=str(p.relative_to(ROOT)), sha256=sha(p.read_bytes()),
            uses_old_mos_profile='mos_console8.bin' in source,
            references_bespoke_vdp='vdp_wolf3d.so' in source,
            requires_new_preparation=True))
    report = dict(schema='wolf-fw001-candidate-inventory-v1',
        source_head=subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
            capture_output=True, text=True, check=True).stdout.strip(),
        unique_packages=packages, assembly_entrypoints=entries, emulator_runners=runners,
        screen_limit='Static package screen only; not full loader admission, allocation, stack or runtime qualification.')
    (TASK/'INVENTORY.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(unique_packages=len(packages),
        static_pass=sum(x['static_screen_passed'] for x in packages.values()),
        entrypoints=len(entries), emulator_runners=len(runners))))


if __name__ == '__main__':
    main()
