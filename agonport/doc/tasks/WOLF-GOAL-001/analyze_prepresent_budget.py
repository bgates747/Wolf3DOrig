"""Offline sequential-frame budget from existing same-clock completion records."""
from pathlib import Path
import csv,hashlib,json,statistics
T=Path(__file__).resolve().parent
def main():
    cases=[];inputs={}
    for task,generation in [('WOLF-PERF-016',81),('WOLF-PERF-017',85)]:
        root=T.parent/task/'results'/('actual'+str(generation))/'evidence'
        if generation==81:root=root.parent
        for p in sorted(root.glob('*-vdplet-room/samples.csv')):
            rows=list(csv.DictReader(p.open()))
            assert [int(r['step'])for r in rows]==list(range(1,601))
            # Time from the preceding completed presentation/fence through the
            # current render reply; the present call is still after this stamp.
            before_present=[int(b['reply_end'])-int(a['present_end'])
                for a,b in zip(rows,rows[1:])]
            intervals=[int(b['present_end'])-int(a['present_end'])
                for a,b in zip(rows,rows[1:])]
            assert all(0<v<8000 for v in before_present)
            assert all(before_present[i]<=intervals[i]for i in range(599))
            cases.append(dict(generation=generation,case=p.parent.name,intervals=599,
                before_present_ms_mean=statistics.mean(before_present),
                before_present_ms_min=min(before_present),before_present_ms_max=max(before_present),
                within_nominal_60hz_single_refresh=sum(v*60<=1000 for v in before_present),
                completed_interval_ms_mean=statistics.mean(intervals)))
            inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    assert len(cases)==8
    result=dict(passed=True,cases=cases,inputs=inputs,
        scope='Existing sequential guest-clock reply/presentation stamps only. Nominal 60Hz source budget, no externally calibrated oscillator or optical scanout claim.',
        limits='Reply phase includes renderer/transport/scheduling waits; not exclusive CPU or unavoidable cost after a future pipeline redesign. Does not isolate C3/fence timing or establish a hidden cap/extra VSYNC. No target run, removal, reordering or new observer selected.')
    (T/'PREPRESENT-BUDGET.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(cases,indent=2))
if __name__=='__main__':main()
