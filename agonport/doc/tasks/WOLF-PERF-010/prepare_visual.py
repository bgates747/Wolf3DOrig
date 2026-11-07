"""Static Fab derivative: retain Arthur reply bindings, reuse real abort body."""
from pathlib import Path
import hashlib,json,shutil
import prepare
T=Path(__file__).resolve().parent;B=T/'build/visual02';Q=T.parent/'WOLF-PERF-007/build/visual02/candidate'
def main():
    B.mkdir(exist_ok=False);source=B/'source'
    shutil.copytree(Q/'guest/source',source,ignore=shutil.ignore_patterns('*.bin','*.lst','*.log'))
    p=source/'wolf3d.asm';s=p.read_text();assert s.count('WP_MODE: equ 3')==1;p.write_text(s.replace('WP_MODE: equ 3','WP_MODE: equ 1'))
    # This exact hardware control already defines wp_settle_display and log.
    shutil.copyfile(T.parent/'WOLF-PERF-009/build/guests01/original/control/source/bench.inc',source/'bench.inc')
    prepare.label(source)
    p=source/'loading_pages.inc';s=p.read_text();assert s.count('WP_LOADING_PAGE_PROOF: equ 0')==1;p.write_text(s.replace('WP_LOADING_PAGE_PROOF: equ 0','WP_LOADING_PAGE_PROOF: equ 1'))
    shutil.copytree(Q/'payload',B/'payload');(B/'payload/expected.json').unlink();(B/'payload/wolf3d.bin').unlink()
    shutil.copyfile(Q/'bridge/vdp_wolf_fab.so',B/'vdp_wolf_fab.so');shutil.copyfile(T.parent/'WOLF-PERF-007/build/visual02/input.so',B/'input.so')
    files=[p for p in B.rglob('*')if p.is_file()]+list(T.glob('*.py'))+[T/'VISUAL-PLAN.md']
    (B/'inputs.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in files},indent=2)+'\n')
if __name__=='__main__':main()
