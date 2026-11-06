from pathlib import Path
import hashlib,json,os,signal,subprocess,time
b=Path(__file__).resolve().parent;start=time.monotonic();rows=[];results=[]
for n,d in json.loads((b/'source-freeze.json').read_text())['files'].items():assert hashlib.sha256((b/n).read_bytes()).hexdigest()==d,n
assert Path('/sys/devices/system/cpu/cpufreq/boost').read_text().strip()=='0'
def guard():
 t=[]
 for n in Path('/sys/class/hwmon').glob('*/name'):
  if n.read_text().strip()=='k10temp':
   for p in n.parent.glob('temp*_label'):
    if p.read_text().strip()=='Tctl':t.append(int(p.with_name(p.name.replace('_label','_input')).read_text())/1000)
 mem=int(next(s.split()[1]for s in Path('/proc/meminfo').read_text().splitlines()if s.startswith('MemAvailable:')));rows.append(dict(seconds=time.monotonic()-start,cpu_c=t,available_kib=mem));assert len(t)==1 and t[0]<80 and mem>524288
includes=['fab/src','fab/src/vdp','video','sdk','fab/src/vdp/userspace-vdp-gl/src','fab/src/vdp/userspace-vdp-gl/src/comdrivers','fab/src/vdp/userspace-vdp-gl/src/dispdrivers','fab/src/vdp/userspace-vdp-gl/src/userspace-platform','fab/src/vdp/userspace-vdp-gl/src/userspace-platform/matrix','deps/CRC/src','deps/ESP32Time']
commands=[['g++','-DUSERSPACE','-std=c++17','-O2','-g','-fPIC','-Wall','-Werror=return-type']+['-I'+n for n in includes]+['-c','adapter.cpp','-o','adapter.o'],['g++','-shared','-Wl,-z,defs','adapter.o','cache/rust_glue.o','cache/CRC16.o','cache/CRC32.o','cache/CrcFastReverse.o','cache/libvdp-gl.a','-pthread','-o','vdp_wolf_fab.so'],['g++','-std=c++17','-O2','selftest.cpp','-ldl','-o','selftest'],['./selftest',str(b/'vdp_wolf_fab.so')]]
try:
 for i,cmd in enumerate(commands):
  guard();beg=time.monotonic()
  with(b/f'build-{i}.log').open('w')as f:
   p=subprocess.Popen(cmd,cwd=b,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
   try:
    while p.poll()is None:
     guard()
     if time.monotonic()-beg>300:raise TimeoutError('single build step300s')
     time.sleep(.5)
   finally:
    if p.poll()is None:
     os.killpg(p.pid,signal.SIGTERM)
     try:p.wait(timeout=5)
     except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   results.append({'command':cmd,'returncode':p.returncode,'seconds':time.monotonic()-beg})
   if p.returncode:raise RuntimeError('build/contract step failed '+str(i))
finally:
 (b/'build-result.json').write_text(json.dumps({'steps':results,'guards':rows,'seconds':time.monotonic()-start,'outputs':{n:hashlib.sha256((b/n).read_bytes()).hexdigest()for n in ('vdp_wolf_fab.so','selftest')if(b/n).exists()}},indent=2)+'\n')
print('FAB BRIDGE BUILD AND CONTRACT CHECKS PASS',flush=True)
