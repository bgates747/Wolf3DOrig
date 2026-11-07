#!/usr/bin/env python3
"""Decode guest output, reject incomplete/mismatched runs, retain raw CSV."""
from pathlib import Path
import argparse,csv,json,statistics,struct,hashlib
MODE={1:'cpu',2:'unpaced',3:'paced',4:'uncapped-visible'}
def u24(b):return int.from_bytes(b,'little')
def summary(xs):
 if not xs:return None
 a=sorted(xs);return {'mean':statistics.mean(a),'median':statistics.median(a),'p95':a[min(len(a)-1,(95*len(a)+99)//100-1)],'max':a[-1],'count':len(a)}
def analyze(directory):
 directory=Path(directory);b=(directory/'timing.bin').read_bytes()
 if len(b)!=33+600*27 or b[:5]!=b'WPF3\x01' or b[5] not in MODE or b[6:8]!=b'\1\1':raise ValueError('invalid header, length, completion or timer restoration')
 count,ps,pe,ms,me,empty,nsize=[u24(b[8+i*3:11+i*3]) for i in range(7)]
 if b[32] not in (1,2) or b[29:32]!=bytes([34,36,0]) or not 0<count<=600:raise ValueError('fixture identity/count mismatch')
 rows=[]
 for i in range(count):
  v=[u24(b[33+i*27+k*3:36+i*27+k*3]) for k in range(9)]
  n,angle,t0,t1,t2,t3,t4,t5,size=v
  if not 1<=n<=600 or angle!=(720*n//600)%360:raise ValueError('pose mismatch')
  if rows and n<=rows[-1]['step']:raise ValueError('duplicate or out-of-order pose')
  if not t0<=t1<=t2<=t3<=t4<=t5:raise ValueError('unordered stage stamps')
  if size!=(24 if b[32]==1 else 28):raise ValueError(f'non-player-only delta: {size}')
  rows.append(dict(step=n,angle=angle,start=t0,pose_end=t1,pack_end=t2,send_end=t3,reply_end=t4,present_end=t5,batch_bytes=size,pose_ms=t1-t0,pack_ms=t2-t1,submit_ms=t3-t2,wait_ms=t4-t3,present_fence_ms=t5-t4,active_ms=t5-t0))
 if rows[-1]['step']!=600 or (b[5]!=3 and count!=600):raise ValueError('incomplete rotation')
 if any(b[33+count*27:]):raise ValueError('sample overflow/extra rows')
 prt=pe-ps;mos=me-ms
 if prt<=0 or mos<0:raise ValueError('invalid elapsed counters')
 report={'schema':'wolf-perf003-result-v1','backend':'bespoke' if b[32]==1 else 'vdplet','mode':MODE[b[5]],'completed_records':count,'scripted_steps':600,'coalesced_poses':600-count,'prt_ticks':prt,'mos_ticks':mos,'prt_nominal_seconds':prt/1000,'mos_nominal_seconds':mos/120,'nominal_prt_records_per_second':count*1000/prt,'nominal_mos_records_per_second':None if mos==0 else count*120/mos,'clock_ratio_mos_seconds_to_prt_seconds':None if mos==0 else (mos/120)/(prt/1000),'empty_600_loop_prt_ticks':empty,'clock_qualification':'Physical fixture; nominal PRT/MOS clocks without external calibration','tile':[34,36],'enemies':0,'host_wall_seconds':'runner records entire process, not race window','stages_nominal_prt_ms':{},'revolutions':{}}
 for key in ('pose_ms','pack_ms','submit_ms','wait_ms','present_fence_ms','active_ms'):
  report['stages_nominal_prt_ms'][key]=summary([r[key] for r in rows])
 report['wire_accounting']={'prepared_bytes_per_pose':24 if b[32]==1 else 28,'request_bytes_per_completed_pose':24 if b[32]==1 else 65,'derivation':'A: pose17+render7; B: clear6+write8+payload28+consolidate6+RUN17. Timed request paths only; replies and paced C3/mode-fence separate. Confirm against actual UART trace before throughput interpretation.'}
 report['cpu_mode_submit_bucket_note']='In CPU mode submit_ms is serializer lifecycle bookkeeping, with no UART submission.'
 report['active_over_33_333_ms']=sum(r['active_ms']>1000/30 for r in rows)
 for rev in (1,2):
  rs=[r for r in rows if (r['step']-1)//300+1==rev]
  report['revolutions'][str(rev)]={'records':len(rs),'active_ms':summary([r['active_ms'] for r in rs])}
 if b[5]>1:
  raw=(directory/'native.bin').read_bytes()
  if len(raw)!=nsize or nsize!=16+count*20:raise ValueError('native size mismatch')
  magic,version,native_count,core=struct.unpack_from('<4I',raw)
  if (magic,version,native_count)!=(0x314e5057,1,count):raise ValueError('native header/count mismatch')
  for i,row in enumerate(rows):
   idx,angle,render,scope,total=struct.unpack_from('<5I',raw,16+i*20)
   if idx!=i or angle!=row['angle'] or not 0<render<=scope<=total<0x80000000:raise ValueError('native sample identity/order/wrap mismatch')
   row.update(render_ccount=render,scope_ccount=scope,dispatch_ccount=total)
  report['vdp_core_id']=core
  report['native_ccount']={k:summary([r[k] for r in rows]) for k in ('render_ccount','scope_ccount','dispatch_ccount')}
  report['native_ccount_note']='Local raw CCOUNT intervals; native dispatch instrumentation must be qualified before accepting dispatch_ccount; includes preemption/service calls. Not calibrated physical milliseconds or exclusive CPU work.'
  for rev in (1,2):
   report['revolutions'][str(rev)]['render_ccount']=summary([r['render_ccount'] for r in rows if (r['step']-1)//300+1==rev])
 # Swap fence intervals, including idle gaps; first interval excluded as no previous sample.
 report['presentation_intervals_nominal_prt_ms']=summary([rows[i]['present_end']-rows[i-1]['present_end'] for i in range(1,count)]) if b[5] in (3,4) else None
 report['sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.bin')}
 with (directory/'samples.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 (directory/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);args=p.parse_args();print(json.dumps(analyze(args.directory),indent=2))
