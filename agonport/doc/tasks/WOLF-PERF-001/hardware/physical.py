"""Owned finite Wolf hardware actions. No firmware operations or automatic replay.
Transport helpers adapted from Rally NAT-HW-001 physical.py; source hash in freeze.
"""
import argparse,hashlib,importlib.util,json,os,re,subprocess,sys,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
BUILD=TASK/'build/olimex01'
EXT=Path('/Agon/mystuff/agon-extender')
ENV=Path('/Agon/mystuff/agon-dev-env')
sys.path.insert(0,str(EXT/'scripts'))
from keyboard import Client as Keys,text_events
from sdcard import Client as Metadata
from passive_serial import open_passive_serial
FAST=EXT/'agents/remote009/fast-transfer-pin-r01/sdcard_staged.py'
assert hashlib.sha256(FAST.read_bytes()).hexdigest()=='f7aa43bd05d62cc1bdc051d8ae569128766cb9ec95076bd1bb951063997683ef'
spec=importlib.util.spec_from_file_location('wolf_fast',FAST)
fast=importlib.util.module_from_spec(spec);spec.loader.exec_module(fast)
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(p,d):
 with Path(p).open('x') as f:json.dump(d,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def verify_runtime_trace(raw,build=b'20261104'):
 values=[int(x) for x in re.findall(rb'W3DDBG VDPL_TX ms=\d+ op=4 token=\d+ kind=4 value=(\d+) rc=0',raw)]
 assert len(values)>=2 and values[0]==0x100 and values[1]&0x101==0x101,'Runtime guard binding not observed'
 assert re.search(rb'VDPL LOAD handle=\d+ build='+re.escape(build)+rb'\b',raw),'Diagnostic module build not observed'
 return values[0],values[1]
class Bench:
 def __init__(self,context):
  self.c=json.loads(Path(context).read_text())
  self.grant=json.loads(Path(self.c['grant']).read_text())
  if 'active' in self.grant:self.grant=self.grant['active']
  assert self.grant['owner']=='wolf3dorig' and self.grant['task']=='WOLF-PERF-001-hardware'
  self.lease=self.grant['lease'];self.out=Path(self.c['output']).resolve()
  assert self.out.is_relative_to((BUILD/'evidence').resolve())
  self.out.mkdir(parents=True,exist_ok=True)
  self.inventory=json.loads((HERE/'freeze.json').read_text())
  for rel,digest in self.inventory['files'].items():assert sha((TASK/rel).read_bytes())==digest,rel
  for name,digest in self.inventory['tools'].items():assert sha(Path(name).read_bytes())==digest,name
  self.components=self.grant['entry_observation']['components']
  assert self.components==self.inventory['expected_components'],'Incoming component mismatch'
  assert self.c['entry_route']=='legacy','Only an established Legacy CLI is admitted'
  self.url=self.c['url'];self.port=self.c['port'];self.remote=self.inventory['remote']
  self.package=BUILD/'payload'
 def own(self):
  subprocess.run([str(ENV/'.venv/bin/python'),str(ENV/'cross-agent/olimex-bench/bench_lease.py'),'assert-owner','--owner','wolf3dorig','--lease',self.lease],check=True,stdout=subprocess.DEVNULL)
 def get(self,p):
  self.own()
  with urllib.request.urlopen(self.url+p,timeout=8)as r:return json.load(r)
 def state(self):return{k:self.get(p)for k,p in [('keyboard','/keyboard/status'),('sd','/sd/status'),('worker','/sd/fast'),('display','/display/status')]}
 def line(self,folder,label,command):
  self.own();save(folder/(label+'-issued.json'),dict(command=command,once=True,epoch=time.time()))
  c=Keys(self.url,folder/(label+'-keys.json'))
  try:
   k=c.status();assert k['ready']and k['physical_neutral']and not k['held']and not k['pending'],k;c.open(k)
   for ch in command:c.send(text_events(ch,k['locale'],k['caps']))
   c.send([(40,1),(40,0)])
   if not c.state.get('pending'):c.cancel()
  finally:c.lock.close()
 def wait_online(self,wanted,seconds=45):
  end=time.monotonic()+seconds
  while True:
   s=self.get('/sd/status')
   if bool(s['online'])==wanted and not s['pending']:return s
   if time.monotonic()>end:raise RuntimeError('Listener transition uncertain; no replay')
   time.sleep(.2)
 def metadata(self,folder,label):
  self.own();c=Metadata(self.url,folder/(label+'-metadata.json'),timeout=60);c.connect(require_fast=True);return c
 def exit(self,folder,label):
  c=self.metadata(folder,label)
  try:self.own();c.rpc(11);self.wait_online(False)
  finally:c.lock.close()
 def transfer(self,folder,label,op,remote,local):
  self.own();c=fast.Client(self.url,folder/(label+'-staged.json'),timeout=300)
  try:r=c.begin(op,remote,source=local if op=='put'else None,destination=local if op=='get'else None,activate=op=='put');save(folder/(label+'-result.json'),r);return r
  finally:c.close()
 def folder(self,name):p=self.out/name;p.mkdir(exist_ok=False);return p
 def capture_until(self,serial,raw,folder,predicate,seconds):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   data=serial.read(8192)
   if data:raw.extend(data);(folder/'serial.bin').write_bytes(raw)
   text=raw.decode(errors='replace')
   if any(x in text for x in ('Guru Meditation','RST $38 panic','Error executing','WOLF-PERF-001 FAILED')):raise RuntimeError('Failure; stop dispatch, preserve raw capture')
   if predicate(raw):return
  raise RuntimeError('Observation bound reached; no automatic replay or next case')
 def entry(self):
  p=self.folder('entry');s=self.state();save(p/'before.json',s)
  assert not s['sd']['online'] and not s['sd']['pending'] and s['worker']['phase']==0
  raw=bytearray();self.own()
  with open_passive_serial(self.port,baudrate=115200,timeout=.2) as serial:
   self.line(p,'mirror','VDU 2');self.line(p,'sentinel','VDU 87 80 69 78 84 82 89 13 10')
   self.capture_until(serial,raw,p,lambda b:b'WPENTRY' in b,20)
   self.line(p,'directory','DIR')
   self.capture_until(serial,raw,p,lambda b:b'Directory:' in b and b' *' in b,20)
  match=re.search(rb'Directory: ([^\r\n]+)',raw);assert match
  (p/'cwd.txt').write_text(match[1].decode().strip())
  self.line(p,'listener','EMOS sdserve --fast /');self.wait_online(True)
  for remote,name,key in [('/autoexec.txt','autoexec.txt','startup_sha256'),('/emos/sdserve.bin','sdserve.bin','listener_sha256')]:
   self.transfer(p,name,'get',remote,p/name);assert sha((p/name).read_bytes())==self.components[key]
  c=self.metadata(p,'directories')
  try:
   c.make_directory('/test/wolf',parents=True)
   assert not any(x[0].lower()==self.remote.lower() for x in c.entries('/test/wolf'))
   c.make_directory(self.remote,parents=True)
  finally:c.lock.close()
  script=p/'save-entry.txt'
  script.write_text('SAVE '+self.remote+'/entry-mode.bin &BC349 &1\nEMOS sdserve --fast /\n')
  self.transfer(p,'mode-script','put',self.remote+'/save-entry.txt',script)
  self.exit(p,'exit-before-save');self.line(p,'mode-save','EXEC '+self.remote+'/save-entry.txt');self.wait_online(True)
  self.transfer(p,'mode-read','get',self.remote+'/entry-mode.bin',p/'mode.bin')
  assert (p/'mode.bin').read_bytes()==bytes([0]),'This first cohort admits native mode0 entry only'
  save(p/'receipt.json',dict(passed=True,actual_cli=True,mode=0,route='legacy',startup_listener_verified=True))
 def stage(self):
  assert json.loads((self.out/'entry/receipt.json').read_text())['passed']
  p=self.folder('stage');c=self.metadata(p,'directories')
  try:
   for case in self.inventory['order']:
    c.make_directory(self.remote+'/'+case,parents=True)
    c.make_directory(self.remote+'/'+case+'/level_00',parents=True)
  finally:c.lock.close()
  for case in self.inventory['order']:
   for i,n in enumerate(self.inventory['case_files'][case]):
    local=self.package/case/n;remote=self.remote+'/'+case+'/'+n
    self.transfer(p,f'{case}-put-{i:02}','put',remote,local)
    read=p/f'{case}-read-{i:02}.bin';self.transfer(p,f'{case}-get-{i:02}','get',remote,read)
    assert read.read_bytes()==local.read_bytes(),remote
   run=p/(case+'-invoke.txt')
   run.write_text('CD '+self.remote+'/'+case+'\nLOAD wolf3d.bin\nRUN .\nSAVE '+self.remote+'/'+case+'/post-mode.bin &BC349 &1\nEMOS sdserve --fast /\n')
   mode=p/(case+'-verify-mode.txt')
   mode.write_text('SAVE '+self.remote+'/'+case+'/current-mode.bin &BC349 &1\nEMOS sdserve --fast /\n')
   for local,name in ((run,'invoke.txt'),(mode,'verify-mode.txt')):self.transfer(p,case+'-'+name,'put',self.remote+'/'+case+'/'+name,local)
  self.exit(p,'exit');save(p/'receipt.json',dict(passed=True,application_invoked=False,cases=self.inventory['order']))
 def run(self,case):
  assert case in self.inventory['order'];assert json.loads((self.out/'stage/receipt.json').read_text())['passed']
  i=self.inventory['order'].index(case)
  if i:assert json.loads((self.out/('returned-'+self.inventory['order'][i-1])/'receipt.json').read_text())['passed']
  p=self.folder('run-'+case);s=self.state();save(p/'before.json',s)
  assert not s['sd']['online'] and not s['sd']['pending'] and s['worker']['phase']==0
  began=time.monotonic();raw=bytearray();self.own()
  with open_passive_serial(self.port,baudrate=115200,timeout=.2) as serial:
   self.line(p,'mirror','VDU 2')
   marker=('WPERF-'+case).encode();command='VDU '+' '.join(map(str,marker))+ ' 13 10'
   self.line(p,'sentinel',command);self.capture_until(serial,raw,p,lambda b:marker in b,20)
   self.line(p,'mode-save','EXEC '+self.remote+'/'+case+'/verify-mode.txt');self.wait_online(True)
   self.transfer(p,'mode-read','get',self.remote+'/'+case+'/current-mode.bin',p/'mode.bin')
   assert (p/'mode.bin').read_bytes()==bytes([0]),'Native entry mode changed'
   self.exit(p,'mode-exit')
   invoked_at=len(raw)
   self.line(p,'invoke','EXEC '+self.remote+'/'+case+'/invoke.txt')
   self.capture_until(serial,raw,p,lambda b:all(x in b[invoked_at:] for x in (b'WOLF-PERF-001 COMPLETE',b'VDPL UNLOAD status=0',b'Thanks for playing Wolf3DOrig!')) and self.get('/sd/status')['online'],300)
  after=self.state();save(p/'after.json',after)
  assert after['keyboard']['boot']==s['keyboard']['boot'],'Input epoch changed; stop dispatch'
  # INFO0 is identity; discovery's IDENT payload is a capability mask.
  values=verify_runtime_trace(raw[invoked_at:])
  save(p/'receipt.json',dict(passed=True,case=case,application_invocations=1,host_whole_operation_seconds=time.monotonic()-began,performance_denominator=False,identity=values[0],capabilities=values[1],normal_return=True,correctness_pending_retrieval=True))
 def retrieve(self,case):
  assert case in self.inventory['order'];assert json.loads((self.out/('run-'+case)/'receipt.json').read_text())['passed']
  p=self.folder('returned-'+case)
  outputs=['timing.bin','before.bin','after.bin','stack.bin','post-mode.bin']
  if case!='cpu':outputs.append('native.bin')
  for name in outputs:self.transfer(p,name,'get',self.remote+'/'+case+'/'+name,p/name)
  assert (p/'post-mode.bin').read_bytes()==bytes([0]),'Application did not restore its native entry mode'
  sys.path.insert(0,str(TASK));from analyze import analyze
  result=analyze(p);assert result['mode']==case
  original=(self.package/case/'wolf3d.bin').read_bytes();before=(p/'before.bin').read_bytes();after=(p/'after.bin').read_bytes()
  offset=0x626e6-0x40000
  assert original[offset:offset+0x57]==before[offset:offset+0x57]==after[offset:offset+0x57],'Audio executable changed'
  positions=self.inventory['stack_offsets'][case]
  pointers=[int.from_bytes(after[n:n+3],'little') for n in positions]
  assert pointers[0]==pointers[1] and 0xb0000<=pointers[0]<0xc0000,'Fixture stack mismatch'
  hashes={name:sha((p/name).read_bytes()) for name in outputs}
  save(p/'integrity.json',dict(audio_code_intact=True,entry_sp=pointers[0],exit_sp=pointers[1],retrieved_sha256=hashes))
  self.exit(p,'exit');save(p/'receipt.json',dict(passed=True,case=case,records=result['completed_records'],physical_clocks_uncalibrated=True,installed_runtime_diagnostic_logging=True))
 def handback(self):
  assert all(json.loads((self.out/('returned-'+case)/'receipt.json').read_text())['passed'] for case in self.inventory['order']),'Uncertain/failed work requires separate recovery, not automatic handback'
  p=self.folder('handback');assert not self.get('/sd/status')['online']
  self.line(p,'listener','EMOS sdserve --fast /');self.wait_online(True)
  for remote,name in [('/autoexec.txt','autoexec.txt'),('/emos/sdserve.bin','sdserve.bin')]:
   self.transfer(p,name,'get',remote,p/name);assert (p/name).read_bytes()==(self.out/'entry'/name).read_bytes()
  script=p/'verify-mode.txt';script.write_text('SAVE '+self.remote+'/handback-mode.bin &BC349 &1\nEMOS sdserve --fast /\n')
  self.transfer(p,'mode-script','put',self.remote+'/handback-mode.txt',script)
  self.exit(p,'mode-exit');self.line(p,'mode-save','EXEC '+self.remote+'/handback-mode.txt');self.wait_online(True)
  self.transfer(p,'mode-read','get',self.remote+'/handback-mode.bin',p/'mode.bin')
  assert (p/'mode.bin').read_bytes()==(self.out/'entry/mode.bin').read_bytes(),'Native entry mode not restored'
  self.exit(p,'exit');self.line(p,'cwd','CD '+(self.out/'entry/cwd.txt').read_text())
  self.line(p,'cursor','VDU 4 23 1 1 23 1 3')
  raw=bytearray();self.own()
  with open_passive_serial(self.port,baudrate=115200,timeout=.2) as serial:
   self.line(p,'mirror','VDU 2');self.line(p,'sentinel','VDU 87 80 72 65 78 68 13 10')
   self.capture_until(serial,raw,p,lambda b:b'WPHAND' in b,20)
   self.line(p,'directory','DIR');self.capture_until(serial,raw,p,lambda b:b'Directory:' in b and b' *' in b,20)
  self.line(p,'mirror-off','VDU 3')
  s=self.state();save(p/'state.json',s);k=s['keyboard']
  assert k['ready'] and k['physical_neutral'] and not k['held'] and not k['pending']
  assert not s['sd']['online'] and not s['sd']['pending'] and s['worker']['phase']==0
  for port in self.c['ports']:
   r=subprocess.run(['fuser',str(Path(port).resolve())],capture_output=True);assert r.returncode==1,r.stdout
  checks={k:True for k in ('no_workload','no_transfer','no_serial_readers','no_reset_holders','cli_verified','input_ready_neutral','listener_offline','staged_job_idle','restoration_verified')}
  provenance={k:('Fresh full-file comparison with entry copy' if k in ('startup_sha256','listener_sha256') else 'Retained verified incoming grant identity; this suite performs no firmware operation') for k in self.components}
  save(p/'observation.json',dict(schema='olimex-bench-observation-v1',bench='olimex',epoch=time.time(),observer='wolf3dorig',lease=self.lease,checks=checks,evidence=[str(p/'state.json'),str(p/'serial.bin'),str(self.out/'entry/receipt.json')],components=self.components,component_provenance=provenance,disposition='Known completed Wolf suite; no firmware operations. Startup/listener actual comparisons, native entry mode/cwd and actual mirrored CLI restored. Cursor commands issued, neutral input, offline idle workers and free ports checked. No optical/audio or calibrated-clock claim.'))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('context');p.add_argument('action',choices=('entry','stage','run','retrieve','handback'));p.add_argument('--case');a=p.parse_args()
 b=Bench(a.context)
 if a.action in ('run','retrieve'):getattr(b,a.action)(a.case)
 else:getattr(b,a.action)()
if __name__=='__main__':main()
