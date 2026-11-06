"""New r07 copies: authoritative loading stage/count drawn on both pages."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def prepare():
 out=HERE/'build/r07';out.mkdir(exist_ok=False)
 for backend in ('bespoke','vdplet','fab-bespoke'):
  for mode in (('paced',)if backend=='fab-bespoke'else('cpu','unpaced','paced')):
   old=HERE/'build/r06'/backend/mode;dst=out/backend/mode
   shutil.copytree(old/'source',dst/'source',ignore=shutil.ignore_patterns('*.bin','*.lst','*.log'))
   shutil.copytree(old/'payload',dst/'payload')
   p=dst/'source/wolf3d.asm';s=p.read_text();start=s.index('\n; Setup-only: make the game\'s finalized-asset dot visible');s=s[:start]+'\n    include "loading_pages.inc"\n'
   s=once(s,"printImageDot:\n    ld a,'.'\n    rst.lil 10h\n    call wp_loading_present\n    xor a\n    ret",'printImageDot:\n    jp wp_loading_tick')
   s=once(s,"    call w3d_audio_mark_sample_buffer_loaded\n    ld a,'.'\n    rst.lil 10h\n    call wp_loading_present\n    xor a\n    ret",'    call w3d_audio_mark_sample_buffer_loaded\n    jp wp_loading_tick')
   s=once(s,'    call printImageDot\n    call w3d_music_service','    call printImageDot\n    ret nz ; failed page update aborts loader\n    call w3d_music_service')
   s=once(s,'printAudioDotAndPollEscape:\n    call printAudioDot\n','printAudioDotAndPollEscape:\n    call printAudioDot\n    ret nz ; failed page update aborts loader\n')
   for key,stage in [('loading_shell_msg','shell'),('loading_sfx_msg','sfx'),('loading_msg','tiles'),('loading_sprites_msg','sprites'),('loading_hud_msg','hud')]:
    a='    ld hl,'+key+'\n    call printString\n    call printNewLine\n'
    s=once(s,a,a+'    ld hl,wp_stage_'+stage+'\n    call wp_loading_begin\n')
   p.write_text(s);ui=(HERE/'loading_pages.inc').read_text()
   if backend=='fab-bespoke':ui=ui.replace('WP_LOADING_PAGE_PROOF: equ 0','WP_LOADING_PAGE_PROOF: equ 1')
   (dst/'source/loading_pages.inc').write_text(ui)
 (out/'source-freeze.json').write_text(json.dumps({str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and 'source'in p.parts},indent=2)+'\n')
def build():
 out=HERE/'build/r07';assembler=ROOT/'src/asm/wolf3d/tgt/.tools/ez80asm';record={}
 for backend in ('bespoke','vdplet','fab-bespoke'):
  for mode in (('paced',)if backend=='fab-bespoke'else('cpu','unpaced','paced')):
   d=out/backend/mode;p=d/'payload'
   with(d/'assemble.log').open('w')as log:subprocess.run([str(assembler),'wolf3d.asm','r07.bin','-l','-c'],cwd=d/'source',stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
   shutil.copyfile(d/'source/r07.bin',p/'wolf3d.bin');assert 0x40000+(p/'wolf3d.bin').stat().st_size<0xa0000
   files={str(f.relative_to(p)):{'bytes':f.stat().st_size,'sha256':sha(f)}for f in p.rglob('*')if f.is_file()and f.name!='expected.json'}
   (p/'expected.json').write_text(json.dumps({'schema':'wolf-perf003-payload-r07','backend':backend,'mode':mode,'files':files},indent=2)+'\n');record[backend+'/'+mode]=files
 (out/'guest-build.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS seven r07 assemblies')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','build'));a=p.parse_args();prepare()if a.action=='prepare'else build()
