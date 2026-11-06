"""Oryx only: prepare stopped, fail-closed, private matched Flexe profiles."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,subprocess
HOME=Path.home();ROOT=HOME/'Agon/mystuff/Wolf3dOrig';HERE=Path(__file__).resolve().parent
BASE=HOME/'Agon/mystuff/AgonArcade/.emulator/rally28-hz60-rows01-rows60'
FRONT=HOME/'Agon/mystuff/flexe-agon-emulator/build/fx153/oryx-one-build/result/target/x86_64-unknown-linux-gnu/release/flexe-agon-emulator'
FRONT_SHA='c987fafc9045dfeb862fc4b0252dab70845c25e87ff5961b80e85a9dcd1b7399'
PINS={'flexe-agon-emulator.bin':'7e7d0e1bc89af72bde7ffbd6c06446aaefda4d1803f89eb1faf3167307ee1e01','flexe-vdp.so':'0866265bd6f3d73ad572f31dc1bb954f308ed9a5d857efa9414d37e1ade13374'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def prepare(revision,native,cohort,name,failure_first=False):
    base=HERE/'build'/revision
    assert sha(FRONT)==FRONT_SHA
    receipt=json.loads((base/(native+'-build.json')).read_text())
    assert set(receipt)=={'bespoke','vdplet'} and all(item.get('returncode')==0 for item in receipt.values())
    for file,digest in PINS.items():assert sha(BASE/file)==digest,file
    out=ROOT/'.emulator'/('wolf-perf003-'+name);out.mkdir(parents=True,exist_ok=False)
    canonical=load('perf003_canonical',HOME/'Agon/mystuff/agon-dev-env/scripts/setup_emulator.py')
    executable=load('perf003_executable',HERE/'build/canonical/flexe_profile.py')
    sequence=[]
    if cohort=='qualify':
        for mode in ('cpu-fail','cpu','unpaced','paced'):
            sequence.extend((backend,mode)for backend in ('bespoke','vdplet'))
    else:
        for mode in ('cpu','unpaced','paced'):
            sequence.extend((backend,mode)for backend in ('bespoke','vdplet','vdplet','bespoke'))
    if failure_first:
        assert cohort=='qualify'
        sequence.remove(('vdplet','paced'));sequence.insert(0,('vdplet','paced'))
    records=[]
    for index,(backend,mode)in enumerate(sequence,1):
        profile=out/f'{index:02d}-{backend}-{mode}'
        sd=canonical.link_shared_runtime(profile,HOME/'Agon/mystuff/golem/.emulator/runtime/fab-1.2.5')
        canonical.replace_symlink(profile/'fab-agon-emulator.bin',FRONT)
        shutil.copyfile(BASE/'flexe-vdp.so',profile/'flexe-vdp.so')
        artifact=base/native/backend/'.pio/build/esp32dev'
        for file in ('firmware.bin','firmware.elf'):
            assert sha(artifact/file)==receipt[backend]['outputs'][file]['sha256']
            shutil.copyfile(artifact/file,profile/('esp32-'+file))
        (profile/'.bespoke-vdp-profile').write_text('flexe-vdp.so\n')
        payload=(HERE/'build/controls01-r02'/backend/'payload')if mode=='cpu-fail'else base/backend/mode/'payload';expected=json.loads((payload/'expected.json').read_text())
        assert expected['backend']==backend and expected['mode']==('cpu-fail-return'if mode=='cpu-fail'else mode)
        for relative,item in expected['files'].items():assert sha(payload/relative)==item['sha256']
        shutil.copytree(payload,sd/'wolf3d')
        (sd/'autoexec.txt').write_bytes(b'SET KEYBOARD 1\r\ncd /wolf3d\r\nrunbin ./wolf3d.bin\r\n')
        canonical.write_profile_launcher(profile,strict_bespoke=True)
        launcher=profile/'fab-agon-emulator';text=launcher.read_text()
        env='''
export AGON_FLEXE_FIRMWARE="$profile_dir/esp32-firmware.bin"
export AGON_FLEXE_ELF="$profile_dir/esp32-firmware.elf"
export AGON_FLEXE_ENGINE="${AGON_FLEXE_ENGINE:-jit}"
export AGON_FLEXE_ARTIFACTS="$profile_dir/last-run"
mkdir -p "$AGON_FLEXE_ARTIFACTS"
'''
        assert text.count('\nvdp_name=')==1
        launcher.write_text(text.replace('\nvdp_name=',env+'\nvdp_name=',1));launcher.chmod(0o755)
        canonical.name_flexe_profile(profile)
        executable.verify_profile_executables(profile/'flexe-agon-emulator',profile/'flexe-agon-emulator.bin')
        shutil.copyfile(ROOT/'.emulator/vdplet-rows-review/review-input.so',profile/'input.so')
        files=['flexe-agon-emulator','flexe-agon-emulator.bin','flexe-vdp.so','esp32-firmware.bin','esp32-firmware.elf','mos_platform.bin','mos_platform.map','sdcard/autoexec.txt','input.so']
        files.extend(str(p.relative_to(profile))for p in sorted((sd/'wolf3d').rglob('*'))if p.is_file())
        (profile/'.runtime.sha256').write_text(''.join(sha(profile/file)+'  '+file+'\n'for file in files))
        subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=profile,check=True)
        records.append({'index':index,'backend':backend,'mode':mode,'profile':str(profile),'capture':cohort=='qualify'and mode=='paced','expect_abort':mode=='cpu-fail','timeout':300,'stopped':True,'inputs':{file:sha(profile/file)for file in files}})
    (out/'profiles.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps({'cohort':cohort,'profiles':len(records),'manifest':str(out/'profiles.json')},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('revision','native','name'):p.add_argument('--'+arg,required=True)
    p.add_argument('--cohort',choices=('qualify','paired'),required=True);p.add_argument('--failure-first',action='store_true');a=p.parse_args()
    prepare(a.revision,a.native,a.cohort,a.name,a.failure_first)
