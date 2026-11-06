"""Explicit failed paced-hold recovery; no guest replay or new test.

Known wp_failed self-loop; timer-restored marker observed. Standing ordinary
Agon recovery, verified unchanged setup-only startup. Installed init.asm keeps
external RAM when warmboot magic survives; SAVE before ANY LOAD, validate bytes
later. Never claim reset preserves every MOS/global/VDP state.
"""
from pathlib import Path
import hashlib,json,sys,time,uuid
from urllib.request import Request,urlopen
from physical02 import Bench,B,save,E
b=Bench(B/'context.json');p=b.folder('paced-failure-collection')
assert b.components['startup_sha256']==hashlib.sha256((b.out/'entry/startup.bin').read_bytes()).hexdigest()
assert b'RUN'not in(b.out/'entry/startup.bin').read_bytes().upper()
source=B/'bespoke/paced/source'
assert b'@hold: jr @hold'in(source/'bench.inc').read_bytes()
assert b'WOLF-PERF-003 FAILED TIMER-RESTORED'in(b.out/'04-bespoke-paced/serial.bin').read_bytes()
sys.path.insert(0,str(E/'scripts'))
from reset_agon import status,wait_boot
c=json.loads((E/'agents/release001/live-preparation-r01/config.json').read_text())
b.own();before=status(b.url);request_id=str(uuid.uuid4())
save(p/'reset-issued.json',dict(epoch=time.time(),once=True,id=request_id,before=before,reason='Known wp_failed hold; standing Agon-first recovery, no application replay',startup_verified=True))
request=Request(c['reset_url'],method='POST',data=json.dumps({'id':request_id}).encode(),headers={'Origin':b.url,'Content-Type':'application/json','X-Agon-Reset':'1'})
with urlopen(request,timeout=15)as response:result=json.load(response)
save(p/'reset-response.json',result)
after=wait_boot(b.url,before['boot'],45);save(p/'reset-admission.json',after)
b.cli(p,'recovery-cli');b.service(p,'listener');b.raw_state(p,'pre')
size=(source/'wolf3d.bin').stat().st_size
script=p/'save.txt';script.write_bytes(('SAVE '+b.remote+'/paced-failure-ram.bin &40000 &'+format(size,'X')+'\r\nEMOS sdserve --fast /\r\n').encode())
b.upload(p,'save-script',script,b.remote+'/paced-failure-save.txt')
b.exit(p,'save-exit');b.line(p,'save-ram','EXEC '+b.remote+'/paced-failure-save.txt');b.wait_online(True)
b.transfer(p,'ram','get',b.remote+'/paced-failure-ram.bin',p/'ram.bin');assert(p/'ram.bin').stat().st_size==size
# Retain every available failure artifact, not just successfully exported cases.
metadata=b.metadata(p,'files')
try:entries=list(metadata.entries(b.remote));save(p/'directory.json',entries)
finally:metadata.lock.close()
for remote,_,attr in entries:
 name=remote.rsplit('/',1)[-1]
 if name in ('before.bin','after.bin','stack.bin','timing.bin','native.bin','loading.bin'):
  assert not attr&16;b.transfer(p,name,'get',remote,p/name)
save(p/'receipt.json',dict(ordinary_agon_resets=1,P4_resets=0,LOAD_before_RAM_save=False,no_replay=True,ram_sha256=hashlib.sha256((p/'ram.bin').read_bytes()).hexdigest(),reset_may_reinitialize_MOS_and_VDP=True))
b.exit(p,'exit');b.flash('restore',B/'restore.bin');b.handback()
save(b.out/'paced-stopped-restored.json',dict(restored=True,benchmark_replayed=False,cases_dispatched=4,cases_passed=3,B_invoked=False))
print('PACED FAILURE RAM PRESERVED; EXACT INCOMING SPAN RESTORED; HANDBACK PASS',flush=True)
