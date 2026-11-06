"""One bounded Oryx-only generic-player check, under caller-asserted lease."""
from pathlib import Path
import argparse,json,os,signal,subprocess,time
p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('--invalid',action='store_true');a=p.parse_args();profile=a.profile.resolve();run=profile/'run';run.mkdir(exist_ok=False)
subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=profile,check=True)
events=run/'events.txt';events.write_text('');env=dict(os.environ);env.pop('BASH_ENV',None)
env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',LD_PRELOAD=str(profile/'input.so'),W3V_REVIEW_EVENTS=str(events),W3V_REVIEW_VDP=str(profile/'flexe-vdp.so'),AGON_FLEXE_ENGINE='jit')
report={'success':False,'negative_control':a.invalid,'human_hearing':False};proc=None;start=time.monotonic()
with (run/'frontend.log').open('w') as log:
 try:
  proc=subprocess.Popen(['./flexe-agon-emulator'],cwd=profile,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  while True:
   if proc.poll() is not None:raise RuntimeError('Unexpected frontend exit')
   f=profile/'last-run/esp32-uart0.log';raw=f.read_bytes() if f.exists() else b''
   if b'RST $38 panic' in raw or b'Guru Meditation' in raw:raise RuntimeError('Guest fault')
   marker=b'PLAYWAV ERROR format; audio untouched' if a.invalid else b'PLAYWAV OK bytes='
   if marker in raw and b'/voice *' in raw[raw.index(marker):]:break
   if not a.invalid and b'PLAYWAV ERROR' in raw:raise RuntimeError('Audio utility failed')
   if time.monotonic()-start>300:raise TimeoutError('Bounded player/MOS completion')
   time.sleep(.1)
  if a.invalid:assert b'PLAYWAV PLAY OK' not in raw
  else:assert b'PLAYWAV PLAY OK' in raw
  with events.open('a') as f:f.write('quit\n')
  proc.wait(timeout=20);assert proc.returncode==0
  stats=json.loads((profile/'last-run/stats.json').read_text());assert not any(stats.get(k)for k in ('failed','unhandled','unregistered','unmapped'))
  (run/'uart.bin').write_bytes(raw);report.update(success=True,normal_mos_return=True,stats=stats)
 except Exception as e:report['error']=str(e);raise
 finally:
  if proc and proc.poll()is None:
   with events.open('a')as f:f.write('quit\n')
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10)
  report['whole_process_seconds']=time.monotonic()-start;(run/'runner.json').write_text(json.dumps(report,indent=2)+'\n')
