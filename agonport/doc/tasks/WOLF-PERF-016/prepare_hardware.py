"""File-only freeze from actual79 retained handback; a fresh grant is separate."""
from pathlib import Path
import hashlib,importlib.util,json,re,shutil,sys
T=Path(__file__).resolve().parent;B=T/'build/hardware01'
ROOT=T.parents[3];E=Path('/Agon/mystuff/agon-extender');D=Path('/Agon/mystuff/agon-dev-env')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert Path(sys.executable)==E/'.venv/bin/python'
    assert not B.exists(),'New revision required after a frozen selection'
    old=json.loads((T.parent/'WOLF-PERF-011/build/hardware02/kit.json').read_text())
    release=Path('/Agon/mystuff/agon-extender/agents/net004/uart1-rx-r01/physical-r01/released.json');actual=json.loads(release.read_text())
    components=actual['release_observation']['components'];assert components==old['incoming_components']
    assert actual['generation']==79 and actual['released']
    assert json.loads((T/'build/r01/build-receipt.json').read_text())['passed']
    assert json.loads((T/'build/guests01/receipt.json').read_text())['passed']
    assert json.loads((T/'build/composition01/receipt.json').read_text())['passed']
    spec=importlib.util.spec_from_file_location('actual_hw',T/'hardware02.py');hw=importlib.util.module_from_spec(spec);spec.loader.exec_module(hw)
    import guest_binding
    guests=json.loads((T/'build/guests01/bindings.json').read_text())
    for modes in guests.values():
        for g in modes.values():guest_binding.verify(g)
    B.mkdir()
    for n,source in (('restore.bin',old['restore']),('install-b.bin',old['install_b'])):shutil.copyfile(source,B/n)
    assert sha(B/'restore.bin')=='85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'
    assert sha(B/'install-b.bin')=='493fd0a010bedcfc5916314353f93565f7b159ac163d9bc61e7c5078140669e8'
    remote='/test/wolf/perf016/r01'
    (B/'state.txt').write_bytes(('SAVE '+remote+'/post-mode.bin &BC349 &1\r\nSAVE '+remote+'/post-callback.bin &BC38E &3\r\nEMOS sdserve --fast /\r\n').encode())
    (B/'route.txt').write_bytes(('SAVE '+remote+'/route.bin &BCB25 &1\r\nEMOS sdserve --fast /\r\n').encode())
    source_binding=json.loads(Path(old['source_binding']).read_text())
    assert source_binding['passed'] and source_binding['rom_sha256']==components['emos_rom_sha256']
    source_binding['provenance']='Actual79 full clean release/current tuple retained, no new target observation claimed. Exact component equality required in the actual future grant; current source references rehashed in this new kit.'
    (B/'source-binding.json').write_text(json.dumps(source_binding,indent=2)+'\n')
    stage={n:p for n,p in old['stage'].items() if n not in ('rotate.bin','wolf3d.vdpl','state.txt','route.txt')}
    # Existing INFO-only resource query, not a static draw/timer fixture.
    probe=json.loads((T.parent/'WOLF-PERF-009/build/hardware01/kit.json').read_text())['stage']['resource-probe.bin']
    stage['resource-probe.bin']=probe
    for modes in guests.values():
        for g in modes.values():stage[g['remote_name']]=g['guest']
    modules={a:guests[a]['room']['module']for a in guests}
    stage.update({'wolf3d.vdpl':modules['original'],'state.txt':str(B/'state.txt'),'route.txt':str(B/'route.txt')})
    listings={'vdplet-'+m:guests['original'][m]['listing']for m in ('room',)}
    files=list(stage.values())+list(listings.values())+list(modules.values())+[str(release),str(Path(old['source_binding']))]
    for root in ('build/guests01','build/r01','build/composition01','results/build01'):
        files += [str(p)for p in (T/root).rglob('*')if p.is_file() and '__pycache__'not in p.parts and p.suffix not in ('','.bin')]
    files += [str(p)for p in T.iterdir()if p.is_file()]
    files += [str(p)for p in B.iterdir()if p.is_file()]
    # Preserve actual passive import closure of this controller, not all obsolete
    # task inputs or stale publication documents from historical kits.
    for module in tuple(sys.modules.values()):
        n=getattr(module,'__file__',None)
        if n and n.endswith(('.py','.so')) and n.startswith(('/Agon/mystuff/','/usr/')):files.append(n)
    files += [str(p)for p in (E/'agents/net004/uart1-bootstrap-r01/bootstrap.py',)]
    inputs={str(Path(p).resolve()):sha(p)for p in files}
    kit=dict(task='WOLF-PERF-016-hardware01',request='456459d1283d',remote=remote,incoming_components=components,
        original_module_sha256=sha(modules['original']),candidate_module_sha256=sha(modules['candidate']),native_b_sha256=old['native_b_sha256'],
        modules=modules,stage=stage,listings=listings,guests=guests,retain_lease_after_test=False,
        restore=str(B/'restore.bin'),install_b=str(B/'install-b.bin'),flash_span=1105920,source_binding=str(B/'source-binding.json'),source_binding_passed=True,boot_binding_passed=True,
        p4_boot_build='net-003-r02-b2026-11-06-09-03-07Z',inputs=inputs,
        restrictions='Actual fresh grant/current expected79 tuple after actual Mech successor handback/stoppedhandoff. ONE finite4guest5probe uncapped room ABBA comparison; firstunexpectedstop, RAMbeforeLOAD, exact fullspan restoration/readback/fullcleanup/normalrelease. Mech first/Wolf second. No Oryx, newcarrier/provider/firmware/defaultaxis.')
    hw.verify_kit(kit)
    (B/'kit.json').write_text(json.dumps(kit,indent=2)+'\n')
    print(json.dumps(dict(files=len(inputs),stage_files=len(stage),kit_sha256=sha(B/'kit.json'),request=kit['request'])))
if __name__=='__main__':main()
