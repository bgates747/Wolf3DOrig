"""Validate actual assembled trace extent/initialization and unchanged sender source."""
from pathlib import Path
import json,re,hashlib,shutil
from trace04 import *
T=Path(__file__).resolve().parents[1];B=T/'build/hardware04';S=B/'loading/source';old=T/'build/hardware03/bespoke/paced/source'
listing=(S/'wolf3d.lst').read_text();binary=(S/'wolf3d.bin').read_bytes()
def at(name):
 m=re.search(r'^([0-9A-F]{6})[^\n]*\b'+name+':',listing,re.M);assert m,name;return int(m[1],16)
assert at('wpl3_current')-at('wpl3_header')==64
assert at('wpl3_ring')-at('wpl3_current')==128
assert at('wpl3_file_end')-at('wpl3_header')==FILE_BYTES
assert at('wpl3_end')<0xa0000,'retain staging separation'
raw=binary[at('wpl3_header')-0x40000:at('wpl3_file_end')-0x40000]
# DS defaults are deliberately NOT trusted. Reconstruct initialization's exact
# byte clear over mutable..end, then validate decoder accepts this empty record.
initialized=raw[:7]+bytes(FILE_BYTES-7);assert decode(initialized)['history']==[]
helper=(S/'loading_trace04.inc').read_text();assert 'ld bc,wpl3_end-wpl3_mutable-1' in helper and 'ldir' in helper
assert not re.search(r'^\s*(?:di|out0|in0)\b',helper,re.M)
wait=(S/'loading_wait.inc').read_text();assert wait.count('MOSCALL mos_clearvdpflags')==1 and wait.count('rst.lil 018h')==1
assert wait.index('rst.lil 018h')<wait.index('@wait:')
main=(S/'wolf3d.asm').read_text();assert '    call wp_run\n' not in main and 'call wpl3_init\n    call main' in main
assert 'call wp_loading_save\n    call wpl3_save' in main
for name in ('agnb_api.inc','agnb_dependencies.inc','wolf3d_audio.inc','wolf3d_render_async.inc','bench.inc','standalone.inc'):
 assert (S/name).read_bytes()==(old/name).read_bytes(),name
assert binary[at('wpl_query')-0x40000:at('wpl_query')-0x40000+3]==bytes((23,0,0x86))
shutil.copyfile(S/'wolf3d.bin',B/'loading/payload/wolf3d.bin')
report=dict(passed=True,no_device_calls=True,binary_bytes=len(binary),binary_sha256=hashlib.sha256(binary).hexdigest(),file_bytes=FILE_BYTES,labels={name:at(name)for name in ('wpl3_header','wpl3_current','wpl3_ring','wpl3_file_end','wpl3_end','wpl_query','wpl_data')},no_reachable_wp_run=True,unchanged_asset_present_send_sources=True,initialized_header_decodes=True)
(B/'source-layout-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
