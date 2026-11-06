"""Build new task-owned r06 guests: bind A map, show existing loading dots."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
PROGRESS='''
; Setup-only: make the game's finalized-asset dot visible on the displayed page.
; Both page states are warmed with full renders before timing starts.
wp_loading_present:
    push af
    push bc
    push de
    push hl
    push ix
    push iy
    call w3d_vdu_present
    call w3d_audio_wait_for_vdp_ingress
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ret
wp_loading_ready:
    ld hl,@message
    call printString
    call printNewLine
    jp wp_loading_present
@message: db "Assets loaded. Preparing room (34,36)...",0
'''
def prepare():
 out=HERE/'build/r06';out.mkdir(exist_ok=False);sources={}
 for backend in ('bespoke','vdplet'):
  for mode in ('cpu','unpaced','paced'):
   old=HERE/'build/r05'/backend/mode;dst=out/backend/mode
   shutil.copytree(old/'source',dst/'source',ignore=shutil.ignore_patterns('*.bin','*.lst','*.log'))
   shutil.copytree(old/'payload',dst/'payload')
   src=dst/'source';s=(src/'wolf3d.asm').read_text()
   s=once(s,"printImageDot:\n    ld a,'.'\n    rst.lil 10h\n", "printImageDot:\n    ld a,'.'\n    rst.lil 10h\n    call wp_loading_present\n")
   s=once(s,"    call w3d_audio_mark_sample_buffer_loaded\n    ld a,'.'\n    rst.lil 10h\n", "    call w3d_audio_mark_sample_buffer_loaded\n    ld a,'.'\n    rst.lil 10h\n    call wp_loading_present\n")
   s=once(s,'    call wp_run\n    jp w3d_gameplay_exit_shutdown', '    call wp_loading_ready\n    call wp_run\n    jp w3d_gameplay_exit_shutdown')
   (src/'wolf3d.asm').write_text(s+PROGRESS)
   if backend=='bespoke':
    f=src/'bench.inc';s=f.read_text();s=once(s,'    call w3d_mark_full_level_dirty\n    call wp_warm_frame\n', '''    call w3d_mark_full_level_dirty
    ; Bind the actual resident tilemap before the first draw. Dirty replay
    ; alone never emits INIT_LEVEL and leaves the native map ID at zero.
    call w3d_submit_level_reset
    jp c,wp_failed
    call wp_a_wait
    jp c,wp_failed
    call w3d_vdu_present
    call wp_a_fence
    jp c,wp_failed
''');f.write_text(s)
   sources[backend+'/'+mode]={str(f.relative_to(src)):sha(f)for f in sorted(src.rglob('*'))if f.is_file()}
 # Fab visual-only A: exact corrected producer, no Xtensa diagnostic CCOUNT API.
 old=out/'bespoke/paced';dst=out/'fab-bespoke/paced';shutil.copytree(old,dst)
 f=dst/'source/bench.inc';s=f.read_text();s=once(s,'    call wp_a_create_log\n    jp c,wp_failed\n','');s=once(s,'    call wp_a_reset\n    jp c,wp_failed\n','')
 start=s.index('    ; Read the native diagnostic log only AFTER all timing has stopped.');end=s.index('    ld a,1\n    ld (wp_status),a',start)
 s=s[:start]+s[end:]
 start=s.index('    ld hl,wp_clear_log\n');end=s.index('    ld hl,0\n    add hl,sp\n    ld (wp_exit_sp),hl',start)
 s=s[:start]+s[end:];f.write_text(s)
 (out/'source-freeze.json').write_text(json.dumps({'revision':'r06','sources':sources,'changes':'A first warm-up INIT_LEVEL+full dirty replay; both loading-dot callbacks present/fence outside timing; FabA diagnostic dump disabled only in named visual variant'},indent=2)+'\n')
def build():
 out=HERE/'build/r06';record={};assembler=ROOT/'src/asm/wolf3d/tgt/.tools/ez80asm';assert assembler.is_file()
 assert 'ez80asm version' in subprocess.check_output([str(assembler),'-v'],text=True)
 for backend in ('bespoke','vdplet','fab-bespoke'):
  for mode in (('paced',)if backend=='fab-bespoke'else('cpu','unpaced','paced')):
   dst=out/backend/mode;src=dst/'source';payload=dst/'payload'
   with (dst/'assemble.log').open('w')as log:subprocess.run([str(assembler),'wolf3d.asm','r06.bin','-l','-c'],cwd=src,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=True)
   shutil.copyfile(src/'r06.bin',payload/'wolf3d.bin');assert 0x40000+(payload/'wolf3d.bin').stat().st_size<0xa0000
   files={str(f.relative_to(payload)):{'bytes':f.stat().st_size,'sha256':sha(f)}for f in sorted(payload.rglob('*'))if f.is_file()and f.name!='expected.json'}
   (payload/'expected.json').write_text(json.dumps({'schema':'wolf-perf003-payload-r06','backend':backend,'mode':mode,'files':files},indent=2)+'\n');record[backend+'/'+mode]=files
 (out/'guest-build.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS seven r06 guest assemblies')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','build'));a=p.parse_args();prepare()if a.action=='prepare'else build()
