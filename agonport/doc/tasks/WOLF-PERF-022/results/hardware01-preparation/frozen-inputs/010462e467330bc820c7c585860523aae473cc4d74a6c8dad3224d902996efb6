"""Finite owned physical candidate comparison. Requires frozen kit/fresh grant.

Reuse the physical54 producer/result/SDK paths; this module owns the new
namespace, admission, module selection and six-case three-arm matrix. Import is passive.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))
P3 = T.parent / 'WOLF-PERF-003'
sys.path.insert(0, str(P3 / 'hardware'))
B = T / 'build/hardware01'
spec = importlib.util.spec_from_file_location('wp007_physical54', P3 / 'hardware/physical09.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
h.B = B
decoder_spec = importlib.util.spec_from_file_location('wolf021_decoder', T/'analyze.py')
decoder = importlib.util.module_from_spec(decoder_spec); decoder_spec.loader.exec_module(decoder)
h.analyze = decoder.analyze
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
SEQUENCE = (
    ('original', 'room'), ('cyan', 'room'), ('combined', 'room'),
    ('combined', 'room'), ('cyan', 'room'), ('original', 'room'),
)
ARMS = ('original', 'cyan', 'combined')
REQUEST = '06d32e827da7'
CLEANUP_RESERVE = 360
GUEST_BOUND = 300


class BudgetStop(RuntimeError):
    """A new operation was refused before submission; retain custody, no replay."""


def verify_kit(kit):
    assert kit['task'] == 'WOLF-PERF-021-hardware01'
    assert kit['remote'] == '/test/wolf/perf021/r01'
    assert kit['request'] == REQUEST
    assert kit['original_module_sha256'] == 'a926b48ab3207b59773cc8283d59cc687f274ef2af00017451567449a4c69656'
    assert kit['cyan_module_sha256'] == '22ef84a767951ec03ea138b048db4cfe613d1edf02e8cbb34ee824ba535d24a1'
    assert kit['combined_module_sha256'] == '8d3d19bb74e1f2ea862b2154c038dfd23de2fd741fd1831d1880d849b5ad838b'
    assert kit['native_b_sha256'] == '7593b9cf9a2dc60e81221d998527d4ac0d1c3f51077348ea03e869016aa0581d'
    assert kit['source_binding_passed'] and kit['boot_binding_passed']
    assert kit['retain_lease_after_test'] is False
    binding = json.loads(Path(kit['source_binding']).read_text())
    assert binding['passed'] and binding['guest_rebuild_required'] is True
    assert binding['carrier'] == 'mainboard-route0-UART0'
    for name, digest in kit['inputs'].items():
        assert sha(name) == digest, name
    for arm in ARMS:
        p = kit['modules'][arm]
        assert p in kit['inputs'] and sha(p) == kit[arm + '_module_sha256']
    for name in kit['stage'].values():
        assert name in kit['inputs']
    assert set(kit['listings']) == {'vdplet-room'}
    for name in kit['listings'].values():
        assert name in kit['inputs']
        listing = Path(name).read_text()
        for label in ('wp_entry_sp', 'wp_exit_sp'):
            match = re.search(r'^([0-9A-F]{6})[^\n]*\b' + label + r':', listing, re.M)
            assert match and 0x40000 <= int(match[1], 16) < 0xa0000
    import guest_binding
    for arm in ARMS:
        for mode in ('room',):
            guest = kit['guests'][arm][mode]
            assert guest['module_sha256'] == kit[arm + '_module_sha256']
            assert guest['module'] == kit['modules'][arm]
            assert guest['remote_name'] == f'b-{arm}-{mode}.bin'
            assert kit['stage'][guest['remote_name']] == guest['guest']
            for name in ('guest', 'listing'):
                assert guest[name] in kit['inputs']
            result = guest_binding.verify(guest)
            # Existing post-run SP check uses original listing only after this
            # proves the actual candidate addresses exactly match that listing.
            original = guest_binding.verify(kit['guests']['original'][mode])
            assert result['stack_labels'] == original['stack_labels']
    for key in ('install_b', 'restore'):
        p = Path(kit[key])
        assert str(p) in kit['inputs'] and p.stat().st_size == kit['flash_span']


class Bench(h.Bench):
    def __init__(self, context):
        self.c = json.loads(Path(context).read_text())
        self.grant = json.loads(Path(self.c['grant']).read_text())
        if 'active' in self.grant:
            self.grant = self.grant['active']
        self.kit = json.loads((B / 'kit.json').read_text())
        verify_kit(self.kit)
        assert self.grant['owner'] == 'wolf3dorig' and self.grant['task'] == self.kit['task']
        assert self.grant['request'] == self.kit['request']
        assert self.c['manifest'] == str(B / 'kit.json')
        assert self.c['retain_lease_after_test'] is False
        self.components = self.grant['entry_observation']['components']
        assert self.components == self.kit['incoming_components']
        self.lease = self.grant['lease']
        self.url = self.c['url']
        self.port = self.c['native_port']
        self.remote = self.kit['remote']
        self.out = B / 'evidence'
        self.out.mkdir(exist_ok=False)
        self.cleaning = False
        self.selected_module_sha256 = self.kit['original_module_sha256']

    def admit(self, operation, allowance=0):
        if self.cleaning:
            return
        remaining = self.deadline - time.monotonic()
        if remaining <= CLEANUP_RESERVE + allowance:
            raise BudgetStop(f'{operation}: {remaining:.3f}s remain; require more than '
                             f'{CLEANUP_RESERVE + allowance}s before submission')

    def transfer(self, folder, label, op, remote, local):
        self.admit('new transfer ' + label)
        # Once submitted, the inherited same-job resume/finite bound remains.
        # No cutoff exception is injected into an in-flight write or GET.
        return super().transfer(folder, label, op, remote, local)

    def metadata(self, folder, label):
        self.admit('new metadata session ' + label)
        return super().metadata(folder, label)

    def line(self, folder, label, command):
        self.admit('guest RUN' if command == 'RUN .' else 'CLI ' + label,
                   GUEST_BOUND if command == 'RUN .' else 0)
        return super().line(folder, label, command)

    def case(self, index, backend, mode):
        self.admit('guest case ' + str(index), GUEST_BOUND)
        return super().case(index, backend, mode)

    def probe(self, label):
        self.admit('resource probe ' + label, GUEST_BOUND)
        return super().probe(label)

    def invoke(self, folder, filename, marker, control=False):
        if filename in ('b-room.bin', 'b-sprites.bin'):
            arms = [a for a in ARMS
                    if self.selected_module_sha256 == self.kit[a + '_module_sha256']]
            assert len(arms) == 1, 'Unbound module selection'
            mode = 'room' if filename == 'b-room.bin' else 'sprites'
            binding = self.kit['guests'][arms[0]][mode]
            import guest_binding
            guest_binding.verify(binding)
            h.save(folder / 'guest-binding.json', dict(arm=arms[0], **binding))
            filename = binding['remote_name']
        return super().invoke(folder, filename, marker, control)

    def capture(self, serial, raw, folder, predicate, bound):
        def terminal_or_expected(data):
            error_at = data.rfind(b'VDPlet startup/render failure:')
            if error_at >= 0 and data.rfind(self.remote.encode() + b' *') > error_at:
                raise h.SetupFailure('VDPlet startup failed; actual post-error MOS prompt observed')
            return predicate(data)
        return super().capture(serial, raw, folder, terminal_or_expected, bound)

    def preserve_setup(self):
        # A real returned failure can precede one/both normal diagnostic files.
        # Preserve RAM first; missing optional output cannot block restoration.
        p = self.folder('failure-collection')
        self.cli(p, 'failure-confirm-cli')
        self.service(p, 'listener')
        self.raw_state(p, 'pre')
        size = max(Path(self.kit['stage'][n]).stat().st_size for n in self.kit['stage']
                   if n.startswith(('a-', 'b-')))
        script = p / 'failure-save.txt'
        script.write_bytes(('SAVE ' + self.remote + '/setup-ram.bin &40000 &' +
            format(size, 'X') + '\r\nEMOS sdserve --fast /\r\n').encode())
        self.upload(p, 'save-script', script, self.remote + '/failure-save.txt')
        self.exit(p, 'save-exit')
        self.line(p, 'save-ram', 'EXEC ' + self.remote + '/failure-save.txt')
        self.wait_online(True)
        self.transfer(p, 'ram', 'get', self.remote + '/setup-ram.bin', p / 'ram.bin')
        assert (p / 'ram.bin').stat().st_size == size
        h.save(p / 'ram-preserved.json', dict(passed=True, size=size,
            sha256=sha(p / 'ram.bin'), before_any_load=True))
        c = self.metadata(p, 'available-diagnostics')
        try:
            entries = list(c.entries(self.remote))
        finally:
            c.lock.close()
        h.save(p / 'entries.json', entries)
        for name, decoder in (('loading.bin', h.decode_loading), ('loading3.bin', h.decode_trace)):
            if any(n.rsplit('/', 1)[-1] == name for n, _, _ in entries):
                self.transfer(p, name, 'get', self.remote + '/' + name, p / name)
                try:
                    h.save(p / (name + '.decoded.json'), decoder((p / name).read_bytes()))
                except Exception as error:
                    h.save(p / (name + '.decode-error.json'), dict(error=repr(error), raw_preserved=True))
            else:
                h.save(p / (name + '.absent.json'), dict(absent=True, no_collector_or_replay=True))
        self.exit(p, 'exit')
        self.flash('restore', self.kit['restore'])
        self.handback()

    def entry(self):
        p = self.folder('entry')
        self.own()
        self.ports_free()
        initial = self.state()
        h.save(p / 'initial-state.json', initial)
        self.check_entry_idle(initial)
        raw = self.cli(p, 'entry')
        cwd = re.search(rb'Directory: ([^\r\n]+)', raw)
        assert cwd
        assert cwd[1].strip() == b'/', 'Fresh root CLI required before namespace changes'
        (p / 'cwd.txt').write_bytes(cwd[1])
        self.service(p, 'listener')
        for remote, name, key in (
            ('/autoexec.txt', 'startup.bin', 'startup_sha256'),
            ('/emos/sdserve.bin', 'listener.bin', 'listener_sha256'),
        ):
            self.transfer(p, name, 'get', remote, p / name)
            assert sha(p / name) == self.components[key]
        c = self.metadata(p, 'directories')
        try:
            c.make_directory('/test/wolf/perf021', parents=True)
            assert not any(n.rstrip('/').lower() == self.remote.lower()
                           for n, _, _ in c.entries('/test/wolf/perf021')), 'Fresh namespace collision'
            c.make_directory(self.remote, parents=True)
            c.make_directory(self.remote + '/level_00', parents=True)
        finally:
            c.lock.close()
        for name in ('state.txt', 'route.txt'):
            self.upload(p, name, self.kit['stage'][name], self.remote + '/' + name)
        self.raw_state(p, 'entry-raw')
        self.verify_route(p, 'entry-route')
        h.save(p / 'receipt.json', dict(passed=True, fresh_namespace=True, mode0_callback0_route0=True))
        self.exit(p, 'entry-offline')
        self.line(p, 'entry-mirror-off', 'VDU 3')
        state = self.state()
        h.save(p / 'state.json', state)
        self.check_entry_idle(state)
        self.ports_free()
        observation = dict(schema='olimex-bench-observation-v1', bench='olimex',
            epoch=time.time(), observer='wolf3dorig', lease=self.lease,
            components=self.components, checks=dict(cli_verified=True,
                input_ready_neutral=True, listener_offline=True, staged_job_idle=True,
                no_serial_readers=True, no_reset_holders=True, mode0_callback0_route0=True,
                whole_startup_listener_unchanged=True),
            evidence=[str(p / n) for n in ('initial-state.json', 'state.json', 'serial.bin',
                'startup.bin', 'listener.bin', 'entry-raw-mode.bin', 'entry-raw-callback.bin', 'entry-route.bin')],
            component_provenance='Actual new grant component identities retained; fresh whole startup/listener reads and SAVE-only mode/callback/route checks. Exact incoming full-span rollback is verified in the immutable kit; no new firmware identity query claimed.')
        self.save_entry(observation)

    @staticmethod
    def check_entry_idle(state):
        k = state['keyboard']
        assert k['ready'] and k['physical_neutral'] and not k['held'] and not k['pending']
        assert not state['sd']['online'] and not state['sd']['pending'] and state['worker']['phase'] == 0

    def save_entry(self, observation):
        assert observation['lease'] == self.lease and observation['observer'] == 'wolf3dorig'
        assert 0 <= time.time() - observation['epoch'] < 120
        assert observation['components'] == self.kit['incoming_components']
        path = self.out / 'entry/observation.json'
        with path.open('x') as f:
            json.dump(observation, f, indent=2); f.write('\n')
        with (self.out / 'entry-context.json').open('x') as f:
            json.dump(dict(schema='wolf-perf021-entry-v1', generation=self.grant['generation'],
                request=self.kit['request'], lease=self.lease, original_grant=self.c['grant'],
                original_grant_sha256=sha(self.c['grant']), manifest=str(B / 'kit.json'),
                manifest_sha256=sha(B / 'kit.json'), dispatch_context=self.c,
                fresh_entry_observation=str(path), fresh_entry_sha256=sha(path),
                epoch=time.time(), retain_lease_after_test=False), f, indent=2); f.write('\n')

    def stage(self):
        assert json.loads((self.out / 'entry/receipt.json').read_text())['passed']
        continuation = json.loads((self.out / 'entry-context.json').read_text())
        assert continuation['manifest_sha256'] == sha(B / 'kit.json')
        assert continuation['lease'] == self.lease
        assert 0 <= time.time() - continuation['epoch'] < 120
        assert sha(continuation['fresh_entry_observation']) == continuation['fresh_entry_sha256']
        p = self.folder('stage')
        self.service(p, 'listener')
        for i, (name, local) in enumerate(self.kit['stage'].items()):
            if name in ('state.txt', 'route.txt'):
                continue  # Already PUT/GET verified before the entry RAM reads.
            self.admit('staging file ' + name)
            self.upload(p, f'file-{i:02d}', local, self.remote + '/' + name)
            print('STAGED', name, flush=True)
        self.exit(p, 'exit')
        h.save(p / 'receipt.json', dict(passed=True, files=len(self.kit['stage']), put_get_verified=True))

    def verify_route(self, folder, label):
        c = self.metadata(folder, label + '-remove-old')
        try:
            for name, _, attr in list(c.entries(self.remote)):
                if name.rsplit('/', 1)[-1] == 'route.bin':
                    assert not attr & 16
                    c.remove(name)
        finally:
            c.lock.close()
        self.exit(folder, label + '-exit')
        self.line(folder, label + '-save', 'EXEC ' + self.remote + '/route.txt')
        self.wait_online(True)
        self.transfer(folder, label + '-get', 'get', self.remote + '/route.bin', folder / (label + '.bin'))
        assert (folder / (label + '.bin')).read_bytes() == b'\0'

    def boot(self, folder, label):
        # This operation must be concretely bound to the current owner procedure
        # in the final kit; the historical P4/parallel literal is not reusable.
        from bootstrap import boot_current
        boot_current(self, folder, label)
        self.cli(folder, label)
        self.service(folder, label + '-listener')
        self.raw_state(folder, label + '-raw')
        self.verify_route(folder, label + '-route')
        self.exit(folder, label + '-exit')

    def ports_free(self):
        self.own()
        for port in self.c['ports']:
            assert subprocess.run(['fuser', str(Path(port).resolve())], capture_output=True).returncode == 1

    def install_module(self, arm, index):
        self.admit('module selection ' + str(index), GUEST_BOUND)
        assert arm in ARMS
        p = self.folder(f'module-{index:02d}-{arm}')
        if not self.get('/sd/status')['online']:
            self.service(p, 'listener')
        target = self.remote + '/wolf3d.vdpl'
        assert self.module_state(p, 'before-state') == b'\x01', 'Unknown module siblings; preserve and stop'
        previous = p / 'previous-target.bin'
        self.transfer(p, 'previous-target', 'get', target, previous)
        assert sha(previous) == self.selected_module_sha256, 'Unexpected previous module; preserve and stop'
        source = Path(self.kit['modules'][arm])
        assert sha(source) == self.kit[arm + '_module_sha256']
        self.upload(p, 'module', source, target)
        assert self.module_state(p, 'after-put-state') == b'\x09', 'Ambiguous replacement; preserve and stop'
        backup = p / 'previous-backup.bin'
        self.transfer(p, 'previous-backup', 'get', target + '.p17bak', backup)
        assert sha(backup) == sha(previous), 'Unexpected backup; preserve and stop'
        # upload() already GET-verified the complete selected target. Retire only
        # this known owned backup through the supported listener recovery API.
        self.admit('explicit verified module backup retirement')
        c = self.metadata(p, 'retire-owned-backup')
        try:
            self.own()
            h.save(p / 'backup-retirement-issued.json', dict(operation='RECOVER3',
                   path=target, previous_sha256=sha(previous), target_sha256=sha(source),
                   backup_sha256=sha(backup), whole_target_get_verified=True))
            state = c.rpc(10, b'\x03' + h.path_payload(target))
            h.save(p / 'backup-retirement-result.json', dict(state=state.hex()))
            assert state == b'\x01', 'Backup retirement incomplete; preserve and stop'
        finally:
            c.lock.close()
        assert self.module_state(p, 'final-state') == b'\x01'
        self.selected_module_sha256 = sha(source)
        self.verify_route(p, 'pre-guest-route')
        h.save(p / 'receipt.json', dict(passed=True, arm=arm, sha256=sha(source), outside_timing=True,
               previous_sha256=sha(previous), backup_retired=True, recovery_state=1))

    def module_state(self, folder, label):
        c = self.metadata(folder, label)
        try:
            self.own()
            state = c.rpc(10, b'\0' + h.path_payload(self.remote + '/wolf3d.vdpl'))
            h.save(folder / (label + '.json'), dict(state=state.hex(), inspect_only=True))
            return state
        finally:
            c.lock.close()

    def run_cases(self):
        for index, (arm, mode) in enumerate(SEQUENCE, 1):
            self.admit('new module/case ' + str(index), GUEST_BOUND)
            self.install_module(arm, index)
            self.case(index, 'vdplet', mode)
            p = self.out / f'{index:02d}-vdplet-{mode}'
            h.save(p / 'arm.json', dict(arm=arm, module_sha256=self.kit[arm + '_module_sha256']))
            self.probe(f'after-{index:02d}-{arm}')

    def handback(self):
        # Include the route check before the inherited final listener retirement.
        p = self.folder('route-handback')
        self.cli(p, 'route-check')
        self.service(p, 'listener')
        self.verify_route(p, 'final-route')
        self.exit(p, 'exit')
        super().handback()
        p = self.folder('final-checks')
        self.line(p, 'cwd', 'CD /')
        raw = self.cli(p, 'root-cli')
        assert re.search(rb'Directory: /\s*\r?\n', raw), 'Root cwd not restored'
        self.line(p, 'mirror-off', 'VDU 3')
        state = self.state()
        h.save(p / 'state.json', state)
        k = state['keyboard']
        assert k['ready'] and k['physical_neutral'] and not k['held'] and not k['pending']
        assert not state['sd']['online'] and not state['sd']['pending'] and state['worker']['phase'] == 0
        for port in self.c['ports']:
            assert subprocess.run(['fuser', str(Path(port).resolve())], capture_output=True).returncode == 1
        checks = {n: True for n in ('no_workload', 'no_transfer', 'no_serial_readers', 'no_reset_holders',
                  'cli_verified', 'input_ready_neutral', 'listener_offline', 'staged_job_idle', 'restoration_verified')}
        h.save(p / 'observation.json', dict(schema='olimex-bench-observation-v1', bench='olimex',
               epoch=time.time(), observer='wolf3dorig', lease=self.lease, checks=checks,
               evidence=[str(p / 'state.json'), str(p / 'serial.bin'), str(self.out / 'route-handback/final-route.bin'),
                         str(self.out / 'handback/observation.json'), str(self.out / 'flash-restore/receipt.json')],
               components=self.components,
               component_provenance={n: ('Fresh unchanged whole-file comparison in handback' if n in ('startup_sha256', 'listener_sha256')
                   else 'Exact incoming application/touched-tail restoration and independent full-span readback' if n == 'native_vdp_sha256'
                   else 'Retained unchanged fresh-grant identity; this suite never writes this component') for n in self.components},
               disposition='New final rootCLI/input/idle/freeUSB observation; earlier same-custody route0/mode0/callback0 and exact app/tail restore/readback retained by original receipt, no intervening guest or route/mode change; startup/listener unchanged; SD mounted.'))

    def suite(self):
        try:
            self.deadline = time.monotonic() + 4200
            self.cleaning = False
            self.entry()
            self.stage()
            self.flash('b', self.kit['install_b'])
            self.probe('entry')
            self.run_cases()
            self.cleaning = True  # Restoration is never refused by dispatch cutoff.
            self.flash('restore', self.kit['restore'])
            self.handback()
            h.save(self.out / 'complete.json', dict(passed=True, guests=6, resource_probes=7, restored=True))
            h.save(self.out / 'restored-idle.json', dict(restored=True, target_actors_stopped=True, lease=self.lease, reason='Ready for normal fresh release after driver and all owned children have exited; no further probing.', epoch=time.time()))
        except h.SetupFailure as error:
            h.save(self.out / 'failure.json', dict(error=repr(error), next_dispatch_stopped=True, actual_mos_return=True, epoch=time.time()))
            self.cleaning = True  # Known actual return; save RAM then restore.
            self.preserve_setup()
            h.save(self.out / 'setup-stopped-restored.json', dict(restored=True, benchmark_claim=False))
        except BaseException as error:
            h.save(self.out / 'failure.json', dict(error=repr(error), next_dispatch_stopped=True, custody_retained=True, epoch=time.time()))
            raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('context')
    args = p.parse_args()
    interrupt_spec = importlib.util.spec_from_file_location('wp007_host_interrupt', P3 / 'hardware/host_interrupt08.py')
    interrupt = importlib.util.module_from_spec(interrupt_spec)
    interrupt_spec.loader.exec_module(interrupt)
    interrupt.install(B / 'host-interruption')
    Bench(args.context).suite()
