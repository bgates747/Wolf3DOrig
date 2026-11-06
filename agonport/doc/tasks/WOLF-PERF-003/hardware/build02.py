"""Finite serial Pi guest assembly, no target/emulator/native rebuild."""
from pathlib import Path
import hashlib,json,os,signal,shutil,subprocess,sys,time
T=Path(__file__).resolve().parents[1];B=T/'build/hardware02';lease=sys.argv[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,digest in json.loads((B/'source-freeze.json').read_text()).items():assert sha(B/name)==digest,name
steps=[];guards=[]
def guard():
 temp=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
 available=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))
 guards.append(dict(epoch=time.time(),cpu_c=temp,available_kib=available));assert temp<80 and available>=524288
for backend in ('bespoke','vdplet'):
 for mode in ('cpu','unpaced','paced','control'):
  subprocess.run(['/Agon/mystuff/agon-dev-env/.venv/bin/python','/Agon/mystuff/agon-dev-env/cross-agent/pi5-workloads/pi5_lease.py','assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL)
  d=B/backend/mode;guard();begin=time.monotonic()
  with(d/'assembly.log').open('x')as log:
   p=subprocess.Popen([str(T.parents[3]/'src/asm/wolf3d/tgt/.tools/ez80asm'),'wolf3d.asm','wolf3d.bin','-l','-c'],cwd=d/'source',stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   try:
    while p.poll()is None:guard();assert time.monotonic()-begin<120;time.sleep(.25)
    steps.append(dict(backend=backend,mode=mode,returncode=p.returncode,seconds=time.monotonic()-begin));assert p.returncode==0,d/'assembly.log'
   finally:
    if p.poll()is None:
     os.killpg(p.pid,signal.SIGTERM)
     try:p.wait(timeout=5)
     except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    (B/'compile-receipt.json').write_text(json.dumps(dict(steps=steps,guards=guards),indent=2)+'\n')
  shutil.copyfile(d/'source/wolf3d.bin',d/'payload/wolf3d.bin')
  assert(d/'payload/wolf3d.bin').stat().st_size<0x60000
  expected=json.loads((d/'payload/expected.json').read_text());expected.update(schema='wolf-perf003-physical-hardware02')
  expected['files']['wolf3d.bin']=dict(bytes=(d/'payload/wolf3d.bin').stat().st_size,sha256=sha(d/'payload/wolf3d.bin'))
  (d/'payload/expected.json').write_text(json.dumps(expected,indent=2)+'\n')
  print('ASSEMBLED',backend,mode,flush=True)
print('EIGHT ASSEMBLIES PASS',flush=True)
