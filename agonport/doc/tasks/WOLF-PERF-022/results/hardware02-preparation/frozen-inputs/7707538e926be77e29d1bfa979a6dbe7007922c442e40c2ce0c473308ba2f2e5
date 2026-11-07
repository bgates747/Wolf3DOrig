"""Compose only independently qualified units, retaining an exact a926 control."""
from pathlib import Path
import difflib,hashlib,json,re,shutil
T=Path(__file__).resolve().parent;P=T.parent;B=T/'build/r01'
BASE=P/'WOLF-PERF-009/build/r01/candidate'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def section(text,start,end):
    a=text.index(start);b=text.index(end,a);return text[a:b]
def numeric(text):return section(text,'union WideWords {','\n#endif')
def main():
    for name,digest in json.loads((T/'SOURCE-PINS.json').read_text())['files'].items():assert sha(name)==digest,name
    assert sha(BASE/'module/wolf_perf.vdpl')=='a926b48ab3207b59773cc8283d59cc687f274ef2af00017451567449a4c69656'
    donors={str(n):P/f'WOLF-PERF-{n:03d}/build/r01/candidate' for n in (15,16,17,18,19)}
    for n,root in donors.items():
        assert json.loads((root.parent/'build-receipt.json').read_text())['passed']
        assert sha(root.parent/'original/module/wolf_perf.vdpl')==sha(BASE/'module/wolf_perf.vdpl')
    B.mkdir(parents=True,exist_ok=False);units={};patches=[]
    for arm in ('original','candidate'):
        a=B/arm;a.mkdir()
        for name in ('production','native-source','qualification','sdk'):shutil.copytree(BASE/name,a/name,ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(BASE/'wolf3d_tables.inc',a/'wolf3d_tables.inc')
        if arm=='candidate':
            for folder in ('production','native-source'):
                p=a/folder/'wolf3d_renderer.cpp';old=p.read_text();new=old
                d={n:(root/folder/'wolf3d_renderer.cpp').read_text()for n,root in donors.items()}
                bg=section(d['16'],'void compose_background(','uint8_t shifted_component(')
                setup=section(d['15'],'ViewState setup_view(','uint8_t base_tile_at(')
                walls=section(d['19'],'RenderDetail draw_walls(','bool transform_point(')
                # Keep the19 chain header/iteration exactly; merge only18's cache locals/body.
                cache=section(d['18'],'        int cached_height = 0;','        for (int col = 0;')
                assert walls.count('        for (int col = heads[id];')==1
                walls=walls.replace('        for (int col = heads[id];',cache+'        for (int col = heads[id];',1)
                body18=section(d['18'],'            const int full_height = heights[col];','        }\n        detail = release_asset')
                old_body=section(walls,'            const int full_height = heights[col];','        }\n        detail = release_asset')
                assert old_body==section(old,'            const int full_height = heights[col];','        }\n        detail = release_asset')
                walls=walls.replace(old_body,body18,1)
                definitions=[('background','void compose_background(','uint8_t shifted_component(',bg),('view','ViewState setup_view(','uint8_t base_tile_at(',setup),('walls','RenderDetail draw_walls(','bool transform_point(',walls)]
                for name,start,end,body in definitions:
                    original=section(new,start,end);new=new.replace(original,body,1)
                    units[folder+'/'+name]=dict(original_sha256=hashlib.sha256(original.encode()).hexdigest(),composed_sha256=hashlib.sha256(body.encode()).hexdigest())
                old_sine=section(new,'int32_t sin_fine(','void fill_rect(');new=new.replace(old_sine,'',1)
                assert new.count('normalize_fine(')==2 and 'sin_fine('not in new and 'cos_fine('not in new
                # Exact reverse-unit proof: no unrelated renderer bytes changed.
                undone=new
                for _name,start,end,_body in definitions:
                    undone=undone.replace(section(undone,start,end),section(old,start,end),1)
                at=undone.index('void fill_rect(');undone=undone[:at]+old_sine+undone[at:]
                assert undone==old
                p.write_text(new)
                patches.append(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original/'+folder+'/wolf3d_renderer.cpp',tofile='candidate/'+folder+'/wolf3d_renderer.cpp')))
                module=a/folder/'wolf3d_module.cpp';original=module.read_text();replacement=(donors['17']/folder/'wolf3d_module.cpp').read_text()
                fast='    if ((dividend.words.high | divisor.words.high) == 0)\n        return static_cast<uint64_t>(dividend.words.low / divisor.words.low);\n'
                assert replacement.replace(fast,'',1)==original and replacement.count(fast)==1
                module.write_text(replacement)
                patches.append(''.join(difflib.unified_diff(original.splitlines(True),replacement.splitlines(True),fromfile='original/'+folder+'/wolf3d_module.cpp',tofile='candidate/'+folder+'/wolf3d_module.cpp')))
            table=(BASE/'wolf3d_tables.inc').read_text();new_table=(donors['15']/'wolf3d_tables.inc').read_text()
            expr=r'static const int32_t kWolfSin(?:Quarter|Degree)\[\d+\] __attribute__\(\(aligned\(4\)\)\) = \{.*?\};'
            assert len(re.findall(expr,table,re.S))==len(re.findall(expr,new_table,re.S))==1
            assert re.sub(expr,'$SINE',table,flags=re.S)==re.sub(expr,'$SINE',new_table,flags=re.S)
            (a/'wolf3d_tables.inc').write_text(new_table)
            patches.append(''.join(difflib.unified_diff(table.splitlines(True),new_table.splitlines(True),fromfile='original/wolf3d_tables.inc',tofile='candidate/wolf3d_tables.inc')))
        # Real native body extraction is required beyond HOST_TEST.
        raw=numeric((a/'native-source/wolf3d_module.cpp').read_text())
        assert raw==numeric((a/'production/wolf3d_module.cpp').read_text())
        source=P/'WOLF-PERF-017/build/r01'/arm/'native-source/wolf3d_module.cpp'
        assert raw==numeric(source.read_text())
        renamed=raw.replace('__udivdi3',arm+'_udiv').replace('__divdi3',arm+'_sdiv')
        (T/(arm+'_numeric.inc')).write_text('namespace '+arm+' {\n'+renamed+'\n}\n')
        units[arm+'/numeric']=dict(source=str(a/'native-source/wolf3d_module.cpp'),body_sha256=hashlib.sha256(raw.encode()).hexdigest(),equal_qualified17_body=True)
    assert (B/'candidate/production/wolf3d_renderer.cpp').read_bytes()==(B/'candidate/native-source/wolf3d_renderer.cpp').read_bytes()
    # Native module intentionally retains the original CCOUNT/entry wrapper.
    # The per-folder inverse FAST proof above preserves that difference exactly.
    (T/'combined.patch').write_text('\n'.join(patches))
    (B/'unit-composition.json').write_text(json.dumps(dict(passed=True,units=units,unselected_renderer_bytes_equal=True,only_numeric17_module_change=True,only_degree15_table_change=True),indent=2)+'\n')
    (B/'native-body-binding.json').write_text(json.dumps(dict(passed=True,units={a:units[a+'/numeric']for a in ('original','candidate')},fallback_and_signed_wrapper_equal=True),indent=2)+'\n')
    files=[p for p in B.rglob('*')if p.is_file()]+[p for p in T.iterdir()if p.is_file()]
    files += [P/'WOLF-PERF-007'/n for n in ('test_equivalence.cpp','test_spans.cpp')]
    (B/'inputs.json').write_text(json.dumps(dict(contract='aa08350',inputs={str(p):sha(p)for p in files}),indent=2)+'\n')
    print(json.dumps(dict(passed=True,inputs=len(files),source_unit_join=True,compiler_or_target=False)))
if __name__=='__main__':main()
