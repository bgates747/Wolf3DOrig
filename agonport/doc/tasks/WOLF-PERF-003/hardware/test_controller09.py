"""Device-free execution of input, entry, stage, case, probe and handback paths.
Binary case fixtures model every backend/mode; retained49 CPU bytes/stack and
loading diagnostics supply source-backed codec inputs, not new target results.
"""
from pathlib import Path
from unittest.mock import patch
import importlib.util,hashlib,json,struct,tempfile,unittest,subprocess
T=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('physical09',T/'hardware/physical09.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
PRIOR=T/'build/hardware06/evidence/02-bespoke-cpu'
LISTING=T/'build/hardware05/bespoke/cpu/source/wolf3d.lst'
class Clock:
 def __init__(self):self.n=0
 def monotonic(self):self.n+=.1;return self.n
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
class Invoke(m.Bench):
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
class Fake(m.Bench):
 def own(self):pass
 def get(self,path):
  assert path=='/sd/status';return dict(online=True)
 def cli(self,folder,label):
  (folder/'serial.bin').write_bytes(b'actual CLI model');self.events.append(('cli',label))
 def service(self,*args):self.events.append(('service',True))
 def exit(self,*args):self.events.append(('exit',True))
 def raw_state(self,*args):self.events.append(('raw',True))
 def clear_outputs(self,*args):self.events.append(('clear',True))
 def reset_config(self,*args):self.events.append(('config',True))
 def invoke(self,*args):self.events.append(('invoke',True));return .2
 def line(self,*args):self.events.append(('line',args[-1]))
 def transfer(self,folder,label,op,remote,local):
  assert op=='get';Path(local).write_bytes(self.files[remote]);self.events.append(('get',remote))
 def upload(self,folder,label,local,remote):
  self.files[remote]=Path(local).read_bytes();self.events.append(('upload',remote))
 def metadata(self,*args):return self
 def entries(self,remote):return self.dirs[remote]
 def remove(self,remote):self.events.append(('remove',remote));del self.files[remote]
 def state(self):return dict(keyboard=dict(ready=True,physical_neutral=True,held=0,pending=0),sd=dict(online=False,pending=False),worker=dict(phase=0))
def fake(root):
 b=object.__new__(Fake);b.out=root;b.remote='/test/wolf/perf003/pair05';b.events=[];b.files={};b.dirs={};b.lock=Lock();b.c={'ports':['NO-DEVICE']};b.lease='MODEL';b.deadline=10000;b.components={'startup_sha256':m.sha(b'STARTUP'),'listener_sha256':m.sha(b'LISTENER')};b.files.update({'/autoexec.txt':b'STARTUP','/emos/sdserve.bin':b'LISTENER'});return b
class Controller(unittest.TestCase):
 def test_all_runtime_inputs_are_preflighted(self):
  with tempfile.TemporaryDirectory()as name:
   p=Path(name)/'listing';p.write_text('040100 wp_entry_sp:\n040103 wp_exit_sp:\n');asset=Path(name)/'asset';asset.write_bytes(b'x');k=dict(inputs={str(p):m.sha(p.read_bytes()),str(asset):m.sha(b'x')},stage={'asset':str(asset)},listings={b+'-'+s:str(p)for b in ('bespoke','vdplet')for s in ('cpu','unpaced','paced','control')})
   m.verify_kit(k);p.unlink()
   with self.assertRaises(FileNotFoundError):m.verify_kit(k)
 def test_actual_retained_entry_and_stage(self):
  for unknown,bad_hash,bad_asset in ((False,False,False),(True,False,False),(False,True,False),(False,False,True)):
   with self.subTest(unknown=unknown,bad_hash=bad_hash,bad_asset=bad_asset),tempfile.TemporaryDirectory()as name:
    root=Path(name);b=fake(root);asset=root/'asset';asset.write_bytes(b'WORLD');cfg=root/'config';cfg.write_bytes(b'');b.kit={'stage':{'level_00/world.bin':str(asset),'wolf3d.cfg':str(cfg)}}
    script=('SAVE '+b.remote+'/post-mode.bin &BC349 &1\r\nSAVE '+b.remote+'/post-callback.bin &BC38E &3\r\nEMOS sdserve --fast /\r\n').encode();b.files.update({b.remote+'/state.txt':script,b.remote+'/level_00/world.bin':b'BAD'if bad_asset else b'WORLD',b.remote+'/wolf3d.cfg':b'GAME-SAVED-CONFIG'})
    b.dirs={'/test/wolf/perf003':[(b.remote,0,16)],b.remote:[(b.remote+'/level_00',0,16),(b.remote+'/wolf3d.cfg',4,0),(b.remote+'/state.txt',len(script),0)],b.remote+'/level_00':[(b.remote+'/level_00/world.bin',5,0)]}
    if unknown:b.dirs[b.remote].append((b.remote+'/unknown-user-file',1,0))
    if bad_hash:b.components['startup_sha256']='0'*64
    with patch.object(m,'time',Clock()):
     if unknown or bad_hash:
      with self.assertRaises(AssertionError):b.entry()
      self.assertFalse(any(e[0]in ('remove','upload','raw')for e in b.events));continue
     b.entry()
     if bad_asset:
      with self.assertRaises(AssertionError):b.stage()
      self.assertFalse(any(e[0]=='upload'for e in b.events));continue
     b.stage()
    self.assertEqual([e for e in b.events if e[0]=='upload'],[('upload',b.remote+'/wolf3d.cfg')]);self.assertEqual((root/'stage/file-01-existing.bin').read_bytes(),b'GAME-SAVED-CONFIG')
 def test_actual_case_codecs_and_listing_for_all_modes(self):
  for backend in ('bespoke','vdplet'):
   for mode in ('control','cpu','unpaced','paced'):
    with self.subTest(backend=backend,mode=mode),tempfile.TemporaryDirectory()as name:
     b=fake(Path(name));b.kit={'listings':{backend+'-'+mode:str(LISTING)}}
     for n in ('before.bin','after.bin','stack.bin','loading.bin','loading3.bin'):b.files[b.remote+'/'+n]=(PRIOR/n).read_bytes()
     raw=bytearray((PRIOR/'timing.bin').read_bytes());raw[5]={'control':1,'cpu':1,'unpaced':2,'paced':3}[mode];raw[32]=1 if backend=='bespoke'else 2
     for i in range(600):raw[33+i*27+24:33+i*27+27]=(24 if backend=='bespoke'else 28).to_bytes(3,'little')
     if mode in ('unpaced','paced'):
      native=struct.pack('<4I',0x314e5057,1,600,1)+b''.join(struct.pack('<5I',i,(720*(i+1)//600)%360,120000,150000,180000)for i in range(600));raw[26:29]=len(native).to_bytes(3,'little');b.files[b.remote+'/native.bin']=native
     b.files[b.remote+'/timing.bin']=bytes(raw)
     with patch.object(m,'time',Clock()):b.case(1,backend,mode)
     p=b.out/('01-'+backend+'-'+mode);r=json.loads((p/'receipt.json').read_text());self.assertTrue(r['passed']);self.assertTrue(r['mode0_callback0']);self.assertEqual(r['loading']['total'],470)
     if mode!='control':self.assertEqual(r['result']['completed_records'],600)
 def test_actual_resource_threshold_and_handback(self):
  for minimum in (512,511):
   with tempfile.TemporaryDirectory()as name:
    b=fake(Path(name));values=[0x100,0x101]+[0]*15+[minimum];b.files[b.remote+'/resource.bin']=b'WPR1\1\0\x12\0'+struct.pack('<18H',*values)
    with patch.object(m,'time',Clock()):
     if minimum<512:
      with self.assertRaises(AssertionError):b.probe('test')
     else:b.probe('test')
  with tempfile.TemporaryDirectory()as name:
   b=fake(Path(name))
   with patch.object(m,'time',Clock()),patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],1))as run:b.handback()
   r=json.loads((b.out/'handback/observation.json').read_text());self.assertTrue(all(r['checks'].values()));self.assertEqual(r['components'],b.components);self.assertEqual(run.call_count,1)
 def test_actual_prompt_barrier_and_setup_stop(self):
  for banner,control in ((b'WOLF-PERF-003 COMPLETE\nThanks for playing Wolf3DOrig!',False),(b'WOLF-PERF-003 CONTROL REGISTERS-RESTORED RETURN\nThanks for playing Wolf3DOrig!',True),(b'AGNB texture load failed; render not submitted.',False)):
   with tempfile.TemporaryDirectory()as name:
    b=object.__new__(Invoke);b.remote='/test/wolf/perf003/pair05';b.port='NO-DEVICE';b.s=Serial();b.banner=banner;m.m.open_passive_serial=lambda *a,**k:b.s;m.time=Clock()
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
