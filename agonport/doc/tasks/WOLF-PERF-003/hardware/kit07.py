"""Freeze unchanged compiled inputs with explicit retained assembler listings."""
from pathlib import Path
import hashlib,json,shutil,importlib.util,sys
T=Path(__file__).resolve().parents[1];B=T/'build/hardware07';prior=T/'build/hardware06'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
k=json.loads((prior/'kit.json').read_text())
for p,h in k['inputs'].items():assert sha(p)==h,p
release=prior/'release49.json';r=json.loads(release.read_text());assert r['generation']==49 and r['released']
assert r['release_observation']['components']==k['incoming_components']and all(r['release_observation']['checks'].values())
for name in ('install-a.bin','install-b.bin','restore.bin'):
 shutil.copyfile(prior/name,B/name);assert sha(B/name)==sha(prior/name)
assert sha(prior/'evidence/flash-restore/read.bin')==sha(B/'restore.bin')
k['listings']={}
for backend in ('bespoke','vdplet'):
 for mode in ('cpu','unpaced','paced','control'):
  p=T/'build/hardware05'/backend/mode/'source/wolf3d.lst';k['listings'][backend+'-'+mode]=str(p);k['inputs'][str(p)]=sha(p)
for p in (release,prior/'evidence/flash-restore/read.bin',B/'install-a.bin',B/'install-b.bin',B/'restore.bin',T/'HARDWARE-RUN-07.md',T/'HARDWARE-R06-RESULT.md',T/'hardware/physical07.py',T/'hardware/test_controller07.py',T/'hardware/kit07.py',T/'hardware/report07.py'):
 k['inputs'][str(p)]=sha(p)
for name in ('before.bin','after.bin','stack.bin','timing.bin','loading.bin','loading3.bin'):
 p=prior/'evidence/02-bespoke-cpu'/name;k['inputs'][str(p)]=sha(p)
k.update(schema='wolf-perf003-physical-kit-v7',rollback_source=str(prior/'evidence/flash-restore/read.bin'))
sys.path.insert(0,str(T/'hardware'));spec=importlib.util.spec_from_file_location('physical07',T/'hardware/physical07.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.verify_kit(k)
(B/'kit.json').write_text(json.dumps(k,indent=2)+'\n')
print('FROZEN',len(k['inputs']),'pins;8listings; unchanged8clients/native/module/assets')
