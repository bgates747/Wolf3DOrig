"""Compile frozen task-owned guests/module. Requires the normal Pi build lease."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys
from types import SimpleNamespace
from instrument import standalone_bench, standalone_guest
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def select_mode(text,mode):
    result=[];stack=[];active=True
    for line in text.splitlines():
        token=line.strip()
        if token.startswith('.if WP_MODE'):
            expr=token[len('.if WP_MODE'):].strip(); op,n=expr[0],int(expr[1:])
            condition=(mode==n if op=='=' else mode>n)
            stack.append((active,condition));active=active and condition
        elif token=='.else':
            parent,condition=stack[-1];active=parent and not condition
        elif token=='.endif':active=stack.pop()[0]
        elif active:result.append(line)
    assert not stack
    return '\n'.join(result)+'\n'


def build(revision):
    base=HERE/'build'/revision
    manifest=json.loads((base/'inputs.json').read_text());inputs=base/'inputs'
    for relative,item in manifest['bindings'].items():
        assert sha(inputs/relative)==item['sha256'],relative
    # The donor imports the production build/asset/assembler helpers. Require
    # the exact snapshotted game builder and all common assets before that call.
    assert sha(ROOT/'src/asm/wolf3d/scripts/build.py')==sha(inputs/'game-builder.py')
    donor=load('perf003_donor',inputs/'donor/build.py')
    # The donor uses only require_open from the older acceptance generator.
    # Keep this bounded validation independent of its unrelated PIL imports.
    original_load=donor.load
    def require_open(level,tile):
        x,y=tile
        if not 0<=x<64 or not 0<=y<64 or level.sections['tilemap'][y*64+x]!=0:
            raise ValueError('fixture tile is not open')
    def donor_load(name,path):
        if name=='wolf_acceptance':return SimpleNamespace(require_open=require_open)
        return original_load(name,path)
    donor.load=donor_load
    driver=base/'fixture-builder';(driver/'src').mkdir(parents=True,exist_ok=False)
    raw=(inputs/'donor/bench.inc').read_text()
    # Use the same standard mode-info ordered parser fence on BOTH arms;
    # neither INFO0 nor its runtime diagnostic formatting is in paced timing.
    raw=raw.replace('call w3d_vdplet_query_identity','call w3d_audio_wait_for_vdp_ingress')
    raw=raw.replace('WOLF-PERF-001','WOLF-PERF-003').replace('db "WPF1",1,WP_MODE','db "WPF3",1,WP_MODE')
    raw_b=raw.replace('db 34,36,0,0 ;','db 34,36,0,2 ;')
    standalone_raw=standalone_bench(raw.replace('db 34,36,0,0 ;','db 34,36,0,1 ;'))
    # Dedicated diagnostic storage is zero-created natively, just as in A.
    # Avoid a 12 KiB zero upload under the borrowed PRT interrupt during setup.
    # No measured pose traffic or renderer work changes.
    raw_b=donor.replace(raw_b,'    ld bc,0f000h\n    ld de,12056\n    call w3d_vdplet_create_zero_buffer\n','    call wp_create_log\n')
    raw_b+='''
wp_create_log:
    ld hl,@packet
    ld bc,@end-@packet
    rst.lil 18h
    jp w3d_audio_wait_for_vdp_ingress
@packet:
    db 23,0,0a0h
    dw 0f000h
    db 2
    db 23,0,0a0h
    dw 0f000h
    db 3
    dw 12056
@end:
'''
    (driver/'src/bench.inc').write_text(raw_b)
    donor.ROOT=ROOT;donor.HERE=driver;donor.BUILD=base/'vdplet'
    donor.GAME=inputs/'game';donor.PROD=inputs/'module';donor.SDK=inputs/'sdk'
    donor.prepare()
    builder=load('perf003_game_builder',inputs/'game-builder.py')
    assembler=builder.resolve_assembler(None)
    for mode,label in [(1,'cpu'),(2,'unpaced'),(3,'paced'),(1,'cpu-fail')]:
        a=base/'bespoke'/label;src=a/'source'
        shutil.copytree(base/'vdplet'/label/'source',src)
        builder.select_backend(src/'wolf3d_backend.inc','standalone')
        standalone_guest(src)
        bench=select_mode(standalone_raw,mode)
        if label=='cpu-fail':
            bench=donor.replace(bench,'    call wp_prt_init\n','    call wp_prt_init\n    jp wp_failed ; owned-timer failure control\n')
        (src/'bench.inc').write_text(bench)
        shutil.copyfile(HERE/'src/standalone.inc',src/'standalone.inc')
        payload=a/'payload';shutil.copytree(base/'common-payload',payload)
        with (a/'assemble.log').open('w')as log:
            subprocess.run([str(assembler),'wolf3d.asm','wp-a.bin','-l','-c'],cwd=src,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)
        shutil.copyfile(src/'wp-a.bin',payload/'wolf3d.bin')
        image_end=0x40000+(payload/'wolf3d.bin').stat().st_size
        assert image_end<0xb0000,'MOS stack reserve overlap'
        (a/'memory-layout.json').write_text(json.dumps({'image_base':0x40000,'image_end':image_end,'stack_reserve_start':0xb0000},indent=2)+'\n')
    # Verify all non-executable common payloads after both builders finish.
    outputs={}
    for backend in ('bespoke','vdplet'):
        for label in ('cpu','unpaced','paced','cpu-fail'):
            payload=base/backend/label/'payload'
            for relative,item in manifest['payload'].items():
                assert sha(payload/relative)==item['sha256'],(backend,label,relative)
            inventory={str(p.relative_to(payload)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(payload.rglob('*')) if p.is_file() and p.name!='expected.json'}
            (payload/'expected.json').write_text(json.dumps({'schema':'wolf-perf003-payload-v1','backend':backend,'mode':label,'files':inventory},indent=2)+'\n')
            outputs[f'{backend}/{label}']=inventory
    (base/'guest-build.json').write_text(json.dumps({'schema':'wolf-perf003-guests-v1','outputs':outputs},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--revision',required=True)
    build(parser.parse_args().revision)
