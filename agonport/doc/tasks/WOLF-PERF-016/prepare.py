"""Supported cyan extent correction only, from exact a926."""
from pathlib import Path
import difflib,hashlib,json,shutil
T=Path(__file__).resolve().parent;B=T/'build/r01'
BASE=T.parent/'WOLF-PERF-009/build/r01/candidate'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    for n,d in json.loads((T/'SOURCE-PINS.json').read_text())['files'].items():assert sha(n)==d,n
    B.mkdir(parents=True,exist_ok=False);patches=[]
    oldline='    fill_rect(frame, 0, 0, W3P_SCREEN_WIDTH - 1, kPlayHeight - 1, kDarkCyan);'
    replacement='''    // A later viewport fill fully replaces cyan only under overwrite masks.
    if (frame.linear != nullptr ||
        (frame.color_mask & frame.preserve_mask) == 0) {
        fill_rect(frame, 0, 0, W3P_SCREEN_WIDTH - 1, kViewY - 1, kDarkCyan);
        fill_rect(frame, 0, kViewY + kViewHeight,
                  W3P_SCREEN_WIDTH - 1, kPlayHeight - 1, kDarkCyan);
        fill_rect(frame, 0, kViewY, kViewX - 1,
                  kViewY + kViewHeight - 1, kDarkCyan);
        fill_rect(frame, kViewX + kViewWidth, kViewY,
                  W3P_SCREEN_WIDTH - 1, kViewY + kViewHeight - 1, kDarkCyan);
    } else {
        // Overlapping masks can retain bits contributed by the first fill.
        fill_rect(frame, 0, 0, W3P_SCREEN_WIDTH - 1,
                  kPlayHeight - 1, kDarkCyan);
    }'''
    for arm in ('original','candidate'):
        a=B/arm;a.mkdir()
        for n in ('native-source','production','qualification','sdk'):shutil.copytree(BASE/n,a/n,ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(BASE/'wolf3d_tables.inc',a/'wolf3d_tables.inc')
        if arm=='candidate':
            for folder in ('production','native-source'):
                p=a/folder/'wolf3d_renderer.cpp';old=p.read_text();assert old.count(oldline)==1
                new=old.replace(oldline,replacement,1);p.write_text(new)
                patches.append(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original/'+folder+'/wolf3d_renderer.cpp',tofile='candidate/'+folder+'/wolf3d_renderer.cpp')))
    assert (B/'candidate/production/wolf3d_renderer.cpp').read_bytes()==(B/'candidate/native-source/wolf3d_renderer.cpp').read_bytes()
    (T/'renderer.patch').write_text('\n'.join(patches))
    files=[p for p in B.rglob('*')if p.is_file()]+[p for p in T.iterdir()if p.is_file()]
    files += [T.parent/'WOLF-PERF-007'/n for n in ('test_equivalence.cpp','test_spans.cpp')]
    (B/'inputs.json').write_text(json.dumps({'contract':'e19f461','inputs':{str(p):sha(p)for p in files}},indent=2)+'\n')
if __name__=='__main__':main()
