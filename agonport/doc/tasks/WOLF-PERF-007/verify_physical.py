"""File-only actual-result joins, independent raw counter/producer rechecks."""
from pathlib import Path
import hashlib,json,re,sys
T=Path(__file__).resolve().parent;B=T/'build/hardware02';E=B/'evidence';sys.path.insert(0,str(T))
import hardware02 as hardware
import compare
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def main():
    k=read(B/'kit.json');hardware.verify_kit(k)
    assert sha(B/'kit.json')=='0528ed132f2ad242e91a150394ed902f21e00a379d80249f66137d1a2f746181'
    c=compare.compare(E)
    assert (E/'flash-b/read.bin').read_bytes()==Path(k['install_b']).read_bytes()
    assert (E/'flash-restore/read.bin').read_bytes()==Path(k['restore']).read_bytes()
    assert sha(E/'flash-restore/read.bin')=='85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'
    obs=read(E/'final-checks/observation.json');assert all(obs['checks'].values()) and obs['components']==k['incoming_components']
    release=read(B/'released73.json');assert release['generation']==73 and release['released'] and release['lease']==obs['lease']
    stopped=read(E/'restored-idle.json');assert stopped['target_actors_stopped'] and stopped['restored'] and stopped['lease']==obs['lease']
    probes={p.parent.name:read(p) for p in sorted(E.glob('probe-*/receipt.json'))};assert len(probes)==7
    assert all(p['passed'] and p['values'][2:4]==[0,0] and p['minimum_stack_bytes']>=512 for p in probes.values())
    cases={};runs=[]
    for i,(arm,mode) in enumerate(hardware.SEQUENCE,1):
        p=E/f'{i:02d}-vdplet-{mode}';j=read(p/'receipt.json');load=read(p/'loading.json')
        assert j['passed'] and j['actual_cli'] and j['mode0_callback0']
        assert load['count']==load['total']==470 and load['fences']==952
        assert all(load[n]==0 for n in ('timeouts','recovered','error','agnb_error'))
        binding=read(p/'guest-binding.json');assert binding==dict(arm=arm,**k['guests'][arm][mode])
        assert (p/'post-mode.bin').read_bytes()==b'\0' and (p/'post-callback.bin').read_bytes()==b'\0\0\0'
        import guest_binding
        actual=guest_binding.verify(binding)
        for name in ('before.bin','after.bin'):
            f=p/name
            if not f.exists():continue
            ram=f.read_bytes()
            for op in actual['operands']:
                at=op['address']-0x40000;assert ram[at:at+4]==bytes.fromhex(op['encoded']),(p,name,op)
        case=dict(arm=arm,mode=mode,receipt=j,guest_binding=binding,actual_ram_producer_operands_verified=True,trace=read(p/'trace.json'))
        if mode=='unpaced':
            run=compare.decode_run(p);case['nominal_draw_ms']=sum(r['draw_ccount'] for r in run['rows'])/600/240000;case['completed_fps_prt_nominal']=600000/run['prt_ticks']
            listing=Path(binding['listing']).read_text();after=(p/'after.bin').read_bytes();sp={}
            for label in ('wp_entry_sp','wp_exit_sp'):
                at=int(re.search(r'^([0-9A-F]{6})[^\n]*\b'+label+r':',listing,re.M)[1],16)-0x40000;sp[label]=int.from_bytes(after[at:at+3],'little')
            assert sp['wp_entry_sp']==sp['wp_exit_sp'] and 0xb0000<=sp['wp_entry_sp']<0xc0000
            case['actual_ez80_stack_pointers']=sp;runs.append((i,arm,case['nominal_draw_ms'],case['completed_fps_prt_nominal']))
        cases[p.name]=case
    lifecycle={}
    for p in sorted(E.glob('module-*')):
        j=read(p/'receipt.json');assert j['passed'] and j['backup_retired'] and j['recovery_state']==1
        assert sha(p/'previous-target.bin')==sha(p/'previous-backup.bin')==j['previous_sha256']
        assert read(p/'before-state.json')['state']=='01' and read(p/'after-put-state.json')['state']=='09' and read(p/'final-state.json')['state']=='01';lifecycle[p.name]=j
    assert len(lifecycle)==6
    entry=read(E/'entry-context.json');assert entry['generation']==73 and entry['manifest_sha256']==sha(B/'kit.json') and entry['lease']==release['lease']
    binary={str(p):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(E.rglob('*.bin'))}
    report=dict(schema='wolf-perf007-physical73-result-v1',passed=True,freeze='5eb6d84',generation=73,cohort='hardware02',kit_sha256=sha(B/'kit.json'),pins=len(k['inputs']),comparison=c,cases=cases,resource_probes=probes,module_lifecycle=lifecycle,binary_hashes=binary,entry_context=entry,fresh_entry=read(E/'entry/observation.json'),restoration=read(E/'flash-restore/receipt.json'),final_observation=obs,central_release=release,original_cohort_disposition='Actual72 host interpreter import failed before any probe/guest/INIT/timing; exact restore/readback/cleanup and normal release, no rendering result; separately corrected launch preflight and actual new73 custody',limits='Original ray-walk method comparison with intended rounding/texture/corner changes, not isolated helper-provider cost or identical old-port pixels. Configured240MHz/preemption-inclusive CCOUNT intervals; nominal PRT/MOS clocks, no optical/external calibration or universal gameplay FPS. Host visual/source safety success is not physical framebuffer capture. Latest raw core header is not continuous migration proof. Static frames and cumulative command-task watermark do not establish per-arm whole-call peaks. Default adoption separate.')
    (B/'comparison.json').write_text(json.dumps(c,indent=2)+'\n');(T/'PHYSICAL73-RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
    print('VERIFIED',len(k['inputs']),'pins,',len(binary),'binary evidence hashes,2400rawtimingrecords,6guest/7probe,6verifiedbackups,exactrestore/fullcleanup/release')
    print('runs',runs);print('mean_draw_ms',c['arms']['original']['nominal_ms']['draw_ccount'],c['arms']['candidate']['nominal_ms']['draw_ccount'])
if __name__=='__main__':main()
