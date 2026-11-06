"""Copy real benchmark producers and bind only exact per-arm package lengths."""
from pathlib import Path
import hashlib,json,shutil
T=Path(__file__).resolve().parent;B=T/'build/guests02';P3=T.parent/'WOLF-PERF-003'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def prepare():
    B.mkdir(exist_ok=False);manifest={};bindings={}
    for arm in ('original','candidate'):
        module=T/'build/r02'/arm/'module/wolf_perf.vdpl';blob=module.read_bytes()
        size=len(blob);assert int.from_bytes(blob[8:12],'little')==size
        assert size=={'original':19876,'candidate':19896}[arm]
        bindings[arm]={}
        for mode in ('control','unpaced'):
            old=P3/'build/hardware05/vdplet'/mode/'source';out=B/arm/mode/'source'
            shutil.copytree(old,out,ignore=shutil.ignore_patterns('*.bin','*.lst','*.log'))
            for name,key,oldvalue,newvalue in [('wolf3d_vdplet_package.inc','W3D_VDPLET_PACKAGE_BYTES',19876,size),('wolf3d_vdplet_client.inc','W3D_VDPLET_PACKAGE_LIMIT',19877,size+1)]:
                p=out/name;s=p.read_text()
                import re
                pattern=r'(?m)^('+key+r':\s+equ )'+str(oldvalue)+r'$'
                assert len(re.findall(pattern,s))==1
                p.write_text(re.sub(pattern,lambda m:m[1]+str(newvalue),s))
            for p in out.iterdir():
                if p.is_file():
                    if p.name not in ('wolf3d_vdplet_package.inc','wolf3d_vdplet_client.inc'):assert p.read_bytes()==(old/p.name).read_bytes()
                    manifest[str(p.relative_to(B))]=sha(p)
            bindings[arm][mode]=dict(module=str(module),module_sha256=sha(module),package_bytes=size,package_limit=size+1,
                guest=str(out/'wolf3d.bin'),listing=str(out/'wolf3d.lst'),source=str(out),
                reference_guest=str(old/'wolf3d.bin'),reference_listing=str(old/'wolf3d.lst'),
                remote_name=f'b-{arm}-{mode}.bin')
    (B/'source-freeze.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (B/'bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
    print('Prepared four actual producers; only candidate PACKAGE_BYTES/LIMIT differ.')
if __name__=='__main__':prepare()
