"""Eight serial assemblies and ordinary source/layout checks, actual Pi owner only."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,time
T=Path(__file__).resolve().parents[1];B=T/'build/hardware05';lease=sys.argv[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for n,h in json.loads((B/'source-freeze.json').read_text()).items():assert sha(B/n)==h,n
steps=[];guards=[];start=time.monotonic()
def guard():
 c=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000;k=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))
 guards.append(dict(epoch=time.time(),cpu_c=c,available_kib=k));assert c<80 and k>=524288 and time.monotonic()-start<600

def run(args,cwd,label):
 subprocess.run(['/Agon/mystuff/agon-dev-env/.venv/bin/python','/Agon/mystuff/agon-dev-env/cross-agent/pi5-workloads/pi5_lease.py','assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL)
 guard();begin=time.monotonic()
 with(B/(label+'.log')).open('x')as log:
  p=subprocess.Popen(args,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   while p.poll()is None:guard();assert time.monotonic()-begin<120;time.sleep(.1)
   steps.append(dict(label=label,args=args,returncode=p.returncode,seconds=time.monotonic()-begin));assert p.returncode==0,label
  finally:
   if p.poll()is None:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   (B/'compile-receipt.json').write_text(json.dumps(dict(steps=steps,guards=guards),indent=2)+'\n')
for backend in ('bespoke','vdplet'):
 for mode in ('cpu','unpaced','paced','control'):
  run([str(T.parents[3]/'src/asm/wolf3d/tgt/.tools/ez80asm'),'wolf3d.asm','wolf3d.bin','-l','-c'],B/backend/mode/'source',f'asm-{backend}-{mode}')
run([sys.executable,str(T/'hardware/test_trace04.py')],T,'decoder')
run([sys.executable,str(T/'hardware/check05.py')],T,'source-layout')
print('PASS8 observer benchmark assemblies and source/layout checks',flush=True)
