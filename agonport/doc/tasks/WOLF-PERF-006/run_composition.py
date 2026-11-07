"""Guard one serial actual-listener host compilation and finite build checks."""
from pathlib import Path
import argparse,hashlib,json,os,signal,subprocess,sys,time
T=Path(__file__).resolve().parent; B=T/'build/composition01';D=Path('/Agon/mystuff/agon-dev-env')

def main(lease):
    B.mkdir(exist_ok=False)
    receipt=dict(passed=False,guards=[],steps=[]);start=time.monotonic();child=None
    def stop(signum,_):
        receipt['host_signal']=dict(number=signum,epoch=time.time());raise KeyboardInterrupt(signum)
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,stop)
    def guard():
        temp=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
        available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))
        receipt['guards'].append(dict(epoch=time.time(),cpu_c=temp,available_kib=available))
        assert temp<80 and available>=524288 and time.monotonic()-start<180
    try:
        subprocess.run([str(D/'.venv/bin/python'),str(D/'cross-agent/pi5-workloads/pi5_lease.py'),'assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL)
        guard()
        source=Path('/Agon/mystuff/agon-extender/agents/remote009/download-r01/source')
        files=[T/n for n in ('hardware.py','bootstrap.py','test_replacement.py','run_composition.py','test_hardware.py','guest_binding.py','test_guest_binding.py')]
        files += [source/'projects/sdserve/src'/n for n in ('service.c','service.h','sd_wire.h')]
        files += [source/'tests/test_sdserve.py',source/'tests/sdserve_host/fs.c',source/'tests/sdserve_host/agon/mos.h']
        files += [T/'build/r01'/a/'module/wolf_perf.vdpl' for a in ('original','candidate')]
        files += [T/'build/guests01'/n for n in ('bindings.json','binding-result.json','compile-receipt.json')]
        receipt['inputs']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        for name in ('test_hardware.py','test_replacement.py','test_guest_binding.py'):
            subprocess.run([str(D/'.venv/bin/python'),str(D/'cross-agent/pi5-workloads/pi5_lease.py'),'assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL)
            guard();begin=time.monotonic()
            with (B/(name+'.log')).open('x') as log:
                child=subprocess.Popen([sys.executable,str(T/name)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                while child.poll() is None:guard();time.sleep(.25)
            receipt['steps'].append(dict(name=name,returncode=child.returncode,seconds=time.monotonic()-begin));assert child.returncode==0,name
            child=None
        receipt['passed']=True
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        receipt['seconds']=time.monotonic()-start
        (B/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ('passed','steps','seconds')}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--lease',required=True);main(p.parse_args().lease)
