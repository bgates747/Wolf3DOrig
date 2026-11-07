"""File-only sprite column decision hoist, from exact a926 control."""
from pathlib import Path
import difflib, hashlib, json, shutil
T=Path(__file__).resolve().parent
B=T/'build/r01'
BASE=T.parent/'WOLF-PERF-009/build/r01/candidate'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    for name,digest in json.loads((T/'SOURCE-PINS.json').read_text())['files'].items():
        assert sha(name)==digest,name
    B.mkdir(parents=True,exist_ok=False)
    patches=[]
    for arm in ('original','candidate'):
        a=B/arm;a.mkdir()
        for name in ('native-source','production','qualification','sdk'):
            shutil.copytree(BASE/name,a/name,ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(BASE/'wolf3d_tables.inc',a/'wolf3d_tables.inc')
        if arm=='candidate':
            for folder in ('native-source','production'):
                p=a/folder/'wolf3d_renderer.cpp';old=p.read_text();new=old
                first='''            int32_t y_fraction = (clipped_top - top) * y_step;
            for (int y = 0; y < height; ++y) {'''
                replacement='''            // Geometry/occlusion depend on destination column, not row.
            // Keep row-major texture/output order and all metadata untouched.
            uint8_t columns[kViewWidth];
            int32_t x_fraction = (clipped_left - left) * x_step;
            for (int x = 0; x < width; ++x) {
                int source_x = x_fraction >> 16;
                if (source_x >= kTextureSize) source_x = kTextureSize - 1;
                columns[x] = wall_heights[clipped_left + x] < size
                    ? static_cast<uint8_t>(source_x) : 0xffu;
                x_fraction += x_step;
            }
            int32_t y_fraction = (clipped_top - top) * y_step;
            for (int y = 0; y < height; ++y) {'''
                assert new.count(first)==1
                new=new.replace(first,replacement,1)
                first='''                int32_t x_fraction = (clipped_left - left) * x_step;
                for (int x = 0; x < width; ++x) {
                    const int screen_x = clipped_left + x;
                    int source_x = x_fraction >> 16;
                    if (source_x >= kTextureSize) source_x = kTextureSize - 1;
                    if (wall_heights[screen_x] < size) {'''
                replacement='''                for (int x = 0; x < width; ++x) {
                    const int screen_x = clipped_left + x;
                    const uint8_t source_x = columns[x];
                    if (source_x != 0xffu) {'''
                assert new.count(first)==1
                new=new.replace(first,replacement,1)
                first='''                    x_fraction += x_step;
                }
                y_fraction += y_step;'''
                assert new.count(first)==1
                new=new.replace(first,'''                }
                y_fraction += y_step;''',1)
                p.write_text(new)
                patches.append(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original/'+folder+'/wolf3d_renderer.cpp',tofile='candidate/'+folder+'/wolf3d_renderer.cpp')))
    assert (B/'candidate/production/wolf3d_renderer.cpp').read_bytes()==(B/'candidate/native-source/wolf3d_renderer.cpp').read_bytes()
    (T/'renderer.patch').write_text('\n'.join(patches))
    files=[p for p in B.rglob('*') if p.is_file()]+[p for p in T.iterdir() if p.is_file()]
    files += [T.parent/'WOLF-PERF-007'/n for n in ('test_equivalence.cpp','test_spans.cpp')]
    (B/'inputs.json').write_text(json.dumps({'contract':'da353d9','inputs':{str(p):sha(p) for p in files}},indent=2)+'\n')
if __name__=='__main__':main()
