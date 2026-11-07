"""One-entry exact full-height scaling setup cache, from a926."""
from pathlib import Path
import difflib,hashlib,json,shutil
T=Path(__file__).resolve().parent;B=T/'build/r01'
BASE=T.parent/'WOLF-PERF-009/build/r01/candidate'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    for n,d in json.loads((T/'SOURCE-PINS.json').read_text())['files'].items():assert sha(n)==d,n
    B.mkdir(parents=True,exist_ok=False);patches=[]
    edits=[
        ('        for (int col = 0; col < kViewWidth; ++col) {\n            if (heights[col] <= 0 || wall_texture_id(world, tiles[col]) != id)',
         '        int cached_height = 0;\n        int cached_top = 0;\n        int cached_count = 0;\n        int32_t cached_step = 0;\n        int32_t cached_fraction = 0;\n        for (int col = 0; col < kViewWidth; ++col) {\n            if (heights[col] <= 0 || wall_texture_id(world, tiles[col]) != id)'),
        ("""            const int full_height = heights[col];
            const int top = kCenterY - full_height / 2;
            const int clipped_top = top < 0 ? 0 : top;
            const int bottom = top + full_height;
            const int clipped_bottom = bottom > kViewHeight ? kViewHeight : bottom;
            const int destination_height = clipped_bottom - clipped_top;
            if (destination_height <= 0) continue;
            const int32_t step = (kTextureSize << 16) / full_height;
            draw_wall_column(frame, static_cast<uint32_t>(kViewX + col),
                             static_cast<uint32_t>(kViewY + clipped_top),
                             destination_height, span.bytes, tex_u[col],
                             step * (clipped_top - top), step);""",
         """            const int full_height = heights[col];
            if (full_height != cached_height) {
                cached_height = full_height;
                const int top = kCenterY - full_height / 2;
                cached_top = top < 0 ? 0 : top;
                const int bottom = top + full_height;
                const int clipped_bottom = bottom > kViewHeight ? kViewHeight : bottom;
                cached_count = clipped_bottom - cached_top;
                cached_step = cached_count > 0
                    ? (kTextureSize << 16) / full_height : 0;
                cached_fraction = cached_step * (cached_top - top);
            }
            if (cached_count <= 0) continue;
            draw_wall_column(frame, static_cast<uint32_t>(kViewX + col),
                             static_cast<uint32_t>(kViewY + cached_top),
                             cached_count, span.bytes, tex_u[col],
                             cached_fraction, cached_step);"""),
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
    (B/'inputs.json').write_text(json.dumps({'contract':'1d98cd8','inputs':{str(p):sha(p)for p in files}},indent=2)+'\n')
if __name__=='__main__':main()
