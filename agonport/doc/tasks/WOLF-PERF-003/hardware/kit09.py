"""Freeze known clean bootstrap and unchanged matched benchmark inputs."""
from pathlib import Path
import hashlib,json,shutil,importlib.util,sys,inspect
from esptool.reset import HardReset
import serial
T=Path(__file__).resolve().parents[1];B=T/'build/hardware09';prior=T/'build/hardware08';E=Path('/Agon/mystuff/agon-extender')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
k=json.loads((prior/'kit.json').read_text())
for p,h in k['inputs'].items():assert sha(p)==h,p
r=json.loads((prior/'release52.json').read_text());assert r['generation']==52 and r['released']and all(r['release_observation']['checks'].values());assert r['release_observation']['components']==k['incoming_components']
for name in ('install-a.bin','install-b.bin','restore.bin'):
 shutil.copyfile(prior/name,B/name);assert sha(B/name)==sha(prior/name)
readback=prior/'evidence/flash-restore/read.bin';assert sha(readback)==sha(B/'restore.bin')
paths=(prior/'release52.json',readback,prior/'evidence/standing-paired-recovery/admission.json',T/'HARDWARE-RUN-09.md',T/'HARDWARE-R08-RESULT.md',T/'hardware/physical09.py',T/'hardware/bootstrap09.py',T/'hardware/test_controller09.py',T/'hardware/test_bootstrap09.py',T/'hardware/kit09.py',T/'hardware/report09.py',B/'install-a.bin',B/'install-b.bin',B/'restore.bin',E/'scripts/reset_agon_usb.py',E/'scripts/reset_agon.py',E/'scripts/p4_boot_guard.py',E/'scripts/passive_serial.py',E/'agents/bench-reset/usb-reset.local.json',Path(sys.executable).resolve(),Path(inspect.getsourcefile(HardReset)),Path(inspect.getsourcefile(serial.Serial)),Path('/Agon/mystuff/agon-dev-env/cross-agent/agentcoms/messages/2026-11-06_03-28-52_linux-extender_wolf52-bootstrap-source-disposition-two.md'))
for p in paths:k['inputs'][str(p)]=sha(p)
k.update(schema='wolf-perf003-physical-kit-v9',rollback_source=str(readback),interpreter=str(E/'.venv/bin/python'),p4_boot_build='net-004-r03-b2026-11-06-04-38-03Z')
sys.path.insert(0,str(T/'hardware'));sp=importlib.util.spec_from_file_location('physical09',T/'hardware/physical09.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);m.verify_kit(k)
(B/'kit.json').write_text(json.dumps(k,indent=2)+'\n');print('FROZEN',len(k['inputs']),'pins; unchanged compiled/timed inputs; clean bootstrap selected')
