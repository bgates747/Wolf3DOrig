"""Offline independent raw replay, producer/lifecycle/resource and cleanup join."""
from pathlib import Path
import argparse, importlib.util, json, statistics

T = Path(__file__).resolve().parent
B = T / 'build/hardware01'
SEQUENCE = [('original', 'room'), ('cyan', 'room'), ('combined', 'room'),
            ('combined', 'room'), ('cyan', 'room'), ('original', 'room')]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(release):
    decoder = load('p21_raw_decoder', T / 'analyze.py')
    for i, (_, scene) in enumerate(SEQUENCE, 1):
        # Recompute all600 native/pose/stage/angle checks from raw binary inputs.
        decoder.analyze(B / 'evidence' / f'{i:02d}-vdplet-{scene}')
    verifier = load('p21_independent_report', T.parent / 'WOLF-GOAL-001/report_h02.py')
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
    result['default_adopted'] = False
    (B / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(comparisons=result['comparisons'], combined_vs_cyan=result['combined_vs_cyan']), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', required=True, type=Path)
    main(parser.parse_args().release)
