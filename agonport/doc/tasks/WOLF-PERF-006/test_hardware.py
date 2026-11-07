"""Device-free tests of the actual adapter/matrix, not a second controller."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
import hardware
import bootstrap


class Model(hardware.Bench):
    def __init__(self, out, fail=None):
        self.out = Path(out)
        self.events = []
        self.fail = fail
        self.lease = 'model-owned-lease'
        self.kit = dict(original_module_sha256='original', candidate_module_sha256='candidate',
                        install_b='install-b.bin', restore='restore.bin')

    def entry(self): self.events.append('entry')
    def stage(self): self.events.append('stage')
    def flash(self, label, _image): self.events.append(('flash', label))
    def probe(self, label): self.events.append(('probe', label))
    def handback(self): self.events.append('handback')
    def preserve_setup(self): self.events.append('preserve-setup-before-new-load')
    def install_module(self, arm, index):
        self.events.append(('module', index, arm))
        if self.fail == ('module', index): raise RuntimeError('module mismatch')
    def case(self, index, backend, mode):
        self.events.append(('case', index, backend, mode))
        if self.fail == ('case', index): raise RuntimeError('first failure')
        if self.fail == ('setup', index): raise hardware.h.SetupFailure('known returned setup failure')
        (self.out / f'{index:02d}-vdplet-{mode}').mkdir()


class ControllerTests(unittest.TestCase):
    def test_continuation_rejects_pending_or_unready_entry(self):
        state = dict(keyboard=dict(ready=True, physical_neutral=True, held=0, pending=0),
                     sd=dict(online=False, pending=0), worker=dict(phase=0))
        hardware.Bench.check_entry_idle(state)
        for section, key, value in (('keyboard','ready',False), ('keyboard','held',1),
                ('keyboard','pending',1), ('keyboard','physical_neutral',False),
                ('sd','online',True), ('sd','pending',1), ('worker','phase',1)):
            changed = json.loads(json.dumps(state)); changed[section][key] = value
            with self.subTest(section=section,key=key), self.assertRaises(AssertionError):
                hardware.Bench.check_entry_idle(changed)

    def test_continuation_joins_fresh_observation_without_replacing_grant(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(hardware, 'B', Path(folder)):
            root = Path(folder); (root/'entry').mkdir()
            grant = root/'original-grant.json'; grant.write_text('{"generation":69}')
            (root/'kit.json').write_text('{"frozen":true}')
            b = object.__new__(hardware.Bench); b.out=root; b.lease='actual-owner'
            b.c=dict(grant=str(grant)); b.kit=dict(request='ab7af23bfd1a',incoming_components={'native':'unchanged'})
            observation=dict(epoch=hardware.time.time(),observer='wolf3dorig',lease=b.lease,components=b.kit['incoming_components'])
            b.save_continuation(observation)
            joined=json.loads((root/'continuation-context.json').read_text())
            self.assertEqual(joined['generation'],69)
            self.assertEqual(joined['original_grant_sha256'],hardware.sha(grant))
            self.assertEqual(joined['manifest_sha256'],hardware.sha(root/'kit.json'))
            self.assertEqual(joined['fresh_entry_sha256'],hardware.sha(root/'entry/observation.json'))
            self.assertTrue(joined['retain_lease_after_test'])
            self.assertEqual(grant.read_text(),'{"generation":69}')
            with self.assertRaises(FileExistsError): b.save_continuation(observation)
            observation['epoch'] -= 121
            with self.assertRaises(AssertionError): b.save_continuation(observation)

    def test_complete_order_and_module_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            m = Model(folder)
            m.suite()
            modules = [e[2] for e in m.events if isinstance(e, tuple) and e[0] == 'module']
            self.assertEqual(modules, ['original', 'candidate', 'original', 'candidate', 'candidate', 'original'])
            cases = [e for e in m.events if isinstance(e, tuple) and e[0] == 'case']
            self.assertEqual([e[3] for e in cases], ['control', 'control', 'unpaced', 'unpaced', 'unpaced', 'unpaced'])
            self.assertEqual(len([e for e in m.events if isinstance(e, tuple) and e[0] == 'probe']), 7)
            self.assertEqual(m.events[-2:], [('flash', 'restore'), 'handback'])
            for i, (arm, mode) in enumerate(hardware.SEQUENCE, 1):
                saved = json.loads((Path(folder) / f'{i:02d}-vdplet-{mode}/arm.json').read_text())
                self.assertEqual(saved, dict(arm=arm, module_sha256=arm))
            self.assertTrue(json.loads((Path(folder) / 'complete.json').read_text())['restored'])
            self.assertEqual(json.loads((Path(folder) / 'author-held-idle.json').read_text())['lease'], m.lease)

    def test_failed_module_never_invokes_guest_or_successor(self):
        with tempfile.TemporaryDirectory() as folder:
            m = Model(folder, ('module', 4))
            with self.assertRaisesRegex(RuntimeError, 'module mismatch'): m.suite()
            self.assertEqual([e[1] for e in m.events if isinstance(e, tuple) and e[0] == 'case'], [1, 2, 3])
            self.assertNotIn(('flash', 'restore'), m.events)
            self.assertTrue(json.loads((Path(folder) / 'failure.json').read_text())['custody_retained'])

    def test_failed_guest_stops_before_next_probe_or_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            m = Model(folder, ('case', 3))
            with self.assertRaisesRegex(RuntimeError, 'first failure'): m.suite()
            self.assertEqual(m.events[-1], ('case', 3, 'vdplet', 'unpaced'))
            self.assertFalse((Path(folder) / 'complete.json').exists())

    def test_returned_setup_failure_collects_without_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            m = Model(folder, ('setup', 2))
            m.suite()
            self.assertEqual(m.events[-1], 'preserve-setup-before-new-load')
            self.assertEqual(len([e for e in m.events if isinstance(e, tuple) and e[0] == 'case']), 2)
            self.assertFalse((Path(folder) / 'complete.json').exists())

    def test_incomplete_current_binding_refused(self):
        with self.assertRaises((KeyError, AssertionError)):
            hardware.verify_kit(dict(task='WOLF-PERF-006-hardware-r01', remote='/test/wolf/perf006/r01'))


class BootstrapTests(unittest.TestCase):
    def setup_model(self, folder):
        root = Path(folder)
        (root / 'entry').mkdir()
        data = b'SET KEYBOARD 1\r\nEMOS KEYINPUT extender\r\n'
        (root / 'entry/startup.bin').write_bytes(data)
        return SimpleNamespace(out=root, components={'startup_sha256': hashlib.sha256(data).hexdigest()},
            kit={'p4_boot_build': bootstrap.BUILD, 'inputs': {str(bootstrap.DONOR): bootstrap.DONOR_SHA}})

    def test_current_source_selected_only_after_startup_check(self):
        with tempfile.TemporaryDirectory() as folder:
            b = self.setup_model(folder)
            child = Path(folder) / 'flash'; child.mkdir()
            called = []
            with patch.object(bootstrap, 'load_donor', return_value=SimpleNamespace(clean_bootstrap=lambda owner, p: called.append((owner, p)))):
                bootstrap.boot_current(b, child, 'b')
            self.assertEqual(called, [(b, child)])
            self.assertEqual(json.loads((child / 'pre-bootstrap.json').read_text())['p4_build'], bootstrap.BUILD)

    def test_old_marker_or_changed_startup_stops_before_reset(self):
        for bad in ('marker', 'startup'):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as folder:
                b = self.setup_model(folder)
                child = Path(folder) / 'flash'; child.mkdir()
                if bad == 'marker': b.kit['p4_boot_build'] = 'old54'
                else: (b.out / 'entry/startup.bin').write_bytes(b'RUN unwanted')
                with patch.object(bootstrap, 'load_donor') as loader:
                    with self.assertRaises(AssertionError): bootstrap.boot_current(b, child, 'b')
                    loader.assert_not_called()


class EntryModel(hardware.Bench):
    """Only device I/O is modeled; entry/route/stage logic is the real adapter."""
    def __init__(self, root, collision=False):
        self.out = Path(root)
        self.remote = '/test/wolf/perf006/r02'
        self.files = {'/autoexec.txt': b'SET KEYBOARD 1', '/emos/sdserve.bin': b'LISTENER'}
        self.components = {k: hashlib.sha256(self.files[n]).hexdigest() for k,n in
            [('startup_sha256','/autoexec.txt'),('listener_sha256','/emos/sdserve.bin')]}
        self.events = []
        self.dirs = {self.remote} if collision else set()
        self.lock = SimpleNamespace(close=lambda: None)
        state = self.out / 'state.txt'; state.write_bytes(b'STATE')
        route = self.out / 'route.txt'; route.write_bytes(b'ROUTE')
        self.kit = {'stage': {'state.txt': str(state), 'route.txt': str(route)}}
        self.lease = 'model-owner69'
        grant = self.out/'original-grant.json'; grant.write_text('{"generation":69}')
        self.c = dict(grant=str(grant))
        self.kit.update(request='ab7af23bfd1a',incoming_components=self.components)
        (self.out/'kit.json').write_text(json.dumps(self.kit))
        self.deadline = hardware.time.monotonic() + 3600
        self.cleaning = False
    def own(self): pass
    def ports_free(self): self.events.append(('ports-free',))
    def state(self):
        return dict(keyboard=dict(ready=True,physical_neutral=True,held=0,pending=0),
                    sd=dict(online=False,pending=0),worker=dict(phase=0))
    def cli(self, p, label): return b'Directory: /\r\n/ *'
    def service(self, *args): pass
    def metadata(self, *args): return self
    def make_directory(self, name, parents=False): self.dirs.add(name)
    def entries(self, path):
        return [(n, len(v), 0) for n,v in self.files.items() if n.rsplit('/',1)[0] == path] + [(n,0,16) for n in self.dirs if n.rsplit('/',1)[0] == path]
    def remove(self, name): self.events.append(('remove',name)); del self.files[name]
    def upload(self, p, label, local, remote):
        self.events.append(('upload',remote)); self.files[remote] = Path(local).read_bytes()
    def transfer(self, p, label, op, remote, local):
        assert op == 'get'; Path(local).write_bytes(self.files[remote])
    def exit(self, *args): pass
    def wait_online(self, *args): pass
    def line(self, p, label, command):
        if command == 'VDU 3': return
        assert command == 'EXEC ' + self.remote + '/route.txt'
        assert self.remote + '/route.bin' not in self.files, 'Stale SAVE destination'
        self.files[self.remote + '/route.bin'] = b'\0'
    def raw_state(self, *args): self.events.append(('raw',))


class EntryTests(unittest.TestCase):
    def test_fresh_namespace_entry_and_scripts_are_not_replaced_in_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            b = EntryModel(folder)
            with patch.object(hardware,'B',Path(folder)): b.entry(); b.stage()
            self.assertEqual([e for e in b.events if e[0] == 'upload'],
                [('upload',b.remote + '/state.txt'),('upload',b.remote + '/route.txt')])
            b.verify_route(b.out / 'stage', 'second-route')
            self.assertIn(('remove',b.remote + '/route.bin'),b.events)
            self.assertTrue(json.loads((b.out / 'entry/receipt.json').read_text())['mode0_callback0_route0'])
            self.assertEqual(json.loads((b.out/'entry/observation.json').read_text())['lease'],b.lease)
            self.assertTrue((b.out/'continuation-context.json').exists())
    def test_namespace_collision_stops_before_any_sd_file_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            b = EntryModel(folder, collision=True)
            with self.assertRaisesRegex(AssertionError, 'collision'): b.entry()
            self.assertFalse(any(e[0] == 'upload' for e in b.events))


class BudgetTests(unittest.TestCase):
    def model(self, remaining):
        b = object.__new__(hardware.Bench)
        b.deadline = 1000 + remaining
        b.cleaning = False
        return b

    def test_no_new_module_case_inside_guest_plus_cleanup_reserve(self):
        for remaining in (330,360,600,660):
            with self.subTest(remaining=remaining), patch.object(hardware.time,'monotonic',return_value=1000):
                b = self.model(remaining)
                with patch.object(b,'install_module') as submit:
                    with self.assertRaises(hardware.BudgetStop): b.run_cases()
                    submit.assert_not_called()

    def test_run_is_rechecked_after_setup_and_before_keyboard_submission(self):
        with patch.object(hardware.time,'monotonic',return_value=1000), patch.object(hardware.h.Bench,'line') as submit:
            b = self.model(660)
            with self.assertRaises(hardware.BudgetStop): b.line(None,'run','RUN .')
            submit.assert_not_called()
            b.deadline += 1
            b.line(None,'run','RUN .')
            submit.assert_called_once()

    def test_collection_refused_before_submission_but_inflight_job_finishes(self):
        now = [1000]
        with patch.object(hardware.time,'monotonic',side_effect=lambda:now[0]):
            b = self.model(361)
            def completed_job(*args):
                now[0] += 400  # Existing finite job is not interrupted at cutoff.
                return 'completed-original-job'
            with patch.object(hardware.h.Bench,'transfer',side_effect=completed_job) as submit:
                self.assertEqual(b.transfer(None,'one','get','remote','local'),'completed-original-job')
                with self.assertRaises(hardware.BudgetStop): b.transfer(None,'two','get','remote','local')
                self.assertEqual(submit.call_count,1)

    def test_metadata_collection_guard_and_cleanup_exemption(self):
        with patch.object(hardware.time,'monotonic',return_value=1000), patch.object(hardware.h.Bench,'metadata') as submit:
            b = self.model(360)
            with self.assertRaises(hardware.BudgetStop): b.metadata(None,'collection')
            submit.assert_not_called()
            b.cleaning = True
            b.metadata(None,'restoration')
            submit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
