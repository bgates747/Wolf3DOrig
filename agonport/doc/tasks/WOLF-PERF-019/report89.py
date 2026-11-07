"""Offline original startup failure plus exact cleanup/release, no timing claim."""
from pathlib import Path
import datetime,hashlib,json
T=Path(__file__).resolve().parent;B=T/'build/hardware01';C=B/'cleanup89'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def main():
    k=read(B/'kit.json');snap=read(B/'frozen-inputs/index.json')
    for name,digest in k['inputs'].items():assert snap[name]['sha256']==digest and sha(snap[name]['snapshot'])==digest,name
    failure=read(B/'evidence/failure.json')
    assert failure['error']=="RuntimeError('Agon admission failed; no retry/RUN')"and failure['next_dispatch_stopped']and failure['custody_retained']
    assert not list((B/'evidence').glob('??-vdplet-*'))and not list((B/'evidence').glob('module-*'))and not list((B/'evidence').glob('probe-*'))
    assert not (B/'evidence/complete.json').exists()
    assert (B/'evidence/flash-b/read.bin').read_bytes()==Path(k['install_b']).read_bytes()
    original=read(T/'results/actual89/context.json');cleanup=read(C/'context.json')
    assert cleanup['manifest']==str(C/'kit.json')and sha(C/'kit.json')==sha(B/'kit.json')
    assert {a:b for a,b in cleanup.items()if a not in ('manifest','cleanup_only')}=={a:b for a,b in original.items()if a!='manifest'}
    assert cleanup['cleanup_only']['original_failure_sha256']==sha(B/'evidence/failure.json')
    assert read(C/'complete.json')['passed']and read(C/'complete.json')['room_records']==0
    assert (C/'evidence/flash-restore/read.bin').read_bytes()==Path(k['restore']).read_bytes()
    assert read(C/'evidence/flash-restore/receipt.json')['passed']
    final=read(C/'evidence/final-checks/observation.json');release=read(B/'release89.json')
    assert all(final['checks'].values())and final['components']==k['incoming_components']
    assert release['released']and release['generation']==89 and release['request']==k['request']and release['release_observation']==final
    assert 0<=datetime.datetime.fromisoformat(release['released']).timestamp()-final['epoch']<120
    for source in (B/'evidence/flash-b/clean-bootstrap',C/'evidence/flash-restore/clean-bootstrap'):
        assert (source/'p4-reset-issued.json').exists()and (source/'agon-reset-issued.json').exists()
    assert not (B/'evidence/flash-b/clean-bootstrap/receipt.json').exists()
    assert (C/'evidence/flash-restore/clean-bootstrap/receipt.json').exists()
    result=dict(benchmark_passed=False,original_suite_stopped=True,frames=0,room_guests=0,resource_probes=0,
        cause='Agon boot/input admission deadline after exact timed-native installation and current matched P4 initialization; reason0/readyfalse does not establish a root cause',
        original_error=failure,original_install_full_readback_verified=True,original_failure_RAM_preserved=False,
        RAM_limit='No guest was loaded; original remote input unready. No original SAVE/CLI or guest RAM receipt is invented. Cleanup raw state is post-restoration/post-bootstrap.',
        cleanup_passed=True,restore_bytes=Path(k['restore']).stat().st_size,restore_sha256=sha(C/'evidence/flash-restore/read.bin'),
        cleanup_context_byte_identical_kit=True,cleanup_did_not_invoke_suite=True,
        reset_ledger=dict(original_timed_image=dict(p4_init_resets=1,agon_resets=1,admission=False),cleanup_incoming_image=dict(p4_init_resets=1,agon_resets=1,admission=True),additional_recovery_attempts=0),
        bench_released=True,release=release['released'],fresh_release_seconds=datetime.datetime.fromisoformat(release['released']).timestamp()-final['epoch'],
        original_selected_inputs=len(k['inputs']),source_and_qualified_modules_retained=True,
        performance_claim=False,independent_chains_trig_timing_still_unmeasured=True)
    (B/'RESULT89.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
