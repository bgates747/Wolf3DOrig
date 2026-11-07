"""Exact real uncapped visible producers, independent per-arm lengths."""
from pathlib import Path
import hashlib,json,re,shutil
T=Path(__file__).resolve().parent;B=T/'build/guests01'
SOURCE=T.parent/'WOLF-PERF-012/build/guest01/source'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert json.loads((T/'build/r01/build-receipt.json').read_text())['passed']
    B.mkdir(exist_ok=False);bindings={}
    for arm in ('original','candidate'):
        module=T/'build/r01'/arm/'module/wolf_perf.vdpl';raw=module.read_bytes();size=len(raw)
        assert int.from_bytes(raw[8:12],'little')==size and 0<size<65536
        bindings[arm]={}
        for scene in ('room',):
            source=B/arm/scene/'source'
            shutil.copytree(SOURCE,source,ignore=shutil.ignore_patterns('*.bin','*.lst','*.log'))
            for name,key,old,new in [('wolf3d_vdplet_package.inc','W3D_VDPLET_PACKAGE_BYTES',24420,size),('wolf3d_vdplet_client.inc','W3D_VDPLET_PACKAGE_LIMIT',24421,size+1)]:
                p=source/name;text=p.read_text();pattern=r'(?m)^('+key+r':\s+equ )'+str(old)+r'$'
                assert len(re.findall(pattern,text))==1
                p.write_text(re.sub(pattern,lambda m:m[1]+str(new),text))
            bindings[arm][scene]=dict(source=str(source),guest=str(source/'wolf3d.bin'),listing=str(source/'wolf3d.lst'),module=str(module),module_sha256=sha(module),package_bytes=size,package_limit=size+1,remote_name=f'b-{arm}-{scene}.bin')
    (B/'bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
    files=[p for p in B.rglob('*') if p.is_file()]
    (B/'inputs.json').write_text(json.dumps({str(p):sha(p) for p in files},indent=2)+'\n')
if __name__=='__main__':main()
