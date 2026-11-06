"""One bounded FX-152 observation; caller asserts its fresh Oryx lease."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,signal,subprocess,time

HERE=Path(__file__).resolve().parent
READER=HERE/'build/s01/read_record.py'
READER_SHA='c5701735631da1b1cf5bc74874bfef4da1c4cd50118809f8cd2d80c90e0fa85b'

def main():
 p=argparse.ArgumentParser();p.add_argument('profile',type=Path);a=p.parse_args()
 profile=a.profile.resolve();assert profile.parent.name=='wolf-perf003-s01'
 assert hashlib.sha256(READER.read_bytes()).hexdigest()==READER_SHA
 spec=importlib.util.spec_from_file_location('fx152_reader',READER);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
 subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=profile,check=True)
 run=profile/'run';run.mkdir(exist_ok=False);events=run/'events.txt';events.write_text('');observation=run/'tx-observer.jsonl'
 env=dict(os.environ);env.pop('BASH_ENV',None);env.pop('FLEXE_UART_OBSERVER_OUTPUT',None)
 env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',LD_PRELOAD=str(profile/'input.so'),W3V_REVIEW_EVENTS=str(events),W3V_REVIEW_VDP=str(profile/'flexe-vdp.so'),AGON_FLEXE_ENGINE='jit',FLEXE_TX_OBSERVER_OUTPUT=str(observation))
 began=time.monotonic();proc=None;error=None;report={'schema':'wolf-perf003-stall-probe-v1','diagnostic_only':True,'performance_result':False,'outcome':None}
 def quit_owned():
  if proc is None or proc.poll() is not None:return
  with events.open('a')as f:f.write('quit\n');f.flush()
  try:proc.wait(timeout=10)
  except subprocess.TimeoutExpired:
   report['termination_fallback']=True;os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
 with (run/'frontend.log').open('w')as log:
  try:
   proc=subprocess.Popen(['./flexe-agon-emulator'],cwd=profile,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   while True:
    if proc.poll() is not None:raise RuntimeError('unexpected frontend exit')
    if observation.exists():
     if observation.stat().st_size>20480:raise ValueError('observer output exceeds20KiB')
     raw=observation.read_bytes()
     if raw.endswith(b'\n'):
      parsed=reader.analyze(raw)
      if parsed['finalized']:
       report['observer_before_quit']=parsed
       if parsed['final_reason']!='stasis_window_observed':raise RuntimeError('observer finalized without complete stasis samples')
       report['outcome']='stall_window_recorded';break
    uart=profile/'last-run/esp32-uart0.log';text=uart.read_text(errors='replace')if uart.exists()else''
    if 'RST $38 panic' in text or 'WOLF-PERF-003 FAILED' in text:raise RuntimeError('guest panic/failure')
    if (profile/'sdcard/wolf3d/timing.bin').exists()and'Thanks for playing Wolf3DOrig!'in text and'/wolf3d *'in text:
     report['outcome']='guest_completed_without_stall';break
    if time.monotonic()-began>300:raise TimeoutError('300-second outer diagnostic bound')
    time.sleep(.2)
  except Exception as e:error=e;report.update(outcome='unexpected_failure',error=str(e))
  finally:
   quit_owned();report['whole_process_seconds']=time.monotonic()-began
   report['returncode']=proc.returncode if proc is not None else None
   try:
    report['observer']=reader.analyze(observation.read_bytes())
    stats=json.loads((profile/'last-run/stats.json').read_text());report['stats']=stats
    if stats.get('failed')or any(stats.get(k,0)for k in ('unhandled','unregistered','unmapped')):raise ValueError('backend faults')
    if report['returncode']!=0 or report.get('termination_fallback'):raise ValueError('normal Quit/join required')
   except Exception as e:
    if error is None:error=e
    report['finalization_error']=str(e)
   (run/'probe.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
 if error is not None:raise error

if __name__=='__main__':main()
