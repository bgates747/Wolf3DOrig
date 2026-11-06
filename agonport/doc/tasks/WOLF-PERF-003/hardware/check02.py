"""Offline controller terminal-path and assembled diagnostic layout checks."""
from pathlib import Path
import importlib.util,json,re
T=Path(__file__).resolve().parents[1];B=T/'build/hardware02'
spec=importlib.util.spec_from_file_location('physical02',T/'hardware/physical02.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
# Test actual invoke/capture against a fake serial/keyboard, including an old
# prompt and a delayed post-main prompt. No device or network helper is called.
class Serial:
 def __init__(self):self.pending=[];self.final_return_seen=False
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self,n):
  if not self.pending:return b''
  r=self.pending.pop(0)
  if b'FINAL-RETURN'in r:self.final_return_seen=True
  return r
class Fake(m.Bench):
 def own(self):pass
 def exit(self,*args):pass
 def service(self,*args):raise AssertionError('Must stop before listener starts')
 def line(self,folder,label,text):
  if label=='start-cue':serial.pending.append(b'WP3-TEST')
  if label in ('cd','load'):serial.pending.append(b'/test/wolf/perf003 *')
  if label=='run':serial.pending.extend([b'AGNB texture load failed; render not submitted.',b'Thanks for playing Wolf3DOrig!',b'WPL diagnostic finished\r\nFINAL-RETURN /test/wolf/perf003 *'])
serial=Serial();m.m.open_passive_serial=lambda *args,**kwargs:serial
b=object.__new__(Fake);b.port='NO-DEVICE';b.remote='/test/wolf/perf003';out=B/'controller-test';out.mkdir(exist_ok=True)
try:b.invoke(out,'a-control.bin','WP3-TEST',True)
except m.SetupFailure:assert serial.final_return_seen
else:raise AssertionError('Early loading failure must stop dispatch')
layouts=[]
for backend in ('bespoke','vdplet'):
 for mode in ('cpu','unpaced','paced','control'):
  d=B/backend/mode/'source';listing=(d/'wolf3d.lst').read_text()
  def at(name):
   r=re.search(r'^([0-9A-F]{6})[^\n]*\b'+name+':',listing,re.M);assert r,name;return int(r[1],16)
  assert at('wpl_end')-at('wpl_data')==48
  raw=(d/'wolf3d.bin').read_bytes();record=raw[at('wpl_data')-0x40000:at('wpl_end')-0x40000]
  parsed=m.decode_loading(record);assert parsed['error']==parsed['timeouts']==parsed['fences']==0
  assert at('wpl_passes')-at('wpl_data')==37
  assert at('wpl_agnb_error')-at('wpl_data')==40
  helper=(d/'loading_wait.inc').read_text()
  assert helper.count('MOSCALL mos_clearvdpflags')==1 and helper.count('rst.lil 018h')==1
  assert helper.index('@wait:')>helper.index('rst.lil 018h')
  assert (d/'bench.inc').read_bytes()==(T/'build/hardware01'/backend/mode/'source/bench.inc').read_bytes()
  layouts.append(dict(backend=backend,mode=mode,record_bytes=len(record),binary_bytes=len(raw)))
(B/'offline-checks.json').write_text(json.dumps(dict(passed=True,actual_controller_early_return_test=True,assembled_layouts=layouts,no_device_calls=True),indent=2)+'\n')
print('PASS controller waits for actual post-RUN prompt; eight assembled layouts; exact timed source identity')
