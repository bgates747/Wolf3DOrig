"""Record host interruption, then stop. No retry, target access or detach."""
from pathlib import Path
import json,os,signal,time,traceback
class HostInterrupted(BaseException):
 def __init__(self,signum):self.signum=signum;super().__init__(signum)
def write_once(path,value):
 with Path(path).open('x')as stream:
  json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
def install(folder):
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
 write_once(folder/'host-launch.json',dict(schema='wolf-host-launch-v1',epoch=time.time(),pid=os.getpid(),ppid=os.getppid(),signals=['SIGTERM','SIGINT','SIGHUP'],target_action=False,detached=False))
 def stopped(signum,frame):
  # Stop reentrant delivery while this same process exits, not during work.
  for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,signal.SIG_DFL)
  try:write_once(folder/'host-interruption.json',dict(schema='wolf-host-interruption-v1',epoch=time.time(),signal=signum,name=signal.Signals(signum).name,pid=os.getpid(),ppid=os.getppid(),sender_unknown=True,stack=traceback.format_stack(frame),continuation=False,replay=False))
  finally:raise HostInterrupted(signum)
 for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,stopped)
