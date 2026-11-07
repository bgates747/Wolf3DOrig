"""Independent file-only raw/custody joins; never qualify this as visible FPS."""
from pathlib import Path
import hashlib,json,re
import decode75,guest_binding
T=Path(__file__).resolve().parent;B=T/'build/hardware01';E=B/'evidence'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def main():
    k=read(B/'kit.json');assert sha(B/'kit.json')=='98d9397e1e362dcd60664aef756974b8f8aba06866b3086ba89286d1efcd9a81'
    snap=read(B/'frozen-inputs/manifest.json');assert len(snap)==469
    for n,d in k['inputs'].items():assert snap[n]['sha256']==d and sha(snap[n]['snapshot'])==d,n
    assert not (E/'complete.json').exists()
    assert not (E/'06-vdplet-unpaced/load-issued.json').exists() and not (E/'06-vdplet-unpaced/run-issued.json').exists()
    obs=read(E/'final-checks/observation.json');release=read(B/'released75.json');assert all(obs['checks'].values()) and obs['components']==k['incoming_components']
    assert release['generation']==75 and release['released'] and obs['lease']==release['lease']
    assert (E/'flash-restore/read.bin').read_bytes()==Path(k['restore']).read_bytes()
    assert sha(E/'flash-restore/read.bin')=='85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'
    cases={}
    for i,(arm,mode) in enumerate((('original','control'),('candidate','control'),('original','unpaced'),('candidate','unpaced'),('candidate','unpaced')),1):
        p=E/f'{i:02d}-vdplet-{mode}';r=read(p/'receipt.json');assert r['passed'] and r['actual_cli'] and r['mode0_callback0']
        load=read(p/'loading.json');assert load['count']==load['total']==470 and load['fences']==952
        assert all(load[n]==0 for n in ('error','agnb_error','timeouts','recovered'))
        binding=read(p/'guest-binding.json');assert binding==dict(arm=arm,**k['guests'][arm][mode]);v=guest_binding.verify(binding)
        for name in ('before.bin','after.bin'):
            if not (p/name).exists():continue
            raw=(p/name).read_bytes()
            for op in v['operands']:
                at=op['address']-0x40000;assert raw[at:at+4]==bytes.fromhex(op['encoded'])
        case=dict(arm=arm,mode=mode,collection_receipt_passed=True,visible_rotation_qualified=False)
        if mode=='unpaced':
            d=decode75.decode_run(p);after=(p/'after.bin').read_bytes();sp={label:int.from_bytes(after[address-0x40000:address-0x40000+3],'little')for label,address in v['stack_labels'].items()}
            assert sp['wp_entry_sp']==sp['wp_exit_sp'] and 0xb0000<=sp['wp_entry_sp']<0xc0000
            case.update(poses=600,distinct_headings=len({x['angle']for x in d['rows']}),draw_call_mean_nominal_ms=sum(x['draw_ccount']for x in d['rows'])/600/240000,hidden_draws_per_nominal_second=600000/d['prt_ticks'],actual_ez80_sp=sp,raw=d['hashes'])
        cases[p.name]=case
    probes={p.parent.name:read(p)for p in E.glob('probe-*/receipt.json')};assert len(probes)==6
    assert all(r['passed'] and r['values'][2:4]==[0,0] and r['minimum_stack_bytes']>=512 for r in probes.values())
    lifecycle={}
    for p in E.glob('module-*'):
        r=read(p/'receipt.json');assert r['passed'] and r['backup_retired'] and r['recovery_state']==1
        assert sha(p/'previous-target.bin')==sha(p/'previous-backup.bin')==r['previous_sha256'];lifecycle[p.name]=r
    assert len(lifecycle)==6
    binaries={str(p):dict(bytes=p.stat().st_size,sha256=sha(p))for p in E.rglob('*.bin')}
    out=dict(schema='wolf-perf009-stopped75-hidden-capacity-only',balanced_comparison_complete=False,visible_rotation_or_gameplay_fps_qualified=False,kit_sha256=sha(B/'kit.json'),inputs=469,cases=cases,resource_probes=probes,lifecycle=lifecycle,binaries=binaries,central_release=release,final_observation=obs,restoration=read(E/'flash-restore/receipt.json'),presentation_correction='Unpaced loop renders hidden poses and presents once after timing stops.720degrees returns initial heading. Human was right to see no motion; Wolf announcements were wrong.',limits='1800 raw timed poses and one baseline/two candidate runs, final baseline not LOAD/RUN. No balanced speed verdict. CCOUNT configured240MHz/preemption-inclusive, PRT nominal/no external calibration. Hidden draw capacity is not visible/gameplay FPS. Largest individual static frame and cumulative resource watermark do not establish whole-call-stack peaks. No default adoption.')
    (T/'STOPPED75-RESULT.json').write_text(json.dumps(out,indent=2)+'\n')
    print('Verified469frozen inputs,1800rawposes,5collection receipts/6probes,6backups,exactrestore/release; NO visibleFPS/full-cohort verdict')
if __name__=='__main__':main()
