"""Freeze task-owned inputs without compiling, running or changing a donor."""
from pathlib import Path
import argparse, hashlib, json, shutil, struct, subprocess, sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BESPOKE = Path('/Agon/mystuff/agon-vdp-wolf3d')
VDPLET = Path('/Agon/mystuff/agon-vdplet')
NATIVE = VDPLET / 'build/vdpl022-text96-r01/firmware-text96'
SDK = NATIVE.parent/'sdk'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(path):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()
    return {'path': str(path), 'commit': git('rev-parse', 'HEAD'),
            'branch': git('branch', '--show-current'),
            'dirty': git('status', '--porcelain')}


def prepare(revision):
    if not revision.isalnum():
        raise ValueError('revision must be alphanumeric')
    out = HERE / 'build' / revision
    out.mkdir(parents=True, exist_ok=False)
    sources = out / 'inputs'
    bindings = {}

    def copy(source, relative):
        target = sources / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        bindings[str(relative)] = {'origin': str(source), 'bytes': source.stat().st_size,
                                  'sha256': sha(source)}
        if sha(target) != bindings[str(relative)]['sha256']:
            raise ValueError('snapshot changed during copy: ' + str(source))

    groups = [('game', ROOT / 'src/asm/wolf3d/src'),
              ('module', ROOT / 'agonport/vdplet/production'),
              ('bespoke/video', BESPOKE / 'video'),
              ('runtime/video', NATIVE / 'firmware-src/video'),
              ('sdk/include', SDK / 'include')]
    for label, directory in groups:
        for source in sorted(directory.rglob('*')):
            if source.is_file() and source.suffix in ('.asm', '.inc', '.cpp', '.h', '.ino') and 'build' not in source.relative_to(directory).parts:
                copy(source, Path(label) / source.relative_to(directory))
    for source, relative in [
        (ROOT/'agonport/vdplet/wolf3d_tables.inc', 'wolf3d_tables.inc'),
        (BESPOKE/'platformio.ini', 'bespoke/platformio.ini'),
        (NATIVE/'firmware-src/platformio.ini', 'runtime/platformio.ini'),
        (NATIVE/'firmware-source.json', 'runtime/firmware-source.json'),
        (NATIVE.parent/'sdk-source.json', 'sdk-source.json'),
        (SDK/'tools/build_module.py', 'sdk/tools/build_module.py'),
        (SDK/'tools/module.exports', 'sdk/tools/module.exports'),
        (SDK/'src/vdplet_policy.h', 'sdk/src/vdplet_policy.h'),
        (HERE.parent/'WOLF-PERF-001/src/bench.inc', 'donor/bench.inc'),
        (HERE.parent/'WOLF-PERF-001/build.py', 'donor/build.py'),
        (ROOT/'src/asm/wolf3d/scripts/build.py', 'game-builder.py')]:
        copy(source, Path(relative))

    sys.path.insert(0, str(ROOT/'agonport/tools/wolf3d_assets'))
    from formats.level_package import LevelPackage, parse_package, build_package
    assets = ROOT/'agonport/assets/generated/wolf3d'
    payload = out/'common-payload'
    payload.mkdir()
    for filename, relative in [('hud.agnb','hud/hud.agnb'), ('sfx.agnb','audio/sfx.agnb'), ('shell.agnb','shell/shell.agnb'), ('level_00/tiles.agnb','levels/level_00/tiles.agnb'), ('level_00/sprites.agnb','levels/level_00/sprites.agnb')]:
        target=payload/filename; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(assets/relative,target)
    levels={}
    for difficulty in ('baby','easy','medium','hard'):
        source=assets/f'levels/level_00/state_{difficulty}.w3l'
        original=parse_package(source.read_bytes())
        if original.sections['tilemap'][36*64+34] != 0:
            raise ValueError('fixture tile is not open')
        sections=dict(original.sections); sections['actors']=b''
        new=LevelPackage(level=original.level,difficulty=original.difficulty,
                         door_count=original.door_count,static_count=original.static_count,
                         actor_count=0,random_index=0,
                         player_pose=struct.pack('<iiH',0x228000,0x248000,0),sections=sections)
        target=payload/'level_00'/source.name;target.write_bytes(build_package(new))
        parsed=parse_package(target.read_bytes())
        assert parsed.actor_count==0 and parsed.sections['actors']==b''
        for key,value in original.sections.items():
            if key!='actors':assert parsed.sections[key]==value
        levels[difficulty]={'source_sha256':sha(source),'fixture_sha256':sha(target),
                            'doors':parsed.door_count,'statics':parsed.static_count}
    (payload/'wolf3d.cfg').write_bytes(b'')
    poses=[{'index':n,'angle':720*n//600%360,'x':0x228000,'y':0x248000}
           for n in range(601)]
    (out/'poses.json').write_text(json.dumps(poses,indent=2)+'\n')
    (out/'angles.inc').write_text(''.join('    dw '+str(p['angle'])+'\n' for p in poses[1:]))
    record={'schema':'wolf-perf003-inputs-v1','revision':revision,
            'plan_commit':'5599f43','repositories':{'game':identity(ROOT),
            'bespoke':identity(BESPOKE),'vdplet':identity(VDPLET)},
            'bindings':bindings,'levels':levels,'poses_sha256':sha(out/'poses.json'),
            'payload':{str(p.relative_to(payload)):{'bytes':p.stat().st_size,'sha256':sha(p)}
                       for p in sorted(payload.rglob('*')) if p.is_file()},
            'timing_note':'Current native source and SDK are prospective; owner compatibility reply and generated diagnostics/build receipts precede execution.'}
    (out/'inputs.json').write_text(json.dumps(record,indent=2)+'\n')
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision',required=True)
    print(prepare(parser.parse_args().revision))
