"""Serial guarded Pi compilation only. No target/emulator execution."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,time
T=Path(__file__).resolve().parents[1];B=T/'build/hardware01'
PY='/Agon/mystuff/agon-dev-env/.venv/bin/python'
HELPER='/Agon/mystuff/agon-dev-env/cross-agent/pi5-workloads/pi5_lease.py'
lease=sys.argv[1];rows=[];guards=[]
resume=len(sys.argv)>2 and sys.argv[2]=='resource'
if resume:
    prior=json.loads((B/'compile-receipt.json').read_text());rows=prior['steps'];guards=prior['guards']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def guard():
    temp=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
    available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))
    guards.append({'epoch':time.time(),'cpu_c':temp,'available_kib':available})
    assert temp<80 and available>=524288,'Host thermal/RAM bound'
def compile(command,cwd,log,bound):
    subprocess.run([PY,HELPER,'assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL)
    guard();begin=time.monotonic()
    with log.open('x') as output:
        p=subprocess.Popen(command,cwd=cwd,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            while p.poll() is None:
                guard();assert time.monotonic()-begin<bound,'Compiler deadline';time.sleep(.5)
            rows.append({'argv':command,'log':str(log),'returncode':p.returncode,'seconds':time.monotonic()-begin})
            assert p.returncode==0,log
        finally:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
            (B/'compile-receipt.json').write_text(json.dumps({'steps':rows,'guards':guards},indent=2)+'\n')
if not resume:
    for n,d in json.loads((B/'source-freeze.json').read_text()).items():assert sha(B/n)==d,n
assembler=str(T.parents[3]/'src/asm/wolf3d/tgt/.tools/ez80asm')
for backend in (() if resume else ('bespoke','vdplet')):
    for mode in ('cpu','unpaced','paced','control'):
        d=B/backend/mode
        compile([assembler,'wolf3d.asm','wolf3d.bin','-l','-c'],d/'source',d/'assembly-hardware01.log',120)
        import shutil
        shutil.copyfile(d/'source/wolf3d.bin',d/'payload/wolf3d.bin')
        e=json.loads((d/'payload/expected.json').read_text());e.update(schema='wolf-perf003-physical-hardware01',mode=mode)
        e['files']['wolf3d.bin']={'bytes':(d/'payload/wolf3d.bin').stat().st_size,'sha256':sha(d/'payload/wolf3d.bin')}
        (d/'payload/expected.json').write_text(json.dumps(e,indent=2)+'\n')
        print('ASSEMBLED',backend,mode,flush=True)
import shutil
shutil.copyfile(T/'hardware/resource.asm',B/'resource.asm')
resource_log=B/'resource-assembly.log'
revision=2
while resource_log.exists():
    resource_log=B/f'resource-assembly-r{revision:02d}.log';revision+=1
compile([assembler,'resource.asm','resource.bin','-l','-c'],B,resource_log,120)
compile(['nice','-n','10','/Agon/mystuff/agon-vdplet/.venv/bin/pio','run','-d',str(B/'native-a'),'-e','esp32dev','-j','1'],B,B/'native-compile.log',900)
outputs={str(p.relative_to(B)):dict(bytes=p.stat().st_size,sha256=sha(p))for p in [B/'resource.bin']+list((B/'native-a/.pio/build/esp32dev').glob('firmware.*')) if p.is_file()}
(B/'outputs.json').write_text(json.dumps(outputs,indent=2)+'\n')
print('HARDWARE01 COMPILATION PASS',flush=True)
