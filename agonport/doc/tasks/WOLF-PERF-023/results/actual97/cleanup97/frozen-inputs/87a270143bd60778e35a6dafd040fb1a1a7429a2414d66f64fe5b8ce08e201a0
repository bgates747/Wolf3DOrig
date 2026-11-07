"""Actual consumer selection against retained deployed listener's host engine.

The MOS filesystem is the owner's POSIX/fault adapter. No HTTP, serial, reset,
emulator or target operations occur. Compile/run only under Pi build custody.
"""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import json
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch
import hardware02 as hardware

T = Path(__file__).resolve().parent
SOURCE = Path('/Agon/mystuff/agon-extender/agents/remote009/download-r01/source')
spec = importlib.util.spec_from_file_location('retained_sdserve_tests', SOURCE/'tests/test_sdserve.py')
owner = importlib.util.module_from_spec(spec); spec.loader.exec_module(owner)
OUT = T/'build/composition02'


class Peer(owner.SdserveTests):
    FAST = 1


class Adapter(hardware.Bench):
    def __init__(self, peer, output):
        self.peer = peer; self.out = Path(output); self.cleaning = False
        self.deadline = hardware.time.monotonic()+4200
        self.remote = '/test/wolf/perf023/r01'
        self.observer_folder = None; self.observer_record = {}
        self.root = peer.disk/self.remote.lstrip('/'); self.root.mkdir(parents=True)
        bindings=json.loads((T/'HARDWARE-GUESTS.json').read_text())
        self.kit = dict(modules={a:bindings[a]['room']['module'] for a in hardware.ARMS})
        for a in hardware.ARMS: self.kit[a+'_module_sha256'] = hardware.sha(self.kit['modules'][a])
        self.selected_module_sha256 = self.kit['original_module_sha256']
        (self.root/'wolf3d.vdpl').write_bytes(Path(self.kit['modules']['original']).read_bytes())
        self.retire_calls = 0; self.put_calls = 0; self.corrupt_target = False; self.corrupt_backup = False
        self.fail_retirement = False
    def own(self): pass
    def get(self,path): assert path=='/sd/status'; return dict(online=True)
    def verify_route(self,*args): pass
    def metadata(self,*args): return SimpleNamespace(rpc=self.rpc,lock=SimpleNamespace(close=lambda:None))
    def rpc(self,op,payload):
        assert op==10
        if payload[0]==3:
            self.retire_calls += 1
            if self.fail_retirement: self.peer.lib.fs_fault(7,1)
        return self.peer.rpc(op,payload)
    def transfer(self,folder,label,op,remote,local):
        if op=='get':
            data=bytearray(); at=0
            while True:
                reply=self.peer.read(remote,at,216);total=struct.unpack_from('<I',reply)[0]
                data.extend(reply[4:]);at+=len(reply)-4
                if at==total:break
                assert len(reply)>4
            Path(local).write_bytes(data)
        else:
            assert op=='put'; self.put_calls += 1
            blob=Path(local).read_bytes(); tid=73
            self.peer.rpc(5,struct.pack('<III',tid,len(blob),0)+owner.path(remote))
            for at in range(0,len(blob),212):self.peer.rpc(6,struct.pack('<II',tid,at)+blob[at:at+212])
            self.peer.rpc(7,struct.pack('<I',tid));self.peer.rpc(8,struct.pack('<I',tid))
            if self.corrupt_target:(self.root/'wolf3d.vdpl').write_bytes(b'corrupted-target')
            if self.corrupt_backup:(self.root/'wolf3d.vdpl.p17bak').write_bytes(b'foreign-backup')


class Composition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Peer.setUpClass()
        shutil.copyfile(Path(Peer.build.name)/'sd.so',OUT/'listener-host.so')
        shutil.copyfile(Path(Peer.build.name)/'probe.c',OUT/'probe.c')
    @classmethod
    def tearDownClass(cls): Peer.tearDownClass()
    def setUp(self):
        self.observer = patch.object(hardware.host_observer, 'check', return_value={})
        self.observer.start(); self.addCleanup(self.observer.stop)
        self.peer=Peer('runTest');self.peer.setUp();self.temp=tempfile.TemporaryDirectory()
        self.b=Adapter(self.peer,self.temp.name)
    def tearDown(self): self.peer.tearDown();self.temp.cleanup()
    def test_old_repeated_replacement_reproduces_guard_without_weakening_it(self):
        b=self.b;source=b.kit['modules']['original'];p=b.folder('old-sequence')
        b.upload(p,'original',source,b.remote+'/wolf3d.vdpl')
        self.assertEqual(b.module_state(p,'retained'),b'\x09')
        blob=Path(b.kit['modules']['candidate']).read_bytes()
        self.peer.rpc(5,struct.pack('<III',74,len(blob),0)+owner.path(b.remote+'/wolf3d.vdpl'),status=8)
        self.assertEqual(hardware.sha(b.root/'wolf3d.vdpl'),b.kit['original_module_sha256'])
        self.assertEqual(b.retire_calls,0)
    def test_actual_consumer_completes_six_selections_including_repeated_same_arm(self):
        b=self.b
        for i,(arm,_) in enumerate(hardware.SEQUENCE,1):
            b.install_module(arm,i)
            self.assertEqual(hardware.sha(b.root/'wolf3d.vdpl'),b.kit[arm+'_module_sha256'])
            self.assertFalse((b.root/'wolf3d.vdpl.p17bak').exists())
            self.assertFalse((b.root/'wolf3d.vdpl.p17meta').exists())
            self.assertFalse((b.root/'wolf3d.vdpl.p17part').exists())
        self.assertEqual(b.retire_calls,4);self.assertEqual(b.put_calls,4)
    def test_existing_foreign_backup_refuses_before_put_or_retirement(self):
        b=self.b;(b.root/'wolf3d.vdpl.p17bak').write_bytes(b'foreign')
        with self.assertRaisesRegex(AssertionError,'Unknown module siblings'):b.install_module('candidate',1)
        self.assertEqual((b.put_calls,b.retire_calls),(0,0))
        self.assertEqual((b.root/'wolf3d.vdpl.p17bak').read_bytes(),b'foreign')
    def test_full_target_readback_mismatch_preserves_backup(self):
        b=self.b;b.corrupt_target=True
        with self.assertRaises(AssertionError):b.install_module('candidate',1)
        self.assertEqual(b.retire_calls,0)
        self.assertEqual(hardware.sha(b.root/'wolf3d.vdpl.p17bak'),b.kit['original_module_sha256'])
    def test_backup_mismatch_preserved_after_verified_target(self):
        b=self.b;b.corrupt_backup=True
        with self.assertRaisesRegex(AssertionError,'Unexpected backup'):b.install_module('candidate',1)
        self.assertEqual(b.retire_calls,0)
        self.assertEqual(hardware.sha(b.root/'wolf3d.vdpl'),b.kit['candidate_module_sha256'])
        self.assertEqual((b.root/'wolf3d.vdpl.p17bak').read_bytes(),b'foreign-backup')
    def test_real_engine_cleanup_failure_preserves_target_and_backup(self):
        b=self.b;b.fail_retirement=True
        with self.assertRaises(AssertionError):b.install_module('candidate',1)
        self.assertEqual(b.retire_calls,1)
        self.assertEqual(hardware.sha(b.root/'wolf3d.vdpl'),b.kit['candidate_module_sha256'])
        self.assertEqual(hardware.sha(b.root/'wolf3d.vdpl.p17bak'),b.kit['original_module_sha256'])
        self.assertFalse((b.out/'module-01-candidate/receipt.json').exists())


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Composition)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
