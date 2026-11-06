"""New hardware02 loading-only candidate; never modifies hardware01."""
from pathlib import Path
import hashlib,json,shutil
T=Path(__file__).resolve().parents[1];B=T/'build/hardware02';B.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for backend in ('bespoke','vdplet'):
 for mode in ('cpu','unpaced','paced','control'):
  old=T/'build/hardware01'/backend/mode;d=B/backend/mode
  shutil.copytree(old/'source',d/'source',ignore=shutil.ignore_patterns('*.bin','*.lst','*.log'))
  shutil.copytree(old/'payload',d/'payload')
  p=d/'source/loading_pages.inc';s=p.read_text()
  assert s.count('call w3d_audio_wait_for_vdp_ingress')==3
  for phase in (1,2,3):s=s.replace('    call w3d_audio_wait_for_vdp_ingress',f'    ld a,{phase}\n    ld (wpl_phase),a\n    call wp_loading_wait',1)
  p.write_text(s+'\n    include "loading_wait.inc"\n')
  shutil.copyfile(T/'hardware/loading_wait.inc',d/'source/loading_wait.inc')
  p=d/'source/wolf3d.asm';s=p.read_text();needle='    call main\n\nexit:';assert s.count(needle)==1
  p.write_text(s.replace(needle,'    call main\n    call wp_loading_save\n\nexit:'))
  for p in (d/'source').iterdir():
   if p.is_file()and p.name not in ('loading_pages.inc','loading_wait.inc','wolf3d.asm'):assert p.read_bytes()==(old/'source'/p.name).read_bytes(),p
manifest={str(p.relative_to(B)):sha(p)for p in B.rglob('*')if p.is_file()and 'source'in p.parts}
(B/'source-freeze.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Prepared eight hardware02 guests; timed loops and native images unchanged')
