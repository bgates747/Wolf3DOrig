"""File-only new three-arm selection from actual82 restored tuple, no device I/O."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,sys
T=Path(__file__).resolve().parent;B=T/'build/hardware02'
E=Path('/Agon/mystuff/agon-extender')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    assert Path(sys.executable)==E/'.venv/bin/python'
    assert not B.exists(),'New revision required after a frozen selection'
    sys.path.insert(0,str(T))
    import hardware02 as hw
    from qualify_h02_guests import qualify
    qualified=qualify()
    composition=T/'build/composition-h02-r02/receipt.json'
    comp=json.loads(composition.read_text());assert comp['passed']
    for name,digest in comp['inputs'].items(): assert sha(name)==digest,name
    old=json.loads((T.parent/'WOLF-PERF-016/build/hardware01/kit.json').read_text())
    release=E/'agents/bench-scheduler/mechagon-goal001-r02/released.json'
    actual=json.loads(release.read_text());assert actual['generation']==82 and actual['released']
    components=actual['release_observation']['components'];assert components==old['incoming_components']
    guests=json.loads((T/'H02-GUESTS.json').read_text())
    modules={a:guests[a]['room']['module']for a in hw.ARMS}
    B.mkdir()
    for name,key in (('restore.bin','restore'),('install-b.bin','install_b')):shutil.copyfile(old[key],B/name)
    assert sha(B/'restore.bin')=='85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'
    assert sha(B/'install-b.bin')=='493fd0a010bedcfc5916314353f93565f7b159ac163d9bc61e7c5078140669e8'
    remote='/test/wolf/goal001/r02'
    (B/'state.txt').write_bytes(('SAVE '+remote+'/post-mode.bin &BC349 &1\r\nSAVE '+remote+'/post-callback.bin &BC38E &3\r\nEMOS sdserve --fast /\r\n').encode())
    (B/'route.txt').write_bytes(('SAVE '+remote+'/route.bin &BCB25 &1\r\nEMOS sdserve --fast /\r\n').encode())
    binding=json.loads(Path(old['source_binding']).read_text())
    assert binding['passed']and binding['rom_sha256']==components['emos_rom_sha256']
    binding['provenance']='Actual82 clean a25f fullROM readback/idle release plus actual81 full native85f9 readback. Retained source hashes revalidated here. Actual successor/current grant equality still required, no fresh device observation claimed.'
    (B/'source-binding.json').write_text(json.dumps(binding,indent=2)+'\n')
    (B/'guest-qualification.json').write_text(json.dumps(qualified,indent=2)+'\n')
    stage={n:p for n,p in old['stage'].items()if n not in ('wolf3d.vdpl','state.txt','route.txt')and not n.startswith(('a-','b-'))}
    for a in hw.ARMS:
        g=guests[a]['room'];stage[g['remote_name']]=g['guest']
    stage.update({'wolf3d.vdpl':modules['original'],'state.txt':str(B/'state.txt'),'route.txt':str(B/'route.txt')})
    listings={'vdplet-room':guests['original']['room']['listing']}
    files=list(stage.values())+list(modules.values())+list(listings.values())
    files += list(qualified['inputs'])+list(comp['inputs'])+[str(composition),str(release)]
    # Explicit current source/rollback evidence; no mutable TODO/global goal plan.
    files += [str(T/n)for n in ('HARDWARE-02-PLAN.md','prepare_h02.py','qualify_h02_guests.py','hardware02.py','h02_analyze.py','h02_bootstrap.py','h02_guest_binding.py','H02-GUESTS.json','H02-LAUNCH-PREFLIGHT.json','launch_h02.py','run_h02_composition.py','test_h02_controller.py','test_h02_replacement.py','snapshot_h02_inputs.py')]
    files += [str(p)for p in B.iterdir()if p.is_file()]
    base=release.parent
    files += [str(base/'release-observation.json'),str(base/'final/fresh.json'),str(base/'owner-install/verify-rollback/ROM.bin'),str(base/'owner-install/verify-rollback/receipt.json')]
    assert sha(base/'owner-install/verify-rollback/ROM.bin')==components['emos_rom_sha256']
    for m in tuple(sys.modules.values()):
        name=getattr(m,'__file__',None)
        if name and name.endswith(('.py','.so'))and name.startswith(('/Agon/mystuff/','/usr/')):files.append(name)
    files.append(str(E/'agents/net004/uart1-bootstrap-r01/bootstrap.py'))
    # Rehash retained exact ROM/map/tool/bootstrap closure, with actual82 identity
    # restoration above. These retained source facts are not a device grant.
    prior=json.loads((T.parent/'WOLF-PERF-009/build/preparation01/expected-context.json').read_text())
    assert prior['retained_components']==components
    assert prior['current_ROM_binding']['symbols']==binding['symbols']
    assert prior['current_ROM_binding']['map_sha256']==binding['map_sha256']
    for name,record in prior['files'].items():
        if name.startswith(str(E))and '/bench-scheduler/'not in name:
            assert sha(name)==record['sha256'],name;files.append(name)
    environment=json.loads((T/'H02-LAUNCH-PREFLIGHT.json').read_text())
    assert environment['passed']and not environment['target_access']
    for name,digest in environment['files'].items():assert sha(name)==digest,name;files.append(name)
    inputs={str(Path(p).resolve()):sha(p)for p in files}
    kit=dict(task='WOLF-GOAL-001-hardware02',request=hw.REQUEST,remote=remote,incoming_components=components,
        native_b_sha256=old['native_b_sha256'],modules=modules,stage=stage,listings=listings,guests=guests,
        retain_lease_after_test=False,restore=str(B/'restore.bin'),install_b=str(B/'install-b.bin'),flash_span=1105920,
        source_binding=str(B/'source-binding.json'),source_binding_passed=True,boot_binding_passed=True,
        p4_boot_build='net-003-r02-b2026-11-06-09-03-07Z',inputs=inputs,
        restrictions='ONE six uncapped room runs original/cache/trig/trig/cache/original and7INFO; shared controls, no source combination.4200s/360reserve/660newguestguard. First unexpected stop/RAMbeforeLOAD/app-only7593/exact85f9restore/fullcleanup/normalrelease. Mech first; reconcile actual predecessor handback/current tuple/fresh token. No Oryx/newcarrier/firmware/provider/default adoption.')
    for a in hw.ARMS:kit[a+'_module_sha256']=sha(modules[a])
    hw.verify_kit(kit)
    (B/'kit.json').write_text(json.dumps(kit,indent=2)+'\n')
    print(json.dumps(dict(passed=True,inputs=len(inputs),stage_files=len(stage),kit_sha256=sha(B/'kit.json'),request=kit['request'])))
if __name__=='__main__':main()
