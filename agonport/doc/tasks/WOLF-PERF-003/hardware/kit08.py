"""Freeze host interruption observability without changing timed work."""
from pathlib import Path
import hashlib,json,shutil,importlib.util,sys
T=Path(__file__).resolve().parents[1];B=T/'build/hardware08';prior=T/'build/hardware07'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
k=json.loads((prior/'kit.json').read_text())
for p,h in k['inputs'].items():assert sha(p)==h,p
r=json.loads((prior/'release51.json').read_text());assert r['generation']==51 and r['released']and all(r['release_observation']['checks'].values());assert r['release_observation']['components']==k['incoming_components']
for name in ('install-a.bin','install-b.bin','restore.bin'):
 shutil.copyfile(prior/name,B/name);assert sha(B/name)==sha(prior/name)
for p in (prior/'release51.json',T/'HARDWARE-RUN-08.md',T/'HARDWARE-R07-RESULT.md',T/'hardware/physical08.py',T/'hardware/host_interrupt08.py',T/'hardware/test_controller08.py',T/'hardware/test_host_interrupt08.py',T/'hardware/kit08.py',T/'hardware/report08.py',B/'install-a.bin',B/'install-b.bin',B/'restore.bin',Path('/Agon/mystuff/agon-dev-env/cross-agent/agentcoms/messages/2026-11-06_03-02-33_pi5-manager_wolf-host-exit143-evidence-answer-one.md')):
 k['inputs'][str(p)]=sha(p)
k.update(schema='wolf-perf003-physical-kit-v8')
sys.path.insert(0,str(T/'hardware'));spec=importlib.util.spec_from_file_location('physical08',T/'hardware/physical08.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.verify_kit(k)
(B/'kit.json').write_text(json.dumps(k,indent=2)+'\n')
print('FROZEN',len(k['inputs']),'inputs; unchanged clients/renderers/module/listings/assets/timed code')
