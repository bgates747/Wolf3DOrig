#!/usr/bin/env python3
"""Oryx-only: create stopped task profiles via canonical generator."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess
HOME=Path.home();ROOT=HOME/'Agon/mystuff/Wolf3dOrig';HERE=Path(__file__).resolve().parent
BASE=HOME/'Agon/mystuff/AgonArcade/.emulator/rally28-hz60-rows01-rows60'
OUT=ROOT/'.emulator/wolf-perf-001-r07'
PINS={'flexe-agon-emulator.bin':'7e7d0e1bc89af72bde7ffbd6c06446aaefda4d1803f89eb1faf3167307ee1e01','esp32-firmware.bin':'a50eb23acf6b3edfb44d3c1bb44858a213be696d68c06a696da7767170ac6f9a','flexe-vdp.so':'0866265bd6f3d73ad572f31dc1bb954f308ed9a5d857efa9414d37e1ade13374'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 spec=importlib.util.spec_from_file_location('canonical',HOME/'Agon/mystuff/agon-dev-env/scripts/setup_emulator.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
 for name,digest in PINS.items():
  if sha(BASE/name)!=digest:raise ValueError('runtime donor drift: '+name)
 spec2=importlib.util.spec_from_file_location('profile_preflight',HERE/'build/canonical/flexe_profile.py');exec_check=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(exec_check)
 receipts=[]
 for mode in ('cpu','unpaced','paced','cpu-fail'):
  profile=OUT/mode
  if (profile/'run').exists():raise ValueError('fresh profile required: '+str(profile))
  if (profile/'.runtime.sha256').exists():
   subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=profile,check=True)
   inputs={line.split('  ',1)[1]:line.split('  ',1)[0] for line in (profile/'.runtime.sha256').read_text().splitlines()}
   receipts.append({'mode':mode,'profile':str(profile),'inputs':inputs,'stopped':True})
   continue
  sd=c.link_shared_runtime(profile,HOME/'Agon/mystuff/golem/.emulator/runtime/fab-1.2.5')
  c.replace_symlink(profile/'fab-agon-emulator.bin',BASE/'flexe-agon-emulator.bin')
  for name in ('flexe-vdp.so','esp32-firmware.bin','esp32-firmware.elf'):shutil.copyfile(BASE/name,profile/name)
  (profile/'.bespoke-vdp-profile').write_text('flexe-vdp.so\n')
  payload=HERE/'build'/mode/'payload';expected=json.loads((payload/'expected.json').read_text())
  for name,entry in expected['files'].items():
   if sha(payload/name)!=entry['sha256']:raise ValueError('payload drift')
  shutil.copytree(payload,sd/'wolf3d',ignore=shutil.ignore_patterns('*.lst'),dirs_exist_ok=True)
  (sd/'autoexec.txt').write_bytes(b'SET KEYBOARD 1\r\ncd /wolf3d\r\nrunbin ./wolf3d.bin\r\n')
  c.write_profile_launcher(profile,strict_bespoke=True)
  launcher=profile/'fab-agon-emulator';s=launcher.read_text()
  env='''
export AGON_FLEXE_FIRMWARE="$profile_dir/esp32-firmware.bin"
export AGON_FLEXE_ELF="$profile_dir/esp32-firmware.elf"
export AGON_FLEXE_ENGINE="${AGON_FLEXE_ENGINE:-jit}"
export AGON_FLEXE_ARTIFACTS="$profile_dir/last-run"
mkdir -p "$AGON_FLEXE_ARTIFACTS"
'''
  if s.count('\nvdp_name=')!=1:raise ValueError('wrapper selection drift')
  launcher.write_text(s.replace('\nvdp_name=',env+'\nvdp_name=',1));launcher.chmod(0o755)
  c.name_flexe_profile(profile)
  exec_check.verify_profile_executables(profile/'flexe-agon-emulator',profile/'flexe-agon-emulator.bin')
  # Qualified existing SDL input shim: task runner uses only its quit event.
  donor=ROOT/'.emulator/vdplet-rows-review/review-input.so'
  shutil.copyfile(donor,profile/'input.so')
  files=['flexe-agon-emulator','flexe-agon-emulator.bin','flexe-vdp.so','esp32-firmware.bin','esp32-firmware.elf','mos_platform.bin','mos_platform.map','sdcard/autoexec.txt','input.so']
  files.extend(str(p.relative_to(profile)) for p in sorted((sd/'wolf3d').rglob('*')) if p.is_file())
  (profile/'.runtime.sha256').write_text(''.join(f'{sha(profile/n)}  {n}\n' for n in files))
  subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=profile,check=True)
  receipts.append({'mode':mode,'profile':str(profile),'inputs':{n:sha(profile/n) for n in files},'stopped':True})
 (OUT/'profiles.json').write_text(json.dumps(receipts,indent=2)+'\n');print(json.dumps(receipts,indent=2))
if __name__=='__main__':main()
