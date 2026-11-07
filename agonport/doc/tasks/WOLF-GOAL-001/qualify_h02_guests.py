"""File-only join of existing qualified source, target and three real producers."""
from pathlib import Path
import hashlib,json,re
import h02_guest_binding as binding
T=Path(__file__).resolve().parent
sha=binding.sha

def qualify():
    guests=json.loads((T/'H02-GUESTS.json').read_text());inputs={};out={}
    def pin(p):
        p=Path(p).resolve();inputs[str(p)]=sha(p)
    for task in ('WOLF-PERF-014','WOLF-PERF-015'):
        q=T.parent/task
        assert json.loads((q/'build/r01/build-receipt.json').read_text())['passed']
        assert json.loads((q/'build/guests01/receipt.json').read_text())['passed']
        historical=json.loads((q/'build/r01/inputs.json').read_text())['inputs']
        archived=json.loads((q/'build/r01/frozen-inputs/index.json').read_text())
        for name,digest in historical.items():
            saved=Path(archived[name]['snapshot'])
            assert archived[name]['sha256']==digest and sha(saved)==digest,name
            pin(saved)
            # Only post-qualification checklist disposition may use archive.
            if Path(name).name!='PLAN.md': assert sha(name)==digest,name
        for name,digest in json.loads((q/'build/guests01/inputs.json').read_text()).items():
            assert sha(name)==digest,name;pin(name)
        for rel in ('build/r01/inputs.json','build/r01/frozen-inputs/index.json','build/r01/build-receipt.json','build/guests01/inputs.json','build/guests01/bindings.json','build/guests01/receipt.json','BUILD-RESULT.md'):
            pin(q/rel)
    for arm,modes in guests.items():
        g=modes['room'];r=binding.verify(g);out[arm]=r
        for name in ('module','guest','listing'):pin(g[name])
        source=Path(g['source']);bench=(source/'bench.inc').read_text()
        loop=bench.split('wp_next:',1)[1].split('call wp_prt_stop',1)[0]
        assert loop.count('call w3d_vdu_present')==1 and '@pace:'not in loop
        assert loop.startswith('\n    ld hl,(wp_n)\n    inc hl\n')
        assert re.search(r'call w3d_vdu_present\s*;[^\n]*\n\s*call w3d_audio_wait_for_vdp_ingress\s*\n\s*jp c,wp_failed',loop)
        receipt=json.loads((source.parents[2]/'receipt.json').read_text())
        old_arm='original'if arm=='original'else'candidate'
        old=receipt['arms'][old_arm]['room']
        assert r=={k:v for k,v in old.items()if k in r}
        blob=Path(g['guest']).read_bytes()
        listing=Path(g['listing']).read_text()
        for call in old['presentation_calls']:
            name=call['target'];m=re.search(r'^([0-9A-F]{6})[^\n]*\b'+name+r':',listing,re.M);assert m
            at=call['address']-0x40000
            assert blob[at:at+4]==b'\xcd'+int(m[1],16).to_bytes(3,'little')
        out[arm]['presentation_calls']=old['presentation_calls']
    original=Path(guests['original']['room']['guest']).read_bytes()
    assert hashlib.sha256(original).hexdigest()=='c43e7fe74148517c30cf9bf83854cf0cf297aeaf8c4684a4624c93849b46df58'
    for arm in ('cache','trig'):
        blob=Path(guests[arm]['room']['guest']).read_bytes();assert len(blob)==len(original)
        assert out[arm]['stack_labels']==out['original']['stack_labels']
        assert out[arm]['presentation_calls']==out['original']['presentation_calls']
        allowed=set()
        for x,y in zip(out['original']['operands'],out[arm]['operands']):
            assert (x['address'],x['symbol'])==(y['address'],y['symbol'])
            allowed.update(x['address']-0x40000+i for i,(u,v)in enumerate(zip(bytes.fromhex(x['encoded']),bytes.fromhex(y['encoded'])))if u!=v)
        assert {i for i,(u,v)in enumerate(zip(original,blob))if u!=v}==allowed
    return dict(passed=True,arms=out,inputs=inputs,target_access=False,rebuilt=False,
                limits='Existing native code/resource and host parity evidence rejoined; no new target execution or three-arm physical outcome.')
if __name__=='__main__':print(json.dumps(qualify(),indent=2))
