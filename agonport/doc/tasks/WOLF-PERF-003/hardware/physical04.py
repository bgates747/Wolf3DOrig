"""Finite loading-only consumer using retained reviewed transport, no benchmark dispatch."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess,time
from trace04 import decode,FILE_BYTES
T=Path(__file__).resolve().parents[1];B=T/'build/hardware04'
spec=importlib.util.spec_from_file_location('wolf_transport03',T/'hardware/physical03.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
# Reuse reviewed transport/flash/handback methods in this process only. Donor
# files, old kits and evidence remain unchanged. No inherited suite is invoked.
q.B=B
save=q.save
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

class LoadingFailure(RuntimeError):pass

class Bench(q.Bench):
 def __init__(self,context):
  self.c=json.loads(Path(context).read_text());self.grant=json.loads(Path(self.c['grant']).read_text())
  if 'active'in self.grant:self.grant=self.grant['active']
  assert self.grant['owner']=='wolf3dorig'and self.grant['task']=='WOLF-PERF-003-loading-r04'
  self.kit=json.loads((B/'kit.json').read_text());assert self.kit['ready']
  self.components=self.grant['entry_observation']['components'];assert self.components==self.kit['incoming_components']
  for name,digest in self.kit['inputs'].items():assert sha(name)==digest,name
  self.lease=self.grant['lease'];self.url=self.c['url'];self.port=self.c['native_port']
  self.remote='/test/wolf/perf003/load04';self.out=B/'evidence';self.out.mkdir(exist_ok=False)
  self.deadline=time.monotonic()+1800
  self.restoring=False
 def own(self):
  super().own()
  if not self.restoring:assert time.monotonic()<self.deadline,'Finite diagnostic dispatch deadline; retain custody on uncertainty'
 def entry(self):
  p=self.folder('entry');self.own();self.cli(p,'loading04-entry');self.service(p,'listener')
  for remote,name,key in [('/autoexec.txt','startup.bin','startup_sha256'),('/emos/sdserve.bin','listener.bin','listener_sha256')]:
   self.transfer(p,name,'get',remote,p/name);assert sha(p/name)==self.components[key]
  c=self.metadata(p,'fresh-namespace')
  try:
   assert not any(n[0].rstrip('/').lower()==self.remote.lower()for n in c.entries('/test/wolf/perf003')),'Fresh namespace collision: preserve, do not overwrite'
   c.make_directory(self.remote,parents=True)
   c.make_directory(self.remote+'/level_00',parents=True)
  finally:c.lock.close()
  # SAVE-only state helper, never LOAD; exact ROM/map-bound addresses.
  state=p/'state.txt';state.write_bytes(('SAVE '+self.remote+'/post-mode.bin &BC349 &1\r\nSAVE '+self.remote+'/post-callback.bin &BC38E &3\r\nEMOS sdserve --fast /\r\n').encode())
  self.upload(p,'state-script',state,self.remote+'/state.txt');self.raw_state(p,'raw')
  save(p/'receipt.json',dict(passed=True,actual_cli=True,mode0_callback0=True,fresh_namespace=True))
 def stage(self):
  p=self.folder('stage')
  for i,(name,local)in enumerate(self.kit['stage'].items()):
   assert time.monotonic()<self.deadline-600,'Dispatch budget'
   self.upload(p,f'file-{i:02d}',Path(local),self.remote+'/'+name)
  self.exit(p,'exit');save(p/'receipt.json',dict(passed=True,files=len(self.kit['stage'])))
 def clear_outputs(self,folder,label):
  # Prior copies have been independently retrieved before any successor load.
  c=self.metadata(folder,label)
  try:
   for name,_,attr in list(c.entries(self.remote)):
    if name.rsplit('/',1)[-1]in('loading.bin','loading3.bin'):
     assert not attr&16;c.remove(name)
  finally:c.lock.close()
 def invoke(self,folder,filename,marker,control=False):
  assert not control and filename=='a-loading04.bin'
  self.exit(folder,'invoke-exit');self.own();raw=bytearray();begin=time.monotonic()
  with q.m.open_passive_serial(self.port,baudrate=115200,timeout=.2)as serial:
   self.line(folder,'mirror','VDU 2');token=marker.encode()
   self.line(folder,'start-cue','VDU '+' '.join(map(str,token))+' 13 10')
   self.capture(serial,raw,folder,lambda r:token in r,20)
   for label,command in [('cd','CD '+self.remote),('load','LOAD '+filename)]:
    start=len(raw);self.line(folder,label,command)
    self.capture(serial,raw,folder,lambda r:self.remote.encode()+b' *'in r[start:],20)
   start=len(raw);self.line(folder,'run','RUN .')
   def done(r):
    tail=r[start:]
    if b'WOLF-PERF-003 FAILED'in tail:raise RuntimeError('Unexpected benchmark path reached')
    returned_banner=any(x in tail for x in (b'Thanks for playing Wolf3DOrig!',b'AGNB texture load failed',b'WOLF LOADING DIAGNOSTIC WRITE FAILED'))
    return returned_banner and self.remote.encode()+b' *'in tail
   self.capture(serial,raw,folder,done,300)
  self.service(folder,'return-listener');return time.monotonic()-begin
 def save_ram(self,folder,index):
  name=f'loading04-{index:02d}-ram.bin';script=folder/'save.txt'
  size=Path(self.kit['stage']['a-loading04.bin']).stat().st_size
  script.write_bytes(('SAVE '+self.remote+'/'+name+' &40000 &'+format(size,'X')+'\r\nEMOS sdserve --fast /\r\n').encode())
  self.upload(folder,'ram-script',script,self.remote+f'/save04-{index:02d}.txt')
  self.exit(folder,'ram-exit');self.line(folder,'save-ram','EXEC '+self.remote+f'/save04-{index:02d}.txt');self.wait_online(True)
  self.transfer(folder,'ram','get',self.remote+'/'+name,folder/'ram.bin')
  assert(folder/'ram.bin').stat().st_size==size
 def case(self,index):
  assert time.monotonic()<self.deadline-600,'Dispatch budget reserved for restoration'
  p=self.folder(f'{index:02d}-loading');self.service(p,'listener');self.clear_outputs(p,'clear');self.reset_config(p)
  seconds=self.invoke(p,'a-loading04.bin',f'WP3-LOADING04-{index}')
  # Preserve every normal-return RAM before another LOAD, including unexpected
  # decoder/schema/final-marker failure. No warmup/render is ever issued.
  self.save_ram(p,index)
  for n in ('loading.bin','loading3.bin'):self.transfer(p,n,'get',self.remote+'/'+n,p/n)
  summary=q.decode_loading((p/'loading.bin').read_bytes());trace=decode((p/'loading3.bin').read_bytes())
  save(p/'loading.json',summary);save(p/'trace.json',trace)
  labels=self.kit['labels'];ram=(p/'ram.bin').read_bytes();at=labels['wpl3_header']-0x40000
  assert ram[at:at+FILE_BYTES]==(p/'loading3.bin').read_bytes(),'RAM/file observation mismatch'
  ok=summary['error']==summary['agnb_error']==0 and summary['total']==470 and trace['main_returned']and trace['loading_ready']and not trace['loading_error']and not trace['frozen']and not trace['save_failed']
  save(p/'receipt.json',dict(passed=bool(ok),seconds=seconds,ram_saved_before_successor_load=True,sha256={n:sha(p/n)for n in ('ram.bin','loading.bin','loading3.bin')}))
  self.raw_state(p,'post');self.exit(p,'exit')
  if not ok:raise LoadingFailure('First loading failure; successors stopped, RAM retained')
  print('LOADING PASS',index,flush=True)
 def suite(self):
  try:
   self.entry();self.stage();self.flash('a-loading',B/'install-a.bin')
   try:
    for index in range(1,5):self.case(index)
   except LoadingFailure as error:
    save(self.out/'loading-stop.json',dict(error=str(error),no_successors=True,performance_claim=False))
   self.restoring=True
   self.flash('restore',B/'restore.bin');self.handback()
   p=self.out/'handback/observation.json';d=json.loads(p.read_text());d['disposition']='Finite loading-only diagnostic ended; incoming native application/tail restored/readback, CLI/mode0/callback0/input/idle/freeports checked, EMOS/P4/startup/listener unchanged; SD mounted. No performance/optical claim.';save(p,d)
   save(self.out/'stopped-restored.json',dict(restored=True,performance_claim=False,all_four_pass=not(self.out/'loading-stop.json').exists()))
  except BaseException as error:
   save(self.out/'failure.json',dict(error=repr(error),epoch=time.time(),next_dispatch_stopped=True,custody_retained=True,no_automatic_reset_or_replay=True));raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('context');args=p.parse_args();Bench(args.context).suite()
