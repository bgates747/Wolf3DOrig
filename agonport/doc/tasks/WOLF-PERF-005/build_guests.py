"""Four serial assemblies and actual producer checks under owned Pi custody."""
from pathlib import Path
import argparse,hashlib,json,os,signal,subprocess,sys,time
T=Path(__file__).resolve().parent;B=T/'build/guests02';D=Path('/Agon/mystuff/agon-dev-env')
ASM=T.parents[3]/'src/asm/wolf3d/tgt/.tools/ez80asm'

def main(lease):
    receipt=dict(passed=False,guards=[],steps=[]);start=time.monotonic();child=None
    def stop(signum,_):receipt['host_signal']=dict(number=signum,epoch=time.time());raise KeyboardInterrupt(signum)
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,stop)
    def guard():
        temp=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
        available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))
        receipt['guards'].append(dict(epoch=time.time(),cpu_c=temp,available_kib=available))
        assert temp<80 and available>=524288 and time.monotonic()-start<600
    def run(args,cwd,label):
        nonlocal child
        subprocess.run([str(D/'.venv/bin/python'),str(D/'cross-agent/pi5-workloads/pi5_lease.py'),'assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL)
        guard();begin=time.monotonic()
        with (B/(label+'.log')).open('x') as log:
            child=subprocess.Popen(args,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            while child.poll() is None:guard();assert time.monotonic()-begin<120;time.sleep(.1)
        receipt['steps'].append(dict(name=label,returncode=child.returncode,seconds=time.monotonic()-begin));assert child.returncode==0,label
        child=None
    try:
        for name,digest in json.loads((B/'source-freeze.json').read_text()).items():assert hashlib.sha256((B/name).read_bytes()).hexdigest()==digest,name
        receipt['assembler_sha256']=hashlib.sha256(ASM.read_bytes()).hexdigest()
        for arm in ('original','candidate'):
            for mode in ('control','unpaced'):
                run([str(ASM),'wolf3d.asm','wolf3d.bin','-l','-c'],B/arm/mode/'source','asm-'+arm+'-'+mode)
        run([sys.executable,str(T/'guest_binding.py')],T,'producer-binding')
        receipt['passed']=True
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        receipt['seconds']=time.monotonic()-start;(B/'compile-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ('passed','steps','seconds')}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--lease',required=True);main(p.parse_args().lease)
