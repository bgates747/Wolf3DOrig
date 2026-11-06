"""One explicit clean P4 initialization, then one Agon reset; no replay.
Selected outside timing after each native installation, including restoration.
Run with the maintained Extender interpreter, which already provides esptool.
"""
from pathlib import Path
import json,subprocess,time,sys
ROOT=Path('/Agon/mystuff/agon-extender')
sys.path.insert(0,str(ROOT/'scripts'))
import serial
from esptool.reset import HardReset
from p4_boot_guard import check_startup
BUILD=b'net-004-r03-b2026-11-06-04-38-03Z'
PAD=b'Parallel boot pads released; awaiting EMOS'
CONSOLE=b'ExCom console '+BUILD+b' (experimental), UART1 1152000 8N1 RTS/CTS'
def save(path,value):
 with Path(path).open('x')as stream:json.dump(value,stream,indent=2);stream.write('\n')
def clean_bootstrap(b,folder):
 p=folder/'clean-bootstrap';p.mkdir(exist_ok=False)
 assert len(b.c['ports'])==2 and 'Espressif'in b.c['ports'][1]
 b.own();assert not b.get('/sd/status')['online']and b.get('/sd/fast')['phase']==0
 raw=bytearray();port=b.c['ports'][1];handle=serial.Serial(port=None,baudrate=115200,timeout=.15,exclusive=True);handle.dtr=handle.rts=False;handle.port=port
 try:
  b.own();handle.open();handle.reset_input_buffer();save(p/'p4-reset-issued.json',dict(epoch=time.time(),once=True,port=port,no_flash=True,build=BUILD.decode()))
  HardReset(handle,uses_usb=True).reset();deadline=time.monotonic()+60;since=None
  while time.monotonic()<deadline:
   raw.extend(handle.read(8192));check_startup(bytes(raw),PAD)
   if PAD not in raw or b'build_id='+BUILD not in raw:continue
   try:d=b.get('/display/status')
   except OSError:continue
   if d.get('available')and not d.get('rolling',{}).get('faults'):
    if since is None:since=time.monotonic()
    if time.monotonic()-since>=5:break
   else:since=None
  else:raise TimeoutError('Clean current P4 PAD/build/display missing; no Agon reset')
  assert raw.count(PAD)==1
  save(p/'p4-initialized.json',dict(epoch=time.time(),build=BUILD.decode(),pad_once=True,display=d))
  root=Path('/Agon/mystuff/agon-extender');argv=[str(root/'.venv/bin/python'),str(root/'scripts/reset_agon_usb.py'),'--config',str(root/'agents/bench-reset/usb-reset.local.json'),'--verify-url',b.url,'--verify-timeout','60']
  b.own();save(p/'agon-reset-issued.json',dict(epoch=time.time(),once=True,argv=argv,p4_clean_before_dispatch=True))
  with(p/'agon-reset.log').open('x')as log:
   child=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT);deadline=time.monotonic()+75
   try:
    while child.poll()is None:
     raw.extend(handle.read(8192));check_startup(bytes(raw),PAD);assert time.monotonic()<deadline,'Agon reset helper bound'
    assert child.wait()==0,'Fresh Agon admission failed; no automatic retry'
   finally:
    if child.poll()is None:child.terminate();child.wait(timeout=5)
  deadline=time.monotonic()+15;since=None
  while time.monotonic()<deadline:
   raw.extend(handle.read(8192));check_startup(bytes(raw),CONSOLE);k=b.get('/keyboard/status');d=b.get('/display/status')
   if CONSOLE in raw and k['ready']and k['physical_neutral']and not k['held']and not k['pending']and d['available']and not d.get('rolling',{}).get('faults'):
    if since is None:since=time.monotonic()
    if time.monotonic()-since>=2:break
   else:since=None
  else:raise TimeoutError('Current console/neutral input missing; no guest dispatch')
  assert raw.count(PAD)==1 and raw.count(CONSOLE)==1
  save(p/'admission.json',dict(epoch=time.time(),p4_build=BUILD.decode(),keyboard=k,display=d,p4_resets=1,agon_resets=1,no_flash=True,no_replay=True))
 finally:(p/'p4-boot.bin').write_bytes(raw);handle.close()
