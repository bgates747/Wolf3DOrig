"""Finite serial host checks/four A guests/native compile under Pi ownership."""
from pathlib import Path
import hashlib,json,os,signal,shutil,subprocess,sys,time
T=Path(__file__).resolve().parents[1];B=T/'build/hardware03';lease=sys.argv[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
steps=[];guards=[]
for name,digest in json.loads((B/'source-freeze.json').read_text()).items():assert sha(B/name)==digest,name
def guard():
 temp=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
 available=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))
 guards.append(dict(epoch=time.time(),cpu_c=temp,available_kib=available));assert temp<80 and available>=524288
def run(args,cwd,label,bound,env=None):
 subprocess.run(['/Agon/mystuff/agon-dev-env/.venv/bin/python','/Agon/mystuff/agon-dev-env/cross-agent/pi5-workloads/pi5_lease.py','assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL)
 guard();begin=time.monotonic()
 with(B/(label+'.log')).open('x')as log:
  p=subprocess.Popen(args,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=env)
  try:
   while p.poll()is None:guard();assert time.monotonic()-begin<bound;time.sleep(.25)
   steps.append(dict(label=label,args=args,returncode=p.returncode,seconds=time.monotonic()-begin));assert p.returncode==0,B/(label+'.log')
  finally:
   if p.poll()is None:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   (B/'compile-receipt.json').write_text(json.dumps(dict(steps=steps,guards=guards),indent=2)+'\n')
# Extract the actual method rather than recoding the protocol in the test.
host=B/'host';host.mkdir();s=(B/'native-a/video/wolf3d.h').read_text()
start=s.index('WolfPerfRecorder wp_recorder;');end=s.index('\n\tbool handle_subcommand',start)
(host/'exact_control.inc').write_text(s[start:end]);shutil.copyfile(B/'native-a/video/wolf_perf_recorder.h',host/'wolf_perf_recorder.h');shutil.copyfile(T/'hardware/lifetime03.cpp',host/'test.cpp')
run(['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','test.cpp','-o','test-lifetime'],host,'host-build',120)
run(['./test-lifetime'],host,'host-lifetime',120,os.environ|{'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
for mode in ('cpu','unpaced','paced','control'):
 d=B/'bespoke'/mode
 run([str(T.parents[3]/'src/asm/wolf3d/tgt/.tools/ez80asm'),'wolf3d.asm','wolf3d.bin','-l','-c'],d/'source','asm-'+mode,120)
 shutil.copyfile(d/'source/wolf3d.bin',d/'payload/wolf3d.bin')
 e=json.loads((d/'payload/expected.json').read_text());e['schema']='wolf-perf003-physical-hardware03';e['files']['wolf3d.bin']=dict(bytes=(d/'payload/wolf3d.bin').stat().st_size,sha256=sha(d/'payload/wolf3d.bin'));(d/'payload/expected.json').write_text(json.dumps(e,indent=2)+'\n')
 print('ASSEMBLED A',mode,flush=True)
run(['nice','-n','10','/Agon/mystuff/agon-vdplet/.venv/bin/pio','run','-d',str(B/'native-a'),'-e','esp32dev','-j','1'],B,'native-compile',900)
print('HARDWARE03 HOST/ASSEMBLY/NATIVE BUILD PASS',flush=True)
