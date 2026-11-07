"""Latest optimized visible guest: LOAD only, then stop for Smith's manual RUN."""
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
B = T/'build/hardware02'
Q = T.parent/'WOLF-PERF-009'
spec = importlib.util.spec_from_file_location('wolf009_transport', Q/'hardware02.py')
parent = importlib.util.module_from_spec(spec); spec.loader.exec_module(parent)
h = parent.h
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verify_kit(kit):
    assert kit['task'] == 'WOLF-PERF-011-visible-manual01'
    assert kit['request'] == '8fd506cf5fbe'
    assert kit['remote'] == '/test/wolf/perf011/r01'
    assert kit['manual_run_only'] and kit['retain_lease_after_test']
    for n, d in kit['inputs'].items():
        assert sha(n) == d, n
    assert kit['module_sha256'] == 'a926b48ab3207b59773cc8283d59cc687f274ef2af00017451567449a4c69656'
    assert sha(kit['stage']['wolf3d.vdpl']) == kit['module_sha256']
    assert Path(kit['install_b']).stat().st_size == Path(kit['restore']).stat().st_size == 1105920
    assert sha(kit['restore']) == '85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'
    assert sha(kit['install_b']) == '493fd0a010bedcfc5916314353f93565f7b159ac163d9bc61e7c5078140669e8'
    assert kit['native_b_sha256'] == '7593b9cf9a2dc60e81221d998527d4ac0d1c3f51077348ea03e869016aa0581d'
    assert set(kit['stage']) == {'rotate.bin','wolf3d.vdpl','wolf3d.cfg','state.txt','route.txt',
        'hud.agnb','sfx.agnb','shell.agnb','level_00/tiles.agnb','level_00/sprites.agnb',
        'level_00/state_easy.w3l','level_00/state_medium.w3l','level_00/state_baby.w3l','level_00/state_hard.w3l'}
    spec = importlib.util.spec_from_file_location('visible_binding', Q/'guest_binding.py')
    binding = importlib.util.module_from_spec(spec); spec.loader.exec_module(binding)
    binding.verify(kit['guest'])
    assert set(kit['listings']) == {'vdplet-paced'}


class Bench(parent.Bench):
    def __init__(self, context):
        self.c = json.loads(Path(context).read_text())
        self.grant = json.loads(Path(self.c['grant']).read_text())
        if 'active' in self.grant:
            self.grant = self.grant['active']
        self.kit = json.loads((B/'kit.json').read_text())
        verify_kit(self.kit)
        assert self.c['manifest'] == str(B/'kit.json') and self.c['retain_lease_after_test']
        assert self.grant['owner'] == 'wolf3dorig'
        assert self.grant['task'] == self.kit['task'] and self.grant['request'] == self.kit['request']
        self.components = self.grant['entry_observation']['components']
        assert self.components == self.kit['incoming_components']
        self.lease = self.grant['lease']
        self.url = self.c['url']; self.port = self.c['native_port']
        self.remote = self.kit['remote']; self.out = B/'evidence'
        self.out.mkdir(exist_ok=True)
        self.cleaning = False; self.deadline = time.monotonic()+3600

    def line(self, folder, label, command):
        # Enforced at the final keyboard-command seam, including inherited code.
        if re.match(r'^\s*RUN\b', command, re.I):
            raise RuntimeError('Smith alone starts the guest: agent RUN forbidden')
        return super().line(folder, label, command)

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
            c.make_directory('/test/wolf/perf011', parents=True)
            assert not any(n.rstrip('/').lower() == self.remote.lower()
                           for n, _, _ in c.entries('/test/wolf/perf011')), 'Fresh namespace collision'
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

    def save_entry(self, observation):
        assert observation['lease'] == self.lease and observation['observer'] == 'wolf3dorig'
        assert 0 <= time.time()-observation['epoch'] < 120
        assert observation['components'] == self.kit['incoming_components']
        p = self.out/'entry/observation.json'
        h.save(p, observation)
        h.save(self.out/'entry-context.json', dict(schema='wolf011-entry-v1',
            generation=self.grant['generation'], request=self.kit['request'], lease=self.lease,
            manifest=str(B/'kit.json'), manifest_sha256=sha(B/'kit.json'),
            original_grant=self.c['grant'], original_grant_sha256=sha(self.c['grant']),
            fresh_entry_observation=str(p), fresh_entry_sha256=sha(p), epoch=time.time(),
            retain_lease_after_test=True))

    def load_for_human(self):
        """Terminal preparation boundary. No RUN, collector, reset or release."""
        p = self.folder('load-only')
        self.own()
        state = self.state(); self.check_entry_idle(state)
        self.ports_free()
        raw = bytearray()
        with h.m.open_passive_serial(self.port, baudrate=115200, timeout=.2) as serial:
            self.line(p, 'mirror', 'VDU 2')
            start = len(raw)
            self.line(p, 'cd', 'CD '+self.remote)
            self.capture(serial, raw, p, lambda r:self.remote.encode()+b' *' in r[start:], 20)
            start = len(raw)
            self.line(p, 'load', 'LOAD rotate.bin')
            self.capture(serial, raw, p, lambda r:self.remote.encode()+b' *' in r[start:], 20)
            assert b'Error loading' not in raw and b'Error executing' not in raw
            # VDU writes do not LOAD or execute code. Show the exact human command.
            message = b'READY: TYPE RUN . TO START TWO TURNS'
            self.line(p, 'ready-message', 'VDU '+' '.join(map(str,message))+' 13 10')
            self.capture(serial, raw, p, lambda r:message in r, 20)
            self.line(p, 'mirror-off', 'VDU 3')
        state = self.state(); h.save(p/'state.json', state)
        self.check_entry_idle(state); self.ports_free()
        h.save(self.out/'ready.json', dict(ready=True, loaded_not_run=True,
            lease=self.lease, generation=self.grant['generation'], epoch=time.time(),
            kit_sha256=sha(B/'kit.json'), guest_sha256=sha(self.kit['guest']['guest']),
            module_sha256=self.kit['module_sha256'], manual_command='RUN .',
            cwd=self.remote, actors_stopped=True, retain_lease=True))
        print('READY LOADED NOT RUN; Smith must type RUN .; custody retained', flush=True)

    def prepare_only(self):
        assert not (self.out/'ready.json').exists(), 'Already loaded: do not replay preparation'
        self.entry()
        self.stage()
        self.flash('b', self.kit['install_b'])
        self.load_for_human()

    def collect_after_human(self):
        """Only selected after Smith confirms he ran it; never starts a guest."""
        ready = json.loads((self.out/'ready.json').read_text())
        assert ready['loaded_not_run'] and ready['lease'] == self.lease
        assert ready['kit_sha256'] == sha(B/'kit.json')
        p = self.folder('human-run-collection')
        self.own(); self.check_entry_idle(self.state())
        self.cli(p, 'actual-return')
        self.service(p, 'listener')
        # Preserve resident application/RAM before any later LOAD (none selected).
        script = p/'preserve.txt'
        script.write_bytes(('SAVE '+self.remote+'/completed-ram.bin &40000 &'+
            format(Path(self.kit['guest']['guest']).stat().st_size,'X')+
            '\r\nEMOS sdserve --fast /\r\n').encode())
        self.upload(p,'save-script',script,self.remote+'/preserve.txt')
        self.exit(p,'save-exit'); self.line(p,'save-resident','EXEC '+self.remote+'/preserve.txt')
        self.wait_online(True)
        for name in ('timing.bin','native.bin','loading.bin','loading3.bin','after.bin','stack.bin','before.bin','completed-ram.bin'):
            self.transfer(p,name,'get',self.remote+'/'+name,p/name)
        result = h.analyze(p)
        assert result['mode'] == 'paced' and result['completed_records'] > 1
        listing = Path(self.kit['guest']['listing']).read_text(); after=(p/'after.bin').read_bytes()
        stack=[]
        for label in ('wp_entry_sp','wp_exit_sp'):
            m=re.search(r'^([0-9A-F]{6})[^\n]*\b'+label+r':',listing,re.M); assert m
            at=int(m[1],16)-0x40000; stack.append(int.from_bytes(after[at:at+3],'little'))
        assert stack[0] == stack[1] and 0xb0000 <= stack[0] < 0xc0000
        h.save(p/'receipt.json',dict(passed=True, human_started=True, agent_run=False,
            result=result, balanced_stack=stack, optical_confirmation='Ask Smith; not inferred from logs'))
        self.raw_state(p,'post'); self.exit(p,'exit')
        self.cleaning=True
        self.flash('restore',self.kit['restore']); self.handback()
        h.save(self.out/'complete.json',dict(passed=True,human_started=True,restored=True,
            no_agent_run=True,result=str(p/'report.json')))


def main():
    p=argparse.ArgumentParser(); p.add_argument('--context',required=True)
    p.add_argument('--action',choices=('prepare','collect'),required=True)
    args=p.parse_args()
    spec=importlib.util.spec_from_file_location('wolf011_interrupt', T.parent/'WOLF-PERF-003/hardware/host_interrupt08.py')
    interrupt=importlib.util.module_from_spec(spec);spec.loader.exec_module(interrupt)
    interrupt.install(B/('host-interruption-'+args.action))
    bench=Bench(args.context)
    try:
        if args.action == 'prepare': bench.prepare_only()
        else: bench.collect_after_human()
    except BaseException as error:
        target=bench.out/('failure-'+args.action+'.json')
        if not target.exists(): h.save(target,dict(error=repr(error),epoch=time.time(),
            dispatch_stopped=True,custody_retained=True,no_automatic_run=True))
        raise


if __name__ == '__main__':
    main()
