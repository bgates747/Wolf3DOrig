"""Finite serial host-only work census; never contacts the hardware bench."""
from pathlib import Path
import argparse,hashlib,json,os,signal,subprocess,time
T=Path(__file__).resolve().parent
D=Path('/Agon/mystuff/agon-dev-env')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(lease):
    B=T/'build/room-count01';B.mkdir(exist_ok=False)
    kit=json.loads((T.parent/'WOLF-PERF-017/build/hardware01/kit.json').read_text())
    level=Path(kit['stage']['level_00/state_easy.w3l'])
    assert sha(level)==kit['inputs'][str(level)]
    original=T/'build/r01/original'
    reference=T.parent/'WOLF-PERF-009/build/r01/candidate'
    for p in (original/'production').iterdir():
        if p.is_file():assert sha(p)==sha(reference/'production'/p.name)
    files=[T/'count_room.cpp',T/'count_room.py',T/'PLAN.md',level,
        T.parent.parent.parent.parent/'src/asm/wolf3d/src/wolf3d_world.inc']
    files += [p for p in (original/'production').rglob('*')if p.is_file()]+[original/'wolf3d_tables.inc']
    r=dict(passed=False,inputs={str(p):sha(p)for p in files},steps=[],guards=[])
    start=time.monotonic();child=None
    def stop(number,_):r['signal']=number;raise KeyboardInterrupt(number)
    for number in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(number,stop)
    def guard():
        temp=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
        mem=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))
        r['guards'].append(dict(cpu_c=temp,available_kib=mem));assert temp<80 and mem>=524288 and time.monotonic()-start<180
    try:
        for name,argv in [('compile',['g++','-std=c++17','-O2','-g','-Wall','-Wextra','-Werror','-pedantic','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-pie','-no-pie','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',T/'count_room.cpp','-o',B/'count-room']),('census',[B/'count-room',level])]:
            subprocess.run([str(D/'.venv/bin/python'),str(D/'cross-agent/pi5-workloads/pi5_lease.py'),'assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL)
            guard();begin=time.monotonic()
            with (B/(name+'.log')).open('x')as log:
                child=subprocess.Popen(list(map(str,argv)),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                while child.poll()is None:guard();time.sleep(.1)
            r['steps'].append(dict(name=name,returncode=child.returncode,seconds=time.monotonic()-begin));assert child.returncode==0,name;child=None
        r['counts']=json.loads((B/'census.log').read_text());r['passed']=True
        r['limits']='Unchanged control raycast on canonical W3L map/door/player inputs and exact600angle script; host opportunity census, not native hit counts or timing.'
    finally:
        if child is not None and child.poll()is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        r['seconds']=time.monotonic()-start;(B/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r['counts']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--lease',required=True);main(p.parse_args().lease)
