"""ONE real full-game profiling qualification; ordinary guarded construction."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
import host_observer
import bootstrap
import qualify_guest
T = Path(__file__).resolve().parent
ROOT = T.parents[3]
B = T / 'build/hardware02'
P3 = T.parent / 'WOLF-PERF-003'
sys.path.insert(0, str(P3 / 'hardware'))
spec = importlib.util.spec_from_file_location('profile_physical_transport', P3 / 'hardware/physical09.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
h.B = B
spec = importlib.util.spec_from_file_location('profile_decoder', ROOT/'src/asm/wolf3d/scripts/decode_profile.py')
decoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decoder)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
REQUEST = '47bae5199a9c'
CLEANUP_RESERVE = 360
GUEST_BOUND = 300

class BudgetStop(RuntimeError):
    pass

def verify_kit(kit):
    bootstrap.verify_closure(kit)
    assert kit['task'] == 'WOLF-PROFILE-001-hardware02'
    assert kit['request'] == REQUEST
    assert kit['remote'] == '/test/wolf/profile001/r02'
    assert not kit['retain_lease_after_test']
    for name, digest in kit['inputs'].items():
        assert sha(name) == digest, name
    for name in kit['stage'].values():
        assert name in kit['inputs']
    binding = json.loads(Path(kit['source_binding']).read_text())
    assert binding['passed'] and binding['rom_sha256'] == kit['incoming_components']['emos_rom_sha256']
    assert binding['carrier'] == 'mainboard-route0-UART0'
    assert kit['native_b_sha256'] == '7593b9cf9a2dc60e81221d998527d4ac0d1c3f51077348ea03e869016aa0581d'
    for key, digest in (('restore','85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'),
                        ('install_b','493fd0a010bedcfc5916314353f93565f7b159ac163d9bc61e7c5078140669e8')):
        assert kit[key] in kit['inputs'] and sha(kit[key]) == digest
        assert Path(kit[key]).stat().st_size == kit['flash_span'] == 1105920
    assert kit['module_sha256'] == '8d3d19bb74e1f2ea862b2154c038dfd23de2fd741fd1831d1880d849b5ad838b'
    assert sha(kit['stage']['wolf3d.vdpl']) == kit['module_sha256']
    qualify_guest.verify(kit['guest'])
    assert kit['stage']['profile.bin'] == kit['guest']['guest']

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
        self.selected_module_sha256 = self.kit['module_sha256']
        self.deadline = time.monotonic() + 1800
        self.observer_folder = B / 'observer'
        self.observer_record = host_observer.create(self.observer_folder, self.lease, sha(B / 'kit.json'))

    def admit(self, operation, allowance=0):
        if self.cleaning:
            return
        host_observer.check(self.observer_folder, self.observer_record)
        remaining = self.deadline - time.monotonic()
        if remaining <= CLEANUP_RESERVE + allowance:
            raise BudgetStop(f'{operation}: {remaining:.3f}s remain; require more than '
                             f'{CLEANUP_RESERVE + allowance}s before submission')

    def flash(self, label, image):
        self.admit('new native flash ' + label)
        return super().flash(label, image)

    def transfer(self, folder, label, op, remote, local):
        self.admit('new transfer ' + label)
        # Once submitted, the inherited same-job resume/finite bound remains.
        # No cutoff exception is injected into an in-flight write or GET.
        return super().transfer(folder, label, op, remote, local)

    def metadata(self, folder, label):
        self.admit('new metadata session ' + label)
        self.own()
        client = h.m.Metadata(self.url, folder / (label + '-metadata.json'), timeout=60)
        try:
            client.connect(require_fast=True)
            return client
        except BaseException:
            client.lock.close()
            raise

    def line(self, folder, label, command):
        self.admit('guest RUN' if command == 'RUN .' else 'CLI ' + label,
                   GUEST_BOUND if command == 'RUN .' else 0)
        return super().line(folder, label, command)

    def capture(self, serial, raw, folder, predicate, bound):
        def terminal_or_expected(data):
            error_at = data.rfind(b'VDPlet startup/render failure:')
            if error_at >= 0 and data.rfind(self.remote.encode() + b' *') > error_at:
                raise h.SetupFailure('VDPlet startup failed; actual post-error MOS prompt observed')
            return predicate(data)
        return super().capture(serial, raw, folder, terminal_or_expected, bound)

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
            namespace_parent = self.remote.rsplit('/', 1)[0]
            c.make_directory(namespace_parent, parents=True)
            assert not any(n.rstrip('/').lower() == self.remote.lower()
                           for n, _, _ in c.entries(namespace_parent)), 'Fresh namespace collision'
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
            json.dump(dict(schema='wolf-profile001-entry-v1', generation=self.grant['generation'],
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

    def save_guest_ram(self, folder):
        """SAVE only, after a proved returned CLI, before any later LOAD/reset."""
        # cli() writes serial.bin: keep the original game transcript intact.
        proof = folder / 'preserve-cli-proof'
        proof.mkdir(exist_ok=False)
        self.cli(proof, 'preserve-cli')
        if not self.get('/sd/status')['online']:
            self.service(folder, 'preserve-listener')
        size = Path(self.kit['guest']['guest']).stat().st_size
        script = folder / 'save-ram.txt'
        script.write_bytes((f'SAVE {self.remote}/profile-ram.bin &40000 &{size:X}\r\n'
                            'EMOS sdserve --fast /\r\n').encode())
        self.upload(folder, 'save-script', script, self.remote + '/save-ram.txt')
        self.exit(folder, 'save-exit')
        self.line(folder, 'save-ram', 'EXEC ' + self.remote + '/save-ram.txt')
        self.wait_online(True)
        self.transfer(folder, 'ram', 'get', self.remote + '/profile-ram.bin', folder / 'ram.bin')
        assert (folder / 'ram.bin').stat().st_size == size
        h.save(folder / 'ram-preserved.json', dict(size=size, sha256=sha(folder / 'ram.bin'),
                                                 before_any_load_or_reset=True))

    def invoke_profile(self, folder):
        self.admit('new full-game guest', GUEST_BOUND)
        self.exit(folder, 'invoke-exit')
        raw = bytearray()
        with h.m.open_passive_serial(self.port, baudrate=115200, timeout=.2) as serial:
            self.line(folder, 'mirror', 'VDU 2')
            token = b'WOLF-PROFILE-001'
            self.line(folder, 'cue', 'VDU ' + ' '.join(map(str, token)) + ' 13 10')
            self.capture(serial, raw, folder, lambda r: token in r, 20)
            for label, command in (('cd', 'CD ' + self.remote), ('load', 'LOAD profile.bin')):
                start = len(raw)
                self.line(folder, label, command)
                self.capture(serial, raw, folder,
                             lambda r: self.remote.encode() + b' *' in r[start:], 20)
            start = len(raw)
            self.line(folder, 'run', 'RUN .')
            self.capture(serial, raw, folder, lambda r:
                         b'Thanks for playing Wolf3DOrig!' in r[start:] and
                         self.remote.encode() + b' *' in r[start:], GUEST_BOUND)
            # Retain the same one-second post-return fault window as the donor.
            end = time.monotonic() + 1
            while time.monotonic() < end:
                raw.extend(serial.read(8192))
                (folder / 'serial.bin').write_bytes(raw)
            assert not any(s in raw for s in (b'Guru Meditation', b'RST $38 panic'))
        h.save(folder / 'returned-cli.json', dict(passed=True, one_guest=True, epoch=time.time()))

    def collect_profile(self, folder):
        self.save_guest_ram(folder)
        for name in ('DONE.BIN', 'WOLFPROF.BIN'):
            self.transfer(folder, name, 'get', self.remote + '/' + name, folder / name)
        result = qualify_guest.check_return(self.kit['guest'], folder)
        profile = decoder.decode((folder / 'WOLFPROF.BIN').read_bytes())
        assert profile['completed_frame_records'] == 250
        assert len(profile['complete_blocks']) >= 3
        assert all(b['status'] == 0 for b in profile['complete_blocks'])
        frames = profile['frames']
        assert all(f['native'] and f['discarded_attempts'] == 0 for f in frames)
        assert len({f['angle'] for f in frames}) > 20, 'Expected changing headings in the actual game'
        assert all(decoder.delta(f['callback'], f['prepare']) < 8000 for f in frames)
        h.save(folder / 'profile.json', profile)
        self.raw_state(folder, 'post')
        self.verify_route(folder, 'post-route')
        # raw_state('post') already used post-exit, before verify_route started
        # a new listener incarnation. Never reuse its completed old journal.
        self.exit(folder, 'profile-collection-exit')
        h.save(folder / 'receipt.json', dict(passed=True, records=250, return_checks=result,
               profile_sha256=sha(folder / 'WOLFPROF.BIN'), real_native_join=True,
               calibrated_clock=False, optical_scanout_observed=False))

    def suite(self):
        try:
            host_observer.wait(self.observer_folder, self.observer_record, seconds=45)
            self.admit('entry')
            self.entry()
            self.stage()
            self.flash('b', self.kit['install_b'])
            p = self.folder('full-game')
            self.service(p, 'listener')
            self.invoke_profile(p)
            self.collect_profile(p)
            self.cleaning = True
            self.flash('restore', self.kit['restore'])
            self.handback()
            h.save(self.out / 'complete.json', dict(passed=True, guests=1,
                   info17_queries=2, restored=True, profiling_qualification_only=True))
            h.save(self.out / 'restored-idle.json', dict(restored=True,
                   target_actors_stopped=True, lease=self.lease, epoch=time.time()))
        except BaseException as error:
            h.save(self.out / 'failure.json', dict(error=repr(error), next_dispatch_stopped=True,
                   custody_retained=True, no_automatic_replay=True, epoch=time.time()))
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('context')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('profile_host_interrupt', P3 / 'hardware/host_interrupt08.py')
    interrupt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(interrupt)
    interrupt.install(B / 'host-interruption')
    Bench(args.context).suite()
