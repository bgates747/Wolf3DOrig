"""Fail before target access unless the actual selected host environment matches."""
from pathlib import Path
import argparse,hashlib,json,runpy,sys
T=Path(__file__).resolve().parent;E=Path('/Agon/mystuff/agon-extender')
def preflight():
    assert Path(sys.executable)==E/'.venv/bin/python','Use the pinned Extender interpreter; target access forbidden before host preflight'
    sys.path.insert(0,str(E/'scripts'))
    from esptool.reset import HardReset
    from serial import Serial
    from p4_boot_guard import check_startup
    assert callable(HardReset) and callable(Serial) and callable(check_startup)
    files={str(Path(sys.executable).resolve())}
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name and ('/site-packages/' in name or name==str(E/'scripts/p4_boot_guard.py')):files.add(str(Path(name).resolve()))
    return dict(passed=True,interpreter=sys.executable,files={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in sorted(files)},target_access=False)
def main():
    p=argparse.ArgumentParser();p.add_argument('--preflight-only',action='store_true');p.add_argument('--context',type=Path);a=p.parse_args()
    actual=preflight()
    if a.preflight_only:print(json.dumps(actual,indent=2));return
    assert a.context is not None
    expected=json.loads((T/'H02-LAUNCH-PREFLIGHT.json').read_text());assert actual==expected,'Actual launcher dependency closure differs from frozen host preflight'
    sys.argv=[str(T/'hardware02.py'),str(a.context.resolve())]
    runpy.run_path(str(T/'hardware02.py'),run_name='__main__')
if __name__=='__main__':main()
