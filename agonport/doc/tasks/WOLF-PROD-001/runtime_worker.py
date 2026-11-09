"""One fresh-process backend-only correctness run; no process is launched on import."""
from pathlib import Path
import hashlib, importlib.util, json, sys


def main():
    root=Path(__file__).resolve().parent
    pins=json.loads((root/'INPUTS.json').read_text())
    for name,expected in pins['files'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=expected:
            raise RuntimeError('Runtime input changed: '+name)
    spec=importlib.util.spec_from_file_location('production_qualification',root/'production/qualify.py')
    q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
    original=q.Target
    def construct(*args,**kwargs):
        target=original.__new__(original)
        try:
            original.__init__(target,*args,**kwargs)
            return target
        except BaseException:
            thread=getattr(target,'thread',None)
            if thread is not None:
                target.lib.vdp_shutdown();thread.join(timeout=10)
                if thread.is_alive():
                    raise RuntimeError('Constructor failure: owned native worker did not join')
            raise
    q.Target=construct
    result=q.qualify('jit',root/'firmware/vdp.bin',root/'backend/flexe-vdp.so',root/'results',600)
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
