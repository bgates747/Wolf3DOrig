"""Oryx-only stopped profile preparation from the pinned, qualified Wolf donor."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,subprocess
ROOT=Path('/home/smith/Agon/mystuff/Wolf3dOrig');TASK=ROOT/'agonport/doc/tasks/WOLF-PERF-002';OUT=ROOT/'.emulator/wolf-voice-r01';BASE=ROOT/'.emulator/wolf-perf-001-r07/paced'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 global OUT
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--name',default='wolf-voice-r01');parser.add_argument('--generic-only',action='store_true');args=parser.parse_args()
 if '/'in args.name or args.name in ('.','..'):parser.error('Profile name must be a simple directory name')
 OUT=ROOT/'.emulator'/args.name
 for f in (TASK/'voice/player/bin/playwav.bin',TASK/'build/voice/wolf-start.wav',TASK/'build/voiced/payload/wolf3d.bin'):
  assert f.is_file(),f
 assert not OUT.exists(),'fresh profiles required'
 subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=BASE,check=True)
 spec=importlib.util.spec_from_file_location('verify',ROOT/'agonport/doc/tasks/WOLF-PERF-001/build/canonical/flexe_profile.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 receipt=[]
 for kind in (('valid','invalid')if args.generic_only else ('valid','invalid','voiced')):
  d=OUT/kind;shutil.copytree(BASE,d,symlinks=True,ignore=shutil.ignore_patterns('run','last-run','timing.bin','native.bin','before.bin','after.bin','stack.bin','*.lock'))
  shutil.rmtree(d/'sdcard/wolf3d')
  if kind=='voiced':
   shutil.copytree(TASK/'build/voiced/payload',d/'sdcard/wolf3d');auto=b'SET KEYBOARD 1\r\ncd /wolf3d\r\nrunbin ./wolf3d.bin\r\n'
  else:
   app=d/'sdcard/voice';app.mkdir();shutil.copyfile(TASK/'voice/player/bin/playwav.bin',app/'playwav.bin');shutil.copyfile(TASK/'build/voice/wolf-start.wav',app/'wolf-start.wav');(app/'bad.wav').write_bytes(b'RIFF'+(36).to_bytes(4,'little')+b'WAVE')
   auto=('SET KEYBOARD 1\r\ncd /voice\r\nrunbin ./playwav.bin '+('bad.wav'if kind=='invalid'else'wolf-start.wav')+'\r\n').encode()
  (d/'sdcard/autoexec.txt').write_bytes(auto)
  m.verify_profile_executables(d/'flexe-agon-emulator',d/'flexe-agon-emulator.bin')
  names=['flexe-agon-emulator','flexe-agon-emulator.bin','esp32-firmware.bin','esp32-firmware.elf','flexe-vdp.so','mos_platform.bin','mos_platform.map','input.so']+[str(p.relative_to(d))for p in sorted((d/'sdcard').rglob('*'))if p.is_file()]
  pins={n:sha(d/n)for n in names};(d/'.runtime.sha256').write_text(''.join(h+'  '+n+'\n'for n,h in pins.items()));subprocess.run(['sha256sum','--check','--status','.runtime.sha256'],cwd=d,check=True);receipt.append(dict(kind=kind,profile=str(d),pins=pins))
 (OUT/'profiles.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Stopped isolated voice profiles prepared')
if __name__=='__main__':main()
