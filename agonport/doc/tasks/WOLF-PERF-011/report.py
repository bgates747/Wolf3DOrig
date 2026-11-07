"""Independent offline joins for Smith's actual visible/manual-start77 run."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import statistics

T=Path(__file__).resolve().parent
B=T/'build/hardware02'
E=B/'evidence'
P=E/'human-run-collection'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())


def main():
    kit=read(B/'kit.json')
    assert sha(B/'kit.json')=='5f77b86af94f5fca78a5f695be0685f3fb413e75065c4d1b98fbbcf863d20225'
    snapshots={r['original']:(n,r)for n,r in read(B/'frozen-inputs/manifest.json').items()}
    assert len(snapshots)==len(kit['inputs'])==163
    for n,d in kit['inputs'].items():
        p,r=snapshots[n];assert r['sha256']==sha(p)==d,n
    spec=importlib.util.spec_from_file_location('binding',T.parent/'WOLF-PERF-009/guest_binding.py')
    binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding)
    actual=binding.verify(kit['guest'])
    calls=read(T/'ASSEMBLY-RESULT.json')['actual_presentation_calls'][:2]
    for name in ('before.bin','after.bin','completed-ram.bin'):
        raw=(P/name).read_bytes()
        for op in actual['operands']:
            at=op['address']-0x40000
            assert raw[at:at+4]==bytes.fromhex(op['encoded'])
        guest=Path(kit['guest']['guest']).read_bytes()
        for call in calls:
            at=call['address']-0x40000
            assert raw[at:at+4]==guest[at:at+4]
    report=read(P/'report.json');receipt=read(P/'receipt.json')
    assert receipt['passed'] and receipt['human_started'] and receipt['agent_run'] is False
    assert report['mode']=='paced' and report['completed_records']==600 and report['coalesced_poses']==0
    with (P/'samples.csv').open() as stream:rows=list(csv.DictReader(stream))
    assert len(rows)==600 and [int(r['step'])for r in rows]==list(range(1,601))
    assert all(int(r['angle'])==(720*int(r['step'])//600)%360 for r in rows)
    assert all(0<int(r['active_ms'])<8000 for r in rows)
    assert receipt['balanced_stack'][0]==receipt['balanced_stack'][1]
    assert read(E/'human-review.json')['visible_two_turns_confirmed']
    assert (E/'complete.json').exists() and read(E/'complete.json')['restored']
    assert (E/'flash-restore/read.bin').read_bytes()==Path(kit['restore']).read_bytes()
    assert sha(E/'flash-restore/read.bin')=='85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'
    final=read(E/'final-checks/observation.json')
    assert all(final['checks'].values()) and final['components']==kit['incoming_components']
    assert final['lease']==read(E/'ready.json')['lease']
    # The collection controller never dispatches RUN. Actual keyboard receipts
    # independently cover both failed preparation and corrected continuation.
    issued=[]
    for p in E.rglob('*-issued.json'):
        v=read(p)
        if 'command'in v:
            assert not v['command'].strip().upper().startswith('RUN'),str(p)
            issued.append(dict(file=str(p),command=v['command']))
    intervals=[int(rows[i]['present_end'])-int(rows[i-1]['present_end'])for i in range(1,600)]
    assert set(intervals)=={33,34}
    result=dict(schema='wolf-perf011-visible-human-started77',human_started=True,
        visible_two_turns_human_confirmed=True,agent_run_commands=0,
        renderer_sha256=kit['module_sha256'],guest=actual,
        presentations=600,scripted_quanta=600,coalesced_poses=0,
        prt_nominal_seconds=report['prt_nominal_seconds'],mos_nominal_seconds=report['mos_nominal_seconds'],
        nominal_presented_updates_per_second=report['nominal_prt_records_per_second'],
        steady_interval_updates_per_second=599000/sum(intervals),
        presentation_interval_nominal_ms=report['presentation_intervals_nominal_prt_ms'],
        distinct_interval_values=sorted(set(intervals)),
        clock_qualification='Physical Olimex, nominal PRT1kHz/MOS120Hz assumptions; counters agree within0.13%. No external optical frame-by-frame or oscillator calibration.',
        stage_nominal_ms=report['stages_nominal_prt_ms'],
        native_ccount=report['native_ccount'],
        native_note='Retained raw configured240MHz CCOUNT includes preemption; PRID/core endpoint is not an affinity qualification. Not the source of the reported presentation rate.',
        observed_rotation='E1L1(34,36), enemy-free,720degrees/20nominal seconds, paced at30Hz; a fixture result, not every gameplay scene.',
        original_native_restored=True,full_restore_sha256=sha(E/'flash-restore/read.bin'),
        final_observation=final,bench_generation=77,bench_released=False,
        custody='Restored and idle; retain actual77 for Smith. No automatic release or additional test.',
        raw_files={str(p):dict(bytes=p.stat().st_size,sha256=sha(p))for p in E.rglob('*.bin')},
        command_receipts=issued)
    (T/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ('presentations','coalesced_poses','nominal_presented_updates_per_second','presentation_interval_nominal_ms','original_native_restored','bench_released')},indent=2))


if __name__=='__main__':main()
