"""Offline curated results only; never publishes RAM, firmware or custody records."""
from pathlib import Path
import csv,hashlib,json,math,shutil,statistics
T=Path(__file__).resolve().parents[1];B=T/'build/hardware09';E=B/'evidence';O=T/'results/hardware09';O.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stats(values):
 a=sorted(values);return dict(count=len(a),mean=statistics.mean(a),median=statistics.median(a),p95=a[math.ceil(len(a)*.95)-1],max=a[-1])
summary=json.loads((B/'physical-summary.json').read_text());assert summary['complete']and len(summary['cases'])==14 and len(summary['resource_probes'])==8
cases=[];samples={};hashes={}
for row in summary['cases']:
 p=E/row['case'];receipt=json.loads((p/'receipt.json').read_text());assert receipt['passed'];loading=receipt['loading'];assert loading['error']==loading['agnb_error']==0 and loading['total']==470 and loading['fences']==952
 entry=dict(case=row['case'],backend=row['backend'],mode=row['mode'],loading=loading)
 if row['mode']!='control':
  report=json.loads((p/'report.json').read_text())
  report['original_analyzer_clock_qualification']=report['clock_qualification']
  report['clock_qualification']='Physical Olimex; source-configured clocks, no external calibration'
  if row['mode']!='cpu':
   assert report['vdp_core_id']==0xcdcd
   report['vdp_core_id_encoding']='Raw Xtensa PRID 0xCDCD = PRO/core0, not a numeric FreeRTOS core index'
  entry.update(report=report);samples[row['case']]=list(csv.DictReader((p/'samples.csv').read_text().splitlines()));assert len(samples[row['case']])==report['completed_records']
  shutil.copyfile(p/'samples.csv',O/(row['case']+'.csv'))
 for name in ('timing.bin','native.bin','loading.bin','loading3.bin','before.bin','after.bin','stack.bin'):
  if(p/name).exists():hashes[row['case']+'/'+name]=sha(p/name)
 cases.append(entry)
pooled={}
for backend in ('bespoke','vdplet'):
 modes={}
 for mode in ('cpu','unpaced','paced'):
  group=[r for r in cases if r['backend']==backend and r['mode']==mode];assert len(group)==2
  rows=[v for r in group for v in samples[r['case']]];reports=[r['report']for r in group];ticks=sum(r['prt_ticks']for r in reports);mos=sum(r['mos_ticks']for r in reports)
  d=dict(cases=[r['case']for r in group],records=len(rows),scripted_quanta=1200,coalesced_quanta=1200-len(rows),prt_ticks=ticks,mos_ticks=mos,nominal_prt_rate=len(rows)*1000/ticks,nominal_mos_rate=len(rows)*120/mos,nominal_active_ms=stats([int(r['active_ms'])for r in rows]),pose_pack_ms=stats([int(r['pose_ms'])+int(r['pack_ms'])for r in rows]),stages_nominal_prt_ms={key:stats([int(r[key])for r in rows])for key in ('pose_ms','pack_ms','submit_ms','wait_ms','present_fence_ms')})
  if mode!='cpu':
   d['native_ms_at_configured_240MHz']={key:stats([int(r[key])/240000 for r in rows])for key in ('render_ccount','scope_ccount','dispatch_ccount')}
   d['active_ms_less_draw_mean_ms']=d['nominal_active_ms']['mean']-d['native_ms_at_configured_240MHz']['render_ccount']['mean']
  if mode=='paced':
   gaps=[int(rows2[i]['present_end'])-int(rows2[i-1]['present_end'])for r in group for rows2 in [samples[r['case']]]for i in range(1,len(rows2))];d['presentation_intervals_nominal_prt_ms']=stats(gaps)
  modes[mode]=d
 pooled[backend]=modes
result=dict(schema='wolf-perf003-curated-hardware09-v1',platform='Physical Olimex Agon Light 2',suite_complete=True,guests=14,resource_probes=8,clean_bootstrap_pairs=4,release_utc=json.loads((B/'release54.json').read_text())['released'],fixture=dict(episode=1,floor=1,tile_zero_based=[34,36],center=[34.5,36.5],turns=2,quanta=600,nominal_paced_seconds=20,enemies=0,doors_closed=22,statics=121,viewport=[32,20,256,160]),clock_limits='PRT nominal 1ms, MOS nominal120Hz, ESP32 source-configured240MHz/PMoff; no external calibration or optical scanout measurement',drawing_scope='Real renderer call: raycasting, background/walls/statics/HUD/weapon and synchronous framebuffer writes. Serial/response and presentation are outside this bracket.',cpu_scope='Scripted pose and backend preparation, no per-pose UART/render backpressure or populated-world simulation; B CPU submit bucket is serializer lifecycle work, not UART time.',pooled=pooled,cases=cases,resources=summary['resource_probes'],draw_ratio_vdplet_to_bespoke=pooled['vdplet']['unpaced']['native_ms_at_configured_240MHz']['render_ccount']['mean']/pooled['bespoke']['unpaced']['native_ms_at_configured_240MHz']['render_ccount']['mean'],native_a_sha256=summary['native_a_sha256'],native_b_sha256=summary['native_b_sha256'],module_sha256=summary['module_sha256'],source_freeze_commit='9e191aa625c7fd771cdd2a80a4323dd675eb3976',limitations=summary['limitations']+['Native O2/Canvas scratch versus module safe Os/PIC/helpers/direct rows; no attribution of aggregate gap to generic dispatch','Current hardware cohort has no new optical pixel/scanout review; retain earlier corrected fixture/Fab/human evidence','All14asset loads have zero timeouts/recoveries, but prior intermittent setup fault remains unresolved, no repair claim','Earlier Flexe/Fab runs establish functional completion, not a matched corrected-runtime timing cohort'])
(O/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');(O/'retained-raw-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
with(O/'cases.csv').open('w')as f:
 names=['case','backend','mode','records','coalesced','prt_ticks','mos_ticks','nominal_completed_per_second','draw_mean_ms_at_configured_240MHz','draw_p95_ms_at_configured_240MHz','active_mean_nominal_ms'];w=csv.DictWriter(f,fieldnames=names);w.writeheader()
 for c in cases:
  if c['mode']=='control':continue
  r=c['report'];native=r.get('native_ccount',{}).get('render_ccount',{});w.writerow(dict(case=c['case'],backend=c['backend'],mode=c['mode'],records=r['completed_records'],coalesced=r['coalesced_poses'],prt_ticks=r['prt_ticks'],mos_ticks=r['mos_ticks'],nominal_completed_per_second=r['nominal_prt_records_per_second'],draw_mean_ms_at_configured_240MHz=native.get('mean',0)/240000 if native else'',draw_p95_ms_at_configured_240MHz=native.get('p95',0)/240000 if native else'',active_mean_nominal_ms=r['stages_nominal_prt_ms']['active_ms']['mean']))
print(json.dumps({b:{m:{'rate':d['nominal_prt_rate'],'active_mean_ms':d['nominal_active_ms']['mean'],'pose_pack_ms':d['pose_pack_ms']['mean'],'draw_mean_ms':d.get('native_ms_at_configured_240MHz',{}).get('render_ccount',{}).get('mean'),'records':d['records'],'coalesced':d['coalesced_quanta']}for m,d in v.items()}for b,v in pooled.items()},indent=2));print('draw ratio',result['draw_ratio_vdplet_to_bespoke'])
