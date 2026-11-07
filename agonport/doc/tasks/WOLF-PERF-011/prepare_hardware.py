"""Freeze exact one-guest LOAD-only kit from current76 restored components."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil

T=Path(__file__).resolve().parent
Q=T.parent/'WOLF-PERF-009'
B=T/'build/hardware02'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    old=json.loads((Q/'build/hardware01/kit.json').read_text())
    release=Path('/Agon/mystuff/agon-extender/agents/bench-scheduler/mechagon-async001-u1-r01/released76.json')
    current=json.loads(release.read_text())
    assert current['generation']==76 and current['released']
    assert current['release_observation']['components']==old['incoming_components']
    rom=release.parent/'owner-install/verify-rollback/ROM.bin'
    assert sha(rom)==old['incoming_components']['emos_rom_sha256']
    receipt=json.loads((T/'build/guest01/receipt.json').read_text());assert receipt['passed']
    guest=json.loads((T/'build/guest01/binding.json').read_text())
    assert guest['package_bytes']==24420 and guest['package_limit']==24421
    B.mkdir(exist_ok=False)
    for n,key in [('restore.bin','restore'),('install-b.bin','install_b')]:
        assert sha(old[key])==old['inputs'][old[key]]
        shutil.copyfile(old[key],B/n)
    remote='/test/wolf/perf011/r01'
    (B/'state.txt').write_bytes(('SAVE '+remote+'/post-mode.bin &BC349 &1\r\nSAVE '+remote+'/post-callback.bin &BC38E &3\r\nEMOS sdserve --fast /\r\n').encode())
    (B/'route.txt').write_bytes(('SAVE '+remote+'/route.bin &BCB25 &1\r\nEMOS sdserve --fast /\r\n').encode())
    stage={n:p for n,p in old['stage'].items() if n.endswith(('.agnb','.w3l','.cfg'))}
    for n,p in stage.items():assert sha(p)==old['inputs'][p],n
    stage.update({'rotate.bin':guest['guest'],'wolf3d.vdpl':guest['module'],
        'state.txt':str(B/'state.txt'),'route.txt':str(B/'route.txt')})
    # Retain and independently pin actual helper/runtime files, not mutable old task statuses.
    dependencies={n:d for n,d in old['inputs'].items() if n.endswith(('.py','.json')) and
        (n.startswith(('/Agon/mystuff/agon-extender/','/Agon/mystuff/agon-dev-env/')) or
         '/WOLF-PERF-003/hardware/' in n or '/WOLF-PERF-001/hardware/' in n)}
    for n,d in dependencies.items():assert sha(n)==d,n
    files=set(dependencies)|set(stage.values())|{str(release),str(rom),old['source_binding']}
    files|={str(p)for p in (T/'build/guest01').rglob('*')if p.is_file()}
    files|={str(p)for p in T.iterdir()if p.is_file()}
    files|={str(p)for p in B.iterdir()if p.is_file()}
    files|={str(Q/n)for n in ('hardware02.py','bootstrap.py','guest_binding.py')}
    files|={str(T.parent/'WOLF-PERF-003/analyze.py'),str(T.parent/'WOLF-PERF-003/hardware/trace04.py')}
    environment=json.loads((T/'LAUNCH-PREFLIGHT.json').read_text())
    for n,d in environment['files'].items():assert sha(n)==d,n
    files|=set(environment['files'])
    inputs={n:sha(n)for n in sorted(files)}
    kit=dict(task='WOLF-PERF-011-visible-manual01',request='8fd506cf5fbe',remote=remote,
        incoming_components=old['incoming_components'],manual_run_only=True,retain_lease_after_test=True,
        module_sha256=guest['module_sha256'],guest=guest,stage=stage,
        listings={'vdplet-paced':guest['listing']},source_binding=old['source_binding'],
        restore=str(B/'restore.bin'),install_b=str(B/'install-b.bin'),flash_span=1105920,
        native_b_sha256=old['native_b_sha256'],p4_boot_build=old['p4_boot_build'],
        inputs=inputs,actual76_release=str(release),
        scope='ONE latest optimized paced visible guest, stage+LOAD only; Smith manually RUNs after ready question. No static/probe/hidden arm. Exact native restore/readback and owned cleanup after review.')
    (B/'kit.json').write_text(json.dumps(kit,indent=2)+'\n')
    print(json.dumps(dict(inputs=len(inputs),stage=len(stage),kit_sha256=sha(B/'kit.json')),indent=2))


if __name__=='__main__':main()
