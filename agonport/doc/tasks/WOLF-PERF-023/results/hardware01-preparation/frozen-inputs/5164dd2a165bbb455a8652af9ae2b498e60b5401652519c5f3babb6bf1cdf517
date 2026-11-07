"""File-only final target admission/provider/flag/resource checks."""
from pathlib import Path
import hashlib,json,re,struct
T=Path(__file__).resolve().parent;B=T/'build/r01'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    out={'passed':False,'arms':{}};commands={}
    for arm,opt in [('original','-O2'),('candidate','-O2')]:
        a=B/arm;manifest=json.loads((a/'module/wolf_perf.json').read_text());m=manifest['module'];raw=(a/'module/wolf_perf.vdpl').read_bytes()
        assert sha(a/'module/wolf_perf.vdpl')==m['sha256'] and len(raw)==m['package_bytes']==int.from_bytes(raw[8:12],'little')
        assert m['capabilities']==257 and (m['abi_major'],m['abi_minor'])==(1,6)
        assert m['compiler_target']['psram_cache_workaround'] and m['resident_text_bytes']<=65536 and m['resident_data_bytes']<=16384 and len(raw)<=131072
        args=json.loads((a/'module/tool-commands.json').read_text());compile=args[0]
        assert opt in compile and sum(x in ('-Os','-O2') for x in compile)==1
        for flag in ('-mfix-esp32-psram-cache-issue','-fPIC','-mlongcalls','-mtext-section-literals','-fno-builtin','-ffp-contract=off','-fstack-usage','-fno-common','-std=c++17','-fno-exceptions','-fno-rtti','-fno-threadsafe-statics'):assert flag in compile,flag
        assert not any(x in compile for x in ('-Ofast','-ffast-math','-mno-fix-esp32-psram-cache-issue'))
        assert not any(x in ('-lm','-lgcc') for argv in args for x in argv)
        commands[arm]=[[x.replace(str(a),'$ARM').replace(opt,'$OPT') for x in argv] for argv in args]
        symbols=(B/(arm+'-symbols.log')).read_text()
        for name in ('__divdi3','_ZL10divide_u64yy','memcpy','memset','vdplet_entry'):assert re.search(r'\b'+name+r'$',symbols,re.M),name
        assert not re.search(r'^\s+U\s',symbols,re.M),'Undefined provider/import'
        stack=[]
        for p in (a/'module').glob('*.su'):
            for line in p.read_text().splitlines():
                f=line.rsplit('\t',2)
                if len(f)==3:
                    n=int(f[1]);assert 0<n<=2048 and f[2]=='static',line
                    stack.append(dict(function=f[0],bytes=n,kind=f[2]))
        assert stack
        # Final dynamic exports must remain the one admitted entry; local helpers
        # are retained native definitions rather than inferred host providers.
        readelf=(a/'module/wolf_perf.readelf.txt').read_text()
        assert '.rela.dyn' in readelf and 'R_XTENSA_RELATIVE' in readelf
        out['arms'][arm]=dict(optimization=opt,package=m,commands=args,stack=stack,max_individual_stack_bytes=max(x['bytes'] for x in stack),unused_unsigned_helper_retained=bool(re.search(r'\b__udivdi3$',symbols,re.M)),symbols_sha256=sha(B/(arm+'-symbols.log')),disassembly_sha256=sha(B/(arm+'-disassembly.log')))
    assert commands['original']==commands['candidate'],'Tool argv differ beyond arm paths'
    assert out['arms']['original']['package']['sha256']=='8d3d19bb74e1f2ea862b2154c038dfd23de2fd741fd1831d1880d849b5ad838b'
    raw=(B/'candidate/module/wolf_perf.elf').read_bytes()
    assert raw[:6]==b'\x7fELF\x01\x01','Actual Xtensa file is not ELF32 little-endian'
    dis=(B/'candidate-disassembly.log').read_text()
    parts=re.split(r'^\s*([0-9a-f]+) <([^\n]+)>:\n',dis,flags=re.M)
    functions={parts[i+1]:dict(address=parts[i],body=parts[i+2]) for i in range(1,len(parts),3)}
    narrow=[(name,f)for name,f in functions.items()if name.startswith('divide_u64(')]
    assert len(narrow)==1
    name,f=narrow[0];assert len(re.findall(r'\bquou\b',f['body']))==1,'Actual narrow divide is not one unsigned32 QUOU'
    assert not re.search(r'\b(?:call[0-9]*|callx[0-9]*)\b',f['body']),'Divider recursively calls another helper'
    native_binding=json.loads((B/'native-body-binding.json').read_text());assert native_binding['passed'] and native_binding['fallback_and_signed_wrapper_equal']
    out['narrow_lowering']=dict(name=name,address=f['address'],unsigned_quou_count=1,no_calls_in_actual_divider=True,elf32_little_endian=True,source_binding=native_binding,limits='Native machine-code/provider inspection plus independent execution of exact native C++ bodies on host; not execution of full64 domain on Xtensa.')
    out['passed']=True;out['limits']='Source/target flags/providers/sections and individual static frames; not execution of excluded native helpers, whole-call stack, physical pixels or timing. Actual generated pixel/counter loops require retained disassembly review.'
    (B/'code-result.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS actual same-policy flags/provider/sections/static-stack/package checks')
if __name__=='__main__':main()
