"""Real foreground engine through fault-injected POSIX adapter, not FAT qualification."""
import ctypes as C
from pathlib import Path
import random
import struct as S
import subprocess
import tempfile
import unittest
import zlib

ROOT=Path(__file__).resolve().parents[1]
def wire(session,seq,op,payload=b'',*,fast=False):
    h=S.pack('<2sBBIIBBH',b'SD',2 if fast else 1,1,session,seq,op,0,len(payload))
    return h+(b'\0'*4 if fast else S.pack('<I',zlib.crc32(h+payload)))+payload
def path(p):
    p=p.encode('ascii');return bytes([len(p)])+p

class SdserveTests(unittest.TestCase):
    FAST=0
    def test_reviewed_codec_matches_owner_when_available(self):
        owner=ROOT.parent/'agon-extender/vdp/video/extender/storage/sd_wire.h'
        if not owner.exists():self.skipTest('Independent checkout; owner codec unavailable')
        self.assertEqual(owner.read_bytes(),(ROOT/'projects/sdserve/src/sd_wire.h').read_bytes())
    @classmethod
    def setUpClass(cls):
        cls.build=tempfile.TemporaryDirectory();lib=Path(cls.build.name)/'sd.so'
        probe=Path(cls.build.name)/'probe.c'
        probe.write_text('#include "'+str(ROOT/'projects/sdserve/src/service.c')+'"\n'+'''
static unsigned crc_calls;
void __attribute__((no_instrument_function)) __cyg_profile_func_enter(void *f,void *caller) {
    (void)caller;if(f==(void *)sd_crc_update)++crc_calls;
}
void __attribute__((no_instrument_function)) __cyg_profile_func_exit(void *f,void *caller) {(void)f;(void)caller;}
unsigned __attribute__((no_instrument_function)) test_crc_calls(void) {return crc_calls;}
void __attribute__((no_instrument_function)) test_crc_reset(void) {crc_calls=0;}
''')
        subprocess.run(['cc','-std=c17','-Wall','-Wextra','-Werror',
                        '-Wno-misleading-indentation','-fsanitize=undefined',
                        '-fPIC','-shared','-finstrument-functions','-fno-inline','-Wl,-Bsymbolic',
                        '-I'+str(ROOT/'tests/sdserve_host'),str(probe),
                        str(ROOT/'tests/sdserve_host/fs.c'),'-o',str(lib)],check=True)
        cls.lib=C.CDLL(str(lib));cls.lib.service_request.argtypes=[C.c_char_p,C.c_uint,C.c_void_p]
    @classmethod
    def tearDownClass(cls): cls.build.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.disk=Path(self.temp.name)
        (self.disk/'test').mkdir();self.lib.fs_root(str(self.disk).encode())
        self.assertEqual(self.lib.service_init_mode(b'/test',101,self.FAST),1)
        self.lib.test_crc_reset();self.seq=0;self.sid=19;self.rpc(1)
    def tearDown(self):
        self.lib.service_stop();self.assertEqual(self.lib.fs_live_files(),0);self.temp.cleanup()
        if self.FAST:self.assertEqual(self.lib.test_crc_calls(),0,'Fast engine performed CRC work')
        else:self.assertGreater(self.lib.test_crc_calls(),0,'Instrumentation must see checked CRC work')
    def wire(self,*args):return wire(*args,fast=self.FAST)
    def send(self,request):
        out=C.create_string_buffer(240);n=self.lib.service_request(request,len(request),out)
        if not n:return None
        b=out.raw[:n];self.assertEqual(b[2],2 if self.FAST else 1)
        self.assertEqual(S.unpack_from('<I',b,16)[0],0 if self.FAST else zlib.crc32(b[:16]+b[20:]))
        self.assertEqual(b[4:13],request[4:13]);return b[13],b[20:]
    def rpc(self,op,p=b'',status=0):
        self.seq+=1;self.last=self.wire(self.sid,self.seq,op,p);result=self.send(self.last)
        self.assertIsNotNone(result);self.assertEqual(result[0],status);return result[1]
    def begin(self,data,name='/test/game.bin'):
        return self.rpc(5,S.pack('<III',73,len(data),0 if self.FAST else zlib.crc32(data))+path(name))
    def stage(self,data):
        self.begin(data)
        for at in range(0,len(data),212):self.rpc(6,S.pack('<II',73,at)+data[at:at+212])
        self.rpc(7,S.pack('<I',73))
    def move_descriptor(self,source,destination):
        a=source.encode();b=destination.encode()
        return S.pack('<BBHHH',6,0,len(a),len(b),0)+a+b
    def move_frag(self,d,offset=0,count=184,status=0,crc=None):
        return self.rpc(14,S.pack('<HHI',len(d),offset,(0 if self.FAST else zlib.crc32(d)) if crc is None else crc)+d[offset:offset+count],status)
    def read(self,name,at,count,status=0):
        return self.rpc(4,S.pack('<IH',at,count)+path(name),status)
    def counts(self):
        return tuple(self.lib.fs_calls(op) for op in (1,10,9,2,4))
    def test_sequential_download_filesystem_cost_and_eof_replay(self):
        data=random.Random(31).randbytes(1000);(self.disk/'test/read.bin').write_bytes(data)
        self.lib.fs_counts_reset()
        for at in range(0,len(data),216):
            self.assertEqual(self.read('/test/read.bin',at,216),S.pack('<I',len(data))+data[at:at+216])
        self.assertEqual(self.counts(),(1,1,0,5,1) if self.FAST else (5,5,5,5,5))
        before=self.counts();self.assertEqual(self.send(self.last),(0,S.pack('<I',1000)+data[864:]))
        self.assertEqual(self.counts(),before);self.assertEqual(self.lib.fs_live_files(),0)
    def test_random_offsets_path_switch_and_metadata(self):
        a=bytes(range(200));b=b'different source';(self.disk/'test/a').write_bytes(a);(self.disk/'test/b').write_bytes(b)
        self.lib.fs_counts_reset()
        for at in (80,100,20):
            self.assertEqual(self.read('/test/a',at,20),S.pack('<I',200)+a[at:at+20])
        self.assertEqual(self.counts(),(1,1,2,3,0) if self.FAST else (3,3,3,3,3))
        self.assertEqual(self.read('/test/b',0,1),S.pack('<I',len(b))+b[:1])
        self.assertEqual(self.lib.fs_live_files(),1 if self.FAST else 0)
        self.rpc(2,path('/test/a'));self.assertEqual(self.lib.fs_live_files(),0)
        self.assertEqual(self.counts(),(2,2,2,4,2) if self.FAST else (4,4,4,4,4))
    def test_empty_zero_count_and_eof(self):
        (self.disk/'test/empty').write_bytes(b'');(self.disk/'test/data').write_bytes(b'abc')
        for name,at,count,want in [('empty',0,216,b''),('data',0,0,b''),('data',3,0,b''),('data',2,216,b'c')]:
            size=0 if name=='empty' else 3
            self.assertEqual(self.read('/test/'+name,at,count),S.pack('<I',size)+want)
        self.assertEqual(self.lib.fs_live_files(),0)
    def test_reader_closes_on_request_and_filesystem_failures(self):
        (self.disk/'test/data').write_bytes(b'abcdef')
        for fault in (1,2,4,9,10):
            with self.subTest(fault=fault):
                self.lib.service_stop();self.lib.fs_fault(fault,1)
                # at1 requires a seek; count216 reaches EOF and requires close.
                self.assertEqual(self.read('/test/data',1,216,6),b'\x01')
                self.assertEqual(self.lib.fs_live_files(),0)
                self.assertEqual(self.read('/test/data',0,216),S.pack('<I',6)+b'abcdef')
        for payload in (S.pack('<IH',0,217)+path('/test/data'),S.pack('<IH',0,1)+path('/outside'),b'',S.pack('<IH',7,1)+path('/test/data')):
            self.read('/test/data',0,1)
            self.rpc(4,payload,1);self.assertEqual(self.lib.fs_live_files(),0)
    def test_reader_replay_stale_and_session_change(self):
        (self.disk/'test/data').write_bytes(b'abcdef');self.read('/test/data',0,1)
        before=self.counts();last=self.last
        self.assertEqual(self.send(last),(0,S.pack('<I',6)+b'a'))
        self.assertEqual(self.send(self.wire(self.sid,self.seq,4,b'conflict'))[0],5)
        self.assertEqual(self.send(self.wire(self.sid+1,1,4,b''))[0],4)
        self.assertEqual(self.counts(),before)
        self.sid+=1;self.seq=0;self.rpc(1)
        self.assertEqual(self.lib.fs_live_files(),0)
        self.read('/test/data',1,1);self.lib.service_stop();self.assertEqual(self.lib.fs_live_files(),0)
        self.assertEqual(self.lib.service_init_mode(b'/test',102,self.FAST),1)
        self.seq=0;self.rpc(1);self.read('/test/data',0,1)
        self.assertEqual(self.lib.service_init_mode(b'/test',103,self.FAST),1)
        self.assertEqual(self.lib.fs_live_files(),0)
    def test_reader_close_failure_blocks_mutation_and_exit(self):
        if not self.FAST:self.skipTest('Persistent reader is fast-only')
        source=self.disk/'test/data';source.write_bytes(b'abcdef')
        for op,payload in ((13,b'\0'+path('/test/data')),(11,b'')):
            self.read('/test/data',0,1);self.lib.fs_fault(4,1)
            self.assertEqual(self.rpc(op,payload,6),b'\x01')
            self.assertTrue(source.exists());self.assertEqual(self.lib.service_exiting(),0)
            self.assertEqual(self.lib.fs_live_files(),0)
        self.rpc(11);self.assertEqual(self.lib.service_exiting(),1)
    def test_reader_closes_before_source_replacement(self):
        source=self.disk/'test/game.bin';source.write_bytes(b'abcdef');self.read('/test/game.bin',0,1)
        self.stage(b'new');self.rpc(8,S.pack('<I',73))
        self.assertEqual(self.read('/test/game.bin',0,216),S.pack('<I',3)+b'new')
        self.rpc(13,b'\0'+path('/test/game.bin'));self.assertFalse(source.exists())
    def test_root_metadata_uses_directory_api(self):
        self.lib.service_stop()
        self.assertEqual(self.lib.service_init_mode(b'/',101,self.FAST),1)
        self.seq=0;self.rpc(1)
        self.assertEqual(self.rpc(2,path('/')),S.pack('<IB',0,16))
    def test_directory_primitives_and_guards(self):
        self.rpc(12,path('/test/new'));self.assertTrue((self.disk/'test/new').is_dir())
        self.rpc(12,path('/test/new'),6)
        self.rpc(13,b'\x01'+path('/test/new'));self.assertTrue((self.disk/'test/new').exists())
        (self.disk/'test/new/file').write_bytes(b'keep')
        self.rpc(13,b'\x00'+path('/test/new'),6)
        for p in ('/test','/TEST','/test/../else','/test/a.p17part','/test/X.P17BAK','/test/sdserve.bin','/'):
            self.rpc(12,path(p),1);self.rpc(13,b'\x01'+path(p),1)
        self.rpc(13,b'\x00'+path('/test/new/file'));self.rpc(13,b'\x00'+path('/test/new'))
        self.assertFalse((self.disk/'test/new').exists())
    def test_move_full_paths_final_only_replay_and_collision(self):
        a='/test/'+('a'*114);b='/test/'+('b'*114);(self.disk/a[1:]).write_bytes(b'payload')
        d=self.move_descriptor(a,b);self.assertEqual(len(d),248)
        self.assertEqual(self.move_frag(d),S.pack('<HB',184,0));self.assertTrue((self.disk/a[1:]).exists())
        self.assertEqual(self.move_frag(d,184),S.pack('<HB',248,1))
        self.assertEqual(self.send(self.last),(0,S.pack('<HB',248,1)))
        self.assertFalse((self.disk/a[1:]).exists());self.assertEqual((self.disk/b[1:]).read_bytes(),b'payload')
        (self.disk/'test/other').write_bytes(b'old');self.move_frag(self.move_descriptor(b,'/test/other'),status=6)
        self.assertEqual((self.disk/'test/other').read_bytes(),b'old')
    def test_move_fragments_cancelled_by_interleave_and_bad_identity(self):
        a='/test/'+('a'*114);b='/test/'+('b'*114);(self.disk/a[1:]).write_bytes(b'x');d=self.move_descriptor(a,b)
        self.move_frag(d);self.rpc(2,path(a));self.move_frag(d,184,status=1)
        self.move_frag(d);self.move_frag(d,183,status=1)
        if self.FAST:self.move_frag(d,crc=1,status=1)
        else:self.move_frag(d,crc=0);self.move_frag(d,184,crc=0,status=7)
        self.assertTrue((self.disk/a[1:]).exists());self.assertFalse((self.disk/b[1:]).exists())
    def test_move_relationships_reserved_and_fault(self):
        (self.disk/'test/dir').mkdir();(self.disk/'test/dir/a').write_bytes(b'x')
        for a,b in [('/test','/test/z'),('/test/dir','/test/dir/sub'),('/test/dir/a','/test/dir'),('/test/dir/a','/test/x.p17meta'),('/test/dir/a','/test/DIR/A')]:
            self.move_frag(self.move_descriptor(a,b),status=1)
        self.lib.fs_fault(6,1);self.move_frag(self.move_descriptor('/test/dir/a','/test/b'),status=6)
        self.assertEqual((self.disk/'test/dir/a').read_bytes(),b'x')
    def test_directory_mutations_busy_during_stage(self):
        self.begin(b'x');self.rpc(12,path('/test/new'),3);self.rpc(13,b'\x00'+path('/test/game.p17part'),3)
        self.move_frag(self.move_descriptor('/test/a','/test/b'),status=3)
        self.rpc(9,S.pack('<I',73))

    def test_empty_binary_boundaries_and_game_size(self):
        for size in (0,1,211,212,213,256,65536,131731):
            with self.subTest(size=size):
                data=random.Random(size).randbytes(size);self.stage(data)
                before=self.last;self.assertEqual(self.send(before),(0,S.pack('<II',size,0 if self.FAST else zlib.crc32(data))))
                self.rpc(8,S.pack('<I',73))
                result=bytearray()
                for at in range(0,max(1,size),216):
                    p=self.rpc(4,S.pack('<IH',at,216)+path('/test/game.bin'))
                    self.assertEqual(S.unpack_from('<I',p)[0],size);result.extend(p[4:])
                self.assertEqual(bytes(result),data)
                self.assertEqual((self.disk/'test/game.bin').read_bytes(),data)
                self.rpc(10,b'\x03'+path('/test/game.bin'))
    def test_replay_conflict_corruption_sequence_and_session(self):
        self.begin(b'abcd');self.rpc(6,S.pack('<II',73,0)+b'abcd')
        self.assertEqual(self.send(self.last),(0,S.pack('<II',73,4)))
        self.assertEqual(self.send(self.wire(self.sid,self.seq,6,b'different'))[0],5)
        self.assertEqual(self.send(self.wire(self.sid,self.seq+2,7,S.pack('<I',73)))[0],5)
        self.assertEqual(self.send(self.wire(22,1,1))[0],3)
        damaged=bytearray(self.last);damaged[-1]^=128
        if self.FAST:self.assertEqual(self.send(bytes(damaged))[0],5)
        else:self.assertIsNone(self.send(bytes(damaged)))
        self.rpc(7,S.pack('<I',73));self.rpc(9,S.pack('<I',73))
        self.assertEqual(self.send(self.wire(22,1,1))[0],0)
    def test_root_traversal_nul_and_bounds(self):
        for p in ('/else','/test/../else','/test//game','/test/a.','/test/a ', '/test/a:b', '/test/a\\b'):
            self.rpc(2,path(p),1)
        self.rpc(2,b'\x08/test/a\0',1)
        self.rpc(4,S.pack('<IH',0,217)+path('/test/game.bin'),1)
        self.rpc(5,S.pack('<III',1,0,0)+path('/test/game.p17bak'),1)
    def test_staged_path_reserves_room_for_readback(self):
        long_name='/test/'+('a'*107)
        self.assertEqual(len(long_name),113)
        self.rpc(5,S.pack('<III',1,0,0)+path(long_name),1)
        self.assertEqual(list((self.disk/'test').iterdir()),[])
        self.begin(b'',long_name[:-1]);self.rpc(7,S.pack('<I',73))
        self.assertEqual(self.rpc(4,S.pack('<IH',0,1)+path(long_name[:-1]+'.p17part')),b'\0'*4)
        self.rpc(9,S.pack('<I',73))
    def test_bad_transfer_is_an_accepted_error_not_a_stale_session(self):
        self.begin(b'a')
        for op in (6,7,8,9):
            payload=S.pack('<I',74)+(S.pack('<I',0)+b'a' if op==6 else b'')
            self.rpc(op,payload,1)
        self.rpc(6,S.pack('<II',73,0)+b'a');self.rpc(7,S.pack('<I',73))
        self.rpc(9,S.pack('<I',73))
    def test_disk_full_sync_and_close_failure_preserve_target(self):
        old=self.disk/'test/game.bin';old.write_bytes(b'old')
        for op in (3,8):  # short write and hard device error
            self.begin(b'data');self.lib.fs_fault(op,1)
            self.rpc(6,S.pack('<II',73,0)+b'data',6)
            self.assertEqual(old.read_bytes(),b'old')
            self.assertEqual(self.rpc(10,b'\0'+path('/test/game.bin')),b'\x07')
            self.rpc(10,b'\x02'+path('/test/game.bin'))
        for op in (4,5):
            self.begin(b'data');self.rpc(6,S.pack('<II',73,0)+b'data')
            self.lib.fs_fault(op,1);self.rpc(7,S.pack('<I',73),6)
            self.assertEqual(old.read_bytes(),b'old');self.rpc(10,b'\x02'+path('/test/game.bin'))
    def test_interrupted_rename_restore_and_cleanup(self):
        old=self.disk/'test/game.bin';old.write_bytes(b'old')
        self.stage(b'new');self.lib.fs_fault(6,2);self.rpc(8,S.pack('<I',73),6)
        self.assertFalse(old.exists());self.assertEqual((self.disk/'test/game.bin.p17bak').read_bytes(),b'old')
        self.assertEqual(self.rpc(10,b'\0'+path('/test/game.bin')),b'\x0e')
        self.rpc(10,b'\x01'+path('/test/game.bin'));self.rpc(10,b'\x02'+path('/test/game.bin'))
        self.assertEqual(old.read_bytes(),b'old')
    def test_journal_retirement_failure_and_corruption(self):
        (self.disk/'test/game.bin').write_bytes(b'old');self.stage(b'new')
        self.lib.fs_fault(7,1);self.rpc(8,S.pack('<I',73),6)
        self.assertEqual(self.rpc(10,b'\0'+path('/test/game.bin')),b'\x0d')
        self.rpc(10,b'\x02'+path('/test/game.bin'));self.rpc(10,b'\x03'+path('/test/game.bin'))
        self.stage(b'again');self.lib.service_stop()
        meta=self.disk/'test/game.bin.p17meta';meta.write_bytes(b'bad')
        self.assertEqual(self.rpc(10,b'\0'+path('/test/game.bin')),b'\x17')
        self.rpc(10,b'\x02'+path('/test/game.bin'),8)
    def test_read_error_and_listing(self):
        (self.disk/'test/a').write_bytes(b'data');self.lib.fs_fault(2,1)
        self.rpc(4,S.pack('<IH',0,4)+path('/test/a'),6)
        p=self.rpc(3,S.pack('<I',0)+path('/test'))
        self.assertEqual(p[4],0);self.assertEqual(p[11:],b'a')
        self.assertEqual(self.rpc(3,S.pack('<I',1)+path('/test'))[4],1)
    def test_unfinished_stage_survives_stop(self):
        (self.disk/'test/game.bin').write_bytes(b'old');self.begin(b'data')
        self.rpc(6,S.pack('<II',73,0)+b'da');self.lib.service_stop()
        self.lib.service_init_mode(b'/test',102,self.FAST);self.sid=20;self.seq=0;self.rpc(1)
        self.assertEqual(self.rpc(10,b'\0'+path('/test/game.bin')),b'\x07')
        self.rpc(10,b'\x02'+path('/test/game.bin'))
    def test_first_upload_orphan_can_be_explicitly_abandoned(self):
        self.begin(b'data');self.rpc(6,S.pack('<II',73,0)+b'da')
        self.lib.service_stop();self.lib.service_init_mode(b'/test',103,self.FAST)
        self.sid=21;self.seq=0;self.rpc(1)
        self.assertEqual(self.rpc(10,b'\0'+path('/test/game.bin')),b'\x06')
        self.rpc(10,b'\x02'+path('/test/game.bin'))
        self.assertEqual(list((self.disk/'test').iterdir()),[])

    def test_mode_and_verification_read_cost(self):
        self.assertEqual(S.unpack('<IHH',self.rpc(1)),(101,212,47|(80 if self.FAST else 0)))
        data=bytes(range(256))*16
        before=self.lib.fs_read_bytes()
        self.stage(data);self.rpc(8,S.pack('<I',73))
        self.assertEqual(self.lib.fs_read_bytes()-before,20+(0 if self.FAST else 2*len(data)))
        self.assertEqual((self.disk/'test/game.bin').read_bytes(),data)

    def test_fast_reserved_crc_refused_and_checked_bad_digest_rejected(self):
        if self.FAST:
            self.rpc(5,S.pack('<III',73,4,123)+path('/test/game.bin'),1)
        self.rpc(5,S.pack('<III',73,4,0 if self.FAST else 123)+path('/test/game.bin'))
        self.rpc(6,S.pack('<II',73,0)+b'data')
        self.rpc(7,S.pack('<I',73),0 if self.FAST else 7)
        if self.FAST:
            self.rpc(8,S.pack('<I',73))
            self.assertEqual((self.disk/'test/game.bin').read_bytes(),b'data')

    def test_post_finish_corruption_demonstrates_mode_tradeoff(self):
        self.stage(b'good')
        (self.disk/'test/game.bin.p17part').write_bytes(b'evil')
        self.rpc(8,S.pack('<I',73),0 if self.FAST else 7)
        self.assertEqual((self.disk/'test/game.bin').read_bytes(),b'evil')

    def test_self_overwrite_and_early_finish_still_rejected(self):
        self.rpc(5,S.pack('<III',73,0,0)+path('/test/SdSeRvE.BiN'),1)
        self.begin(b'abcd');self.rpc(6,S.pack('<II',73,0)+b'ab')
        self.rpc(7,S.pack('<I',73),7);self.rpc(9,S.pack('<I',73))

class FastSdserveTests(SdserveTests):
    FAST=1

    def test_checked_packet_is_refused_without_crc_work(self):
        self.assertIsNone(self.send(wire(self.sid,self.seq+1,1)))
        bad=bytearray(self.wire(self.sid,self.seq+1,1));bad[16]=1
        self.assertIsNone(self.send(bytes(bad)))

    def test_checked_metadata_is_preserved_without_crc_work(self):
        metadata=b'SDT1'+S.pack('<III',73,4,zlib.crc32(b'data'))
        metadata+=S.pack('<I',zlib.crc32(metadata))
        (self.disk/'test/game.bin.p17meta').write_bytes(metadata)
        (self.disk/'test/game.bin.p17part').write_bytes(b'data')
        self.assertEqual(self.rpc(10,b'\0'+path('/test/game.bin')),bytes([22]))
        self.rpc(10,b'\x02'+path('/test/game.bin'),8)
        self.assertEqual((self.disk/'test/game.bin.p17meta').read_bytes(),metadata)
        self.assertEqual((self.disk/'test/game.bin.p17part').read_bytes(),b'data')

    def test_fast_metadata_and_size_only_recovery(self):
        self.stage(b'data')
        meta=self.disk/'test/game.bin.p17meta'
        self.assertEqual(meta.read_bytes(),b'SDT2'+S.pack('<IIII',73,4,0,0))
        self.lib.service_stop();self.lib.service_init_mode(b'/test',104,1)
        self.sid=22;self.seq=0;self.rpc(1)
        (self.disk/'test/game.bin.p17part').unlink()
        (self.disk/'test/game.bin').write_bytes(b'bad')
        self.rpc(10,b'\x02'+path('/test/game.bin'),7)
        self.assertTrue(meta.exists())
        (self.disk/'test/game.bin').write_bytes(b'good')
        self.rpc(10,b'\x02'+path('/test/game.bin'))
        self.assertFalse(meta.exists())

if __name__=='__main__':unittest.main()
