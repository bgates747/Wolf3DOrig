"""Exact real uncapped visible producers, independent per-arm lengths."""
from pathlib import Path
import hashlib,json,re,shutil
T=Path(__file__).resolve().parent;B=T/'build/guests01'
SOURCE=T.parent/'WOLF-PERF-012/build/guest01/source'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
POINTS=((33,36),(35,36),(34,35),(34,37),(33,35),(35,35),(33,37),(35,37))
def main():
    assert json.loads((T/'build/r01/build-receipt.json').read_text())['passed']
    B.mkdir(exist_ok=False);bindings={}
    kit=json.loads((T.parent/'WOLF-PERF-011/build/hardware02/kit.json').read_text())
    level=Path(kit['stage']['level_00/state_easy.w3l']).read_bytes()
    at=int.from_bytes(level[38:40],'little')
    assert all(level[at+x*64+y]==0 for x,y in POINTS),'Sprite location not on retained floor'
    so=int.from_bytes(level[28:30],'little');count=int.from_bytes(level[10:12],'little')
    assert any(int.from_bytes(level[so+i*6+2:so+i*6+4],'little',signed=True)==14 for i in range(count))
    for arm in ('original','candidate'):
        module=T/'build/r01'/arm/'module/wolf_perf.vdpl';raw=module.read_bytes();size=len(raw)
        assert int.from_bytes(raw[8:12],'little')==size and 0<size<65536
        bindings[arm]={}
        for scene in ('room','sprites'):
            source=B/arm/scene/'source'
            shutil.copytree(SOURCE,source,ignore=shutil.ignore_patterns('*.bin','*.lst','*.log'))
            for name,key,old,new in [('wolf3d_vdplet_package.inc','W3D_VDPLET_PACKAGE_BYTES',24420,size),('wolf3d_vdplet_client.inc','W3D_VDPLET_PACKAGE_LIMIT',24421,size+1)]:
                p=source/name;text=p.read_text();pattern=r'(?m)^('+key+r':\s+equ )'+str(old)+r'$'
                assert len(re.findall(pattern,text))==1
                p.write_text(re.sub(pattern,lambda m:m[1]+str(new),text))
            if scene=='sprites':
                p=source/'bench.inc';text=p.read_text()
                needle='    call wp_prt_init\n'
                assert text.count(needle)==1
                seed='''    ; Finite render-only sprite-rich scene, before full snapshot/warm-up.
    ld hl,wp_sprite_statics
    ld de,w3d_statics
    ld bc,8*W3D_STATIC_SIZE
    ldir
    ld a,8
    ld (w3d_static_count+0),a
    xor a
    ld (w3d_static_count+1),a
'''
                text=text.replace(needle,seed+needle,1)
                text+='\nwp_sprite_statics:\n'+''.join('    db '+','.join(map(str,(x,y,14,0,0,0)))+'\n' for x,y in POINTS)
                p.write_text(text)
                p=source/'loading_pages.inc';text=p.read_text()
                assert text.count('UNCAPPED ROTATION - NO FRAME RATE LIMIT')==1
                p.write_text(text.replace('UNCAPPED ROTATION - NO FRAME RATE LIMIT','UNCAPPED SPRITE ROTATION - NO FRAME LIMIT',1))
            bindings[arm][scene]=dict(source=str(source),guest=str(source/'wolf3d.bin'),listing=str(source/'wolf3d.lst'),module=str(module),module_sha256=sha(module),package_bytes=size,package_limit=size+1,remote_name=f'b-{arm}-{scene}.bin')
    (B/'bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
    (B/'scene.json').write_text(json.dumps(dict(points=POINTS,shape=14,actors=0,stage_level_sha256=hashlib.sha256(level).hexdigest(),floor_witness_offset=at,source=str(SOURCE)),indent=2)+'\n')
    files=[p for p in B.rglob('*') if p.is_file()]
    (B/'inputs.json').write_text(json.dumps({str(p):sha(p) for p in files},indent=2)+'\n')
if __name__=='__main__':main()
