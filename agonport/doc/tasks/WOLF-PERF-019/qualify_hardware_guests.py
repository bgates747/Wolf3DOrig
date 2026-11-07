"""File-only rejoin of retained019/015 qualification and selected three room producers."""
from pathlib import Path
import hashlib,json
import guest_binding
T=Path(__file__).resolve().parent
sha=guest_binding.sha

def qualify():
    files=[]
    for task in ('WOLF-PERF-019','WOLF-PERF-015'):
        q=T.parent/task
        for rel in ('build/r01/build-receipt.json','build/guests01/receipt.json'):
            assert json.loads((q/rel).read_text())['passed'];files.append(q/rel)
        old=json.loads((q/'build/r01/inputs.json').read_text())['inputs']
        archive=json.loads((q/'build/r01/frozen-inputs/index.json').read_text())
        for name,digest in old.items():
            saved=Path(archive[name]['snapshot']);assert sha(saved)==digest,name;files.append(saved)
            if Path(name).name!='PLAN.md':assert sha(name)==digest,name
        for name,digest in json.loads((q/'build/guests01/inputs.json').read_text()).items():
            assert sha(name)==digest,name;files.append(Path(name))
        for rel in ('build/r01/inputs.json','build/r01/frozen-inputs/index.json','build/guests01/inputs.json','build/guests01/bindings.json','build/guests01/receipt.json','BUILD-RESULT.md'):
            files.append(q/rel)
    guests=json.loads((T/'HARDWARE-GUESTS.json').read_text());out={}
    assert set(guests)=={'original','chains','trig'}
    for arm in guests:
        assert set(guests[arm])=={'room'};g=guests[arm]['room'];result=guest_binding.verify(g)
        q=T if arm!='trig' else T.parent/'WOLF-PERF-015'
        receipt=json.loads((q/'build/guests01/receipt.json').read_text());prior=receipt['arms']['original' if arm=='original' else 'candidate']['room'];assert result=={k:v for k,v in prior.items()if k in result}
        binary=Path(g['guest']).read_bytes();original=Path(guests['original']['room']['guest']).read_bytes()
        original_checks=guest_binding.verify(guests['original']['room'])
        assert result['stack_labels']==original_checks['stack_labels']
        for call in prior['presentation_calls']:
            assert binary[call['address']-0x40000:call['address']-0x40000+4]==original[call['address']-0x40000:call['address']-0x40000+4]
        out[arm]=dict(**result,presentation_calls=prior['presentation_calls'])
        files += [Path(g[n])for n in ('module','listing','guest')]
        root=q/'build/r01'/('original' if arm=='original' else 'candidate')/'module'
        files += [p for p in root.iterdir()if p.is_file()and p.suffix in ('.elf','.json','.su','.txt','.map')]
    assert out['original']['guest_sha256']=='c43e7fe74148517c30cf9bf83854cf0cf297aeaf8c4684a4624c93849b46df58'
    original=Path(guests['original']['room']['guest']).read_bytes()
    for arm in ('chains','trig'):
        candidate=Path(guests[arm]['room']['guest']).read_bytes();allowed=set()
        for a,b in zip(out['original']['operands'],out[arm]['operands']):
            assert (a['address'],a['symbol'])==(b['address'],b['symbol'])
            allowed.update(a['address']-0x40000+i for i,(x,y)in enumerate(zip(bytes.fromhex(a['encoded']),bytes.fromhex(b['encoded'])))if x!=y)
        assert len(original)==len(candidate)and {i for i,(a,b)in enumerate(zip(original,candidate))if a!=b}==allowed
    for rel in ('build/r01/code-result.json','build/r01/nested-stack-source.json','build/r01/chains-check.log','build/r01/room-census.log','count_room.cpp','test_chains.cpp'):files.append(T/rel)
    return dict(passed=True,arms=out,inputs={str(p.resolve()):sha(p)for p in files},target_access=False,rebuilt=False,limits='Retained real source/target/host/scalar-alias/canonical-room work/producers rejoined; no physical timing or sampled native branch events.')
if __name__=='__main__':print(json.dumps(qualify(),indent=2))
