"""File-only private Fab bridge/real producer preparation. No remote workload."""
from pathlib import Path
import argparse,json,hashlib,shutil,re
T=Path(__file__).resolve().parent;P3=T.parent/'WOLF-PERF-003';B=T/'build/visual02'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main(shim):
    assert sha(shim)=='7d9f52a705776bf9db3ab84d16fcf66902a589e3a494ff42103fda27f60315e4'
    B.mkdir(exist_ok=False)
    base=P3/'build/fabbridge01'
    frozen=json.loads((base/'source-freeze.json').read_text())['files']
    for name,digest in frozen.items():assert sha(base/name)==digest,name
    bindings={};files={}
    for arm in ('original','candidate'):
        a=B/arm;a.mkdir();target=T/'build/r01'/arm;module=target/'module/wolf_perf.vdpl';size=module.stat().st_size
        assert int.from_bytes(module.read_bytes()[8:12],'little')==size and size<65536
        bridge=a/'bridge';bridge.mkdir()
        for name in frozen:
            if name.startswith(('video/host-module/','video/expected_package.h')):continue
            q=bridge/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/name,q)
        production=bridge/'video/host-module/production'
        shutil.copytree(target/'production',production)
        shutil.copytree(target/'qualification',production.parent/'qualification')
        shutil.copyfile(target/'wolf3d_tables.inc',production.parent/'wolf3d_tables.inc')
        (bridge/'video/expected_package.h').write_text('static const unsigned char wolf_expected_package[]={'+','.join(map(str,module.read_bytes()))+'};\n')
        shutil.copyfile(T/'visual_build.py',bridge/'build.py')
        bridge_files={str(p.relative_to(bridge)):sha(p) for p in bridge.rglob('*') if p.is_file()}
        (bridge/'source-freeze.json').write_text(json.dumps(dict(files=bridge_files),indent=2)+'\n')
        src=a/'guest/source';old=P3/'build/fab-b-guest01/source'
        shutil.copytree(old,src,ignore=shutil.ignore_patterns('*.bin','*.lst','*.log'))
        for name,key,value in (('wolf3d_vdplet_package.inc','W3D_VDPLET_PACKAGE_BYTES',size),('wolf3d_vdplet_client.inc','W3D_VDPLET_PACKAGE_LIMIT',size+1)):
            p=src/name;s=p.read_text();pattern=r'(?m)^('+key+r':\s+equ )\d+$';assert len(re.findall(pattern,s))==1
            p.write_text(re.sub(pattern,lambda m:m[1]+str(value),s))
        assert 'WP_MODE: equ 3' in (src/'wolf3d.asm').read_text()
        assert (src/'bench.inc').read_bytes()==(old/'bench.inc').read_bytes()
        for p in src.iterdir():
            if p.is_file() and p.name not in ('wolf3d_vdplet_client.inc','wolf3d_vdplet_package.inc'):
                assert p.read_bytes()==(old/p.name).read_bytes(),p.name
        bindings[arm]=dict(module=str(module),module_sha256=sha(module),package_bytes=size,package_limit=size+1,
            source=str(src),guest=str(src/'wolf3d.bin'),listing=str(src/'wolf3d.lst'))
    shutil.copyfile(P3/'four_fab_run.py',B/'retained_runner.py')
    shutil.copyfile(shim,B/'input.so')
    files={str(p.relative_to(B)):sha(p) for p in B.rglob('*') if p.is_file()}
    (B/'source-freeze.json').write_text(json.dumps(dict(files=files,bindings=bindings,fixture='Unchanged qualified Fab paced600step/720degree/noenemy/E1L1(34,36), CCOUNT omitted; no native performance claim'),indent=2)+'\n')
    (B/'bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
    print('Prepared two private exact-source bridges and real paced Fab producers; existing bench loop unchanged.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--shim',type=Path,required=True);main(p.parse_args().shim)
