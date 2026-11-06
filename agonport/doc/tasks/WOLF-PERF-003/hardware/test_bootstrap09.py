"""Device-free real bootstrap ordering/failure-stop checks; no resets executed."""
from pathlib import Path
from unittest.mock import patch
import importlib.util,json,tempfile,unittest
import bootstrap09 as m
T=Path(__file__).resolve().parents[1]
class Clock:
 def __init__(self):self.t=0
 def monotonic(self):self.t+=.5;return self.t
 def time(self):return self.monotonic()
class Model:
 def __init__(self,panic=False,agon_ok=True):self.events=[];self.panic=panic;self.agon_ok=agon_ok;self.agon=False;self.pad_sent=False;self.console_sent=False;self.closed=False
 def open(self):self.events.append('open')
 def close(self):self.closed=True;self.events.append('close')
 def reset_input_buffer(self):pass
 def read(self,size):
  if not self.pad_sent:
   self.pad_sent=True;return b'build_id='+m.BUILD+b'\n'+m.PAD+b'\n'+(b'Guru Meditation'if self.panic else b'')
  if self.agon and not self.console_sent:self.console_sent=True;return m.CONSOLE+b'\n'
  return b''
class Bench:
 def __init__(self,model):self.model=model;self.c={'ports':['MAINBOARD','Espressif-P4']};self.url='http://NO-DEVICE'
 def own(self):pass
 def get(self,path):
  if path=='/sd/status':return {'online':False}
  if path=='/sd/fast':return {'phase':0}
  if path=='/display/status':return {'available':True}
  if path=='/keyboard/status':return dict(ready=True,physical_neutral=True,held=0,pending=0)
  raise AssertionError(path)
class Child:
 def __init__(self,model,*args,**kwargs):self.model=model;model.events.append('agon');model.agon=True;self.calls=0
 def poll(self):self.calls+=1;return None if self.calls==1 else(0 if self.model.agon_ok else 1)
 def wait(self,timeout=None):return 0 if self.model.agon_ok else 1
 def terminate(self):self.model.events.append('terminate')
class Reset:
 def __init__(self,model):self.model=model
 def reset(self):self.model.events.append('p4')
class Bootstrap(unittest.TestCase):
 def test_current_build_then_single_agon_and_failure_stops(self):
  for panic,agon_ok in ((False,True),(True,True),(False,False)):
   with self.subTest(panic=panic,agon_ok=agon_ok),tempfile.TemporaryDirectory()as name:
    model=Model(panic,agon_ok);b=Bench(model);p=Path(name)
    with patch.object(m.serial,'Serial',return_value=model),patch.object(m,'HardReset',return_value=Reset(model)),patch.object(m,'time',Clock()),patch.object(m.subprocess,'Popen',side_effect=lambda *a,**kw:Child(model,*a,**kw))as spawn:
     if panic or not agon_ok:
      with self.assertRaises((RuntimeError,AssertionError)):m.clean_bootstrap(b,p)
     else:m.clean_bootstrap(b,p)
    self.assertTrue(model.closed);self.assertEqual(model.events.count('p4'),1)
    if panic:self.assertNotIn('agon',model.events);spawn.assert_not_called()
    else:
     self.assertEqual(model.events.count('agon'),1);self.assertLess(model.events.index('p4'),model.events.index('agon'))
     args=spawn.call_args[0][0];self.assertIn('reset_agon_usb.py',args[1]);self.assertNotIn('write-flash',' '.join(args))
    if not panic and agon_ok:
     r=json.loads((p/'clean-bootstrap/admission.json').read_text());self.assertEqual((r['p4_resets'],r['agon_resets']),(1,1));self.assertTrue(r['no_replay'])
    else:self.assertFalse((p/'clean-bootstrap/admission.json').exists())
 def test_actual_driver_boot_finishes_cleanly_before_use(self):
  spec=importlib.util.spec_from_file_location('physical09',T/'hardware/physical09.py');driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
  class B(driver.Bench):
   def cli(self,*a):events.append('cli')
   def service(self,*a):events.append('listener')
   def raw_state(self,*a):events.append('state')
   def exit(self,*a):events.append('exit')
  for fails in (False,True):
   events=[];b=object.__new__(B)
   def boot(*a):
    events.append('bootstrap')
    if fails:raise RuntimeError('failed current bootstrap')
   with patch.object(m,'clean_bootstrap',side_effect=boot):
    if fails:
     with self.assertRaises(RuntimeError):b.boot(Path('NO-DEVICE'),'test')
    else:b.boot(Path('NO-DEVICE'),'test')
   self.assertEqual(events,['bootstrap']if fails else['bootstrap','cli','listener','state','exit'])
if __name__=='__main__':unittest.main()
