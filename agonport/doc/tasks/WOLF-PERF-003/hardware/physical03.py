"""Owner-bound monitored Olimex suite. Stop first failure; never replay a guest."""
from pathlib import Path
import argparse,csv,hashlib,importlib.util,json,os,re,struct,subprocess,sys,time
T=Path(__file__).resolve().parents[1];B=T/'build/hardware03'
E=Path('/Agon/mystuff/agon-extender');D=Path('/Agon/mystuff/agon-dev-env')
donor=T.parent/'WOLF-PERF-001/hardware/physical.py'
spec=importlib.util.spec_from_file_location('wolf_physical_transport',donor)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sys.path.insert(0,str(T));from analyze import analyze
sha=lambda data:hashlib.sha256(data).hexdigest()
from sdcard import path_payload
save=m.save

def decode_loading(raw):
 assert len(raw)==48 and raw[:5]==b'WPL2\1' and raw[38:40]==bytes([10,1]),raw.hex()
 r={n:int.from_bytes(raw[at:at+3],'little') for n,at in [('count',8),('total',11),('fences',14),('timeouts',17),('recovered',20),('max_ticks',23),('last_ticks',26),('first_timeout_total',29),('first_timeout_ticks',34)]}
 r.update(error=raw[5],phase=raw[6],status=raw[7],first_timeout_phase=raw[32],first_status=raw[33],last_passes=raw[37],agnb_error=raw[40]);return r

class SetupFailure(RuntimeError):pass

class Bench(m.Bench):
 def __init__(self,context):
  self.c=json.loads(Path(context).read_text());self.grant=json.loads(Path(self.c['grant']).read_text())
  if 'active'in self.grant:self.grant=self.grant['active']
  assert self.grant['owner']=='wolf3dorig' and self.grant['task']=='WOLF-PERF-003-hardware-r03'
  self.lease=self.grant['lease'];self.out=B/'evidence';self.out.mkdir(exist_ok=True)
  self.url=self.c['url'];self.port=self.c['native_port'];self.remote='/test/wolf/perf003'
  self.kit=json.loads((B/'kit.json').read_text());self.components=self.grant['entry_observation']['components']
  assert self.components==self.kit['incoming_components']
  for name,digest in self.kit['inputs'].items():assert sha(Path(name).read_bytes())==digest,name
 def own(self):
  subprocess.run([str(D/'.venv/bin/python'),str(D/'cross-agent/olimex-bench/bench_lease.py'),'assert-owner','--owner','wolf3dorig','--lease',self.lease],check=True,stdout=subprocess.DEVNULL)
 def transfer(self,folder,label,op,remote,local):
  self.own();c=m.fast.Client(self.url,folder/(label+'-job.json'),timeout=45);begin=time.monotonic()
  try:
   try:r=c.begin(op,remote,source=local if op=='put' else None,destination=local if op=='get' else None,activate=op=='put')
   except TimeoutError:
    while True:
     self.own();assert time.monotonic()-begin<750,'Original staged job bound; retain journal'
     try:r=c.resume();break
     except TimeoutError:pass
   save(folder/(label+'-result.json'),dict(result=r,seconds=time.monotonic()-begin));return r
  finally:c.close()
 def upload(self,folder,label,local,remote):
  self.transfer(folder,label+'-put','put',remote,local)
  read=folder/(label+'-read.bin');self.transfer(folder,label+'-get','get',remote,read)
  assert read.read_bytes()==Path(local).read_bytes(),remote
 def capture(self,serial,raw,folder,predicate,bound):
  end=time.monotonic()+bound
  while time.monotonic()<end:
   chunk=serial.read(8192)
   if chunk:raw.extend(chunk);(folder/'serial.bin').write_bytes(raw)
   if any(x in raw for x in (b'Guru Meditation',b'RST $38 panic',b'Error executing',b'Error loading',b'WOLF RESOURCE FAILED')):raise RuntimeError('Unexpected target failure; stop dispatch')
   if predicate(raw):return
  raise TimeoutError('Original observation bound; no automatic replay')
 def cli(self,folder,label):
  self.own();raw=bytearray()
  with m.open_passive_serial(self.port,baudrate=115200,timeout=.2)as serial:
   self.line(folder,label+'-mirror','VDU 2')
   marker=('WP3-'+label).encode();self.line(folder,label+'-sentinel','VDU '+' '.join(map(str,marker))+' 13 10')
   self.capture(serial,raw,folder,lambda r:marker in r,20)
   start=len(raw);self.line(folder,label+'-dir','DIR')
   self.capture(serial,raw,folder,lambda r:b'Directory:'in r[start:] and b' *'in r[start:],20)
  return raw
 def service(self,folder,label):
  assert not self.get('/sd/status')['online']
  self.line(folder,label,'EMOS sdserve --fast /');self.wait_online(True)
 def raw_state(self,folder,label):
  # Listener online; this command never LOADs and preserves unsaved result RAM.
  c=self.metadata(folder,label+'-fresh')
  try:
   for name,_,attr in list(c.entries(self.remote)):
    if name.rsplit('/',1)[-1] in ('post-mode.bin','post-callback.bin'):
     assert not attr&16;c.remove(name)
  finally:c.lock.close()
  self.exit(folder,label+'-exit');self.line(folder,label+'-save','EXEC '+self.remote+'/state.txt');self.wait_online(True)
  for name in ('mode','callback'):
   self.transfer(folder,label+'-'+name,'get',self.remote+'/post-'+name+'.bin',folder/(label+'-'+name+'.bin'))
  assert(folder/(label+'-mode.bin')).read_bytes()==b'\0'
  assert(folder/(label+'-callback.bin')).read_bytes()==b'\0\0\0'
 def entry(self):
  p=self.folder('entry');self.own();self.cli(p,'entry')
  self.service(p,'listener')
  for path,name,key in [('/autoexec.txt','startup.bin','startup_sha256'),('/emos/sdserve.bin','listener.bin','listener_sha256')]:
   self.transfer(p,name,'get',path,p/name);assert sha((p/name).read_bytes())==self.components[key]
  c=self.metadata(p,'dir')
  try:
   c.make_directory('/test/wolf',parents=True)
   assert any(n[0].lower()==self.remote.lower()for n in c.entries('/test/wolf')),'Expected retained hardware01 directory'
   known={n.split('/')[0]for n in self.kit['stage']}|{'state.txt','post-mode.bin','post-callback.bin','before.bin','after.bin','stack.bin','timing.bin','native.bin','resource.bin','loading.bin','setup-failure-ram.bin','failure-save.txt','failure02-save.txt','setup03-ram.bin','paced-failure-ram.bin','paced-failure-save.txt'}
   entries=list(c.entries(self.remote));save(p/'retained-directory.json',entries)
   for name,size,attr in entries:
    base=name.rsplit('/',1)[-1]
    assert base in known,('Unknown file/journal; reconcile before mutation',name)
    assert bool(attr&16)==(base=='level_00'),name
  finally:c.lock.close()
  data=('SAVE '+self.remote+'/post-mode.bin &BC349 &1\r\nSAVE '+self.remote+'/post-callback.bin &BC38E &3\r\nEMOS sdserve --fast /\r\n').encode()
  script=p/'state.txt';script.write_bytes(data);self.transfer(p,'state-existing','get',self.remote+'/state.txt',p/'state-existing.txt');assert(p/'state-existing.txt').read_bytes()==data
  self.raw_state(p,'raw');save(p/'receipt.json',dict(passed=True,actual_cli=True,mode=0,callback_zero=True))
 def stage(self):
  assert json.loads((self.out/'entry/receipt.json').read_text())['passed'];p=self.folder('stage')
  prior=json.loads((T/'build/hardware02/kit.json').read_text())['stage']
  for i,(name,local)in enumerate(self.kit['stage'].items()):
   label=f'file-{i:02d}';existing=p/(label+'-old.bin')
   self.transfer(p,label+'-existing','get',self.remote+'/'+name,existing)
   if name=='wolf3d.cfg':
    # The game saves its configuration. Preserve it before normalizing this input.
    c=self.metadata(p,label+'-config-remove')
    try:c.remove(self.remote+'/'+name)
    finally:c.lock.close()
    self.upload(p,label,Path(local),self.remote+'/'+name)
   elif existing.read_bytes()!=Path(local).read_bytes():
    assert name in prior and existing.read_bytes()==Path(prior[name]).read_bytes(),name
    self.upload(p,label,Path(local),self.remote+'/'+name)
    c=self.metadata(p,label+'-backup-clean')
    try:c.rpc(10,bytes([3])+path_payload(self.remote+'/'+name))
    finally:c.lock.close()
   print('VERIFIED',name,flush=True)
  self.exit(p,'exit');save(p/'receipt.json',dict(passed=True,files=len(self.kit['stage']),application_invoked=False))
 def boot(self,folder,label):
  end=time.monotonic()+45
  while True:
   k=self.get('/keyboard/status')
   if k['ready'] and k['physical_neutral'] and not k['held'] and not k['pending']:break
   assert time.monotonic()<end,'Boot input bound';time.sleep(.25)
  self.cli(folder,label);self.service(folder,label+'-listener');self.raw_state(folder,label+'-raw');self.exit(folder,label+'-exit')
 def flash(self,label,image):
  p=self.folder('flash-'+label);self.own()
  if label!='restore':assert time.monotonic()<self.deadline-360,'Whole-suite dispatch deadline'
  assert not self.get('/sd/status')['online'] and self.get('/sd/fast')['phase']==0
  assert sha((self.out/'entry/startup.bin').read_bytes())==self.components['startup_sha256']
  r=subprocess.run(['fuser',str(Path(self.port).resolve())],capture_output=True);assert r.returncode==1
  image=Path(image);span=self.kit['flash_span'];assert image.stat().st_size==span
  prefix=[str(E/'.venv/bin/python'),'-m','esptool','--chip','esp32','--port',self.port,'--baud','460800','--after','hard-reset']
  for name,args in [('write',['write-flash','--flash-mode','keep','--flash-freq','keep','--flash-size','keep','0x10000',str(image)]),('read',['read-flash','--flash-size','detect','--no-progress','0x10000',str(span),str(p/'read.bin')])]:
   self.own();save(p/(name+'-issued.json'),dict(argv=prefix+args,epoch=time.time(),once=True))
   with(p/(name+'.log')).open('x')as log:subprocess.run(prefix+args,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
  assert(p/'read.bin').read_bytes()==image.read_bytes()
  self.boot(p,label);save(p/'receipt.json',dict(passed=True,image_sha256=sha(image.read_bytes()),offset=65536,span=span,independent_readback=True,app_only=True))
  print('FLASH VERIFIED',label,flush=True)
 def clear_outputs(self,folder,label):
  c=self.metadata(folder,label)
  try:
   for remote,_,attr in list(c.entries(self.remote)):
    if remote.rsplit('/',1)[-1] in ('before.bin','after.bin','stack.bin','timing.bin','native.bin','resource.bin','loading.bin'):
     assert not attr&16;c.remove(remote)
  finally:c.lock.close()
 def invoke(self,folder,filename,marker,control=False):
  self.exit(folder,'invoke-exit');self.own();raw=bytearray();begin=time.monotonic()
  with m.open_passive_serial(self.port,baudrate=115200,timeout=.2)as serial:
   self.line(folder,'mirror','VDU 2');token=marker.encode()
   self.line(folder,'start-cue','VDU '+' '.join(map(str,token))+' 13 10')
   self.capture(serial,raw,folder,lambda r:token in r,20)
   start=len(raw);self.line(folder,'cd','CD '+self.remote)
   self.capture(serial,raw,folder,lambda r:b'/test/wolf/perf003 *'in r[start:],20)
   start=len(raw);self.line(folder,'load','LOAD '+filename)
   self.capture(serial,raw,folder,lambda r:b'/test/wolf/perf003 *'in r[start:],20)
   start=len(raw);self.line(folder,'run','RUN .')
   def done(r):
    tail=r[start:]
    if b'/test/wolf/perf003 *'in tail and (b'AGNB texture load failed'in tail or b'WOLF LOADING DIAGNOSTIC WRITE FAILED'in tail):return True
    if b'WOLF-PERF-003 FAILED'in tail and not control:raise RuntimeError('Guest failed; stop dispatch')
    expected=b'WOLF-PERF-003 CONTROL REGISTERS-RESTORED RETURN'if control else (b'WOLF RESOURCE COMPLETE' if filename=='resource-probe.bin' else b'WOLF-PERF-003 COMPLETE')
    return expected in tail and b'/test/wolf/perf003 *'in tail and (filename=='resource-probe.bin' or b'Thanks for playing Wolf3DOrig!'in tail)
   self.capture(serial,raw,folder,done,300)
   tail=raw[start:]
   if b'AGNB texture load failed' in tail or b'WOLF LOADING DIAGNOSTIC WRITE FAILED' in tail:
    raise SetupFailure('Loading aborted or diagnostic write failed; actual post-RUN prompt observed')
   settle=time.monotonic()+1
   while time.monotonic()<settle:
    raw.extend(serial.read(8192));(folder/'serial.bin').write_bytes(raw)
   assert not any(x in raw for x in (b'Guru Meditation',b'RST $38 panic')),'Late target fault'
  self.service(folder,'return-listener');return time.monotonic()-begin
 def probe(self,label):
  p=self.folder('probe-'+label);self.service(p,'listener')
  self.clear_outputs(p,'clean')
  seconds=self.invoke(p,'resource-probe.bin','WP3-RESOURCE')
  self.transfer(p,'resource','get',self.remote+'/resource.bin',p/'resource.bin')
  raw=(p/'resource.bin').read_bytes();assert len(raw)==44 and raw[:8]==b'WPR1\1\0\x12\0'
  values=struct.unpack('<18H',raw[8:]);assert values[0]==0x100 and values[1]&0x101==0x101 and values[2]==values[3]==0 and values[17]>=512
  save(p/'receipt.json',dict(passed=True,values=values,minimum_stack_bytes=values[17],whole_seconds=seconds,cumulative=True,non_atomic_memory_halves=True))
  self.raw_state(p,'post');self.exit(p,'exit');print('RESOURCE',label,'stack',values[17],flush=True)
 def case(self,index,backend,mode):
  assert time.monotonic()<self.deadline-300,'Whole-suite dispatch deadline'
  label=f'{index:02d}-{backend}-{mode}';p=self.folder(label)
  if not self.get('/sd/status')['online']:self.service(p,'listener')
  self.clear_outputs(p,'clean');self.reset_config(p)
  seconds=self.invoke(p,('a'if backend=='bespoke'else'b')+'-'+mode+'.bin','WP3-'+label,mode=='control')
  self.transfer(p,'loading','get',self.remote+'/loading.bin',p/'loading.bin');loading=decode_loading((p/'loading.bin').read_bytes())
  assert loading['error']==0 and loading['agnb_error']==0 and loading['total']==470,loading
  save(p/'loading.json',loading)
  outputs=['before.bin']if mode=='control'else['before.bin','after.bin','stack.bin','timing.bin']+([]if mode=='cpu'else['native.bin'])
  for n in outputs:self.transfer(p,n,'get',self.remote+'/'+n,p/n)
  result={'control':True}if mode=='control'else analyze(p)
  if mode not in ('control','cpu'):
   # Independently bound every native interval below half the32bit CCOUNT
   # wrap at source240MHz using the surrounding guest timer interval.
   samples=list(csv.DictReader((p/'samples.csv').open()))
   assert all(int(row['active_ms'])<8000 for row in samples),'Native CCOUNT wrap bound not independently qualified'
  if mode!='control':
   listing=(B/backend/mode/'source/wolf3d.lst').read_text();after=(p/'after.bin').read_bytes()
   pointers=[]
   for name in ('wp_entry_sp','wp_exit_sp'):
    match=re.search(r'^([0-9A-F]{6})[^\n]*\b'+name+r':',listing,re.M);assert match
    at=int(match[1],16)-0x40000;pointers.append(int.from_bytes(after[at:at+3],'little'))
   assert pointers[0]==pointers[1] and 0xb0000<=pointers[0]<0xc0000
  self.raw_state(p,'post');self.exit(p,'exit')
  save(p/'receipt.json',dict(passed=True,backend=backend,mode=mode,whole_seconds=seconds,result=result,loading=loading,sha256={n:sha((p/n).read_bytes())for n in outputs},actual_cli=True,mode0_callback0=True))
  print('CASE PASS',label,flush=True)
 def reset_config(self,folder):
  self.transfer(folder,'config-generated','get',self.remote+'/wolf3d.cfg',folder/'config-generated.bin')
  c=self.metadata(folder,'config-remove')
  try:c.remove(self.remote+'/wolf3d.cfg')
  finally:c.lock.close()
  self.upload(folder,'config-empty',Path(self.kit['stage']['wolf3d.cfg']),self.remote+'/wolf3d.cfg')
 def preserve_setup(self):
  p=self.folder('failure-collection');self.service(p,'listener');self.raw_state(p,'pre')
  # SAVE before any LOAD, collector or new guest; preserve actual resident code/data.
  size=max(Path(self.kit['stage'][n]).stat().st_size for n in self.kit['stage'] if n.startswith(('a-','b-')))
  script=p/'failure-save.txt';script.write_bytes(('SAVE '+self.remote+'/setup03-ram.bin &40000 &'+format(size,'X')+'\r\nEMOS sdserve --fast /\r\n').encode())
  self.upload(p,'save-script',script,self.remote+'/failure03-save.txt')
  self.exit(p,'save-exit');self.line(p,'save-ram','EXEC '+self.remote+'/failure03-save.txt');self.wait_online(True)
  self.transfer(p,'ram','get',self.remote+'/setup03-ram.bin',p/'ram.bin')
  self.transfer(p,'loading','get',self.remote+'/loading.bin',p/'loading.bin');save(p/'loading.json',decode_loading((p/'loading.bin').read_bytes()))
  self.exit(p,'exit');self.flash('restore',B/'restore.bin');self.handback()
 def handback(self):
  p=self.folder('handback');self.cli(p,'handback');self.service(p,'listener')
  for remote,name,key in [('/autoexec.txt','startup.bin','startup_sha256'),('/emos/sdserve.bin','listener.bin','listener_sha256')]:
   self.transfer(p,name,'get',remote,p/name);assert sha((p/name).read_bytes())==self.components[key]
  self.raw_state(p,'final');self.exit(p,'exit');self.line(p,'cursor','VDU 4 23 1 1 23 1 3');self.cli(p,'final-cli');self.line(p,'mirror-off','VDU 3')
  s=self.state();save(p/'state.json',s);k=s['keyboard'];assert k['ready']and k['physical_neutral']and not k['held']and not k['pending']
  assert not s['sd']['online']and not s['sd']['pending']and s['worker']['phase']==0
  for port in self.c['ports']:
   r=subprocess.run(['fuser',str(Path(port).resolve())],capture_output=True);assert r.returncode==1
  checks={n:True for n in ('no_workload','no_transfer','no_serial_readers','no_reset_holders','cli_verified','input_ready_neutral','listener_offline','staged_job_idle','restoration_verified')}
  save(p/'observation.json',dict(schema='olimex-bench-observation-v1',bench='olimex',epoch=time.time(),observer='wolf3dorig',lease=self.lease,checks=checks,evidence=[str(p/'state.json'),str(p/'serial.bin'),str(self.out/'flash-restore/receipt.json')],components=self.components,component_provenance={n:('Fresh full-file comparison'if n in ('startup_sha256','listener_sha256')else'Exact app-span restoration/readback'if n=='native_vdp_sha256'else'Retained unchanged grant identity, no new device read')for n in self.components},disposition='Matched Wolf suite stopped; exact native application/touched tail restored, mode0/callback0/CLI/input/idle/freeports checked, startup/listener unchanged; card mounted. Cursor command only, no optical or calibrated-clock claim.'))
 def suite(self):
  try:
   self.deadline=time.monotonic()+6000
   self.entry();self.stage();index=0
   for group,backend in [('a1','bespoke'),('b1','vdplet'),('a2','bespoke')]:
    self.flash(group,B/('install-a.bin'if backend=='bespoke'else'install-b.bin'))
    if backend=='vdplet':self.probe('b-entry')
    modes=(['control'] if group!='a2' else [])+(['cpu','unpaced','paced']*(2 if backend=='vdplet' else 1))
    for mode in modes:
     index+=1;self.case(index,backend,mode)
     if backend=='vdplet':self.probe(f'b-after-{index:02d}')
   assert index==14
   self.flash('restore',B/'restore.bin');self.handback();save(self.out/'complete.json',dict(passed=True,cases=index,restored=True))
  except SetupFailure as error:
   save(self.out/'failure.json',dict(error=repr(error),next_dispatch_stopped=True,epoch=time.time(),actual_mos_return=True))
   self.preserve_setup();save(self.out/'setup-stopped-restored.json',dict(restored=True,benchmark_claim=False));return
  except BaseException as error:
   save(self.out/'failure.json',dict(error=repr(error),epoch=time.time(),next_dispatch_stopped=True,custody_retained=True,no_automatic_replay=True));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('context');a=p.parse_args();Bench(a.context).suite()
