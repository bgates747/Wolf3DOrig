"""Exercise the real load-only method and final keyboard RUN rejection seam."""
from pathlib import Path
import importlib.util
import json
import tempfile
from unittest.mock import patch

T=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('visible_hardware',T/'hardware.py')
hw=importlib.util.module_from_spec(spec);spec.loader.exec_module(hw)


class Serial:
    def __enter__(self):return self
    def __exit__(self,*args):pass


def main():
    commands=[]
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);out=root/'evidence';out.mkdir()
        (root/'selection.json').write_text('{}');(root/'guest.bin').write_bytes(b'qualified guest stand-in')
        b=object.__new__(hw.Bench)
        b.out=out;b.remote='/test/wolf/perf011/r01';b.port='unused';b.lease='test-only'
        b.grant={'generation':0};b.kit={'guest':{'guest':str(root/'guest.bin')},'module_sha256':'test-only'}
        b.own=lambda:None;b.ports_free=lambda:None
        b.state=lambda:dict(keyboard=dict(ready=True,physical_neutral=True,held=[],pending=False),
            sd=dict(online=False,pending=False),worker=dict(phase=0))
        def capture(serial,raw,folder,predicate,bound):
            raw.extend(b'/test/wolf/perf011/r01 * READY: TYPE RUN . FOR UNCAPPED ROTATION\r\n')
            assert predicate(raw)
        b.capture=capture
        def line(self,folder,label,command):commands.append(command)
        with patch.object(hw,'B',root),patch.object(hw.base.parent.Bench,'line',line),patch.object(hw.h.m,'open_passive_serial',lambda *a,**k:Serial()):
            b.load_for_human()
            assert commands[2]=='LOAD rotate-max.bin' and commands[-1]=='VDU 3'
            assert not any(x.upper().startswith(('RUN','EXEC')) for x in commands)
            ready=json.loads((out/'ready.json').read_text())
            assert ready['loaded_not_run'] and ready['actors_stopped'] and ready['retain_lease']
            for command in ('RUN .','run .','  RuN .','RUN rotate.bin'):
                before=len(commands)
                try:b.line(out,'forbidden',command)
                except RuntimeError:pass
                else:raise AssertionError('Agent RUN reached keyboard transport')
                assert len(commands)==before
    print('PASS actual load-only flow, ready receipt, actor closure, four RUN rejection cases; no target I/O')


if __name__=='__main__':main()
