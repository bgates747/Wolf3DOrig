"""Offline freeze after successful hardware03 build and lifecycle regression."""
from pathlib import Path
import hashlib,json,shutil,struct
T=Path(__file__).resolve().parents[1];B=T/'build/hardware03';old=T/'build/hardware02'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
k=json.loads((old/'kit.json').read_text())
for n,digest in k['inputs'].items():assert sha(Path(n))==digest,n
build=json.loads((B/'compile-receipt.json').read_text());assert len(build['steps'])==7 and all(s['returncode']==0 for s in build['steps'])
assert 'PASS exact native control:'in(B/'host-lifetime.log').read_text()
checks={}
for mode in ('cpu','unpaced','paced','control'):
 d=B/'bespoke'/mode;prior=old/'bespoke'/mode
 s=(d/'source/bench.inc').read_text();addition='    call wp_a_disarm ; release borrow before deleting backing storage\n    jp c,wp_failed\n';assert s.count(addition)==1
 assert s.replace(addition,'')==(prior/'source/bench.inc').read_text()
 s=(d/'source/standalone.inc').read_text();addition='wp_a_disarm:\n    ld a,242\n    ld hl,0\n    jp wp_a_control\n';assert s.count(addition)==1
 s=s.replace(addition,'').replace('wp_a_create_log:\n    call wp_a_disarm\n    ret c\n','wp_a_create_log:\n')
 assert s==(prior/'source/standalone.inc').read_text()
 for p in (d/'source').iterdir():
  if p.is_file()and p.suffix not in ('.bin','.lst','.log'):
   if p.name not in ('bench.inc','standalone.inc'):assert p.read_bytes()==(prior/'source'/p.name).read_bytes(),p
   k['inputs'][str(p)]=sha(p)
 expected=json.loads((d/'payload/expected.json').read_text())
 for name,pin in expected['files'].items():assert sha(d/'payload'/name)==pin['sha256'],name
 name='a-'+mode+'.bin';k['stage'][name]=str(d/'payload/wolf3d.bin');k['inputs'][str(d/'payload/wolf3d.bin')]=sha(d/'payload/wolf3d.bin')
 checks[mode]='Only acknowledged setup/release calls differ; all measured-loop instructions equal hardware02'
# B module reacquires/releases its log view each render and resets count onINIT;
# no persistent borrowed buffer pointer. Exact B binary/module remain retained.
bs=T/'build/r04/vdplet/native-source/wolf3d_module.cpp';text=bs.read_text();assert 'if(r->operation==VDPL_INIT)wp_log_count=0;'in text and 'h->buffer_acquire'in text and 'h->buffer_release'in text
k['inputs'][str(bs)]=sha(bs)
for p in (B/'vdplet').rglob('*'):
 if p.is_file():assert p.read_bytes()==(old/'vdplet'/p.relative_to(B/'vdplet')).read_bytes(),p
native=B/'native-a/video';prior=T/'build/hardware01/native-a/video'
a=(native/'wolf3d.h').read_text();a0=(prior/'wolf3d.h').read_text()
start=a.index('\tbool render_frame(');end=a.index('\n\t// Actual wall-column blit',start)
start0=a0.index('\tbool render_frame(');end0=a0.index('\n\t// Actual wall-column blit',start0)
assert a[start:end]==a0[start0:end0]
for name in ('wolf3d/wolf3d_world.h','wolf3d/render/wolf3d_draw.h'):assert(native/name).read_bytes()==(prior/name).read_bytes()
h=(native/'wolf_perf_recorder.h').read_text();assert h.replace('    void release() { data=nullptr; count=0; failed=false; }\n','')==(prior/'wolf_perf_recorder.h').read_text()
for p in native.rglob('*'):
 if p.is_file()and p.suffix not in ('.log',):k['inputs'][str(p)]=sha(p)
image=B/'native-a/.pio/build/esp32dev/firmware.bin';raw=image.read_bytes();incoming=Path(k['rollback_source']).read_bytes();offset=k['flash_offset'];span=k['flash_span']
assert len(raw)<=span and raw[0]==0xe9 and struct.unpack_from('<H',raw,12)[0]==0 and raw[2:4]==incoming[offset+2:offset+4]
(B/'install-a.bin').write_bytes(raw+incoming[offset+len(raw):offset+span])
for name in ('install-b.bin','restore.bin'):shutil.copyfile(old/name,B/name)
k.update(schema='wolf-perf003-physical-kit-v3',native_a_sha256=sha(image))
for name in ('hardware/physical03.py','hardware/prepare03.py','hardware/build03.py','hardware/lifetime03.cpp','hardware/kit03.py','HARDWARE-RUN-03.md'):
 p=T/name;k['inputs'][str(p)]=sha(p)
for p in [image,B/'install-a.bin',B/'install-b.bin',B/'restore.bin',B/'host/exact_control.inc',B/'host/wolf_perf_recorder.h']+list((B/'native-a/.pio/build/esp32dev').glob('firmware.*')):
 if p.is_file():k['inputs'][str(p)]=sha(p)
(B/'source-checks.json').write_text(json.dumps(dict(A_guest_scope=checks,native_draw_bracket_unchanged=True,overflow_guard_unchanged=True,B_retained_no_persistent_log_view=True,host_real_control_lifecycle_pass=True),indent=2)+'\n')
(B/'kit.json').write_text(json.dumps(k,indent=2)+'\n')
print('FROZEN',len(k['inputs']),'inputs; new nativeA',k['native_a_sha256'])
