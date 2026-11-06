"""Freeze observer-bearing matched cohort against actual44 release and retained bytes."""
from pathlib import Path
import json,hashlib
T=Path(__file__).resolve().parents[1];B=T/'build/hardware05';old=T/'build/hardware03';prior=T/'build/hardware04'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
k=json.loads((old/'kit.json').read_text())
for n,h in k['inputs'].items():assert sha(n)==h,n
current=json.loads((prior/'kit.json').read_text());release=json.loads((prior/'release44.json').read_text());components=release['release_observation']['components'];assert components==current['incoming_components']
checks=json.loads((B/'source-layout-check.json').read_text());assert checks['passed']and len(checks['clients'])==8
for backend in ('bespoke','vdplet'):
 for mode in ('cpu','unpaced','paced','control'):
  d=B/backend/mode;expected=json.loads((d/'payload/expected.json').read_text())
  for n,pin in expected['files'].items():assert sha(d/'payload'/n)==pin['sha256'],n
  k['stage'][('a-'if backend=='bespoke'else'b-')+mode+'.bin']=str(d/'payload/wolf3d.bin')
  for p in (d/'source').iterdir():
   if p.is_file()and p.suffix not in ('.bin','.lst','.log'):k['inputs'][str(p)]=sha(p)
  k['inputs'][str(d/'payload/wolf3d.bin')]=sha(d/'payload/wolf3d.bin')
# Old shared canonical assets/module/probe stay exact; each newly assembled
# payload's copies were independently checked above, so stage originals safely.
for p in k['stage'].values():k['inputs'][p]=sha(p)
a=old/'native-a/.pio/build/esp32dev/firmware.bin';b=T/'build/r04/native02/vdplet/.pio/build/esp32dev/firmware.bin'
assert sha(a)=='c5cfaaed91a0d294bbe30811ca57ff36a585d070946f0813a469412f57d77fcc'
assert sha(b)=='7593b9cf9a2dc60e81221d998527d4ac0d1c3f51077348ea03e869016aa0581d'
context=json.loads((prior/'incoming43.json').read_text());source=Path(context['native_span']);original=source.read_bytes();assert len(original)==1105920 and sha(source)=='5fbf82c41d6a7fbee6a9f121b16f321db544c316ee286f634878d7763ce54f37'
actual44=prior/'evidence/flash-restore/read.bin';r=actual44.read_bytes();assert r==original[:len(r)]and len(r)==1101824
span=((max(a.stat().st_size,b.stat().st_size,1101408)+4095)//4096)*4096;assert span==len(original)==1105920
for image,name in ((a,'install-a.bin'),(b,'install-b.bin')):
 raw=image.read_bytes();(B/name).write_bytes(raw+original[len(raw):span]);k['inputs'][str(B/name)]=sha(B/name)
(B/'restore.bin').write_bytes(original)
k.update(schema='wolf-perf003-physical-kit-v5',incoming_components=components,flash_span=span,native_a_sha256=sha(a),rollback_source=str(source))
# Pin current diagnostic-ROM maps/private compatibility evidence, not merely
# the old historical incoming identities inherited from the comparison kit.
for n,h in current['inputs'].items():
 if any(tag in n for tag in ('emos-control-tx-diag-r01','p4-full-r02','rebind43.json','incoming43.json')):assert sha(n)==h,n;k['inputs'][n]=h
for p in (source,actual44,prior/'release44.json',B/'restore.bin',B/'source-layout-check.json',T/'HARDWARE-RUN-05.md',T/'hardware/physical05.py',T/'hardware/prepare05.py',T/'hardware/build05.py',T/'hardware/check05.py',T/'hardware/kit05.py',T/'hardware/test_controller05.py',T/'hardware/trace04.py'):
 k['inputs'][str(p)]=sha(p)
(B/'kit.json').write_text(json.dumps(k,indent=2)+'\n')
print('FROZEN',len(k['inputs']),'inputs;8clients/nativeA/B unchanged; commonspan',span)
