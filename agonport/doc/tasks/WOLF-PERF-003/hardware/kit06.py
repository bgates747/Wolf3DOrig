"""Freeze a corrected host entry controller, reusing all compiled05 inputs."""
from pathlib import Path
import hashlib,json,shutil
T=Path(__file__).resolve().parents[1];B=T/'build/hardware06';prior=T/'build/hardware05'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
k=json.loads((prior/'kit.json').read_text())
for p,h in k['inputs'].items():assert sha(p)==h,p
release=prior/'release47.json';r=json.loads(release.read_text());assert r['generation']==47 and r['released']
assert r['release_observation']['components']==k['incoming_components']
assert all(r['release_observation']['checks'].values())
for name in ('install-a.bin','install-b.bin','restore.bin'):
 shutil.copyfile(prior/name,B/name);assert sha(B/name)==sha(prior/name)
for p in (release,B/'install-a.bin',B/'install-b.bin',B/'restore.bin',T/'HARDWARE-RUN-06.md',T/'HARDWARE-ENTRY-R05-RESULT.md',T/'hardware/physical06.py',T/'hardware/test_controller06.py',T/'hardware/kit06.py',T/'hardware/report06.py'):
 k['inputs'][str(p)]=sha(p)
k.update(schema='wolf-perf003-physical-kit-v6')
(B/'kit.json').write_text(json.dumps(k,indent=2)+'\n')
print('FROZEN',len(k['inputs']),'pins; original8clients/native/module/asset bytes unchanged')
