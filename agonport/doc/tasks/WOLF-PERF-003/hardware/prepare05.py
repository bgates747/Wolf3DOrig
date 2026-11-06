"""Copy the real benchmark sequence and add setup-only observations, no build/device."""
from pathlib import Path
import hashlib,json,shutil
T=Path(__file__).resolve().parents[1];B=T/'build/hardware05';B.mkdir(exist_ok=False)
changed={'wolf3d.asm','loading_pages.inc','loading_wait.inc','loading_trace04.inc'}
for backend in ('bespoke','vdplet'):
 for mode in ('cpu','unpaced','paced','control'):
  old=T/'build'/('hardware03'if backend=='bespoke'else'hardware02')/backend/mode;d=B/backend/mode
  shutil.copytree(old/'source',d/'source',ignore=shutil.ignore_patterns('*.bin','*.lst','*.log'))
  shutil.copytree(old/'payload',d/'payload')
  p=d/'source/wolf3d.asm';s=p.read_text();needle='    call main\n    call wp_loading_save';assert s.count(needle)==1
  s=s.replace(needle,'    call wpl3_init\n    call main\n    call wp_loading_save\n    call wpl3_save')
  needle='    call wp_loading_ready\n    call wp_run';assert s.count(needle)==1
  s=s.replace(needle,'    call wp_loading_ready\n    ld a,(wp_loading_error)\n    or a\n    jp nz,w3d_gameplay_exit_shutdown\n    ld a,1\n    ld (wpl3_reached),a\n    call wp_run');p.write_text(s)
  # Use the assembled/qualified loader hooks, restoring the canonical text.
  for name in ('loading_pages.inc','loading_wait.inc','loading_trace04.inc'):
   text=(T/'build/hardware04/loading/source'/name).read_text()
   if name=='loading_pages.inc':text=text.replace('Loading diagnostic - no rotation.','Rotation starts after loading.')
   (d/'source'/name).write_text(text)
  for p in (d/'source').iterdir():
   if p.is_file()and p.name not in changed:assert p.read_bytes()==(old/'source'/p.name).read_bytes(),p
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(B/'source-freeze.json').write_text(json.dumps({str(p.relative_to(B)):sha(p)for p in B.rglob('*')if p.is_file()and'source'in p.parts},indent=2)+'\n')
print('Prepared8 observer-bearing benchmark clients; exact timed/asset/send/renderer sources retained.')
