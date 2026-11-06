from pathlib import Path
import shutil,hashlib,json
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;ROOT=TASK.parents[3];out=TASK/'build/fabbridge01';out.mkdir(exist_ok=False)
# Private copies only. Reuse retained x86 compatibility objects; no owner edits.
video=TASK/'build/r04/inputs/bespoke/video';shutil.copytree(video,out/'video')
shutil.copytree(Path('/Agon/mystuff/fab-agon-emulator/src/vdp'),out/'fab/src/vdp',ignore=shutil.ignore_patterns('.git','*.o','*.a','*.so','__pycache__'))
shutil.copytree(Path('/Agon/mystuff/agon-vdp-wolf3d/.pio/libdeps/esp32dev/CRC'),out/'deps/CRC',ignore=shutil.ignore_patterns('.git'))
shutil.copytree(Path('/Agon/mystuff/agon-vdp-wolf3d/.pio/libdeps/esp32dev/ESP32Time'),out/'deps/ESP32Time',ignore=shutil.ignore_patterns('.git'))
mod=out/'video/host-module/production';shutil.copytree(TASK/'build/r04/inputs/module',mod)
q=mod.parent/'qualification';q.mkdir();shutil.copyfile(ROOT/'agonport/vdplet/qualification/vdplet_host_shim.h',q/'vdplet_host_shim.h')
shutil.copyfile(TASK/'build/r04/inputs/wolf3d_tables.inc',mod.parent/'wolf3d_tables.inc')
shutil.copytree(TASK/'build/r04/inputs/sdk/include',out/'sdk')
for n in ('bridge.h','selftest.cpp'):shutil.copyfile(HERE/n,out/('video/wolf_fab_bridge.h'if n=='bridge.h'else n))
package=(TASK/'build/r07/vdplet/paced/payload/wolf3d.vdpl').read_bytes()
(out/'video/expected_package.h').write_text('static const unsigned char wolf_expected_package[]={'+','.join(map(str,package))+'};\n')
p=out/'video/vdu_stream_processor.h';s=p.read_text();anchor='\t\tvoid vdu_sys_video();';assert s.count(anchor)==1;p.write_text(s.replace(anchor,anchor+'\n\t\tvoid vdu_sys_wolf_fab(bool discovery);'))
p=out/'video/vdu_sys.h';s=p.read_text();anchor='#include "ymodem.h"';s=s.replace(anchor,anchor+'\n#include "wolf_fab_bridge.h"');anchor='\t\tcase VDP_CONTEXT: {';assert s.count(anchor)==1;s=s.replace(anchor,'\t\tcase 0xD8: vdu_sys_wolf_fab(false); break;\n\t\tcase 0xD9: vdu_sys_wolf_fab(true); break;\n'+anchor);p.write_text(s)
(out/'adapter.cpp').write_text('#include "Arduino.h"\n#include "vdp-console8.h"\nfabgl::SoundGenerator *getVDPSoundGenerator(){return &*soundGenerator;}\n#include "video/video.ino"\n')
cache=out/'cache';cache.mkdir()
for n in ('libvdp-gl.a','rust_glue.o','CRC16.o','CRC32.o','CrcFastReverse.o'):shutil.copyfile(Path('/Agon/mystuff/agon-vdp-wolf3d/video/build/userspace')/n,cache/n)
files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(out.rglob('*'))if p.is_file()}
(out/'source-freeze.json').write_text(json.dumps({'purpose':'single exact-package native production-source Fab visual adapter;not-Xtensa','files':files},indent=2)+'\n');print(out,len(files))
