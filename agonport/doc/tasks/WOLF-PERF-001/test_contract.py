"""Independent endpoint, immutable-scene and corrupt-evidence checks."""
import json,struct,sys,tempfile,unittest
from pathlib import Path
from analyze import analyze
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'agonport/tools/wolf3d_assets'))
from formats.level_package import parse_package
class Contract(unittest.TestCase):
 def test_workload_is_exact_and_only_enemies_and_pose_change(self):
  for difficulty in ('baby','easy','medium','hard'):
   original=parse_package((ROOT/f'agonport/assets/generated/wolf3d/levels/level_00/state_{difficulty}.w3l').read_bytes())
   new=parse_package((HERE/f'build/paced/payload/level_00/state_{difficulty}.w3l').read_bytes())
   self.assertEqual((new.actor_count,new.sections['actors'],new.player_pose),(0,b'',struct.pack('<iiH',0x228000,0x248000,0)))
   for section in original.sections:
    if section!='actors':self.assertEqual(new.sections[section],original.sections[section],section)
  angles=[720*n//600%360 for n in range(601)]
  self.assertEqual((angles[0],angles[300],angles[600]),(0,0,0))
  self.assertEqual(sum((b-a)%360 for a,b in zip(angles,angles[1:])),720)
 def test_decoder_rejects_false_success(self):
  u24=lambda x:x.to_bytes(3,'little')
  header=b'WPF1'+bytes([1,1,1,1])+b''.join(u24(x) for x in (600,0,600,0,72,0,0))+bytes([34,36,0,0])
  rows=b''.join(b''.join(u24(x) for x in (n,720*n//600%360,n,n,n,n,n,n,28)) for n in range(1,601))
  with tempfile.TemporaryDirectory() as name:
   p=Path(name);(p/'timing.bin').write_bytes(header+rows);self.assertEqual(analyze(p)['completed_records'],600)
   for offset in (6,7,33,36):
    bad=bytearray(header+rows);bad[offset]^=1;(p/'timing.bin').write_bytes(bad)
    with self.assertRaises(ValueError):analyze(p)
 def test_production_sources_unchanged_since_build(self):
  import hashlib
  manifest=json.loads((HERE/'build/inputs.json').read_text())
  for path,digest in manifest['production_sources'].items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)
 def test_partial_paced_storage_and_native_identity(self):
  u24=lambda x:x.to_bytes(3,'little')
  header=b'WPF1'+bytes([1,3,1,1])+b''.join(u24(x) for x in (2,0,20000,0,2400,0,56))+bytes([34,36,0,0])
  rows=b''.join(b''.join(u24(x) for x in (n,0,t,t,t,t,t,t,28)) for n,t in ((300,10000),(600,20000)))
  data=header+rows+bytes(598*27)
  native=struct.pack('<4I',0x314e5057,1,2,0)+struct.pack('<5I',0,0,10,20,30)+struct.pack('<5I',1,0,10,20,30)
  with tempfile.TemporaryDirectory() as name:
   p=Path(name);(p/'timing.bin').write_bytes(data);(p/'native.bin').write_bytes(native)
   self.assertEqual(analyze(p)['coalesced_poses'],598)
   (p/'timing.bin').write_bytes(data[:-1]+b'\xff')
   with self.assertRaises(ValueError):analyze(p)
   (p/'timing.bin').write_bytes(data)
   bad=bytearray(native);bad[40]=1;(p/'native.bin').write_bytes(bad)
   with self.assertRaises(ValueError):analyze(p)
if __name__=='__main__':unittest.main()
