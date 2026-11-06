"""Offline pinning, flash-span construction and package checks. No device I/O."""
from pathlib import Path
import hashlib,json,struct,re
T=Path(__file__).resolve().parents[1];B=T/'build/hardware01';E=T.parents[3].parent/'agon-extender'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
incoming=E/'agents/net003/physical-r02/backup-native/incoming-4MiB.bin'
assert sha(incoming)=='696755fa659e0e454a70ed8a010524963502fa73c33ad0b88d7dd3dc72067fb2'
full=incoming.read_bytes();assert len(full)==0x400000
offset=0x10000;original=full[offset:offset+1101408]
assert hashlib.sha256(original).hexdigest()=='200299428f75d8d54cfc4e5710950b28d0d697b503dcb066157739c316b2c91a'
a=B/'native-a/.pio/build/esp32dev/firmware.bin'
b=T/'build/r04/native02/vdplet/.pio/build/esp32dev/firmware.bin'
assert sha(a)=='85c520a1a9a82731c86778c00c3c6734db48e7529c925d5a44d030f1fdf61ff5'
assert sha(b)=='7593b9cf9a2dc60e81221d998527d4ac0d1c3f51077348ea03e869016aa0581d'
span=(max(a.stat().st_size,b.stat().st_size,len(original))+4095)&~4095
assert span<=1310720
for path in (a,b):
 raw=path.read_bytes();assert raw[0]==0xe9 and struct.unpack_from('<H',raw,12)[0]==0 # classic ESP32
 assert raw[2:4]==full[offset+2:offset+4], 'flash mode/frequency/size header mismatch'
for name,path in [('install-a.bin',a),('install-b.bin',b)]:
 raw=path.read_bytes();(B/name).write_bytes(raw+full[offset+len(raw):offset+span])
(B/'restore.bin').write_bytes(full[offset:offset+span])
stage={};inputs={}
for backend in ('bespoke','vdplet'):
 for mode in ('cpu','unpaced','paced','control'):
  payload=B/backend/mode/'payload';expected=json.loads((payload/'expected.json').read_text())
  for name,item in expected['files'].items():assert sha(payload/name)==item['sha256'],(backend,mode,name)
  stage[('a'if backend=='bespoke'else'b')+'-'+mode+'.bin']=str(payload/'wolf3d.bin')
  for name in expected['files']:
   if name=='wolf3d.bin':continue
   if name in stage:assert sha(stage[name])==sha(payload/name),name
   else:stage[name]=str(payload/name)
stage['resource-probe.bin']=str(B/'resource.bin')
obs=json.loads((E.parent/'MechAgon/.runtime/bench39-release/observation.json').read_text())
for name in ('hardware/physical.py','hardware/resource.asm','hardware/prepare.py','hardware/build.py','hardware/kit.py','HARDWARE-RUN-01.md','analyze.py'):
 p=T/name;inputs[str(p)]=sha(p)
for p in [a,b,incoming,B/'install-a.bin',B/'install-b.bin',B/'restore.bin',T.parent/'WOLF-PERF-001/hardware/physical.py']+[E/'scripts'/n for n in ('keyboard.py','sdcard.py','sdcard_staged.py','passive_serial.py')]+list(map(Path,stage.values())):
 inputs[str(p)]=sha(p)
for backend in ('bespoke','vdplet'):
 for mode in ('cpu','unpaced','paced','control'):
  source=B/backend/mode/'source'
  for p in source.glob('*.inc'):inputs[str(p)]=sha(p)
  inputs[str(source/'wolf3d.asm')]=sha(source/'wolf3d.asm')
 # All corrected normal timed loops remain byte-identical to r07.
 for mode in ('cpu','unpaced','paced'):
  assert (B/backend/mode/'source/bench.inc').read_bytes()==(T/'build/r07'/backend/mode/'source/bench.inc').read_bytes()
# A renderer/world source remains identical; private reply tag is in glue only.
for name in ('wolf3d/render/wolf3d_draw.h','wolf3d/wolf3d_world.h'):
 assert(B/'native-a/video'/name).read_bytes()==(T/'build/r04/native02/bespoke/video'/name).read_bytes()
kit=dict(schema='wolf-perf003-physical-kit-v1',incoming_components=obs['components'],stage=stage,inputs=inputs,flash_offset=offset,flash_span=span,rollback_source=str(incoming),native_a_sha256=sha(a),native_b_sha256=sha(b),stack_floor_bytes=512,source_nominal_cpu_hz=240000000,calibration='No external physical clock calibration; preserve raw counters')
(B/'kit.json').write_text(json.dumps(kit,indent=2)+'\n')
print(json.dumps(dict(stage_files=len(stage),flash_span=span,inputs=len(inputs),native_a=sha(a),native_b=sha(b)),indent=2))
