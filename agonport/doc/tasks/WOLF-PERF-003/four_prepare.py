"""Oryx: fresh four-combination profiles, no emulator launch."""
from pathlib import Path
import json,hashlib,shutil,subprocess,importlib.util
ROOT=Path.home()/'Agon/mystuff/Wolf3dOrig';TASK=ROOT/'agonport/doc/tasks/WOLF-PERF-003';OUT=ROOT/'.emulator/wolf-four01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
OUT.mkdir(exist_ok=False);records=[]
spec=importlib.util.spec_from_file_location('fv',TASK/'fab_visual.py');fv=importlib.util.module_from_spec(spec);spec.loader.exec_module(fv)
for backend in ('bespoke','vdplet'):
 p=OUT/('fab-'+backend+'-01');fv.PROFILE=p;fv.PAYLOAD=TASK/('build/r07/fab-bespoke/paced/payload'if backend=='bespoke'else'build/fab-b-guest01/payload');fv.prepare()
 if backend=='vdplet':
  (p/'vdp_wolf3d.so').unlink();shutil.copyfile(TASK/'build/fabbridge01/vdp_wolf_fab.so',p/'vdp_wolf_fab.so');(p/'.bespoke-vdp-profile').write_text('vdp_wolf_fab.so\n')
  m=json.loads((p/'inputs.json').read_text());del m['vdp_wolf3d.so'];m['vdp_wolf_fab.so']=sha(p/'vdp_wolf_fab.so');(p/'inputs.json').write_text(json.dumps(m,indent=2)+'\n');(p/'.runtime.sha256').write_text(''.join(d+'  '+n+'\n'for n,d in m.items()))
 subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=p,check=True);records.append(dict(emulator='fab',backend=backend,trial=1,profile=str(p)))
for backend,old in [('bespoke','09-bespoke-paced'),('vdplet','10-vdplet-paced')]:
 for i in range(1,6):
  p=OUT/f'flexe-{backend}-{i:02d}';shutil.copytree(ROOT/'.emulator/wolf-perf003-p02'/old,p,symlinks=True);assert not(p/'run').exists()
  shutil.rmtree(p/'sdcard/wolf3d');shutil.copytree(TASK/'build/r07'/backend/'paced/payload',p/'sdcard/wolf3d')
  names=[s.split('  ',1)[1]for s in(p/'.runtime.sha256').read_text().splitlines()];m={n:sha(p/n)for n in names};(p/'.runtime.sha256').write_text(''.join(d+'  '+n+'\n'for n,d in m.items()));(p/'inputs.json').write_text(json.dumps(m,indent=2)+'\n');subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=p,check=True)
  records.append(dict(emulator='flexe',backend=backend,trial=i,profile=str(p)))
(OUT/'profiles.json').write_text(json.dumps(records,indent=2)+'\n');print('ALL FOUR STOPPED PROFILE SETS READY',OUT)
