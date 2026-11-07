"""One isolated real-firmware Alexe run. Existing executable names stay flexe."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import time

BASE = Path.home() / 'Agon/mystuff/Wolf3dOrig/.emulator/wolf-profile001-alexe01'
PINS = {
    'flexe-agon-emulator': 'f7951314959be72ab7757579a9daf2a42383ccdb5187dec9d9653b42ad8a477c',
    'flexe-agon-emulator.bin': 'c987fafc9045dfeb862fc4b0252dab70845c25e87ff5961b80e85a9dcd1b7399',
    'flexe-vdp.so': '0866265bd6f3d73ad572f31dc1bb954f308ed9a5d857efa9414d37e1ade13374',
    'esp32-firmware.bin': '7593b9cf9a2dc60e81221d998527d4ac0d1c3f51077348ea03e869016aa0581d',
    'esp32-firmware.elf': '092bacc3bb965dc3347625e892f19006e54fbada15561b54b3689ade39d7bdb4',
    'mos_platform.bin': 'd564243283972690933a4554296ad6202ca4ef54572279533a942960846bebae',
    'mos_platform.map': 'd69e60bbce61a7b4b3eef318ba395f11c4e1a5b585755755113992dc94edcb86',
    'input.so': '7d9f52a705776bf9db3ab84d16fcf66902a589e3a494ff42103fda27f60315e4',
}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def assert_owner(lease):
    assert lease, 'Actual Oryx checkout token required before preparation or launch'
    subprocess.run(['ssh', '-o', 'BatchMode=yes', 'raspberrypi',
        '/Agon/mystuff/agon-dev-env/.venv/bin/python',
        '/Agon/mystuff/agon-dev-env/cross-agent/vdplet-rollout/oryx_lease.py',
        'assert-owner', '--owner', 'wolf3dorig', '--lease', lease],
        check=True, stdout=subprocess.DEVNULL, timeout=30)


def prepare(lease):
    assert_owner(lease)
    old = BASE.parent / 'wolf-four01/flexe-vdplet-01'
    for name, digest in PINS.items():
        assert sha(old / name) == digest, name
        shutil.copyfile(old / name, BASE / name)
    for name in ('.mos-release', '.mos-release.sha256', '.bespoke-vdp-profile'):
        shutil.copyfile(old / name, BASE / name)
    for name in ('flexe-agon-emulator', 'flexe-agon-emulator.bin'):
        (BASE / name).chmod(0o755)
    payload = json.loads((BASE / 'inputs/payload.json').read_text())
    for name, digest in payload['files'].items():
        assert sha(BASE / 'inputs' / name) == digest, name
    guest_hash = {
        '01': 'fda77dfd4f13e8d824f10fa371759ec5ad7f6e81bd1786161b5607b22579ea22',
        '02': '9777b1a8718a4501622d28f2764e08f6e7d6e6adc968acbae76d3784446755e0',
        '03': '49c9355f570e58d0b2665df24a161155db3827cea8057740db9ac5781c5a2a6c',
        '04': '96d6e7d4fce6a1f357b55d862ee75ebcbe9eee1dcdf37438229c29f3d5d21d84',
    }[BASE.name[-2:]]
    assert payload['guest_sha256'] == guest_hash
    assert payload['module_sha256'] == '8d3d19bb74e1f2ea862b2154c038dfd23de2fd741fd1831d1880d849b5ad838b'
    game = BASE / 'sdcard/wolf3d'
    shutil.copytree(BASE / 'inputs/assets', game)
    for name in ('wolf3d.bin', 'wolf3d.vdpl', 'wolf3d.cfg'):
        shutil.copyfile(BASE / 'inputs' / name, game / name)
    (BASE / 'sdcard/autoexec.txt').write_bytes(b'SET KEYBOARD 1\r\ncd /wolf3d\r\nrunbin ./wolf3d.bin\r\n')
    files = [BASE / n for n in PINS] + [BASE / 'sdcard/autoexec.txt']
    files += [p for p in game.rglob('*') if p.is_file()]
    files += [BASE / 'inputs/decode_profile.py', BASE / 'inputs/payload.json', Path(__file__)]
    manifest = {str(p.relative_to(BASE)): sha(p) for p in files}
    (BASE / 'inputs.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (BASE / '.runtime.sha256').write_text(''.join(v + '  ' + k + '\n' for k, v in manifest.items()))
    print(json.dumps(dict(prepared=True, inputs=len(manifest), no_launch=True)))


def guard():
    assert Path('/sys/devices/system/cpu/cpufreq/boost').read_text().strip() == '0'
    temps = []
    for name in Path('/sys/class/hwmon').glob('*/name'):
        if name.read_text().strip() == 'k10temp':
            for label in name.parent.glob('temp*_label'):
                if label.read_text().strip() == 'Tctl':
                    temps.append(int(label.with_name(label.name.replace('_label', '_input')).read_text()) / 1000)
    mem = int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))
    assert len(temps) == 1 and temps[0] < 80 and mem >= 524288, (temps, mem)
    return dict(cpu_c=temps[0], available_kib=mem)


def run(lease):
    assert_owner(lease)
    manifest = json.loads((BASE / 'inputs.json').read_text())
    for name, digest in manifest.items():
        assert sha(BASE / name) == digest, name
    out = BASE / 'run'
    out.mkdir(exist_ok=False)
    events = out / 'events.txt'
    events.write_text('')
    env = dict(os.environ)
    for name in ('BASH_ENV', 'LD_LIBRARY_PATH', 'FLEXE_UART_OBSERVER_OUTPUT',
                 'FLEXE_TX_OBSERVER_OUTPUT', 'FLEXE_TX_BATCH_OBSERVER_OUTPUT'):
        env.pop(name, None)
    env.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
        LD_PRELOAD=str(BASE / 'input.so'), W3V_REVIEW_EVENTS=str(events),
        W3V_REVIEW_VDP=str(BASE / 'flexe-vdp.so'), AGON_FLEXE_ENGINE='jit')
    began = time.monotonic()
    child, guards = None, []
    result = dict(passed=False, real_firmware=True, native_synthetic=False,
        hardware_P4_handshake_emulated=False, physical_timing_claim=False)
    with (out / 'frontend.log').open('x') as log:
        try:
            guards.append(dict(seconds=0, **guard()))
            child = subprocess.Popen(['./flexe-agon-emulator'], cwd=BASE, env=env,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            result['pid'] = child.pid
            print(json.dumps(dict(pid=child.pid, original_bound_seconds=300)), flush=True)
            next_guard, next_capture, captures = 0, 0, 0
            game = BASE / 'sdcard/wolf3d'
            done = game / 'DONE.BIN'
            while time.monotonic() - began < 300:
                assert child.poll() is None, 'Unexpected emulator exit'
                now = time.monotonic() - began
                if now >= next_guard:
                    guards.append(dict(seconds=now, **guard()))
                    next_guard = now + 1
                if now >= next_capture:
                    with events.open('a') as stream:
                        stream.write('capture ' + str(out / f'frame-{captures:03d}.ppm') + '\n')
                    captures += 1
                    next_capture = now + 1
                uart = BASE / 'last-run/esp32-uart0.log'
                text = uart.read_text(errors='replace') if uart.exists() else ''
                assert 'RST $38 panic' not in text, 'Guest panic'
                assert 'VDPL ERROR' not in text, 'Runtime returned a VDPL error; stop original case'
                if done.exists() and done.stat().st_size == 32:
                    raw = done.read_bytes()
                    result['done_hex'] = raw.hex()
                    shutil.copyfile(done, out / 'DONE.BIN')
                    if (game / 'WOLFPROF.BIN').exists():
                        shutil.copyfile(game / 'WOLFPROF.BIN', out / 'WOLFPROF.BIN')
                    assert raw[:4] == b'WPT1' and raw[4:7] == bytes(3), ('Profiler completion status', raw.hex())
                    assert not raw[7] & 0x41
                    u24 = lambda at: int.from_bytes(raw[at:at+3], 'little')
                    assert u24(8) == 250 and u24(20) == 0
                    assert u24(12) == u24(16)
                    stacks = [int.from_bytes(raw[n:n+4], 'little') for n in (24, 28)]
                    assert all(512 <= v < 65536 for v in stacks), stacks
                    if 'Thanks for playing Wolf3DOrig!' not in text or '/wolf3d *' not in text:
                        time.sleep(.1)
                        continue
                    spec = importlib.util.spec_from_file_location('decode', BASE / 'inputs/decode_profile.py')
                    decoder = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(decoder)
                    decoded = decoder.decode((game / 'WOLFPROF.BIN').read_bytes())
                    assert decoded['completed_frame_records'] == 250 and decoded['discarded_attempts'] == 0
                    assert len(decoded['complete_blocks']) >= 3
                    assert all(b['status'] == 0 for b in decoded['complete_blocks'])
                    assert all(f['native'] for f in decoded['frames'])
                    assert len({f['angle'] for f in decoded['frames']}) >= 20
                    (out / 'decoded.json').write_text(json.dumps(decoded, indent=2) + '\n')
                    result.update(passed=True, frames=250, native_info17=stacks,
                        entry_sp=u24(12), exit_sp=u24(16), captures=captures)
                    break
                time.sleep(.1)
            else:
                raise TimeoutError('Original300s guest/MOS completion bound')
        except BaseException as error:
            result['error'] = repr(error)
        finally:
            if child and child.poll() is None:
                with events.open('a') as stream:
                    stream.write('capture ' + str(out / 'final.ppm') + '\nquit\n')
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait(timeout=5)
            result['returncode'] = None if child is None else child.returncode
            if result['returncode'] != 0:
                result['passed'] = False
            stats_path = BASE / 'last-run/stats.json'
            if stats_path.exists():
                stats = json.loads(stats_path.read_text())
                result['stats'] = stats
                if stats.get('failed') or any(stats.get(k, 0) for k in ('unhandled', 'unregistered', 'unmapped')):
                    result['passed'] = False
            else:
                result['passed'] = False
            result['config_output'] = dict(before=manifest['sdcard/wolf3d/wolf3d.cfg'],
                after=sha(BASE / 'sdcard/wolf3d/wolf3d.cfg'), ordinary_config_save_expected=True)
            result.update(seconds=time.monotonic() - began, owned_child_joined=True,
                all_immutable_inputs_unchanged=all(sha(BASE / p) == d for p, d in manifest.items()
                    if p != 'sdcard/wolf3d/wolf3d.cfg'))
            if not result['all_immutable_inputs_unchanged']:
                result['passed'] = False
            (out / 'host-guards.json').write_text(json.dumps(guards, indent=2) + '\n')
            (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'run'))
    parser.add_argument('--lease')
    parser.add_argument('--revision', choices=('01', '02', '03', '04'), default='01')
    args = parser.parse_args()
    BASE = BASE.with_name('wolf-profile001-alexe' + args.revision)
    if args.action == 'prepare':
        prepare(args.lease)
    else:
        assert args.lease
        raise SystemExit(run(args.lease))
