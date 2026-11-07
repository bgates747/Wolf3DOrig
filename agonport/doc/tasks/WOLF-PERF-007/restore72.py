"""Cleanup only: exact incoming span restore/readback/bootstrap/full handback."""
from pathlib import Path
import importlib.util,json,sys,time
T=Path(__file__).resolve().parent;B=T/'build/hardware01'
spec=importlib.util.spec_from_file_location('wolf007_restore72',T/'hardware.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def main():
    assert Path(sys.executable)==Path('/Agon/mystuff/agon-extender/.venv/bin/python')
    from esptool.reset import HardReset
    assert HardReset
    b=m.Bench.__new__(m.Bench);b.c=json.loads((B/'context72.json').read_text());b.grant=json.loads((B/'grant72.json').read_text());b.grant=b.grant.get('active',b.grant)
    b.kit=json.loads((B/'kit.json').read_text());m.verify_kit(b.kit)
    assert b.grant['generation']==72 and b.grant['request']==b.kit['request'] and b.grant['owner']=='wolf3dorig'
    b.components=b.grant['entry_observation']['components'];assert b.components==b.kit['incoming_components']
    b.lease=b.grant['lease'];b.url=b.c['url'];b.port=b.c['native_port'];b.remote=b.kit['remote'];b.out=B/'evidence';b.cleaning=True;b.deadline=time.monotonic()
    b.selected_module_sha256=b.kit['original_module_sha256']
    failure=json.loads((b.out/'failure.json').read_text());assert failure['error']=="ModuleNotFoundError(\"No module named 'esptool'\")"
    assert (b.out/'flash-b/read.bin').read_bytes()==Path(b.kit['install_b']).read_bytes()
    assert not (b.out/'flash-b/clean-bootstrap').exists()
    assert not list(b.out.glob('probe-*')) and not list(b.out.glob('0*-vdplet-*'))
    m.h.save(b.out/'cleanup-selection.json',dict(scope='Only exact incoming native app/tail restoration/readback, one existing matched bootstrap and full handback; no benchmark or timing-image bootstrap/replay.',original_failure_preserved=True,benchmark_guests=0,resource_probes=0,p4_clean_bootstraps_before_restore=0,interpreter=sys.executable,epoch=time.time()))
    b.own();b.ports_free()
    try:
        b.flash('restore',b.kit['restore']);b.handback()
        m.h.save(b.out/'stopped-restored.json',dict(restored=True,benchmark_guests=0,resource_probes=0,performance_claim=False,scope='Exact incoming span restored and independently read back; matched bootstrap/full handback only, failed cohort not replayed.',epoch=time.time()))
        print('PASS cleanup-only exact incoming restoration/readback/full handback; no test replay',flush=True)
    except BaseException as error:
        m.h.save(b.out/'cleanup-failure.json',dict(error=repr(error),custody_retained=True,no_replay=True,epoch=time.time()));raise
if __name__=='__main__':main()
