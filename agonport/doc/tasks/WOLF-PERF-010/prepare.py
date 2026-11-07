"""Prepare new labeled fixtures without editing any measured historical input."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import caption

T = Path(__file__).resolve().parent
B = T / 'build/r01'
BASE = T.parent / 'WOLF-PERF-009/build/guests01'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def label(source):
    p = source / 'loading_pages.inc'
    old = p.read_text()
    needle = '    ld hl,wp_loading_hint\n    jp printString'
    assert old.count(needle) == 1
    new = old.replace(needle, '''    ld hl,wp_loading_hint
    call printString
    .if WP_MODE = 1
    call wp_static_caption_paint
    .endif
    ret''')
    # Preserve the unpaced machine code: the original tail jump stays intact.
    new = new.replace('    ld hl,wp_loading_hint\n    call printString\n    .if WP_MODE = 1\n',
        '    ld hl,wp_loading_hint\n    .if WP_MODE = 1\n    call printString\n')
    new = new.replace('    call wp_static_caption_paint\n    .endif\n    ret',
        '    call wp_static_caption_paint\n    ret\n    .else\n    jp printString\n    .endif')
    text = 'wp_loading_hint: db "Rotation starts after loading.",0'
    assert new.count(text) == 1
    new = new.replace(text, '''    .if WP_MODE = 1
wp_loading_hint: db "NO ROTATION EXPECTED - TIMER ABORT CHECK",0
    .else
''' + text + '''
    .endif''')
    new += '\n    .if WP_MODE = 1\n    include "static_caption.inc"\n    .endif\n'
    p.write_text(new)
    p = source / 'wolf3d.asm'
    main = p.read_text()
    needle = '@restore_screen:\n    call w3d_restore_original_screen_mode'
    assert main.count(needle) == 1
    p.write_text(main.replace(needle, '''@restore_screen:
    .if WP_MODE = 1
    call wp_static_caption_close
    .endif
    call w3d_restore_original_screen_mode'''))
    (source / 'static_caption.inc').write_text(caption.assembly())


def main():
    for name, digest in json.loads((T / 'SOURCE-PINS.json').read_text())['files'].items():
        assert sha(name) == digest, name
    B.mkdir(parents=True, exist_ok=False)
    for arm in ('original', 'candidate'):
        for mode in ('control', 'unpaced'):
            before = BASE / arm / mode / 'source'
            out = B / arm / mode / 'source'
            shutil.copytree(before, out, ignore=shutil.ignore_patterns('*.bin','*.lst','*.log'))
            label(out)
    raw = caption.pixels()
    (B / 'caption.rgba2222').write_bytes(raw)
    (B / 'caption.ppm').write_bytes(f'P6\n{caption.WIDTH} {caption.HEIGHT}\n255\n'.encode() +
        b''.join(bytes([255,255,255]) if x == 0xff else bytes(3) for x in raw))
    files = [p for p in B.rglob('*') if p.is_file()] + [p for p in T.iterdir() if p.is_file()]
    (B / 'inputs.json').write_text(json.dumps({str(p): sha(p) for p in files}, indent=2) + '\n')


if __name__ == '__main__':
    main()
