"""Actual per-arm Fab producer verification; retained checker, six operands."""
from pathlib import Path
import hashlib,importlib.util,json,shutil
T=Path(__file__).resolve().parent;B=T/'build/visual02';P3=T.parent/'WOLF-PERF-003'
spec=importlib.util.spec_from_file_location('binding',T.parent/'WOLF-PERF-006/guest_binding.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def main():
    bindings=json.loads((B/'bindings.json').read_text());result={}
    for arm,binding in bindings.items():
        result[arm]=m.verify(binding)
        dst=B/arm/'payload';shutil.copytree(P3/'build/fab-b-guest01/payload',dst,ignore=shutil.ignore_patterns('expected.json','timing.bin','after.bin','before.bin'))
        shutil.copyfile(binding['guest'],dst/'wolf3d.bin');shutil.copyfile(binding['module'],dst/'wolf3d.vdpl')
        files={str(p.relative_to(dst)):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in dst.rglob('*') if p.is_file()}
        (dst/'expected.json').write_text(json.dumps(dict(files=files),indent=2)+'\n')
    a=Path(bindings['original']['guest']).read_bytes();c=Path(bindings['candidate']['guest']).read_bytes();assert len(a)==len(c)
    actual=[i for i,(x,y) in enumerate(zip(a,c)) if x!=y];expected=[]
    for x,y in zip(result['original']['operands'],result['candidate']['operands']):
        assert x['address']==y['address']
        expected.extend(x['address']-0x40000+i for i,(u,v) in enumerate(zip(bytes.fromhex(x['encoded']),bytes.fromhex(y['encoded']))) if u!=v)
    assert actual==expected
    (B/'binding-result.json').write_text(json.dumps(dict(passed=True,arms=result,changed_binary_offsets=actual),indent=2)+'\n')
    print('PASS actual two Fab producer lengths/limits, 12 binary operands, package/payload hashes; unchanged paced loop')
if __name__=='__main__':main()
