#!/usr/bin/env python3
"""Qualify and package the maintained optimized production renderer.

Run under the normal serial compiler checkout. The task wrapper supplies host
thermal/time/process guards. No firmware, emulator or device is launched here.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
BUILD = HERE / 'build'
TASKS = PROJECT / 'agonport/doc/tasks'
SDK = TASKS / 'WOLF-PERF-021/build/r01/candidate/sdk'
SDK_PYTHON = Path('/Agon/mystuff/agon-vdplet/.venv/bin/python')
TOOLCHAIN = Path('/home/smith/.platformio/packages/toolchain-xtensa-esp32/bin')
sys.path.insert(0, str(PROJECT / 'tools'))
from wolf_firmware import PRODUCTION_MODULE_SHA, module_info


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command):
    subprocess.run(list(map(str, command)), cwd=HERE, check=True, timeout=180)


def parse_stack(path):
    return {row[0].split(':', 3)[-1]: int(row[1])
            for line in path.read_text().splitlines()
            if len(row := line.rsplit('\t', 2)) == 3}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--discover-package', action='store_true',
                        help='Qualification only: record a new package before pinning the default')
    args = parser.parse_args()
    pins = json.loads((HERE / 'promotion.json').read_text())
    for path, digest in pins['sdk'].items():
        if sha(PROJECT / path) != digest:
            raise AssertionError('Qualified O2/PSRAM SDK input changed: ' + path)
    sources = {'renderer': HERE / 'wolf3d_renderer.cpp',
               'module_source': HERE / 'wolf3d_module.cpp',
               'raywalk': HERE / 'original_raywalk.h',
               'tangents': HERE / 'original_tangents.inc',
               'tables': HERE / 'wolf3d_tables.inc'}
    for name, path in sources.items():
        if sha(path) != pins[name + '_sha256']:
            raise AssertionError('Promotion unit changed without qualification: ' + name)
    BUILD.mkdir(exist_ok=True)
    run([sys.executable, HERE / 'contract.py', '--check'])
    flags = ['g++', '-std=c++17', '-O2', '-g1', '--param=ggc-min-expand=10', '--param=ggc-min-heapsize=8192', '-Wall', '-Wextra', '-Werror',
             '-pedantic', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
             '-fno-omit-frame-pointer']
    core = [HERE / 'wolf3d_world_mirror.cpp', HERE / 'wolf3d_renderer.cpp']
    def host(name, inputs, arguments=(), extra=()):
        executable = BUILD / name
        run([*flags, *extra, *inputs, '-o', executable])
        run([executable, *arguments])
    host('test_world_mirror', [HERE / 'wolf3d_world_mirror.cpp', HERE / 'test_world_mirror.cpp'])
    # The old DDA stays test-only. Its divider is now defined for negative a.
    host('test_fixed_div', [HERE / 'wolf3d_world_mirror.cpp', HERE / 'test_fixed_div.cpp'])
    for source in ('wolf3d_scene.cpp', 'wolf3d_scene_rows.cpp'):
        host(source + '-division', [HERE / 'test_fixed_div.cpp'], extra=[
            '-DWOLF3D_HOST_TEST', '-DWOLF_DIV_FUNCTION=fixed_div',
            '-DWOLF_DIV_SOURCE="../' + source + '"', '-I' + str(SDK / 'include')])
    host('legacy_renderer', [HERE / 'wolf3d_world_mirror.cpp',
                           HERE / 'reference/legacy_renderer.cpp', HERE / 'test_renderer.cpp'],
         [BUILD / 'legacy-frame.bin', BUILD / 'legacy-geometry.bin'])
    for actual, original in [('legacy-frame.bin', 'renderer-frame.bin'),
                             ('legacy-geometry.bin', 'renderer-geometry.bin')]:
        if sha(BUILD / actual) != pins['legacy_golden'][original]:
            raise AssertionError('Corrected legacy divider changed retained output: ' + actual)
    host('test_renderer', [*core, HERE / 'test_renderer.cpp'],
         [BUILD / 'fixture-frame.bin', BUILD / 'fixture-geometry.bin'])
    target_fixture = BUILD / 'target-fixture'
    if target_fixture.exists():
        shutil.rmtree(target_fixture)
    host('test_module', [HERE / 'wolf3d_module.cpp', HERE / 'test_module.cpp'],
         [BUILD / 'module-frame.bin', target_fixture],
         ['-DWOLF3D_HOST_TEST', '-I' + str(SDK / 'include'),
          '-I' + str(PROJECT / 'agonport/vdplet/qualification')])
    host('equivalence', [*core, TASKS / 'WOLF-PERF-007/test_equivalence.cpp'],
         [BUILD / 'frames600.bin', BUILD / 'states600.bin'], ['-I' + str(HERE)])
    host('spans', [HERE / 'wolf3d_world_mirror.cpp', TASKS / 'WOLF-PERF-007/test_spans.cpp'],
         [BUILD / 'spans.bin'], ['-I' + str(HERE)])
    for name, expected in pins['golden'].items():
        path = BUILD / name
        if path.stat().st_size != expected['bytes'] or sha(path) != expected['sha256']:
            raise AssertionError('Output differs from completed combined021: ' + name)
    host('original-raywalk', [TASKS / 'WOLF-PERF-007/test_original_raywalk.cpp'],
         extra=['-I' + str(HERE)])
    host('original-crossings', [TASKS / 'WOLF-PERF-007/test_crossing_order.cpp'],
         extra=['-I' + str(HERE)])
    # Test actual freestanding helper bodies, which HOST_TEST otherwise excludes.
    text = (HERE / 'wolf3d_module.cpp').read_text()
    body = text[text.index('union WideWords {'):text.index('\n#endif', text.index('union WideWords {'))]
    donor = (TASKS / 'WOLF-PERF-021/candidate_numeric.inc').read_text()
    renamed = body.replace('__udivdi3', 'candidate_udiv').replace('__divdi3', 'candidate_sdiv')
    if donor != 'namespace candidate {\n' + renamed + '\n}\n':
        raise AssertionError('Native divider differs from qualified exact-body test')
    host('numeric', [TASKS / 'WOLF-PERF-021/test_numeric.cpp'])
    module_dir = BUILD / 'module'
    module_dir.mkdir(exist_ok=True)
    run([SDK_PYTHON, SDK / 'tools/build_module.py', HERE / 'wolf3d_module.cpp',
         '--output', module_dir, '--compiler', TOOLCHAIN / 'xtensa-esp32-elf-gcc',
         '--name', 'wolf3d_production', '--capabilities', '257', '--abi-minor', '6',
         '--text-limit', '65536', '--data-limit', '16384', '--stack-limit', '2048',
         '--image-limit', '131072', '--build-id', '0x20261109'])
    manifest = json.loads((module_dir / 'wolf3d_production.json').read_text())
    package = manifest['module']
    if not args.discover_package and package['sha256'] != PRODUCTION_MODULE_SHA:
        raise AssertionError('Production package changed without selection update')
    image = module_dir / 'wolf3d_production.vdpl'
    admitted = module_info(image)
    if (admitted['abi_minor'], admitted['capabilities']) != (6, 257):
        raise AssertionError('Production ABI/capability changed')
    if not package['compiler_target']['psram_cache_workaround']:
        raise AssertionError('PSRAM workaround disabled')
    undefined = subprocess.check_output([str(TOOLCHAIN / 'xtensa-esp32-elf-nm'),
        '-u', str(module_dir / 'wolf3d_production.o')], text=True).strip()
    if undefined:
        raise AssertionError('Undefined native symbols: ' + undefined)
    disassembly = subprocess.check_output([str(TOOLCHAIN / 'xtensa-esp32-elf-objdump'),
        '-drC', str(module_dir / 'wolf3d_production.elf')], text=True)
    if 'quou' not in disassembly.lower():
        raise AssertionError('Native unsigned division missing')
    (module_dir / 'demangled-disassembly.txt').write_text(disassembly)
    stack = parse_stack(module_dir / 'wolf3d_production.su')
    def frame(fragment):
        found = [size for name, size in stack.items() if fragment in name]
        if len(found) != 1:
            raise AssertionError((fragment, found))
        return found[0]
    # Include the non-inlined optimized wall painter, unlike the old DDA sum.
    chains = {
        'entry/apply/validate': sum(frame(s) for s in ('vdplet_entry', 'apply_update_batch', 'validate_batch')),
        'entry/direct/compositor/walls/acquire': sum(frame(s) for s in
            ('vdplet_entry', 'render_world_direct', 'render_world_to_target', 'draw_walls', 'acquire_asset')),
        'entry/descriptor/copy': sum(frame(s) for s in ('vdplet_entry', 'require_matching_descriptor', 'copy_descriptor')),
        'entry/fizzle': frame('vdplet_entry') + frame('emit_fizzle'),
    }
    if max(chains.values()) > 2048:
        raise AssertionError('Module selected stack path exceeds 2048: ' + str(chains))
    receipt = dict(schema=3, passed=True, renderer_selection='combined021-production',
        donor_module_sha256=pins['donor_module_sha256'], package=package,
        output_sha256={n: sha(BUILD / n) for n in pins['golden']},
        package_component_sha256={n: sha(p) for n, p in sources.items()},
        sdk_inputs=pins['sdk'], native_undefined_symbols=undefined,
        source_stack_frames=stack, source_call_chain_sums=chains,
        largest_source_call_chain_sum=max(chains.values()),
        stack_limit_note='Selected module-owned paths; runtime/foreign callback/ISR peak still needs separate target evidence.',
        frame_geometry_state_bytes_identical_to_qualified_combined=True,
        signed_shift='Removed from active ray walk; corrected test-only legacy divider uses int64 multiplication',
        firmware_execution=False, diagnostic_entries=False)
    (BUILD / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    if not args.discover_package:
        shutil.copyfile(image, BUILD / 'wolf3d_production.vdpl')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
