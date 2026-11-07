"""Owned serial private Fab builds and two fixed source-bridge visual fixtures."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,shutil,subprocess,time
ROOT=Path.home()/'Agon/mystuff/Wolf3dOrig';T=ROOT/'agonport/doc/tasks/WOLF-PERF-007';B=T/'build/visual02'
PROFILE=ROOT/'.emulator/wolf-perf007-visual01'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main(lease):
    receipt=dict(passed=False,steps=[]);begin=time.monotonic();child=None
    def own():
        subprocess.run(['ssh','-o','BatchMode=yes','raspberrypi','/Agon/mystuff/agon-dev-env/.venv/bin/python','/Agon/mystuff/agon-dev-env/cross-agent/vdplet-rollout/oryx_lease.py','assert-owner','--owner','wolf3dorig','--lease',lease],check=True,timeout=20,stdout=subprocess.DEVNULL)
    try:
        for n,d in json.loads((B/'dispatch-inputs.json').read_text()).items():assert sha(B/n)==d,n
        for path,d in json.loads((B/'runtime-pins.json').read_text()).items():assert sha(path)==d,path
        assert not PROFILE.exists();PROFILE.mkdir()
        runner=load('retained',B/'retained_runner.py');setup=load('setup',Path.home()/'Agon/mystuff/agon-dev-env/scripts/setup_emulator.py')
        for arm in ('original','candidate'):
            own();bridge=B/arm/'bridge'
            build=load('build_'+arm,bridge/'build.py');build.main(lease)
            receipt['steps'].append(dict(arm=arm,build=json.loads((bridge/'build-result.json').read_text())))
            own();profile=PROFILE/arm
            sd=setup.link_shared_runtime(profile,Path.home()/'Agon/mystuff/golem/.emulator/runtime/fab-1.2.5')
            shutil.copyfile(bridge/'vdp_wolf_fab.so',profile/'vdp_wolf_fab.so');(profile/'.bespoke-vdp-profile').write_text('vdp_wolf_fab.so\n');setup.write_profile_launcher(profile,strict_bespoke=True)
            payload=B/arm/'payload';expected=json.loads((payload/'expected.json').read_text())['files']
            for n,item in expected.items():assert sha(payload/n)==item['sha256'],n
            shutil.copytree(payload,sd/'wolf3d');(sd/'autoexec.txt').write_bytes(b'SET KEYBOARD 1\r\ncd /wolf3d\r\nrunbin ./wolf3d.bin\r\n')
            shutil.copyfile(B/'input.so',profile/'input.so')
            files=[profile/n for n in ('fab-agon-emulator','fab-agon-emulator.bin','vdp_wolf_fab.so','mos_platform.bin','mos_platform.map','input.so','sdcard/autoexec.txt')]+list((sd/'wolf3d').rglob('*'))
            manifest={str(p.relative_to(profile)):sha(p) for p in files if p.is_file()};(profile/'inputs.json').write_text(json.dumps(manifest,indent=2)+'\n');(profile/'.runtime.sha256').write_text(''.join(d+'  '+n+'\n' for n,d in manifest.items()))
            own();runner.PROFILE=profile;runner.run(False)
            result=json.loads((profile/'run/result.json').read_text());receipt['steps'].append(dict(arm=arm,run=result));assert result['success'],result.get('error')
            assert result['returncode']==0,'Unexpected frontend exit status'
        receipt['passed']=True
    finally:
        receipt['seconds']=time.monotonic()-begin;(B/'cohort-result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('PASS two fixed Fab fixtures; source execution only, no ESP32 timing')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--lease',required=True);main(p.parse_args().lease)
