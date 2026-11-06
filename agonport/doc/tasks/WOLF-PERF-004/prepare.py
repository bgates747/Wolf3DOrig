"""Prepare fresh task-owned sources only. Never compiles or accesses a device."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import shutil

T = Path(__file__).resolve().parent
ROOT = T.parents[3]
P3 = T.parent / 'WOLF-PERF-003'
B = T / 'build/r01'
FROZEN = P3 / 'build/r04/vdplet/native-source'
PROD = ROOT / 'agonport/vdplet/production'
SDK = P3 / 'build/r04/inputs/sdk'
ORIGINAL_RENDERER = 'aee6ed184b0d29e090b2f869559110d1c13fa801b735b1cbd5f36f53e43a3107'
OLD = 'for (uint32_t y = 0; y < W3P_SCREEN_HEIGHT; ++y)\n        fill_span(frame, 0, y, W3P_SCREEN_WIDTH, kDarkGray);'
NEW = 'for (uint32_t y = kPlayHeight; y < W3P_SCREEN_HEIGHT; ++y)\n        fill_span(frame, 0, y, W3P_SCREEN_WIDTH, kDarkGray);'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(revision, defined_scaling):
    global B
    assert revision == 'r03' and defined_scaling, 'Use the identified include-path-corrected revision'
    B = T / 'build' / revision
    assert not B.exists(), 'Fresh revision required; preserve previous output'
    assert sha(FROZEN / 'wolf3d_renderer.cpp') == ORIGINAL_RENDERER
    assert (FROZEN / 'wolf3d_renderer.cpp').read_bytes() == (PROD / 'wolf3d_renderer.cpp').read_bytes()
    B.mkdir(parents=True)
    pins = {}
    for arm in ('original', 'candidate'):
        a = B / arm
        shutil.copytree(FROZEN, a / 'native-source')
        shutil.copytree(PROD, a / 'production', ignore=shutil.ignore_patterns('build', '__pycache__'))
        (a / 'qualification').mkdir()
        shutil.copyfile(ROOT / 'agonport/vdplet/qualification/vdplet_host_shim.h', a / 'qualification/vdplet_host_shim.h')
        shutil.copyfile(P3 / 'build/r04/vdplet/wolf3d_tables.inc', a / 'wolf3d_tables.inc')
        if defined_scaling:
            for directory in ('native-source', 'production'):
                p = a / directory / 'wolf3d_renderer.cpp'
                raw = p.read_text()
                old_scale = '(static_cast<int64_t>(a) << 16) / b'
                assert raw.count(old_scale) == 1
                changed = raw.replace(old_scale, '(static_cast<int64_t>(a) * 65536) / b', 1)
                p.write_text(changed)
                (B / (arm + '-' + directory + '-scaling.patch')).write_text(''.join(difflib.unified_diff(
                    raw.splitlines(True), changed.splitlines(True),
                    fromfile='historical/' + directory, tofile=arm + '/' + directory)))
        if arm == 'candidate':
            for directory in ('native-source', 'production'):
                p = a / directory / 'wolf3d_renderer.cpp'
                original = p.read_text()
                assert original.count(OLD) == 1
                changed = original.replace(OLD, NEW, 1)
                p.write_text(changed)
                (B / (directory + '-candidate.patch')).write_text(''.join(difflib.unified_diff(
                    original.splitlines(True), changed.splitlines(True),
                    fromfile='original/' + directory, tofile='candidate/' + directory)))
        assert (a / 'native-source/wolf3d_renderer.cpp').read_bytes() == (a / 'production/wolf3d_renderer.cpp').read_bytes()
    # The build uses only the immutable SDK; record every file it can import.
    for p in sorted(SDK.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            pins[str(p)] = sha(p)
    for p in sorted(B.rglob('*')):
        if p.is_file():
            pins[str(p)] = sha(p)
    for p in (T / 'prepare.py', T / 'test_equivalence.cpp', T / 'test_fixed_div.cpp', T / 'build.py'):
        pins[str(p)] = sha(p)
    (B / 'inputs.json').write_text(json.dumps(dict(
        task='WOLF-PERF-004', plan_freeze='b9a7062', inputs=pins,
        amendment_freeze='aa0e77f',
        scope='Common defined-scaling prerequisite; candidate clear extent only; host module excludes target helper/observer blocks'), indent=2) + '\n')
    print('Prepared original/candidate sources; one clear-loop lower bound differs; all build inputs pinned.')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--revision', required=True)
    p.add_argument('--defined-scaling', action='store_true')
    args = p.parse_args()
    main(args.revision, args.defined_scaling)
