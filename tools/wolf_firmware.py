"""Project-owned pinned firmware and payload checks. No device or process launch."""
from pathlib import Path
import gzip
import hashlib
import json
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = ROOT / 'agonport/doc/tasks/WOLF-FW-001/build/releases'
VDP_SHA = 'b004570b607b45bbd6e87a3c704b65b23d3221981db3aac6cf2578aa22d766e3'
SUMS_SHA = '6469f6d6717ede6acb68d9b7ce519db07a1d5a08a0ef7c765739dfe86658aa9d'
MOS_SHA = 'd7a51147f3381cd68d56f3fbe4605434a897dfae1b049269afeba09ec2b7eb50'
ZIP_SHA = '9c8a9a28b0f597e6a9294d806491ffca3902c16cf1876b092ae8944f65368061'
ELF_SHA = '3b471a388764e5d8da6d10cc78f46361b8aef1f884ea0f24d86369a366460a7d'
PRODUCTION_MODULE_SHA = '266f809ff76e56733251da202e5c4747cd9c12d247d799d486471a262c0404b7'
DEFAULT_MODULE = ROOT / 'agonport/vdplet/production/build/wolf3d_production.vdpl'
DEFAULT_PAYLOAD = ROOT / 'tgt/wolf3d-standard'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_name(name):
    path = Path(name)
    require(bool(name) and not path.is_absolute() and '..' not in path.parts,
            'Unsafe relative payload path: ' + name)
    return path


def release_files(cache=DEFAULT_CACHE):
    """Verify release bytes on every preparation, including ZIP MOS and map."""
    cache = Path(cache)
    vdp = cache / 'vdplet'
    sums = vdp / 'SHA256SUMS'
    require(sha(sums) == SUMS_SHA, 'VDPlet SHA256SUMS differs from selected release')
    for line in sums.read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        path = vdp / safe_name(name.lstrip('*'))
        require(sha(path) == expected, 'VDPlet release asset changed: ' + name)
    firmware = vdp / 'vdp-vdplet-0.1.2-alpha.bin'
    require(sha(firmware) == VDP_SHA and firmware.stat().st_size == 1100304,
            'Wrong VDPlet release image')
    elf = gzip.decompress((vdp / 'vdp-vdplet-0.1.2-alpha.elf.gz').read_bytes())
    require(hashlib.sha256(elf).hexdigest() == ELF_SHA, 'Wrong release debug ELF')
    archive = cache / 'eirene/3.1.0_uart0_rc_3.zip'
    require(sha(archive) == ZIP_SHA, 'Wrong Eirene release ZIP')
    with zipfile.ZipFile(archive) as z:
        mos, mapping = z.read('mos-rc3.bin'), z.read('mos-rc3.map')
    require(len(mos) == 100879 and hashlib.sha256(mos).hexdigest() == MOS_SHA,
            'Wrong mos-rc3.bin ZIP member')
    return dict(firmware=firmware.read_bytes(), elf=elf, mos=mos, mos_map=mapping,
        identity=dict(vdp_version='v0.1.2-alpha', vdp_sha256=VDP_SHA,
            vdp_elf_sha256=ELF_SHA, mos_version='3.1.0_uart0_rc_3',
            mos_sha256=MOS_SHA, mos_map_sha256=hashlib.sha256(mapping).hexdigest()))


def module_info(path):
    raw = Path(path).read_bytes()
    require(len(raw) >= 64 and raw[:4] == b'VDPL', 'Not a VDPlet module')
    u16 = lambda at: struct.unpack_from('<H', raw, at)[0]
    u32 = lambda at: struct.unpack_from('<I', raw, at)[0]
    require((u16(4), u16(6), u32(8), u32(12)) == (1, 64, len(raw), 0x32505345),
            'Module image/header size or architecture mismatch')
    require(u16(16) == 1 and u16(18) <= 6 and u32(20) & ~287 == 0,
            'Module requires features absent from pinned VDPlet release')
    require(0 < u32(24) <= 98304 and 0 < u32(28) <= 16384 and
            u32(32) <= 2048 and len(raw) <= 131072, 'Module exceeds release policy')
    require(u32(40) == 64 and u32(44) == len(raw)-64 and u32(48) == 80400 and
            raw[52:64] == bytes(12), 'Unsupported ELF container/compiler header')
    elf=raw[64:]
    require(len(elf)>=52 and elf[:7]==b'\x7fELF\x01\x01\x01' and
            struct.unpack_from('<HHI',elf,16)==(3,94,1), 'Expected ELF32 Xtensa shared image')
    at=struct.unpack_from('<I',elf,32)[0]
    width,count,names=struct.unpack_from('<HHH',elf,46)
    require(width==40 and 0<count<=32 and names<count and at+count*40<=len(elf), 'ELF section table bounds')
    sections=[struct.unpack_from('<10I',elf,at+40*i) for i in range(count)]
    strings=sections[names]
    require(strings[4]+strings[5]<=len(elf),'ELF name table bounds')
    names_blob=elf[strings[4]:strings[4]+strings[5]]
    text=data=0
    for s in sections:
        require(s[0]<len(names_blob) and b'\0' in names_blob[s[0]:], 'ELF section name bounds')
        name=names_blob[s[0]:].split(b'\0',1)[0]
        require(s[1]==8 or s[4]+s[5]<=len(elf), 'ELF section file bounds')
        require(s[1]!=9, 'REL relocation is unsupported')
        if s[1] in (2,11):
            require(s[9]==16 and s[5]%16==0,'ELF symbol table format')
            for offset in range(s[4]+16,s[4]+s[5],16):
                require(struct.unpack_from('<H',elf,offset+14)[0]!=0,'Undefined module import')
        if s[1]==4:
            require(s[9]==12 and s[5]%12==0,'ELF RELA format')
            for offset in range(s[4],s[4]+s[5],12):
                address,info,addend=struct.unpack_from('<3I',elf,offset)
                require(address%4==0 and info==5 and addend==0,'Unsupported module relocation')
        if not s[2]&2 or not s[5]:continue
        if name in (b'.hash',b'.dynsym',b'.dynstr',b'.rela.dyn'):continue
        require(name in (b'.text',b'.rodata',b'.data',b'.bss',b'.data.rel.ro'),
                'Unsupported allocated module section: '+repr(name))
        if name==b'.text':text+=(s[5]+3)&~3
        else:data+=(s[5]+3)&~3
    require(0<text<=u32(24) and data<=u32(28),'Module resident bytes exceed declarations')
    return dict(bytes=len(raw), sha256=sha(path), abi_minor=u16(18),
                capabilities=u32(20), resident_text=text,resident_data=data,
                static_screen_only=True)


def verify_payload(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / 'payload.json').read_text())
    require(manifest['schema'] == 'wolf-pinned-payload-v1', 'Unknown payload schema')
    require(manifest['firmware']['vdp_sha256'] == VDP_SHA and
            manifest['firmware']['mos_sha256'] == MOS_SHA, 'Stale payload firmware pins')
    for name, record in manifest['files'].items():
        path = directory / safe_name(name)
        require(path.is_file() and path.resolve().is_relative_to(directory),
                'Missing/escaping payload file: ' + name)
        require(path.stat().st_size == record['bytes'] and sha(path) == record['sha256'],
                'Payload file changed: ' + name)
    for name in (manifest['entry'], 'wolf3d.vdpl'):
        require(name in manifest['files'], 'Missing payload entry/module')
    info = module_info(directory / 'wolf3d.vdpl')
    require(info['sha256'] == manifest['module']['sha256'], 'Module/receipt mismatch')
    return manifest


def legacy_exception(argv, purpose):
    """Explicit existing-policy exception, not new permission or a lease."""
    if any(arg in ('-h', '--help') for arg in argv[1:]):
        print(purpose + ': historical Fab/firmware runner. Use tools/wolf_prepare.py '
              'for pinned preparation. For an already-authorized model/version '
              'exception, add --firmware-exception "specific purpose". '
              'This command does not grant workload or resource permission.')
        raise SystemExit(0)
    option = '--firmware-exception'
    if option not in argv:
        raise SystemExit(purpose + ': historical firmware/profile is not a routine '
            'pinned-release path. Use tools/wolf_prepare.py, or include '
            '--firmware-exception "specific compatibility/model purpose" in '
            'the already-authorized invocation and scheduling request.')
    at = argv.index(option)
    require(at+1 < len(argv) and len(argv[at+1].strip()) >= 12 and
            not argv[at+1].startswith('-'), 'A specific firmware-exception reason is required')
    print('Firmware exception (existing permissions still apply): ' + argv[at+1])
    del argv[at:at+2]
