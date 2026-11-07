"""Verify the real MOS read/upload/VDPL LOAD producer against its module."""
from pathlib import Path
import hashlib,json,re
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def equ(source,name):
    matches=re.findall(r'(?m)^'+re.escape(name)+r':\s+equ (\d+)\s*$',source)
    assert len(matches)==1,(name,matches)
    return int(matches[0])

def verify(binding):
    module=Path(binding['module']);blob=module.read_bytes();size=len(blob)
    assert sha(module)==binding['module_sha256']
    assert int.from_bytes(blob[8:12],'little')==size
    assert binding['package_bytes']==size and binding['package_limit']==size+1
    source=Path(binding['source']);length=equ((source/'wolf3d_vdplet_package.inc').read_text(),'W3D_VDPLET_PACKAGE_BYTES')
    limit=equ((source/'wolf3d_vdplet_client.inc').read_text(),'W3D_VDPLET_PACKAGE_LIMIT')
    assert length==size and limit==size+1,'Actual producer length/strict-limit differs from selected module'
    client=(source/'wolf3d_vdplet_client.inc').read_text()
    assert re.search(r'ld hl,W3D_VDPLET_PACKAGE_BYTES\s*\n\s*ld \(@package_bytes\),hl',client)
    assert re.search(r'xor a\s*\n\s*ld \(@package_bytes\+3\),a',client)
    listing=Path(binding['listing']).read_text();binary=Path(binding['guest']).read_bytes();operands=[]
    pattern=r'^([0-9A-F]{6}) ((?:[0-9A-F]{2} ){0,5}[0-9A-F]{2})\s+\d+\*?\s+ld (hl|bc|de),(W3D_VDPLET_PACKAGE_BYTES|W3D_VDPLET_PACKAGE_LIMIT)\b'
    for match in re.finditer(pattern,listing,re.M):
        address=int(match[1],16);value=limit if match[4].endswith('LIMIT') else length
        encoded=bytes([{'hl':0x21,'bc':0x01,'de':0x11}[match[3]]])+value.to_bytes(3,'little')
        assert bytes.fromhex(match[2])==encoded
        assert binary[address-0x40000:address-0x40000+4]==encoded
        operands.append(dict(address=address,register=match[3],symbol=match[4],value=value,encoded=encoded.hex()))
    assert len(operands)==6 and sum(x['symbol'].endswith('LIMIT') for x in operands)==1
    assert sorted(x['register'] for x in operands)==['bc','de','de','hl','hl','hl']
    stack={}
    for label in ('wp_entry_sp','wp_exit_sp'):
        m=re.search(r'^([0-9A-F]{6})[^\n]*\b'+label+r':',listing,re.M);assert m
        stack[label]=int(m[1],16);assert 0x40000<=stack[label]<0xa0000
    return dict(passed=True,package_bytes=size,guest_sha256=sha(binding['guest']),listing_sha256=sha(binding['listing']),operands=operands,stack_labels=stack)

