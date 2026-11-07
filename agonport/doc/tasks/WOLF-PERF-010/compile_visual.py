"""One actual static Fab visual derivative assembly; normal Pi build custody."""
from pathlib import Path
import argparse,json,hashlib,os,signal,subprocess,time
T=Path(__file__).resolve().parent;B=T/'build/visual02';D=Path('/Agon/mystuff/agon-dev-env');ASM=T.parents[3]/'src/asm/wolf3d/tgt/.tools/ez80asm'
def main(lease):
    for n,d in json.loads((B/'inputs.json').read_text()).items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==d,n
    subprocess.run([str(D/'.venv/bin/python'),str(D/'cross-agent/pi5-workloads/pi5_lease.py'),'assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL)
    guards=[];start=time.monotonic();child=None;result={'passed':False}
    def stop(sig,_):raise KeyboardInterrupt(sig)
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,stop)
    try:
        with (B/'assembly.log').open('x') as log:
            child=subprocess.Popen([str(ASM),'wolf3d.asm','wolf3d.bin','-l','-c'],cwd=B/'source',stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            while child.poll() is None:
                temp=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000;mem=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))
                guards.append({'cpu_c':temp,'available_kib':mem});assert temp<80 and mem>=524288 and time.monotonic()-start<120;time.sleep(.1)
        assert child.returncode==0
        import shutil
        shutil.copyfile(B/'source/wolf3d.bin',B/'payload/wolf3d.bin')
        sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
        result.update(passed=True,guest_sha256=sha(B/'source/wolf3d.bin'))
        files=[p for p in B.rglob('*') if p.is_file() and p.name not in ('inputs.json','assembly.json')]
        (B/'dispatch.json').write_text(json.dumps({str(p.relative_to(B)):sha(p)for p in files},indent=2)+'\n')
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        result.update(seconds=time.monotonic()-start,guards=guards);(B/'assembly.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS actual static visual derivative assembly')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--lease',required=True);main(p.parse_args().lease)
