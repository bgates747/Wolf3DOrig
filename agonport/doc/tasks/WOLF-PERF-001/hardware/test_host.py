"""Device-free guard and deployment checks for the Olimex coordinator."""
import importlib.util,json,shutil,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('wolf_physical',HERE/'physical.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Host(unittest.TestCase):
 def test_durable_records_refuse_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'record.json';m.save(p,{'passed':True})
   self.assertEqual(json.loads(p.read_text()),{'passed':True})
   with self.assertRaises(FileExistsError):m.save(p,{})
 def test_retained_runtime_binding_and_refusals(self):
  root=HERE.parents[4]
  raw=(root/'agonport/build/hardware/vdplet-discovery-r01/attempt-05-mainboard.raw').read_bytes()
  self.assertEqual(m.verify_runtime_trace(raw,b'20261031'),(256,287))
  for bad in (raw.replace(b'value=256',b'value=287'),raw.replace(b'value=287',b'value=31'),raw[:20]):
   with self.assertRaises(AssertionError):m.verify_runtime_trace(bad,b'20261031')
  with self.assertRaises(AssertionError):m.verify_runtime_trace(raw)
 def test_staging_does_not_invoke(self):
  with tempfile.TemporaryDirectory() as d:
   b=m.Bench.__new__(m.Bench);b.out=Path(d)/'evidence';b.out.mkdir();(b.out/'entry').mkdir()
   m.save(b.out/'entry/receipt.json',{'passed':True})
   b.package=Path(d)/'payload';(b.package/'cpu').mkdir(parents=True);(b.package/'cpu/wolf3d.bin').write_bytes(b'fixture')
   b.inventory={'order':['cpu'],'case_files':{'cpu':['wolf3d.bin']}};b.remote='/test/wolf/fresh'
   b.metadata=lambda *args:SimpleNamespace(make_directory=lambda *args,**kw:None,lock=SimpleNamespace(close=lambda:None))
   stored={}
   def transfer(folder,label,op,remote,local):
    if op=='put':stored[remote]=local.read_bytes()
    else:local.write_bytes(stored[remote])
   b.transfer=transfer;b.exit=lambda *args:None
   b.line=lambda *args:(_ for _ in ()).throw(AssertionError('staging invoked CLI'))
   b.stage();script=stored['/test/wolf/fresh/cpu/invoke.txt'].decode()
   self.assertEqual(script.count('RUN .\n'),1)
   self.assertIn('&BC349',script);self.assertNotIn('autoexec', '\n'.join(stored))
   self.assertNotIn('BC42B',script)
   self.assertFalse(json.loads((b.out/'stage/receipt.json').read_text())['application_invoked'])
 def test_failure_precedes_completion(self):
  with tempfile.TemporaryDirectory() as d:
   b=m.Bench.__new__(m.Bench)
   serial=SimpleNamespace(read=lambda n:b'WOLF-PERF-001 FAILED TIMER-RESTORED\n')
   with self.assertRaises(RuntimeError):b.capture_until(serial,bytearray(),Path(d),lambda raw:True,1)
 def test_context_admission_has_no_device_side_effects(self):
  freeze=json.loads((HERE/'freeze.json').read_text())
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);grant=root/'grant.json';context=root/'context.json'
   record={'owner':'wolf3dorig','task':'WOLF-PERF-001-hardware','lease':'device-free-unit-test','entry_observation':{'components':freeze['expected_components']}}
   grant.write_text(json.dumps(record))
   context.write_text(json.dumps({'grant':str(grant),'output':str(root/'evidence/fresh'),'url':'http://not-used.invalid','port':'not-used','ports':[],'entry_route':'legacy'}))
   with patch.object(m,'BUILD',root),patch.object(m.urllib.request,'urlopen',side_effect=AssertionError('network contact')),patch.object(m.subprocess,'run',side_effect=AssertionError('process launch')),patch.object(m,'open_passive_serial',side_effect=AssertionError('serial contact')):
    m.Bench(context)
    record['entry_observation']['components']['native_vdp_sha256']='0'*64;grant.write_text(json.dumps(record))
    with self.assertRaises(AssertionError):m.Bench(context)
if __name__=='__main__':unittest.main()
