"""Finite source-bound host-only projection classification; normal build custody."""
from pathlib import Path
import argparse,hashlib,json,os,re,signal,struct,subprocess,time
T=Path(__file__).resolve().parent;B=T/'build/projection01';D=Path('/Agon/mystuff/agon-dev-env')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(lease):
    B.mkdir(exist_ok=False);r=dict(passed=False,steps=[],guards=[]);start=time.monotonic();child=None
    def stop(sig,_):r['signal']=sig;raise KeyboardInterrupt(sig)
    for sig in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT):signal.signal(sig,stop)
    def guard():
        temp=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
        mem=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))
        r['guards'].append(dict(cpu_c=temp,available_kib=mem));assert temp<80 and mem>=524288 and time.monotonic()-start<180
    def run(name,args):
        nonlocal child
        subprocess.run([str(D/'.venv/bin/python'),str(D/'cross-agent/pi5-workloads/pi5_lease.py'),'assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL);guard();begin=time.monotonic()
        with (B/(name+'.log')).open('x')as log:
            child=subprocess.Popen([str(x)for x in args],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            while child.poll()is None:guard();time.sleep(.1)
        r['steps'].append(dict(name=name,returncode=child.returncode,seconds=time.monotonic()-begin));assert child.returncode==0,name;child=None
    try:
        old=json.loads((T/'build/r01/inputs.json').read_text())['inputs'];index=json.loads((T/'build/r01/frozen-inputs/index.json').read_text())
        files=[]
        for name,digest in old.items():
            saved=Path(index[name]['snapshot']);assert sha(saved)==digest;files.append(saved)
            if Path(name).name!='PLAN.md':assert sha(name)==digest,name
        h02=T.parent/'WOLF-GOAL-001';kit=json.loads((h02/'build/hardware02/kit.json').read_text())
        level=Path(kit['stage']['level_00/state_easy.w3l']);assert sha(level)==kit['inputs'][str(level)]
        bindings=json.loads((T/'build/guests01/bindings.json').read_text())
        source=Path(bindings['original']['room']['source']);angle=source/'angles.inc'
        values=[int(x)for x in re.findall(r'^\s*dw (\d+)\s*$',angle.read_text(),re.M)]
        assert len(values)==600 and values==[(720*n//600)%360 for n in range(1,601)]
        (B/'angles.bin').write_bytes(struct.pack('<600H',*values))
        # Join parsed static format and rich points to the actual producers.
        rich=(Path(bindings['original']['sprites']['source'])/'bench.inc').read_text()
        for x,y in ((33,36),(35,36),(34,35),(34,37),(33,35),(35,35),(33,37),(35,37)):
            assert f'    db {x},{y},14,0,0,0\n'in rich
        assert 'ld bc,8*W3D_STATIC_SIZE\n'in rich
        body=json.loads((T/'build/r01/native-body-binding.json').read_text())
        for arm in ('original','candidate'):
            p=Path(body['units'][arm]['source']);assert sha(p)==body['units'][arm]['source_sha256'];files.append(p)
        files += [T/n for n in ('projection_coverage.cpp','run_projection_coverage.py','PROJECTION-COVERAGE-PLAN.md','original_numeric.inc','candidate_numeric.inc')]
        files += [level,angle,Path(bindings['original']['sprites']['source'])/'bench.inc',source/'wolf3d_level_loader.inc',source/'wolf3d_motion.inc',source/'wolf3d_world.inc',T/'build/r01/native-body-binding.json']
        files += list((T/'build/r01/original/production').glob('*.cpp'))+list((T/'build/r01/original/production').glob('*.h'))+[T/'build/r01/original/wolf3d_tables.inc']
        r['inputs']={str(p):sha(p)for p in files}
        # Actual final ELF dataflow: transform_point's long call literal resolves
        # to the retained signed helper in each arm, with the admitted relative fixup.
        joins={}
        for arm in ('original','candidate'):
            root=T/'build/r01'/arm/'module';elf=root/'wolf_perf.elf';blob=elf.read_bytes()
            header=struct.unpack_from('<16sHHIIIIIHHHHHH',blob)
            sections=[struct.unpack_from('<10I',blob,header[6]+i*header[11])for i in range(header[12])]
            matches=[q for q in sections if q[2]&2 and q[1]!=8 and q[3]<=0xea4 and 0xea8<=q[3]+q[5]]
            assert len(matches)==1;q=matches[0];value=struct.unpack_from('<I',blob,q[4]+0xea4-q[3])[0]
            symbols=T/'build/r01'/(arm+'-symbols.log');m=re.search(r'^([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+\w\s+__divdi3$',symbols.read_text(),re.M);assert m and value==int(m[1],16)
            dis=T/'build/r01'/(arm+'-disassembly.log');text=dis.read_text().split('::transform_point(',1)[1].split('\n\n',1)[0]
            assert re.search(r'f2d:.*l32r\s+a3, ea4',text)and re.search(r'f35:.*callx8\s+a3',text)
            reloc=root/'wolf_perf.readelf.txt';assert re.search(r'^00000ea4\s+00000005\s+R_XTENSA_RELATIVE\s+0$',reloc.read_text(),re.M)
            joins[arm]=dict(call=0xf35,literal=0xea4,signed_helper=value,relocation='R_XTENSA_RELATIVE',limits='Final target source/dataflow proof, not sampled native call counts.')
            for item in (elf,symbols,dis,reloc):r['inputs'][str(item)]=sha(item)
        r['actual_target_projection_call_join']=joins
        run('compile',['g++','-std=c++17','-O2','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',T/'projection_coverage.cpp','-o',B/'projection'])
        run('coverage',[B/'projection',level,B/'angles.bin'])
        r['scenes']=[json.loads(x)for x in (B/'coverage.log').read_text().splitlines()]
        assert len(r['scenes'])==2
        r['passed']=True;r['limits']='Host-only actual-source/input classification; not native hit instrumentation, hardware timing, full-domain Xtensa execution, or physical matrix selection.'
    finally:
        if child is not None and child.poll()is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        r['seconds']=time.monotonic()-start;(B/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k]for k in ('passed','scenes','seconds')}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--lease',required=True);main(p.parse_args().lease)
