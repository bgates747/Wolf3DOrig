"""Serial actual eZ80 assembly and independent linked producer/present checks."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re,signal,subprocess,time
T=Path(__file__).resolve().parent;B=T/'build/guests01';D=Path('/Agon/mystuff/agon-dev-env')
ASM=T.parents[3]/'src/asm/wolf3d/tgt/.tools/ez80asm'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(lease):
    start=time.monotonic();receipt=dict(passed=False,guards=[],steps=[],arms={});child=None
    def stop(sig,_):receipt['host_signal']=sig;raise KeyboardInterrupt(sig)
    for sig in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT):signal.signal(sig,stop)
    def guard():
        cpu=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
        mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))
        receipt['guards'].append(dict(cpu_c=cpu,available_kib=mem));assert cpu<80 and mem>=524288 and time.monotonic()-start<240
    try:
        for name,digest in json.loads((B/'inputs.json').read_text()).items():assert sha(name)==digest,name
        spec=importlib.util.spec_from_file_location('binding',T/'guest_binding.py');binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding)
        bindings=json.loads((B/'bindings.json').read_text())
        for arm in ('original','candidate'):
            receipt['arms'][arm]={}
            for scene in ('room','sprites'):
                g=bindings[arm][scene];source=Path(g['source']);guard()
                subprocess.run([str(D/'.venv/bin/python'),str(D/'cross-agent/pi5-workloads/pi5_lease.py'),'assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL)
                begin=time.monotonic()
                with (B/(arm+'-'+scene+'.log')).open('x') as log:
                    child=subprocess.Popen([str(ASM),'wolf3d.asm','wolf3d.bin','-l','-c'],cwd=source,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    while child.poll() is None:guard();assert time.monotonic()-begin<120;time.sleep(.1)
                receipt['steps'].append(dict(arm=arm,scene=scene,returncode=child.returncode,seconds=time.monotonic()-begin));assert child.returncode==0
                result=binding.verify(g);binary=Path(g['guest']).read_bytes();listing=Path(g['listing']).read_text();bench=(source/'bench.inc').read_text()
                loop=bench.split('wp_next:',1)[1].split('call wp_prt_stop',1)[0]
                assert loop.count('call w3d_vdu_present')==1 and '@pace:' not in loop
                assert loop.startswith('\n    ld hl,(wp_n)\n    inc hl\n')
                assert re.search(r'call w3d_vdu_present\s*;[^\n]*\n\s*call w3d_audio_wait_for_vdp_ingress\s*\n\s*jp c,wp_failed',loop)
                symbols={}
                for n in ('wp_next','wp_prt_stop','w3d_vdu_present','w3d_audio_wait_for_vdp_ingress'):
                    m=re.search(r'^([0-9A-F]{6})[^\n]*\b'+n+r':',listing,re.M);assert m;symbols[n]=int(m[1],16)
                calls=[]
                for m in re.finditer(r'^([0-9A-F]{6}) ((?:[0-9A-F]{2} ){3}[0-9A-F]{2})\s+\d+\*?\s+call (w3d_vdu_present|w3d_audio_wait_for_vdp_ingress)\b',listing,re.M):
                    at=int(m[1],16)
                    if symbols['wp_next']<=at<symbols['wp_next']+700:
                        assert binary[at-0x40000:at-0x40000+4]==bytes.fromhex(m[2])==bytes([0xcd])+symbols[m[3]].to_bytes(3,'little')
                        calls.append(dict(address=at,target=m[3]))
                assert {x['target'] for x in calls}=={'w3d_vdu_present','w3d_audio_wait_for_vdp_ingress'}
                result['presentation_calls']=calls;receipt['arms'][arm][scene]=result
        assert sha(bindings['original']['room']['guest'])=='c43e7fe74148517c30cf9bf83854cf0cf297aeaf8c4684a4624c93849b46df58','Exact original room guest reproduction'
        for scene in ('room','sprites'):
            a=receipt['arms']['original'][scene];b=receipt['arms']['candidate'][scene]
            assert a['stack_labels']==b['stack_labels']
            original=Path(bindings['original'][scene]['guest']).read_bytes();candidate=Path(bindings['candidate'][scene]['guest']).read_bytes();assert len(original)==len(candidate)
            allowed=set()
            for x,y in zip(a['operands'],b['operands']):
                assert x['address']==y['address'] and x['symbol']==y['symbol']
                allowed.update(x['address']-0x40000+i for i,(u,v) in enumerate(zip(bytes.fromhex(x['encoded']),bytes.fromhex(y['encoded']))) if u!=v)
            changed={i for i,(x,y) in enumerate(zip(original,candidate)) if x!=y};assert changed==allowed,(scene,changed,allowed)
            receipt['arms']['candidate'][scene]['changed_offsets']=sorted(changed)
        receipt['passed']=True
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        receipt['seconds']=time.monotonic()-start
        (B/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('PASS four actual uncapped presented guest/length/stack/arm-only-operand checks')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--lease',required=True);main(p.parse_args().lease)
