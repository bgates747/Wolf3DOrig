"""Offline same-clock phase covariance from retained actual81, no new workload."""
from pathlib import Path
import collections,csv,hashlib,json,statistics
T=Path(__file__).resolve().parent;E=T.parent/'WOLF-PERF-016/results/actual81'
def main():
    out=[];inputs={}
    for p in sorted(E.glob('*-vdplet-room')):
        path=p/'samples.csv';inputs[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        all_rows=list(csv.DictReader(path.open()));assert [int(x['step'])for x in all_rows]==list(range(1,601))
        rows=all_rows[1:] # Initial presentation can start at a different raster phase.
        x=[int(r['wait_ms'])for r in rows];y=[int(r['present_fence_ms'])for r in rows]
        mx,my=statistics.mean(x),statistics.mean(y)
        covariance=sum((a-mx)*(b-my)for a,b in zip(x,y));vx=sum((a-mx)**2 for a in x);vy=sum((b-my)**2 for b in y)
        intervals=[int(b['present_end'])-int(a['present_end'])for a,b in zip(all_rows,all_rows[1:])]
        assert len(intervals)==599
        out.append(dict(case=p.name,phase_rows=599,excluded_initial_phase_row=True,
            wait_ms=mx,present_fence_ms=my,active_ms=statistics.mean(int(r['active_ms'])for r in rows),
            within_run_fence_vs_wait_slope=covariance/vx if vx else None,
            within_run_correlation=covariance/(vx*vy)**.5 if vx and vy else None,
            presentation_interval_histogram=dict(sorted(collections.Counter(intervals).items())),
            interval_count=599,steady_fps_nominal_prt=599000/sum(intervals)))
    assert len(out)==4
    result=dict(passed=True,scope='Offline actual81 same nominal1ms guest clock only; conditional association not causal/exclusive CPU attribution.',cases=out,inputs=inputs,
        limits='Combined presentation includes C3, ordered-fence query and serial handling. Native CCOUNT is not subtracted from guest ms. No new target observer, resource, model fit to raster clock, or hardware change.')
    path=T/'PRESENTATION-81-PHASES.json';path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
