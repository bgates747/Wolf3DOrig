"""Signal only an isolated owned host child; no board, build or replay."""
from pathlib import Path
import json,os,signal,subprocess,sys,tempfile,unittest
HERE=Path(__file__).resolve().parent
class Interrupted(unittest.TestCase):
 def test_actual_child_records_signal_and_unwinds(self):
  for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):
   with self.subTest(signal=sig),tempfile.TemporaryDirectory()as name:
    code="""import sys,signal
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from host_interrupt08 import install,HostInterrupted
p=Path(sys.argv[2]);install(p)
try:
 try:
  print('READY',flush=True)
  signal.pause()
 finally:(p/'unwound').write_text('closed')
except HostInterrupted as stopped:raise SystemExit(128+stopped.signum)
(p/'continued').write_text('WRONG')
"""
    child=subprocess.Popen([sys.executable,'-u','-c',code,str(HERE),name],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
     self.assertEqual(child.stdout.readline().strip(),'READY');os.kill(child.pid,sig);out,err=child.communicate(timeout=5)
    finally:
     if child.poll()is None:child.kill();child.communicate()
    self.assertEqual(child.returncode,128+sig,err);p=Path(name);r=json.loads((p/'host-interruption.json').read_text());self.assertEqual(r['signal'],sig);self.assertEqual(r['pid'],child.pid);self.assertTrue(r['sender_unknown']);self.assertFalse(r['continuation']);self.assertFalse((p/'continued').exists());self.assertEqual((p/'unwound').read_text(),'closed');self.assertTrue(r['stack'])
if __name__=='__main__':unittest.main()
