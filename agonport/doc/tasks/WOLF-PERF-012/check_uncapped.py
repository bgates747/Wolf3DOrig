"""Qualify the already assembled guest; no reassembly or failed-result rewrite."""
from pathlib import Path
import hashlib
import importlib.util
import json

T=Path(__file__).resolve().parent;B=T/'build/guest01'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    first=json.loads((B/'receipt.json').read_text())
    assert not first['passed'] and first['producer']['passed']
    g=json.loads((B/'binding.json').read_text())
    spec=importlib.util.spec_from_file_location('producer',T.parent/'WOLF-PERF-009/guest_binding.py')
    binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding)
    actual=binding.verify(g)
    assert actual['guest_sha256']==first['producer']['guest_sha256']
    bench=(B/'source/bench.inc').read_text()
    loop=bench.split('wp_next:',1)[1].split('jp c,wp_next',1)[0]
    assert loop.startswith('\n    ld hl,(wp_n)\n    inc hl\n')
    assert 'call wp_clock' not in loop and '@pace' not in loop
    assert loop.count('call w3d_vdu_present')==1
    assert loop.index('call w3d_vdplet_wait_run')<loop.index('call w3d_vdu_present')<loop.index('ld (ix+21),hl')
    assert (B/'source/wolf3d.asm').read_text().count('WP_MODE: equ 4')==1
    import re
    listing=Path(g['listing']).read_text();raw=Path(g['guest']).read_bytes()
    for name in ('w3d_vdu_present','w3d_audio_wait_for_vdp_ingress'):
        target=int(re.search(r'^([0-9A-F]{6})[^\n]*\b'+name+r':',listing,re.M)[1],16)
        matches=list(re.finditer(r'^([0-9A-F]{6}) ((?:[0-9A-F]{2} ){3}[0-9A-F]{2})\s+\d+\*?\s+call '+name+r'\b',listing,re.M))
        assert matches
        for m in matches:
            at=int(m[1],16)-0x40000
            assert raw[at:at+4]==bytes.fromhex(m[2])==bytes([0xcd])+target.to_bytes(3,'little')
    result=dict(passed=True,mode=4,producer=actual,bench_sha256=sha(B/'source/bench.inc'),
        loop_pacing_removed=True,per_frame_presentation_retained=True,
        first_check_disposition='Assembly and producer passed; first gate incorrectly included legitimate final clock stamp after loop. Original failed receipt/script preserved; no reassembly.',
        first_receipt_sha256=sha(B/'receipt.json'))
    (T/'CHECK-RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
