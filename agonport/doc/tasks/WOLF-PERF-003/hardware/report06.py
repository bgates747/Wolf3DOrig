"""Offline physical result summary. Never invokes devices, tests or collectors."""
from pathlib import Path
import csv,json,statistics
B=Path(__file__).resolve().parents[1]/'build/hardware06';E=B/'evidence'
rows=[]
for directory in sorted(E.glob('[0-9][0-9]-*')):
 receipt=directory/'receipt.json'
 if not receipt.exists():continue
 r=json.loads(receipt.read_text());assert r['passed']
 row={'case':directory.name,'backend':r['backend'],'mode':r['mode'],'whole_operation_seconds':r['whole_seconds'],'loading':r.get('loading')}
 if r['mode']!='control':
  samples=list(csv.DictReader((directory/'samples.csv').open()));n=len(samples);g=r['result']
  assert n==g['completed_records'] and int(samples[-1]['step'])==600
  row.update(records=n,coalesced=600-n,prt_ticks=g['prt_ticks'],mos_ticks=g['mos_ticks'],nominal_prt_rate=n*1000/g['prt_ticks'],nominal_mos_rate=n*120/g['mos_ticks'],mean_pose_pack_nominal_ms=statistics.mean(float(s['pose_ms'])+float(s['pack_ms'])for s in samples),stages=g['stages_nominal_prt_ms'])
  if r['mode']!='cpu':
   row['native_ccount']=g['native_ccount']
   row['draw_ms_at_source_nominal_240MHz']=g['native_ccount']['render_ccount']['mean']/240000
 rows.append(row)
complete=(E/'complete.json').exists()
probes=[]
for p in sorted(E.glob('probe-*/receipt.json')):
 r=json.loads(p.read_text());assert r['passed'];probes.append({'name':p.parent.name,'stack_minimum_bytes':r['minimum_stack_bytes'],'values':r['values']})
if complete:
 assert len(rows)==14 and len(probes)==8
 for mode in ('cpu','unpaced','paced'):assert [r['backend']for r in rows if r['mode']==mode]==['bespoke','vdplet','vdplet','bespoke']
report=dict(platform='Physical Olimex Agon Light 2',complete=complete,cases=rows,resource_probes=probes,clock_qualification='Nominal PRT 1ms/tick, MOS120units/s, source-configured ESP32 240MHz/PMoff; no external calibration or optical measurement',counter_boundaries='Pose/pack, sender/receiver/presentation and nested native draw/scope/dispatch intervals are distinct; do not sum overlapping stages or call wait time exclusive VDP drawing',native_a_sha256=json.loads((B/'kit.json').read_text())['native_a_sha256'],native_b_sha256='7593b9cf9a2dc60e81221d998527d4ac0d1c3f51077348ea03e869016aa0581d',module_sha256='1907ce1711f68676dc1c0c6eb70b8f55ae03d0934aee537329edcf77fe652610',limitations=['B module Os/PIC/helpers versus native O2 and Canvas scratch versus direct rows: aggregate implementation comparison, not pure dispatch overhead','CPU workload is scripted pose/packing, not populated-world simulation','Paced latest-pose coalescing may retain fewer than600 records; closing step600 required','Inherited generic per-case analyzer clock label mentions emulator; this summary explicitly identifies actual physical execution and preserves originals'])
(B/'physical-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
