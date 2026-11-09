"""Real-release/package refusal checks; never execute an emulator or firmware."""
import ast
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import wolf_firmware as fw
import wolf_prepare as prep


@pytest.fixture
def payload(tmp_path):
    receipt = ROOT/'src/asm/wolf3d/tgt/pinned/wolf3d-vdplet-direct.json'
    assert receipt.is_file(), 'Assemble the current real client before these checks'
    output = tmp_path/'payload'
    prep.package(receipt,output)
    return output


def test_actual_release_zip_member_and_all_vdp_assets_are_verified():
    r=fw.release_files()
    assert len(r['mos']) == 100879
    assert r['identity']['mos_sha256'] == fw.MOS_SHA
    assert r['identity']['vdp_sha256'] == fw.VDP_SHA


def test_changed_checksum_manifest_refuses_before_any_output(tmp_path):
    (tmp_path/'vdplet').mkdir()
    (tmp_path/'vdplet/SHA256SUMS').write_text('wrong')
    with pytest.raises(ValueError,match='SHA256SUMS'):
        fw.release_files(tmp_path)


@pytest.mark.parametrize('offset,value', [(8,1),(20,512),(28,16385),(32,2049)])
def test_incompatible_module_header_refused(tmp_path,offset,value):
    raw=bytearray(fw.DEFAULT_MODULE.read_bytes())
    struct.pack_into('<I',raw,offset,value)
    p=tmp_path/'bad.vdpl';p.write_bytes(raw)
    with pytest.raises(ValueError):fw.module_info(p)


def test_new_unsupported_allocated_section_is_refused(tmp_path):
    raw=fw.DEFAULT_MODULE.read_bytes().replace(b'.text\0',b'.evil\0')
    assert raw!=fw.DEFAULT_MODULE.read_bytes()
    p=tmp_path/'bad-section.vdpl';p.write_bytes(raw)
    with pytest.raises(ValueError,match='allocated module section'):
        fw.module_info(p)


def test_complete_payload_contains_matching_module_and_all_ten_levels(payload):
    m=fw.verify_payload(payload)
    assert m['module']['sha256'] == fw.PRODUCTION_MODULE_SHA
    assert {'wolf3d.bin','wolf3d.vdpl','shell.agnb','help.agnb','end.agnb'} <= set(m['files'])
    for i in range(10):
        assert f'level_{i:02d}/state_hard.w3l' in m['files']


@pytest.mark.parametrize('name', ['wolf3d.bin','wolf3d.vdpl','level_00/tiles.agnb'])
def test_changed_or_missing_payload_is_never_deployed(payload,name):
    (payload/name).unlink()
    with pytest.raises(ValueError,match='Missing'):
        fw.verify_payload(payload)


def test_module_hash_mismatch_receipt_refused_without_creating_output(tmp_path):
    p=ROOT/'src/asm/wolf3d/tgt/pinned/wolf3d-vdplet-direct.json'
    m=json.loads(p.read_text());m['module']['sha256']='0'*64
    bad=tmp_path/'bad.json';bad.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='module mismatch'):
        prep.package(bad,tmp_path/'output')
    assert not (tmp_path/'output').exists()


def test_real_payload_profile_preparation_cannot_start_the_application(payload,tmp_path):
    executable=tmp_path/'frontend';executable.write_text('#!/bin/sh\necho BAD > executed\n');executable.chmod(0o755)
    backend=tmp_path/'backend.so';backend.write_bytes(b'local test sentinel')
    output=tmp_path/'profile'
    m=prep.profile(payload,output,executable,backend)
    assert m['stopped'] and not m['launched'] and not m['autoexec_runs']
    lines=(output/'sdcard/autoexec.txt').read_text().splitlines()
    assert lines[-1]=='load wolf3d.bin'
    assert not any(line.lower().startswith(('run','runbin')) for line in lines)
    assert fw.sha(output/'esp32-firmware.bin') == fw.VDP_SHA
    assert fw.sha(output/'mos_platform.bin') == fw.MOS_SHA
    assert not (output/'executed').exists()
    before=fw.sha(output/'esp32-firmware.bin')
    with pytest.raises(ValueError,match='fresh output'):
        prep.profile(payload,output,executable,backend)
    assert fw.sha(output/'esp32-firmware.bin')==before


def test_legacy_runner_requires_specific_exception_without_implying_permission():
    with pytest.raises(SystemExit,match='historical'):
        fw.legacy_exception(['old.py'],'fixture')
    args=['old.py','--firmware-exception','source-model visual compatibility','--some-original-argument']
    fw.legacy_exception(args,'fixture')
    assert args==['old.py','--some-original-argument']


def test_every_maintained_legacy_entrypoint_refuses_before_calling_its_main():
    paths=list((ROOT/'src/asm').glob('*/scripts/*emulator*py'))
    paths += [ROOT/p for p in ('agonport/tools/setup_emulator.py','agonport/tools/stage_wolf3d_emulator.py',
        'agonport/vdplet/production/stage_target_oryx.py','agonport/vdplet/qualification/stage_rows_target_oryx.py',
        'agonport/vdplet/qualification/stage_errors.py','src/asm/wolf3d_vdplet_client/scripts/stage_oryx.py',
        'src/asm/wolf3d_vdplet_client/scripts/rehearse.py')]
    assert len(paths)==32
    for p in paths:
        tree=ast.parse(p.read_text())
        blocks=[n for n in tree.body if isinstance(n,ast.If) and '__name__' in ast.unparse(n.test)]
        assert len(blocks)==1,p
        insert = next(n for n in ast.walk(blocks[0]) if isinstance(n,ast.Call)
                      and isinstance(n.func,ast.Attribute) and n.func.attr=='insert')
        index = next(n.slice.value for n in ast.walk(insert) if isinstance(n,ast.Subscript)
                     and isinstance(n.value,ast.Attribute) and n.value.attr=='parents')
        assert p.resolve().parents[index] / 'tools/wolf_firmware.py' == ROOT/'tools/wolf_firmware.py',p
        calls=[n.value.func.id for n in blocks[0].body if isinstance(n,ast.Expr)
               and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name)]
        assert calls[0]=='legacy_exception',p


@pytest.mark.parametrize('path', [
    'src/asm/wolf3d_actors/scripts/run_actor_emulator_regression.py',
    'agonport/vdplet/production/stage_target_oryx.py',
    'agonport/tools/setup_emulator.py',
])
def test_legacy_help_loads_guard_without_entering_runner(path):
    result=subprocess.run([sys.executable,str(ROOT/path),'--help'],
                          capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
    assert 'historical Fab/firmware runner' in result.stdout


def test_generic_deployment_manifest_includes_module_and_payload():
    import tomllib
    manifest=tomllib.loads((ROOT/'deploy.toml').read_text())
    bundle=manifest['bundles']['wolf3d']
    assert {'wolf3d.bin','wolf3d.vdpl','payload.json'} <= set(bundle['require'])
    assert all(i['source'].startswith('tgt/wolf3d-production-optimized-async-r1/') for i in bundle['items'])


def test_superseded_same_version_receipt_refused_before_output(tmp_path):
    p=ROOT/'src/asm/wolf3d/tgt/pinned/wolf3d-vdplet-direct.json'
    data=json.loads(p.read_text())
    data['required_firmware']['vdp_sha256']='b004570b607b45bbd6e87a3c704b65b23d3221981db3aac6cf2578aa22d766e3'
    old=tmp_path/'old.json';old.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='Stale build receipt'):
        prep.package(old,tmp_path/'output')
    assert not (tmp_path/'output').exists()
