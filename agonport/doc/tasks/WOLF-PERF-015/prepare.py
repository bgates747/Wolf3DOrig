"""Exact whole-degree setup table only; retain fine ray normalization/data."""
from pathlib import Path
import difflib, hashlib, json, re, shutil
T = Path(__file__).resolve().parent
B = T/'build/r01'
BASE = T.parent/'WOLF-PERF-009/build/r01/candidate'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    for n,d in json.loads((T/'SOURCE-PINS.json').read_text())['files'].items():
        assert sha(n)==d,n
    B.mkdir(parents=True,exist_ok=False)
    table=(BASE/'wolf3d_tables.inc').read_text()
    pattern=r'static const int32_t kWolfSinQuarter\[901\] __attribute__\(\(aligned\(4\)\)\) = \{(.*?)\};'
    matches=list(re.finditer(pattern,table,re.S));assert len(matches)==1
    quarter=[int(x) for x in re.findall(r'-?\d+',matches[0][1])]
    assert len(quarter)==901 and quarter[0]==0 and quarter[-1]==65536
    degree=[]
    for d in range(360):
        q,r=divmod(d,90)
        degree.append((quarter[r*10],quarter[900-r*10],-quarter[r*10],-quarter[900-r*10])[q])
    assert [degree[x] for x in (0,90,180,270)]==[0,65536,0,-65536]
    declaration='static const int32_t kWolfSinDegree[360] __attribute__((aligned(4))) = {\n'
    declaration+=''.join('    '+', '.join(str(x)for x in degree[i:i+8])+',\n' for i in range(0,360,8))+'};'
    replacement=table[:matches[0].start()]+declaration+table[matches[0].end():]
    # Independent test oracle retains the actual full quarter values and logic.
    (T/'test_sine_reference.inc').write_text(matches[0][0].replace('kWolfSinQuarter','kOriginalSinQuarter')+'\n')
    patches=[]
    for arm in ('original','candidate'):
        a=B/arm;a.mkdir()
        for n in ('native-source','production','qualification','sdk'):
            shutil.copytree(BASE/n,a/n,ignore=shutil.ignore_patterns('__pycache__'))
        (a/'wolf3d_tables.inc').write_text(table if arm=='original' else replacement)
        if arm=='candidate':
            for folder in ('production','native-source'):
                p=a/folder/'wolf3d_renderer.cpp';old=p.read_text()
                begin=old.index('int32_t sin_fine(');end=old.index('void fill_rect(',begin)
                new=old[:begin]+old[end:]
                before='''    const int32_t fine = static_cast<int32_t>(world.player.angle) * 10;
    ViewState view;
    view.sine = sin_fine(fine);
    view.cosine = cos_fine(fine);'''
                after='''    const uint32_t degree = static_cast<uint32_t>(world.player.angle) % 360u;
    ViewState view;
    view.sine = kWolfSinDegree[degree];
    view.cosine = kWolfSinDegree[(degree + 90u) % 360u];'''
                assert new.count(before)==1
                new=new.replace(before,after,1)
                assert new.count('normalize_fine(')==2 and 'sin_fine('not in new and 'cos_fine('not in new
                p.write_text(new)
                patches.append(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original/'+folder+'/wolf3d_renderer.cpp',tofile='candidate/'+folder+'/wolf3d_renderer.cpp')))
    patches.append(''.join(difflib.unified_diff(table.splitlines(True),replacement.splitlines(True),fromfile='original/wolf3d_tables.inc',tofile='candidate/wolf3d_tables.inc')))
    (T/'renderer.patch').write_text('\n'.join(patches))
    assert (B/'candidate/production/wolf3d_renderer.cpp').read_bytes()==(B/'candidate/native-source/wolf3d_renderer.cpp').read_bytes()
    files=[p for p in B.rglob('*')if p.is_file()]+[p for p in T.iterdir()if p.is_file()]
    files += [T.parent/'WOLF-PERF-007'/n for n in ('test_equivalence.cpp','test_spans.cpp')]
    (B/'inputs.json').write_text(json.dumps({'contract':'5132189','inputs':{str(p):sha(p)for p in files}},indent=2)+'\n')

if __name__=='__main__':main()
