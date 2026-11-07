"""File-only qualified kit/current-release join. No hardware admission or I/O."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

T=Path(__file__).resolve().parent
B=T/'build/hardware02'
E=Path('/Agon/mystuff/agon-extender')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert Path(sys.executable)==E/'.venv/bin/python'
    assert not B.exists(),'Preserve a frozen selection; use a new revision'
    sys.path.insert(0,str(T))
    import hardware02 as hw
    import bootstrap
    import qualify_hardware_guests as qualifier
    qualified=qualifier.qualify();assert qualified['passed']
    old_path=T.parent/'WOLF-PERF-022/build/hardware02/kit.json'
    old=json.loads(old_path.read_text())
    prior_result=T.parent/'WOLF-PERF-022/results/actual95/RESULT.json'
    assert json.loads(prior_result.read_text())['passed']
    latest=E/'agents/bench-scheduler/mechagon-goal001-r09'
    release=json.loads((latest/'released.json').read_text())
    assert release['generation']==98 and release['released']
    components=release['release_observation']['components']
    assert components==old['incoming_components']
    assert sha(latest/'owner-install/verify-rollback/ROM.bin')==components['emos_rom_sha256']
    restored97=T/'results/actual97/cleanup97/evidence/flash-restore/read.bin'
    assert sha(restored97)==sha(old['restore'])
    files=[Path(p) for p in qualified['inputs']]
    files.extend((old_path,prior_result,restored97,T/'results/actual97/RESULT.json',latest/'released.json',latest/'release-observation.json',
        latest/'final/fresh.json',latest/'owner-install/verify-rollback/ROM.bin',
        latest/'owner-install/verify-rollback/receipt.json'))
    B.mkdir()
    for name,key in (('restore.bin','restore'),('install-b.bin','install_b')):
        assert sha(old[key])==old['inputs'][old[key]]
        shutil.copyfile(old[key],B/name)
    assert sha(B/'restore.bin')=='85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'
    assert sha(B/'install-b.bin')=='493fd0a010bedcfc5916314353f93565f7b159ac163d9bc61e7c5078140669e8'
    remote='/test/wolf/perf023/r02'
    (B/'state.txt').write_bytes(('SAVE '+remote+'/post-mode.bin &BC349 &1\r\nSAVE '+remote+'/post-callback.bin &BC38E &3\r\nEMOS sdserve --fast /\r\n').encode())
    (B/'route.txt').write_bytes(('SAVE '+remote+'/route.bin &BCB25 &1\r\nEMOS sdserve --fast /\r\n').encode())
    binding=json.loads(Path(old['source_binding']).read_text())
    assert binding['passed'] and binding['rom_sha256']==components['emos_rom_sha256']
    binding['provenance']='Actual98 exacta25f fullROM rollback/readback and clean release match retained d9b/a25f/5d657/ed403/0566. Actual97 full85f9 native rollback/readback independently verified. This is retained source/release provenance, not a new device read or grant; actual current admission remains mandatory.'
    (B/'source-binding.json').write_text(json.dumps(binding,indent=2)+'\n')
    (B/'guest-qualification.json').write_text(json.dumps(qualified,indent=2)+'\n')
    guests=json.loads((T/'HARDWARE-GUESTS.json').read_text())
    modules={a:guests[a]['room']['module']for a in hw.ARMS}
    stage={n:p for n,p in old['stage'].items() if not n.startswith('b-') and n not in ('wolf3d.vdpl','state.txt','route.txt')}
    for p in stage.values():
        assert sha(p)==old['inputs'][p],p
        files.append(Path(p))
    for arm in hw.ARMS:stage[guests[arm]['room']['remote_name']]=guests[arm]['room']['guest']
    stage.update({'wolf3d.vdpl':modules['original'],'state.txt':str(B/'state.txt'),'route.txt':str(B/'route.txt')})
    for n in ('PLAN.md','HARDWARE-PLAN.md','HARDWARE-PLAN02.md','prepare_hardware.py','hardware02.py','launch02.py',
        'host_observer.py','observe.py','OBSERVER-PREFLIGHT.json','LAUNCH-PREFLIGHT.json',
        'bootstrap.py','test_bootstrap_closure.py','AMENDMENT-02.md','guest_binding.py','analyze.py','HARDWARE-GUESTS.json','snapshot_inputs.py',
        'test_hardware02.py','test_replacement02.py','test_observer_controller.py','run_composition.py',
        'HOST-REUSE.json','controller-source-delta.patch','CONTROLLER-RESULT.md','CONTROLLER-RESULT03.md','report_physical.py','record_actors.py'):
        files.append(T/n)
    files.extend(T.parent/'WOLF-PERF-022/results/host01'/n for n in ('RESULT.json','SHA256.json','release.json'))
    for n,interpreter in (('LAUNCH-PREFLIGHT.json',str(E/'.venv/bin/python')),('OBSERVER-PREFLIGHT.json','/usr/bin/python3')):
        environment=json.loads((T/n).read_text())
        assert environment['passed'] and not environment['target_access'] and environment['interpreter']==interpreter
        for p,digest in environment['files'].items():
            assert sha(p)==digest,p
            files.append(Path(p))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name and name.endswith(('.py','.so')) and name.startswith(('/Agon/mystuff/','/usr/')):files.append(Path(name))
    # Dynamic imports, subprocess scripts and their configs are explicit inputs.
    files.extend(bootstrap.REQUIRED)
    files.extend(p for p in B.iterdir()if p.is_file())
    kit={k:old[k]for k in ('native_b_sha256','flash_span','p4_boot_build')}
    kit.update(task='WOLF-PERF-023-hardware02',request=hw.REQUEST,remote=remote,
        listings={'vdplet-room':guests['original']['room']['listing']},
        incoming_components=components,modules=modules,stage=stage,guests=guests,
        retain_lease_after_test=False,restore=str(B/'restore.bin'),install_b=str(B/'install-b.bin'),
        source_binding=str(B/'source-binding.json'),source_binding_passed=True,boot_binding_passed=True,
        inputs={str(p.resolve()):sha(p)for p in files},
        restrictions='ONE separate four uncapped original/candidate/candidate/original rooms/fiveINFO. Positive same-lease foreground observer before targetIO;45s handshake within4200s/360cleanup/660newguest guards. First unexpectedSTOP/RAMbeforeLOAD/safe in-flight completion/full85f9restore/fullcleanup/normalrelease. Mech-first; no firmware/carrier/provider/default change or replay/HOLD.')
    for arm in hw.ARMS:kit[arm+'_module_sha256']=sha(modules[arm])
    hw.verify_kit(kit)
    (B/'kit.json').write_text(json.dumps(kit,indent=2)+'\n')
    print(json.dumps(dict(passed=True,files=len(kit['inputs']),stage=len(stage),kit_sha256=sha(B/'kit.json'),target_io=False)))


if __name__=='__main__':main()
