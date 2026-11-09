"""Finite serial compiler/check tranche; never starts emulators or devices."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

T=Path(__file__).resolve().parent
ROOT=T.parents[3]
ENV=ROOT.parent/'agon-dev-env'
LEASE=[str(ENV/'.venv/bin/python'),str(ENV/'cross-agent/pi5-workloads/pi5_lease.py')]


def guard():
    sensors=list(Path('/sys/class/thermal').glob('thermal_zone*/temp'))
    if not sensors:
        raise RuntimeError('No thermal sensor')
    temperature=max(float(p.read_text())/1000 for p in sensors)
    available=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))
    if temperature>=80 or available<524288:
        raise RuntimeError(f'Host guard: {temperature}C/{available}KiB')
    return temperature


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--lease',required=True);parser.add_argument('--revision',default='r01')
    parser.add_argument('--checks-only',action='store_true',help='Keep completed real assemblies; correct only finite-client leaf and remaining checks')
    args=parser.parse_args();out=T/'build'/args.revision
    assert not out.exists(),'Use a fresh evidence revision'
    out.mkdir(parents=True)
    receipt=dict(passed=False,steps=[],no_emulator=True,no_device=True,peak_c=0)
    started=time.monotonic()
    def run(name,command):
        subprocess.run(LEASE+['assert-owner','--owner','wolf3dorig','--lease',args.lease],check=True,stdout=subprocess.DEVNULL,timeout=20)
        if time.monotonic()-started>720:raise RuntimeError('No new child inside final cleanup reserve')
        step=dict(name=name,command=list(map(str,command)));before=time.monotonic();p=None
        try:
            with (out/(name+'.log')).open('w') as log:
                p=subprocess.Popen(step['command'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                while p.poll() is None:
                    receipt['peak_c']=max(receipt['peak_c'],guard())
                    if time.monotonic()-before>180 or time.monotonic()-started>900:
                        raise RuntimeError('Compiler/check time bound')
                    time.sleep(.2)
                step['exit_code']=p.returncode
                if p.returncode:raise RuntimeError(name+' failed; preserve original log')
        finally:
            if p is not None and p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
            step['elapsed_s']=time.monotonic()-before;receipt['steps'].append(step)
            (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(name+' passed',flush=True)
    python=str(ROOT/'.venv/bin/python');builder=ROOT/'src/asm/wolf3d/scripts/build.py'
    try:
        if not args.checks_only:
            run('normal-client',[python,builder])
            run('profile-native-client',[python,builder,'--profile','--profile-native','--module',ROOT/'agonport/doc/tasks/WOLF-PERF-021/results/build01/candidate/module/wolf_perf.vdpl'])
            run('standalone-assembly-control',[python,builder,'--backend','standalone','--output-dir',ROOT/'src/asm/wolf3d/tgt/fw002-control'])
        run('finite-client',[python,ROOT/'src/asm/wolf3d_vdplet_client/scripts/build.py'])
        run('finite-client-contract',[python,ROOT/'src/asm/wolf3d_vdplet_client/scripts/test_client_contract.py','-v'])
        run('preparation-and-profile-checks',[python,'-m','pytest','-q','tests/test_firmware_preparation.py','tests/test_profile.py'])
        # Disabled profiling still assembles the exact historical standalone bytes.
        old=ROOT/'src/asm/wolf3d/tgt/wolf3d.bin'
        new=ROOT/'src/asm/wolf3d/tgt/fw002-control/wolf3d.bin'
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        assert old.read_bytes()==new.read_bytes(),'Disabled-profile standalone output changed'
        receipt['standalone_control_sha256']=sha(new)
        receipt['passed']=True
    except BaseException as exc:
        receipt['error']=repr(exc);raise
    finally:
        receipt['elapsed_s']=time.monotonic()-started
        (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
        release=subprocess.run(LEASE+['release','--owner','wolf3dorig','--lease',args.lease,'--work-stopped','--cleanup-complete'],capture_output=True,text=True,timeout=30)
        (out/'release.txt').write_text(release.stdout+release.stderr)
        print('Owned compiler children joined; release status '+str(release.returncode),flush=True)


if __name__=='__main__':main()
