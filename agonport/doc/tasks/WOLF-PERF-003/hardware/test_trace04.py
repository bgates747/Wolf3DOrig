"""Device-free schema checks for wrapped, failed, pending and corrupt observations."""
import unittest
from trace04 import *

def put24(data,at,value):data[at:at+3]=(value&MASK).to_bytes(3,'little')
def row(seq,failed=False,pending=False):
 d=bytearray(SIZE);put24(d,0,seq);d[3]=1;d[26:29]=bytes((23,0,0x86));put24(d,32,3)
 put24(d,53,MASK-2);put24(d,56,2);d[77]=15 if failed else 0;d[78]=10 if failed else 1;d[79]=not pending
 return d

def fixture(n=0,failed=False,pending=False):
 d=bytearray(FILE_BYTES);d[:7]=b'WPQ3'+bytes((1,SIZE,CAPACITY));d[7]=n%CAPACITY;d[8]=min(n,CAPACITY);d[9]=failed;d[10]=not pending;d[11]=failed;put24(d,12,n);d[19]=not failed and not pending
 for seq in range(max(1,n-CAPACITY+1),n+1):
  offset=HEADER+SIZE*(1+(seq-1)%CAPACITY);d[offset:offset+SIZE]=row(seq,failed and seq==n)
 if n:d[HEADER:HEADER+SIZE]=row(n,failed)
 if pending:d[HEADER:HEADER+SIZE]=row(n+1,pending=True)
 return d

class Trace(unittest.TestCase):
 def test_wrap_and_first_failure(self):
  for n in (0,1,31,32,33,845):
   d=decode(fixture(n,failed=n>0));self.assertEqual(d['completed_fences'],n)
   self.assertEqual(len(d['history']),min(n,CAPACITY))
   if n:self.assertEqual(d['history'][-1]['wait_status'],15);self.assertEqual(d['history'][-1]['durations_raw_mos']['query_call'],5)
 def test_inflight_not_called_complete(self):
  d=decode(fixture(33,pending=True));self.assertFalse(d['main_returned']);self.assertFalse(d['current']['returned']);self.assertEqual(d['current']['fence'],34);self.assertIsNone(d['current']['durations_raw_mos']['query_call'])
 def test_corruption_refused(self):
  good=fixture(33,True)
  for at in (0,4,5,6,7,8,9,10,11,18,19,20,HEADER+26,HEADER+107,HEADER+SIZE+3,HEADER+SIZE+79):
   bad=bytearray(good);bad[at]=255
   with self.assertRaises(ValueError,msg=str(at)):decode(bad)
  with self.assertRaises(ValueError):decode(good[:-1])
  bad=fixture(1);bad[HEADER+SIZE*3]=1
  with self.assertRaises(ValueError):decode(bad)

if __name__=='__main__':unittest.main()
