"""Check actual generated inputs and reject corrupt timing evidence."""
from pathlib import Path
import argparse,hashlib,json,struct,sys,tempfile,unittest
from analyze import analyze
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'agonport/tools/wolf3d_assets'))
from formats.level_package import parse_package
BASE=None

class Contract(unittest.TestCase):
    def test_generated_payloads_and_backend_headers(self):
        manifest=json.loads((BASE/'inputs.json').read_text())
        reference=BASE/'common-payload'
        for backend,identity,size in [('bespoke',1,24),('vdplet',2,28)]:
            for mode_id,mode in [(1,'cpu'),(2,'unpaced'),(3,'paced'),(1,'cpu-fail')]:
                payload=BASE/backend/mode/'payload';binary=(payload/'wolf3d.bin').read_bytes()
                magic=b'WPF3\1'+bytes([mode_id]);self.assertEqual(binary.count(magic),1)
                at=binary.index(magic);self.assertEqual(binary[at+29:at+33],bytes([34,36,0,identity]))
                for relative,item in manifest['payload'].items():
                    data=(payload/relative).read_bytes();self.assertEqual(data,(reference/relative).read_bytes())
                    self.assertEqual(hashlib.sha256(data).hexdigest(),item['sha256'])
                source=(BASE/backend/mode/'source/bench.inc').read_text()
                if backend=='bespoke':self.assertNotIn('w3d_vdplet_',source)
                self.assertIn('call w3d_audio_wait_for_vdp_ingress' if backend=='vdplet' else 'call wp_a_fence',source)
        for difficulty in ('baby','easy','medium','hard'):
            level=parse_package((reference/f'level_00/state_{difficulty}.w3l').read_bytes())
            original=parse_package((ROOT/f'agonport/assets/generated/wolf3d/levels/level_00/state_{difficulty}.w3l').read_bytes())
            self.assertEqual((level.actor_count,level.sections['actors'],level.player_pose),(0,b'',struct.pack('<iiH',0x228000,0x248000,0)))
            for key,value in original.sections.items():
                if key!='actors':self.assertEqual(level.sections[key],value)
        poses=json.loads((BASE/'poses.json').read_text())
        self.assertEqual([poses[n]['angle']for n in (0,300,600)],[0,0,0])
        self.assertEqual(sum((b['angle']-a['angle'])%360 for a,b in zip(poses,poses[1:])),720)
        self.assertEqual({(p['x'],p['y'])for p in poses},{(0x228000,0x248000)})

    def test_safe_module_and_frozen_source_bindings(self):
        record=json.loads((BASE/'inputs.json').read_text())
        for relative,item in record['bindings'].items():
            self.assertEqual(hashlib.sha256((BASE/'inputs'/relative).read_bytes()).hexdigest(),item['sha256'])
        module=json.loads((BASE/'vdplet/module/wolf_perf.json').read_text())['module']
        self.assertTrue(module['compiler_target']['psram_cache_workaround'])
        self.assertEqual((module['abi_minor'],module['capabilities']),(6,257))
        self.assertLessEqual(module['resident_text_bytes'],65536)
        self.assertLessEqual(module['resident_data_bytes'],16384)

    def test_decoder_accepts_both_backend_schemas_and_refuses_corruption(self):
        u24=lambda n:n.to_bytes(3,'little')
        for backend,prepared in [(1,24),(2,28)]:
            header=b'WPF3'+bytes([1,3,1,1])+b''.join(u24(n)for n in (2,0,20000,0,2400,0,56))+bytes([34,36,0,backend])
            rows=b''.join(b''.join(u24(n)for n in (index,0,t,t,t,t,t,t,prepared))for index,t in ((300,10000),(600,20000)))
            timing=header+rows+bytes(598*27)
            native=struct.pack('<4I',0x314e5057,1,2,0xcdcd)+struct.pack('<5I',0,0,48,48,64)+struct.pack('<5I',1,0,48,48,64)
            with tempfile.TemporaryDirectory()as name:
                p=Path(name);(p/'native.bin').write_bytes(native);(p/'timing.bin').write_bytes(timing)
                report=analyze(p);self.assertEqual(report['backend'],'bespoke' if backend==1 else 'vdplet')
                self.assertEqual(report['completed_records'],2);self.assertEqual(report['coalesced_poses'],598)
                for offset in [6,7,32,33,36,57,len(timing)-1]:
                    bad=bytearray(timing);bad[offset]^=1;(p/'timing.bin').write_bytes(bad)
                    with self.assertRaises(ValueError,msg=str((backend,offset))):analyze(p)
                (p/'timing.bin').write_bytes(timing)
                for offset in (8,36,40,44):
                    bad=bytearray(native);bad[offset]^=1;(p/'native.bin').write_bytes(bad)
                    with self.assertRaises(ValueError,msg=str((backend,offset))):analyze(p)
                    (p/'native.bin').write_bytes(native)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--revision',required=True)
    args,rest=parser.parse_known_args();BASE=HERE/'build'/args.revision
    unittest.main(argv=[sys.argv[0],*rest])
