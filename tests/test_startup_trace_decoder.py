from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "src/asm/wolf3d/scripts/decode_startup_trace.py"
)
SPEC = spec_from_file_location("decode_startup_trace", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
DECODER = module_from_spec(SPEC)
SPEC.loader.exec_module(DECODER)


def test_decodes_only_reserved_startup_families():
    lines = [
        "noise",
        "vdu_sys_buffered: buffer 53280, 0 streams stored",
        "vdu_sys_buffered: buffer 53528, 0 streams stored",
        "vdu_sys_buffered: buffer 42, 1 streams stored",
    ]
    assert DECODER.decode(lines, {24: "ATKPISTOL"}) == [
        "     2  D020  SFX asset load beginning",
        "     3  D118  SFX 24 ATKPISTOL",
    ]


def test_sound_names_follow_generated_asset_contract():
    source = SCRIPT.parents[1] / "src/wolf3d_audio_assets.inc"
    names = DECODER.parse_sound_names(source)
    assert names[0] == "HITWALL"
    assert names[24] == "ATKPISTOL"
    assert names[68] == "DOGATTACK"
