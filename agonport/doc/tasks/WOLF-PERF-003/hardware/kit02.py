"""Freeze newly built loading candidates and unchanged retained components."""
from pathlib import Path
import hashlib,json,shutil
T=Path(__file__).resolve().parents[1];B=T/'build/hardware02';old=T/'build/hardware01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
k=json.loads((old/'kit.json').read_text())
for name,digest in k['inputs'].items():assert sha(Path(name))==digest,name
for name in ('install-a.bin','install-b.bin','restore.bin'):shutil.copyfile(old/name,B/name)
k['schema']='wolf-perf003-physical-kit-v2'
for backend in ('bespoke','vdplet'):
 for mode in ('cpu','unpaced','paced','control'):
  d=B/backend/mode;expected=json.loads((d/'payload/expected.json').read_text())
  for name,pin in expected['files'].items():assert sha(d/'payload'/name)==pin['sha256'],name
  label=('a'if backend=='bespoke'else'b')+'-'+mode+'.bin';k['stage'][label]=str(d/'payload/wolf3d.bin')
  prior=old/backend/mode/'source';now=d/'source'
  differences=[p.name for p in now.iterdir()if p.is_file()and p.suffix not in ('.bin','.lst','.log')and(not(prior/p.name).exists()or p.read_bytes()!=(prior/p.name).read_bytes())]
  assert sorted(differences)==['loading_pages.inc','loading_wait.inc','wolf3d.asm'],differences
  assert(now/'bench.inc').read_bytes()==(prior/'bench.inc').read_bytes()
  for p in now.iterdir():
   if p.is_file()and p.suffix not in ('.bin','.lst','.log'):k['inputs'][str(p)]=sha(p)
  k['inputs'][str(d/'payload/wolf3d.bin')]=sha(d/'payload/wolf3d.bin')
for name in ('hardware/physical02.py','hardware/loading_wait.inc','hardware/prepare02.py','hardware/build02.py','hardware/kit02.py','hardware/check02.py','HARDWARE-RUN-02.md'):
 p=T/name;k['inputs'][str(p)]=sha(p)
for name in ('install-a.bin','install-b.bin','restore.bin'):k['inputs'][str(B/name)]=sha(B/name)
(B/'kit.json').write_text(json.dumps(k,indent=2)+'\n')
print('HARDWARE02 frozen',len(k['inputs']),'pins; native images/timed sources unchanged')
