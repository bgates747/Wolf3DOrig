"""Prepare one loading-only sender-observation guest; no compiler or device calls."""
from pathlib import Path
import hashlib,json,shutil
T=Path(__file__).resolve().parents[1]
B=T/'build/hardware04'
B.mkdir(exist_ok=False)
old=T/'build/hardware03/bespoke/paced'
d=B/'loading'
shutil.copytree(old/'source',d/'source',ignore=shutil.ignore_patterns('*.bin','*.lst','*.log'))
shutil.copytree(old/'payload',d/'payload')
def edit(name,before,after):
 p=d/'source'/name;s=p.read_text();assert s.count(before)==1,(name,before)
 p.write_text(s.replace(before,after))
edit('wolf3d.asm','    call main\n    call wp_loading_save','    call wpl3_init\n    call main\n    call wp_loading_save\n    call wpl3_save')
edit('wolf3d.asm','    call wp_run\n    jp w3d_gameplay_exit_shutdown','    ld a,1\n    ld (wpl3_reached),a ; loading-only: no warmup/render/PRT/log lifecycle\n    jp w3d_gameplay_exit_shutdown')
# Wrap only loading page calls; production present/print/asset send implementations
# and the existing timed harness are preserved verbatim.
p=d/'source/loading_pages.inc';s=p.read_text()
s=s.replace('    call wp_loading_paint','    call wpl3_paint_begin\n    call wp_loading_paint\n    call wpl3_paint_end')
s=s.replace('    call w3d_vdu_present','    call wpl3_present_begin\n    call w3d_vdu_present\n    call wpl3_present_done')
s=s.replace('Rotation starts after loading.','Loading diagnostic - no rotation.')
p.write_text(s)
edit('loading_wait.inc','    ld c,010h\n    MOSCALL mos_clearvdpflags','    call wpl3_begin_fence\n    call wpl3_clear_begin\n    ld c,010h\n    MOSCALL mos_clearvdpflags\n    call wpl3_clear_end\n    call wpl3_tx_begin')
edit('loading_wait.inc','    rst.lil 018h\n@wait:','    rst.lil 018h\n    call wpl3_tx_end\n    call wpl3_wait_begin\n@wait:')
edit('loading_wait.inc','    inc (hl)\n    or a','    inc (hl)\n    call wpl3_wait_end\n    or a')
edit('loading_wait.inc','@expired:\n    call wpl_record_elapsed','@expired:\n    call wpl_record_elapsed\n    call wpl3_commit')
edit('loading_wait.inc','@record:\n    call wpl_record_elapsed','@record:\n    call wpl_record_elapsed\n    call wpl3_commit')
p=d/'source/loading_wait.inc';p.write_text(p.read_text()+'\n    include "loading_trace04.inc"\n')
shutil.copyfile(T/'hardware/loading_trace04.inc',d/'source/loading_trace04.inc')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
changed={'wolf3d.asm','loading_pages.inc','loading_wait.inc','loading_trace04.inc'}
for p in (d/'source').iterdir():
 if p.is_file()and p.name not in changed:assert p.read_bytes()==(old/'source'/p.name).read_bytes(),p
(B/'source-freeze.json').write_text(json.dumps({str(p.relative_to(B)):sha(p)for p in B.rglob('*')if p.is_file()and'source'in p.parts},indent=2)+'\n')
(B/'candidate.json').write_text(json.dumps(dict(schema='wolf-loading-query04-source',base_native='c5cfaaed91a0d294bbe30811ca57ff36a585d070946f0813a469412f57d77fcc',emos_rom='b5a1f4aa3b9f4527aafb5f48aa29445c3e30962c5b21382729c370944b043b02',emos_source='c9c8b6be316b5ebb64da1f16773ec3c886349267',p4_last_verified='a967fac2e1364e5c1d80964ed5e8183feee693e4f63c256a02654dc8482e6eee',private_ram=dict(serial_flags=0xbc35a,backend=0xbcb25,reply_parser=0xbc378),native_incoming=None,current_grant=None,changed_sources=sorted(changed),no_render=True,no_prt=True,authority='Smith existing003-16 hardware diagnosis renewed proceed2026-11-05; actual hardware admission separate'),indent=2)+'\n')
print('Prepared loading-only source and32-entry+current RAM trace; no compiler/device operation.')
