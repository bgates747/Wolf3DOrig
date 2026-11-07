"""One guarded narrow unsigned subset; exact old fallback/signed wrapper."""
from pathlib import Path
import difflib,hashlib,json,shutil
T=Path(__file__).resolve().parent;B=T/'build/r01'
BASE=T.parent/'WOLF-PERF-009/build/r01/candidate'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
GUARD='    if (divisor.words.low == 0 && divisor.words.high == 0) return UINT64_MAX;\n'
FAST='''    if ((dividend.words.high | divisor.words.high) == 0)
        return static_cast<uint64_t>(dividend.words.low / divisor.words.low);
'''
def body(text):
    begin=text.index('union WideWords {')
    end=text.index('\n#endif',begin)
    return text[begin:end]
def main():
    for n,d in json.loads((T/'SOURCE-PINS.json').read_text())['files'].items():assert sha(n)==d,n
    B.mkdir(parents=True,exist_ok=False);patch=[];units={}
    for arm in ('original','candidate'):
        a=B/arm;a.mkdir()
        for n in ('native-source','production','qualification','sdk'):
            shutil.copytree(BASE/n,a/n,ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(BASE/'wolf3d_tables.inc',a/'wolf3d_tables.inc')
        if arm=='candidate':
            for folder in ('production','native-source'):
                p=a/folder/'wolf3d_module.cpp';old=p.read_text();assert old.count(GUARD)==1
                new=old.replace(GUARD,GUARD+FAST,1);p.write_text(new)
                assert new.replace(FAST,'',1)==old
                patch.append(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original/'+folder+'/wolf3d_module.cpp',tofile='candidate/'+folder+'/wolf3d_module.cpp')))
        raw=body((a/'native-source/wolf3d_module.cpp').read_text())
        assert raw==body((a/'production/wolf3d_module.cpp').read_text())
        renamed=raw.replace('__udivdi3',arm+'_udiv').replace('__divdi3',arm+'_sdiv')
        assert renamed.replace(arm+'_udiv','__udivdi3').replace(arm+'_sdiv','__divdi3')==raw
        units[arm]=dict(source_sha256=sha(a/'native-source/wolf3d_module.cpp'),body_sha256=hashlib.sha256(raw.encode()).hexdigest(),source=str(a/'native-source/wolf3d_module.cpp'))
        (T/(arm+'_numeric.inc')).write_text('namespace '+arm+' {\n'+renamed+'\n}\n')
    original=body((B/'original/native-source/wolf3d_module.cpp').read_text())
    candidate=body((B/'candidate/native-source/wolf3d_module.cpp').read_text())
    assert candidate.replace(FAST,'',1)==original
    (T/'renderer.patch').write_text('\n'.join(patch))
    (B/'native-body-binding.json').write_text(json.dumps(dict(passed=True,units=units,fallback_and_signed_wrapper_equal=True,only_renamed_abi_symbols_for_host=True),indent=2)+'\n')
    files=[p for p in B.rglob('*')if p.is_file()]+[p for p in T.iterdir()if p.is_file()]
    files += [T.parent/'WOLF-PERF-007'/n for n in ('test_equivalence.cpp','test_spans.cpp')]
    (B/'inputs.json').write_text(json.dumps(dict(contract='0aba906',inputs={str(p):sha(p)for p in files}),indent=2)+'\n')
if __name__=='__main__':main()
