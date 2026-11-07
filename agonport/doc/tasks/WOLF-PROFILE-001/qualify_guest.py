"""Verify the real MOS read/upload/VDPL LOAD producer against its module."""
from pathlib import Path
import hashlib,json,re,importlib.util
_builder_path=Path(__file__).resolve().parents[4]/'src/asm/wolf3d/scripts/build.py'
_spec=importlib.util.spec_from_file_location('storage_builder',_builder_path)
_builder=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_builder)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def equ(source,name):
    matches=re.findall(r'(?m)^'+re.escape(name)+r':\s+equ ([0-9a-fA-F]+h?)\s*$',source)
    assert len(matches)==1,(name,matches)
    value=matches[0]
    return int(value[:-1],16) if value.endswith('h') else int(value)

def verify(binding):
    module=Path(binding['module']);blob=module.read_bytes();size=len(blob)
    assert sha(module)==binding['module_sha256']
    assert int.from_bytes(blob[8:12],'little')==size
    assert binding['package_bytes']==size and binding['package_limit']==0x20000
    source=Path(binding['source']);length=equ((source/'wolf3d_vdplet_package.inc').read_text(),'W3D_VDPLET_PACKAGE_BYTES')
    limit=equ((source/'wolf3d_vdplet_client.inc').read_text(),'W3D_VDPLET_PACKAGE_LIMIT')
    assert length==size and limit==0x20000 and size<limit,'Actual producer length/limit differs from selected normal client'
    client=(source/'wolf3d_vdplet_client.inc').read_text()
    assert re.search(r'ld hl,W3D_VDPLET_PACKAGE_BYTES\s*\n\s*ld \(@package_bytes\),hl',client)
    assert re.search(r'xor a\s*\n\s*ld \(@package_bytes\+3\),a',client)
    storage=_builder.verify_package_storage(Path(binding['guest']),Path(binding['listing']),size)
    assert storage==binding['package_storage'], 'Linked package storage identity'
    listing=Path(binding['listing']).read_text();binary=Path(binding['guest']).read_bytes();operands=[]
    pattern=r'^([0-9A-F]{6}) ((?:[0-9A-F]{2} ){0,5}[0-9A-F]{2})\s+\d+\*?\s+ld (hl|bc|de),(W3D_VDPLET_PACKAGE_BYTES|W3D_VDPLET_PACKAGE_LIMIT)\b'
    for match in re.finditer(pattern,listing,re.M):
        instruction_address=int(match[1],16);value=limit if match[4].endswith('LIMIT') else length
        encoded=bytes([{'hl':0x21,'bc':0x01,'de':0x11}[match[3]]])+value.to_bytes(3,'little')
        assert bytes.fromhex(match[2])==encoded
        assert binary[instruction_address-0x40000:instruction_address-0x40000+4]==encoded
        operands.append(dict(address=instruction_address,register=match[3],symbol=match[4],value=value,encoded=encoded.hex()))
    assert len(operands)==6 and sum(x['symbol'].endswith('LIMIT') for x in operands)==1
    assert sorted(x['register'] for x in operands)==['bc','de','de','hl','hl','hl']
    stack={}
    for label in ('wp_test_entry_sp','wp_test_exit_sp'):
        m=re.search(r'^([0-9A-F]{6})[^\n]*\b'+label+r':',listing,re.M);assert m
        stack[label]=int(m[1],16);assert 0x40000<=stack[label]<0xa0000
    asm=(source/'wolf3d.asm').read_text()
    backend=(source/'wolf3d_backend.inc').read_text()
    assert equ(backend,'W3D_PROFILE')==1 and equ(backend,'W3D_PROFILE_NATIVE')==1
    assert equ(asm,'WPT_FULL_GAME')==1 and equ(asm,'WPT_NATIVE_MOCK')==0
    assert equ(asm,'WPT_FRAMES')==250
    assert asm.count('call wp_hw_stack')==2
    # Check emitted VDU header, INFO operation, reply flag and field17.
    # Package operands and query-call counts alone missed operation0 in r01.
    packet=address(binding,'wp_hw_stack_packet')
    expected=bytes.fromhex('1700d808000104000001001100')
    assert binary[packet:packet+len(expected)]==expected, 'Actual INFO17 request encoding'
    assert 'call wp_test_hold' not in asm
    profile=(source/'wolf3d_profile.inc').read_text()
    assert 'call wp_test_hold' not in profile and 'wp_test_read16' not in profile
    motion=(source/'wolf3d_motion.inc').read_text()
    assert 'w3d_poll_keys:\n    call wp_test_steer\n' in motion, 'Missing held-key poll seam'
    poll=address(binding,'w3d_poll_keys');steer=address(binding,'wp_test_steer')+0x40000
    assert binary[poll:poll+4]==b'\xcd'+steer.to_bytes(3,'little'), 'Actual held-key poll seam'
    mask=address(binding,'w3d_keyboard_masks')+0x40000+3
    at=steer-0x40000
    assert binary[at:at+6]==b'\x21'+mask.to_bytes(3,'little')+b'\xcb\xce', 'Actual held-left latch'
    assert 'call w3d_run_gameplay_session' in (source/'selftest.inc').read_text()
    return dict(passed=True,package_bytes=size,package_storage=storage,guest_sha256=sha(binding['guest']),listing_sha256=sha(binding['listing']),operands=operands,stack_labels=stack)



def address(binding, name):
    listing=Path(binding['listing']).read_text()
    m=re.search(r'^([0-9A-F]{6})[^\n]*\b'+re.escape(name)+r':',listing,re.M)
    assert m, name
    return int(m[1],16)-0x40000


def check_return(binding, folder):
    """Compare actual resident state, independent DONE report and selected artifact."""
    folder=Path(folder)
    verify(binding)
    ram=(folder/'ram.bin').read_bytes()
    done=(folder/'DONE.BIN').read_bytes()
    assert len(ram)==Path(binding['guest']).stat().st_size
    assert len(done)==32 and done[:4]==b'WPT1'
    assert done[4:7]==bytes(3), ('status/ownership/buffer',done.hex())
    u24=lambda data,at:int.from_bytes(data[at:at+3],'little')
    assert u24(done,8)==250 and u24(done,20)==0
    a,b=u24(done,12),u24(done,16)
    assert a==b and 0xb0000<=a<0xc0000
    for label,value in (('wp_test_entry_sp',a),('wp_test_exit_sp',b),('wp_sequence',250),('wp_dropped',0)):
        assert u24(ram,address(binding,label))==value, label
    for label in ('wp_status','wp_owned','wp_count'):
        assert ram[address(binding,label)]==0, label
    assert done[7]==ram[address(binding,'wp_old_ctl')]
    assert not done[7]&0x41
    stacks=[int.from_bytes(done[n:n+4],'little')for n in (24,28)]
    assert all(512<=v<65536 for v in stacks), stacks
    report=address(binding,'wp_test_report')
    assert ram[report:report+32]==done
    return dict(passed=True,entry_sp=a,exit_sp=b,native_info17=stacks,
                timer_control_restored=done[7],records_expected=250,discarded=0)
