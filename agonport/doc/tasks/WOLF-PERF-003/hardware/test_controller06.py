"""Device-free actual prompt and full-sequence/first-failure dispatch checks."""
from pathlib import Path
import importlib.util,tempfile,unittest,json
T=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('physical06',T/'hardware/physical06.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
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
class Lock:
 def close(self):pass
class Entry(m.Bench):
 def own(self):pass
 def cli(self,*args):pass
 def service(self,*args):pass
 def transfer(self,folder,label,op,remote,local):
  assert op=='get';Path(local).write_bytes(self.files[remote]);self.calls.append(('get',remote))
 def metadata(self,*args):return self
 def entries(self,remote):return self.existing
 def make_directory(self,remote,parents):self.calls.append(('mkdir',remote))
 def upload(self,folder,label,local,remote):
  self.calls.append(('upload',remote));self.script=Path(local).read_bytes()
 def raw_state(self,*args):self.calls.append(('raw',True))
class Controller(unittest.TestCase):
 def test_actual_entry_file_hashes_and_namespace(self):
  for wrong_hash,collision in ((False,False),(True,False),(False,True)):
   with self.subTest(wrong_hash=wrong_hash,collision=collision),tempfile.TemporaryDirectory()as name:
    b=object.__new__(Entry);b.out=Path(name);b.remote='/test/wolf/perf003/pair05';b.calls=[];b.lock=Lock();b.existing=[(b.remote,0,16)]if collision else[]
    b.files={'/autoexec.txt':b'SET KEYBOARD 1\r\n','/emos/sdserve.bin':b'\x00\xffLISTENER'}
    b.components={'startup_sha256':m.sha(b.files['/autoexec.txt']),'listener_sha256':m.sha(b.files['/emos/sdserve.bin'])}
    if wrong_hash:b.components['startup_sha256']='0'*64
    if wrong_hash or collision:
     with self.assertRaises(AssertionError):b.entry()
     self.assertFalse(any(c[0]in ('upload','mkdir','raw')for c in b.calls))
    else:
     b.entry();self.assertTrue(json.loads((b.out/'entry/receipt.json').read_text())['passed'])
     self.assertEqual([c for c in b.calls if c[0]=='get'],[('get','/autoexec.txt'),('get','/emos/sdserve.bin')])
     self.assertIn(b'&BC349 &1',b.script);self.assertIn(b'&BC38E &3',b.script);self.assertNotIn(b'LOAD',b.script);self.assertNotIn(b'RUN',b.script)

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
