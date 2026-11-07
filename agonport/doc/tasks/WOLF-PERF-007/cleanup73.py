"""Bounded stopped-cohort preservation and exact restoration, never a replay."""
from pathlib import Path
import json,sys,time,shutil,hashlib
T=Path(__file__).resolve().parent;sys.path.insert(0,str(T))
import launch02
assert launch02.preflight()==json.loads((T/'LAUNCH-PREFLIGHT.json').read_text())
import hardware02 as m
B=T/'build/hardware02';E=B/'evidence';R=B/'cleanup73'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    b=m.Bench.__new__(m.Bench);b.c=json.loads((B/'context73.json').read_text());b.grant=json.loads((B/'grant73.json').read_text());b.grant=b.grant.get('active',b.grant)
    b.kit=json.loads((B/'kit.json').read_text());m.verify_kit(b.kit)
    assert b.grant['generation']==73 and b.grant['request']==b.kit['request'] and b.grant['owner']=='wolf3dorig'
    b.components=b.grant['entry_observation']['components'];assert b.components==b.kit['incoming_components']
    b.lease=b.grant['lease'];b.url=b.c['url'];b.port=b.c['native_port'];b.remote=b.kit['remote'];b.out=E;b.cleaning=True;b.deadline=time.monotonic();b.selected_module_sha256=b.kit['candidate_module_sha256']
    assert json.loads((E/'failure.json').read_text())['next_dispatch_stopped'] and not (E/'06-vdplet-unpaced').exists()
    assert b'WOLF-PERF-003 COMPLETE' in (E/'05-vdplet-unpaced/serial.bin').read_bytes()
    b.own();b.ports_free()
    journal=E/'05-vdplet-unpaced/after.bin-job.json';shutil.copyfile(journal,R/'original-after-job-preserved.json')
    m.h.save(R/'cleanup-selection.json',dict(scope='Exact identified terminalfailedGET retirement; one original timing/native/stack preservation; fresh SAVE-only RAM before any LOAD; exact incoming native restore/readback/current bootstrap/full handback. No failed after.bin retry/guest/probe/successorbaseline.',failed_job=3215372350,failed_boot=2910473983,source='wolf-perf007-failedget73-source-cleanup-return-one',epoch=time.time()))
    try:
        b.own();c=m.h.m.fast.Client(b.url,journal,timeout=45)
        try:
            job=c.state['job'];assert job['id']==3215372350 and job['boot']==2910473983 and job['operation']=='get' and job['remote']==b.remote+'/after.bin'
            current=c.status();m.h.save(R/'before-discard.json',current)
            assert current['id']==job['id'] and current['boot']==job['boot'] and current['phase']==5 and current['error']==3
            state=b.state();m.h.save(R/'before-discard-state.json',state)
            keyboard=state['keyboard'];assert keyboard['ready'] and keyboard['physical_neutral'] and not keyboard['held'] and not keyboard['pending']
            assert state['worker']['phase']==5 and state['worker']['id']==job['id'] and state['worker']['boot']==job['boot']
            assert state['sd']['online'] and not state['sd']['pending']
            # The generic idle predicate requires phase0; terminalphase5 is
            # instead explicitly bound above to this exact stopped failed job.
            b.own();c.release(discard=True);after=c.status();m.h.save(R/'after-discard.json',after)
            assert after['boot']==2910473983 and after['phase']==0
        finally:c.close()
        for name in ('timing.bin','native.bin','stack.bin'):b.transfer(R,'preserve-'+name,'get',b.remote+'/'+name,R/name)
        # A fresh SAVE-only file retains current resident RAM before any LOAD.
        size=max(Path(g['guest']).stat().st_size for modes in b.kit['guests'].values() for g in modes.values())
        script=R/'save-current-ram.txt';script.write_bytes(('SAVE '+b.remote+'/cleanup73-ram.bin &40000 &'+format(size,'X')+'\r\nEMOS sdserve --fast /\r\n').encode())
        b.upload(R,'ram-save-script',script,b.remote+'/cleanup73-save.txt');b.exit(R,'save-cli-exit');b.cli(R,'save-cli')
        b.line(R,'save-current-ram','EXEC '+b.remote+'/cleanup73-save.txt');b.wait_online(True)
        c=b.metadata(R,'ram-saved-stat')
        try:
            entries=list(c.entries(b.remote));matches=[x for x in entries if x[0].rsplit('/',1)[-1]=='cleanup73-ram.bin'];assert len(matches)==1 and matches[0][1]==size
            m.h.save(R/'ram-saved-metadata.json',dict(remote=b.remote+'/cleanup73-ram.bin',bytes=size,entries=entries,before_any_load=True,local_readback=False,original_after_bin_retained=True))
        finally:c.lock.close()
        b.exit(R,'preservation-exit');b.flash('restore',b.kit['restore']);b.handback()
        m.h.save(E/'stopped-restored.json',dict(restored=True,complete_cohort=False,fully_collected_cases=4,completed_candidate_repeat_saved=True,successor_baseline_dispatched=False,performance_claim='Partial evidence only; no full matched-cohort verdict.',epoch=time.time()))
        print('PASS original-output preservation/SAVE-only RAM/exact native restoration/readback/full handback; no replay',flush=True)
    except BaseException as error:
        m.h.save(R/'cleanup-failure.json',dict(error=repr(error),custody_retained=True,no_replay=True,epoch=time.time()));raise
if __name__=='__main__':main()
