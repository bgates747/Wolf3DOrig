#!/usr/bin/env python3
"""One bounded headless profile invocation. Caller asserts the live Oryx lease."""
from pathlib import Path
import argparse,json,os,signal,subprocess,time,hashlib,struct
from analyze import analyze

def main():
 p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('--timeout',type=int,default=300);p.add_argument('--capture',action='store_true');p.add_argument('--expect-abort',action='store_true');p.add_argument('--engine',choices=('jit','interp'),default='jit');a=p.parse_args();profile=a.profile.resolve();app=profile/'sdcard/wolf3d';run=profile/'run'
 if run.exists():raise ValueError('fresh output required')
 for n in ('timing.bin','native.bin'):
  if (app/n).exists():raise ValueError('prior result exists')
 subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=profile,check=True)
 run.mkdir();events=run/'events.txt';events.write_text('');env=dict(os.environ);env.pop('BASH_ENV',None)
 env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',LD_PRELOAD=str(profile/'input.so'),W3V_REVIEW_EVENTS=str(events),W3V_REVIEW_VDP=str(profile/'flexe-vdp.so'),AGON_FLEXE_ENGINE=a.engine)
 next_capture=0;captures=[]
 began=time.monotonic();report={'success':False,'scope':'headless emulator only','engine':a.engine};proc=None
 with (run/'frontend.log').open('w') as log:
  try:
   proc=subprocess.Popen(['./flexe-agon-emulator'],cwd=profile,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   while True:
    if proc.poll() is not None:raise RuntimeError('unexpected frontend exit')
    if a.capture and time.monotonic()-began>=next_capture:
     shot=run/f'frame-{len(captures):03d}.ppm'
     with events.open('a')as events_file:events_file.write('capture '+str(shot)+'\n');events_file.flush()
     captures.append({'file':shot.name,'host_seconds':time.monotonic()-began});next_capture=time.monotonic()-began+1
    uart=profile/'last-run/esp32-uart0.log';text=uart.read_text(errors='replace') if uart.exists() else ''
    if 'RST $38 panic' in text:raise RuntimeError('guest panic')
    if 'WOLF-PERF-003 FAILED' in text:
     if a.expect_abort and 'WOLF-PERF-003 FAILED TIMER-RESTORED' in text:break
     raise RuntimeError('guest failed')
    if (app/'timing.bin').exists() and 'Thanks for playing Wolf3DOrig!' in text and '/wolf3d *' in text:break
    if time.monotonic()-began>a.timeout:raise TimeoutError('guest completion/MOS return timeout')
    time.sleep(.2)
   shutil_results=[]
   for n in ('timing.bin','native.bin'):
    if (app/n).exists():(run/n).write_bytes((app/n).read_bytes());shutil_results.append(n)
   if a.expect_abort:
    if 'WOLF-PERF-003 FAILED TIMER-RESTORED' not in text:raise ValueError('expected owned-timer abort not reached')
    guest={'control':'intentional abort after PRT initialization','timer_restoration_verified':True,'performance_result':False}
   else:guest=analyze(run)
   with events.open('a') as f:f.write('quit\n');f.flush()
   proc.wait(timeout=20)
   if proc.returncode:raise RuntimeError(f'frontend exit {proc.returncode}')
   stats=json.loads((profile/'last-run/stats.json').read_text())
   if stats.get('failed') or any(stats.get(k,0) for k in ('unhandled','unregistered','unmapped')):raise ValueError('backend fault counters')
   # Exact counter names differ by backend; preserve the whole object.
   report.update(success=True,captures=captures,capture_perturbs_emulator_timing=a.capture,guest=guest,stats=stats,returncode=proc.returncode,results=shutil_results)
  except Exception as e:report['error']=str(e);raise
  finally:
   if proc and proc.poll() is None:
    with events.open('a') as f:f.write('quit\n');f.flush()
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
   report['whole_process_seconds']=time.monotonic()-began
   (run/'runner.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
