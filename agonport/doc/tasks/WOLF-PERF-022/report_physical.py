"""Offline independent raw replay, producer/lifecycle/resource and cleanup join."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, statistics

T = Path(__file__).resolve().parent
B = T / 'build/hardware02'
SEQUENCE = [('original', 'room'), ('cyan', 'room'), ('combined', 'room'),
            ('combined', 'room'), ('cyan', 'room'), ('original', 'room')]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observer_join(release):
    """Offline receipt join only; never attach, poll or signal another process."""
    folder = B / 'observer'
    read = lambda p: json.loads(Path(p).read_text())
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    session = read(folder / 'session.json')
    ack = read(folder / 'attached.json')
    outcome = read(folder / 'observer-result.json')
    launch = read(B / 'host-interruption/host-launch.json')
    actors = read(B / 'host-actors-terminal.json')
    released = read(release)
    assert released['released'] and released['lease'] == session['lease']
    assert digest(B / 'kit.json') == session['kit_sha256']
    assert ack['session_sha256'] == digest(folder / 'session.json')
    assert ack['nonce'] == session['nonce']
    controller = session['controller']
    assert launch['pid'] == controller['pid'] and launch['ppid'] == controller['ppid']
    assert not launch['target_action'] and not launch['detached']
    assert ack['observer']['ppid'] == controller['ppid']
    assert ack['tracer']['ppid'] == ack['observer']['pid']
    assert ack['tracer']['pgid'] == ack['tracer']['pid'] != controller['pgid']
    assert outcome['controller'] == controller and outcome['observer'] == ack['observer']
    assert outcome['passed'] and outcome['owned_tracer_joined']
    assert outcome['tracer_returncode'] == 0 and not outcome['controller_signalled_by_observer']
    assert not (B / 'host-interruption/host-interruption.json').exists()
    assert '--- SIGTERM ' not in (folder / 'signal.trace').read_text()
    assert actors['controller'] == controller and actors['observer'] == ack['observer']
    assert actors['tracer'] == ack['tracer'] and actors['all_original_handles_terminal']
    assert actors['controller_returncode'] == actors['observer_returncode'] == 0
    assert actors['exact_processes_terminal'] and actors['epoch'] >= ack['epoch']
    return dict(exact_kit_and_lease=True, positive_handshake=True,
                controller_identity=controller, observer_identity=ack['observer'],
                tracer_identity=ack['tracer'], original_foreground_handles=actors['handles'],
                original_handles_terminal=True, owned_tracer_joined=True,
                SIGTERM_observed=False, simultaneous_cancellation_qualified=False,
                trace_sha256=digest(folder / 'signal.trace'),
                limits='Prospective exact-controller host diagnostic; historical interruptions remain unexplained. Same observer for every arm; host setup/collection can be perturbed, not an exclusive CPU/optical profile.')


def main(release):
    decoder = load('p22_raw_decoder', T / 'analyze.py')
    for i, (_, scene) in enumerate(SEQUENCE, 1):
        # Recompute all600 native/pose/stage/angle checks from raw binary inputs.
        decoder.analyze(B / 'evidence' / f'{i:02d}-vdplet-{scene}')
    verifier = load('p22_independent_report', T.parent / 'WOLF-GOAL-001/report_h02.py')
    result = verifier.report(T, B, release, SEQUENCE)
    cases = result['cases']
    cyan = [c for c in cases if c['arm'] == 'cyan']
    combined = [c for c in cases if c['arm'] == 'combined']
    assert len(cyan) == len(combined) == 2
    a = statistics.mean(c['render_cycles_mean'] for c in cyan)
    b = statistics.mean(c['render_cycles_mean'] for c in combined)
    fa = sum(c['frames'] for c in cyan) / sum(c['seconds_nominal'] for c in cyan)
    fb = sum(c['frames'] for c in combined) / sum(c['seconds_nominal'] for c in combined)
    result['combined_vs_cyan'] = dict(cyan_runs=[c['index'] for c in cyan],
        combined_runs=[c['index'] for c in combined],
        cyan_render_ms_at_configured240MHz=a / 240000,
        combined_render_ms_at_configured240MHz=b / 240000,
        draw_reduction_percent=(1 - b / a) * 100,
        cyan_presented_fps=fa, combined_presented_fps=fb,
        presented_fps_change_percent=(fb / fa - 1) * 100,
        scope='Two runs per arm in one symmetric six-case comparison. Shared original controls expose drift; no individual contribution or causal additive timing attribution.')
    result['qualification'] += ' Five supported local units combined. Independent019 chain/trig timing remains unmeasured after its failed pre-guest startup; this new comparison does not replace those individual measurements.'
    result['host_observer'] = observer_join(release)
    result['default_adopted'] = False
    (B / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(comparisons=result['comparisons'], combined_vs_cyan=result['combined_vs_cyan']), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', required=True, type=Path)
    main(parser.parse_args().release)
