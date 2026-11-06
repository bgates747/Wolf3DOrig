"""One audio-only native CLI qualification, with original transport/handback."""
from pathlib import Path
import argparse,importlib.util,json,hashlib,re,time
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;BUILD=TASK/'build/audio-hw'
DONOR=TASK.parent/'WOLF-PERF-001/hardware/physical.py'
spec=importlib.util.spec_from_file_location('wolf_audio_transport',DONOR);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class AudioBench(m.Bench):
 def __init__(self,context):
  self.c=json.loads(Path(context).read_text());self.grant=json.loads(Path(self.c['grant']).read_text())
  if 'active'in self.grant:self.grant=self.grant['active']
  assert self.grant['owner']=='wolf3dorig'and self.grant['task']=='WOLF-AUDIO-001'
  admission=self.grant['entry_observation'].get('audio_admission')
  assert admission==dict(native_mode=0,vdu_callback_zero=True,channel0_disposable=True,buffer_f100_disposable=True),'Fresh scoped audio/CLI resource admission required'
  self.lease=self.grant['lease'];self.out=Path(self.c['output']).resolve();assert self.out.is_relative_to((BUILD/'evidence').resolve());self.out.mkdir(parents=True,exist_ok=True)
  self.inventory=json.loads((BUILD/'freeze.json').read_text())
  for f,h in self.inventory['files'].items():assert m.sha(Path(f).read_bytes())==h,f
  for f,h in self.inventory['tools'].items():assert m.sha(Path(f).read_bytes())==h,f
  self.components=self.grant['entry_observation']['components'];assert self.components==self.inventory['expected_components']
  assert self.c['entry_route']=='legacy'
  self.url=self.c['url'];self.port=self.c['port'];self.remote=self.inventory['remote'];self.package=BUILD/'payload'
 def stage(self):
  assert json.loads((self.out/'entry/receipt.json').read_text())['passed'];p=self.folder('stage')
  c=self.metadata(p,'directories')
  try:c.make_directory(self.remote+'/audio',parents=True)
  finally:c.lock.close()
  for i,name in enumerate(self.inventory['case_files']['audio']):
   src=self.package/'audio'/name;remote=self.remote+'/audio/'+name;read=p/f'read-{i:02}.bin'
   self.transfer(p,f'put-{i:02}','put',remote,src);self.transfer(p,f'get-{i:02}','get',remote,read);assert read.read_bytes()==src.read_bytes()
  script=p/'invoke.txt';script.write_text('CD '+self.remote+'/audio\nLOAD playwav.bin\nRUN . notification.wav\nSAVE '+self.remote+'/audio/post-mode.bin &BC349 &1\nEMOS sdserve --fast /\n')
  self.transfer(p,'invoke','put',self.remote+'/audio/invoke.txt',script)
  self.exit(p,'exit');m.save(p/'receipt.json',dict(passed=True,application_invoked=False))
 def run(self):
  assert json.loads((self.out/'stage/receipt.json').read_text())['passed'];p=self.folder('run-audio');state=self.state();m.save(p/'before.json',state)
  assert not state['sd']['online']and not state['sd']['pending']and state['worker']['phase']==0
  raw=bytearray();self.own();start=time.monotonic()
  with m.open_passive_serial(self.port,baudrate=115200,timeout=.2)as serial:
   self.line(p,'mirror','VDU 2');self.line(p,'sentinel','VDU 87 79 76 70 65 85 68 73 79 13 10');self.capture_until(serial,raw,p,lambda b:b'WOLFAUDIO'in b,20)
   offset=len(raw);self.line(p,'invoke','EXEC '+self.remote+'/audio/invoke.txt')
   def finished(b):
    if b'PLAYWAV ERROR'in b[offset:]:raise RuntimeError('Audio application refused/failed; stop, no replay')
    return b'PLAYWAV OK bytes='in b[offset:]and self.get('/sd/status')['online']
   self.capture_until(serial,raw,p,finished,120)
  assert b'PLAYWAV ERROR'not in raw[offset:]and b'PLAYWAV PLAY OK'in raw[offset:]
  match=re.search(rb'PLAYWAV OK bytes=(\d+) rate=(\d+)',raw[offset:]);assert match
  assert (int(match[1]),int(match[2]))==(self.inventory['pcm_bytes'],16000)
  m.save(p/'receipt.json',dict(passed=True,one_invocation=True,play_command_acknowledged=True,cleanup_complete=True,normal_exec_continuation=True,host_operation_seconds=time.monotonic()-start,human_hearing='pending'))
 def retrieve(self):
  assert json.loads((self.out/'run-audio/receipt.json').read_text())['passed'];p=self.folder('returned-audio');self.transfer(p,'mode','get',self.remote+'/audio/post-mode.bin',p/'mode.bin');assert(p/'mode.bin').read_bytes()==(self.out/'entry/mode.bin').read_bytes()==bytes([0]);self.exit(p,'exit');m.save(p/'receipt.json',dict(passed=True,native_mode_preserved=True))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('context');p.add_argument('action',choices=('entry','stage','run','retrieve','handback'));a=p.parse_args();getattr(AudioBench(a.context),a.action)()
