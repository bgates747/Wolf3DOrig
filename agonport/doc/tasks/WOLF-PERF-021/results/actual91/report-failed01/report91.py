"""Preserve interrupted cohort and independently validate recovered original SD."""
from pathlib import Path
import datetime, importlib.util, json, re

T = Path(__file__).resolve().parent
B = T / 'build/hardware01'
C = B / 'restore91'
read = lambda p: json.loads(Path(p).read_text())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    binding = load('p21_recovered_binding', T / 'guest_binding.py')
    sha = binding.sha
    kit = read(B / 'kit.json')
    snapshots = read(B / 'frozen-inputs/index.json')
    for name, digest in kit['inputs'].items():
        assert snapshots[name]['sha256'] == digest and sha(snapshots[name]['snapshot']) == digest
    failure = read(B / 'evidence/failure.json')
    signal = read(B / 'host-interruption/host-interruption.json')
    launch = read(B / 'host-interruption/host-launch.json')
    assert failure['error'] == 'HostInterrupted(15)' and signal['signal'] == 15
    assert signal['pid'] == launch['pid'] == 1425962
    assert not (B / 'evidence/complete.json').exists()
    assert not list((B / 'evidence').glob('02-vdplet-*'))
    assert not list((B / 'evidence').glob('module-02-*'))
    assert not (B / 'evidence/01-vdplet-room/receipt.json').exists()
    assert read(B / 'evidence/entry/receipt.json')['fresh_namespace']
    selected = read(B / 'evidence/module-01-original/receipt.json')
    assert selected['passed'] and selected['sha256'] == kit['original_module_sha256']
    assert (B / 'evidence/flash-b/read.bin').read_bytes() == Path(kit['install_b']).read_bytes()
    assert read(B / 'evidence/flash-b/clean-bootstrap/receipt.json')['keyboard']['ready']
    probe = read(B / 'evidence/probe-entry/receipt.json')
    assert probe['passed'] and probe['minimum_stack_bytes'] == 2728
    observed = read(B / 'cleanup91/evidence/original-observation/receipt.json')
    assert observed['passive_only'] and not observed['returned_prompt']
    scope = read(C / 'evidence/recovery/scope.json')
    assert not scope['original_guest_RAM']['live_preserved']
    assert scope['original_guest_RAM']['bytes'] == 325309
    assert read(C / 'evidence/recovery/actual-cli.json')['post_reset']
    capture = read(C / 'evidence/recovery/original-sd-capture.json')
    assert capture['namespace_cleared_before_original_RUN'] and capture['no_new_guest_since_original_RUN']
    assert not capture['original_live_RAM_preserved']
    R = B / 'recovered-control91'
    for name, record in capture['files'].items():
        assert not record.get('absent', False)
        assert sha(R / name) == record['sha256'] == sha(C / 'evidence/recovery' / name)
    guest = kit['guests']['original']['room']
    actual = binding.verify(guest)
    listing = Path(guest['listing']).read_text()
    binary = Path(guest['guest']).read_bytes()
    address = lambda name: int(re.search(r'^([0-9A-F]{6})[^\n]*\b' + name + r':', listing, re.M)[1], 16)
    dump_bytes = address('wp_result_end') - 0x40000
    assert dump_bytes == 305873
    calls = read(B / 'guest-qualification.json')['arms']['original']['presentation_calls']
    for name in ('before.bin', 'after.bin'):
        ram = (R / name).read_bytes()
        assert len(ram) == dump_bytes
        for operand in actual['operands'] + calls:
            at = operand['address'] - 0x40000
            assert ram[at:at + 4] == binary[at:at + 4] == bytes.fromhex(operand['encoded'])
    ram = (R / 'after.bin').read_bytes()
    stack = [int.from_bytes(ram[address(n) - 0x40000:address(n) - 0x40000 + 3], 'little') for n in ('wp_entry_sp', 'wp_exit_sp')]
    assert stack[0] == stack[1] and 0xb0000 <= stack[0] < 0xc0000
    decoder = load('p21_recovered_raw', T / 'analyze.py')
    original = decoder.analyze(R)
    assert original['mode'] == 'uncapped-visible' and original['completed_records'] == 600
    hardware = load('p21_recovered_loading', T / 'hardware02.py')
    loading = hardware.h.decode_loading((R / 'loading.bin').read_bytes())
    trace = hardware.h.decode_trace((R / 'loading3.bin').read_bytes())
    assert loading['error'] == loading['agnb_error'] == 0 and loading['total'] == 470
    assert trace['main_returned'] and trace['loading_ready'] and not trace['loading_error'] and not trace['frozen']
    complete = read(C / 'complete.json')
    assert complete['passed'] and complete['ordinary_recovery_attempts'] == 1 and complete['paired_recovery_attempts'] == 0
    assert (C / 'evidence/flash-restore/read.bin').read_bytes() == Path(kit['restore']).read_bytes()
    final = read(C / 'evidence/final-checks/observation.json')
    release = read(B / 'release91.json')
    assert all(final['checks'].values()) and final['components'] == kit['incoming_components']
    assert release['generation'] == 91 and release['released'] and release['release_observation'] == final
    age = datetime.datetime.fromisoformat(release['released']).timestamp() - final['epoch']
    assert 0 <= age < 120
    result = dict(benchmark_comparison_passed=False, original_driver_stopped=True,
        original_driver_pid=signal['pid'], host_signal=15, signal_sender_and_cause='UNKNOWN',
        signal_after_launch_seconds=signal['epoch'] - launch['epoch'],
        signal_after_RUN_seconds=signal['epoch'] - scope['original_run']['epoch'],
        candidate_runs=0, complete_room_receipts=0, resource_queries=1,
        original_live_RAM_preserved=False, original_guest_file_bytes=len(binary),
        recovered_original_guest_SD_dump_bytes=dump_bytes, producer=actual,
        balanced_original_guest_stack=stack, original_presentation_calls=calls,
        recovered_original_SD_validated=True, original_frames_in_SD=600,
        original_render_ms_at_configured240MHz=original['native_ccount']['render_ccount']['mean'] / 240000,
        original_nominal_completed_fps=original['nominal_prt_records_per_second'],
        original_loading=loading, original_trace=trace,
        recovery=dict(ordinary_agon_attempts=1, paired_fallback_attempts=0,
            actual_CLI_proved_after_reset=True, original_SD_collected_after_reset=True,
            no_new_guest_LOAD_RUN_getter_or_probe=True),
        incoming_restored_and_readback=True, restore_bytes=1105920,
        restore_sha256=sha(C / 'evidence/flash-restore/read.bin'),
        full_handback_passed=True, bench_released=release['released'], release_observation_age_seconds=age,
        selected_inputs=len(kit['inputs']),
        limits='Existing cleared-namespace original SD records validate one600-pose control after collection following recovery; no original pre-reset CLI/liveRAM or after-control resource state was observed. No candidate ran, no matched speedup/regression or optical/exclusiveCPU claim, no default adoption. Full selected cohort remains interrupted.')
    (B / 'RESULT91.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('benchmark_comparison_passed', 'original_frames_in_SD', 'candidate_runs', 'original_render_ms_at_configured240MHz', 'original_nominal_completed_fps', 'bench_released')}, indent=2))


if __name__ == '__main__':
    main()
