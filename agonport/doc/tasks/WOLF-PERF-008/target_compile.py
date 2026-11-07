"""Use unchanged SDK admission, preserving its first failure and tool argv."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json

T = Path(__file__).resolve().parent
B = T / 'build/r01'


def main(arm):
    a = B / arm
    sdk = a / 'sdk'
    output = a / 'module'
    output.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('private_sdk_' + arm, sdk / 'tools/build_module.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.run
    commands = []

    def trace(args, **kwargs):
        commands.append(list(map(str, args)))
        (output / 'tool-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        return original(args, **kwargs)

    module.run = trace
    compiler = Path('/home/smith/.platformio/packages/toolchain-xtensa-esp32/bin/xtensa-esp32-elf-gcc')
    try:
        entry = module.build_one(a / 'native-source/wolf3d_module.cpp', output, compiler,
            'wolf_perf', 1, 0x20261104, 257, 65536, 16384, 2048, 131072,
            math=arm == 'candidate', abi_minor=6, psram_workaround=True, text_profile='standard')
    except Exception as error:
        (output / 'admission-failure.json').write_text(json.dumps({
            'type': type(error).__name__, 'message': str(error), 'commands': commands}, indent=2) + '\n')
        raise
    (output / 'wolf_perf.json').write_text(json.dumps(entry, indent=2) + '\n')
    if arm == 'original':
        assert hashlib.sha256((output / 'wolf_perf.vdpl').read_bytes()).hexdigest() == \
            'c8f99354bef6495e76f15201e64bdd010da6369a0b91d2fed37c0a3eb27f997d'


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--arm', choices=('original', 'candidate'), required=True)
    main(p.parse_args().arm)
