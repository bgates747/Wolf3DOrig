"""One asset-loading-only Fab trial; no matched rendering/performance claim."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,shutil,signal,subprocess,time
ROOT=Path.home()/'Agon/mystuff/Wolf3dOrig';HERE=ROOT/'agonport/doc/tasks/WOLF-PERF-003';PROFILE=ROOT/'.emulator/wolf-perf003-fab-r06a';PAYLOAD=HERE/'build/r07/fab-bespoke/paced/payload'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare():
 assert not PROFILE.exists()
 spec=importlib.util.spec_from_file_location('setup',Path.home()/'Agon/mystuff/agon-dev-env/scripts/setup_emulator.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 sd=m.link_shared_runtime(PROFILE,Path.home()/'Agon/mystuff/golem/.emulator/runtime/fab-1.2.5')
 so=Path('/tmp/wolf-perf003-fab-vdp.so');assert sha(so)=='5c4e4b9bf6b58ade665b1d19f87697b54d08113a0962b3fe946bf899a1d49e2f'
 shutil.copyfile(so,PROFILE/'vdp_wolf3d.so');(PROFILE/'.bespoke-vdp-profile').write_text('vdp_wolf3d.so\n');m.write_profile_launcher(PROFILE,strict_bespoke=True)
 payload=PAYLOAD;e=json.loads((payload/'expected.json').read_text())
 for n,d in e['files'].items():assert sha(payload/n)==d['sha256'],n
 shutil.copytree(payload,sd/'wolf3d');(sd/'autoexec.txt').write_bytes(b'SET KEYBOARD 1\r\ncd /wolf3d\r\nrunbin ./wolf3d.bin\r\n')
 shutil.copyfile(ROOT/'.emulator/vdplet-rows-review/review-input.so',PROFILE/'input.so')
 files=[PROFILE/n for n in ('fab-agon-emulator','fab-agon-emulator.bin','vdp_wolf3d.so','mos_platform.bin','mos_platform.map','input.so','sdcard/autoexec.txt')]+list((sd/'wolf3d').rglob('*'))
 manifest={str(p.relative_to(PROFILE)):sha(p)for p in files if p.is_file()};(PROFILE/'inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (PROFILE/'.runtime.sha256').write_text(''.join(d+'  '+n+'\n'for n,d in manifest.items()))
 print(json.dumps({'profile':str(PROFILE),'inputs':manifest},indent=2))
def run(visible=False):
 for n,d in json.loads((PROFILE/'inputs.json').read_text()).items():assert sha(PROFILE/n)==d,n
 assert Path('/sys/devices/system/cpu/cpufreq/boost').read_text().strip()=='0'
 out=PROFILE/'run';out.mkdir(exist_ok=False);events=out/'events.txt';events.write_text('');began=time.monotonic();proc=None;guards=[];captures=[];nextcapture=0;report={'success':False,'scope':'Fab visual correction check; native CCOUNT collection disabled; no performance claim','timeout_seconds':300,'boost':0}
 env=dict(os.environ)
 for k in ('BASH_ENV','LD_LIBRARY_PATH','FLEXE_UART_OBSERVER_OUTPUT','FLEXE_TX_OBSERVER_OUTPUT','FLEXE_TX_BATCH_OBSERVER_OUTPUT'):env.pop(k,None)
 env.pop('SDL_VIDEODRIVER',None);env.pop('SDL_AUDIODRIVER',None)
 if not visible:env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
 env.update(LD_PRELOAD=str(PROFILE/'input.so'),W3V_REVIEW_EVENTS=str(events),W3V_REVIEW_VDP=str(PROFILE/(PROFILE/'.bespoke-vdp-profile').read_text().strip()),WOLF_FAB_BRIDGE_REPORT=str(out/'bridge.json'))
 def guard():
  temps=[]
  for n in Path('/sys/class/hwmon').glob('*/name'):
   if n.read_text().strip()=='k10temp':
    for l in n.parent.glob('temp*_label'):
     if l.read_text().strip()=='Tctl':temps.append(int(l.with_name(l.name.replace('_label','_input')).read_text())/1000)
  mem=int(next(l.split()[1]for l in Path('/proc/meminfo').read_text().splitlines()if l.startswith('MemAvailable:')))
  guards.append(dict(seconds=time.monotonic()-began,cpu_c=temps,available_kib=mem))
  if len(temps)!=1 or temps[0]>=80 or mem<524288:raise RuntimeError('host thermal/RAM guard')
 with (out/'frontend.log').open('w')as log:
  try:
   guard();proc=subprocess.Popen(['./fab-agon-emulator'],cwd=PROFILE,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);nextguard=0
   while time.monotonic()-began<300:
    if proc.poll()is not None:raise RuntimeError('unexpected Fab exit')
    if time.monotonic()>=nextguard:guard();nextguard=time.monotonic()+1
    if time.monotonic()-began>=nextcapture:
     image=out/f'frame-{len(captures):03d}.ppm'
     with events.open('a')as f:f.write('capture '+str(image)+'\n')
     captures.append({'file':image.name,'seconds':time.monotonic()-began});nextcapture=time.monotonic()-began+1
    before=PROFILE/'sdcard/wolf3d/timing.bin'
    if before.exists()and before.stat().st_size==16233 and (PROFILE/'sdcard/wolf3d/after.bin').exists():
     raw=before.read_bytes();assert raw[:5]==b'WPF3\1'and raw[6:8]==b'\1\1';assert int.from_bytes(raw[8:11],'little')==600
     report.update(success=True,completed_poses=600,seconds_to_boundary=time.monotonic()-began,before_bytes=before.stat().st_size,before_sha256=sha(before));shutil.copyfile(before,out/'timing.bin');break
    time.sleep(.2)
   else:raise TimeoutError('corrected visual fixture not completed in300s')
   with events.open('a')as f:f.write('capture '+str(out/'final.ppm')+'\n')
   time.sleep(.5)
  except Exception as e:report['error']=str(e)
  finally:
   if proc and proc.poll()is None:
    with events.open('a')as f:f.write('capture '+str(out/'final.ppm')+'\nquit\n')
    try:proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
     os.killpg(proc.pid,signal.SIGTERM)
     try:proc.wait(timeout=5)
     except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
   bridge=out/'bridge.json'
   if bridge.exists():
    details=json.loads(bridge.read_text());report['bridge']=details
    if not(details['loads']==details['unloads']==1 and details['renders']==602 and not any(details[k]for k in ('errors','residual_cleanup','loaded','busy','frame'))):report.update(success=False,error='native source bridge lifecycle/counters')
   elif report.get('success') and (PROFILE/'.bespoke-vdp-profile').read_text().strip()=='vdp_wolf_fab.so':report.update(success=False,error='missing bridge report')
   report.update(captures=captures,whole_seconds=time.monotonic()-began,returncode=None if proc is None else proc.returncode)
   (out/'host-guards.json').write_text(json.dumps(guards,indent=2)+'\n');(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--profile',type=Path);p.add_argument('--visible',action='store_true');p.add_argument('--payload',type=Path);a=p.parse_args()
 if a.profile:PROFILE=a.profile.resolve()
 if a.payload:PAYLOAD=a.payload.resolve()
 prepare()if a.action=='prepare'else run(a.visible)
