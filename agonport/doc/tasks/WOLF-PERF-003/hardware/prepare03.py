"""New identified native recorder release candidate, never runs compilers/devices."""
from pathlib import Path
import hashlib,json,shutil
T=Path(__file__).resolve().parents[1];B=T/'build/hardware03';B.mkdir(exist_ok=False)
old=T/'build/hardware02';native=B/'native-a'
shutil.copytree(T/'build/hardware01/native-a',native,ignore=shutil.ignore_patterns('*.log'))
p=native/'video/wolf_perf_recorder.h';s=p.read_text();needle='    bool reset(uint8_t *store, size_t size, uint32_t current_core) {';assert s.count(needle)==1
s=s.replace(needle,'    void release() { data=nullptr; count=0; failed=false; }\n'+needle);p.write_text(s)
p=native/'video/wolf3d.h';s=p.read_text();needle='    } else if (op==241) {\n        ok=wp_recorder.read16(uint32_t(offset),value);\n    }';assert s.count(needle)==1
s=s.replace(needle,needle[:-5]+'    } else if (op==242) {\n        ok=offset==0;\n        if (ok) wp_recorder.release();\n    }')
s=s.replace('case 240: case 241: return wp_control(processor,subcmd);','case 240: case 241: case 242: return wp_control(processor,subcmd);');p.write_text(s)
for mode in ('cpu','unpaced','paced','control'):
 d=B/'bespoke'/mode;prior=old/'bespoke'/mode
 shutil.copytree(prior/'source',d/'source',ignore=shutil.ignore_patterns('*.bin','*.lst','*.log'))
 shutil.copytree(prior/'payload',d/'payload')
 p=d/'source/standalone.inc';s=p.read_text();needle='wp_a_create_log:\n';assert s.count(needle)==1
 s=s.replace(needle,'wp_a_disarm:\n    ld a,242\n    ld hl,0\n    jp wp_a_control\n'+needle+'    call wp_a_disarm\n    ret c\n');p.write_text(s)
 p=d/'source/bench.inc';s=p.read_text();needle='    ld hl,wp_clear_log\n';assert s.count(needle)==1
 s=s.replace(needle,'    call wp_a_disarm ; release borrow before deleting backing storage\n    jp c,wp_failed\n'+needle);p.write_text(s)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(B/'source-freeze.json').write_text(json.dumps({str(p.relative_to(B)):sha(p)for p in B.rglob('*')if p.is_file()and '.pio'not in p.parts and p.suffix not in ('.bin','.elf','.map','.lst','.log')},indent=2)+'\n')
print('Prepared native release API plus four A guests; no compiler or target action')
