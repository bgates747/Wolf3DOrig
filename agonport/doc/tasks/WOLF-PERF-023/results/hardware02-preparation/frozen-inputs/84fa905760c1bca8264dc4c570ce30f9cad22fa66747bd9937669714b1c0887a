"""Rejoin actual span source/ELF/producer/resource qualification; file-only."""
from pathlib import Path
import json
import guest_binding

T=Path(__file__).resolve().parent
sha=guest_binding.sha


def qualify():
    assert Path(guest_binding.__file__).resolve()==T/'guest_binding.py'
    files=[]
    archive=T/'results/build01/frozen-inputs'
    saved=json.loads((archive/'index.json').read_text())
    selected=json.loads((T/'build/r01/build-inputs.json').read_text())['inputs']
    assert set(saved)==set(selected)
    for name,digest in selected.items():
        snapshot=Path(saved[name]['snapshot'])
        assert sha(snapshot)==digest
        files.append(snapshot)
        # Completed checkboxes are disposed after the build; retain exact
        # historical plan bytes, never restamp that earlier source selection.
        if Path(name)!=T/'PLAN.md':
            assert sha(name)==digest,name
            files.append(Path(name))
    for rel in ('build/r01/build-receipt.json','build/r01/code-result.json',
                'build/r01/nested-stack-source.json','build/r01/byte-loop-audit.json',
                'build/guests01/receipt.json','build/composition04/receipt.json'):
        p=T/rel
        assert json.loads(p.read_text())['passed'],rel
        files.append(p)
    for name,digest in json.loads((T/'build/guests01/inputs.json').read_text()).items():
        assert sha(name)==digest,name
        files.append(Path(name))
    composition=json.loads((T/'build/composition04/receipt.json').read_text())
    composition_saved=json.loads((T/'results/controller04/frozen-inputs/index.json').read_text())
    for name,digest in composition['inputs'].items():
        snapshot=Path(composition_saved[name]['snapshot'])
        assert sha(snapshot)==digest
        files.append(snapshot)
        if Path(name)!=T/'PLAN.md':
            assert sha(name)==digest,name
            files.append(Path(name))
    guests=json.loads((T/'HARDWARE-GUESTS.json').read_text())
    assert guests==json.loads((T/'build/guests01/bindings.json').read_text())
    assert set(guests)=={'original','candidate'}
    receipt=json.loads((T/'build/guests01/receipt.json').read_text())
    out={}
    for arm in ('original','candidate'):
        assert set(guests[arm])=={'room'}
        g=guests[arm]['room']
        actual=guest_binding.verify(g)
        expected=receipt['arms'][arm]['room']
        assert actual=={k:expected[k] for k in actual}
        assert g['package_bytes']==(22572 if arm=='original' else 22620)
        assert g['package_limit']==g['package_bytes']+1
        out[arm]=dict(**actual,presentation_calls=expected['presentation_calls'])
        files.extend(Path(g[n]) for n in ('module','guest','listing'))
        for p in (T/'build/r01'/arm/'module').iterdir():
            if p.is_file() and p.suffix in ('.elf','.json','.su','.txt','.map','.vdpl'): files.append(p)
    assert out['original']['guest_sha256']=='6180358376c1b8cec3554176271075c50d89e8b69e03fb1dbbf56e023d8754d1'
    assert out['original']['stack_labels']==out['candidate']['stack_labels']
    original=Path(guests['original']['room']['guest']).read_bytes()
    candidate=Path(guests['candidate']['room']['guest']).read_bytes()
    assert len(original)==len(candidate)
    allowed=set()
    for a,b in zip(out['original']['operands'],out['candidate']['operands']):
        assert (a['address'],a['symbol'])==(b['address'],b['symbol'])
        allowed.update(a['address']-0x40000+i for i,(x,y) in enumerate(zip(bytes.fromhex(a['encoded']),bytes.fromhex(b['encoded']))) if x!=y)
    assert {i for i,(a,b) in enumerate(zip(original,candidate)) if a!=b}==allowed
    for call in out['original']['presentation_calls']:
        at=call['address']-0x40000
        assert original[at:at+4]==candidate[at:at+4]
    files.extend(T/n for n in ('qualify_hardware_guests.py','guest_binding.py','HARDWARE-GUESTS.json',
        'build/guests01/inputs.json','build/guests01/bindings.json','BUILD-RESULT.md'))
    return dict(passed=True,arms=out,inputs={str(p.resolve()):sha(p) for p in files},
        target_access=False,rebuilt=False,
        limits='Actual retained source/ELF/producer/stack/controller/listener qualification. No physical hitcount, pixels, speed or default adoption inferred.')


if __name__=='__main__':print(json.dumps(qualify(),indent=2))
