"""Exercise actual loading04 invoke with device-free serial/keyboard doubles."""
from pathlib import Path
import importlib.util,tempfile,unittest
T=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('loading04',T/'hardware/physical04.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Serial:
 def __init__(self):self.pending=[];self.after_run=False;self.completed=False
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self,n):
  if not self.pending:return b''
  data=self.pending.pop(0)
  if b'FINAL-MOS'in data:self.completed=True
  return data
class Fake(m.Bench):
 def own(self):pass
 def exit(self,*args):pass
 def service(self,*args):assert self.serial.completed,'No listener before true post-RUN return'
 def line(self,folder,label,text):
  prompt=self.remote.encode()+b' *'
  if label=='start-cue':self.serial.pending.append(b'MARKER')
  elif label in ('cd','load'):self.serial.pending.append(prompt)
  elif label=='run':
   self.serial.after_run=True
   self.serial.pending.extend([self.banner,b'FINAL-MOS '+prompt])
class Controller(unittest.TestCase):
 def test_success_and_setup_failure_wait_for_return(self):
  for banner in (b'Thanks for playing Wolf3DOrig!',b'AGNB texture load failed; render not submitted.'):
   with tempfile.TemporaryDirectory()as name:
    b=object.__new__(Fake);b.remote='/test/wolf/perf003/load04';b.port='NO-DEVICE';b.banner=banner;b.serial=Serial()
    m.q.m.open_passive_serial=lambda *a,**k:b.serial
    b.invoke(Path(name),'a-loading04.bin','MARKER');self.assertTrue(b.serial.completed)
 def test_benchmark_path_refused(self):
  with tempfile.TemporaryDirectory()as name:
   b=object.__new__(Fake);b.remote='/test/wolf/perf003/load04';b.port='NO-DEVICE';b.banner=b'WOLF-PERF-003 FAILED';b.serial=Serial()
   m.q.m.open_passive_serial=lambda *a,**k:b.serial
   with self.assertRaises(RuntimeError):b.invoke(Path(name),'a-loading04.bin','MARKER')
if __name__=='__main__':unittest.main()
