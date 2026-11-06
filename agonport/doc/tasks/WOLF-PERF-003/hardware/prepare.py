"""Prepare identified P3DR A transport and all physical inputs; never executes."""
from pathlib import Path
import hashlib,json,shutil
TASK=Path(__file__).resolve().parents[1]
OUT=TASK/'build/hardware01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def change(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)
def binding(source):
    p=source/'wolf3d_render_async.inc';s=p.read_text()
    assert s.count("cp 'W'")==3
    s=s.replace("cp 'W'", "cp 'P'") # ISR capture plus render/fizzle foreground validators.
    p.write_text(s)
    p=source/'standalone.inc';s=p.read_text()
    s=change(s,"    cp 'W'\n", "    cp 'P'\n")
    s=change(s,"    cp 'T'\n    jr nz,@other\n", "    cp 'R'\n    jr nz,@other\n    ld a,(ix+5)\n    and 0feh\n    cp 080h\n    jr nz,@other\n")
    s=change(s,'    ldir\n    ld a,1\n    ld (wp_a_ready),a', '    ldir\n    ld a,(wp_a_reply+5)\n    and 1\n    ld (wp_a_reply+5),a\n    ld a,1\n    ld (wp_a_ready),a')
    p.write_text(s)
def negative(source):
    p=source/'bench.inc';s=p.read_text()
    s=change(s,'    call wp_prt_init\n','    call wp_prt_init\n    ld a,1\n    ld (wp_expected_abort),a\n    jp wp_failed ; selected owned-timer restoration control\n')
    donor=(TASK/'build/controls01-r02/bespoke/source/bench.inc').read_text()
    begin=donor.index('    ; Only the selected direct failure returns.')
    end=donor.index('wp_clear_log:',begin)
    s=change(s,'@hold: jr @hold\n',donor[begin:end])
    p.write_text(s)
OUT.mkdir(exist_ok=False)
native=OUT/'native-a'
shutil.copytree(TASK/'build/r04/native02/bespoke',native,ignore=shutil.ignore_patterns('build.log'))
p=native/'video/wolf3d.h';s=p.read_text()
s=change(s,"'W', '3', 'D', 'R',", "'P', '3', 'D', 'R',")
s=change(s,"{'W','3','D','T',1,uint8_t(ok),", "{'P','3','D','R',1,uint8_t(0x80|uint8_t(ok)),")
p.write_text(s)
for backend in ('bespoke','vdplet'):
    for mode in ('cpu','unpaced','paced','control'):
        donor=TASK/'build/r07'/backend/('cpu' if mode=='control' else mode)
        dest=OUT/backend/mode
        shutil.copytree(donor/'source',dest/'source',ignore=shutil.ignore_patterns('*.bin','*.lst'))
        shutil.copytree(donor/'payload',dest/'payload')
        if backend=='bespoke':binding(dest/'source')
        if mode=='control':negative(dest/'source')
# Preserve exact source changes and artifact origins separately from build output.
manifest={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and '.pio' not in p.parts and p.suffix not in ('.bin','.elf','.map','.log','.lst')}
(OUT/'source-freeze.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Prepared hardware01; no compiler, emulator or device invoked.')
