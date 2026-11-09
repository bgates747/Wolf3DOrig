"""Prepare immutable current-firmware runtime inputs locally; no host/device launch."""
from pathlib import Path
import hashlib,json,shutil,sys
T=Path(__file__).resolve().parent;ROOT=T.parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from wolf_firmware import release_files,PRODUCTION_MODULE_SHA,sha


def main():
    out=T/'build/runtime-inputs01';out.mkdir(parents=True,exist_ok=False)
    files=release_files()
    production=ROOT/'agonport/vdplet/production'
    for name in ('runtime_worker.py','runtime_supervisor.py'):shutil.copyfile(T/name,out/name)
    for name in ('production','qualification','backend','firmware'):(out/name).mkdir()
    shutil.copyfile(production/'qualify.py',out/'production/qualify.py')
    shutil.copyfile(production.parent/'qualification/target.py',out/'qualification/target.py')
    (out/'production/build').mkdir()
    module=production/'build/wolf3d_production.vdpl'
    assert sha(module)==PRODUCTION_MODULE_SHA
    shutil.copyfile(module,out/'production/build/wolf3d_production.vdpl')
    shutil.copytree(production/'build/target-fixture',out/'production/build/target-fixture')
    (out/'firmware/vdp.bin').write_bytes(files['firmware'])
    (out/'firmware/vdp.elf').write_bytes(files['elf'])
    emulator=ROOT.parent/'flexe-agon-emulator/docs/tasks'
    backend=emulator/'FX-224/oryx-results-r03/artifacts/flexe-vdp.so'
    assert sha(backend)=='d77a7305b5c180381e49a4922ffd5a8ea9f824fee29110d5a955f337a1c96f0d'
    shutil.copyfile(backend,out/'backend/flexe-vdp.so')
    shutil.copyfile(emulator/'FX-274/wolf-prod001-backend-closure-r01.json',out/'backend/closure.json')
    record=dict(schema=1,firmware=files['identity'],module_sha256=PRODUCTION_MODULE_SHA,
        files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    (out/'INPUTS.json').write_text(json.dumps(record,indent=2)+'\n')
    (T/'RUNTIME-INPUTS.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(prepared=True,files=len(record['files']),bytes=sum(p.stat().st_size for p in out.rglob('*') if p.is_file()),no_execution=True)))
if __name__=='__main__':main()
