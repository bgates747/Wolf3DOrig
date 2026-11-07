"""One cleanup-only continuation of interrupted generation84; never dispatch a guest."""
from pathlib import Path
import json
import os
import shutil
import time
import hardware02 as hw

CONTEXT = Path('/Agon/mystuff/agon-extender/agents/bench-scheduler/wolf-goal001-h02/context.json')

def main():
    b = object.__new__(hw.Bench)
    b.c = json.loads(CONTEXT.read_text())
    b.grant = json.loads(Path(b.c['grant']).read_text())
    b.grant = b.grant.get('active', b.grant)
    b.kit = json.loads((hw.B/'kit.json').read_text())
    hw.verify_kit(b.kit)
    assert b.grant['generation'] == 84 and b.grant['request'] == hw.REQUEST
    assert b.grant['owner'] == 'wolf3dorig'
    b.lease = b.grant['lease']
    assert b.lease == '1f5f3fa5d76b4288ad27e4d7ed877fed'
    b.components = b.grant['entry_observation']['components']
    assert b.components == b.kit['incoming_components']
    b.url, b.port, b.remote = b.c['url'], b.c['native_port'], b.kit['remote']
    b.out = hw.B/'evidence'
    b.cleaning = True
    b.selected_module_sha256 = b.kit['original_module_sha256']
    p = b.folder('cleanup84')
    hw.h.save(p/'host-start.json', dict(pid=os.getpid(), parent=os.getppid(), epoch=time.time(),
        cleanup_only=True, source_sha256=hw.sha(__file__), no_guest_dispatch=True))
    print('CLEANUP PID', os.getpid(), 'EVIDENCE', p, flush=True)
    b.own(); b.ports_free()
    original = b.out/'01-vdplet-room/cd-keys.json'
    shutil.copyfile(original, p/'original-cd-keys.json')
    shutil.copyfile(b.out/'01-vdplet-room/serial.bin', p/'original-serial.bin')
    journal = json.loads(original.read_text())
    assert journal['pending'] is None and journal['active']
    expected_session = (1264934178, 382700053, 5)
    assert (journal['boot'], journal['session'], journal['sequence']) == expected_session
    c = hw.h.m.Keys(b.url, original)
    try:
        status = c.status()
        hw.h.save(p/'original-status.json', status)
        assert (status['boot'], status['session'], status['sequence']) == expected_session
        assert status['ready'] and status['physical_neutral'] and not status['held'] and not status['pending']
        hw.h.save(p/'cancel-issued.json', dict(epoch=time.time(), operation=3, once=True))
        result = c.cancel()
        hw.h.save(p/'cancel-result.json', result)
        assert not result['held'] and not result['pending']
    finally:
        c.lock.close()
    raw = bytearray()
    with hw.h.m.open_passive_serial(b.port, baudrate=115200, timeout=.2) as serial:
        c = hw.h.m.Keys(b.url, p/'escape-keys.json')
        try:
            status = c.status()
            hw.h.save(p/'escape-status.json', status)
            assert status['boot'] == journal['boot']
            assert status['ready'] and status['physical_neutral'] and not status['held'] and not status['pending']
            c.open(status)
            hw.h.save(p/'escape-issued.json', dict(epoch=time.time(), events=[[41,1],[41,0]], no_enter=True, once=True))
            hw.h.save(p/'escape-result.json', c.send([(41,1),(41,0)]))
            c.cancel()
        finally:
            c.lock.close()
        b.capture(serial, raw, p, lambda data: b'Escape' in data and b' *' in data, 20)
    hw.h.save(p/'escape-prompt.json', dict(passed=True, command_not_executed=True))
    b.cli(p, 'cleanup84-cli')
    b.service(p, 'cleanup84-listener')
    script = p/'save84.txt'
    script.write_bytes(('SAVE '+b.remote+'/stop84-ram.bin &40000 &10000\r\n'
                       'EMOS sdserve --fast /\r\n').encode())
    b.upload(p, 'save-script', script, b.remote+'/save84.txt')
    b.exit(p, 'save-exit')
    b.line(p, 'save-current-ram', 'EXEC '+b.remote+'/save84.txt')
    b.wait_online(True)
    b.transfer(p, 'ram', 'get', b.remote+'/stop84-ram.bin', p/'ram.bin')
    assert (p/'ram.bin').stat().st_size == 65536
    hw.h.save(p/'ram-preserved.json', dict(passed=True, bytes=65536, sha256=hw.sha(p/'ram.bin'),
        address=0x40000, before_any_cleanup_load_or_reset=True, no_room_guest_dispatched=True))
    b.exit(p, 'restore-offline')
    print('CURRENT RAM PRESERVED; RESTORING EXACT INCOMING SPAN', flush=True)
    b.flash('restore', b.kit['restore'])
    b.handback()
    hw.h.save(p/'complete.json', dict(passed=True, restored=True, no_guest_dispatch=True,
        original_failure_preserved=True, epoch=time.time()))
    print('CLEANUP COMPLETE; READY FOR NORMAL RELEASE', flush=True)

if __name__ == '__main__':
    main()
