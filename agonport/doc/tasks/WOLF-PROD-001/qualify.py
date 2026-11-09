"""Finite serial qualification wrapper: no emulator or device execution."""
from pathlib import Path
import argparse, json, os, signal, subprocess, sys, time
T=Path(__file__).resolve().parent; ROOT=T.parents[3]; ENV=ROOT.parent/'agon-dev-env'
LEASE=[str(ENV/'.venv/bin/python'),str(ENV/'cross-agent/pi5-workloads/pi5_lease.py')]

def main():
    p=argparse.ArgumentParser();p.add_argument('--lease',required=True);p.add_argument('--revision',required=True)
    p.add_argument('--stage',choices=('module','clients'),required=True);a=p.parse_args()
    out=T/'build'/a.revision;out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();result=dict(passed=False,steps=[],peak_c=0,min_available_kib=None);child=None
    def interrupted(number,_):raise KeyboardInterrupt(number)
    for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):signal.signal(sig,interrupted)
    def guard():
        sensors=list(Path('/sys/class/thermal').glob('thermal_zone*/temp'))
        if not sensors:raise RuntimeError('Missing thermal sensor')
        c=max(float(s.read_text())/1000 for s in sensors)
        kib=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))
        result['peak_c']=max(c,result['peak_c']);result['min_available_kib']=min(kib,result['min_available_kib'] or kib)
        if c>=80 or kib<524288 or time.monotonic()-started>1800:raise RuntimeError(f'Host/time guard {c}/{kib}')
    def run(name,argv,bound=180):
        nonlocal child
        if time.monotonic()-started>1740:raise RuntimeError('No new work in cleanup reserve')
        subprocess.run(LEASE+['assert-owner','--owner','wolf3dorig','--lease',a.lease],check=True,timeout=20,stdout=subprocess.DEVNULL)
        guard();begin=time.monotonic();step=dict(name=name,argv=list(map(str,argv)))
        with (out/(name+'.log')).open('x') as log:
            child=subprocess.Popen(step['argv'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                while child.poll() is None:
                    guard()
                    if time.monotonic()-begin>bound:raise RuntimeError('Child bound: '+name)
                    time.sleep(.2)
                step.update(returncode=child.returncode,seconds=time.monotonic()-begin);result['steps'].append(step)
                if child.returncode:raise RuntimeError(name+' failed; retain original log')
            finally:
                if child.poll() is None:
                    os.killpg(child.pid,signal.SIGTERM)
                    try:child.wait(timeout=5)
                    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                child=None
    try:
        py=ROOT/'.venv/bin/python';builder=ROOT/'src/asm/wolf3d/scripts/build.py'
        if a.stage=='module':
            run('production-module',[py,ROOT/'agonport/vdplet/production/build.py','--discover-package'],900)
        else:
            run('normal-client',[py,builder])
            run('profile-client',[py,builder,'--profile'])
            run('native-profile-control',[py,builder,'--profile','--profile-native','--module',ROOT/'agonport/doc/tasks/WOLF-PERF-021/results/build01/candidate/module/wolf_perf.vdpl'])
            run('preparation-and-profile',[py,'-m','pytest','-q','tests/test_firmware_preparation.py','tests/test_profile.py'])
            run('complete-payload',[py,ROOT/'tools/wolf_prepare.py','package','--receipt',ROOT/'src/asm/wolf3d/tgt/pinned/wolf3d-vdplet-direct.json'])
            run('verify-default-payload',[py,ROOT/'tools/wolf_prepare.py','verify-payload'])
        result['passed']=True
    except BaseException as exc:
        result['error']=repr(exc);raise
    finally:
        result['seconds']=time.monotonic()-started
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        release=subprocess.run(LEASE+['release','--owner','wolf3dorig','--lease',a.lease,'--work-stopped','--cleanup-complete'],capture_output=True,text=True,timeout=30)
        (out/'release.txt').write_text(release.stdout+release.stderr)
        print('Owned children joined; compiler release status',release.returncode,flush=True)
if __name__=='__main__':main()
