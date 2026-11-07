"""Offline raw/source/restore joins for the actual uncapped visible77 run."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import re

T=Path(__file__).resolve().parent;B=T/'build/hardware01';E=B/'evidence'
P=E/'human-run-collection';Q=T.parent/'WOLF-PERF-011'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())


def main():
    selected=read(B/'selection.json');ready=read(E/'ready.json')
    assert selected['mode']==4 and selected['uncapped'] and selected['manual_run_only']
    assert ready['selection_sha256']==sha(B/'selection.json') and ready['loaded_not_run']
    assert sha(B/'extension.json')==read(B/'context.json')['extension_sha256']
    for n,d in read(B/'extension.json').items():assert sha(n)==d,n
    original=read(selected['original_kit'])
    assert sha(selected['original_kit'])==selected['original_kit_sha256']
    for n,d in original['inputs'].items():assert sha(n)==d,n
    spec=importlib.util.spec_from_file_location('actual_binding',T.parent/'WOLF-PERF-009/guest_binding.py')
    binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding)
    actual=binding.verify(selected['guest'])
    assert actual['guest_sha256']==ready['guest_sha256']==sha(E/'entry/new-guest-read.bin')
    assert sha(E/'entry/module.bin')==selected['module_sha256']==ready['module_sha256']
    listing=Path(selected['guest']['listing']).read_text();binary=Path(selected['guest']['guest']).read_bytes()
    start=int(re.search(r'^([0-9A-F]{6})[^\n]*\bwp_next:',listing,re.M)[1],16)
    stop=min(int(m[1],16)for m in re.finditer(r'^([0-9A-F]{6})[^\n]*\bcall wp_prt_stop\b',listing,re.M)if int(m[1],16)>start)
    calls=[]
    for m in re.finditer(r'^([0-9A-F]{6}) ((?:[0-9A-F]{2} ){3}[0-9A-F]{2})\s+\d+\*?\s+call (w3d_vdu_present|w3d_audio_wait_for_vdp_ingress)\b',listing,re.M):
        if start<=int(m[1],16)<stop:calls.append(dict(address=int(m[1],16),encoded=m[2],target=m[3]))
    assert [x['target']for x in calls]==['w3d_vdu_present','w3d_audio_wait_for_vdp_ingress']
    for name in ('before.bin','after.bin','completed-ram.bin'):
        raw=(P/name).read_bytes()
        for op in actual['operands']+calls:
            at=op['address']-0x40000;expected=bytes.fromhex(op['encoded'])
            assert raw[at:at+4]==binary[at:at+4]==expected
    report=read(P/'report.json');receipt=read(P/'receipt.json')
    assert receipt['passed'] and receipt['human_started'] and receipt['agent_run'] is False
    assert report['mode']=='uncapped-visible' and report['completed_records']==600
    with (P/'samples.csv').open()as stream:rows=list(csv.DictReader(stream))
    assert [int(r['step'])for r in rows]==list(range(1,601))
    assert all(int(r['angle'])==(720*int(r['step'])//600)%360 and 0<int(r['active_ms'])<8000 for r in rows)
    assert receipt['balanced_stack'][0]==receipt['balanced_stack'][1]
    assert read(E/'human-review.json')['visible_two_turns_confirmed']
    assert read(E/'complete.json')['restored']
    assert (E/'flash-restore/read.bin').read_bytes()==Path(original['restore']).read_bytes()
    final=read(E/'final-checks/observation.json')
    assert all(final['checks'].values())and final['components']==original['incoming_components']
    assert final['lease']==ready['lease']
    archive=read(E/'entry/archive.json');assert archive['passed']and len(archive['moved'])==13
    old=read(Q/'RESULT.json')
    for n,d in old['raw_files'].items():assert sha(n)==d['sha256'],n
    commands=[]
    for p in E.rglob('*-issued.json'):
        data=read(p)
        if 'command'in data:
            assert not data['command'].strip().upper().startswith('RUN'),str(p)
            commands.append(dict(file=str(p),command=data['command']))
    intervals=[int(rows[i]['present_end'])-int(rows[i-1]['present_end'])for i in range(1,600)]
    assert set(intervals)=={33,34}
    result=dict(schema='wolf-perf012-uncapped-visible-actual77',human_started=True,
        human_confirmed_both_turns=True,agent_run_commands=0,synthetic_pacing=False,
        renderer_sha256=selected['module_sha256'],guest=actual,
        frames=600,prt_nominal_seconds=report['prt_nominal_seconds'],mos_nominal_seconds=report['mos_nominal_seconds'],
        nominal_presented_fps=report['nominal_prt_records_per_second'],
        steady_interval_updates_per_second=599000/sum(intervals),
        presentation_interval_nominal_ms=report['presentation_intervals_nominal_prt_ms'],
        native_ccount=report['native_ccount'],stage_nominal_ms=report['stages_nominal_prt_ms'],
        previous_paced=dict(nominal_presented_fps=old['nominal_presented_updates_per_second'],
            prt_nominal_seconds=old['prt_nominal_seconds'],
            steady_interval_updates_per_second=old['steady_interval_updates_per_second'],
            intervals=old['presentation_interval_nominal_ms']),
        comparison='Uncapped visible cadence is effectively unchanged. Whole-run difference is approximately one initial paced frame interval; steady means differ by one nominal tick over599 intervals. No meaningful speedup from removing the cap.',
        qualification='Physical presented-update timestamps, nominal PRT/MOS clocks, human confirmed rotation. No external oscillator or frame-by-frame optical calibration; not every gameplay scene or a pure renderer-throughput measure.',
        actual_present_calls=calls,old_sd_outputs_preserved=archive,
        original_native_restored=True,restore_sha256=sha(E/'flash-restore/read.bin'),
        final_observation=final,bench_generation=77,bench_released=False,
        custody='Original native restored and full idle handback passed; retain actual77 for Smith, no further test or automatic release.',
        raw_files={str(p):dict(bytes=p.stat().st_size,sha256=sha(p))for p in E.rglob('*.bin')},
        command_receipts=commands)
    (T/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ('frames','prt_nominal_seconds','nominal_presented_fps','steady_interval_updates_per_second','presentation_interval_nominal_ms','original_native_restored','bench_released')},indent=2))


if __name__=='__main__':main()
