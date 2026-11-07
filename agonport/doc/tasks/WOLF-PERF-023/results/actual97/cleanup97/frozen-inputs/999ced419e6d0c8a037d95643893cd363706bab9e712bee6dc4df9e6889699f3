"""Exact real uncapped visible producers, independent per-arm lengths."""
from pathlib import Path
import hashlib,json,re,shutil
T=Path(__file__).resolve().parent;B=T/'build/guests01'
SOURCE=T.parent/'WOLF-PERF-021/build/guests01/candidate/room/source'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert json.loads((T/'build/r01/build-receipt.json').read_text())['passed']
    assert json.loads((T/'build/r01/byte-loop-audit.json').read_text())['passed']
    assert sha(SOURCE/'wolf3d.bin')=='6180358376c1b8cec3554176271075c50d89e8b69e03fb1dbbf56e023d8754d1'
    selected=json.loads((T.parent/'WOLF-PERF-022/build/hardware02/kit.json').read_text())['inputs']
    donor_files=[p for p in SOURCE.rglob('*') if p.is_file() and p.suffix not in ('.bin','.lst','.log') and '__pycache__' not in p.parts]
    for p in donor_files: assert sha(p)==selected[str(p.resolve())],p
    B.mkdir(exist_ok=False);bindings={}
    for arm in ('original','candidate'):
        module=T/'build/r01'/arm/'module/wolf_perf.vdpl';raw=module.read_bytes();size=len(raw)
        assert int.from_bytes(raw[8:12],'little')==size and 0<size<65536
        bindings[arm]={}
        for scene in ('room',):
            source=B/arm/scene/'source'
            shutil.copytree(SOURCE,source,ignore=shutil.ignore_patterns('*.bin','*.lst','*.log','__pycache__'))
            for name,key,old,new in [('wolf3d_vdplet_package.inc','W3D_VDPLET_PACKAGE_BYTES',22572,size),('wolf3d_vdplet_client.inc','W3D_VDPLET_PACKAGE_LIMIT',22573,size+1)]:
                p=source/name;text=p.read_text();pattern=r'(?m)^('+key+r':\s+equ )'+str(old)+r'$'
                assert len(re.findall(pattern,text))==1
                p.write_text(re.sub(pattern,lambda m:m[1]+str(new),text))
            bindings[arm][scene]=dict(source=str(source),guest=str(source/'wolf3d.bin'),listing=str(source/'wolf3d.lst'),module=str(module),module_sha256=sha(module),package_bytes=size,package_limit=size+1,remote_name=f'b-{arm}-{scene}.bin')
    (B/'bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
    files=[p for p in B.rglob('*') if p.is_file()]+donor_files
    files += [T/n for n in ('prepare_guests.py','build_guests.py','guest_binding.py','HARDWARE-PLAN.md')]
    files += [T.parents[3]/'src/asm/wolf3d/tgt/.tools/ez80asm']
    files += [Path(bindings[a]['room']['module']) for a in bindings]
    (B/'inputs.json').write_text(json.dumps({str(p):sha(p) for p in files},indent=2)+'\n')
if __name__=='__main__':main()
