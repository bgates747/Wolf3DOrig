"""Publish preserved partial observations; never manufacture a complete cohort."""
from pathlib import Path
import hashlib,json,re,sys
T=Path(__file__).resolve().parent;B=T/'build/hardware02';E=B/'evidence';R=B/'cleanup73';sys.path.insert(0,str(T))
import compare,guest_binding
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def main():
    k=read(B/'kit.json');snap=read(B/'frozen-inputs/manifest.json')['files'];assert len(snap)==len(k['inputs'])==486
    for n,d in k['inputs'].items():assert snap[n]['sha256']==d and sha(snap[n]['snapshot'])==d,n
    assert not (E/'complete.json').exists() and not (E/'06-vdplet-unpaced').exists()
    try:compare.compare(E)
    except FileNotFoundError as error:assert Path(error.filename).name=='complete.json';refusal=str(error)
    else:raise AssertionError('Incomplete full cohort accepted')
    cases={}
    for i,(arm,mode) in enumerate((('original','control'),('candidate','control'),('original','unpaced'),('candidate','unpaced')),1):
        p=E/f'{i:02d}-vdplet-{mode}';j=read(p/'receipt.json');assert j['passed'] and j['actual_cli'] and j['mode0_callback0']
        binding=read(p/'guest-binding.json');assert binding==dict(arm=arm,**k['guests'][arm][mode]);producer=guest_binding.verify(binding)
        for name in ('before.bin','after.bin'):
            f=p/name
            if not f.exists():continue
            ram=f.read_bytes()
            for op in producer['operands']:
                at=op['address']-0x40000;assert ram[at:at+4]==bytes.fromhex(op['encoded'])
        load=read(p/'loading.json');assert load['count']==load['total']==470 and load['fences']==952 and all(load[n]==0 for n in ('error','agnb_error','timeouts','recovered'))
        case=dict(arm=arm,mode=mode,receipt=j,producer_actual_ram_operands=True)
        if mode=='unpaced':
            after=(p/'after.bin').read_bytes();sp={name:int.from_bytes(after[at-0x40000:at-0x40000+3],'little') for name,at in producer['stack_labels'].items()};assert sp['wp_entry_sp']==sp['wp_exit_sp'];case['actual_guest_sp']=sp
        cases[p.name]=case
    runs={}
    for label,path,arm,salvaged in [('baseline03',E/'03-vdplet-unpaced','original',False),('candidate04',E/'04-vdplet-unpaced','candidate',False),('candidate05-salvaged',R,'candidate',True)]:
        r=compare.decode_run(path);rows=r.pop('rows');summaries={key:compare.summarize([x[key]/240000 for x in rows]) for key in ('draw_ccount','scope_ccount','command_ccount')}
        runs[label]=dict(arm=arm,module_sha256=k[arm+'_module_sha256'],records=len(rows),raw=r,nominal_ms=summaries,completed_fps_prt_nominal=600000/r['prt_ticks'],completed_fps_mos_nominal=72000/r['mos_ticks'],salvaged=salvaged,complete_case=not salvaged)
    assert len({r['raw']['raw_prid'] for r in runs.values()})==1
    repeat=E/'05-vdplet-unpaced';repeat_binding=read(repeat/'guest-binding.json')
    assert repeat_binding==dict(arm='candidate',**k['guests']['candidate']['unpaced'])
    producer=guest_binding.verify(repeat_binding);ram=(repeat/'before.bin').read_bytes()
    for op in producer['operands']:
        at=op['address']-0x40000;assert ram[at:at+4]==bytes.fromhex(op['encoded'])
    baseline=runs['baseline03']['nominal_ms']['draw_ccount']['mean'];candidates=[runs[n]['nominal_ms']['draw_ccount']['mean'] for n in ('candidate04','candidate05-salvaged')];mean=sum(candidates)/2
    probes={p.parent.name:read(p) for p in sorted(E.glob('probe-*/receipt.json'))};assert len(probes)==5 and all(x['passed'] and x['values'][2:4]==[0,0] and x['minimum_stack_bytes']>=512 for x in probes.values())
    lifecycle={p.parent.name:read(p) for p in sorted(E.glob('module-*/receipt.json'))};assert len(lifecycle)==5 and all(x['passed'] and x['backup_retired'] and x['recovery_state']==1 for x in lifecycle.values())
    before=read(R/'before-discard.json');idle=read(R/'after-discard.json');assert before['phase']==5 and before['error']==3 and before['id']==3215372350 and before['boot']==2910473983 and idle['phase']==0 and idle['boot']==before['boot']
    assert not (E/'05-vdplet-unpaced/after.bin').exists() and (R/'original-after-job-preserved.json').exists()
    saved=read(R/'ram-saved-metadata.json');assert saved['before_any_load'] and saved['bytes']==325300 and not saved['local_readback']
    assert (E/'flash-b/read.bin').read_bytes()==Path(k['install_b']).read_bytes() and (E/'flash-restore/read.bin').read_bytes()==Path(k['restore']).read_bytes()
    assert sha(E/'flash-restore/read.bin')=='85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'
    release=read(B/'released73.json');ob=read(E/'final-checks/observation.json');assert release['generation']==73 and release['released'] and release['lease']==ob['lease'] and ob['components']==k['incoming_components'] and all(ob['checks'].values())
    binary={str(p.relative_to(B)):dict(bytes=p.stat().st_size,sha256=sha(p)) for root in (E,R) for p in sorted(root.rglob('*.bin'))}
    result=dict(schema='wolf-perf007-partial73-result-v1',complete_cohort=False,implementation_qualified_offline=True,hardware_generation=73,freeze='5eb6d84',kit_sha256=sha(B/'kit.json'),selected_input_snapshots=486,snapshot_manifest_sha256=sha(B/'frozen-inputs/manifest.json'),full_cohort_decoder_refusal=refusal,fully_collected_cases=cases,records=1800,runs=runs,descriptive_unbalanced_summary=dict(baseline_records=600,candidate_records=1200,candidate_mean_draw_nominal_ms=mean,saved_draw_nominal_ms=baseline-mean,reduction_percent=100*(baseline-mean)/baseline,limits='One baseline versus two candidate observations; final reverse-order baseline absent, correlated scripted frames, no complete balanced matched-cohort verdict'),failure=read(E/'failure.json'),failed_get_status=before,terminal_retirement_after=idle,ram_save_metadata=saved,resource_probes=probes,module_lifecycle=lifecycle,restoration=read(E/'flash-restore/receipt.json'),stopped_restored=read(E/'stopped-restored.json'),final_observation=ob,central_release=release,binary_hashes=binary,limits='Configured240MHz/preemption-inclusive raw draw intervals and nominal PRT/MOS clocks; no external/optical calibration or universal gameplay FPS. Original ray-walk method intentionally changes some rounding/crossing/texture columns. Candidate05 timings were salvaged after collection failure; after.bin/actualpost-SP and postrepeatresourceprobe were not verified. No failedGET retry, successorbaseline, complete-cohort result or default adoption. Cumulative INFO17 watermark is not per-arm whole-call peak attribution; memory halves are non-atomic. Native profile8 restored, all actors stopped and normalrelease completed.')
    (T/'PARTIAL73-RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print('VERIFIED partial1800records/4completecases+onecompletedrepeat/5probes/5modulechains/486snapshots/exactrestore/release; full-cohort gate refuses')
    for n,r in runs.items():print(n,{k:round(v['mean'],6) for k,v in r['nominal_ms'].items()},'fps',r['completed_fps_prt_nominal'])
    print(result['descriptive_unbalanced_summary']);print('binaryevidence',len(binary))
if __name__=='__main__':main()
