"""File-only selected ordinary wall/acquire call-path bound, not a universal peak."""
from pathlib import Path
import hashlib,json,re
T=Path(__file__).resolve().parent;B=T/'build/r01'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    prior=json.loads((T.parent/'WOLF-PERF-019/build/r01/nested-stack-source.json').read_text())
    for p,digest in prior['native_files'].items():assert sha(p)==digest,p
    result=dict(passed=False,native_files=prior['native_files'],arms={},module_budget=2048,task_stack_bytes=4096,
        limits='Selected synchronous ordinary wall/acquire and background/span paths only; not a universal ISR/error/foreign-callback peak. Actual cumulative INFO512B floor and same safe resource admission remain.')
    files={str(Path(__file__).resolve()):sha(__file__)}
    for arm in ('original','candidate'):
        rows=[]
        for p in (B/arm/'module').glob('*.su'):
            files[str(p)]=sha(p)
            for line in p.read_text().splitlines():
                f=line.rsplit('\t',2)
                if len(f)==3:assert f[2]=='static';rows.append((f[0],int(f[1])))
        dis=B/(arm+'-disassembly.log');files[str(dis)]=sha(dis);text=dis.read_text()
        frames={}
        for name in ('vdplet_entry','wp_production_entry','render_world_direct','render_world_to_target','draw_walls','acquire_asset'):
            matches=[(label,size)for label,size in rows if re.search(r'\b'+name+r'\(',label)]
            if name=='draw_walls'and not matches:
                assert not re.search(r'^\s*[0-9a-f]+ <[^\n]*\b'+name+r'\(',text,re.M)
                continue
            assert len(matches)==1,(arm,name,matches)
            frames[name]=matches[0][1]
        # Native prefix/acquire frames are the exact unchanged7593 paths from
        # the retained source/ELF proof, not newly measured resource values.
        native_prefix=prior['arms']['original']['native_prefix_bytes']
        native_acquire=prior['arms']['original']['native_acquire_frame']
        module=sum(frames.values());whole=module+native_prefix+native_acquire
        background={k:v for k,v in frames.items() if k not in ('draw_walls','acquire_asset')}
        for name in ('compose_background','fill_rect','fill_span'):
            matches=[(label,size) for label,size in rows if re.search(r'\b'+name+r'\(',label)]
            if not matches:
                assert not re.search(r'^\s*[0-9a-f]+ <[^\n]*\b'+name+r'\(',text,re.M)
                continue
            # Named static clones are alternatives at this source call level;
            # take their maximum rather than guessing an inlining decision.
            background[name]=max(size for _,size in matches)
        background_module=sum(background.values())
        background_whole=background_module+native_prefix
        assert background_module<=2048 and background_whole<=4096

        assert module<=2048 and whole<=4096,(arm,frames,module,whole)
        result['arms'][arm]=dict(frames=frames,module_selected_path_bytes=module,native_prefix_bytes=native_prefix,
            native_acquire_frame=native_acquire,selected_task_chain_bytes=whole, background_frames=background, background_module_bytes=background_module, background_task_bytes=background_whole)
    result.update(passed=True,inputs=files)
    (B/'nested-stack-source.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['arms'],indent=2))
if __name__=='__main__':main()
