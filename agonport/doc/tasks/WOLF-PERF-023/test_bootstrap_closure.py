"""Exercise actual file-only guards/constructor; never call a device helper."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import bootstrap
import hardware02 as hardware

T = Path(__file__).resolve().parent


class BootstrapClosureTests(unittest.TestCase):
    def test_exact_current_dependencies_and_full_real_kit_accept(self):
        kit = json.loads((T / 'results/actual97/kit.json').read_text())
        kit.update(task='WOLF-PERF-023-hardware02', request=hardware.REQUEST,
                   remote='/test/wolf/perf023/r02')
        kit['inputs'] = {name: hardware.sha(name) for name in kit['inputs']}
        kit['inputs'].update({str(p): digest for p, digest in bootstrap.REQUIRED.items()})
        prior = json.loads((T.parent / 'WOLF-PERF-022/results/actual95/kit.json').read_text())
        for name, digest in bootstrap.verify_closure(kit).items():
            self.assertEqual(prior['inputs'][name], digest)
        with patch.object(bootstrap, 'load_donor') as loader:
            hardware.verify_kit(kit)
            loader.assert_not_called()

    def test_each_missing_wrong_or_changed_dependency_refuses_ordinary_constructor(self):
        # Isolated copies permit real stale-byte checks without touching shared
        # owner files. The production validator and ordinary constructor run.
        for selected in bootstrap.REQUIRED:
            for defect in ('missing-pin', 'wrong-pin', 'changed-file', 'missing-file'):
                with self.subTest(path=str(selected), defect=defect), tempfile.TemporaryDirectory() as name:
                    root = Path(name)
                    required = {}
                    selected_copy = None
                    for index, (path, digest) in enumerate(bootstrap.REQUIRED.items()):
                        copy = root / ('dependency-' + str(index))
                        copy.write_bytes(path.read_bytes())
                        required[copy] = digest
                        if path == selected:
                            selected_copy = copy
                    kit = dict(p4_boot_build=bootstrap.BUILD,
                               inputs={str(p): digest for p, digest in required.items()})
                    if defect == 'missing-pin': del kit['inputs'][str(selected_copy)]
                    elif defect == 'wrong-pin': kit['inputs'][str(selected_copy)] = '0' * 64
                    elif defect == 'changed-file': selected_copy.write_bytes(b'changed')
                    else: selected_copy.unlink()
                    (root / 'kit.json').write_text(json.dumps(kit))
                    (root / 'grant.json').write_text('{}')
                    (root / 'context.json').write_text(json.dumps(dict(grant=str(root / 'grant.json'))))
                    with patch.object(bootstrap, 'REQUIRED', required), patch.object(hardware, 'B', root), \
                            patch.object(hardware.host_observer, 'create') as publish, \
                            patch.object(hardware.Bench, 'entry') as entry, \
                            patch.object(hardware.h.Bench, 'flash') as flash, \
                            patch.object(bootstrap, 'load_donor') as loader:
                        with self.assertRaises((AssertionError, FileNotFoundError)):
                            hardware.Bench(root / 'context.json')
                        publish.assert_not_called()
                        entry.assert_not_called()
                        flash.assert_not_called()
                        loader.assert_not_called()
                    self.assertFalse((root / 'evidence').exists())

    def test_original97_missing_closure_rejected_before_general_kit_validation(self):
        kit = json.loads((T / 'results/actual97/kit.json').read_text())
        with self.assertRaisesRegex(AssertionError, 'Missing/wrong bootstrap pin'):
            hardware.verify_kit(kit)


if __name__ == '__main__':
    unittest.main()
