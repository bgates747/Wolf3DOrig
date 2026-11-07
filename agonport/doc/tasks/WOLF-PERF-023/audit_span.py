"""Inspect the completed exact Xtensa packages; no compiler or target I/O."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re

T = Path(__file__).resolve().parent
B = T/'build/r01'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def loops(arm):
    text = (B/(arm+'-disassembly.log')).read_text()
    chunks = re.split(r'^\s*([0-9a-f]+) <([^\n]+)>:\n',text,flags=re.M)
    matches = [(chunks[i],chunks[i+1],chunks[i+2]) for i in range(1,len(chunks),3)
               if '::fill_span(' in chunks[i+1]]
    assert len(matches)==1
    address,name,body = matches[0]
    rows=[]
    for line in body.splitlines():
        m=re.match(r'^\s*([0-9a-f]+):\s+[0-9a-f]+\s+([a-z0-9.]+)\s*(.*)$',line)
        if m: rows.append(dict(address=int(m[1],16),opcode=m[2],operands=m[3]))
    result=[]
    for end,row in enumerate(rows):
        if row['opcode']!='bnez': continue
        dest=int(re.search(r',\s*([0-9a-f]+)\s+<',row['operands'])[1],16)
        if dest>=row['address']: continue
        starts=[i for i,x in enumerate(rows) if x['address']==dest]
        assert len(starts)==1
        result.append(rows[starts[0]:end+1])
    assert not re.search(r'\b(?:call[0-9]*|callx[0-9]*)\b',body)
    assert rows[0]['opcode']=='entry' and rows[0]['operands']=='a1, 32'
    return dict(address=address,name=name,loops=result,individual_frame_bytes=32,
                disassembly_sha256=sha(B/(arm+'-disassembly.log')))


def main():
    receipt=json.loads((B/'build-receipt.json').read_text());assert receipt['passed']
    original=loops('original');candidate=loops('candidate')
    assert len(original['loops'])==2 and len(candidate['loops'])==3
    ops=lambda loop:[x['opcode'] for x in loop]
    linear=['s8i','memw','addi.n','addi.n','bnez']
    assert ops(original['loops'][0])==ops(candidate['loops'][0])==linear
    scalar=Counter(['xor','add.n','addi.n','l8ui','and','or','s8i','memw','addi.n','bnez'])
    assert Counter(ops(original['loops'][1]))==Counter(ops(candidate['loops'][2]))==scalar
    fast=['l8ui','and','or','s8i','memw','addi.n','addi.n','bnez']
    assert ops(candidate['loops'][1])==fast
    assert sha(B/'original/module/wolf_perf.vdpl')=='8d3d19bb74e1f2ea862b2154c038dfd23de2fd741fd1831d1880d849b5ad838b'
    assert sha(B/'candidate/module/wolf_perf.vdpl')=='b181a8fdba5b0e0791359593e95169a99ad732e369cbb9442be1e4046baed1d4'
    result=dict(passed=True,original=original,candidate=candidate,
        admitted_pixel_loop_instructions=dict(original=10,candidate=8),
        byte_read_store_and_poststore_memw_retained=True,
        unchanged_linear_and_scalar_fallback_opcode_counts=True,
        no_calls_in_actual_span=True,no_wider_fast_path_access=True,
        limits='Static emitted instruction accounting, not executed cycles or physical eligibility/hitcount. Private target calls are positive-count; source count0 early return is separately tested on host, not claimed as an executed zero-call Xtensa path. Valid original row storage and exclusive lease remain required.')
    (B/'byte-loop-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS actual byte loops:10 to8 instructions; one l8ui/s8i/memw,32B frame, unchanged scalar/linear policy; no timing claim')


if __name__=='__main__':main()
