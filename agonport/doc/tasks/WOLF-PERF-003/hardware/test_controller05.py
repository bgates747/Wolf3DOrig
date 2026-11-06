"""Device-free actual prompt and full-sequence/first-failure dispatch checks."""
from pathlib import Path
import importlib.util,tempfile,unittest,json
T=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('physical05',T/'hardware/physical05.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Clock:
 def __init__(self):self.value=0
 def monotonic(self):self.value+=.1;return self.value
 def time(self):return self.monotonic()
class Serial:
 def __init__(self):self.pending=[];self.returned=False
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def read(self,n):
  if not self.pending:return b''
  r=self.pending.pop(0)
  if b'FINAL-RETURN'in r:self.returned=True
  return r
class Fake(m.Bench):
 def own(self):pass
 def exit(self,*a):pass
 def service(self,*a):assert self.s.returned
 def line(self,folder,label,text):
  prompt=self.remote.encode()+b' *'
  if label=='start-cue':self.s.pending.append(b'MARKER')
  elif label in ('cd','load'):self.s.pending.append(prompt)
  elif label=='run':self.s.pending.extend([self.banner,b'FINAL-RETURN '+prompt])
class Suite(m.Bench):
 def entry(self):pass
 def stage(self):pass
 def flash(self,label,image):self.flashes.append(label)
 def probe(self,label):self.probes.append(label)
 def handback(self):self.restored=True
 def case(self,index,backend,mode):
  self.cases.append((index,backend,mode))
  if index==self.fail:raise m.SetupFailure('retained setup failure')
 def preserve_setup(self):self.preserved=True;self.restored=True
class Controller(unittest.TestCase):
 def test_actual_prompt_barrier_and_setup_stop(self):
  for banner,control in ((b'WOLF-PERF-003 COMPLETE\nThanks for playing Wolf3DOrig!',False),(b'WOLF-PERF-003 CONTROL REGISTERS-RESTORED RETURN\nThanks for playing Wolf3DOrig!',True),(b'AGNB texture load failed; render not submitted.',False)):
   with tempfile.TemporaryDirectory()as name:
    b=object.__new__(Fake);b.remote='/test/wolf/perf003/pair05';b.port='NO-DEVICE';b.s=Serial();b.banner=banner;m.m.open_passive_serial=lambda *a,**k:b.s;m.time=Clock()
    if banner.startswith(b'AGNB'):
     with self.assertRaises(m.SetupFailure):b.invoke(Path(name),'a-paced.bin','MARKER')
    else:b.invoke(Path(name),'a-control.bin'if control else'a-unpaced.bin','MARKER',control)
    self.assertTrue(b.s.returned)
 def test_actual_full_sequence_and_first_failure(self):
  for failure in (None,4):
   with tempfile.TemporaryDirectory()as name:
    b=object.__new__(Suite);b.out=Path(name);b.flashes=[];b.probes=[];b.cases=[];b.fail=failure;b.preserved=False;b.restored=False;m.time=Clock()
    b.suite();self.assertTrue(b.restored)
    if failure is None:
     self.assertEqual(len(b.cases),14);self.assertEqual(len(b.probes),8);self.assertEqual(b.flashes,['a1','b1','a2','restore']);self.assertTrue((b.out/'complete.json').exists())
    else:
     self.assertEqual(len(b.cases),4);self.assertEqual(b.flashes,['a1']);self.assertTrue(b.preserved);self.assertFalse((b.out/'complete.json').exists())
if __name__=='__main__':unittest.main()
