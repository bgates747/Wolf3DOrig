"""Owner-bound monitored Olimex suite. Stop first failure; never replay a guest."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re,struct,subprocess,sys,time
T=Path(__file__).resolve().parents[1];B=T/'build/hardware01'
E=Path('/Agon/mystuff/agon-extender');D=Path('/Agon/mystuff/agon-dev-env')
donor=T.parent/'WOLF-PERF-001/hardware/physical.py'
spec=importlib.util.spec_from_file_location('wolf_physical_transport',donor)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sys.path.insert(0,str(T));from analyze import analyze
sha=lambda data:hashlib.sha256(data).hexdigest()
save=m.save

class Bench(m.Bench):
 def __init__(self,context):
  self.c=json.loads(Path(context).read_text());self.grant=json.loads(Path(self.c['grant']).read_text())
  if 'active'in self.grant:self.grant=self.grant['active']
  assert self.grant['owner']=='wolf3dorig' and self.grant['task']=='WOLF-PERF-003-hardware-r01'
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
   assert not any(n[0].lower()==self.remote.lower()for n in c.entries('/test/wolf')),'Existing task path needs offline reconciliation'
   c.make_directory(self.remote);c.make_directory(self.remote+'/level_00')
  finally:c.lock.close()
  data=('SAVE '+self.remote+'/post-mode.bin &BC349 &1\r\nSAVE '+self.remote+'/post-callback.bin &BC38E &3\r\nEMOS sdserve --fast /\r\n').encode()
  script=p/'state.txt';script.write_bytes(data);self.upload(p,'state',script,self.remote+'/state.txt')
  self.raw_state(p,'raw');save(p/'receipt.json',dict(passed=True,actual_cli=True,mode=0,callback_zero=True))
 def stage(self):
  assert json.loads((self.out/'entry/receipt.json').read_text())['passed'];p=self.folder('stage')
  for i,(name,local)in enumerate(self.kit['stage'].items()):
   self.upload(p,f'file-{i:02d}',Path(local),self.remote+'/'+name);print('STAGED',name,flush=True)
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
    if remote.rsplit('/',1)[-1] in ('before.bin','after.bin','stack.bin','timing.bin','native.bin','resource.bin'):
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
    if b'WOLF-PERF-003 FAILED'in tail and not control:raise RuntimeError('Guest failed; stop dispatch')
    expected=b'WOLF-PERF-003 CONTROL REGISTERS-RESTORED RETURN'if control else (b'WOLF RESOURCE COMPLETE' if filename=='resource-probe.bin' else b'WOLF-PERF-003 COMPLETE')
    return expected in tail and b'/test/wolf/perf003 *'in tail and (filename=='resource-probe.bin' or b'Thanks for playing Wolf3DOrig!'in tail)
   self.capture(serial,raw,folder,done,300)
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
  label=f'{index:02d}-{backend}-{mode}';p=self.folder(label)
  if not self.get('/sd/status')['online']:self.service(p,'listener')
  self.clear_outputs(p,'clean')
  seconds=self.invoke(p,('a'if backend=='bespoke'else'b')+'-'+mode+'.bin','WP3-'+label,mode=='control')
  outputs=['before.bin']if mode=='control'else['before.bin','after.bin','stack.bin','timing.bin']+([]if mode=='cpu'else['native.bin'])
  for n in outputs:self.transfer(p,n,'get',self.remote+'/'+n,p/n)
  result={'control':True}if mode=='control'else analyze(p)
  if mode!='control':
   listing=(B/backend/mode/'source/wolf3d.lst').read_text();after=(p/'after.bin').read_bytes()
   pointers=[]
   for name in ('wp_entry_sp','wp_exit_sp'):
    match=re.search(r'^([0-9A-F]{6})[^\n]*\b'+name+r':',listing,re.M);assert match
    at=int(match[1],16)-0x40000;pointers.append(int.from_bytes(after[at:at+3],'little'))
   assert pointers[0]==pointers[1] and 0xb0000<=pointers[0]<0xc0000
  self.raw_state(p,'post');self.exit(p,'exit')
  save(p/'receipt.json',dict(passed=True,backend=backend,mode=mode,whole_seconds=seconds,result=result,sha256={n:sha((p/n).read_bytes())for n in outputs},actual_cli=True,mode0_callback0=True))
  print('CASE PASS',label,flush=True)
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
  except BaseException as error:
   save(self.out/'failure.json',dict(error=repr(error),epoch=time.time(),next_dispatch_stopped=True,custody_retained=True,no_automatic_replay=True));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('context');a=p.parse_args();Bench(a.context).suite()
