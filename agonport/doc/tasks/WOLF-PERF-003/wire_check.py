"""Validate actual timed request bytes against completed guest records; no device."""
from pathlib import Path
import argparse,hashlib,json,struct

def check(profile):
 profile=Path(profile);wire=(profile/'last-run/mos-to-vdp.bin').read_bytes()
 timing=profile/'run/timing.bin'
 if not timing.exists():timing=profile/'sdcard/wolf3d/timing.bin'
 t=timing.read_bytes();assert t[:5]==b'WPF3\1'and t[5]in(2,3)
 count=int.from_bytes(t[8:11],'little');backend=t[32];assert backend in(1,2)and 0<count<=600
 if backend==1:
  marker=bytes.fromhex('1700a001004af0');positions=[i for i in range(len(wire))if wire.startswith(marker,i)]
  assert len(positions)==1;pos=positions[0]+11
 else:
  marker=bytes.fromhex('1700d80c000102');positions=[];start=0
  while True:
   start=wire.find(marker,start)
   if start<0:break
   if int.from_bytes(wire[start+13:start+15],'little')==100:positions.append(start)
   start+=17
  assert len(positions)==1;pos=positions[0]+17
 begin=pos;generations=[];tokens=[]
 for i in range(count):
  row=t[33+i*27:33+(i+1)*27];angle=int.from_bytes(row[3:6],'little');pose=struct.pack('<iiH',0x228000,0x248000,angle)
  if backend==1:
   expected=bytes.fromhex('1700a001004a02')+pose+bytes.fromhex('1700a001004a07')
   assert wire[pos:pos+24]==expected,(i,pos,'pose/render');pos+=24
  else:
   assert wire[pos:pos+14]==bytes.fromhex('1700a00171021700a00171001c00'),(i,pos,'clear/write')
   payload=wire[pos+14:pos+42];assert payload[:6]==b'W3DU\2\x10'and payload[8:12]==bytes.fromhex('1c000100')
   assert payload[16:]==bytes([2,10])+pose,(i,pos,'player-only batch')
   generations.append(int.from_bytes(payload[12:16],'little'))
   assert wire[pos+42:pos+48]==bytes.fromhex('1700a001710e')
   run=wire[pos+48:pos+65];assert run[:7]==marker and run[9:11]==b'\1\0'and run[13:17]==bytes.fromhex('01000371')
   tokens.append(int.from_bytes(run[7:9],'little'));pos+=65
  if t[5]==3:
   assert wire[pos:pos+6]==bytes.fromhex('1700c3170086'),(i,pos,'present/fence');pos+=6
 if t[5]==2:
  assert wire[pos:pos+6]==bytes.fromhex('1700c3170086');pos+=6
 if backend==1:assert wire[pos:pos+7]==bytes.fromhex('1700a001004af1')
 else:
  assert wire[pos:pos+7]==bytes.fromhex('1700d80c000105')
  assert all(b==a+1 for a,b in zip(generations,generations[1:]))
  assert all(b==(a+1)%65536 for a,b in zip(tokens,tokens[1:]))
 return {'schema':'wolf-perf003-wire-check-v1','backend':'bespoke'if backend==1 else'vdplet','mode':'unpaced'if t[5]==2 else'paced','completed_requests':count,'request_bytes_per_frame':24 if backend==1 else 65,'present_fence_bytes_per_frame':6 if t[5]==3 else 0,'post_timing_final_present_bytes':6 if t[5]==2 else 0,'trace_start':begin,'trace_end':pos,'verified_request_region_bytes':pos-begin,'sha256':hashlib.sha256(wire).hexdigest(),'interpretation':'Byte/pose correspondence only; no physical link-time or FPS inference.'}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('profile',type=Path);args=parser.parse_args();print(json.dumps(check(args.profile),indent=2))
