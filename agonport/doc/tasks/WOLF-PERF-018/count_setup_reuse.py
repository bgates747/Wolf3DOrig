"""File-only eligible setup counts in the existing six-scenario parity fixture."""
from pathlib import Path
import hashlib
import json
import struct

T = Path(__file__).resolve().parent
B = T/'build/r01'

def main():
    original = B/'original/host-results/states600.bin'
    candidate = B/'candidate/host-results/states600.bin'
    raw = original.read_bytes()
    assert raw == candidate.read_bytes() and len(raw) == 600*1802
    total = reused = 0
    frames = []
    for frame in range(600):
        part = raw[frame*1802:(frame+1)*1802]
        heights = struct.unpack_from('<256i', part)
        tiles = part[1024:1280]
        last = {}
        columns = hits = 0
        # Both immutable fixture doors resolve to texture3 in all six scenes.
        # Each ID has an independent last-height cache and columns are ascending.
        for height, tile in zip(heights, tiles):
            if height <= 0:
                continue
            if 128 <= tile <= 191:
                assert tile-128 < 2
                tile = 3
            if not 1 <= tile <= 127:
                continue
            columns += 1
            if last.get(tile, 0) == height:
                hits += 1
            else:
                last[tile] = height
        total += columns
        reused += hits
        frames.append(dict(step=frame+1, columns=columns, eligible_reuses=hits))
    files = [original, candidate,
        B/'original/production/renderer_fixture.h',
        B/'original/production/test_renderer.cpp',
        B/'original/production/wolf3d_production_contract.h',
        T.parent/'WOLF-PERF-007/test_equivalence.cpp']
    result = dict(passed=True, frames=600, valid_columns=total,
        eligible_reuses=reused, remaining_setup_evaluations=total-reused,
        eligible_fraction=reused/total,
        minimum_reuses_per_frame=min(x['eligible_reuses'] for x in frames),
        maximum_reuses_per_frame=max(x['eligible_reuses'] for x in frames),
        scope='Existing six-scenario host parity fixture; not the physical E1L1 room, native branch counters, timing or observed target speed.',
        inputs={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        per_frame=frames)
    (B/'setup-opportunities.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('inputs','per_frame')}, indent=2))

if __name__ == '__main__':
    main()
