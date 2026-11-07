"""Exact incoming restoration only after original89 pre-guest bootstrap failure."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,time
T=Path(__file__).resolve().parent;B=T/'build/hardware01';C=B/'cleanup89'
E=Path('/Agon/mystuff/agon-extender/agents/bench-scheduler/wolf-perf019-r01')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    grant=json.loads((E/'grant.json').read_text());context=json.loads((E/'context.json').read_text())
    assert grant['owner']=='wolf3dorig'and grant['generation']==89 and grant['request']=='1fec8fdf3f1b'
    assert grant['lease']=='1e6055eea0224fa6b557752484206782'
    assert context['manifest']==str(B/'kit.json')and context['sole_operator_handoff']and context['no_pending_extender_target_commands']
    assert sha(B/'kit.json')=='4e6612a4979a8b227c733195b7b9ad189097950daa4eba3f2bf76d6bfaacb67a'
    failure=B/'evidence/failure.json';f=json.loads(failure.read_text())
    assert f['error']=="RuntimeError('Agon admission failed; no retry/RUN')"and f['custody_retained']and f['next_dispatch_stopped']
    assert not list((B/'evidence').glob('??-vdplet-*')) and not list((B/'evidence').glob('probe-*'))
    assert not list((B/'evidence').glob('module-*'))
    assert (B/'evidence/flash-b/read.bin').read_bytes()==Path(json.loads((B/'kit.json').read_text())['install_b']).read_bytes()
    assert (B/'evidence/flash-b/clean-bootstrap/agon-reset-issued.json').exists()
    assert not (B/'evidence/flash-b/clean-bootstrap/receipt.json').exists()
    spec=importlib.util.spec_from_file_location('wolf019_cleanup89_adapter',T/'hardware02.py')
    hw=importlib.util.module_from_spec(spec);spec.loader.exec_module(hw)
    hw.verify_kit(json.loads((B/'kit.json').read_text()))
    C.mkdir(exist_ok=False)
    shutil.copyfile(B/'kit.json',C/'kit.json');assert sha(C/'kit.json')==sha(B/'kit.json')
    copied=dict(context);copied['manifest']=str(C/'kit.json')
    copied['cleanup_only']=dict(original_context=str(E/'context.json'),original_context_sha256=sha(E/'context.json'),
        original_grant_sha256=sha(E/'grant.json'),original_failure=str(failure),original_failure_sha256=sha(failure),
        original_driver_terminal=1,no_guest_probe_module_or_LOAD=True,once=True)
    (C/'context.json').write_text(json.dumps(copied,indent=2)+'\n')
    # The ordinary constructor is file-only. Give it a fresh evidence directory
    # and byte-identical immutable kit; do not bypass its binding checks or call
    # entry/stage/suite/probe/case/run_cases. Original evidence is never reused.
    hw.B=C;hw.h.B=C
    b=hw.Bench(C/'context.json');b.cleaning=True;b.deadline=time.monotonic()+900
    entry=b.out/'entry';entry.mkdir(exist_ok=False)
    for name,key in (('startup.bin','startup_sha256'),('listener.bin','listener_sha256')):
        source=B/'evidence/entry'/name;assert sha(source)==b.components[key]
        shutil.copyfile(source,entry/name)
    b.own();b.ports_free()
    hw.h.save(C/'scope.json',dict(cleanup_only=True,epoch=time.time(),lease=b.lease,
        no_pre_restore_reset=True,no_suite_guest_probe_LOAD_or_replay=True,original_failure_preserved=True,
        no_guest_RAM_claim=True,startup_listener_unchanged_since_original_read=True,
        action='Exact incoming native/tail restore/readback FIRST, one current matched bootstrap/fullhandback then STOP/release'))
    try:
        b.flash('restore',b.kit['restore'])
        b.handback()
        hw.h.save(C/'complete.json',dict(passed=True,exact_incoming_restored=True,full_handback=True,
            original_suite_failed=True,room_records=0,owned_actors_stopped=True,epoch=time.time()))
    except BaseException as error:
        hw.h.save(C/'failure.json',dict(error=repr(error),cleanup_leaf_stopped=True,custody_retained=True,
            no_retry=True,epoch=time.time()))
        raise
if __name__=='__main__':main()
