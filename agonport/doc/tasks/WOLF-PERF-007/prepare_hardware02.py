"""File-only exact matched hardware kit; retained source context is not a grant."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,shutil
T=Path(__file__).resolve().parent;P6=T.parent/'WOLF-PERF-006';B=T/'build/hardware02'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):
    with p.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def main(preparation):
    current=json.loads(preparation.read_text());assert current['request']=='a9367f3c73e6'
    old=json.loads((P6/'build/hardware02/kit.json').read_text());components=current['retained_components']
    # The actual new grant must independently match this tuple before any I/O.
    assert components==old['incoming_components'],'Changed component requires explicit fresh source/rollback qualification'
    for name,record in current['files'].items():assert sha(name)==record['sha256'],name
    for name,digest in json.loads((T/'COMPOSITION-FREEZE.json').read_text()).items():assert sha(name)==digest,name
    native=current['native_write'];assert native['offset']==65536 and native['span']==1105920
    assert sha(native['restore'])==native['restore_sha256']=='85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'
    assert sha(native['install'])==native['install_sha256']=='493fd0a010bedcfc5916314353f93565f7b159ac163d9bc61e7c5078140669e8'
    assert native['native_app_sha256']==old['native_b_sha256']
    boot=current['boot'];assert boot['BUILD']=='net-003-r02-b2026-11-06-09-03-07Z'
    spec=importlib.util.spec_from_file_location('binding',T/'guest_binding.py');binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding)
    guests=json.loads((T/'build/guests01/bindings.json').read_text());binding.qualify(guests)
    composition=T/'build/composition02/receipt.json';q=json.loads(composition.read_text());assert q['passed'] and q['inputs'][str(T/'hardware02.py')]==sha(T/'hardware02.py')
    B.mkdir(exist_ok=False);shutil.copyfile(native['restore'],B/'restore.bin');shutil.copyfile(native['install'],B/'install-b.bin')
    remote='/test/wolf/perf007/r02'
    (B/'state.txt').write_bytes(('SAVE '+remote+'/post-mode.bin &BC349 &1\r\nSAVE '+remote+'/post-callback.bin &BC38E &3\r\nEMOS sdserve --fast /\r\n').encode())
    (B/'route.txt').write_bytes(('SAVE '+remote+'/route.bin &BCB25 &1\r\nEMOS sdserve --fast /\r\n').encode())
    stage={n:p for n,p in old['stage'].items() if not n.startswith('b-') and n not in ('wolf3d.vdpl','state.txt','route.txt')}
    for name,path in stage.items():assert sha(path)==old['inputs'][path],name
    modules={a:str(T/'build/r01'/a/'module/wolf_perf.vdpl') for a in guests}
    for modes in guests.values():
        for g in modes.values():stage[g['remote_name']]=g['guest']
    stage.update({'wolf3d.vdpl':modules['original'],'state.txt':str(B/'state.txt'),'route.txt':str(B/'route.txt')})
    listings={'vdplet-'+mode:guests['original'][mode]['listing'] for mode in ('control','unpaced')}
    oldbinding=json.loads(Path(old['source_binding']).read_text());assert current['current_ROM_binding']['rom_sha256']==oldbinding['rom_sha256'] and current['current_ROM_binding']['map_sha256']==oldbinding['map_sha256']
    assert current['current_ROM_binding']['symbols']==oldbinding['symbols']
    # Retained binding facts are valid only with exact unchanged source/client.
    sources={n:d for n,d in old['inputs'].items() if n.startswith(('/Agon/mystuff/agon-extender/','/Agon/mystuff/agon-dev-env/')) and '/bench-scheduler/' not in n}
    for name,digest in sources.items():assert sha(name)==digest,name
    oldbinding['provenance']='Current owner retained ROM/map/source and matched tuple rehashed; original69 source semantics unchanged. Actual new grant and fresh raw mode/callback/route/CLI/file checks are required; no fresh firmware read claimed.'
    oldbinding['transfer_lifecycle']['host_composition_receipt_sha256']=sha(composition)
    save(B/'source-binding.json',oldbinding)
    files=list(stage.values())+list(listings.values())+list(modules.values())+list(current['files'])+list(sources)
    files += [str(p) for p in T.glob('*.py')]+[str(p) for p in T.glob('*.md')]+[str(T/n) for n in ('SOURCE-PINS.json','COMPOSITION-FREEZE.json','BUILD-RESULT.json','VISUAL-RESULT.json')]
    files += [str(p) for p in (T/'build/guests01').rglob('*') if p.is_file()]
    files += [str(p) for p in (T/'build/r01').rglob('*') if p.is_file() and (p.suffix in ('.vdpl','.elf','.map','.su','.json','.txt','.cpp','.h','.inc','.log') or '/sdk/' in str(p)) and '__pycache__' not in p.parts]
    files += [str(p) for p in B.iterdir() if p.is_file()]
    files += [str(preparation),str(composition),str(P6/'build/hardware02/kit.json')]
    files += [n for n,d in old['inputs'].items() if '/WOLF-PERF-003/hardware/' in n or n.endswith(('/WOLF-PERF-001/hardware/physical.py','/WOLF-PERF-003/analyze.py'))]
    for modes in guests.values():
        for g in modes.values():
            for p in Path(g['source']).iterdir():
                if p.suffix not in ('.asm','.inc'):continue
                if p.name=='loading_trace04.inc':
                    addresses=set(int(x,16) for x in re.findall(r'\(0([0-9a-f]+)h\)',p.read_text(),re.I));assert addresses<=set(int(x,16) for x in oldbinding['symbols'].values())
    preflight=T/'LAUNCH-PREFLIGHT.json';files.append(str(preflight));environment=json.loads(preflight.read_text());assert environment['passed'] and not environment['target_access'];files+=list(environment['files'])
    for n,d in environment['files'].items():assert sha(n)==d,n
    inputs={str(Path(n).resolve()):sha(n) for n in files}
    kit=dict(task='WOLF-PERF-007-hardware-r02',request=current['request'],remote=remote,incoming_components=components,
             preparation=str(preparation),original_module_sha256=sha(modules['original']),candidate_module_sha256=sha(modules['candidate']),native_b_sha256=old['native_b_sha256'],modules=modules,stage=stage,listings=listings,guests=guests,
             retain_lease_after_test=False,restore=str(B/'restore.bin'),install_b=str(B/'install-b.bin'),flash_span=1105920,source_binding=str(B/'source-binding.json'),source_binding_passed=True,boot_binding_passed=True,p4_boot_build=boot['BUILD'],inputs=inputs,
             restrictions='Fresh new grant/current matching tuple/owned entry observation; ONE finite sixguest/sevenprobe comparison then exact restore/readback/fullcleanup/normalrelease; no oldtoken/HOLD/carrier/provider/firmware/default substitution.')
    save(B/'kit.json',kit)
    for n,d in inputs.items():assert sha(n)==d,n
    print(json.dumps(dict(files=len(inputs),stage_files=len(stage),kit_sha256=sha(B/'kit.json'),restoration=sha(B/'restore.bin'),install=sha(B/'install-b.bin'))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--preparation',type=Path,required=True);main(p.parse_args().preparation.resolve())
