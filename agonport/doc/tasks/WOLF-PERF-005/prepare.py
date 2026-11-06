"""File-only span candidate preparation from exact physical63 control."""
from pathlib import Path
import hashlib,json,shutil,difflib
T=Path(__file__).resolve().parent;P4=T.parent/'WOLF-PERF-004';P3=T.parent/'WOLF-PERF-003'
BASE=P4/'build/r03/candidate';B=T/'build/r02';SDK=P3/'build/r04/inputs/sdk'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
OLD='''    while (count-- != 0) put_pixel(target, x++, y, color);'''
NEW='''    if (count == 0) return;
    uint8_t *const row = reinterpret_cast<uint8_t *>(target.rows[y]);
    uint32_t mapped_x = target.x_bias + x;
    const uint32_t pixel_xor = target.pixel_xor;
    const uint8_t preserve_mask = target.preserve_mask;
    const uint8_t color_bits = static_cast<uint8_t>(color & target.color_mask);
    while (count-- != 0) {
        uint8_t *const pixel = row + (mapped_x++ ^ pixel_xor);
        *pixel = static_cast<uint8_t>((*pixel & preserve_mask) | color_bits);
    }'''

def main():
    assert sha(BASE/'native-source/wolf3d_renderer.cpp')=='be04d1a8511c8ccee6a4d8d39800c8b3bde45b54d63d7e8a7f06c89d76424adb'
    assert sha(BASE/'module/wolf_perf.vdpl')=='54568e4534a8d8af16c4122ed086d38489668aa7270042645a68063448bb7055'
    B.mkdir(parents=True,exist_ok=False)
    for arm in ('original','candidate'):
        a=B/arm;a.mkdir()
        for n in ('native-source','production','qualification'):shutil.copytree(BASE/n,a/n)
        shutil.copyfile(BASE/'wolf3d_tables.inc',a/'wolf3d_tables.inc')
        for n in ('native-source','production'):
            p=a/n/'wolf3d_renderer.cpp';raw=p.read_text();assert raw.count(OLD)==1
            if arm=='candidate':
                changed=raw.replace(OLD,NEW,1);p.write_text(changed)
                (B/(n+'-candidate.patch')).write_text(''.join(difflib.unified_diff(raw.splitlines(True),changed.splitlines(True),fromfile='54568/'+n,tofile='span/'+n)))
        assert (a/'native-source/wolf3d_renderer.cpp').read_bytes()==(a/'production/wolf3d_renderer.cpp').read_bytes()
    pins={}
    for root in (SDK,B):
        for p in sorted(root.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:pins[str(p)]=sha(p)
    for n in ('prepare.py','build.py','test_spans.cpp','test_equivalence.cpp','test_fixed_div.cpp','PLAN.md','PRE-CODE.md'):pins[str(T/n)]=sha(T/n)
    (B/'inputs.json').write_text(json.dumps(dict(task='WOLF-PERF-005',plan_freeze='36fbd5f',inputs=pins,control='54568',scope='Only direct bytewise fill_span invariant hoisting; linear/other methods/target helpers unchanged'),indent=2)+'\n')
    print('Prepared task-only original/candidate with exact physical63 control')

if __name__=='__main__':main()
