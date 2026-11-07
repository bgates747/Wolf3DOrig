"""Oryx-only private x86 bridge build, actual lease before each child."""
from pathlib import Path
import argparse,hashlib,json,os,signal,subprocess,time
b=Path(__file__).resolve().parent

def main(lease):
    start=time.monotonic();rows=[];results=[];child=None
    freeze=json.loads((b/'source-freeze.json').read_text())
    for n,d in freeze['files'].items():assert hashlib.sha256((b/n).read_bytes()).hexdigest()==d,n
    assert Path('/sys/devices/system/cpu/cpufreq/boost').read_text().strip()=='0'
    def own():
        subprocess.run(['ssh','-o','BatchMode=yes','raspberrypi','/Agon/mystuff/agon-dev-env/.venv/bin/python','/Agon/mystuff/agon-dev-env/cross-agent/vdplet-rollout/oryx_lease.py','assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL,timeout=20)
    def guard():
        temps=[]
        for n in Path('/sys/class/hwmon').glob('*/name'):
            if n.read_text().strip()=='k10temp':
                for p in n.parent.glob('temp*_label'):
                    if p.read_text().strip()=='Tctl':temps.append(int(p.with_name(p.name.replace('_label','_input')).read_text())/1000)
        mem=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))
        rows.append(dict(seconds=time.monotonic()-start,cpu_c=temps,available_kib=mem));assert len(temps)==1 and temps[0]<80 and mem>524288 and time.monotonic()-start<600
    includes=['fab/src','fab/src/vdp','video','sdk','fab/src/vdp/userspace-vdp-gl/src','fab/src/vdp/userspace-vdp-gl/src/comdrivers','fab/src/vdp/userspace-vdp-gl/src/dispdrivers','fab/src/vdp/userspace-vdp-gl/src/userspace-platform','fab/src/vdp/userspace-vdp-gl/src/userspace-platform/matrix','deps/CRC/src','deps/ESP32Time']
    commands=[['g++','-DUSERSPACE','-std=c++17','-O2','-g','-fPIC','-Wall','-Werror=return-type']+['-I'+n for n in includes]+['-c','adapter.cpp','-o','adapter.o'],['g++','-shared','-Wl,-z,defs','adapter.o','cache/rust_glue.o','cache/CRC16.o','cache/CRC32.o','cache/CrcFastReverse.o','cache/libvdp-gl.a','-pthread','-o','vdp_wolf_fab.so'],['g++','-std=c++17','-O2','selftest.cpp','-ldl','-o','selftest'],['./selftest',str(b/'vdp_wolf_fab.so')]]
    try:
        for i,args in enumerate(commands):
            own();guard();beg=time.monotonic()
            with (b/f'build-{i}.log').open('x') as log:
                child=subprocess.Popen(args,cwd=b,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                while child.poll() is None:
                    guard();assert time.monotonic()-beg<300;time.sleep(.5)
            results.append(dict(argv=args,returncode=child.returncode,seconds=time.monotonic()-beg));assert child.returncode==0
            child=None
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        result=dict(passed=len(results)==4 and all(r['returncode']==0 for r in results),steps=results,guards=rows,seconds=time.monotonic()-start,outputs={n:hashlib.sha256((b/n).read_bytes()).hexdigest() for n in ('vdp_wolf_fab.so','selftest') if (b/n).exists()})
        (b/'build-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS private Fab source bridge build/contract; no Xtensa execution')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--lease',required=True);main(p.parse_args().lease)
