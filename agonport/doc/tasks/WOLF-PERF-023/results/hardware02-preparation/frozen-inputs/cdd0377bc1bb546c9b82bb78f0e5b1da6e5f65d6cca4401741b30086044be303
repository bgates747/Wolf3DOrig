"""Record actual SDK tool argv while preserving its selected build path."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess
T=Path(__file__).resolve().parent;B=T/'build/r01'

def main(arm):
    a=B/arm;sdk=a/'sdk';output=a/'module';output.mkdir(exist_ok=False)
    spec=importlib.util.spec_from_file_location('private_sdk_'+arm,sdk/'tools/build_module.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original=module.run;commands=[]
    def trace(args,**kwargs):
        commands.append(list(map(str,args)))
        (output/'tool-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        return original(args,**kwargs)
    module.run=trace
    compiler=Path('/home/smith/.platformio/packages/toolchain-xtensa-esp32/bin/xtensa-esp32-elf-gcc')
    entry=module.build_one(a/'native-source/wolf3d_module.cpp',output,compiler,'wolf_perf',1,0x20261104,257,65536,16384,2048,131072,math=False,abi_minor=6,psram_workaround=True,text_profile='standard')
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    manifest=dict(compiler=subprocess.check_output([str(compiler),'--version'],text=True).splitlines()[0],
        abi_header_sha256=sha(sdk/'include/vdplet.h'),protocol_header_sha256=sha(sdk/'include/vdplet_protocol.h'),
        services_header_sha256=sha(sdk/'include/vdplet_services.h'),pcm_sink_header_sha256=sha(sdk/'include/vdplet_pcm_sink.h'),module=entry)
    (output/'wolf_perf.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',choices=('original','candidate'),required=True);main(p.parse_args().arm)
