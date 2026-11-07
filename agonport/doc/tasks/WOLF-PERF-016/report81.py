"""Offline join of actual submitted guest, resident code, timing and restoration."""
from pathlib import Path
import csv,hashlib,importlib.util,json,re,statistics
T=Path(__file__).resolve().parent;B=T/'build/hardware01';E=B/'evidence'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
SEQUENCE=(('original','room'),('candidate','room'),('candidate','room'),('original','room'))
def main():
    kit=read(B/'kit.json')
    snapshots=read(B/'frozen-inputs/index.json')
    for p,d in kit['inputs'].items():
        archived=snapshots[p];assert archived['sha256']==d and sha(archived['snapshot'])==d,p
        # Checklists/preparation witnesses may be disposed after actual release;
        # the exact selected bytes survive independently in the hash archive.
    release=read(T/'results/actual81/released78.json');assert release['generation']==81 and release['released']

    assert read(E/'complete.json')['passed'] and read(E/'complete.json')['restored']
    assert (E/'flash-restore/read.bin').read_bytes()==Path(kit['restore']).read_bytes()
    final=read(E/'final-checks/observation.json');assert all(final['checks'].values()) and final['components']==kit['incoming_components']
    spec=importlib.util.spec_from_file_location('verified_producer',T/'guest_binding.py');binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding)
    cases=[]
    for i,(arm,scene) in enumerate(SEQUENCE,1):
        p=E/f'{i:02d}-vdplet-{scene}';receipt=read(p/'receipt.json');assert receipt['passed']
        assert read(p/'arm.json')['module_sha256']==kit[arm+'_module_sha256']
        g=kit['guests'][arm][scene];actual=binding.verify(g)
        assert read(p/'guest-binding.json')['module_sha256']==g['module_sha256']
        listing=Path(g['listing']).read_text();binary=Path(g['guest']).read_bytes()
        start=int(re.search(r'^([0-9A-F]{6})[^\n]*\bwp_next:',listing,re.M)[1],16)
        stop=min(int(m[1],16)for m in re.finditer(r'^([0-9A-F]{6})[^\n]*\bcall wp_prt_stop\b',listing,re.M)if int(m[1],16)>start)
        calls=[]
        for m in re.finditer(r'^([0-9A-F]{6}) ((?:[0-9A-F]{2} ){3}[0-9A-F]{2})\s+\d+\*?\s+call (w3d_vdu_present|w3d_audio_wait_for_vdp_ingress)\b',listing,re.M):
            if start<=int(m[1],16)<stop:calls.append(dict(address=int(m[1],16),encoded=m[2],target=m[3]))
        assert [x['target']for x in calls]==['w3d_vdu_present','w3d_audio_wait_for_vdp_ingress']
        for name in ('before.bin','after.bin'):
            raw=(p/name).read_bytes()
            for op in actual['operands']+calls:
                at=op['address']-0x40000;expected=bytes.fromhex(op['encoded'])
                assert raw[at:at+4]==binary[at:at+4]==expected,(i,name,op)
        after=(p/'after.bin').read_bytes();sp=[]
        for name in ('wp_entry_sp','wp_exit_sp'):
            at=int(re.search(r'^([0-9A-F]{6})[^\n]*\b'+name+':',listing,re.M)[1],16)-0x40000
            sp.append(int.from_bytes(after[at:at+3],'little'))
        assert sp[0]==sp[1] and 0xb0000<=sp[0]<0xc0000
        result=read(p/'report.json');assert result['mode']=='uncapped-visible' and result['completed_records']==600
        with (p/'samples.csv').open()as f:rows=list(csv.DictReader(f))
        assert [int(r['step'])for r in rows]==list(range(1,601))
        assert all(int(r['angle'])==(720*int(r['step'])//600)%360 and 0<int(r['active_ms'])<8000 for r in rows)
        intervals=[int(rows[n]['present_end'])-int(rows[n-1]['present_end'])for n in range(1,600)]
        render=[int(r['render_ccount'])for r in rows]
        assert len(render)==600 and all(0<x<0x80000000 for x in render)
        cases.append(dict(index=i,arm=arm,scene=scene,module_sha256=g['module_sha256'],producer=actual,balanced_stack=sp,presentation_calls=calls,
            frames=600,seconds_nominal=result['prt_nominal_seconds'],fps_nominal=result['nominal_prt_records_per_second'],steady_fps_nominal=599000/sum(intervals),interval_ms=result['presentation_intervals_nominal_prt_ms'],
            render_cycles_mean=statistics.mean(render),render_cycles_median=statistics.median(render),render_ms_at_configured240MHz=statistics.mean(render)/240000,
            native=result['native_ccount'],stages=result['stages_nominal_prt_ms'],
            raw_files={str(q):dict(bytes=q.stat().st_size,sha256=sha(q))for q in p.glob('*.bin')}))
    comparisons={}
    for scene in ('room',):
        groups={a:[c for c in cases if c['scene']==scene and c['arm']==a]for a in ('original','candidate')}
        means={a:statistics.mean(c['render_cycles_mean']for c in group)for a,group in groups.items()}
        fps={a:sum(c['frames']for c in group)/sum(c['seconds_nominal']for c in group)for a,group in groups.items()}
        comparisons[scene]=dict(runs_per_arm=len(groups['original']),original_render_cycles=means['original'],candidate_render_cycles=means['candidate'],render_reduction_percent=(1-means['candidate']/means['original'])*100,original_presented_fps=fps['original'],candidate_presented_fps=fps['candidate'],presented_fps_change_percent=(fps['candidate']/fps['original']-1)*100,scope='Two same-session runs per arm in A/B/B/A order')
    probes={p.parent.name:read(p)for p in E.glob('probe-*/receipt.json')};assert len(probes)==5 and all(x['passed']for x in probes.values())
    result=dict(passed=True,schema='wolf-perf016-actual81',bench_generation=81,synthetic_pacing=False,human_optical_confirmation=False,frames=2400,cases=cases,comparisons=comparisons,resource_probes=probes,
        original_native_restored=True,restore_sha256=sha(E/'flash-restore/read.bin'),final_observation=final,
        qualification='Physical per-frame ordered completion timestamps and inclusive nativeCCOUNT; nominal PRT/MOS/configured240MHz, no external oscillator/optical scanout calibration or exclusiveCPU attribution. Source/host equivalence separate; no human visual claim. Matched ordinary room ABBA only; other scenes remain unmeasured.')
    result.update(bench_released=True,release_receipt=str((T/'results/actual81/released78.json').resolve()),decision='Retain the exact measured candidate and control; evaluate draw time, presentation cadence and resource cost separately. Unchanged FPS alone is not a rejection criterion; no silent default adoption.',input_snapshots=str((B/'frozen-inputs/index.json').resolve()))
    (T/'RESULT81.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(comparisons,indent=2))
if __name__=='__main__':main()
