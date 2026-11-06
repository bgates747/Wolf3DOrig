"""Oryx only: fresh negative-control profiles, with unchanged baseline runtime."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess
HERE=Path(__file__).resolve().parent
ROOT=Path.home()/'Agon/mystuff/Wolf3dOrig'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 out=ROOT/'.emulator/wolf-perf003-controls01';out.mkdir(exist_ok=False);records=[]
 for index,backend in enumerate(('bespoke','vdplet'),1):
  original=ROOT/'.emulator/wolf-perf003-q02'/f'{index+6:02d}-{backend}-cpu-fail'
  subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=original,check=True)
  dest=out/f'{index:02d}-{backend}';dest.mkdir()
  files={line.split('  ',1)[1]for line in(original/'.runtime.sha256').read_text().splitlines()}
  files.update(('.bespoke-vdp-profile','.mos-release','.mos-release.sha256'))
  for rel in sorted(files):
   target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original/rel,target)
  payload=HERE/'build/controls01-r02'/backend/'payload';expected=json.loads((payload/'expected.json').read_text())
  for rel,item in expected['files'].items():assert sha(payload/rel)==item['sha256'],rel
  for path in payload.rglob('*'):
   if path.is_file():shutil.copyfile(path,dest/'sdcard/wolf3d'/path.relative_to(payload))
  for rel in ('flexe-agon-emulator','flexe-agon-emulator.bin'):(dest/rel).chmod(0o755)
  (dest/'firmware').symlink_to((original/'firmware').resolve(),target_is_directory=True)
  for path in(original/'sdcard').iterdir():
   if path.name=='wolf3d'or(dest/'sdcard'/path.name).exists():continue
   if path.is_dir():shutil.copytree(path,dest/'sdcard'/path.name)
   else:shutil.copyfile(path,dest/'sdcard'/path.name)
  assert sha(dest/'flexe-agon-emulator.bin')=='7e7d0e1bc89af72bde7ffbd6c06446aaefda4d1803f89eb1faf3167307ee1e01'
  inputs={rel:sha(dest/rel)for rel in sorted(files)}
  (dest/'.runtime.sha256').write_text(''.join(d+'  '+r+'\n'for r,d in inputs.items()))
  spec=importlib.util.spec_from_file_location('canonical',HERE/'build/canonical/flexe_profile.py');canonical=importlib.util.module_from_spec(spec);spec.loader.exec_module(canonical)
  canonical.name_flexe_profile(dest);canonical.verify_profile_executables(dest/'flexe-agon-emulator',dest/'flexe-agon-emulator.bin')
  subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=dest,check=True)
  records.append({'index':index,'backend':backend,'profile':str(dest),'inputs':inputs,'timeout':300,'expect_abort':True})
 (out/'profiles.json').write_text(json.dumps(records,indent=2)+'\n')
 print('prepared two stopped normal-return failure controls')
if __name__=='__main__':main()
