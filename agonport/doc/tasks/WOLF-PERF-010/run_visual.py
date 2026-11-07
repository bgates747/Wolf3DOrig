"""One owned headless Fab run; no build, target timing or hardware access."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,shutil,signal,subprocess,time
ROOT=Path.home()/'Agon/mystuff/Wolf3dOrig';T=ROOT/'agonport/doc/tasks/WOLF-PERF-010';B=T/'build/visual01';PROFILE=ROOT/'.emulator/wolf-perf010-caption01'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(lease):
    for n,d in json.loads((B/'dispatch.json').read_text()).items():assert sha(B/n)==d,n
    assert Path('/sys/devices/system/cpu/cpufreq/boost').read_text().strip()=='0'
    assert not PROFILE.exists();PROFILE.mkdir()
    path=Path.home()/'Agon/mystuff/agon-dev-env/scripts/setup_emulator.py';spec=importlib.util.spec_from_file_location('setup',path);setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
    sd=setup.link_shared_runtime(PROFILE,Path.home()/'Agon/mystuff/golem/.emulator/runtime/fab-1.2.5')
    shutil.copyfile(B/'vdp_wolf_fab.so',PROFILE/'vdp_wolf_fab.so');(PROFILE/'.bespoke-vdp-profile').write_text('vdp_wolf_fab.so\n');setup.write_profile_launcher(PROFILE,strict_bespoke=True)
    shutil.copyfile(B/'input.so',PROFILE/'input.so');shutil.copytree(B/'payload',sd/'wolf3d');(sd/'autoexec.txt').write_bytes(b'SET KEYBOARD 1\r\ncd /wolf3d\r\nrunbin ./wolf3d.bin\r\n')
    inputs={str(p.relative_to(PROFILE)):sha(p)for p in PROFILE.rglob('*')if p.is_file()};(PROFILE/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n');(PROFILE/'.runtime.sha256').write_text(''.join(d+'  '+n+'\n'for n,d in inputs.items()))
    subprocess.run(['ssh','-o','BatchMode=yes','raspberrypi','/Agon/mystuff/agon-dev-env/.venv/bin/python','/Agon/mystuff/agon-dev-env/cross-agent/vdplet-rollout/oryx_lease.py','assert-owner','--owner','wolf3dorig','--lease',lease],check=True,timeout=20,stdout=subprocess.DEVNULL)
    out=PROFILE/'run';out.mkdir();events=out/'events.txt';events.write_text('');begin=time.monotonic();child=None;guards=[];captures=[];result={'passed':False,'scope':'Static timer caption Fab source-bridge pixels only; no Xtensa/timing proof'}
    env=dict(os.environ)
    for k in ('BASH_ENV','LD_LIBRARY_PATH','FLEXE_UART_OBSERVER_OUTPUT','FLEXE_TX_OBSERVER_OUTPUT','FLEXE_TX_BATCH_OBSERVER_OUTPUT'):env.pop(k,None)
    env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',LD_PRELOAD=str(PROFILE/'input.so'),W3V_REVIEW_EVENTS=str(events),W3V_REVIEW_VDP=str(PROFILE/'vdp_wolf_fab.so'),WOLF_FAB_BRIDGE_REPORT=str(out/'bridge.json'))
    with (out/'frontend.log').open('x') as log:
        try:
            child=subprocess.Popen(['./fab-agon-emulator'],cwd=PROFILE,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            nextcap=0;nextguard=0;done=None
            while time.monotonic()-begin<300:
                elapsed=time.monotonic()-begin
                if child.poll() is not None:raise RuntimeError('Unexpected frontend exit')
                if elapsed>=nextguard:
                    temps=[]
                    for n in Path('/sys/class/hwmon').glob('*/name'):
                        if n.read_text().strip()=='k10temp':
                            for q in n.parent.glob('temp*_label'):
                                if q.read_text().strip()=='Tctl':temps.append(int(q.with_name(q.name.replace('_label','_input')).read_text())/1000)
                    mem=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))
                    guards.append(dict(seconds=elapsed,cpu_c=temps,available_kib=mem));assert len(temps)==1 and temps[0]<80 and mem>=524288;nextguard=elapsed+1
                if elapsed>=nextcap:
                    name=f'frame-{len(captures):04d}.ppm'
                    with events.open('a')as f:f.write('capture '+str(out/name)+'\n')
                    captures.append(dict(file=name,seconds=elapsed));nextcap=elapsed+.25
                # Control intentionally has no timing.bin. Loading trace is saved
                # on ordinary shutdown; allow two seconds for final mode cleanup.
                f=sd/'wolf3d/loading3.bin'
                if f.exists() and f.stat().st_size>32:
                    if done is None:done=elapsed
                    if elapsed-done>=2:result['passed']=True;break
                time.sleep(.1)
            else:raise TimeoutError('Static control did not return in300s')
        except Exception as error:result['error']=repr(error)
        finally:
            if child is not None and child.poll() is None:
                with events.open('a')as f:f.write('capture '+str(out/'final.ppm')+'\nquit\n')
                try:child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGTERM)
                    try:child.wait(timeout=5)
                    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
            result.update(seconds=time.monotonic()-begin,returncode=None if child is None else child.returncode,captures=captures)
            if (out/'bridge.json').exists():result['bridge']=json.loads((out/'bridge.json').read_text())
            (out/'guards.json').write_text(json.dumps(guards,indent=2)+'\n');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));assert result['passed'] and result['returncode']==0
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--lease',required=True);main(p.parse_args().lease)
