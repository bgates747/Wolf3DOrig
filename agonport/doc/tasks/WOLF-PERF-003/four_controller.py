"""Pi orchestration only. User-approved finite four-way cohort on held Oryx."""
from pathlib import Path
import subprocess,json,sys,time
ROOT=Path('/Agon/mystuff/Wolf3dOrig');TASK=ROOT/'agonport/doc/tasks/WOLF-PERF-003';REMOTE='/home/smith/Agon/mystuff/Wolf3dOrig';SSH=['ssh','-o','BatchMode=yes','oryx-linuxlite'];PY=REMOTE+'/.venv/bin/python';OUT=TASK/'build/four01';OUT.mkdir(exist_ok=True)
profiles=json.loads((OUT/'profiles.json').read_text());rows=[];lease=sys.argv[1]
def save():
 (OUT/'controller-results.json').write_text(json.dumps({'rule':'per Flexe backend firstsuccess->five trials;firstfailure->two trials;hostguard aborts','trials':rows},indent=2)+'\n')
def one(emulator,backend,trial):
 r=next(r for r in profiles if(r['emulator'],r['backend'],r['trial'])==(emulator,backend,trial));p=r['profile']
 subprocess.run(['/Agon/mystuff/agon-dev-env/.venv/bin/python','/Agon/mystuff/agon-dev-env/cross-agent/vdplet-rollout/oryx_lease.py','assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL)
 print('START',emulator,backend,trial,flush=True)
 script='four_fab_run.py'if emulator=='fab'else'matched_run.py'
 command=SSH+[PY,REMOTE+'/agonport/doc/tasks/WOLF-PERF-003/'+script]
 command+=['run','--profile',p]if emulator=='fab'else[p,'--timeout','300']
 beg=time.monotonic();result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=350)
 (OUT/f'{emulator}-{backend}-{trial:02d}.log').write_text(result.stdout)
 name='result.json'if emulator=='fab'else'runner.json';data=json.loads(subprocess.check_output(SSH+['cat',p+'/run/'+name],text=True,timeout=20))
 row={**r,'success':bool(data.get('success')),'error':data.get('error'),'process_returncode':result.returncode,'controller_seconds':time.monotonic()-beg,'whole_seconds':data.get('whole_seconds',data.get('whole_process_seconds'))};rows.append(row);save();print('PASS'if row['success']else'FAIL',emulator,backend,trial,row.get('error'),flush=True)
 if row['error']and any(x in row['error'].lower()for x in ('thermal','ram guard')):raise RuntimeError('hostguard stops cohort')
 return row['success']
try:
 # First exercise the new source bridge; do not bury an adapter failure in repeats.
 for backend in ('vdplet','bespoke'):
  if not one('fab',backend,1):raise RuntimeError('Fab correctness failure; preserve cohort for source disposition')
 for backend in ('bespoke','vdplet'):
  success=one('flexe',backend,1);limit=5 if success else 2
  for trial in range(2,limit+1):one('flexe',backend,trial)
 (OUT/'complete.json').write_text(json.dumps({'complete':True,'trials':len(rows),'successes':sum(r['success']for r in rows)},indent=2)+'\n');print('FOUR-WAY COHORT FINISHED',len(rows),flush=True)
except Exception as e:
 (OUT/'controller-error.txt').write_text(repr(e)+'\n');save();raise
