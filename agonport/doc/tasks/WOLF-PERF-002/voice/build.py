#!/usr/bin/env python3
"""Compile only a task-owned paced application; reuse the exact native module."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;ROOT=TASK.parents[3]
BASE=TASK.parent/'WOLF-PERF-001/build/paced';OUT=TASK/'build/voiced'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def patch(s,a,b):
 if s.count(a)!=1:raise ValueError('ambiguous patch: '+a)
 return s.replace(a,b)
def main():
 assert not OUT.exists(),'fresh build required'
 src=OUT/'source';shutil.copytree(BASE/'source',src,ignore=shutil.ignore_patterns('*.lst','*.bin'))
 s=(src/'bench.inc').read_text()
 s=patch(s,'    call wp_prt_init\n','    call wp_prt_init\n    call wp_voice_prepare\n')
 s=patch(s,'    ; Empty 600-iteration control.','    call wp_voice_play\n    ; Empty 600-iteration control.')
 s=patch(s,'    call wp_prt_stop\n    ; Presentation','    call wp_prt_stop\n    ld hl,wp_voice_rotation_done\n    call printString\n    ; Presentation')
 (src/'bench.inc').write_text(s+'\n    include "voice_start.inc"\n')
 shutil.copyfile(HERE/'start.inc',src/'voice_start.inc');shutil.copyfile(TASK/'build/voice/voice_duration.inc',src/'voice_duration.inc')
 spec=importlib.util.spec_from_file_location('builder',ROOT/'src/asm/wolf3d/scripts/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
 subprocess.run([str(b.resolve_assembler(None)),'wolf3d.asm','wp.bin','-l','-c'],cwd=src,check=True,timeout=120)
 payload=OUT/'payload';shutil.copytree(BASE/'payload',payload)
 shutil.copyfile(src/'wp.bin',payload/'wolf3d.bin');shutil.copyfile(TASK/'build/voice/voice.agnb',payload/'voice.agnb')
 assert 0x40000+(payload/'wolf3d.bin').stat().st_size<=0xa0000
 assert sha(payload/'wolf3d.vdpl')=='27f3d39285a5b49fec8aeed35085b1916ef537154f1d1d53956b075e00174c82'
 expected=json.loads((BASE/'payload/expected.json').read_text());expected.update(scope='visible-only paced rotation with spoken cue before timing',voice=json.loads((TASK/'build/voice/manifest.json').read_text()))
 expected['files']={str(p.relative_to(payload)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(payload.rglob('*')) if p.is_file() and p.name!='expected.json'}
 (payload/'expected.json').write_text(json.dumps(expected,indent=2)+'\n')
 (OUT/'sources.json').write_text(json.dumps({str(p.relative_to(src)):sha(p) for p in sorted(src.iterdir()) if p.is_file()},indent=2)+'\n')
 print('Voiced paced payload:',payload)
if __name__=='__main__':main()
