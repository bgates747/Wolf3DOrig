"""File-only original-method candidate; preserve exact physical69 O2 control."""
from pathlib import Path
import hashlib,json,shutil,difflib
from generate_tables import write
T=Path(__file__).resolve().parent;BASE=T.parent/'WOLF-PERF-006/build/r01/candidate';B=T/'build/r01'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    pins=json.loads((T/'SOURCE-PINS.json').read_text())
    for p,digest in pins['files'].items():assert sha(p)==digest,p
    B.mkdir(parents=True,exist_ok=False)
    for arm in ('original','candidate'):
        a=B/arm;a.mkdir()
        for name in ('native-source','production','qualification','sdk'):
            shutil.copytree(BASE/name,a/name,ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(BASE/'wolf3d_tables.inc',a/'wolf3d_tables.inc')
    table=write(B/'original_tangents.inc')
    changes=[]
    for folder in ('native-source','production'):
        p=B/'candidate'/folder/'wolf3d_renderer.cpp';old=p.read_text();new=old
        new=new.replace('#include "wolf3d_renderer.h"','#include "wolf3d_renderer.h"\n#include "original_raywalk.h"',1)
        start=new.index('int32_t fixed_div(');end=new.index('\nint32_t normalize_fine(',start)
        new=new[:start]+new[end+1:]
        start=new.index('struct PushwallHit {');end=new.index('int32_t projected_height(',start)
        new=new[:start]+new[end:]
        start=new.index('RenderDetail cast_walls(');end=new.index('\nuint8_t wall_texture_id(',start)
        new=new[:start]+(T/'cast_walls.inc').read_text()+new[end:]
        p.write_text(new)
        shutil.copyfile(T/'original_raywalk.h',p.parent/'original_raywalk.h')
        shutil.copyfile(B/'original_tangents.inc',p.parent/'original_tangents.inc')
        changes.append(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original/'+folder,tofile='candidate/'+folder)))
    assert (B/'candidate/production/wolf3d_renderer.cpp').read_bytes()==(B/'candidate/native-source/wolf3d_renderer.cpp').read_bytes()
    (B/'renderer.patch').write_text('\n'.join(changes))
    (B/'table-generation.json').write_text(json.dumps(table,indent=2)+'\n')
    files=[p for p in B.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [T/n for n in ('PLAN.md','PRE-CODE.md','DESIGN-01.md','SOURCE-PINS.json','prepare.py','generate_tables.py','original_raywalk.h','cast_walls.inc','test_original_raywalk.cpp')]
    (B/'inputs.json').write_text(json.dumps(dict(control_sha256=pins['baseline_module_sha256'],design_freeze='6d28a4d',inputs={str(p):sha(p) for p in files}),indent=2)+'\n')
    print('Prepared exact O2 source control and original tangent/intercept candidate; no build/target operation.')
if __name__=='__main__':main()
