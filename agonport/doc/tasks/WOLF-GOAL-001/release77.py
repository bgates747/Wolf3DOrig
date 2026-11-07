"""Fresh cleanup-only release proof; no guest, flash, reset or RUN."""
from pathlib import Path
import importlib.util
import json
import re
import subprocess
import time

T=Path(__file__).resolve().parent;B=T/'build/release77'
P=T.parent/'WOLF-PERF-012'
spec=importlib.util.spec_from_file_location('last_owned_bench',P/'hardware.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
h=module.h


def main():
    b=module.Bench(P/'build/hardware01/context.json')
    original=b.out
    assert h.sha((original/'flash-restore/read.bin').read_bytes())=='85f9cf31219d679cffef48029d736331a3a3dfc78511d19d48a04cd2bd6a74de'
    assert json.loads((original/'complete.json').read_text())['restored']
    b.out=B;b.cleaning=True
    b.own();b.ports_free();state=b.state();b.check_entry_idle(state)
    h.save(B/'initial-state.json',state)
    first=b.folder('first-cli');raw=b.cli(first,'fresh-release')
    assert re.search(rb'Directory: /\s*\r?\n',raw)
    p=b.folder('checks');b.service(p,'listener')
    for remote,name,key in (('/autoexec.txt','startup.bin','startup_sha256'),('/emos/sdserve.bin','listener.bin','listener_sha256')):
        b.transfer(p,name,'get',remote,p/name)
        assert h.sha((p/name).read_bytes())==b.components[key]
    b.raw_state(p,'fresh-raw');b.verify_route(p,'fresh-route');b.exit(p,'exit')
    b.line(p,'cursor','VDU 4 23 1 1 23 1 3')
    final=b.folder('final-cli');raw=b.cli(final,'root')
    assert re.search(rb'Directory: /\s*\r?\n',raw)
    b.line(final,'mirror-off','VDU 3')
    state=b.state();h.save(B/'final-state.json',state)
    b.check_entry_idle(state);b.ports_free()
    checks={k:True for k in ('no_workload','no_transfer','no_serial_readers','no_reset_holders',
        'cli_verified','input_ready_neutral','listener_offline','staged_job_idle','restoration_verified')}
    obs=dict(schema='olimex-bench-observation-v1',bench='olimex',epoch=time.time(),
        observer='wolf3dorig',lease=b.lease,checks=checks,components=b.components,
        component_provenance={k:('Fresh whole-file read/compare during release'if k in ('startup_sha256','listener_sha256')
            else 'Exact prior same-custody full-span restoration/readback; no intervening firmware/guest operation'if k=='native_vdp_sha256'
            else 'Retained unchanged current77 identity; Wolf never wrote this component')for k in b.components},
        evidence=[str(B/'final-state.json'),str(final/'serial.bin'),str(p/'startup.bin'),str(p/'listener.bin'),
            str(p/'fresh-raw-mode.bin'),str(p/'fresh-raw-callback.bin'),str(p/'fresh-route.bin'),str(original/'flash-restore/receipt.json')],
        disposition='Smith new overnight direction makes MechAgon first priority and Wolf second; release restored idle77 for normal scheduler use. No new RUN/LOAD/reset/flash; old accepted results preserved, SD mounted.')
    h.save(B/'observation.json',obs)
    argv=['/Agon/mystuff/agon-dev-env/.venv/bin/python','/Agon/mystuff/agon-dev-env/cross-agent/olimex-bench/bench_lease.py',
        'release','--owner','wolf3dorig','--lease',b.lease,'--idle-evidence',str(B/'observation.json')]
    b.own()
    with (B/'released77.json').open('x')as f:subprocess.run(argv,stdout=f,check=True)
    print((B/'released77.json').read_text(),flush=True)


if __name__=='__main__':main()
