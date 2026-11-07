"""File-only rejoin of retained017 qualification and selected two room producers."""
from pathlib import Path
import hashlib,json
import guest_binding
T=Path(__file__).resolve().parent
sha=guest_binding.sha

def qualify():
    files=[]
    for rel in ('build/r01/build-receipt.json','build/guests01/receipt.json','build/projection01/receipt.json'):
        assert json.loads((T/rel).read_text())['passed'];files.append(T/rel)
    old=json.loads((T/'build/r01/inputs.json').read_text())['inputs']
    archive=json.loads((T/'build/r01/frozen-inputs/index.json').read_text())
    for name,digest in old.items():
        saved=Path(archive[name]['snapshot']);assert sha(saved)==digest,name;files.append(saved)
        if Path(name).name!='PLAN.md':assert sha(name)==digest,name
    for name,digest in json.loads((T/'build/guests01/inputs.json').read_text()).items():
        assert sha(name)==digest,name;files.append(Path(name))
    for name,digest in json.loads((T/'build/projection01/receipt.json').read_text())['inputs'].items():
        assert sha(name)==digest,name;files.append(Path(name))
    guests=json.loads((T/'HARDWARE-GUESTS.json').read_text());receipt=json.loads((T/'build/guests01/receipt.json').read_text());out={}
    assert set(guests)=={'original','candidate'}
    for arm in guests:
        assert set(guests[arm])=={'room'};g=guests[arm]['room'];result=guest_binding.verify(g)
        prior=receipt['arms'][arm]['room'];assert result=={k:v for k,v in prior.items()if k in result}
        binary=Path(g['guest']).read_bytes();original=Path(guests['original']['room']['guest']).read_bytes()
        original_checks=guest_binding.verify(guests['original']['room'])
        assert result['stack_labels']==original_checks['stack_labels']
        for call in prior['presentation_calls']:
            assert binary[call['address']-0x40000:call['address']-0x40000+4]==original[call['address']-0x40000:call['address']-0x40000+4]
        out[arm]=dict(**result,presentation_calls=prior['presentation_calls'])
        files += [Path(g[n])for n in ('module','listing','guest')]
        root=T/'build/r01'/arm/'module'
        files += [p for p in root.iterdir()if p.is_file()and p.suffix in ('.elf','.json','.su','.txt','.map')]
    assert out['original']['guest_sha256']=='c43e7fe74148517c30cf9bf83854cf0cf297aeaf8c4684a4624c93849b46df58'
    original=Path(guests['original']['room']['guest']).read_bytes();candidate=Path(guests['candidate']['room']['guest']).read_bytes();allowed=set()
    for a,b in zip(out['original']['operands'],out['candidate']['operands']):
        assert (a['address'],a['symbol'])==(b['address'],b['symbol'])
        allowed.update(a['address']-0x40000+i for i,(x,y)in enumerate(zip(bytes.fromhex(a['encoded']),bytes.fromhex(b['encoded'])))if x!=y)
    assert len(original)==len(candidate)and {i for i,(a,b)in enumerate(zip(original,candidate))if a!=b}==allowed
    for rel in ('build/r01/native-body-binding.json','build/r01/code-result.json','build/r01/inputs.json','build/r01/frozen-inputs/index.json','build/guests01/inputs.json','build/guests01/bindings.json','build/projection01/coverage.log','PROJECTION-DOMAIN.md','PROJECTION-DOMAIN-PINS.json','PROJECTION-RESULT.md','NATIVE-LOWERING.md','BUILD-RESULT.md'):files.append(T/rel)
    return dict(passed=True,arms=out,inputs={str(p.resolve()):sha(p)for p in files},target_access=False,rebuilt=False,limits='Retained real source/target/host/projection arithmetic/producers rejoined; no physical timing or sampled native branch events.')
if __name__=='__main__':print(json.dumps(qualify(),indent=2))
