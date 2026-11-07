"""Restore incoming image FIRST after the pre-guest missing-bootstrap-pin stop.

Separate cleanup-only context, ordinary file-only constructor, same actual97.
No original-kit mutation, pre-restore reset, guest, INFO probe or suite replay.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import time

T=Path(__file__).resolve().parent
B=T/'build/hardware01'
C=B/'cleanup97'
G=Path('/Agon/mystuff/agon-extender/agents/bench-scheduler/wolf-perf023-r01')
E=Path('/Agon/mystuff/agon-extender')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    grant=json.loads((G/'grant.json').read_text())
    context=json.loads((G/'context.json').read_text())
    assert grant['owner']=='wolf3dorig' and grant['generation']==97
    assert grant['request']=='098fa3fae20d' and grant['lease']=='4c9a75bf225b4eb9bd25dd130bb34c49'
    assert context['manifest']==str(B/'kit.json') and context['sole_operator_handoff']
    assert context['no_pending_extender_target_commands']
    assert sha(B/'kit.json')=='1b4d2dd929827cdf00f9fa7aef4b1da3ebbfc5b3e665642db263eb8ea900d143'
    failure=json.loads((B/'evidence/failure.json').read_text())
    donor=E/'agents/net004/uart1-bootstrap-r01/bootstrap.py'
    assert failure['error']==repr(KeyError(str(donor)))
    assert failure['custody_retained'] and failure['next_dispatch_stopped']
    assert not list((B/'evidence').glob('??-vdplet-*'))
    assert not list((B/'evidence').glob('probe-*'))
    assert not list((B/'evidence').glob('module-*'))
    assert not (B/'evidence/flash-b/clean-bootstrap').exists()
    actors=json.loads((B/'host-actors-terminal.json').read_text())
    assert actors['all_original_handles_terminal'] and actors['exact_processes_terminal']
    assert actors['controller_returncode']==1 and actors['observer_returncode']==0
    kit=json.loads((B/'kit.json').read_text())
    assert (B/'evidence/flash-b/read.bin').read_bytes()==Path(kit['install_b']).read_bytes()
    old=json.loads((T.parent/'WOLF-PERF-022/build/hardware02/kit.json').read_text())
    assert json.loads((T.parent/'WOLF-PERF-022/results/actual95/RESULT.json').read_text())['passed']
    additions={}
    for rel in ('agents/net004/uart1-bootstrap-r01/bootstrap.py','scripts/reset_agon_usb.py',
                'agents/bench-reset/usb-reset.local.json','scripts/reset_agon.py',
                'scripts/passive_serial.py','scripts/p4_boot_guard.py'):
        p=E/rel;digest=sha(p)
        assert digest==old['inputs'][str(p)],rel
        if str(p) not in kit['inputs']:additions[str(p)]=digest
        else:assert kit['inputs'][str(p)]==digest
    assert len(additions)==4 and additions[str(donor)]=='d04f18ee229b4eca6c7134f8ba1efaa91edc5aebccc6b183b6ab4656c526ea83'
    C.mkdir(exist_ok=False)
    kit['inputs'].update(additions)
    (C/'kit.json').write_text(json.dumps(kit,indent=2)+'\n')
    delta=dict(original_kit=str(B/'kit.json'),original_kit_sha256=sha(B/'kit.json'),
        cleanup_kit_sha256=sha(C/'kit.json'),added_inputs=additions,
        provenance='All additions independently match actual95 successful frozen pins and current files. Same unchanged commissioned bootstrap/reset source/config; cleanup-only, not a new benchmark selection.',
        existing_inputs_unmodified=True,only_missing_current_source_config_bindings_added=True)
    (C/'binding-delta.json').write_text(json.dumps(delta,indent=2)+'\n')
    copied=dict(context);copied['manifest']=str(C/'kit.json')
    copied['cleanup_only']=dict(original_context=str(G/'context.json'),
        original_context_sha256=sha(G/'context.json'),original_grant_sha256=sha(G/'grant.json'),
        original_failure=str(B/'evidence/failure.json'),original_failure_sha256=sha(B/'evidence/failure.json'),
        original_cohort_failed=True,no_guest_probe_module_LOAD_or_replay=True,
        no_guest_RAM_exists=True,no_pre_restore_reset=True,once=True)
    (C/'context.json').write_text(json.dumps(copied,indent=2)+'\n')
    spec=importlib.util.spec_from_file_location('wolf023_cleanup97_adapter',T/'hardware02.py')
    hw=importlib.util.module_from_spec(spec);spec.loader.exec_module(hw)
    # Ordinary constructor still verifies every original selected byte, exact
    # task/request/grant/current component and every real guest/size operand.
    hw.B=C;hw.h.B=C
    b=hw.Bench(C/'context.json');b.cleaning=True;b.deadline=time.monotonic()+900
    entry=b.out/'entry';entry.mkdir(exist_ok=False)
    for name,key in (('startup.bin','startup_sha256'),('listener.bin','listener_sha256')):
        p=B/'evidence/entry'/name;assert sha(p)==b.components[key]
        shutil.copyfile(p,entry/name)
    b.own();b.ports_free()
    hw.h.save(C/'scope.json',dict(epoch=time.time(),lease=b.lease,cleanup_only=True,
        original_failure_preserved=True,no_guest_or_timing_result=True,
        bootstrap_specific_attempts_before_cleanup=0,
        original_flash_esptool_after_hard_resets=2,
        no_pre_restore_reset=True,no_guest_probe_LOAD_or_replay=True,
        no_original_guest_RAM_claim=True,
        action='Exact incoming85f9 native/tail restore and full readback FIRST; ONE maintained current matched bootstrap and full fresh handback, then STOP/normal release'))
    try:
        b.flash('restore',b.kit['restore'])
        b.handback()
        hw.h.save(C/'complete.json',dict(passed=True,exact_incoming_restored=True,
            full_handback=True,original_suite_failed=True,room_records=0,
            owned_actors_stopped=True,epoch=time.time()))
        print('CLEANUP97 COMPLETE: exact incoming restoration/full handback; no guest or comparison',flush=True)
    except BaseException as error:
        hw.h.save(C/'failure.json',dict(error=repr(error),cleanup_leaf_stopped=True,
            custody_retained=True,no_retry=True,epoch=time.time()))
        raise


if __name__=='__main__':main()
