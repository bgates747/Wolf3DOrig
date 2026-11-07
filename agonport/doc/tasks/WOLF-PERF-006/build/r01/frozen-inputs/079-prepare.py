"""File-only identical-source copies; only the candidate private SDK flag changes."""
from pathlib import Path
import hashlib,json,shutil,difflib
T=Path(__file__).resolve().parent;P5=T.parent/'WOLF-PERF-005';P3=T.parent/'WOLF-PERF-003'
BASE=P5/'build/r02/candidate';B=T/'build/r01';SDK=P3/'build/r04/inputs/sdk'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    assert sha(BASE/'module/wolf_perf.vdpl')=='bf7f2bb038387698464fbb297a437ef98457638a28261dc7f9688044d9b6eb28'
    B.mkdir(parents=True,exist_ok=False);diffs=[]
    for arm in ('original','candidate'):
        a=B/arm;a.mkdir()
        for n in ('native-source','production','qualification'):shutil.copytree(BASE/n,a/n)
        shutil.copyfile(BASE/'wolf3d_tables.inc',a/'wolf3d_tables.inc')
        shutil.copytree(SDK,a/'sdk',ignore=shutil.ignore_patterns('__pycache__'))
        if arm=='candidate':
            p=a/'sdk/tools/build_module.py';old=p.read_text();assert old.count('"-Os"')==1
            new=old.replace('"-Os"','"-O2"');p.write_text(new)
            (B/'sdk-flag.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original-sdk',tofile='candidate-sdk')))
    for rootname in ('native-source','production','qualification','sdk'):
        for p in sorted((B/'original'/rootname).rglob('*')):
            if not p.is_file():continue
            q=B/'candidate'/p.relative_to(B/'original')
            if p.read_bytes()!=q.read_bytes():
                diffs.append(str(p.relative_to(B/'original')))
                assert rootname=='sdk' and p.name=='build_module.py'
                assert p.read_bytes()==q.read_bytes().replace(b'"-O2"',b'"-Os"')
    assert diffs==['sdk/tools/build_module.py']
    pins={str(p):sha(p) for p in sorted(B.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    for name in ('PLAN.md','PRE-CODE.md','prepare.py','build.py','target_compile.py','code_check.py','test_spans.cpp','test_fixed_div.cpp','test_equivalence.cpp'):pins[str(T/name)]=sha(T/name)
    (B/'inputs.json').write_text(json.dumps(dict(task='WOLF-PERF-006',plan_freeze='6681bf5',inputs=pins,source_identical=True,only_difference=diffs,control_sha256=sha(BASE/'module/wolf_perf.vdpl')),indent=2)+'\n')
    print('Prepared identical source/ABI/helpers with only private -Os→-O2 flag difference.')
if __name__=='__main__':main()
