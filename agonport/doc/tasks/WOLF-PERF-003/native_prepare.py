"""Prepare private diagnostic firmware projects with frozen local libraries."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
from instrument import standalone_native,vdplet_native
HERE=Path(__file__).resolve().parent
DONORS={
 'bespoke':Path('/Agon/mystuff/agon-vdp-wolf3d'),
 'vdplet':Path('/Agon/mystuff/agon-vdplet/build/vdpl022-text96-r01/firmware-text96/firmware-src')}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(revision,attempt):
    base=HERE/'build'/revision;manifest=json.loads((base/'inputs.json').read_text());records={}
    for backend,input_name in [('bespoke','bespoke'),('vdplet','runtime')]:
        source=base/'inputs'/input_name
        for relative,item in manifest['bindings'].items():
            if relative.startswith(input_name+'/'):
                assert sha(base/'inputs'/relative)==item['sha256'],relative
        project=base/attempt/backend
        shutil.copytree(source,project)
        if backend=='bespoke':standalone_native(project/'video/wolf3d.h')
        else:vdplet_native(project/'video/vdplet_runtime.h')
        donor=DONORS[backend]/'.pio/libdeps/esp32dev'
        dependencies={}
        for name in ('vdp-gl','CRC','ESP32Time'):
            dest=project/'deps'/name
            shutil.copytree(donor/name,dest,ignore=shutil.ignore_patterns('.git','__pycache__','.DS_Store'))
            files={str(p.relative_to(dest)):sha(p)for p in sorted(dest.rglob('*'))if p.is_file()}
            dependencies[name]={'source':str(donor/name),'files':files}
        dependencies['vdp-gl']['git_commit']=subprocess.check_output(['git','-C',str(donor/'vdp-gl'),'rev-parse','HEAD'],text=True).strip()
        assert dependencies['vdp-gl']['git_commit']=='ac2dd5986daf496c43ae8e7fe41836274aec54a0'
        # Use the frozen private lib_dir; no floating dependency resolution or
        # edits to another project's dependency cache are required.
        config=(project/'platformio.ini').read_text()
        config,n=re.subn(r'(?ms)^lib_deps\s*=.*?(?=^build_unflags\s*=)', '',config);assert n==1
        config=config.replace('src_dir = video','src_dir = video\nlib_dir = deps')
        (project/'platformio.ini').write_text(config)
        records[backend]={'project':str(project),'dependencies':dependencies,
                          'files':{str(p.relative_to(project)):sha(p)for p in sorted(project.rglob('*'))if p.is_file()},
                          'timing':'A: render through final drain, before reply; B: fully received command through invoke return, before reply; module logs renderer and row scope separately',
                          'compiler_policy':'unchanged O2 firmware and classic ESP32 PSRAM safeguard; module remains safe Os/PIC'}
    (base/(attempt+'-inputs.json')).write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps({name:{'project':item['project'],'source_files':len(item['files']),'graphics':item['dependencies']['vdp-gl']['git_commit']}for name,item in records.items()},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--revision',required=True);p.add_argument('--attempt',required=True);a=p.parse_args();prepare(a.revision,a.attempt)
