"""Freeze loading04 candidate; optionally bind a reconciled retained incoming image."""
from pathlib import Path
import argparse,hashlib,json,struct
T=Path(__file__).resolve().parents[1];B=T/'build/hardware04';E=Path('/Agon/mystuff/agon-extender')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--incoming',type=Path);args=p.parse_args()
check=json.loads((B/'source-layout-check.json').read_text());assert check['passed']
for name,digest in json.loads((B/'source-freeze.json').read_text()).items():assert sha(B/name)==digest,name
assert all(x['returncode']==0 for x in json.loads((B/'compile-receipt.json').read_text())['steps'])
fixed={E/'agents/net004/emos-rfc25-r01/ROM.bin':'b5a1f4aa3b9f4527aafb5f48aa29445c3e30962c5b21382729c370944b043b02',E/'agents/net004/emos-rfc25-r01/mos.map':'c1da58e4491ab0a5d0fd4720457ce42ccdb955a67776efeac61fef08ee14cc10',E/'agents/net004/emos-rfc25-r01/mos.elf.map':'8580fd2676d1d41b314c9d19b8e88fd4d08a2ae2a9ddd87b7172140ad6ec4701',E/'agents/net004/p4-full-r02/build/agon_extender.bin':'a967fac2e1364e5c1d80964ed5e8183feee693e4f63c256a02654dc8482e6eee',T/'build/hardware03/native-a/.pio/build/esp32dev/firmware.bin':'c5cfaaed91a0d294bbe30811ca57ff36a585d070946f0813a469412f57d77fcc'}
for path,digest in fixed.items():assert sha(path)==digest,path
maps=(E/'agents/net004/emos-rfc25-r01/mos.map').read_text()
for symbol,address in {'_sysvars':0xbc322,'_vpd_protocol_flags':0xbc326,'_serialFlags':0xbc35a,'_emosVduBackend':0xbcb25,'_vdp_protocol_state':0xbc378,'_user_kbvector':0xbc38e}.items():
 import re
 match=re.search(r'0x([0-9a-fA-F]+)\s+'+symbol+r'\s*$',maps,re.M);assert match and int(match[1],16)==address,symbol
payload=B/'loading/payload';expected=json.loads((payload/'expected.json').read_text())
for name,pin in expected['files'].items():
 if name!='wolf3d.bin':assert sha(payload/name)==pin['sha256'],name
expected.update(schema='wolf-loading04',mode='loading-only',no_render=True)
expected['files']['wolf3d.bin']=dict(bytes=(payload/'wolf3d.bin').stat().st_size,sha256=sha(payload/'wolf3d.bin'))
(payload/'expected.json').write_text(json.dumps(expected,indent=2)+'\n')
stage={('a-loading04.bin'if name=='wolf3d.bin'else name):str(payload/name)for name in expected['files']}
inputs={str(path):digest for path,digest in fixed.items()}
for name in stage.values():inputs[name]=sha(name)
for root in (B/'loading/source',T/'hardware'):
 for f in root.rglob('*'):
  if f.is_file()and f.suffix not in ('.bin','.lst','.log','.pyc')and '__pycache__'not in f.parts:inputs[str(f)]=sha(f)
# Reviewed inherited code and its transport imports remain consumer inputs.
for path in [T.parent/'WOLF-PERF-001/hardware/physical.py',E/'scripts/sdcard.py',E/'scripts/sdcard_staged.py',E/'scripts/keyboard.py',E/'scripts/passive_serial.py',T/'HARDWARE-LOADING-R04.md']:
 inputs[str(path)]=sha(path)
kit=dict(schema='wolf-loading04-kit',ready=False,stage=stage,inputs=inputs,labels=check['labels'],candidate_sha256=check['binary_sha256'],native_a_sha256=fixed[T/'build/hardware03/native-a/.pio/build/esp32dev/firmware.bin'],incoming_components=None,flash_offset=65536)
if args.incoming:
 context=json.loads(args.incoming.read_text());components=context['components'];assert set(components)=={'emos_rom_sha256','p4_app_sha256','native_vdp_sha256','startup_sha256','listener_sha256'}
 assert components['emos_rom_sha256']==fixed[E/'agents/net004/emos-rfc25-r01/ROM.bin']
 assert components['p4_app_sha256']==fixed[E/'agents/net004/p4-full-r02/build/agon_extender.bin']
 assert components['startup_sha256']=='ed403e17f90a22c634afa0de3cad65451bc52da86bde6da084abe42fac3b7c64'
 assert components['listener_sha256']=='0566e17f18747c2e625d2450ce5324a2b1097bce323a5e4d70fad6dcb41cdff2'
 # Caller must supply reconciled owner/scheduler release evidence, not inferred
 # current state. This freezes retained bytes; it performs no target read.
 evidence=Path(context['release_evidence']);assert evidence.is_file()
 image=Path(context['native_app']);assert sha(image)==components['native_vdp_sha256']
 offset=65536;old=image.read_bytes();new=(T/'build/hardware03/native-a/.pio/build/esp32dev/firmware.bin').read_bytes()
 assert context['active_app_offset']==offset and context['active_partition_bytes']>=max(len(old),len(new))
 span=((max(len(old),len(new))+4095)//4096)*4096;assert span<=context['active_partition_bytes']
 # Prefer the actual owner's retained independently verified app/tail span.
 # No new whole-device backup is requested. A prior fullflash artifact is only
 # admissible if its bytes already match this reconciled incoming application.
 if 'native_span' in context:
  backup=Path(context['native_span']);assert sha(backup)==context['native_span_sha256']
  raw=backup.read_bytes();assert len(raw)>=span and raw[:len(old)]==old
  original=raw[:span]
 else:
  backup=Path(context['native_fullflash']);assert sha(backup)==context['native_fullflash_sha256']
  raw=backup.read_bytes();assert len(raw)==4194304 and raw[offset:offset+len(old)]==old
  original=raw[offset:offset+span]
 assert old[0]==new[0]==0xe9 and old[2:4]==new[2:4]and struct.unpack_from('<H',new,12)[0]==0
 (B/'restore.bin').write_bytes(original);(B/'install-a.bin').write_bytes(new+original[len(new):])
 kit.update(ready=True,incoming_components=components,flash_span=span,rollback_source=str(backup),incoming_evidence=str(evidence))
 for f in (args.incoming,image,backup,evidence,B/'restore.bin',B/'install-a.bin'):kit['inputs'][str(f)]=sha(f)
(B/('kit.json'if args.incoming else'candidate-kit.json')).write_text(json.dumps(kit,indent=2)+'\n')
print('FROZEN',len(inputs),'candidate inputs; current incoming bound:',kit['ready'])
