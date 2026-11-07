"""Correct only manifest-scoped staging after the stopped77 host path assertion."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import time

T=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('wolf011_manual',T/'hardware.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
h=base.h
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Bench(base.Bench):
    def fresh_continuation_entry(self):
        assert json.loads((self.out/'entry/receipt.json').read_text())['passed']
        assert (self.out/'failure-prepare.json').exists()
        assert not any((self.out/n).exists() for n in ('stage','flash-b','load-only','ready.json'))
        p=self.folder('continuation-entry')
        self.own();self.ports_free();self.check_entry_idle(self.state())
        raw=self.cli(p,'fresh-cli')
        assert b'Directory: /' in raw
        self.service(p,'listener')
        for remote,name,key in (('/autoexec.txt','startup.bin','startup_sha256'),
                                ('/emos/sdserve.bin','listener.bin','listener_sha256')):
            self.transfer(p,name,'get',remote,p/name)
            assert sha(p/name)==self.components[key]
        c=self.metadata(p,'entry-files')
        try:
            entries=list(c.entries(self.remote));h.save(p/'entries.json',entries)
            assert {n.rsplit('/',1)[-1]for n,_,_ in entries}=={
                'level_00','state.txt','route.txt','post-mode.bin','post-callback.bin','route.bin'}
            assert list(c.entries(self.remote+'/level_00'))==[]
        finally:c.lock.close()
        for name in ('state.txt','route.txt'):
            self.transfer(p,name,'get',self.remote+'/'+name,p/name)
            assert (p/name).read_bytes()==Path(self.kit['stage'][name]).read_bytes()
        self.raw_state(p,'fresh-raw');self.verify_route(p,'fresh-route')
        self.exit(p,'exit');self.line(p,'mirror-off','VDU 3')
        state=self.state();h.save(p/'state.json',state)
        self.check_entry_idle(state);self.ports_free()
        h.save(p/'receipt.json',dict(passed=True,epoch=time.time(),lease=self.lease,
            kit_sha256=sha(base.B/'kit.json'),no_guest_loaded=True,no_firmware_written=True))

    def stage(self):
        entry=json.loads((self.out/'continuation-entry/receipt.json').read_text())
        assert entry['passed'] and entry['lease']==self.lease
        assert entry['kit_sha256']==sha(base.B/'kit.json')
        assert 0<=time.time()-entry['epoch']<120
        p=self.folder('stage');self.service(p,'listener')
        for i,(name,local)in enumerate(self.kit['stage'].items()):
            if name in ('state.txt','route.txt'):continue
            self.admit('staging file '+name)
            self.upload(p,f'file-{i:02d}',local,self.remote+'/'+name)
            print('STAGED',name,flush=True)
        self.exit(p,'exit')
        h.save(p/'receipt.json',dict(passed=True,files=len(self.kit['stage']),put_get_verified=True))

    def continuation(self):
        self.fresh_continuation_entry()
        self.stage()
        self.flash('b',self.kit['install_b'])
        self.load_for_human()


def main():
    p=argparse.ArgumentParser();p.add_argument('--context',required=True);args=p.parse_args()
    c=json.loads(Path(args.context).read_text())
    assert sha(c['extension'])==c['extension_sha256']
    for n,d in json.loads(Path(c['extension']).read_text()).items():assert sha(n)==d,n
    # Same actual interpreter/import closure as the original qualified launcher.
    s=importlib.util.spec_from_file_location('launch_check',T/'launch.py')
    launch=importlib.util.module_from_spec(s);s.loader.exec_module(launch)
    assert launch.preflight()==json.loads((T/'LAUNCH-PREFLIGHT.json').read_text())
    s=importlib.util.spec_from_file_location('interrupt',T.parent/'WOLF-PERF-003/hardware/host_interrupt08.py')
    interrupt=importlib.util.module_from_spec(s);s.loader.exec_module(interrupt)
    interrupt.install(base.B/'host-interruption-continuation01')
    b=Bench(args.context)
    try:b.continuation()
    except BaseException as error:
        h.save(b.out/'failure-continuation01.json',dict(error=repr(error),epoch=time.time(),
            dispatch_stopped=True,custody_retained=True,no_agent_run=True))
        raise


if __name__=='__main__':main()
