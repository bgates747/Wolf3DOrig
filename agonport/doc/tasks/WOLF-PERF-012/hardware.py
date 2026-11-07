"""Uncapped visible fixture under held77; all agent RUN commands remain blocked."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import time

T=Path(__file__).resolve().parent;B=T/'build/hardware01'
P=T.parent/'WOLF-PERF-011'
s=importlib.util.spec_from_file_location('manual_base',P/'hardware.py')
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
h=base.h
s=importlib.util.spec_from_file_location('uncapped_decoder',T/'analyze.py')
decoder=importlib.util.module_from_spec(s);s.loader.exec_module(decoder)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Bench(base.Bench):
    def __init__(self,context):
        super().__init__(context)
        assert self.grant['generation']==77
        selected=json.loads((B/'selection.json').read_text())
        assert selected['original_kit_sha256']==sha(base.B/'kit.json')
        assert selected['module_sha256']==self.kit['module_sha256']
        assert json.loads((T/'CHECK-RESULT.json').read_text())['passed']
        s=importlib.util.spec_from_file_location('actual_binding',T.parent/'WOLF-PERF-009/guest_binding.py')
        binding=importlib.util.module_from_spec(s);s.loader.exec_module(binding)
        binding.verify(selected['guest'])
        self.kit=dict(self.kit,guest=selected['guest'])
        self.out=B/'evidence';self.out.mkdir(exist_ok=True)
        self.selected=selected

    def entry_and_archive(self):
        p=self.folder('entry');self.own();self.ports_free();self.check_entry_idle(self.state())
        assert json.loads((base.B/'evidence/complete.json').read_text())['restored']
        self.cli(p,'entry');self.service(p,'listener')
        for remote,name,key in (('/autoexec.txt','startup.bin','startup_sha256'),('/emos/sdserve.bin','listener.bin','listener_sha256')):
            self.transfer(p,name,'get',remote,p/name);assert sha(p/name)==self.components[key]
        c=self.metadata(p,'archive')
        try:
            entries=list(c.entries(self.remote));h.save(p/'before-directory.json',entries)
            assert not any(n.rsplit('/',1)[-1] in ('paced77-results','rotate-max.bin')for n,_,_ in entries)
            names={n.rsplit('/',1)[-1]:(n,size,attr)for n,size,attr in entries}
            archive=self.remote+'/paced77-results';c.make_directory(archive)
            moved=[]
            for name in ('before.bin','after.bin','timing.bin','native.bin','stack.bin','loading.bin','loading3.bin',
                         'completed-ram.bin','preserve.txt','wolf3d.cfg','post-mode.bin','post-callback.bin','route.bin'):
                source,size,attr=names[name];assert not attr&16
                previous=base.B/'evidence/human-run-collection'/name
                if previous.exists():assert previous.stat().st_size==size
                destination=archive+'/'+name
                h.save(p/(name+'-move-issued.json'),dict(source=source,destination=destination,once=True,size=size))
                c.move(source,destination)
                actual,attributes=c.stat_entry(destination)
                assert actual==size and not attributes&16
                moved.append(dict(source=source,destination=destination,size=size))
            h.save(p/'archive.json',dict(passed=True,moved=moved,old_host_raw_preserved=True))
        finally:c.lock.close()
        # Config path is now absent, so this is a fresh PUT without replacement siblings.
        self.upload(p,'empty-config',Path(self.kit['stage']['wolf3d.cfg']),self.remote+'/wolf3d.cfg')
        self.transfer(p,'existing-module','get',self.remote+'/wolf3d.vdpl',p/'module.bin')
        assert sha(p/'module.bin')==self.kit['module_sha256']
        self.upload(p,'new-guest',Path(self.kit['guest']['guest']),self.remote+'/rotate-max.bin')
        self.raw_state(p,'fresh-raw');self.verify_route(p,'fresh-route');self.exit(p,'exit')
        self.line(p,'mirror-off','VDU 3');self.check_entry_idle(self.state());self.ports_free()
        h.save(p/'receipt.json',dict(passed=True,guest_readback=True,module_readback=True,
            retained_assets='Prior full readbacks match source; unchanged under sole owner and guest does not write asset banks',
            previous_outputs_archived=True,no_guest_run=True))

    def prepare(self):
        self.entry_and_archive()
        self.flash('b',self.kit['install_b'])
        self.load_for_human()


    def load_for_human(self):
        """Terminal preparation boundary. No RUN, collector, reset or release."""
        p = self.folder('load-only')
        self.own()
        state = self.state(); self.check_entry_idle(state)
        self.ports_free()
        raw = bytearray()
        with h.m.open_passive_serial(self.port, baudrate=115200, timeout=.2) as serial:
            self.line(p, 'mirror', 'VDU 2')
            start = len(raw)
            self.line(p, 'cd', 'CD '+self.remote)
            self.capture(serial, raw, p, lambda r:self.remote.encode()+b' *' in r[start:], 20)
            start = len(raw)
            self.line(p, 'load', 'LOAD rotate-max.bin')
            self.capture(serial, raw, p, lambda r:self.remote.encode()+b' *' in r[start:], 20)
            assert b'Error loading' not in raw and b'Error executing' not in raw
            # VDU writes do not LOAD or execute code. Show the exact human command.
            message = b'READY: TYPE RUN . FOR UNCAPPED ROTATION'
            self.line(p, 'ready-message', 'VDU '+' '.join(map(str,message))+' 13 10')
            self.capture(serial, raw, p, lambda r:message in r, 20)
            self.line(p, 'mirror-off', 'VDU 3')
        state = self.state(); h.save(p/'state.json', state)
        self.check_entry_idle(state); self.ports_free()
        h.save(self.out/'ready.json', dict(ready=True, loaded_not_run=True,
            lease=self.lease, generation=self.grant['generation'], epoch=time.time(),
            selection_sha256=sha(B/'selection.json'), guest_sha256=sha(self.kit['guest']['guest']),
            module_sha256=self.kit['module_sha256'], manual_command='RUN .',
            cwd=self.remote, actors_stopped=True, retain_lease=True))
        print('READY LOADED NOT RUN; Smith must type RUN .; custody retained', flush=True)

    def collect_after_human(self):
        """Only selected after Smith confirms he ran it; never starts a guest."""
        ready = json.loads((self.out/'ready.json').read_text())
        assert ready['loaded_not_run'] and ready['lease'] == self.lease
        assert ready['selection_sha256'] == sha(B/'selection.json')
        p = self.folder('human-run-collection')
        self.own(); self.check_entry_idle(self.state())
        self.cli(p, 'actual-return')
        self.service(p, 'listener')
        # Preserve resident application/RAM before any later LOAD (none selected).
        script = p/'preserve.txt'
        script.write_bytes(('SAVE '+self.remote+'/completed-ram.bin &40000 &'+
            format(Path(self.kit['guest']['guest']).stat().st_size,'X')+
            '\r\nEMOS sdserve --fast /\r\n').encode())
        self.upload(p,'save-script',script,self.remote+'/preserve.txt')
        self.exit(p,'save-exit'); self.line(p,'save-resident','EXEC '+self.remote+'/preserve.txt')
        self.wait_online(True)
        for name in ('timing.bin','native.bin','loading.bin','loading3.bin','after.bin','stack.bin','before.bin','completed-ram.bin'):
            self.transfer(p,name,'get',self.remote+'/'+name,p/name)
        result = decoder.analyze(p)
        assert result['mode'] == 'uncapped-visible' and result['completed_records'] > 1
        listing = Path(self.kit['guest']['listing']).read_text(); after=(p/'after.bin').read_bytes()
        stack=[]
        for label in ('wp_entry_sp','wp_exit_sp'):
            m=re.search(r'^([0-9A-F]{6})[^\n]*\b'+label+r':',listing,re.M); assert m
            at=int(m[1],16)-0x40000; stack.append(int.from_bytes(after[at:at+3],'little'))
        assert stack[0] == stack[1] and 0xb0000 <= stack[0] < 0xc0000
        h.save(p/'receipt.json',dict(passed=True, human_started=True, agent_run=False,
            result=result, balanced_stack=stack, optical_confirmation='Ask Smith; not inferred from logs'))
        self.raw_state(p,'post'); self.exit(p,'exit')
        self.cleaning=True
        self.flash('restore',self.kit['restore']); self.handback()
        h.save(self.out/'complete.json',dict(passed=True,human_started=True,restored=True,
            no_agent_run=True,result=str(p/'report.json')))


def main():
    p=argparse.ArgumentParser();p.add_argument('--context',required=True)
    p.add_argument('--action',choices=('prepare','collect'),required=True);args=p.parse_args()
    c=json.loads(Path(args.context).read_text())
    assert sha(c['extension'])==c['extension_sha256']
    for n,d in json.loads(Path(c['extension']).read_text()).items():assert sha(n)==d,n
    s=importlib.util.spec_from_file_location('actual_launch',P/'launch.py')
    launch=importlib.util.module_from_spec(s);s.loader.exec_module(launch)
    assert launch.preflight()==json.loads((P/'LAUNCH-PREFLIGHT.json').read_text())
    s=importlib.util.spec_from_file_location('host_interrupt',T.parent/'WOLF-PERF-003/hardware/host_interrupt08.py')
    interrupt=importlib.util.module_from_spec(s);s.loader.exec_module(interrupt)
    interrupt.install(B/('host-interruption-'+args.action))
    b=Bench(args.context)
    try:
        if args.action=='prepare':b.prepare()
        else:b.collect_after_human()
    except BaseException as error:
        h.save(b.out/('failure-'+args.action+'.json'),dict(error=repr(error),epoch=time.time(),
            dispatch_stopped=True,custody_retained=True,no_agent_run=True))
        raise


if __name__=='__main__':main()
