"""Oryx-only finite owned process-group guard for one prepared native leaf."""
from pathlib import Path
import argparse, hashlib, json, os, re, signal, subprocess, sys, time


def main():
    p=argparse.ArgumentParser();p.add_argument('--lease',required=True);a=p.parse_args()
    root=Path(__file__).resolve().parent
    out=root/'supervisor';out.mkdir(exist_ok=False)
    result=dict(passed=False,lease=a.lease,guards=[]);child=None;began=time.monotonic()
    def interrupted(sig,_):raise KeyboardInterrupt(sig)
    for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):signal.signal(sig,interrupted)
    def guard():
        if Path('/sys/devices/system/cpu/cpufreq/boost').read_text().strip()!='0':
            raise RuntimeError('Boost is not off')
        temps=[]
        for sensor in Path('/sys/class/hwmon').glob('*/name'):
            if sensor.read_text().strip()=='k10temp':
                for label in sensor.parent.glob('temp*_label'):
                    if label.read_text().strip()=='Tctl':
                        temps.append(int(label.with_name(label.name.replace('_label','_input')).read_text())/1000)
        available=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))
        result['guards'].append(dict(cpu_c=temps,available_kib=available,seconds=time.monotonic()-began))
        if len(temps)!=1 or temps[0]>=80 or available<524288 or time.monotonic()-began>720:
            raise RuntimeError('Thermal/sensor/memory/time guard')
    try:
        subprocess.run(['ssh','-o','BatchMode=yes','raspberrypi',
            '/Agon/mystuff/agon-dev-env/.venv/bin/python',
            '/Agon/mystuff/agon-dev-env/cross-agent/vdplet-rollout/oryx_lease.py',
            'assert-owner','--owner','wolf3dorig','--lease',a.lease],check=True,timeout=30)
        pins=json.loads((root/'INPUTS.json').read_text())
        for name,digest in pins['files'].items():
            if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
                raise RuntimeError('Changed input: '+name)
        env=dict(os.environ)
        for key in list(env):
            if key in ('LD_PRELOAD','LD_LIBRARY_PATH','BASH_ENV') or key.startswith(('AGON_FLEXE_','FLEXE_')):
                env.pop(key)
        guard()
        closure=json.loads((root/'backend/closure.json').read_text())['retained_dependency_closure']
        for name,info in closure.items():
            actual=Path(name).resolve()
            if str(actual)!=info['realpath'] or hashlib.sha256(actual.read_bytes()).hexdigest()!=info['sha256']:
                raise RuntimeError('Changed backend library: '+name)
        loader=subprocess.check_output(['ldd',str(root/'backend/flexe-vdp.so')],env=env,text=True,timeout=20)
        (out/'loader.txt').write_text(loader)
        resolved={str(Path(n).resolve()) for n in re.findall(r'(/[^\s()]+)',loader)}
        expected={info['realpath'] for info in closure.values()}
        if resolved!=expected:raise RuntimeError('Actual loader closure differs from retained backend closure')
        with (out/'worker.log').open('x') as log:
            child=subprocess.Popen([sys.executable,str(root/'runtime_worker.py')],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            result['worker_pid']=child.pid
            while child.poll() is None:
                guard();time.sleep(1)
            result['returncode']=child.returncode
            if child.returncode:raise RuntimeError('Original runtime leaf failed; no replay')
        evidence=json.loads((root/'results/evidence.json').read_text())
        if not evidence['passed']:raise RuntimeError('Missing successful runtime receipt')
        result['passed']=True
    except BaseException as exc:
        result['error']=repr(exc);raise
    finally:
        if child is not None:
            # Covers descendants even if the original worker exited first.
            try:os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGKILL);child.wait()
            try:os.killpg(child.pid,0)
            except ProcessLookupError:result['owned_group_empty']=True
            else:
                os.killpg(child.pid,signal.SIGKILL)
                result['owned_group_empty']=False
                result['passed']=False
        result['seconds']=time.monotonic()-began
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
