"""Oryx only: copy verified owned setup-stall inputs into fresh FX-152 profiles."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess

ROOT=Path.home()/'Agon/mystuff/Wolf3dOrig'
HERE=Path(__file__).resolve().parent
FRONT=Path.home()/'Agon/mystuff/flexe-agon-emulator/build/fx152/candidate-r01/flexe-agon-emulator'
FRONT_SHA='625d08b7d2c119ab149ad63ec696af0a03808dca0ae78b66a8fe35755dfaed84'
READER=HERE/'build/s01/read_record.py'
READER_SHA='c5701735631da1b1cf5bc74874bfef4da1c4cd50118809f8cd2d80c90e0fa85b'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
 assert sha(FRONT)==FRONT_SHA and sha(READER)==READER_SHA
 spec=importlib.util.spec_from_file_location('canonical_flexe',HERE/'build/canonical/flexe_profile.py')
 canonical=importlib.util.module_from_spec(spec);spec.loader.exec_module(canonical)
 out=ROOT/'.emulator/wolf-perf003-s01';out.mkdir(exist_ok=False)
 records=[]
 for index,name in enumerate(('q02/02-bespoke-cpu','q01/06-vdplet-paced'),1):
  cohort,case=name.split('/');source=ROOT/'.emulator'/('wolf-perf003-'+cohort)/case
  subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=source,check=True)
  dest=out/f'{index:02d}-{case[3:]}';dest.mkdir()
  # Copy to new regular files; never write through another profile's symlinks.
  files={line.split('  ',1)[1] for line in (source/'.runtime.sha256').read_text().splitlines()}
  files.update(('.bespoke-vdp-profile','.mos-release','.mos-release.sha256'))
  for rel in sorted(files):
   assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
   target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True)
   shutil.copyfile(source/rel,target)
  shutil.copyfile(FRONT,dest/'flexe-agon-emulator.bin')
  for rel in ('flexe-agon-emulator','flexe-agon-emulator.bin'):(dest/rel).chmod(0o755)
  (dest/'firmware').symlink_to((source/'firmware').resolve(),target_is_directory=True)
  # Canonical non-game MOS utilities remain identical; exclude old result files.
  for directory in (source/'sdcard').iterdir():
   if directory.name=='wolf3d' or (dest/'sdcard'/directory.name).exists():continue
   if directory.is_dir():shutil.copytree(directory,dest/'sdcard'/directory.name)
   else:shutil.copyfile(directory,dest/'sdcard'/directory.name)
  assert not any((dest/'sdcard/wolf3d'/n).exists() for n in ('timing.bin','native.bin'))
  inputs={rel:sha(dest/rel)for rel in sorted(files)}
  assert inputs['flexe-vdp.so']=='0866265bd6f3d73ad572f31dc1bb954f308ed9a5d857efa9414d37e1ade13374'
  assert inputs['flexe-agon-emulator.bin']==FRONT_SHA
  (dest/'.runtime.sha256').write_text(''.join(digest+'  '+rel+'\n'for rel,digest in inputs.items()))
  canonical.name_flexe_profile(dest)
  canonical.verify_profile_executables(dest/'flexe-agon-emulator',dest/'flexe-agon-emulator.bin')
  subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=dest,check=True)
  records.append({'index':index,'source':str(source),'profile':str(dest),'inputs':inputs,'timeout':300,'diagnostic_only':True})
 (out/'profiles.json').write_text(json.dumps(records,indent=2)+'\n')
 print(json.dumps({'profiles':str(out/'profiles.json'),'count':len(records)}))

if __name__=='__main__':main()
