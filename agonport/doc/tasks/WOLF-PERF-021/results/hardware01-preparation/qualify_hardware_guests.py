"""File-only join of actual combined and cyan source/target/producer evidence."""
from pathlib import Path
import json
import guest_binding

T = Path(__file__).resolve().parent
sha = guest_binding.sha


def qualify():
    files = []
    for task in ('WOLF-PERF-021', 'WOLF-PERF-016'):
        q = T.parent / task
        for rel in ('build/r01/build-receipt.json', 'build/guests01/receipt.json'):
            assert json.loads((q / rel).read_text())['passed']
            files.append(q / rel)
        old = json.loads((q / 'build/r01/inputs.json').read_text())['inputs']
        for name, digest in old.items():
            if Path(name).name == 'PLAN.md':
                saved = (T / 'build/hardware-preparation01/PERF016-PRE-CODE-PLAN.md' if task.endswith('016')
                         else T / 'results/build01/PRE-CODE-PLAN.md')
                assert sha(saved) == digest
                files.append(saved)
            else:
                assert sha(name) == digest, name
                files.append(Path(name))
        for name, digest in json.loads((q / 'build/guests01/inputs.json').read_text()).items():
            assert sha(name) == digest, name
            files.append(Path(name))
        for rel in ('build/r01/inputs.json', 'build/guests01/inputs.json', 'build/guests01/bindings.json',
                    'build/guests01/receipt.json', 'BUILD-RESULT.md'):
            files.append(q / rel)
    # Supplemental51-input ordered-alias evidence remains a distinct receipt.
    assert json.loads((T / 'build/alias01/receipt.json').read_text())['passed']
    inputs = json.loads((T / 'build/alias01/inputs.json').read_text())
    for name, digest in inputs.items():
        saved = T / 'build/alias01/frozen-inputs' / Path(name).relative_to(T)
        assert sha(saved) == digest
        files.append(saved)
        if Path(name).name != 'ALIAS-CHECK-PLAN.md':
            assert sha(name) == digest
    files.extend(T / 'build/alias01' / n for n in ('inputs.json', 'receipt.json', 'original-check.log', 'candidate-check.log'))
    guests = json.loads((T / 'HARDWARE-GUESTS.json').read_text())
    assert set(guests) == {'original', 'cyan', 'combined'}
    out = {}
    for arm in guests:
        assert set(guests[arm]) == {'room'}
        g = guests[arm]['room']
        result = guest_binding.verify(g)
        q = T.parent / 'WOLF-PERF-016' if arm == 'cyan' else T
        prior = json.loads((q / 'build/guests01/receipt.json').read_text())['arms']['original' if arm == 'original' else 'candidate']['room']
        assert result == {k: v for k, v in prior.items() if k in result}
        binary = Path(g['guest']).read_bytes()
        original = Path(guests['original']['room']['guest']).read_bytes()
        assert result['stack_labels'] == guest_binding.verify(guests['original']['room'])['stack_labels']
        for call in prior['presentation_calls']:
            at = call['address'] - 0x40000
            assert binary[at:at + 4] == original[at:at + 4]
        out[arm] = dict(**result, presentation_calls=prior['presentation_calls'])
        files.extend(Path(g[n]) for n in ('module', 'listing', 'guest'))
        root = q / 'build/r01' / ('original' if arm == 'original' else 'candidate') / 'module'
        files.extend(p for p in root.iterdir() if p.is_file() and p.suffix in ('.elf', '.json', '.su', '.txt', '.map'))
    assert out['original']['guest_sha256'] == 'c43e7fe74148517c30cf9bf83854cf0cf297aeaf8c4684a4624c93849b46df58'
    original = Path(guests['original']['room']['guest']).read_bytes()
    for arm in ('cyan', 'combined'):
        binary = Path(guests[arm]['room']['guest']).read_bytes()
        allowed = set()
        for a, b in zip(out['original']['operands'], out[arm]['operands']):
            assert (a['address'], a['symbol']) == (b['address'], b['symbol'])
            allowed.update(a['address'] - 0x40000 + i for i, (x, y) in enumerate(zip(bytes.fromhex(a['encoded']), bytes.fromhex(b['encoded']))) if x != y)
        assert len(original) == len(binary)
        assert {i for i, (a, b) in enumerate(zip(original, binary)) if a != b} == allowed
    for rel in ('build/r01/code-result.json', 'build/r01/nested-stack-source.json', 'build/r01/unit-composition.json',
                'build/r01/background-check.log', 'build/r01/setup-check.log', 'build/r01/chains-check.log',
                'build/r01/trig-check.log', 'build/r01/numeric-check.log'):
        files.append(T / rel)
    return dict(passed=True, arms=out, inputs={str(p.resolve()): sha(p) for p in files}, target_access=False, rebuilt=False,
        limits='Exact retained original/cyan/combined source, target, producer and ordered-alias evidence; no physical speed, branch count, optical output or default adoption.')


if __name__ == '__main__':
    print(json.dumps(qualify(), indent=2))
