"""Cleanup only after the human-visible test discrepancy; never resume cases."""
from pathlib import Path
import json,sys,time
T=Path(__file__).resolve().parent;sys.path.insert(0,str(T))
import hardware02 as m,launch02
B=T/'build/hardware01';E=B/'evidence';R=B/'cleanup75'
def main():
    assert launch02.preflight()==json.loads((T/'LAUNCH-PREFLIGHT.json').read_text())
    c=json.loads(Path('/Agon/mystuff/agon-extender/agents/bench-scheduler/wolf-perf009-r01/context.json').read_text())
    g=json.loads(Path(c['grant']).read_text());g=g.get('active',g)
    b=m.Bench.__new__(m.Bench);b.c=c;b.grant=g;b.kit=json.loads((B/'kit.json').read_text());m.verify_kit(b.kit)
    assert g['generation']==75 and g['request']==b.kit['request'] and g['owner']=='wolf3dorig'
    b.components=g['entry_observation']['components'];assert b.components==b.kit['incoming_components']
    b.lease=g['lease'];b.url=c['url'];b.port=c['native_port'];b.remote=b.kit['remote'];b.out=E;b.cleaning=True;b.deadline=time.monotonic();b.selected_module_sha256=b.kit['original_module_sha256']
    assert json.loads((E/'failure.json').read_text())['error']=='HostInterrupted(15)'
    assert json.loads((B/'visual-stop.json').read_text())['owned_driver_pid']==1213755
    assert json.loads((E/'05-vdplet-unpaced/receipt.json').read_text())['passed']
    assert not (E/'06-vdplet-unpaced/load-issued.json').exists() and not (E/'06-vdplet-unpaced/run-issued.json').exists()
    R.mkdir(exist_ok=False)
    m.h.save(R/'selection.json',dict(epoch=time.time(),scope='Cleanup-only exact incoming native/tail restoration/readback, one matched current bootstrap and full handback. No successor guest/probe/replay.',stop='Human saw stationary VGA during announced rotation. Source proves unpaced hidden writes with final-only presentation; original comparison/visual claims withdrawn.',partial_line='Final baseline stopped while typing VDU marker, before ENTER/LOAD/RUN. Preserve journal; no attempt to finish or replay line.',preservation='Original completed cases03/04/05 raw RAM/timing/native/stack are already local. Resource probe after05 subsequently overwrote resident guest header; no pristine guest-RAM claim or collector LOAD.'))
    b.own();b.ports_free();state=b.state();m.h.save(R/'pre-restore-state.json',state)
    k=state['keyboard'];assert k['ready'] and k['physical_neutral'] and not k['held'] and not k['pending']
    assert not state['sd']['online'] and not state['sd']['pending'] and state['worker']['phase']==0
    try:
        b.flash('restore',b.kit['restore']);b.handback()
        m.h.save(E/'stopped-restored.json',dict(restored=True,complete_cohort=False,visible_rotation_qualified=False,fully_collected_cases=5,final_baseline_load_or_run=False,epoch=time.time()))
        m.h.save(E/'restored-idle.json',dict(restored=True,target_actors_stopped=True,lease=b.lease,epoch=time.time(),reason='All cleanup children joined; cleanup driver will exit before normal release. No new target action.'))
        print('PASS exact incoming restoration/readback/current bootstrap/full cleanup; stopped visual claim not replayed',flush=True)
    except BaseException as error:
        m.h.save(R/'failure.json',dict(error=repr(error),custody_retained=True,no_replay=True,epoch=time.time()));raise
if __name__=='__main__':main()
