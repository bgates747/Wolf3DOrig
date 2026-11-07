"""Actual corrected staging ignores the donor's different global manifest path."""
from pathlib import Path
import importlib.util
import json
import tempfile
import time
from unittest.mock import patch

T=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('continuation',T/'continue_prepare.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);out=root/'evidence';(out/'continuation-entry').mkdir(parents=True)
        (root/'kit.json').write_text('new task kit')
        (root/'guest.bin').write_text('verified guest')
        entry=dict(passed=True,epoch=time.time(),lease='test',kit_sha256=m.sha(root/'kit.json'))
        (out/'continuation-entry/receipt.json').write_text(json.dumps(entry))
        b=object.__new__(m.Bench);b.out=out;b.lease='test';b.remote='/test-only'
        b.kit={'stage':{'state.txt':'already checked','route.txt':'already checked','rotate.bin':str(root/'guest.bin')}}
        calls=[];b.service=lambda *a:calls.append('listener');b.admit=lambda *a:None
        b.upload=lambda *a:calls.append(('upload',a[2],a[3]));b.exit=lambda *a:calls.append('exit')
        with patch.object(m.base,'B',root),patch.object(m.base.parent,'B',root/'WRONG-DONOR-PATH'):
            b.stage()
        assert calls==['listener',('upload',str(root/'guest.bin'),'/test-only/rotate.bin'),'exit']
        assert json.loads((out/'stage/receipt.json').read_text())['passed']
    print('PASS corrected real stage uses own manifest with different donor path; no RUN or target I/O')


if __name__=='__main__':main()
