"""Decode bounded loading sender observations, never treat them as UART delivery proof."""
from pathlib import Path
import argparse,json
HEADER=64
SIZE=128
CAPACITY=32
FILE_BYTES=HEADER+SIZE*(CAPACITY+1)
MASK=(1<<24)-1

def u24(data,at):return int.from_bytes(data[at:at+3],'little')

def record(data):
 if len(data)!=SIZE:raise ValueError('record size')
 if not any(data):return None
 if data[3]not in (1,2,3)or data[79]not in (0,1):raise ValueError('phase/returned')
 if any(data[107:]):raise ValueError('nonzero reserved record bytes')
 if data[26:29]!=bytes((23,0,0x86))or u24(data,32)!=3:raise ValueError('query descriptor changed')
 times={name:u24(data,at)for name,at in (('paint_begin',35),('paint_end',38),('present_begin',41),('present_end',44),('clear_begin',47),('clear_end',50),('tx_begin',53),('tx_end',56),('wait_begin',59),('wait_end',62))}
 durations={name:(times[end]-times[start])&MASK for name,start,end in (('paint','paint_begin','paint_end'),('present','present_begin','present_end'),('clear','clear_begin','clear_end'),('query_call','tx_begin','tx_end'),('wait_window','wait_begin','wait_end'))}
 if not data[79]:durations={name:None for name in durations} # unfinished current snapshot has no validated end markers
 return dict(fence=u24(data,0),phase=data[3],stage_pointer=u24(data,4),count=u24(data,7),total=u24(data,10),buffer_id=int.from_bytes(data[13:15],'little'),declared_bytes=int.from_bytes(data[15:19],'little'),stream_remaining=u24(data,19),last_block_bytes=u24(data,22),mbase=data[25],query_pointer=u24(data,29),query_bytes=data[26:29].hex(),times_raw_mos=times,durations_raw_mos=durations,send_return=dict(a=data[65],f=data[66],carry=bool(data[66]&1),hl=u24(data,67),bc=u24(data,70)),mode_flags=dict(before_clear=data[73],after_clear=data[74],after_tx=data[75],after_wait=data[76]),wait_status=data[77],wait_passes=data[78],returned=bool(data[79]),serial_flags_before=data[80],serial_flags_after=data[81],backend_before=data[82],backend_after=data[83],emos_reply_parser_nonatomic=dict(state_before=data[84],state_after=data[85],cmd=data[86],length=data[87],pointer=u24(data,88),data=data[91:107].hex()))

def decode(data):
 if len(data)!=FILE_BYTES:raise ValueError('file size')
 if data[:7]!=b'WPQ3'+bytes((1,SIZE,CAPACITY)):raise ValueError('schema')
 nxt,valid,frozen,returned,error=data[7:12]
 if nxt>=CAPACITY or valid>CAPACITY or any(n>1 for n in (frozen,returned,error,data[18],data[19])):raise ValueError('header bounds')
 if any(data[20:HEADER]):raise ValueError('nonzero reserved header')
 total=u24(data,12)
 if valid!=min(total,CAPACITY)or nxt!=total%CAPACITY:raise ValueError('ring accounting')
 slots=[data[HEADER+SIZE*(1+i):HEADER+SIZE*(2+i)]for i in range(CAPACITY)]
 order=list(range(valid))if valid<CAPACITY else list(range(nxt,CAPACITY))+list(range(nxt))
 rows=[record(slots[i])for i in order]
 if any(r is None or not r['returned']for r in rows):raise ValueError('missing completed ring record')
 if [r['fence']for r in rows]!=list(range(total-valid+1,total+1)):raise ValueError('sequence')
 if valid<CAPACITY and any(any(s)for s in slots[valid:]):raise ValueError('nonzero unused ring slot')
 current=record(data[HEADER:HEADER+SIZE])
 if rows and current is None:raise ValueError('missing current record')
 return dict(schema='wolf-query-trace04',main_returned=bool(returned),loading_error=error,frozen=bool(frozen),loading_ready=bool(data[19]),save_failed=bool(data[18]),completed_fences=total,total_assets=u24(data,15),current=current,history=rows,limits='Nominal MOS ticks and non-atomic sender/reply-parser RAM snapshots; not per-byte UART timing, VDP grammar or a render measurement.')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('path',type=Path);a=p.parse_args()
 print(json.dumps(decode(a.path.read_bytes()),indent=2))
