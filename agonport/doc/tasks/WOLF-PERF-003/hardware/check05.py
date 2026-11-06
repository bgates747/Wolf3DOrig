"""Actual assembled bounds, unchanged timed/send/pixel source and sequence checks."""
from pathlib import Path
import hashlib,json,re,shutil,ast
from trace04 import FILE_BYTES
T=Path(__file__).resolve().parents[1];B=T/'build/hardware05';results=[]
for backend in ('bespoke','vdplet'):
 for mode in ('cpu','unpaced','paced','control'):
  d=B/backend/mode;old=T/'build'/('hardware03'if backend=='bespoke'else'hardware02')/backend/mode
  for n in ('bench.inc','agnb_api.inc','agnb_dependencies.inc','wolf3d_render_async.inc','wolf3d_audio.inc')+ (('standalone.inc',)if backend=='bespoke'else('wolf3d_vdplet_batch.inc','wolf3d_vdplet_backend.inc')):
   assert(d/'source'/n).read_bytes()==(old/'source'/n).read_bytes(),(backend,mode,n)
  main=(d/'source/wolf3d.asm').read_text();assert main.count('    call wp_run\n')==1
  assert 'ld a,(wp_loading_error)\n    or a\n    jp nz,w3d_gameplay_exit_shutdown' in main
  wait=(d/'source/loading_wait.inc').read_text();assert wait.count('MOSCALL mos_clearvdpflags')==wait.count('rst.lil 018h')==1
  text=(d/'source/loading_pages.inc').read_text();assert 'Rotation starts after loading.'in text and 'Loading diagnostic - no rotation.'not in text
  listing=(d/'source/wolf3d.lst').read_text()
  def at(n):
   m=re.search(r'^([0-9A-F]{6})[^\n]*\b'+n+':',listing,re.M);assert m,n;return int(m[1],16)
  assert at('wpl3_file_end')-at('wpl3_header')==FILE_BYTES and at('wpl3_end')<0xa0000
  raw=(d/'source/wolf3d.bin').read_bytes();assert raw[at('wpl_query')-0x40000:at('wpl_query')-0x40000+3]==bytes((23,0,0x86))
  shutil.copyfile(d/'source/wolf3d.bin',d/'payload/wolf3d.bin')
  expected=json.loads((d/'payload/expected.json').read_text());expected['schema']='wolf-perf003-hardware05';expected['files']['wolf3d.bin']=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
  for n,pin in expected['files'].items():assert hashlib.sha256((d/'payload'/n).read_bytes()).hexdigest()==pin['sha256'],n
  (d/'payload/expected.json').write_text(json.dumps(expected,indent=2)+'\n')
  results.append(dict(backend=backend,mode=mode,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),trace=at('wpl3_header'),staging_clear=True,timed_source_unchanged=True))
ast.parse((T/'hardware/physical05.py').read_text())
(B/'source-layout-check.json').write_text(json.dumps(dict(passed=True,clients=results,no_device_calls=True),indent=2)+'\n')
print('PASS8 actual assembled layouts, original timed/client send sources, original hint and fail-closed final loading fence')
