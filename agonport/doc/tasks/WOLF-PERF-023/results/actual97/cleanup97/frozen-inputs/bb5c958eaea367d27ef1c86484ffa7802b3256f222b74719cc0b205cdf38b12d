"""Freeze exact prepared sources, native numeric provenance and actual oracles.

File-only; neither compilation nor physical access. Preserve any build attempt.
"""
from pathlib import Path
import hashlib
import json
import re

T = Path(__file__).resolve().parent
B = T / 'build/r01'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (B/'build-inputs.json').exists()
    old = json.loads((B/'inputs.json').read_text())
    for p, d in old['inputs'].items(): assert sha(p) == d, p
    prior = T.parent/'WOLF-PERF-021/build/r01'
    binding = json.loads((prior/'native-body-binding.json').read_text())
    assert binding['passed'] and binding['fallback_and_signed_wrapper_equal']
    files = {str(prior/'native-body-binding.json'): sha(prior/'native-body-binding.json')}
    numeric_units = {}
    for arm in ('original','candidate'):
        for folder in ('production','native-source'):
            source = B/arm/folder/'wolf3d_module.cpp'
            donor = prior/'candidate'/folder/'wolf3d_module.cpp'
            assert source.read_bytes() == donor.read_bytes()
            files[str(donor)] = sha(donor)
            text = source.read_text()
            body = text[text.index('union WideWords {'):text.index('\n#endif',text.index('union WideWords {'))]
            digest = hashlib.sha256(body.encode()).hexdigest()
            assert digest == binding['units']['candidate']['body_sha256']
            numeric_units[arm+'/'+folder] = dict(source=str(source),sha256=sha(source),body_sha256=digest)
    (B/'native-body-binding.json').write_text(json.dumps(dict(passed=True,
        units=numeric_units, fallback_and_signed_wrapper_equal=True,
        exact_full_modules_equal_to_qualified_combined=True,
        limits='Unchanged full native sources and retained qualified numeric body; no new Xtensa execution or independent full64-domain claim.'),indent=2)+'\n')
    renderer = (B/'candidate/native-source/wolf3d_renderer.cpp').read_text()
    matches = re.findall(r'if \((pixel_xor <= 3u .*?)\) \{',renderer,re.S)
    assert len(matches)==1
    expression = matches[0]
    assert expression.strip().endswith('count <= UINT32_MAX - mapped_x')
    template = (T/'test_guard_domain.cpp.in').read_text()
    assert template.count('@ACTUAL_PREDICATE@')==1
    (B/'guard-domain.cpp').write_text(template.replace('@ACTUAL_PREDICATE@',expression))
    for p in B.rglob('*'):
        if p.is_file(): files[str(p.resolve())]=sha(p)
    for p in T.iterdir():
        if p.is_file(): files[str(p.resolve())]=sha(p)
    for p in (T.parent/'WOLF-PERF-007/test_equivalence.cpp',
              T.parent/'WOLF-PERF-007/test_spans.cpp',
              T.parent/'WOLF-PERF-021/test_background_alias.cpp'):
        files[str(p)]=sha(p)
    (B/'build-inputs.json').write_text(json.dumps(dict(inputs=files,
        source_selection='Exact combined8d3d control plus only aligned byte span insertion',
        no_compiler_or_target_io=True),indent=2)+'\n')
    print(json.dumps(dict(passed=True,inputs=len(files),compiler_or_target=False)))


if __name__ == '__main__': main()
