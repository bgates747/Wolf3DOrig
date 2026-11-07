"""Bounded ascending per-texture column chains, from a926."""
from pathlib import Path
import difflib,hashlib,json,shutil
T=Path(__file__).resolve().parent;B=T/'build/r01'
BASE=T.parent/'WOLF-PERF-009/build/r01/candidate'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    for n,d in json.loads((T/'SOURCE-PINS.json').read_text())['files'].items():assert sha(n)==d,n
    B.mkdir(parents=True,exist_ok=False);patches=[]
    edits=[
        ("""    bool needed[128];
    clear_bytes(needed, 0, sizeof(needed));
    for (int col = 0; col < kViewWidth; ++col) {
        if (heights[col] <= 0) continue;
        const uint8_t id = wall_texture_id(world, tiles[col]);
        if (id >= 1 && id <= W3P_MAX_WALL_TEXTURE) needed[id] = true;
    }""",
         """    static_assert(kViewWidth == 256, "column-chain byte domain changed");
    static_assert(W3P_MAX_WALL_TEXTURE < 128, "column-chain head domain changed");
    uint16_t heads[128];
    uint8_t next[kViewWidth];
    for (int id = 0; id < 128; ++id) heads[id] = kViewWidth;
    clear_bytes(next, 0, sizeof(next));
    for (int col = kViewWidth - 1; col >= 0; --col) {
        if (heights[col] <= 0) continue;
        const uint8_t id = wall_texture_id(world, tiles[col]);
        if (id < 1 || id > W3P_MAX_WALL_TEXTURE) continue;
        next[col] = heads[id] < kViewWidth
            ? static_cast<uint8_t>(heads[id]) : static_cast<uint8_t>(col);
        heads[id] = static_cast<uint16_t>(col);
    }"""),
        ('        if (!needed[id]) continue;', '        if (heads[id] == kViewWidth) continue;'),
        ("""        for (int col = 0; col < kViewWidth; ++col) {
            if (heights[col] <= 0 || wall_texture_id(world, tiles[col]) != id)
                continue;
            const int full_height = heights[col];""",
         """        for (int col = heads[id]; col < kViewWidth;
             col = next[col] == col ? kViewWidth : next[col]) {
            const int full_height = heights[col];"""),
    ]
    for arm in ('original','candidate'):
        a=B/arm;a.mkdir()
        for n in ('native-source','production','qualification','sdk'):shutil.copytree(BASE/n,a/n,ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(BASE/'wolf3d_tables.inc',a/'wolf3d_tables.inc')
        if arm=='candidate':
            for folder in ('production','native-source'):
                p=a/folder/'wolf3d_renderer.cpp';old=p.read_text()
                new=old
                for needle,replacement in edits:
                    assert new.count(needle)==1
                    new=new.replace(needle,replacement,1)
                p.write_text(new)
                patches.append(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original/'+folder+'/wolf3d_renderer.cpp',tofile='candidate/'+folder+'/wolf3d_renderer.cpp')))
    assert (B/'candidate/production/wolf3d_renderer.cpp').read_bytes()==(B/'candidate/native-source/wolf3d_renderer.cpp').read_bytes()
    (T/'renderer.patch').write_text('\n'.join(patches))
    files=[p for p in B.rglob('*')if p.is_file()]+[p for p in T.iterdir()if p.is_file()]
    files += [T.parent/'WOLF-PERF-007'/n for n in ('test_equivalence.cpp','test_spans.cpp')]
    (B/'inputs.json').write_text(json.dumps({'contract':'3b55782','inputs':{str(p):sha(p)for p in files}},indent=2)+'\n')
if __name__=='__main__':main()
