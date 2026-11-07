"""Finite actual-assembly staging/layout checks; requires normal Pi compiler lease."""
from pathlib import Path
import importlib.util
import argparse
import json
import shutil
import subprocess
import sys
import tempfile

T = Path(__file__).resolve().parent
ROOT = T.parents[3]
spec = importlib.util.spec_from_file_location('builder', ROOT/'src/asm/wolf3d/scripts/build.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

def main(revision='storage03'):
    assert revision in ('storage03','storage04')
    out = T/'build'/revision
    out.mkdir(exist_ok=False)
    module=ROOT/'agonport/doc/tasks/WOLF-PERF-021/results/build01/candidate/module/wolf_perf.vdpl'
    assembler=b.resolve_assembler(None)
    results=[]
    for backend,profile,native in [('standalone',False,False),('standalone',True,False),
                                  ('vdplet-direct',False,False),('vdplet-direct',True,False),
                                  ('vdplet-direct',True,True)]:
        receipt=b.build(assembler,backend,module if backend=='vdplet-direct' else None,
                        profile=profile,profile_native=native)
        binary=ROOT/receipt['output']
        name=backend+('-pn' if native else '-p' if profile else '-off')
        folder=out/name; folder.mkdir()
        for file in (binary,binary.with_suffix('.lst'),binary.with_suffix('.json')):
            shutil.copyfile(file,folder/file.name)
        if backend=='standalone' and not profile:
            assert receipt['sha256']=='063f7ab7b9b2df44fe1541871662ce7656c3c28d6693872de824c5bfce40a2e6'
        if backend=='vdplet-direct':
            assert receipt['module']['sha256']=='8d3d19bb74e1f2ea862b2154c038dfd23de2fd741fd1831d1880d849b5ad838b'
        results.append(receipt)
    subprocess.run([sys.executable,str(T/'build_hardware_guest.py'),'--revision','hardware-guest03'],check=True,timeout=120)
    spec=importlib.util.spec_from_file_location('qualifier',T/'qualify_guest.py')
    q=importlib.util.module_from_spec(spec); spec.loader.exec_module(q)
    binding=json.loads((T/'build/hardware-guest03/receipt.json').read_text())
    binding['source']=str(Path(binding['guest']).parent)
    qualified=q.verify(binding)
    # Actual old artifact must fail for its missing owned storage.
    old=T/'build/hardware-guest02/source'
    try:
        b.verify_package_storage(old/'profile.bin',old/'wolf3d.lst',22572)
    except AssertionError as error:
        assert 'Missing owned package storage' in str(error)
    else:
        raise AssertionError('Old executable overlap admitted')
    # Actual emitted MOS LOAD address must point to owned storage, not060000.
    raw=bytearray(Path(binding['guest']).read_bytes())
    operand=binding['package_storage']['operands'][0]['address']-0x40000
    raw[operand+1:operand+4]=(0x60000).to_bytes(3,'little')
    with tempfile.TemporaryDirectory() as directory:
        bad=Path(directory)/'wrong.bin';bad.write_bytes(raw)
        try:
            b.verify_package_storage(bad,Path(binding['listing']),22572)
        except AssertionError as error:
            assert 'Binary package address mismatch' in str(error)
        else:
            raise AssertionError('Unsafe emitted package destination admitted')
        # The same existing helper always writes a4096-byte zero page, even
        # for smaller module packages. Exercise actual tiny-package assembly.
        tiny=out/'tiny-package-layout'; shutil.copytree(b.SOURCE,tiny)
        b.select_backend(tiny/'wolf3d_backend.inc','vdplet-direct')
        b.select_package(tiny/'wolf3d_vdplet_package.inc',1)
        subprocess.run([str(assembler),'wolf3d.asm','tiny.bin','-l','-c'],
                       cwd=tiny,check=True,timeout=120)
        small=b.verify_package_storage(tiny/'tiny.bin',tiny/'wolf3d.lst',1)
        assert small['bytes']==4096 and small['package_bytes']==1
    result=dict(passed=True,builds=results,guest=qualified,negative_controls=2)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,builds=len(results),guest_sha256=binding['guest_sha256'],storage=binding['package_storage'])))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--revision',default='storage03')
    main(parser.parse_args().revision)
