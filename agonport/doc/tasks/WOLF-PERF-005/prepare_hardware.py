"""File-only preparation of the finite hardware kit. Never contacts a device."""
from pathlib import Path
import hashlib
import json
import re
import shutil

T = Path(__file__).resolve().parent
P3 = T.parent / 'WOLF-PERF-003'
P4 = T.parent / 'WOLF-PERF-004'
E = Path('/Agon/mystuff/agon-extender')
D = Path('/Agon/mystuff/agon-dev-env')
B = T / 'build/hardware01'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def save(p, value):
    with p.open('x') as f:
        json.dump(value, f, indent=2); f.write('\n')

def prepare():
    B.mkdir(exist_ok=False)
    old = json.loads((P3 / 'build/hardware09/kit.json').read_text())
    release = P4 / 'build/hardware03/release63.json'
    released = json.loads(release.read_text())
    assert released['generation'] == 63 and released['released']
    components = released['release_observation']['components']
    assert components['native_vdp_sha256'] == '5d65797e53a70db8716cc3bc31dc936e431aea975ffad8efb76d5d7e8c1e3d07'
    restore = Path('/Agon/mystuff/MechAgon/.runtime/render001/native-install-r01/candidate-sectors.bin')
    assert sha(restore) == '85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'
    native_app = Path('/Agon/mystuff/agon-vdplet/build/vdpl028-profile8-r02/firmware/firmware-src/.pio/build/esp32dev/firmware.bin')
    assert sha(native_app) == components['native_vdp_sha256']
    assert restore.read_bytes()[:native_app.stat().st_size] == native_app.read_bytes()
    installed = Path('/Agon/mystuff/MechAgon/.runtime/render001/watch003/install-native/receipt.json')
    assert json.loads(installed.read_text())['sectors_readback_match']
    shutil.copyfile(restore, B / 'restore.bin')
    native_b = P3 / 'build/r04/native02/vdplet/.pio/build/esp32dev/firmware.bin'
    assert sha(native_b) == '7593b9cf9a2dc60e81221d998527d4ac0d1c3f51077348ea03e869016aa0581d'
    data = bytearray(restore.read_bytes()); data[:native_b.stat().st_size] = native_b.read_bytes()
    assert len(data) == 1105920
    (B / 'install-b.bin').write_bytes(data)
    remote = '/test/wolf/perf005/r01'
    (B / 'state.txt').write_bytes(('SAVE '+remote+'/post-mode.bin &BC349 &1\r\nSAVE '+remote+'/post-callback.bin &BC38E &3\r\nEMOS sdserve --fast /\r\n').encode())
    (B / 'route.txt').write_bytes(('SAVE '+remote+'/route.bin &BCB25 &1\r\nEMOS sdserve --fast /\r\n').encode())
    names = ['wolf3d.cfg','hud.agnb','sfx.agnb','shell.agnb'] + [n for n in old['stage'] if n.startswith('level_00/')] + ['b-unpaced.bin','b-control.bin','resource-probe.bin']
    stage = {n: old['stage'][n] for n in names}
    for p in stage.values():
        assert sha(p) == old['inputs'][p], ('Changed retained physical54 input', p)
    modules = {a: str(T / 'build/r02' / a / 'module/wolf_perf.vdpl') for a in ('original','candidate')}
    stage.update({'wolf3d.vdpl': modules['original'], 'state.txt': str(B / 'state.txt'), 'route.txt': str(B / 'route.txt')})
    listings = {n: old['listings'][n] for n in ('vdplet-control','vdplet-unpaced')}
    source = E / 'agents/net004/emos-uart-rfc25-source/src'
    rom = E / 'agents/net004/emos-uart-rfc25-r02/ROM.bin'
    mapfile = rom.parent / 'mos.elf.map'
    assert sha(rom) == components['emos_rom_sha256']
    symbols = {'_vpd_protocol_flags': 0xbc326, '_scrmode': 0xbc349, '_serialFlags': 0xbc35a,
               '_vdp_protocol_state': 0xbc378, '_vdp_protocol_cmd': 0xbc379, '_vdp_protocol_len': 0xbc37a,
               '_vdp_protocol_ptr': 0xbc37b, '_vdp_protocol_data': 0xbc37e, '_user_kbvector': 0xbc38e, '_emosVduBackend': 0xbcb25}
    mapping = mapfile.read_text()
    for name, address in symbols.items():
        m = re.search(r'0x([0-9a-f]+)\s+' + re.escape(name) + r'\s*$', mapping, re.M)
        assert m and int(m[1], 16) == address, name
    guest_sources = []
    for mode in ('control','unpaced'):
        root = P3 / 'build/hardware05/vdplet' / mode / 'source'
        guest_sources += [p for p in root.iterdir() if p.suffix in ('.asm','.inc')]
        trace = (root / 'loading_trace04.inc').read_text()
        addresses = set(int(x, 16) for x in re.findall(r'\(0([0-9a-f]+)h\)', trace, re.I))
        assert addresses <= set(symbols.values()), addresses - set(symbols.values())
    binding = dict(passed=True, guest_rebuild_required=False, carrier='mainboard-route0-UART0',
        symbols={k:hex(v) for k,v in symbols.items()}, rom_sha256=sha(rom), map_sha256=sha(mapfile),
        provenance='Current retained UART source/map and installed full-ROM identity; actual grant/raw route0 admission still required.',
        findings=[
            'reset.asm RST18 -> handlers.asm rst_18_handler -> serial.asm EMOS_vdu_WRITE route0 -> synchronous UART0 PUTCH loop. No async host buffer lifetime substitution.',
            'UART0 PUTCH checks enabled/CTS then waits for each byte accepted. Source-backed behavior, not a fresh wire or receiver-timing observation.',
            'mos_api.asm 40 clears selected existing flags;41 calls mos.c wait_VDP, polling same flag up to250000 iterations without query replay or clear.',
            'vdp_protocol.asm KEY requires completed ten-byte body and route0, exact P3DR or VDPL tag, callback-only; guest owns token/kind/sequence validation. Not a generic completion ABI.',
            'Current map proves retained loading observer private reads, mode/callback and route SAVE addresses. Ordinary RAM reads only; guest literals remain byte-identical to physical54.',
            'Actual retained mode producer waits for matching136 reply then wp_settle_display240 MOS ticks before setup/loading. Invocation capture retains1second after final return before collection; entry0 only.',
            'No parallel networking API/carrier substitution, old54 bootstrap marker or firmware rollback permitted.'
        ])
    composition = T / 'build/composition03/receipt.json'
    qualified = json.loads(composition.read_text())
    assert qualified['passed'] and qualified['inputs'][str(T/'hardware.py')] == sha(T/'hardware.py')
    service = E / 'agents/remote009/download-r01/source/projects/sdserve/src/service.c'
    binding['transfer_lifecycle'] = dict(listener_app_sha256=components['listener_sha256'],
        retained_service_sha256=sha(service), recovery_operation=10, inspect_action=0, backup_cleanup_action=3,
        required_before_state=1, required_after_put_state=9, required_final_state=1,
        host_composition_receipt_sha256=sha(composition), qualification='Actual consumer method plus retained real listener engine; POSIX/MOS host adapter, not physical FAT/UART qualification')
    save(B / 'source-binding.json', binding)
    tools = [E / 'scripts' / n for n in ('keyboard.py','sdcard.py','sdcard_staged.py','passive_serial.py','reset_agon_usb.py','reset_agon.py','p4_boot_guard.py')]
    tools += [E / 'agents/remote009/fast-transfer-pin-r01/sdcard_staged.py', E / 'agents/bench-reset/usb-reset.local.json', E / 'agents/net004/uart1-bootstrap-r01/bootstrap.py',
              D / 'cross-agent/olimex-bench/bench_lease.py', D / 'cross-agent/olimex-bench/README.md',
              Path('/Agon/mystuff/agon-dev-env/.local/mig001-arm64/cpython-3.14.6-linux-aarch64-gnu/bin/python3.14'),
              E / '.venv/lib/python3.14/site-packages/esptool/reset.py', E / '.venv/lib/python3.14/site-packages/serial/serialposix.py']
    sources = [source / n for n in ('reset.asm','handlers.asm','serial.asm','mos_api.asm','mos.c','vdp_protocol.asm','emos.c')]
    files = list(stage.values()) + list(listings.values()) + list(modules.values()) + guest_sources + tools + sources
    files += [T/'R02-BUILD.json',T/'R02-RESULT.md',rom,mapfile,restore,native_app,installed,native_b,release,B/'restore.bin',B/'install-b.bin',B/'source-binding.json',T/'HARDWARE-RUN-01.md',T/'PRE-CODE.md',T/'hardware.py',T/'bootstrap.py',T/'prepare_hardware.py',T/'test_hardware.py',T/'test_replacement.py',T/'run_composition.py',T/'build/composition03/receipt.json',P3/'hardware/physical09.py',P3/'hardware/trace04.py',P3/'hardware/host_interrupt08.py',P3/'analyze.py',T.parent/'WOLF-PERF-001/hardware/physical.py']
    listener_source = E / 'agents/remote009/download-r01/source'
    files += [listener_source/'projects/sdserve/src'/n for n in ('service.c','service.h','sd_wire.h')]
    files += [listener_source/'tests/test_sdserve.py',listener_source/'tests/sdserve_host/fs.c',listener_source/'tests/sdserve_host/agon/mos.h']
    proof = P4 / 'build/hardware03/evidence/flash-restore/read.bin'
    assert sha(proof) == sha(restore)
    files += [proof,P4/'build/hardware03/evidence/flash-restore/receipt.json']
    inputs = {str(p):sha(p) for p in files}
    request = json.loads((T / 'build/bench-request01.json').read_text())['request']
    kit = dict(task='WOLF-PERF-005-hardware-r01',request=request,remote=remote,
        incoming_components=components, incoming_release=str(release), incoming_generation=63,
        original_module_sha256=sha(modules['original']),candidate_module_sha256=sha(modules['candidate']),native_b_sha256=sha(native_b),
        modules=modules,stage=stage,listings=listings,restore=str(B/'restore.bin'),install_b=str(B/'install-b.bin'),flash_span=len(data),
        source_binding=str(B/'source-binding.json'),source_binding_passed=True,boot_binding_passed=True,
        p4_boot_build='net-003-r02-b2026-11-06-09-03-07Z', inputs=inputs,
        restrictions='Fresh actual grant matching exact incoming tuple required. Candidate comparison only; no default adoption, P4/EMOS writes or carrier substitution.')
    save(B / 'kit.json', kit)
    print(json.dumps(dict(files=len(inputs),stage_files=len(stage),kit_sha256=sha(B/'kit.json'),rollback=sha(B/'restore.bin'),install=sha(B/'install-b.bin'))))

if __name__ == '__main__': prepare()
