"""Build only revised negative controls; normal Pi serial compiler lease required."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess,sys

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def replace(text,old,new):
 assert text.count(old)==1,old
 return text.replace(old,new,1)

def main():
 out=HERE/'build/controls01-r02';out.mkdir(exist_ok=False);records={}
 spec=importlib.util.spec_from_file_location('control_game_builder',HERE/'build/r05/inputs/game-builder.py');builder=importlib.util.module_from_spec(spec);sys.modules[spec.name]=builder;spec.loader.exec_module(builder)
 assembler=builder.resolve_assembler(None)
 for backend in ('bespoke','vdplet'):
  donor=HERE/'build/r05'/backend/'cpu-fail';dest=out/backend
  shutil.copytree(donor/'source',dest/'source',ignore=shutil.ignore_patterns('*.lst','wp*.bin'))
  shutil.copytree(donor/'payload',dest/'payload')
  source=dest/'source';bench=source/'bench.inc';text=bench.read_text();before=sha(bench)
  marker='    jp wp_failed ; '+('owned-timer'if backend=='bespoke'else'intentional owned-timer')+' failure control\n'
  text=replace(text,marker,'    ld a,1\n    ld (wp_expected_abort),a\n    jp wp_failed ; selected restoration control\n')
  text=replace(text,'@hold: jr @hold\n','''    ; Only the selected direct failure returns. Unexpected failures still hold.
    ld a,(wp_expected_abort)
    or a
    jr z,@hold
    ld a,(wp_restored)
    or a
    jr z,@hold
    in0 a,(092h)
    ld b,a
    ld a,(wp_old_iss)
    cp b
    jr nz,@hold
    in0 a,(083h)
    and 07eh
    ld b,a
    ld a,(wp_old_ctl)
    and 07eh
    cp b
    jr nz,@hold
    ; Unwind the exact wp_run entry frame, then use ordinary game shutdown.
    ld hl,(wp_entry_sp)
    ld sp,hl
    pop iy
    pop ix
    ld hl,wp_control_return_msg
    call printString
    ret
@hold: jr @hold
wp_expected_abort: db 0
wp_control_return_msg: db "WOLF-PERF-003 CONTROL REGISTERS-RESTORED RETURN",13,10,0
''')
  bench.write_text(text)
  with (dest/'assemble.log').open('w')as log:
   subprocess.run([str(assembler),'wolf3d.asm','control.bin','-l','-c'],cwd=source,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)
  shutil.copyfile(source/'control.bin',dest/'payload/wolf3d.bin')
  assert 0x40000+(dest/'payload/wolf3d.bin').stat().st_size<(0xa0000 if backend=='vdplet'else 0xb0000)
  payload=dest/'payload';inventory={str(p.relative_to(payload)):{'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(payload.rglob('*'))if p.is_file()and p.name!='expected.json'}
  (payload/'expected.json').write_text(json.dumps({'schema':'wolf-perf003-payload-v1','backend':backend,'mode':'cpu-fail-return','files':inventory},indent=2)+'\n')
  records[backend]={'donor':'r05/'+backend+'/cpu-fail','donor_bench_sha256':before,'source':{str(p.relative_to(source)):sha(p)for p in sorted(source.rglob('*'))if p.is_file()and p.suffix not in ('.lst','.bin')},'outputs':inventory}
 (out/'build.json').write_text(json.dumps(records,indent=2)+'\n')
 print('two restoration/normal-return controls built; timed guests/firmware unchanged')

if __name__=='__main__':main()
