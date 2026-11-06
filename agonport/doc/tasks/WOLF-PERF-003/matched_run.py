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
 for key in ('FLEXE_UART_OBSERVER_OUTPUT','FLEXE_TX_OBSERVER_OUTPUT','FLEXE_TX_BATCH_OBSERVER_OUTPUT','LD_LIBRARY_PATH'):env.pop(key,None)
 subprocess.run(['sha256sum','--check','--status',str(Path(__file__).resolve().parent/'build/q03/dependencies.sha256')],check=True)
 env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',LD_PRELOAD=str(profile/'input.so'),W3V_REVIEW_EVENTS=str(events),W3V_REVIEW_VDP=str(profile/'flexe-vdp.so'),AGON_FLEXE_ENGINE=a.engine)
 next_capture=0;captures=[]
 next_guard=0;guard_rows=[]
 began=time.monotonic();report={'success':False,'scope':'headless emulator only','engine':a.engine};proc=None
 with (run/'frontend.log').open('w') as log:
  try:
   def host_guard():
    values=[]
    for sensor in Path('/sys/class/hwmon').glob('*/name'):
     if sensor.read_text().strip()=='k10temp':
      for label in sensor.parent.glob('temp*_label'):
       if label.read_text().strip()=='Tctl':values.append(int(label.with_name(label.name.replace('_label','_input')).read_text())/1000)
    mem=int(next(line.split()[1]for line in Path('/proc/meminfo').read_text().splitlines()if line.startswith('MemAvailable:')))
    row={'host_seconds':time.monotonic()-began,'cpu_c':values,'available_kib':mem};guard_rows.append(row)
    if len(values)!=1 or max(values)>=80 or mem<512*1024:raise RuntimeError('host thermal/RAM guard')
   host_guard()
   proc=subprocess.Popen(['./flexe-agon-emulator'],cwd=profile,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   while True:
    if proc.poll() is not None:raise RuntimeError('unexpected frontend exit')
    if time.monotonic()-began>=next_guard:host_guard();next_guard=time.monotonic()-began+1
    if a.capture and time.monotonic()-began>=next_capture:
     shot=run/f'frame-{len(captures):03d}.ppm'
     with events.open('a')as events_file:events_file.write('capture '+str(shot)+'\n');events_file.flush()
     captures.append({'file':shot.name,'host_seconds':time.monotonic()-began});next_capture=time.monotonic()-began+1
    uart=profile/'last-run/esp32-uart0.log';text=uart.read_text(errors='replace') if uart.exists() else ''
    if 'RST $38 panic' in text:raise RuntimeError('guest panic')
    if 'WOLF-PERF-003 FAILED' in text:
     if a.expect_abort:
      if all(s in text for s in ('WOLF-PERF-003 FAILED TIMER-RESTORED','WOLF-PERF-003 CONTROL REGISTERS-RESTORED RETURN','Thanks for playing Wolf3DOrig!','/wolf3d *')):break
     else:raise RuntimeError('guest failed')
     if time.monotonic()-began>a.timeout:raise TimeoutError('restored-control MOS return timeout')
     time.sleep(.2);continue
    if (app/'timing.bin').exists() and 'Thanks for playing Wolf3DOrig!' in text and '/wolf3d *' in text:break
    if time.monotonic()-began>a.timeout:raise TimeoutError('guest completion/MOS return timeout')
    time.sleep(.2)
   shutil_results=[]
   for n in ('timing.bin','native.bin'):
    if (app/n).exists():(run/n).write_bytes((app/n).read_bytes());shutil_results.append(n)
   if a.expect_abort:
    if 'WOLF-PERF-003 FAILED TIMER-RESTORED' not in text:raise ValueError('expected owned-timer abort not reached')
    guest={'control':'intentional abort after PRT initialization','timer_restoration_verified':True,'register_restoration_verified':True,'actual_mos_return':True,'performance_result':False}
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
   (run/'host-guards.json').write_text(json.dumps(guard_rows,indent=2)+'\n')
   (run/'runner.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
